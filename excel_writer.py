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
                    'category': item.get('category', ''),
                    'subcategory': item.get('subcategory', ''),
                    'paper_no': paper.get('paper_no', ''),
                    'title': paper.get('title', ''),
                    'main_author_group': main_author.get('group', ''),
                    'main_author_affiliation': main_author.get('affiliation', ''),
                    'co_author_group': '; '.join(a.get('group', '') for a in co_authors),
                    'co_author_affiliation': '; '.join(a.get('affiliation', '') for a in co_authors),
                    'organizers': '; '.join(item.get('organizers', [])),
                    'chairperson': item.get('chairperson', '')
                }
                rows.append(row)
        
        # DataFrameの作成
        df = pd.DataFrame(rows)
        
        # カテゴリーとサブカテゴリーの日本語マッピング
        category_mapping = {
            "Vehicle Dynamics": "車両ダイナミクス",
            "Powertrain": "パワートレイン",
            "Safety": "安全性",
            "Materials": "材料",
            "Manufacturing": "製造",
            "Electrification": "電動化",
            "Autonomous": "自動運転",
            "Connectivity": "コネクティビティ",
            "Simulation": "シミュレーション",
            "Testing": "テスト",
            "Regulation": "規制",
            "Business": "ビジネス",
            "Others": "その他"
        }
        
        subcategory_mapping = {
            "Suspension": "サスペンション",
            "Braking": "ブレーキ",
            "Steering": "ステアリング",
            "Tire": "タイヤ",
            "Engine": "エンジン",
            "Transmission": "トランスミッション",
            "Hybrid": "ハイブリッド",
            "Battery": "バッテリー",
            "Crash": "衝突",
            "Pedestrian": "歩行者",
            "Active Safety": "アクティブセーフティ",
            "Passive Safety": "パッシブセーフティ",
            "Steel": "鋼材",
            "Aluminum": "アルミニウム",
            "Composites": "複合材料",
            "Plastics": "プラスチック",
            "Assembly": "組立",
            "Welding": "溶接",
            "Machining": "加工",
            "Quality": "品質",
            "Battery Management": "バッテリー管理",
            "Motor Control": "モーター制御",
            "Charging": "充電",
            "Perception": "認識",
            "Planning": "計画",
            "Control": "制御",
            "V2X": "V2X",
            "Infotainment": "インフォテインメント",
            "Telematics": "テレマティクス",
            "CAE": "CAE",
            "CFD": "CFD",
            "FEA": "FEA",
            "Durability": "耐久性",
            "NVH": "NVH",
            "Emissions": "排出",
            "Fuel Economy": "燃費",
            "Market": "市場",
            "Strategy": "戦略",
            "Others": "その他"
        }
        
        # カテゴリーとサブカテゴリーを日本語に変換
        df['category'] = df['category'].map(category_mapping).fillna('その他')
        df['subcategory'] = df['subcategory'].map(subcategory_mapping).fillna('その他')
        
        # 列の順序を指定
        columns = [
            'session_name', 'session_code', 'overview',
            'category', 'subcategory', 'paper_no', 'title',
            'main_author_group', 'main_author_affiliation',
            'co_author_group', 'co_author_affiliation',
            'organizers', 'chairperson'
        ]
        
        # カラム名を日本語に変換
        column_names = {
            'session_name': 'セッション名',
            'session_code': 'セッションコード',
            'overview': '概要',
            'category': 'カテゴリー',
            'subcategory': 'サブカテゴリー',
            'paper_no': '論文番号',
            'title': 'タイトル',
            'main_author_group': '筆頭著者グループ',
            'main_author_affiliation': '筆頭著者所属',
            'co_author_group': '共著者グループ',
            'co_author_affiliation': '共著者所属',
            'organizers': 'オーガナイザー',
            'chairperson': '議長'
        }
        
        # 指定した列の順序でDataFrameを並び替え
        df = df[columns].rename(columns=column_names)
        
        # Excelファイルに書き込み
        df.to_excel(output_file, index=False)
        print(f"Excelファイルを出力しました: {output_file}")
        return output_file
        
    except Exception as e:
        print(f"Excelファイルの書き込み中にエラーが発生しました: {str(e)}")
        return None