import sounddevice as sd
import numpy as np
import keyboard
import collections
import time
import os

os.environ['KMP_DUPLICATE_LIB_OK']='True'

from faster_whisper import WhisperModel

class Ear:
    def __init__(self, model_size="base.en", device="cuda"):
        print(f"[EAR] Loading Whisper Model ({model_size}) on {device}...")
        self.model = WhisperModel(model_size, device=device, compute_type="int8")
        self.sample_rate = 16000
        self.audio_queue = collections.deque()
        self.is_recording = False
        self.stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            callback=self.audio_callback,
            blocksize=2048
        )
        self.stream.start()

    def audio_callback(self, indata, frames, time, status):
        if self.is_recording:
            self.audio_queue.append(indata.copy())

    def listen(self):
        print("[EAR] Hold SPACE to talk...(ESC for cancel)")
        self.audio_queue.clear()
        
        while not keyboard.is_pressed('space'):
            if keyboard.is_pressed('esc'): return None
            time.sleep(0.01)

        print("[EAR] Listening...")
        self.is_recording = True

        while keyboard.is_pressed('space'):
            time.sleep(0.01)

        self.is_recording = False
        print("[EAR] Processing audio...")

        if not self.audio_queue: return ""

        audio_data = np.concatenate(list(self.audio_queue), axis=0).flatten().astype(np.float32)

        segments, info = self.model.transcribe(audio_data, beam_size=1,condition_on_previous_text=False)

        text = " ".join([s.text for s in segments]).strip()

        return text
    
if __name__ == "__main__":
    try:
        ear = Ear()
        print("Test Ready. Hold SPACE to talk...(ESC for cancel)")
        while True:
            result = ear.listen()
            if result:
                print(f"\n[HEARD]: {result}")
    except Exception as e:
        print(f"Error: {e}")