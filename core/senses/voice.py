import sounddevice as sd
import soundfile as sf
import numpy as np
import torch
import os

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


    def speak(self, text, blend_config={'bm_george': 0.7, 'bm_fable': 0.3}):
        print(f" [ATLAS]: {text}")

        if not text.strip(): return
        
        generator = self.pipeline(
            text,
            voice=self.voice_tensor,
            speed=0.95,
        )

        for i, (gs, ps, audio) in enumerate(generator):
            self.stream.write(audio)

    def close(self):
        self.stream.stop()
        self.stream.close()

if __name__ == "__main__":
    try:
        mouth = Mouth(device="cpu")

        test_text = """
        Hello Sir, I am Atlas, ASPIRING THINKING LOCAL ADMINISTRATIVE SYSTEM. Always a pleasure seeing you work sir.
        """
        voice = {'bm_george': 0.7, 'bm_fable': 0.3}
        mouth.speak(test_text, blend_config=voice)
    except Exception as e:
        print(f"An error occurred: {e}")