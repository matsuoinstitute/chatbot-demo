import os

import chainlit as cl
from dotenv import load_dotenv
from openai import OpenAI

# .envファイルのパス
dotenv_path = '/workspaces/chatbot-demo/.env'
load_dotenv(dotenv_path)

# OpenAI APIキーを環境変数から取得
api_key = os.environ.get('OPENAI_API_KEY')
if not api_key:
    raise ValueError("OpenAI API key not found. Make sure it is set in the .env file.")

# OpenAIクライアントの設定
client = OpenAI(api_key=api_key)


# キャラクターの情報を読み込む関数
def load_character_info(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return "情報ファイルが見つかりませんでした。"


# キャラクター情報のロード
character_info = load_character_info('/workspaces/chatbot-demo/src/knowledge.txt')


@cl.on_chat_start
async def start():
    await cl.Message(content='やっほー、今日はどうしたの？').send()

settings = {
    "model": "gpt-3.5-turbo",
    "temperature": 0.8,
    "presence_penalty": 1.0,
    # ... more settings
}


@cl.on_message
async def on_message(message: cl.Message):
    # ユーザーのメッセージに基づいて、キャラクター情報を組み込む
    context = (
        f"{character_info}\n\n"
        "あなたは関西弁を話す高校2年生の女の子です。"
        "おしゃべりが好きで色んな話題をユーザーに与えます。"
        "第一人称は「うち」。"
    )

    response = client.chat.completions.create(
        messages=[
            {"role": "system", "content": context},
            {"role": "user", "content": message.content}
        ],
        **settings
    )
    await cl.Message(content=response.choices[0].message.content).send()
