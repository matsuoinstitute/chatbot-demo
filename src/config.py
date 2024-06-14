import os

from dotenv import load_dotenv

# .envファイルへの相対パス
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=env_path)

# 環境変数を取得
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
CHAINLIT_AUTH_SECRET = os.getenv('CHAINLIT_AUTH_SECRET')