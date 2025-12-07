import time
from detect_core import listen_once
from gpt_client import ask_gpt
from tts_client import speak


SYSTEM_PROMPT = (
"あなたは家庭用スマートスピーカーです。" 
"聞き取った音声が少し不完全でも文脈補完して答えてください。" 
"冒頭の『スタート』などのウェイクワードは無視してください。" 
"少しユーモアを入れて返答してください。"
)

def main():
    print("[READY] 『スタート』と言って話しかけてください。")

    while True:
        print("[WAIT] 待機中...")

        # -----------------------------
        # ① 音声認識の開始
        # -----------------------------
        t0 = time.time()
        text = listen_once()
        t1 = time.time()

        print(f"[YOU] {text}")
        print(f"[TIME] ASR finished in {t1 - t0:.2f} sec")

        if not text.strip():
            continue

        # -----------------------------
        # ② GPT API 呼び出し
        # -----------------------------
        t2 = time.time()
        reply = ask_gpt(text, SYSTEM_PROMPT)
        t3 = time.time()

        print(f"[GPT] {reply}")
        print(f"[TIME] GPT responded in {t3 - t2:.2f} sec")

        # -----------------------------
        # ③ TTS 音声生成
        # -----------------------------
        t4 = time.time()
        speak(reply)
        t5 = time.time()

        print(f"[TIME] TTS+play in {t5 - t4:.2f} sec")
        print("-" * 60)

if __name__ == "__main__":
    main()
