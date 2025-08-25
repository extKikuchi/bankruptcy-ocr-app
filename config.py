# 設定ファイル（クラウド対応版）
import os
from pathlib import Path

# ベースディレクトリ（環境に応じて自動調整）
if os.getenv('STREAMLIT_RUNTIME_ENV') == 'cloud':
    # Streamlit Cloud環境
    BASE_DIR = Path.cwd()
else:
    # ローカル環境
    BASE_DIR = Path("G:/AI自己破産/cloude-ocr-output/claude-out")

OUTPUT_DIR = BASE_DIR / "outputs"
DATABASE_DIR = BASE_DIR / "database"
TEMP_DIR = BASE_DIR / "temp"

# ディレクトリを作成（エラーを無視）
try:
    OUTPUT_DIR.mkdir(exist_ok=True)
except Exception:
    pass
try:
    DATABASE_DIR.mkdir(exist_ok=True)
except Exception:
    pass
try:
    TEMP_DIR.mkdir(exist_ok=True)
except Exception:
    pass

# データベースパス
DATABASE_PATH = DATABASE_DIR / "ocr_patterns.db"

# Azure Form Recognizer設定（環境変数から取得）
AZURE_ENDPOINT = os.getenv('AZURE_ENDPOINT', "https://docintelligence-debt.cognitiveservices.azure.com/")
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
