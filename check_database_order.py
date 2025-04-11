from db_handler import DatabaseHandler
import sqlite3

def check_database_order():
    """データベースの内容を抽出順序で確認する"""
    try:
        print("データベースの内容を確認します...")
        db = DatabaseHandler()
        
        # データベースに接続
        with sqlite3.connect(db.db_path) as conn:
            cursor = conn.cursor()
            
            # 異なる並び順でデータを取得して比較
            queries = {
                "ID順": "SELECT id, no, session_code, session_name, paper_no, title FROM sessions ORDER BY id",
                "No順": "SELECT id, no, session_code, session_name, paper_no, title FROM sessions ORDER BY no",
                "登録順": "SELECT id, no, session_code, session_name, paper_no, title FROM sessions ORDER BY created_at",
                "セッションコード順": "SELECT id, no, session_code, session_name, paper_no, title FROM sessions ORDER BY session_code"
            }
            
            for order_name, query in queries.items():
                print(f"\n=== {order_name} ===")
                print("-" * 100)
                cursor.execute(query)
                rows = cursor.fetchall()
                
                print(f"{'ID':^5} | {'No':^5} | {'セッションコード':^15} | {'セッション名':^30} | {'論文番号':^10} | タイトル")
                print("-" * 100)
                
                for row in rows:
                    id_, no, code, name, paper, title = row
                    # 長いフィールドは省略
                    name = (name[:27] + '...') if name and len(name) > 30 else (name or '').ljust(30)
                    title = (title[:40] + '...') if title and len(title) > 40 else (title or '')
                    print(f"{id_:^5} | {no:^5} | {code or '':^15} | {name} | {paper or '':^10} | {title}")
            
            print("\nデータベースの確認が完了しました")
            
    except Exception as e:
        print(f"Error: データベースの確認中にエラーが発生: {str(e)}")

if __name__ == "__main__":
    check_database_order() 