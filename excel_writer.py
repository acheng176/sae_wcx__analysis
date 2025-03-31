import pandas as pd
import os
import config
import re

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

def write_to_excel(data, output_file):
    """抽出データをExcelに書き込む"""
    print(f"\nPreparing to write data to Excel: {output_file}")
    
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
    
    # Excelに書き込み
    print(f"Writing data to Excel file: {output_file}")
    df.to_excel(output_file, index=False)
    
    # ファイル存在確認
    if os.path.exists(output_file):
        file_size = os.path.getsize(output_file) / 1024  # KBに変換
        print(f"Excel file created successfully: {output_file} (Size: {file_size:.2f} KB)")
    else:
        print(f"ERROR: Failed to create Excel file at {output_file}")
    
    return output_file