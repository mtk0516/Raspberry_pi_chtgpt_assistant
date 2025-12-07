# test_vosk_input.py
import sounddevice as sd
import numpy as np
from vosk import Model, KaldiRecognizer
import json

sd.default.device = ("hw:0,0", None)
sd.default.channels = 1
sd.default.samplerate = 48000
sd.default.dtype = "int16"

model = Model("/home/user/models/vosk-model-ja-0.22")
rec = KaldiRecognizer(model, 16000)

print("話しかけてください Ctrl+Cで終了")

def callback(indata, frames, t, status):
    audio = indata[:, 0].copy()
    audio16 = np.interp(
        np.arange(0, len(audio)*16000/48000),
        np.arange(0, len(audio)),
        audio
    ).astype(np.int16).tobytes()

    if rec.AcceptWaveform(audio16):
        print("[FINAL]", json.loads(rec.Result())["text"])
    else:
        print("[PARTIAL]", json.loads(rec.PartialResult())["partial"])

with sd.InputStream(callback=callback):
    import time
    while True:
        time.sleep(0.1)
