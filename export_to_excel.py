from db_handler import DatabaseHandler
import pandas as pd
import sqlite3
from datetime import datetime
import os

# カテゴリの日本語マッピング
CATEGORY_MAPPING = {
    'Internal Combustion Engine': '内燃機関技術',
    'ADAS/AVS': 'ADAS/AVS',
    'Electrification': '電動化技術',
    'Emissions Control': '排出ガス制御',
    'Vehicle Development': '車両開発',
    'Powertrain': 'パワートレイン',
    'Materials': '材料技術',
    'Crash Safety': '衝突安全',
    'Vehicle Dynamics': '車両ダイナミクス',
    'NVH': 'NVH',
    'Reliability/Durability': '信頼性/耐久性',
    'Manufacturing': '製造技術',
    'Body Engineering': '車体技術',
    'Electronics': '電装技術',
    'Human Factors': 'ヒューマンファクター',
    'Racing Technology': 'レース技術',
    'Others': 'その他'
}

# サブカテゴリの日本語マッピング
SUBCATEGORY_MAPPING = {
    'Environmental Technology': '環境技術',
    'AI/Machine Learning': 'AI/機械学習',
    'Cybersecurity': 'サイバーセキュリティ',
    'IoT': 'IoT',
    'HVAC': '空調システム',
    'Alternative Fuels': '代替燃料',
    'Battery Technology': 'バッテリー技術',
    'Connectivity': 'コネクティビティ',
    'Cooling Systems': '冷却システム',
    'Lubrication': '潤滑',
    'Software Defined Vehicle': 'ソフトウェア定義車両',
    'Recycling': 'リサイクル',
    'Hydrogen Technology': '水素技術',
    'Ammonia Technology': 'アンモニア技術',
    'Human Factors': 'ヒューマンファクター',
    'Reliability/Durability': '信頼性/耐久性',
    'Racing Technology': 'レース技術',
    'Emissions Control': '排出ガス制御',
    'Manufacturing': '製造技術',
    'Materials': '材料技術',
    'Body Engineering': '車体工学',
    'NVH': 'NVH',
    'Others': 'その他'
}

def export_to_excel():
    """データベースの内容をExcelファイルとしてエクスポート"""
    try:
        # データベースに接続
        db = DatabaseHandler()
        with sqlite3.connect(db.db_path) as conn:
            # テーブル構造を確認するクエリを実行
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(sessions)")
            columns = cursor.fetchall()
            print("\nテーブル構造:")
            for col in columns:
                print(f"- {col[1]}")
            
            # 最初の5行を確認
            print("\nデータベースの最初の5行:")
            cursor.execute("""
                SELECT *
                FROM sessions
                LIMIT 5
            """)
            rows = cursor.fetchall()
            for row in rows:
                print(row)
            
            # 全レコード数を確認
            cursor.execute("SELECT COUNT(*) FROM sessions")
            total_count = cursor.fetchone()[0]
            print(f"\n総レコード数: {total_count}件")
            
            # メインのクエリを実行してデータを取得
            query = """
                SELECT *
                FROM sessions
                ORDER BY year DESC, category, subcategory
            """
            
            # pandasのDataFrameとしてデータを読み込み
            df = pd.read_sql_query(query, conn)
            
            # カテゴリとサブカテゴリを日本語に変換
            df['category_ja'] = df['category'].map(CATEGORY_MAPPING)
            df['subcategory_ja'] = df['subcategory'].map(SUBCATEGORY_MAPPING)
            
            print("\nカテゴリマッピング:")
            for eng, ja in CATEGORY_MAPPING.items():
                print(f"- {eng} -> {ja}")
            
            print("\nサブカテゴリマッピング:")
            for eng, ja in SUBCATEGORY_MAPPING.items():
                print(f"- {eng} -> {ja}")
            
            # 元のカラムを削除
            df = df.drop(['category', 'subcategory'], axis=1)
            
            # カラムの順序を変更
            columns = df.columns.tolist()
            columns.remove('category_ja')
            columns.remove('subcategory_ja')
            new_order = columns[:6] + ['category_ja', 'subcategory_ja'] + columns[6:]
            df = df[new_order]
            
            # 出力ディレクトリの作成
            output_dir = "output/excel"
            os.makedirs(output_dir, exist_ok=True)
            
            # ファイル名に現在の日時を含める
            current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"{output_dir}/wcx_sessions_{current_time}.xlsx"
            
            # Excelファイルとして保存
            with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
                df.to_excel(
                    writer,
                    sheet_name='WCX Sessions',
                    index=False,
                    float_format="%.2f"
                )
                
                # ワークシートを取得
                worksheet = writer.sheets['WCX Sessions']
                
                # カラム幅の自動調整
                for column in worksheet.columns:
                    max_length = 0
                    column = [cell for cell in column]
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = (max_length + 2)
                    # 最大幅を100文字に制限
                    adjusted_width = min(adjusted_width, 100)
                    worksheet.column_dimensions[column[0].column_letter].width = adjusted_width
            
            print(f"\nエクスポート完了: {output_file}")
            print(f"エクスポートしたレコード数: {len(df)}件")
            
    except sqlite3.Error as e:
        print(f"データベースエラーが発生しました: {e}")
    except Exception as e:
        print(f"予期せぬエラーが発生しました: {e}")

if __name__ == "__main__":
    export_to_excel() 