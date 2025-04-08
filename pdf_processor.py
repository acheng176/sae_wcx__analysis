import os
import PyPDF2
from tqdm import tqdm

def extract_text_from_pdf(pdf_path):
    """PDFからテキストを抽出する"""
    print(f"\nProcessing PDF: {pdf_path}")
    text = ""
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            print(f"PDF has {len(reader.pages)} pages")
            for page_num in range(len(reader.pages)):
                page_text = reader.pages[page_num].extract_text()
                # セッションの区切りを保持
                page_text = page_text.replace("Session Code", "\nSession Code")
                page_text = page_text.replace("Room", "\nRoom")
                page_text = page_text.replace("Organizers", "\nOrganizers")
                text += page_text + "\n\n"  # ページ間の区切りを追加
                if page_num == 0:  # 最初のページのサンプルテキストを表示
                    print(f"Sample text from first page (first 200 chars): {page_text[:200]}")
        print(f"Successfully extracted {len(text)} characters from PDF")
        return text
    except Exception as e:
        print(f"Error extracting text from {pdf_path}: {e}")
        return ""

def process_pdfs(input_folder):
    """フォルダ内のすべてのPDFを処理する"""
    print(f"\nSearching for PDFs in folder: {input_folder}")
    all_texts = []
    
    # 入力フォルダが存在するか確認
    if not os.path.exists(input_folder):
        print(f"Input folder does not exist: {input_folder}")
        return all_texts
    
    pdf_files = [f for f in os.listdir(input_folder) if f.lower().endswith('.pdf')]
    print(f"Found {len(pdf_files)} PDF files: {pdf_files}")
    
    for pdf_file in tqdm(pdf_files, desc="Processing PDFs"):
        pdf_path = os.path.join(input_folder, pdf_file)
        text = extract_text_from_pdf(pdf_path)
        if text:
            all_texts.append({
                "filename": pdf_file,
                "text": text
            })
            print(f"Added {pdf_file} to processing queue (text length: {len(text)} chars)")
        else:
            print(f"Skipping {pdf_file} due to extraction failure")
    
    print(f"Total PDFs processed: {len(all_texts)}")
    return all_texts