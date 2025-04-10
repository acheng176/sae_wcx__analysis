from db_handler import DatabaseHandler

def clear_database():
    """データベースの全データを削除する"""
    try:
        print("データベースの削除を開始します...")
        db = DatabaseHandler()
        
        if db.delete_all_data():
            print("データベースの削除が完了しました")
        else:
            print("Error: データベースの削除に失敗しました")
            
    except Exception as e:
        print(f"Error: データベース削除中にエラーが発生: {str(e)}")

if __name__ == "__main__":
    clear_database() 