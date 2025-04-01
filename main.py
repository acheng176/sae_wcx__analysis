import os
import config
from pdf_processor import process_pdfs
from ai_extractor import extract_structured_data
from excel_writer import write_to_excel, extract_year_from_text
import time

def main():
    start_time = time.time()
    print("="*80)
    print("Starting SAE WCX data extraction...")
    print("="*80)
    
    # 設定情報の表示
    print(f"Input folder: {config.INPUT_FOLDER}")
    print(f"Output folder: {config.OUTPUT_FOLDER}")
    
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
    
    # 各PDFのテキストを処理
    all_data = []
    all_text_content = ""  # 全テキスト内容を集約（年の抽出用）
    
    for pdf_data in all_texts:
        # 辞書からテキストを取得（pdf_dataが辞書の場合）
        if isinstance(pdf_data, dict):
            pdf_text = pdf_data.get('text', '')
            pdf_filename = pdf_data.get('filename', 'unknown.pdf')
        else:
            # 直接テキストが返される場合
            pdf_text = pdf_data
            pdf_filename = 'unknown.pdf'
            
        print(f"Processing text from {pdf_filename} ({len(pdf_text)} characters)")
        
        # テキストが存在する場合のみ処理
        if pdf_text:
            all_text_content += pdf_text  # テキストを集約
            pdf_results = extract_structured_data(pdf_text)
            if pdf_results:
                # ソースファイル情報を追加
                for record in pdf_results:
                    record['Source File'] = pdf_filename
                
                all_data.extend(pdf_results)
                print(f"  Extracted {len(pdf_results)} records from {pdf_filename}")
    
    print(f"\nTotal extracted data records: {len(all_data)}")
    
    # 処理対象がなければ終了
    if not all_data:
        print("No data was extracted. Please check the AI processing.")
        return
    
    # 年を抽出
    year = extract_year_from_text(all_text_content)
    print(f"Extracted year from document: {year}")
    
    # 出力ファイル名の生成
    output_file = os.path.join(config.OUTPUT_FOLDER, f"{config.base_filename}.xlsx")
    print(f"Base output file: {output_file}")
    
    # Excelに書き込み
    print("\n" + "="*40)
    print("STEP 3: Writing data to Excel")
    print("="*40)
    excel_path = write_to_excel(all_data, output_file, all_text_content)
    
    # 処理終了
    elapsed_time = time.time() - start_time
    print("\n" + "="*80)
    print(f"Processing completed in {elapsed_time:.2f} seconds")
    print(f"Output file: {excel_path}")
    print("="*80)

if __name__ == "__main__":
    main()