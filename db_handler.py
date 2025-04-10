import sqlite3
import pandas as pd
import os
from datetime import datetime

class DatabaseHandler:
    def __init__(self):
        """データベースハンドラの初期化"""
        # 出力ディレクトリの作成
        self.output_dir = os.path.join("output", "db")
        os.makedirs(self.output_dir, exist_ok=True)
        
        # データベースファイルのパス
        self.db_path = os.path.join(self.output_dir, "wcx_sessions.db")
        print(f"データベースファイルの保存先: {self.db_path}")
        self.create_tables()

    def create_tables(self):
        """必要なテーブルを作成"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # セッションテーブルの作成
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                year INTEGER,
                session_name TEXT,
                session_code TEXT,
                overview TEXT,
                category TEXT,
                subcategory TEXT,
                paper_no TEXT,
                title TEXT,
                main_author_group TEXT,
                main_author_affiliation TEXT,
                co_author_group TEXT,
                co_author_affiliation TEXT,
                organizers TEXT,
                chairperson TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            conn.commit()

    def store_data(self, data, year):
        """データをSQLiteデータベースに保存する"""
        try:
            # データの検証
            if not validate_db_input(data, year):
                print("Error: データの検証に失敗しました")
                return False
            
            # データベース接続
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # データの挿入
            for item in data:
                cursor.execute('''
                    INSERT INTO sessions (
                        year, session_name, session_code, overview,
                        category, subcategory, paper_no, title,
                        main_author_group, main_author_affiliation,
                        co_author_group, co_author_affiliation,
                        organizers, chairperson
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    year,
                    item.get('session_name', ''),
                    item.get('session_code', ''),
                    item.get('overview', ''),
                    item.get('category', ''),
                    item.get('subcategory', ''),
                    item.get('paper_no', ''),
                    item.get('title', ''),
                    item.get('main_author_group', ''),
                    item.get('main_author_affiliation', ''),
                    item.get('co_author_group', ''),
                    item.get('co_author_affiliation', ''),
                    item.get('organizers', ''),
                    item.get('chairperson', '')
                ))
            
            conn.commit()
            conn.close()
            print(f"データベースへの保存が完了しました（{len(data)}件）")
            return True
            
        except Exception as e:
            print(f"Error: データベースへの保存中にエラーが発生: {str(e)}")
            return False

    def get_category_summary(self, year=None):
        """カテゴリー別の集計を取得"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                query = "SELECT * FROM category_summary"
                if year:
                    query += f" WHERE year = {year}"
                df = pd.read_sql_query(query, conn)
            return df
        except Exception as e:
            print(f"Error: カテゴリー集計中にエラー: {e}")
            return None

    def create_visualization(self, year=None):
        """カテゴリー別の集計をグラフ化"""
        try:
            summary_df = self.get_category_summary(year)
            if summary_df is None or summary_df.empty:
                return None
            
            # グラフの作成（例：棒グラフ）
            plot = summary_df.plot(
                kind='bar',
                x='category',
                y='count',
                title=f'Category Distribution{f" for {year}" if year else ""}'
            )
            
            # グラフの保存
            output_file = os.path.join('output', f'category_summary{"_" + str(year) if year else ""}.png')
            plot.figure.savefig(output_file, bbox_inches='tight')
            print(f"グラフを保存しました: {output_file}")
            return output_file
        except Exception as e:
            print(f"Error: グラフ作成中にエラー: {e}")
            return None 