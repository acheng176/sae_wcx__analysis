import os
from dotenv import load_dotenv
from datetime import datetime

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
base_filename = "wcx_sessions"
current_date = datetime.now().strftime("%Y%m%d")
OUTPUT_EXCEL_FILE = os.path.join(OUTPUT_FOLDER, f"{base_filename}_{current_date}.xlsx")

# 抽出するデータのカラム
COLUMNS = [
    "Session_Name", 
    "Session_Code", 
    "Abstract",
    "Paper_No", 
    "Title", 
    "Authors",
    "Affiliations",
    "Organizers",
    "Chairperson"
]