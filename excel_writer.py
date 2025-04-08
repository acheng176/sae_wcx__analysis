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

def write_to_excel(data, output_file, source_text):
    """データをエクセルファイルに書き込む"""
    try:
        # データフレームの作成
        df = pd.DataFrame(data)
        
        # カラムの順序を定義
        columns = [
            'no',
            'session_name',
            'session_code',
            'paper_no',
            'title',
            'main_author_group',
            'main_author_affiliation',
            'co_author_group',
            'co_author_affiliation',
            'organizers',
            'chairperson',
            'sourcefile'
        ]
        
        # 必要なカラムが存在しない場合は追加
        for col in columns:
            if col not in df.columns:
                df[col] = ''
        
        # カラムの順序を設定
        df = df[columns]
        
        # データの整形
        df['no'] = range(1, len(df) + 1)
        df['sourcefile'] = os.path.basename(source_text)
        
        # エクセルファイルに書き込み
        df.to_excel(output_file, index=False, engine='openpyxl')
        
        print(f"\nエクセルファイルに書き込み完了: {output_file}")
        print(f"書き込まれたレコード数: {len(df)}")
        print(f"カラム一覧: {', '.join(df.columns)}")
        
        return output_file
        
    except Exception as e:
        print(f"Error: エクセルファイルへの書き込み中にエラー: {str(e)}")
        return None