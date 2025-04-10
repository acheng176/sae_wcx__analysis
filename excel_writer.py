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
            # 論文情報がない場合は、セッション自体を1行として扱う
            if not item.get('papers', []):
                row = {
                    'session_name': item.get('session_name', ''),
                    'session_code': item.get('session_code', ''),
                    'overview': item.get('overview', ''),
                    'category': item.get('category', 'Others'),  # カテゴリーが指定されていない場合は'Others'を使用
                    'subcategory': item.get('subcategory', 'Others'),  # サブカテゴリーが指定されていない場合は'Others'を使用
                    'paper_no': '',
                    'title': '',
                    'main_author_group': '',
                    'main_author_affiliation': '',
                    'co_author_group': '',
                    'co_author_affiliation': '',
                    'organizers': '; '.join(item.get('organizers', [])),
                    'chairperson': item.get('chairperson', '')
                }
                rows.append(row)
            else:
                for paper in item.get('papers', []):
                    main_author = paper.get('main_author', {})
                    co_authors = paper.get('co_authors', [])
                    
                    row = {
                        'session_name': item.get('session_name', ''),
                        'session_code': item.get('session_code', ''),
                        'overview': item.get('overview', ''),
                        'category': item.get('category', 'Others'),  # カテゴリーが指定されていない場合は'Others'を使用
                        'subcategory': item.get('subcategory', 'Others'),  # サブカテゴリーが指定されていない場合は'Others'を使用
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
        
        if not rows:
            print("Error: 有効なデータがありません")
            return None
        
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
        
        # カテゴリーを日本語に変換（必ず何らかの値が設定される）
        df['category'] = df['category'].map(category_mapping).fillna('その他')
        
        # サブカテゴリーを日本語に変換（該当なしの場合は「その他」）
        df['subcategory'] = df['subcategory'].map(subcategory_mapping).fillna('その他')
        
        # Excelファイルに書き込み
        df.to_excel(output_file, index=False)
        print(f"Excelファイルを出力しました: {output_file}")
        return output_file
        
    except Exception as e:
        print(f"Excelファイルの書き込み中にエラーが発生しました: {str(e)}")
        return None