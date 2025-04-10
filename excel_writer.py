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

def write_to_excel(data, year, output_dir="output"):
    """抽出したデータをExcelファイルに書き込む"""
    try:
        # 出力ディレクトリの作成
        os.makedirs(output_dir, exist_ok=True)
        
        # 出力ファイル名の生成（年を文字列に変換）
        output_file = os.path.join(output_dir, f"sae_wcx_{str(year)}.xlsx")
        
        # データの整形
        rows = []
        for item in data:
            for paper in item.get('papers', []):
                # 著者情報の処理
                authors = paper.get('authors', [])
                main_author = authors[0] if authors else {}
                co_authors = authors[1:] if len(authors) > 1 else []
                
                row = {
                    'session_name': item.get('session_name', ''),
                    'session_code': item.get('session_code', ''),
                    'overview': item.get('overview', ''),
                    'paper_no': paper.get('paper_no', ''),
                    'title': paper.get('title', ''),
                    'main_author_group': main_author.get('group', ''),
                    'main_author_affiliation': main_author.get('affiliation', ''),
                    'co_author_group': '; '.join(a.get('group', '') for a in co_authors),
                    'co_author_affiliation': '; '.join(a.get('affiliation', '') for a in co_authors),
                    'organizers': '; '.join(item.get('organizers', [])),
                    'chairperson': item.get('chairperson', ''),
                    'category': item.get('category', ''),
                    'subcategory': item.get('subcategory', '')
                }
                rows.append(row)
        
        # DataFrameの作成
        df = pd.DataFrame(rows)
        
        # 列の順序を指定
        columns = [
            'session_name',
            'session_code',
            'overview',
            'paper_no',
            'title',
            'main_author_group',
            'main_author_affiliation',
            'co_author_group',
            'co_author_affiliation',
            'organizers',
            'chairperson',
            'category',
            'subcategory'
        ]
        
        # 指定した列の順序でDataFrameを並び替え
        df = df[columns]
        
        # Excelファイルに書き込み
        df.to_excel(output_file, index=False)
        print(f"Excelファイルを出力しました: {output_file}")
        
    except Exception as e:
        print(f"Excelファイルの書き込み中にエラーが発生しました: {str(e)}")