from db_handler import DatabaseHandler
import pandas as pd
import sqlite3
from datetime import datetime
import os

# カテゴリの日本語マッピング
CATEGORY_MAPPING = {
    'Internal Combustion Engine': '内燃機関技術',
    'ADAS/AVS': 'ADAS/AVS',
    'Electrification': '電動化技術',
    'Emissions Control': '排出ガス制御',
    'Vehicle Development': '車両開発',
    'Powertrain': 'パワートレイン',
    'Materials': '材料技術',
    'Crash Safety': '衝突安全',
    'Vehicle Dynamics': '車両ダイナミクス',
    'NVH': 'NVH',
    'Reliability/Durability': '信頼性/耐久性',
    'Manufacturing': '製造技術',
    'Body Engineering': '車体技術',
    'Electronics': '電装技術',
    'Human Factors': 'ヒューマンファクター',
    'Racing Technology': 'レース技術',
    'Others': 'その他'
}

# サブカテゴリの日本語マッピング
SUBCATEGORY_MAPPING = {
    'Environmental Technology': '環境技術',
    'AI/Machine Learning': 'AI/機械学習',
    'Cybersecurity': 'サイバーセキュリティ',
    'IoT': 'IoT',
    'HVAC': '空調システム',
    'Alternative Fuels': '代替燃料',
    'Battery Technology': 'バッテリー技術',
    'Connectivity': 'コネクティビティ',
    'Cooling Systems': '冷却システム',
    'Lubrication': '潤滑',
    'Software Defined Vehicle': 'ソフトウェア定義車両',
    'Recycling': 'リサイクル',
    'Hydrogen Technology': '水素技術',
    'Ammonia Technology': 'アンモニア技術',
    'Human Factors': 'ヒューマンファクター',
    'Reliability/Durability': '信頼性/耐久性',
    'Racing Technology': 'レース技術',
    'Emissions Control': '排出ガス制御',
    'Manufacturing': '製造技術',
    'Materials': '材料技術',
    'Body Engineering': '車体工学',
    'NVH': 'NVH',
    'Others': 'その他'
}

def extract_oem(row):
    """著者の所属から自動車メーカーを抽出"""
    # まずmain author affiliationのみで判定
    main_affiliation = str(row['main_author_affiliation']).upper()
    co_affiliation = str(row['co_author_affiliation']).upper()
    
    # メーカー判定関数
    def check_maker(affiliation):
        # 日本メーカー
        if 'TOYOTA' in affiliation or 'DAIHATSU' in affiliation or 'LEXUS' in affiliation:
            return 'Toyota'
        elif 'HONDA' in affiliation:
            return 'Honda'
        elif 'NISSAN' in affiliation or 'INFINITI' in affiliation:
            return 'Nissan'
        elif 'MAZDA' in affiliation:
            return 'Mazda'
        elif 'SUBARU' in affiliation or 'FUJI HEAVY' in affiliation:
            return 'Subaru'
        elif 'MITSUBISHI' in affiliation or 'MITSUBISHI MOTORS' in affiliation:
            return 'Mitsubishi'
        elif 'SUZUKI' in affiliation:
            return 'Suzuki'
        elif 'ISUZU' in affiliation:
            return 'Isuzu'
        elif 'DAIHATSU' in affiliation:
            return 'Daihatsu'
        
        # アメリカメーカー
        elif 'FORD' in affiliation:
            return 'Ford'
        elif 'GENERAL MOTORS' in affiliation or 'GM ' in affiliation or 'CHEVROLET' in affiliation or 'CADILLAC' in affiliation or 'BUICK' in affiliation:
            return 'GM'
        elif 'STELLANTIS' in affiliation or 'CHRYSLER' in affiliation or 'FCA' in affiliation or 'JEEP' in affiliation or 'DODGE' in affiliation or 'RAM' in affiliation:
            return 'Stellantis'
        elif 'TESLA' in affiliation:
            return 'Tesla'
        
        # 韓国メーカー
        elif 'HYUNDAI' in affiliation or 'KIA' in affiliation:
            return 'Hyundai'
        
        # ドイツメーカー
        elif 'VOLKSWAGEN' in affiliation or 'VW ' in affiliation or 'AUDI' in affiliation or 'PORSCHE' in affiliation or 'BENTLEY' in affiliation or 'LAMBORGHINI' in affiliation:
            return 'Volkswagen'
        elif 'BMW' in affiliation or 'MINI' in affiliation or 'ROLLS-ROYCE' in affiliation:
            return 'BMW'
        elif 'MERCEDES' in affiliation or 'MERCEDES-BENZ' in affiliation or 'DAIMLER' in affiliation:
            return 'Mercedes-Benz'
        
        # フランスメーカー
        elif 'RENAULT' in affiliation:
            return 'Renault'
        elif 'PEUGEOT' in affiliation or 'CITROEN' in affiliation:
            return 'PSA'
        
        # イタリアメーカー
        elif 'FIAT' in affiliation:
            return 'Fiat'
        
        # スウェーデンメーカー
        elif 'VOLVO' in affiliation:
            return 'Volvo'
        
        # 中国メーカー
        elif 'BYD' in affiliation:
            return 'BYD'
        elif 'GEELY' in affiliation:
            return 'Geely'
        elif 'SAIC' in affiliation:
            return 'SAIC'
        elif 'CHANGAN' in affiliation:
            return 'Changan'
        elif 'GREAT WALL' in affiliation:
            return 'Great Wall'
        elif 'DONGFENG' in affiliation:
            return 'Dongfeng'
        elif 'FAW' in affiliation:
            return 'FAW'
        
        return ''
    
    # まずmain authorのaffiliationで判定
    main_maker = check_maker(main_affiliation)
    if main_maker:
        return main_maker
    
    # main authorに自動車メーカーが含まれていない場合のみ、co-authorを確認
    return check_maker(co_affiliation)

def export_to_excel():
    """データベースの内容をExcelファイルとしてエクスポート"""
    try:
        # データベースに接続
        db = DatabaseHandler()
        with sqlite3.connect(db.db_path) as conn:
            # メインのクエリを実行してデータを取得
            query = """
                SELECT 
                    no,
                    year,
                    category,
                    subcategory,
                    session_name,
                    session_code,
                    overview,
                    paper_no,
                    title,
                    main_author_group,
                    main_author_affiliation,
                    co_author_group,
                    co_author_affiliation,
                    organizers,
                    chairperson
                FROM sessions
                ORDER BY year DESC, category, subcategory
            """
            
            # pandasのDataFrameとしてデータを読み込み
            df = pd.read_sql_query(query, conn)
            
            # 自動車メーカーを抽出
            df['oem'] = df.apply(extract_oem, axis=1)
            
            # 著者情報を結合
            df['authors'] = df.apply(lambda x: 
                f"{x['main_author_group']} ({x['main_author_affiliation']})" if x['main_author_group'] else "" +
                (f", {x['co_author_group']} ({x['co_author_affiliation']})" if x['co_author_group'] else ""), 
                axis=1
            )
            
            # 列の順序を設定
            df = df[[
                'no', 'year', 'category', 'subcategory', 
                'session_name', 'session_code', 'paper_no', 'title',
                'authors', 'main_author_group', 'main_author_affiliation',
                'co_author_group', 'co_author_affiliation', 'oem',
                'overview', 'organizers', 'chairperson'
            ]]
            
            # 列名を設定
            df.columns = [
                'No', 'Year', 'Category', 'Subcategory',
                'Session Name', 'Session Code', 'Paper No', 'Title',
                'Authors', 'Main Author Group', 'Main Author Affiliation',
                'Co-Author Group', 'Co-Author Affiliation', 'OEM',
                'Overview', 'Organizers', 'Chairperson'
            ]
            
            # 出力ディレクトリの作成
            output_dir = "output/excel"
            os.makedirs(output_dir, exist_ok=True)
            
            # 現在の日時を取得
            current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # 出力ファイル名の生成
            output_file = f"{output_dir}/wcx_sessions_{current_time}.xlsx"
            
            # Excelファイルとして保存
            with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='WCX Sessions', index=False)
                
                # ワークシートを取得
                worksheet = writer.sheets['WCX Sessions']
                
                # カラム幅の自動調整
                for column in worksheet.columns:
                    max_length = 0
                    column = [cell for cell in column]
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = (max_length + 2)
                    adjusted_width = min(adjusted_width, 100)  # 最大幅を100文字に制限
                    worksheet.column_dimensions[column[0].column_letter].width = adjusted_width
            
            print(f"Excelファイルを出力しました: {output_file}")
            return True
            
    except Exception as e:
        print(f"Error: Excelファイルの出力中にエラーが発生: {str(e)}")
        return False

if __name__ == "__main__":
    export_to_excel() 