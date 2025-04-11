from db_handler import DatabaseHandler
import sqlite3

def fix_missing_session_data():
    """セッション情報が欠損しているデータを補完する"""
    try:
        print("欠損データの補完を開始します...")
        db = DatabaseHandler()
        
        with sqlite3.connect(db.db_path) as conn:
            cursor = conn.cursor()
            
            # 全レコードを取得
            cursor.execute("""
                SELECT id, no, session_name, session_code, overview, paper_no, title
                FROM sessions
                ORDER BY no
            """)
            rows = cursor.fetchall()
            
            # 更新が必要なレコードを特定
            updates = []
            previous_row = None
            
            print("\n=== 補完対象のデータ ===")
            print("-" * 100)
            print(f"{'No':^5} | {'元のセッション名':^30} | {'新セッション名':^30} | {'新コード':^15} | 新概要")
            print("-" * 100)
            
            for row in rows:
                id_, no, session_name, session_code, overview, paper_no, title = row
                
                # WCX SAE...で始まり、session_codeとoverviewが空のレコードを検出
                if (session_name and session_name.startswith("WCX SAE World Congress Experience") and 
                    not session_code and not overview and 
                    previous_row is not None):
                    
                    # 前の行のデータで補完
                    prev_id, prev_no, prev_name, prev_code, prev_overview, _, _ = previous_row
                    
                    # 更新情報を保存
                    updates.append({
                        'id': id_,
                        'session_name': prev_name,
                        'session_code': prev_code,
                        'overview': prev_overview
                    })
                    
                    # 補完内容を表示
                    prev_name_short = (prev_name[:27] + '...') if len(prev_name) > 30 else prev_name
                    session_name_short = (session_name[:27] + '...') if len(session_name) > 30 else session_name
                    prev_overview_short = (prev_overview[:40] + '...') if prev_overview and len(prev_overview) > 40 else prev_overview
                    
                    print(f"{no:^5} | {session_name_short:30} | {prev_name_short:30} | {prev_code:^15} | {prev_overview_short}")
                
                previous_row = row
            
            # 更新の実行
            if updates:
                print(f"\n{len(updates)}件のデータを補完します...")
                for update in updates:
                    cursor.execute("""
                        UPDATE sessions 
                        SET session_name = ?, session_code = ?, overview = ?
                        WHERE id = ?
                    """, (
                        update['session_name'],
                        update['session_code'],
                        update['overview'],
                        update['id']
                    ))
                conn.commit()
                print("データの補完が完了しました")
            else:
                print("\n補完が必要なデータはありませんでした")
            
    except Exception as e:
        print(f"Error: データの補完中にエラーが発生: {str(e)}")

if __name__ == "__main__":
    fix_missing_session_data() 