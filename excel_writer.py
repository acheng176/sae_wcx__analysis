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

def write_to_excel(data, year, output_dir=r"output\file"):
    """抽出したデータをExcelファイルに書き込む"""
    try:
        # デバッグ情報の出力
        print(f"現在の作業ディレクトリ: {os.getcwd()}")
        print(f"指定された出力ディレクトリ: {output_dir}")
        
        # 出力ディレクトリの作成（パスを正規化）
        output_dir = os.path.normpath(output_dir)
        print(f"正規化後の出力ディレクトリ: {output_dir}")
        
        # ディレクトリの存在確認
        if not os.path.exists(output_dir):
            print(f"ディレクトリが存在しないため作成します: {output_dir}")
            os.makedirs(output_dir, exist_ok=True)
            print(f"ディレクトリ作成後の状態: {os.path.exists(output_dir)}")
        
        # 出力ファイル名の生成（年を文字列に変換）
        output_file = os.path.join(output_dir, f"sae_wcx_{str(year)}.xlsx")
        print(f"出力ファイルの完全パス: {output_file}")
        
        # データの整形
        rows = []
        for item in data:
            # 各アイテムを直接行として追加
            row = {
                'session_name': item.get('session_name', ''),
                'session_code': item.get('session_code', ''),
                'overview': item.get('overview', ''),
                'category': item.get('category', 'Others'),
                'subcategory': item.get('subcategory', 'Others'),
                'paper_no': item.get('paper_no', ''),
                'title': item.get('title', ''),
                'main_author_group': clean_string_array(item.get('main_author_group', '')),
                'main_author_affiliation': clean_string_array(item.get('main_author_affiliation', '')),
                'co_author_group': clean_string_array(item.get('co_author_group', '')),
                'co_author_affiliation': clean_string_array(item.get('co_author_affiliation', '')),
                'organizers': clean_string_array(item.get('organizers', '')),
                'chairperson': clean_string_array(item.get('chairperson', ''))
            }
            rows.append(row)
            
            # デバッグ出力
            print("\n--- データ変換結果 ---")
            print(f"Session: {row['session_name']} ({row['session_code']})")
            print(f"Paper: {row['paper_no']}")
            print(f"Authors: {row['main_author_group']} ({row['main_author_affiliation']})")
            print(f"Co-Authors: {row['co_author_group']} ({row['co_author_affiliation']})")
            print("--------------------")
        
        if not rows:
            print("Error: 有効なデータがありません")
            return None, None
        
        # DataFrameを作成
        df = pd.DataFrame(rows)
        
        # 連番を追加（1から始まる）
        df.insert(0, 'no', range(1, len(df) + 1))
        
        # 列の順序を指定
        column_order = [
            'no',
            'session_name',
            'session_code',
            'overview',
            'category',
            'subcategory',
            'paper_no',
            'title',
            'main_author_group',
            'main_author_affiliation',
            'co_author_group',
            'co_author_affiliation',
            'organizers',
            'chairperson'
        ]
        
        # 列の順序を変更
        df = df[column_order]
        
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
        
        # Excelファイルに保存
        df.to_excel(output_file, index=False)
        print(f"\nExcelファイルを保存しました: {output_file}")
        
        return output_file, df
        
    except Exception as e:
        print(f"Error: Excelファイルの作成中にエラー: {e}")
        return None, None