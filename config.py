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

# Excel出力設定のベース
base_filename = "wcx_sessions"

# 注: ファイル名は extract_year_from_text 関数により
# YYYY_base_filename.xlsx 形式に変更されます

# 抽出するデータのカラム
COLUMNS = [
    "Session_Name", 
    "Session_Code", 
    "Overview",
    "Paper_No", 
    "Title", 
    "Authors",
    "Affiliations",
    "Organizers",
    "Chairperson"
]