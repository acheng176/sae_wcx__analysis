from db_handler import DatabaseHandler
import sqlite3

def check_database_order():
    """データベースの内容を異なる並び順で確認する"""
    try:
        print("\nデータベースの並び順を確認します...")
        db = DatabaseHandler()
        
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

    except Exception as e:
        print(f"Error: データベースの確認中にエラーが発生: {str(e)}")

def check_database_content():
    """データベースの詳細な内容を確認する"""
    try:
        print("\nデータベースの詳細内容を確認します...")
        db = DatabaseHandler()
        
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

    except Exception as e:
        print(f"Error: データベースの確認中にエラーが発生: {str(e)}")

def fix_missing_session_data():
    """セッション情報が欠損しているデータを補完する"""
    try:
        print("\n欠損データの補完を開始します...")
        db = DatabaseHandler()
        
        with sqlite3.connect(db.db_path) as conn:
            cursor = conn.cursor()
            
            while True:
                # 未補完の欠損データを1件取得
                cursor.execute("""
                    SELECT id, no, session_name, session_code, overview, paper_no, title
                    FROM sessions
                    WHERE (session_code IS NULL OR session_code = '')
                    AND (overview IS NULL OR overview = '')
                    ORDER BY no
                    LIMIT 1
                """)
                
                row = cursor.fetchone()
                if not row:
                    print("\n全ての欠損データの補完が完了しました")
                    break
                    
                id_, no, session_name, session_code, overview, paper_no, title = row
                
                # 直前の有効なデータを取得
                cursor.execute("""
                    SELECT session_name, session_code, overview
                    FROM sessions
                    WHERE no < ?
                    AND session_code IS NOT NULL
                    AND session_code != ''
                    AND overview IS NOT NULL
                    AND overview != ''
                    ORDER BY no DESC
                    LIMIT 1
                """, (no,))
                
                prev_row = cursor.fetchone()
                if not prev_row:
                    print(f"\n警告: No.{no}の直前に有効なデータが見つかりませんでした")
                    continue
                
                prev_name, prev_code, prev_overview = prev_row
                
                # 補完内容を表示
                print("\n=== 補完対象のデータ ===")
                print("-" * 100)
                print(f"No: {no}")
                print(f"元のセッション名: {session_name}")
                print(f"新セッション名: {prev_name}")
                print(f"新セッションコード: {prev_code}")
                print(f"新概要: {prev_overview[:100]}..." if len(prev_overview) > 100 else prev_overview)
                print("-" * 100)
                
                # データを更新
                cursor.execute("""
                    UPDATE sessions 
                    SET session_name = ?,
                        session_code = ?,
                        overview = ?
                    WHERE id = ?
                """, (prev_name, prev_code, prev_overview, id_))
                
                conn.commit()
                print("データを補完しました")
                
        print("\nデータベースの補完処理を終了します")
            
    except Exception as e:
        print(f"Error: データの補完中にエラーが発生: {str(e)}")

if __name__ == "__main__":
    fix_missing_session_data() 