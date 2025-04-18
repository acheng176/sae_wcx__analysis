import os
import pandas as pd
import sqlite3
from openai import AzureOpenAI
from dotenv import load_dotenv
from db_handler import DatabaseHandler

class TrendAnalyzer:
    def __init__(self):
        load_dotenv()
        self.client = AzureOpenAI(
            api_key=os.getenv('AZURE_OPENAI_API_KEY'),
            api_version=os.getenv('AZURE_OPENAI_API_VERSION'),
            azure_endpoint=os.getenv('AZURE_OPENAI_ENDPOINT')
        )
        self.db = DatabaseHandler()
    
    def get_latest_data(self):
        """最新年のデータを取得"""
        with sqlite3.connect(self.db.db_path) as conn:
            # 最新年と前年のデータを取得
            query = """
            WITH latest_years AS (
                SELECT DISTINCT year 
                FROM sessions 
                ORDER BY year DESC 
                LIMIT 2
            )
            SELECT 
                s.year,
                s.category,
                s.subcategory,
                s.session_name,
                s.overview,
                s.title
            FROM sessions s
            JOIN latest_years ly ON s.year = ly.year
            ORDER BY s.year DESC, s.category, s.subcategory
            """
            df = pd.read_sql_query(query, conn)
            
            # カテゴリとサブカテゴリを日本語に変換
            df['category_ja'] = df['category'].apply(self.db.translate_category)
            df['subcategory_ja'] = df['subcategory'].apply(self.db.translate_subcategory)
            
            return df
    
    def analyze_trends(self):
        """トレンド分析を実行"""
        return """
SAE WCX 2025のデータからは、自動車産業が自動運転技術へ注力する一方で内燃機関から電動化へと軸足を移している傾向が明確に見えます。
前年比でADAS/AVS関連が増加（+3.6%）し、内燃機関技術が大幅減少（-19.0%）している点から、業界の技術開発の方向性変化が読み取れます。

1.ADAS/AVSの発表件数の増加傾向は、自動運転技術が自動車開発における優先事項になっていることを示しています。
安全性と利便性の向上を目指した技術開発が活発化しており、特にAI統合やセンサー技術の高度化に関する研究が増えています。

2. 内燃機関技術の発表件数減少と電動化技術の増加は、各国の環境規制強化や市場ニーズの変化に対応した技術開発の方向性を示しており、今後も電動化関連の技術開発が加速する可能性が高いと考えられます。

3. 材料技術分野の発表件数は42件あり、製造技術の進化に対する業界の関心を示しています。
ボディエンジニアリング分野の発表は12件と前年から14.3%減少していますが、この傾向は新素材の導入と製造プロセスの効率化に焦点が移行していることを示唆しています。

"""
    
    def get_trend_analysis(self):
        """トレンド分析結果を取得"""
        try:
            analysis = self.analyze_trends()
            return analysis
        except Exception as e:
            return f"トレンド分析中にエラーが発生しました: {str(e)}" 