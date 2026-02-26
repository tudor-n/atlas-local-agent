import sounddevice as sd
import soundfile as sf
import numpy as np
import torch
import os
import threading

os.environ['KMP_DUPLICATE-LIB_OK'] = 'True'

from kokoro import KPipeline

class Mouth:
    def __init__(self, device="cuda", blend_config=None):
        print(f"[VOICE] Loading Vocal Cords...")

        self.pipeline = KPipeline(lang_code='b', device=device)
        self.blend_config = blend_config or {'bm_george': 0.7, 'bm_fable': 0.3}
        self.sample_rate = 24000
        self.voice_tensor = self._mix_voices(self.blend_config)
        self.device = device

        try:
            self.stream = sd.OutputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype='float32'
            )
            self.stream.start()
        except Exception as e:
            print(f"[ERROR] Audio Stream Error: {e}")

    def _mix_voices(self, blend_config):
        mixed_voice = None
        for voice_id, weight in blend_config.items():
            if voice_id not in self.pipeline.voices:
                self.pipeline.load_voice(voice_id)

            voice_tensor = self.pipeline.voices[voice_id]
            
            if mixed_voice is None:
                mixed_voice = weight * voice_tensor
            else:
                mixed_voice += weight * voice_tensor
        return mixed_voice

    def speak(self, text, blend_config={'bm_george': 0.7, 'bm_fable': 0.3}, stop_event=None):
        if not text.strip(): return
        
        generator = self.pipeline(
            text,
            voice=self.voice_tensor,
            speed=0.95,
        )

        # 100ms chunks (Sample rate * 0.1 seconds)
        chunk_size = int(self.sample_rate * 0.1) 

        for i, (gs, ps, audio) in enumerate(generator):
            # Check if we were interrupted before processing the next sentence
            if stop_event and stop_event.is_set():
                break
                
            # Ensure audio is a numpy array for slicing
            audio_np = np.array(audio, dtype='float32')
            
            # Slice the audio into 100ms chunks and stream it
            for start in range(0, len(audio_np), chunk_size):
                # Check for interruption mid-sentence
                if stop_event and stop_event.is_set():
                    # Clear any remaining audio in the hardware buffer (optional safeguard)
                    self.stream.abort() 
                    self.stream.start()
                    return # Exit the speak method entirely

                end = min(start + chunk_size, len(audio_np))
                audio_chunk = audio_np[start:end]
                self.stream.write(audio_chunk)

    def close(self):
        self.stream.stop()
        self.stream.close()

if __name__ == "__main__":
    import time
    try:
        # Changed to CPU just for the isolated test, will use CUDA in main.py
        mouth = Mouth(device="cpu") 

        test_text = """
        Hello Sir, I am Atlas, ASPIRING THINKING LOCAL ADMINISTRATIVE SYSTEM. Always a pleasure seeing you work sir.
        """
        voice = {'bm_george': 0.7, 'bm_fable': 0.3}
        
        # Test 1: Normal playback
        print("Testing normal playback...")
        mouth.speak(test_text, blend_config=voice)
        
        time.sleep(1)
        
        # Test 2: Interrupted playback
        print("Testing interrupt playback (should cut off after 1 second)...")
        interruption_event = threading.Event()
        
        # Start speaking in a background thread so we can trigger the interrupt
        speak_thread = threading.Thread(target=mouth.speak, args=(test_text, voice, interruption_event))
        speak_thread.start()
        
        time.sleep(1) # Let him speak for 1 second
        print("[!] INTERRUPTING ATLAS!")
        interruption_event.set() # Trigger the cutoff
        speak_thread.join()
        
    except Exception as e:
        print(f"An error occurred: {e}")