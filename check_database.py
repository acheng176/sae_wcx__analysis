from db_handler import DatabaseHandler
import sqlite3

def check_database():
    """データベースの内容を確認する"""
    try:
        print("データベースの内容を確認します...")
        db = DatabaseHandler()
        
        # データベースに接続
        with sqlite3.connect(db.db_path) as conn:
            cursor = conn.cursor()
            
            # 総レコード数を取得
            cursor.execute("SELECT COUNT(*) FROM sessions")
            total_count = cursor.fetchone()[0]
            print(f"\n総レコード数: {total_count}")
            
            # 全レコードを取得
            cursor.execute("""
                SELECT id, no, year, session_name, session_code, overview, 
                       category, subcategory, paper_no, title, 
                       main_author_group, main_author_affiliation,
                       co_author_group, co_author_affiliation
                FROM sessions
                ORDER BY no
            """)
            
            # カラム名を取得
            columns = [description[0] for description in cursor.description]
            
            # 結果を表示
            print("\nデータベースの内容:")
            print("-" * 100)
            for row in cursor.fetchall():
                print("\n--- レコード ---")
                for col, val in zip(columns, row):
                    # 長いフィールドは省略して表示
                    if val and isinstance(val, str) and len(val) > 100:
                        val = val[:100] + "..."
                    print(f"{col}: {val}")
                print("-" * 50)
            
            print("\nデータベースの確認が完了しました")
            
    except Exception as e:
        print(f"Error: データベースの確認中にエラーが発生: {str(e)}")

if __name__ == "__main__":
    check_database() 