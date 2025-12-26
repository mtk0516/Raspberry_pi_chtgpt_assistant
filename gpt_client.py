# gpt_client.py
import os
from openai import OpenAI

# 環境変数 OPENAI_API_KEY を使用
_client = OpenAI()

MODEL = "gpt-4.1-mini"  # ここは好みで変えてもよいが、mini以外のモデルだとレスポンス遅い

def ask_gpt(user_text: str, system_text: str | None = None) -> str:
    """
    OpenAI Responses APIで user_text を投げ、テキスト応答を返す。
    """
    messages = []
    if system_text:
        messages.append({"role": "system", "content": system_text})
    messages.append({"role": "user", "content": user_text})

    # Responses API（最新推奨）
    resp = _client.responses.create(
        model=MODEL,
        input=messages,
        temperature=0.75,
        max_output_tokens=2048,
    )
    # SDKの helper（output_text）を使うと楽（v1.40+）
    try:
        return resp.output_text  # まとまったテキスト
    except AttributeError:
        # 念のためフォールバック
        # choices[0].message.content のような形式に入っている場合がある
        for out in getattr(resp, "output", []) or []:
            if out and getattr(out, "content", None):
                # content は list; text型を連結
                chunks = [c.text for c in out.content if getattr(c, "type", "") == "output_text"]
                if chunks:
                    return "".join(chunks)
        return ""
