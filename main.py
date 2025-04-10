import os
import json
from pdf_processor import process_pdfs
from ai_extractor import extract_structured_data
from categorizer import add_categories_to_data
from db_handler import DatabaseHandler
from excel_writer import write_to_excel

def save_to_json(data, year, output_dir="output"):
    """抽出したデータをJSONファイルに保存する"""
    try:
        # 出力ディレクトリの作成
        os.makedirs(output_dir, exist_ok=True)
        
        # 出力ファイル名の生成
        output_file = os.path.join(output_dir, f"sae_wcx_{year}.json")
        
        # JSONファイルに書き込み
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"JSONファイルを出力しました: {output_file}")
        return True
        
    except Exception as e:
        print(f"警告: JSONファイルの保存中にエラーが発生しました: {str(e)}")
        return False

def main():
    try:
        # 入力ディレクトリの設定
        input_dir = "data/input"
        
        # PDFファイルの処理
        print("\nPDFファイルの処理を開始します...")
        pdf_texts = process_pdfs(input_dir)
        if not pdf_texts:
            print("エラー: PDFファイルの処理に失敗しました")
            return
        
        # 各PDFファイルを処理
        for pdf_data in pdf_texts:
            pdf_file = pdf_data["filename"]
            input_text = pdf_data["text"]
            
            print(f"\n処理開始: {pdf_file}")
            
            # 年の抽出
            print("\n年の抽出を開始します...")
            year = None
            try:
                year = int(input_text.split()[0])
                print(f"抽出された年: {year}")
            except Exception as e:
                print(f"警告: 年の抽出に失敗しました: {str(e)}")
                print("デフォルトの年（2024）を使用します")
                year = 2024
            
            # 構造化データの抽出
            print("\n構造化データの抽出を開始します...")
            try:
                data = extract_structured_data(input_text)
                if not data:
                    print("エラー: データの抽出に失敗しました")
                    continue
                print(f"抽出されたセッション数: {len(data)}")
            except Exception as e:
                print(f"エラー: データの抽出中にエラーが発生しました: {str(e)}")
                continue
            
            # JSONファイルへの保存
            print("\nJSONファイルへの保存を開始します...")
            save_to_json(data, year)
            
            # カテゴリ分類
            print("\nカテゴリ分類を開始します...")
            try:
                data = add_categories_to_data(data)
                print("カテゴリ分類が完了しました")
            except Exception as e:
                print(f"警告: カテゴリ分類中にエラーが発生しました: {str(e)}")
                print("カテゴリ分類をスキップします")
            
            # データベースへの保存
            print("\nデータベースへの保存を開始します...")
            try:
                db_handler = DatabaseHandler()
                if not db_handler.store_data(data, year):
                    print("警告: データベースへの保存に失敗しました")
            except Exception as e:
                print(f"警告: データベースへの保存中にエラーが発生しました: {str(e)}")
            
            # Excelファイルへの書き込み
            print("\nExcelファイルへの書き込みを開始します...")
            try:
                write_to_excel(data, year)
                print("処理が完了しました")
            except Exception as e:
                print(f"エラー: Excelファイルの書き込み中にエラーが発生しました: {str(e)}")
                continue
        
    except Exception as e:
        print(f"エラー: プログラム実行中にエラーが発生しました: {str(e)}")
        return

if __name__ == "__main__":
    main()