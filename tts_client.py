from openai import OpenAI
from pathlib import Path
import subprocess
import time

client = OpenAI(timeout=20.0)
TTS_MODEL = "gpt-4o-mini-tts"
VOICE = "alloy"
TTS_OUT = Path("/tmp/tts_out.wav")   # 固定!

def speak(text: str):
    if not text.strip():
        return

    start = time.time()

    # --- TTS生成 ---
    gen_start = time.time()
    resp = client.audio.speech.create(
        model=TTS_MODEL,
        voice=VOICE,
        input=text,
    )
    audio_bytes = resp.read()
    TTS_OUT.write_bytes(audio_bytes)
    gen_end = time.time()

    # --- 再生 非同期 ---
    play_start = time.time()
    subprocess.Popen(
        ["pw-play", str(TTS_OUT)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    play_end = time.time()

    print(f"[TTS GEN]   {gen_end - gen_start:.2f}s")
    print(f"[TTS PLAY]  {play_end - play_start:.4f}s (non-blocking)")
    print(f"[TTS TOTAL] {time.time() - start:.2f}s")
