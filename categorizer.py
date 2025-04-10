import openai
import os
import json
from dotenv import load_dotenv

def setup_azure_openai():
    """Azure OpenAI APIの設定"""
    load_dotenv()
    openai.api_type = "azure"
    openai.api_base = os.getenv("AZURE_OPENAI_ENDPOINT")
    openai.api_version = os.getenv("AZURE_OPENAI_API_VERSION")
    openai.api_key = os.getenv("AZURE_OPENAI_API_KEY")
    openai.deployment_id = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")

def get_categorization_prompt(overview, title):
    """カテゴリ分類用のプロンプトを生成"""
    return f"""
以下のセッション情報を分析し、最も適切なカテゴリとサブカテゴリを決定してください。

タイトル: {title}
概要: {overview}

カテゴリの選択肢:
- Internal Combustion Engine: 内燃機関、エンジン、燃焼、シリンダー、ピストンに関する技術
- ADAS/AVS: 自動運転、運転支援、ADAS、AVS、センサー、認識技術
- Electrification: 電動化、モーター、バッテリー、EV、HEV、PHEV
- Emissions Control: 排気、触媒、排出ガス、環境規制
- Vehicle Development: 車両開発、設計、テスト、評価
- Powertrain: パワートレイン、トランスミッション、駆動系
- Materials: 材料、複合材料、金属、樹脂
- Crash Safety: 衝突安全、クラッシュ、安全性能
- Vehicle Dynamics: 車両ダイナミクス、操縦性、安定性
- NVH: 騒音、振動、ハーシュネス
- Reliability/Durability: 信頼性、耐久性、テスト
- Manufacturing: 製造、生産、組立
- Body Engineering: 車体、構造、空力
- Electronics: 電装、センサー、ECU
- Human Factors: HMI、人間工学、インターフェース
- Racing Technology: レース、モータースポーツ

サブカテゴリの選択肢:
- Environmental Technology: 環境技術、サステナビリティ
- AI/Machine Learning: AI、機械学習、深層学習
- Cybersecurity: サイバーセキュリティ、セキュリティ
- IoT: IoT、コネクテッド、接続性
- HVAC: HVAC、空調、暖房
- Alternative Fuels: 代替燃料、バイオ燃料
- Battery Technology: バッテリー、エネルギー貯蔵
- Connectivity: コネクティビティ、V2X、通信
- Cooling Systems: 冷却、温度管理
- Lubrication: 潤滑、トライボロジー
- Software Defined Vehicle: ソフトウェア、OTA
- Recycling: リサイクル、再利用
- Hydrogen Technology: 水素、燃料電池
- Ammonia Technology: アンモニア

以下のJSON形式で回答してください：
{{
    "category": "最も適切なカテゴリ",
    "subcategory": "最も適切なサブカテゴリ（該当なしの場合は空文字列）",
    "confidence": "分類の確信度（0-1）",
    "explanation": "分類の理由の簡単な説明"
}}
"""

def categorize_session(overview, title):
    """セッションのカテゴリとサブカテゴリを決定する"""
    try:
        print(f"\nカテゴリ分類開始:")
        print(f"タイトル: {title}")
        print(f"概要: {overview}")

        if not overview and not title:
            print("警告: 概要とタイトルが両方とも空です")
            return "Others", ""

        try:
            # Azure OpenAIの設定
            setup_azure_openai()

            # プロンプトの生成
            prompt = get_categorization_prompt(overview, title)

            # Azure OpenAI APIの呼び出し
            response = openai.ChatCompletion.create(
                deployment_id=openai.deployment_id,
                messages=[
                    {"role": "system", "content": "あなたは自動車技術の専門家です。セッションの内容を分析し、適切なカテゴリとサブカテゴリを決定してください。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )

            # レスポンスの解析
            result = json.loads(response.choices[0].message.content)
            
            print(f"分類結果: {result['category']} - {result['subcategory']}")
            print(f"確信度: {result['confidence']}")
            print(f"説明: {result['explanation']}")

            return result['category'], result['subcategory']

        except Exception as api_error:
            print(f"警告: API呼び出し中にエラーが発生しました: {str(api_error)}")
            print("キーワードベースの分類にフォールバックします")
            
            # キーワードベースの分類にフォールバック
            text = f"{title} {overview}".lower()
            
            # カテゴリのキーワードマッピング
            category_keywords = {
                "Internal Combustion Engine": ["engine", "combustion", "cylinder", "piston", "内燃機関"],
                "ADAS/AVS": ["adas", "autonomous", "self-driving", "driver assistance", "自動運転"],
                "Electrification": ["electric", "battery", "motor", "電動", "モーター"],
                "Emissions Control": ["emission", "exhaust", "catalyst", "排気", "触媒"],
                "Vehicle Development": ["vehicle", "development", "design", "車両", "開発"],
                "Powertrain": ["powertrain", "transmission", "driveline", "駆動", "トランスミッション"],
                "Materials": ["material", "composite", "metallurgy", "材料", "複合材料"],
                "Crash Safety": ["crash", "safety", "impact", "衝突", "安全"],
                "Vehicle Dynamics": ["dynamics", "handling", "stability", "ダイナミクス", "操縦性"],
                "NVH": ["noise", "vibration", "harshness", "騒音", "振動"],
                "Reliability/Durability": ["reliability", "durability", "testing", "信頼性", "耐久性"],
                "Manufacturing": ["manufacturing", "production", "assembly", "製造", "生産"],
                "Body Engineering": ["body", "structure", "aerodynamics", "車体", "空力"],
                "Electronics": ["electronics", "sensor", "ecu", "電装", "センサー"],
                "Human Factors": ["hmi", "ergonomics", "interface", "人間工学", "インターフェース"],
                "Racing Technology": ["racing", "motorsports", "レース", "モータースポーツ"]
            }
            
            # キーワードに基づいてカテゴリを決定
            for category, keywords in category_keywords.items():
                if any(keyword in text for keyword in keywords):
                    return category, ""
            
            return "Others", ""

    except Exception as e:
        print(f"警告: カテゴリ分類中にエラーが発生しました: {str(e)}")
        return "Others", ""

def add_categories_to_data(data):
    """データセット全体にカテゴリー情報を追加する"""
    for item in data:
        category, subcategory = categorize_session(
            item.get('overview', ''),
            item.get('title', '')
        )
        item['category'] = category
        item['subcategory'] = subcategory
    return data

def write_to_excel(data, year, output_dir="output"):
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

    # ここでExcelファイルへの書き込み処理を行う
    # 例: pandasを使用してExcelファイルに書き込む
    # import pandas as pd
    # df = pd.DataFrame(rows)
    # df.to_excel(output_file, index=False)

    # この関数の実装は、実際のファイル書き込み処理に依存します。
    # ここでは単にデータを表示するだけにします。
    print("以下のデータをExcelに書き込みます:")
    for row in rows:
        print(row) 