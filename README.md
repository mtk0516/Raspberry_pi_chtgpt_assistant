# Raspberry_pi_chtgpt_assistant
raspi5(Debian環境)で動作する音声ベースのgpt_aiアシスタントのモジュール<br>
他の環境でもPython環境があれば動作するかも？未確認<br>
適宜、main.pyにGPTへのPROMPTが入っていますので、好きにいじってください。

# requirements
喋った音声の認識モデルとして、voskというモデルを利用しています。<br>
以下いずれかをDLして解凍したうえで、detect_core.pyのDEFAULT_MODEL変数にパスを通してください。<br>
 ⇒こっちのが認識精度高い [vosk_0.22_ja_large](https://alphacephei.com/vosk/models/vosk-model-ja-0.22.zip)<br>
[vosk_0.22_ja_small](https://alphacephei.com/vosk/models/vosk-model-small-ja-0.22.zip)

<br>
当然ですが、マイク入力と音声出力ができる環境が必要になります。<br>

# start
python main.py

# notice
export OPENAI_API_KEY=st_xxx で事前に環境変数にapikeyの設定が必要<br>
※openai api利用(課金)が前提<br>
「スタート」というwakewordは任意に変更してください、その他local_modelのpathなども同様
