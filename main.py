import os
import config
from pdf_processor import process_pdfs
from ai_extractor import process_all_texts
from excel_writer import write_to_excel
import time

def main():
    start_time = time.time()
    print("="*80)
    print("Starting SAE WCX data extraction...")
    print("="*80)
    
    # 設定情報の表示
    print(f"Input folder: {config.INPUT_FOLDER}")
    print(f"Output folder: {config.OUTPUT_FOLDER}")
    print(f"Output Excel file: {config.OUTPUT_EXCEL_FILE}")
    
    # 入力フォルダからPDFを処理
    print("\n" + "="*40)
    print("STEP 1: Processing PDFs")
    print("="*40)
    all_texts = process_pdfs(config.INPUT_FOLDER)
    print(f"\nExtracted text from {len(all_texts)} PDF files")
    
    # 処理対象がなければ終了
    if not all_texts:
        print("No PDF files were processed. Please check the input folder.")
        return
    
    # AIを使って構造化データを抽出
    print("\n" + "="*40)
    print("STEP 2: Extracting structured data using AI")
    print("="*40)
    all_data = process_all_texts(all_texts)
    print(f"\nExtracted {len(all_data)} data records")
    
    # 処理対象がなければ終了
    if not all_data:
        print("No data was extracted. Please check the AI processing.")
        return
    
    # Excelに書き込み
    print("\n" + "="*40)
    print("STEP 3: Writing data to Excel")
    print("="*40)
    output_file = config.OUTPUT_EXCEL_FILE
    excel_path = write_to_excel(all_data, output_file)
    
    # 処理終了
    elapsed_time = time.time() - start_time
    print("\n" + "="*80)
    print(f"Processing completed in {elapsed_time:.2f} seconds")
    print(f"Output file: {excel_path}")
    print("="*80)

if __name__ == "__main__":
    main()