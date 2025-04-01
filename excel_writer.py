import pandas as pd
import os
import config
import re
from datetime import datetime

def clean_string_array(text):
    """文字列として表現された配列をクリーニングする（シングルクォーテーションと角括弧を除外）"""
    if text is None:
        return ""
        
    # 文字列に変換
    text = str(text)
    
    # 角括弧（[]）を削除
    text = text.replace('[', '').replace(']', '')
    
    # シングルクォート（'）を削除
    text = text.replace("'", "")
    
    # 余分なスペースを削除
    text = re.sub(r'\s+', ' ', text.strip())
    
    # 末尾のカンマやセミコロンを削除
    text = re.sub(r'[,;]\s*$', '', text)
    
    return text

def extract_year_from_text(text):
    """赤字で書かれた日付から年を抽出する（今回は入力テキストから年を抽出）"""
    # 年を抽出するための正規表現パターン
    # "2024年"や"2024", "April 2024", "2024 Apr"などの形式に対応
    patterns = [
        r'20\d{2}年',  # 2024年
        r'20\d{2}',    # 2024
        r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+20\d{2}',  # April 2024
        r'20\d{2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)'  # 2024 Apr
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text)
        if matches:
            # 最初に見つかった年を使用
            year_match = matches[0]
            # 数字だけを抽出
            year = re.search(r'20\d{2}', year_match).group(0)
            return year
    
    # 見つからない場合は現在の年を使用
    return str(datetime.now().year)

def write_to_excel(data, output_file, input_text=""):
    """抽出データをExcelに書き込む（シート名を年に設定）"""
    print(f"\nPreparing to write data to Excel: {output_file}")
    
    # 年を抽出
    year = extract_year_from_text(input_text)
    print(f"Extracted year: {year}")
    
    # 出力ファイル名を年を含む形式に変更
    file_dir = os.path.dirname(output_file)
    file_name = os.path.basename(output_file)
    
    # ファイル名パターンを変更: base_filename_YYYYMMDD.xlsx -> YYYY_base_filename.xlsx
    base_name = config.base_filename
    new_file_name = f"{year}_{base_name}.xlsx"
    output_file = os.path.join(file_dir, new_file_name)
    
    print(f"Updated output file name: {output_file}")
    
    # 出力フォルダが存在しない場合は作成
    output_dir = os.path.dirname(output_file)
    if not os.path.exists(output_dir):
        print(f"Creating output directory: {output_dir}")
        os.makedirs(output_dir, exist_ok=True)
    
    # データのクリーニング
    clean_data = []
    for item in data:
        clean_item = {}
        for key, value in item.items():
            if key in ['Authors', 'Affiliations']:
                # 配列や文字列の整形
                clean_item[key] = clean_string_array(value)
            else:
                clean_item[key] = value
        clean_data.append(clean_item)
    
    # DataFrameに変換
    df = pd.DataFrame(clean_data)
    print(f"Created DataFrame with {len(df)} rows and {len(df.columns)} columns")
    print(f"DataFrame columns: {df.columns.tolist()}")
    
    # 列の順序を指定
    columns = config.COLUMNS + ["Source File"]
    
    # 指定の列が存在する場合のみ選択
    available_columns = [col for col in columns if col in df.columns]
    print(f"Available columns: {available_columns}")
    df = df[available_columns]
    
    # サンプルデータを表示
    if not df.empty:
        print("\nSample data (first 2 rows):")
        print(df.head(2).to_string())
    
    # ExcelWriterの作成
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        # シート名を年に設定して書き込み
        df.to_excel(writer, sheet_name=year, index=False)
    
    # ファイル存在確認
    if os.path.exists(output_file):
        file_size = os.path.getsize(output_file) / 1024  # KBに変換
        print(f"Excel file created successfully: {output_file} (Size: {file_size:.2f} KB)")
        print(f"Data written to sheet named '{year}'")
    else:
        print(f"ERROR: Failed to create Excel file at {output_file}")
    
    return output_file