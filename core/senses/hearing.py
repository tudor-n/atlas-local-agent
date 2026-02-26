import numpy as np
import sounddevice as sd
import torch
import queue
import threading
import collections
import os
from colorama import Fore
from faster_whisper import WhisperModel

os.environ['KMP_DUPLICATE_LIB_OK']='True'

class Ear:
    def __init__(self, model_size="base.en", device="cuda"):
        print(Fore.YELLOW + f"[EAR] Loading Whisper Model ({model_size}) on {device}...")
        self.whisper_model = WhisperModel(model_size, device=device, compute_type="int8")

        print(Fore.YELLOW + "[EAR] Loading Silero VAD (Voice Activity Detection)...")
        self.vad_model, utils = torch.hub.load(
            repo_or_dir='snakers4/silero-vad',
            model='silero_vad',
            force_reload=False,
            trust_repo=True
        )
        self.vad_model.to(device)
        self.device = device

        self.sample_rate = 16000
        self.chunk_size = 512
        self.transcription_queue = queue.Queue()
        
        self.is_listening = False
        self.current_stop_event = None

    def set_interrupt_target(self, stop_event):
        self.current_stop_event = stop_event

    def start_listening(self):
        self.is_listening = True
        self.stream_thread = threading.Thread(target=self._vad_audio_loop, daemon=True)
        self.stream_thread.start()

    def stop_listening(self):
        self.is_listening = False

    def _vad_audio_loop(self):
        buffer = []
        is_speaking = False
        silence_chunks = 0
        
        # THE PRE-ROLL BUFFER: Stores the last ~0.5 seconds of audio to catch the start of words
        ring_buffer = collections.deque(maxlen=15) 
        
        # Wait ~1.2 seconds of silence before sending to Whisper
        MAX_SILENCE_CHUNKS = int((self.sample_rate / self.chunk_size) * 1.2) 

        print(Fore.GREEN + "[EAR] Continuous listening active. Speak naturally to interact.")
        
        with sd.InputStream(samplerate=self.sample_rate, channels=1, dtype='float32', blocksize=self.chunk_size) as stream:
            while self.is_listening:
                try:
                    audio_chunk, overflow = stream.read(self.chunk_size)
                    if overflow: continue
                        
                    audio_np = audio_chunk.flatten()
                    
                    # Always keep the pre-roll buffer updated
                    ring_buffer.append(audio_np)

                    # Silero VAD evaluation
                    audio_tensor = torch.from_numpy(audio_np).unsqueeze(0).to(self.device)
                    speech_prob = self.vad_model(audio_tensor, self.sample_rate).item()

                    # Threshold increased to 0.7 to ignore breathing/computer fans better
                    if speech_prob > 0.7: 
                        if not is_speaking:
                            is_speaking = True
                            silence_chunks = 0
                            
                            # Inject the pre-roll audio so we don't clip the first word!
                            buffer = list(ring_buffer) 
                            
                            # Trigger Barge-in
                            if self.current_stop_event and not self.current_stop_event.is_set():
                                self.current_stop_event.set()
                        else:
                            buffer.append(audio_np)
                            silence_chunks = 0
                            
                    elif is_speaking:
                        buffer.append(audio_np)
                        silence_chunks += 1
                        
                        if silence_chunks > MAX_SILENCE_CHUNKS:
                            is_speaking = False
                            full_audio = np.concatenate(buffer)
                            buffer = []
                            threading.Thread(target=self._transcribe_audio, args=(full_audio,), daemon=True).start()
                except Exception as e:
                    print(Fore.RED + f"[EAR] Audio read error: {e}")

    def _transcribe_audio(self, audio_array):
        try:
            amplitude = np.abs(audio_array).mean()
            if amplitude < 0.005: 
                return

            segments, info = self.whisper_model.transcribe(
                audio_array, 
                beam_size=1, 
                condition_on_previous_text=False,
                # Added 'hypothesize' and 'imagine' to bias the model towards your Romanian accent!
                initial_prompt="Atlas, exit, shutdown, robot, engineering, system, vitals, hypothesize, imagine." 
            )
            text = " ".join([s.text for s in segments]).strip()
            
            if len(text) < 3: return
            
            words = text.lower().replace('.', '').replace(',', '').split()
            if len(words) > 5:
                unique_words = len(set(words))
                diversity_ratio = unique_words / len(words)
                if diversity_ratio < 0.4: 
                    # GLASS BRAIN PRINT:
                    print(Fore.LIGHTBLACK_EX + f" [EAR] Dropped hallucination (repetitive): {text}")
                    return 

            junk_phrases = ["thank you", "okay", "bye", "subscribe", "it's all good", "all good", "thanks for watching"]
            lower_text = text.lower()
            if any(junk in lower_text for junk in junk_phrases) and len(words) < 15:
                # GLASS BRAIN PRINT:
                print(Fore.LIGHTBLACK_EX + f" [EAR] Dropped junk phrase: {text}")
                return 
                
            self.transcription_queue.put(text)
            
        except Exception as e:
            print(Fore.RED + f"[EAR] Transcription error: {e}")

    def wait_for_input(self):
        return self.transcription_queue.get()