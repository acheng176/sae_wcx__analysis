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
        # データを取得
        df = self.get_latest_data()
        
        # 最新年と前年を取得
        years = sorted(df['year'].unique(), reverse=True)
        latest_year = years[0]
        previous_year = years[1] if len(years) > 1 else None
        
        # カテゴリ別の件数を集計
        category_counts = df.groupby(['year', 'category_ja']).size().reset_index(name='count')
        
        # 最新年のデータを準備
        latest_data = df[df['year'] == latest_year]
        previous_data = df[df['year'] == previous_year] if previous_year else None
        
        # カテゴリ別の成長率を計算
        if previous_year:
            latest_counts = category_counts[category_counts['year'] == latest_year].set_index('category_ja')['count']
            prev_counts = category_counts[category_counts['year'] == previous_year].set_index('category_ja')['count']
            growth_rates = ((latest_counts - prev_counts) / prev_counts * 100).fillna(0)
            
            # 成長率でソートしたトップカテゴリ
            top_growing = growth_rates.sort_values(ascending=False).head(5)
        
        # プロンプトの作成
        prompt = f"""
あなたは自動車産業の技術トレンド分析を専門とする上級アナリストです。
SAE WCXでの技術発表論文データを分析し、技術トレンドと今後の方向性について包括的な洞察を提供してください。

【分析の目的】
・SAE WCXでの技術発表論文データから業界全体の技術動向を把握する
・研究開発戦略立案のための重点領域を特定する
・経営層向けに簡潔で行動に結びつく示唆を提供する

【分析内容】
データを自由に分析し、最も重要だと判断される3つのトレンド・発見を抽出してください。

【出力形式】
1. 全体概要（2-3文）
   * 分析結果の要点を簡潔に述べる

重要トレンド（最重要な3つを選択）
   * 各トレンドには明確な見出しをつける
   * 各トレンドは自然な文章で記述し、以下の要素を流れるように含める:
     - トレンドの概要（1文目に重要数値を組み込む）
     - そのトレンドが示す業界の方向性
     - 技術的・市場的影響
   * 箇条書きは使わず、簡潔な段落形式で記述する
   * 数値は文中に自然に組み込む（例: 「ADASの論文は171件（前年比+3.6%）に達し、自動運転技術の重要性が高まっています」）

各項目は経営層が理解しやすい簡潔な日本語で記述し、具体的な数値や比較を含めてください。業界専門用語は必要最小限にとどめ、論文数や成長率などの定量的な裏付けを示してください。
        参考データ：
        最新年: {latest_year}
        前年: {previous_year}

        カテゴリ別件数（最新年）:
        {category_counts[category_counts['year'] == latest_year].to_string()}

        成長率トップ5カテゴリ:
        {top_growing.to_string() if previous_year else "前年データなし"}

        セッションタイトルのトレンド（最新年）:
        {latest_data['title'].head(10).to_string()}

        出力は日本語で、簡潔かつ具体的に記述してください。
        各セクションは2-3行程度で、重要なポイントを箇条書きで示してください。
        """
        
        # Azure OpenAI APIを呼び出し
        response = self.client.chat.completions.create(
            model=os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME'),
            messages=[
                {"role": "system", "content": "あなたは自動車業界の専門家で、SAE WCXのトレンド分析を行います。技術的な洞察と具体的な数値を含めた分析を提供してください。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1500
        )
        
        return response.choices[0].message.content
    
    def get_trend_analysis(self):
        """トレンド分析結果を取得"""
        try:
            analysis = self.analyze_trends()
            return analysis
        except Exception as e:
            return f"トレンド分析中にエラーが発生しました: {str(e)}" 