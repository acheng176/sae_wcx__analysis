import os
from dotenv import load_dotenv

# .envファイルから環境変数を読み込む
load_dotenv()

# Azure OpenAI設定
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")
AZURE_OPENAI_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")

# フォルダパス
INPUT_FOLDER = "data/input"
OUTPUT_FOLDER = "output"

# Excel出力設定
OUTPUT_EXCEL_FILE = os.path.join(OUTPUT_FOLDER, "wcx_sessions.xlsx")

# 抽出するデータのカラム
COLUMNS = [
    "Session Name", 
    "Session Code", 
    "Paper No.", 
    "Title", 
    "Abstract",
    "Main-author GR",
    "Main-author affiliation",
    "Co-author & Affiliation Gr",
    "Region"
]