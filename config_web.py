# 設定ファイル（Web公開版）
import os
from pathlib import Path

# ベースディレクトリ
BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "outputs"
TEMP_DIR = BASE_DIR / "temp"

# ディレクトリを作成
OUTPUT_DIR.mkdir(exist_ok=True)
TEMP_DIR.mkdir(exist_ok=True)

# データベース設定
# ローカル開発用のSQLite
LOCAL_DATABASE_PATH = BASE_DIR / "database" / "ocr_patterns.db"

# 本番環境用のPostgreSQL（環境変数から取得）
DATABASE_URL = os.getenv('DATABASE_URL', f'sqlite:///{LOCAL_DATABASE_PATH}')

# データベースタイプの判定
IS_PRODUCTION = os.getenv('STREAMLIT_RUNTIME_ENV') == 'cloud' or os.getenv('DATABASE_URL') is not None

# Azure Form Recognizer設定（環境変数から取得）
AZURE_ENDPOINT = os.getenv('AZURE_ENDPOINT', "")
AZURE_API_KEY = os.getenv('AZURE_API_KEY', "")
AZURE_MODEL_ID = os.getenv('AZURE_MODEL_ID', "prebuilt-read")

# Google OCR設定（環境変数から取得）
# 本番環境では環境変数から JSON 文字列として取得
GOOGLE_CREDENTIALS_JSON = os.getenv('GOOGLE_CREDENTIALS_JSON')
if GOOGLE_CREDENTIALS_JSON:
    import json
    GOOGLE_CREDENTIALS_DICT = json.loads(GOOGLE_CREDENTIALS_JSON)
else:
    GOOGLE_CREDENTIALS_DICT = None

# OpenAI API設定（環境変数から読み込み）
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# 書類カテゴリの定義
DOCUMENT_CATEGORIES = [
    "銀行残高証明書",
    "預金通帳",
    "年金通知書",
    "確定申告書",
    "給与明細書",
    "保険証券",
    "不動産登記簿",
    "車両登録証",
    "その他財産書類"
]

# ファイルアップロードの制限
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_FILE_TYPES = ['pdf']
