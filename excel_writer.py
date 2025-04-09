import pandas as pd
import os
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
    """テキストから年を抽出する"""
    try:
        # まず、"As of" の後の年を探す
        as_of_pattern = r'As of\s+[A-Za-z]+\s+\d+,\s+(\d{4})'
        as_of_match = re.search(as_of_pattern, text)
        if as_of_match:
            return as_of_match.group(1)
        
        # 次に、ファイル内の最初の4桁の数字を探す
        year_pattern = r'\b(20\d{2})\b'
        year_match = re.search(year_pattern, text)
        if year_match:
            return year_match.group(1)
        
        return str(datetime.now().year)  # デフォルトは現在の年
    except Exception as e:
        print(f"Warning: 年の抽出中にエラー: {e}")
        return str(datetime.now().year)

def write_to_excel(data, output_file, text_content=None):
    """データをExcelファイルに書き込む"""
    try:
        # 出力ディレクトリの作成
        output_dir = os.path.join("output", "file")
        os.makedirs(output_dir, exist_ok=True)
        
        # 出力ファイルのパスを設定
        output_path = os.path.join(output_dir, output_file)
        
        # データフレームの作成
        df = pd.DataFrame(data)
        
        # 必要なカラムの順序を定義
        columns = [
            'no', 'session_name', 'session_code', 'overview',
            'paper_no', 'title', 'main_author_group', 'main_author_affiliation',
            'co_author_group', 'co_author_affiliation', 'organizers', 'chairperson'
        ]
        
        # 不足しているカラムを追加
        for col in columns:
            if col not in df.columns:
                df[col] = ''
        
        # カラムの順序を整える
        df = df[columns]
        
        # 連番を追加
        df['no'] = range(1, len(df) + 1)
        
        # Excelファイルに書き込み
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # データを書き込み
            df.to_excel(writer, sheet_name='Sessions', index=False)
            
            # テキストコンテンツがある場合は別シートに保存
            if text_content:
                text_df = pd.DataFrame({'text': [text_content]})
                text_df.to_excel(writer, sheet_name='Raw Text', index=False)
        
        print(f"Excelファイルに保存しました: {output_path}")
        print(f"書き込まれたレコード数: {len(df)}")
        return output_path, df
    except Exception as e:
        print(f"Error: Excelファイルの保存中にエラー: {e}")
        return None, None