import sqlite3
import pandas as pd
import os
from datetime import datetime

class DatabaseHandler:
    def __init__(self, use_temp_db=False):
        """データベースハンドラの初期化
        
        Args:
            use_temp_db (bool): 一時的なデータベースを使用するかどうか
        """
        # 出力ディレクトリの作成
        self.output_dir = os.path.join("output", "db")
        os.makedirs(self.output_dir, exist_ok=True)
        
        # データベースファイルのパス
        if use_temp_db:
            self.db_path = os.path.join(self.output_dir, "wcx_sessions_temp.db")
            print(f"一時的なデータベースファイルの保存先: {self.db_path}")
        else:
            self.db_path = os.path.join(self.output_dir, "wcx_sessions.db")
            print(f"データベースファイルの保存先: {self.db_path}")
            
        self.create_tables()
        
        # カテゴリとサブカテゴリの翻訳マップ
        self.category_translation = {
            'Vehicle Dynamics': '車両ダイナミクス',
            'Vehicle Design': '車両設計',
            'Vehicle Safety': '車両安全',
            'Vehicle Performance': '車両性能',
            'Vehicle Testing': '車両試験',
            'Vehicle Manufacturing': '車両製造',
            'Vehicle Electronics': '車両電子制御',
            'Vehicle Materials': '車両材料',
            'Vehicle Powertrain': '車両パワートレイン',
            'Vehicle Emissions': '車両排出ガス',
            'Vehicle Noise': '車両騒音',
            'Vehicle Vibration': '車両振動',
            'Vehicle Aerodynamics': '車両空力',
            'Vehicle Thermal Management': '車両熱管理',
            'Vehicle Energy Management': '車両エネルギー管理',
            'Vehicle Connectivity': '車両コネクティビティ',
            'Vehicle Automation': '車両自動化',
            'Vehicle Electrification': '車両電動化',
            'Vehicle Sustainability': '車両持続可能性',
            'Vehicle Cybersecurity': '車両サイバーセキュリティ',
            'Vehicle Human Factors': '車両人間工学',
            'Vehicle Regulations': '車両規制',
            'Vehicle Standards': '車両標準',
            'Vehicle Education': '車両教育',
            'Vehicle History': '車両歴史',
            'Vehicle Future': '車両未来',
            'Vehicle Other': 'その他'
        }
        
        self.subcategory_translation = {
            'Aerodynamics': '空力',
            'Braking': 'ブレーキ',
            'Chassis': 'シャシー',
            'Control Systems': '制御システム',
            'Crashworthiness': '衝突安全性',
            'Dynamics': 'ダイナミクス',
            'Electronics': '電子制御',
            'Emissions': '排出ガス',
            'Energy': 'エネルギー',
            'Engine': 'エンジン',
            'Fuel': '燃料',
            'Human Factors': '人間工学',
            'Materials': '材料',
            'Noise': '騒音',
            'Performance': '性能',
            'Powertrain': 'パワートレイン',
            'Safety': '安全',
            'Simulation': 'シミュレーション',
            'Testing': '試験',
            'Thermal': '熱',
            'Tires': 'タイヤ',
            'Transmission': 'トランスミッション',
            'Vehicle Design': '車両設計',
            'Vibration': '振動',
            'Other': 'その他'
        }

    def create_tables(self):
        """必要なテーブルを作成"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # セッションテーブルの作成
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                no INTEGER,
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
            
            # 現在の最大noを取得
            cursor.execute("SELECT MAX(no) FROM sessions")
            max_no = cursor.fetchone()[0] or 0
            
            # データの挿入
            for i, item in enumerate(data, 1):
                cursor.execute('''
                    INSERT INTO sessions (
                        no, year, session_name, session_code, overview,
                        category, subcategory, paper_no, title,
                        main_author_group, main_author_affiliation,
                        co_author_group, co_author_affiliation,
                        organizers, chairperson
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    max_no + i,  # 連番を設定
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

    def delete_all_data(self):
        """データベースの全データを削除する"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM sessions")
                conn.commit()
            return True
        except Exception as e:
            print(f"Error: データの削除中にエラーが発生: {str(e)}")
            return False

    def translate_category(self, category):
        """カテゴリを日本語に翻訳"""
        return self.category_translation.get(category, category)
    
    def translate_subcategory(self, subcategory):
        """サブカテゴリを日本語に翻訳"""
        return self.subcategory_translation.get(subcategory, subcategory)

def validate_db_input(data, year):
    """データベース入力の妥当性を検証する
    
    Args:
        data (list): 検証するデータのリスト
        year (int or str): 年
        
    Returns:
        bool: データが有効な場合はTrue、そうでない場合はFalse
    """
    if not isinstance(data, list):
        print("Error: データはリストである必要があります")
        return False
        
    if not isinstance(year, (int, str)):
        print("Error: 年は整数または文字列である必要があります")
        return False
        
    required_fields = [
        "session_name",
        "session_code",
        "overview",
        "paper_no",
        "title",
        "category",
        "subcategory"
    ]
    
    for item in data:
        if not isinstance(item, dict):
            print("Error: 各データ項目は辞書である必要があります")
            return False
            
        for field in required_fields:
            if field not in item:
                print(f"Error: 必須フィールド '{field}' が欠けています")
                return False
                
            if not isinstance(item[field], str):
                print(f"Error: フィールド '{field}' は文字列である必要があります")
                return False
    
    return True 