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
                no INTEGER,
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

    def store_data(self, df, year):
        """データをSQLiteデータベースに保存する"""
        try:
            # データベース接続
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # テーブルが存在しない場合は作成
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    year INTEGER,
                    session_name TEXT,
                    session_code TEXT,
                    overview TEXT,
                    paper_no TEXT,
                    title TEXT,
                    main_author_group TEXT,
                    main_author_affiliation TEXT,
                    co_author_group TEXT,
                    co_author_affiliation TEXT,
                    organizers TEXT,
                    chairperson TEXT,
                    category TEXT,
                    subcategory TEXT
                )
            ''')
            
            # データの挿入
            records = df.to_dict('records')
            total_records = len(records)
            inserted_records = 0
            
            for record in records:
                try:
                    cursor.execute('''
                        INSERT INTO sessions (
                            year, session_name, session_code, overview,
                            paper_no, title, main_author_group, main_author_affiliation,
                            co_author_group, co_author_affiliation, organizers,
                            chairperson, category, subcategory
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        year,
                        record.get('session_name', ''),
                        record.get('session_code', ''),
                        record.get('overview', ''),
                        record.get('paper_no', ''),
                        record.get('title', ''),
                        record.get('main_author_group', ''),
                        record.get('main_author_affiliation', ''),
                        record.get('co_author_group', ''),
                        record.get('co_author_affiliation', ''),
                        record.get('organizers', ''),
                        record.get('chairperson', ''),
                        record.get('category', ''),
                        record.get('subcategory', '')
                    ))
                    inserted_records += 1
                except Exception as e:
                    print(f"Warning: レコードの挿入中にエラー: {e}")
                    print(f"問題のあるレコード: {record}")
                    continue
            
            # 変更をコミット
            conn.commit()
            
            # 格納状況の表示
            print(f"\nデータベース格納状況:")
            print(f"総レコード数: {total_records}")
            print(f"正常に格納されたレコード数: {inserted_records}")
            print(f"格納失敗レコード数: {total_records - inserted_records}")
            
            # テーブルの現在の総レコード数を表示
            cursor.execute("SELECT COUNT(*) FROM sessions")
            total_in_db = cursor.fetchone()[0]
            print(f"データベース内の総レコード数: {total_in_db}")
            
            # 今年のレコード数を表示
            cursor.execute("SELECT COUNT(*) FROM sessions WHERE year = ?", (year,))
            year_records = cursor.fetchone()[0]
            print(f"{year}年のレコード数: {year_records}")
            
            # 接続を閉じる
            conn.close()
            
            return True
        except Exception as e:
            print(f"Error: データベース保存中にエラー: {e}")
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