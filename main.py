import os
import config
from pdf_processor import process_pdfs
from ai_extractor import extract_structured_data
from excel_writer import write_to_excel, extract_year_from_text
import time

def main():
    """メイン処理"""
    try:
        # 入力ファイルのパス
        input_file = "input/2024_wcx_program.txt"
        
        # 出力ファイル名の生成
        year = get_year_from_text(input_file)
        output_file = f"wcx_sessions_{year}.xlsx"
        
        # テキストの読み込み
        text_content = read_text_file(input_file)
        if not text_content:
            return
        
        # データの抽出
        all_data = extract_structured_data(text_content)
        if not all_data:
            print("Error: データの抽出に失敗しました")
            return
        
        # Excelファイルへの書き込み
        excel_file, df = write_to_excel(all_data, output_file, text_content)
        if not excel_file:
            print("Error: Excelファイルの作成に失敗しました")
            return
        
        # データベースへの保存
        db_handler = DatabaseHandler()
        if not db_handler.store_data(df, year):
            print("Error: データベースへの保存に失敗しました")
            return
        
        print("\n処理が完了しました")
        print(f"Excelファイル: {excel_file}")
        print(f"データベース: {db_handler.db_path}")
        
    except Exception as e:
        print(f"Error: メイン処理中にエラーが発生: {e}")

if __name__ == "__main__":
    main()