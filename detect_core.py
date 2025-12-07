# detect_core.py
# Voskで「スタート」検出→一定時間だけ認識→最終テキストを返すユーティリティ

import queue, sys, json, time, re
from pathlib import Path
import numpy as np
import sounddevice as sd
from vosk import Model, KaldiRecognizer

DEFAULT_MODEL = Path("/home/user/デスクトップ/python/rasgpt/model/vosk-model-ja-0.22")

DEFAULT_MIC_KEY = "UACDemoV1.0"
DEFAULT_BLOCK_FRAMES = 24000       # 48kHz で約0.5秒
DEFAULT_WINDOW_SEC = 8.85             # ウェイク後に聞く時間（秒）
DEFAULT_WAKE = ["スタート", "すたーと", "start", "開始"]
QUEUE_MAX = 16

_audio_q = queue.Queue(maxsize=QUEUE_MAX)
_model_cache: dict[str, Model] = {}
_dropped = 0


def _get_model(model_dir: Path) -> Model:
    key = str(model_dir)
    if key not in _model_cache:
        print(f"[LOAD] Vosk model loading ... {key}", flush=True)
        _model_cache[key] = Model(key)
    return _model_cache[key]


def _pick_input_device(name_keyword: str | None):
    devices = sd.query_devices()
    if name_keyword:
        for idx, d in enumerate(devices):
            if d["max_input_channels"] > 0 and name_keyword.lower() in d["name"].lower():
                return idx, d
    for idx, d in enumerate(devices):
        if d["max_input_channels"] > 0:
            return idx, d
    return None, None


def _audio_cb(indata, frames, time_info, status):
    global _dropped
    if status:
        # Input overflow はよく出るので軽くログするだけ
        if "Input overflow" in str(status):
            _dropped += 1
            # print(f"[WARN] Input overflow ({_dropped})", file=sys.stderr, flush=True)
        else:
            print(status, file=sys.stderr, flush=True)

    try:
        _audio_q.put_nowait(bytes(indata))
    except queue.Full:
        try:
            _audio_q.get_nowait()
            _audio_q.put_nowait(bytes(indata))
            _dropped += 1
        except queue.Empty:
            pass


def _normalize(text: str) -> str:
    # スペースや記号を除去・小文字化
    t = re.sub(r"\s+", "", text)
    t = re.sub(r"[！!。．,.、・ー\-＿_/\\~^`＋+＝=]", "", t)
    return t.lower()

def _contains_wake(text: str, wake_list) -> bool:
    nt = _normalize(text)
    for w in wake_list:
        if nt.endswith(_normalize(w)):    # 文末一致
            return True
    return False



def _downsample_int16(raw_bytes: bytes, in_sr: int, out_sr: int = 16000) -> bytes:
    if in_sr == out_sr:
        return raw_bytes
    x = np.frombuffer(raw_bytes, dtype=np.int16)
    ratio = in_sr / out_sr
    # 48k または 44.1k → 16k のだいたい3分の1間引き
    if abs(ratio - 3.0) < 1e-6 or abs(ratio - 2.75625) < 1e-3:
        return x[::3].tobytes()
    return raw_bytes


def listen_once(
    model_dir: str | Path = DEFAULT_MODEL,
    mic_key: str = DEFAULT_MIC_KEY,
    device_index: int | None = None,
    block_frames: int = DEFAULT_BLOCK_FRAMES,
    window_sec: int = DEFAULT_WINDOW_SEC,
    wake_list = DEFAULT_WAKE,
    phrases: list[str] | None = None,
    max_total_sec: int = 30,          # 全体タイムアウト
    silence_after_wake_sec: float = 1.5,  # ウェイク後無音が続いたら終了
) -> str:
    """
    ウェイクワード検出後、window_sec または 無音一定時間 だけ認識し、最終テキストを返す。
    テキストが無ければ空文字を返す。
    """

    model_path = Path(model_dir)
    if not model_path.exists():
        raise FileNotFoundError(f"Voskモデルが見つかりません: {model_path}")

    model = _get_model(model_path)

    if device_index is not None:
        dev_idx = device_index
        sd.query_devices(dev_idx)
    else:
        dev_idx, dev = _pick_input_device(mic_key)
    if dev_idx is None:
        raise RuntimeError("入力デバイスが見つかりません。")

    in_sr = int(sd.query_devices(dev_idx)["default_samplerate"])
    sd.default.device = (dev_idx, None)
    sd.default.channels = 1

    # recognizer は毎回作り直しでOK（軽い）
    if phrases:
        import json as _json
        rec = KaldiRecognizer(model, 16000, _json.dumps(phrases))
    else:
        rec = KaldiRecognizer(model, 16000)
    rec.SetWords(True)

    # キューをクリア
    while not _audio_q.empty():
        try:
            _audio_q.get_nowait()
        except queue.Empty:
            break

    print(f"[WAIT] Listening... (device={dev_idx}, SR={in_sr})", flush=True)

    listening = False
    deadline = 0.0
    buffer: list[str] = []
    start_time = time.time()
    last_activity = start_time  # 何か喋った/Partialが出た時刻

    part_count = 0
    full_count = 0

    with sd.RawInputStream(
        samplerate=in_sr,
        blocksize=block_frames,
        dtype="int16",
        channels=1,
        callback=_audio_cb,
        latency="high",
    ):
        while True:
            # 全体タイムアウト
            now = time.time()
            if now - start_time > max_total_sec:
                print("[TIMEOUT] max_total_sec reached, return.", flush=True)
                return " ".join(buffer).strip()

            try:
                data = _audio_q.get(timeout=0.5)
            except queue.Empty:
                # しばらく音が来てない
                if listening and (now - last_activity) > silence_after_wake_sec:
                    # サイレンスで早期終了
                    final = json.loads(rec.FinalResult())
                    tail = (final.get("text") or "").strip()
                    if tail:
                        buffer.append(tail)
                    result = " ".join(buffer).strip()
                    print(f"[RESULT(silence)] {result}", flush=True)
                    return result
                continue

            data16 = _downsample_int16(data, in_sr, 16000)

            # FULL result 内でだけ wake を拾う
            if rec.AcceptWaveform(data16):
                res = json.loads(rec.Result())
                text = (res.get("text") or "").strip()
                if text:
                    print(f"[FULL] {text}")
                    last_activity = now

                if not listening:
                    # ← PARTIAL ではやらない！
                    if text and _contains_wake(text, wake_list):
                        listening = True
                        deadline = now + window_sec
                        buffer.clear()
                        print(f"[WAKE] Wake detected → start {window_sec}s recognition")

                    # listening でないときは何もためない
                else:
                    if text:
                        buffer.append(text)

            else:
                part = (json.loads(rec.PartialResult()).get("partial") or "").strip()
                if part:
                    part_count += 1
                    print(f"[PART {now - start_time:5.2f}s] {part}", flush=True)
                    last_activity = now

                if not listening and part and _contains_wake(part, wake_list):
                    listening = True
                    deadline = now + window_sec
                    buffer.clear()
                    print(f"[WAKE] (partial) Wake detected → start {window_sec}s recognition", flush=True)

            # ウェイク後の終了条件
            now = time.time()
            if listening:
                # ① 時間で切る
                if now >= deadline:
                    final = json.loads(rec.FinalResult())
                    tail = (final.get("text") or "").strip()
                    if tail:
                        buffer.append(tail)
                    result = " ".join(buffer).strip()
                    print(f"[RESULT(time)] {result}", flush=True)
                    return result

                # ② サイレンスで切る
                if (now - last_activity) > silence_after_wake_sec:
                    final = json.loads(rec.FinalResult())
                    tail = (final.get("text") or "").strip()
                    if tail:
                        buffer.append(tail)
                    result = " ".join(buffer).strip()
                    print(f"[RESULT(silence2)] {result}", flush=True)
                    return result
