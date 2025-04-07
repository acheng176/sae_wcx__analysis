import os
import json
import openai
from dotenv import load_dotenv
import re
import textwrap
from datetime import datetime
import time  # timeモジュールを追加

def split_text(text, max_chars=4000):
    """テキストをセッションごとに分割し、Overviewの継続性を保持する"""
    try:
        # セッションの開始パターンで分割
        session_pattern = r'(?:Session Code\s+[A-Z0-9]+|Room \d+[A-Z]*\s+Session)'
        sessions = re.split(f'({session_pattern})', text)
        
        # セッションごとのデータを管理
        session_data = {}  # {session_code: {'overview': str, 'text_parts': [str]}}
        current_session_code = None
        current_text = ""
        
        for i, part in enumerate(sessions):
            if re.match(session_pattern, part):
                # 新しいセッションの開始を検出
                code_match = re.search(r'Session Code\s+([A-Z0-9]+)', part)
                if code_match:
                    current_session_code = code_match.group(1)
                    if current_session_code not in session_data:
                        session_data[current_session_code] = {
                            'overview': None,
                            'text_parts': []
                        }
                    current_text = part
            else:
                if current_session_code and part.strip():
                    current_text += part
                    
                    # Overviewを探す
                    if not session_data[current_session_code]['overview']:
                        # Overview抽出パターンを改善
                        overview_patterns = [
                            # パターン1: Room行の後からTimeまでの文章
                            r'(?:Room \d+[A-Z]*.*?\n)(.*?)(?=(?:Time|Organizers|\d{1,2}:\d{2}|$))',
                            # パターン2: This sessionで始まる文章
                            r'(?:This session.*?)(?=(?:Time|Organizers|\d{1,2}:\d{2}|$))',
                            # パターン3: セッション名の後の説明文
                            r'(?:Session\s+\d{1,2}:\d{2}\s*(?:a\.m\.|p\.m\.).*?\n)(.*?)(?=(?:Time|Organizers|\d{1,2}:\d{2}|$))'
                        ]
                        
                        for pattern in overview_patterns:
                            overview_match = re.search(pattern, part, re.DOTALL)
                            if overview_match:
                                overview_text = overview_match.group(1) if len(overview_match.groups()) > 0 else overview_match.group(0)
                                overview_text = overview_text.strip()
                                if overview_text and len(overview_text) > 10:  # 最小長さチェック
                                    session_data[current_session_code]['overview'] = overview_text
                                    break
                    
                    # テキストが最大サイズを超えた場合、分割して保存
                    if len(current_text) > max_chars:
                        session_data[current_session_code]['text_parts'].append(current_text)
                        current_text = ""
        
        # 最後のテキストを保存
        if current_text and current_session_code:
            session_data[current_session_code]['text_parts'].append(current_text)
        
        # セッション情報を含むチャンクを生成
        enhanced_chunks = []
        for session_code, data in session_data.items():
            for text_part in data['text_parts']:
                session_info = {
                    'session_code': session_code,
                    'overview': data['overview']
                }
                enhanced_chunk = f"SESSION_INFO: {json.dumps(session_info)}\n{text_part}"
                enhanced_chunks.append(enhanced_chunk)
        
        # デバッグ情報
        print(f"\nテキストを {len(enhanced_chunks)} チャンクに分割しました")
        for session_code, data in session_data.items():
            print(f"\nセッション {session_code}:")
            print(f"Overview: {data['overview'][:100]}..." if data['overview'] else "Overview: Not found")
            print(f"テキストパート数: {len(data['text_parts'])}")
        
        return enhanced_chunks
    
    except Exception as e:
        print(f"Error: テキスト分割中にエラー: {str(e)}")
        return [text]

def setup_azure_openai():
    """Azure OpenAI APIの設定を行う"""
    load_dotenv()
    openai.api_type = "azure"
    openai.api_base = os.getenv("AZURE_OPENAI_ENDPOINT")
    openai.api_version = os.getenv("AZURE_OPENAI_API_VERSION")
    openai.api_key = os.getenv("AZURE_OPENAI_API_KEY")

def chunk_text(text, max_chunk_size=6000):
    """テキストを意味のある単位で分割する"""
    if not text:
        return []
    
    try:
        chunks = []
        # セッションの区切りとなるマーカー
        session_markers = ["Room ", "Session Code", "Part 1 of", "Part 2 of", "Part 3 of"]
        
        start = 0
        while start < len(text):
            # 理想的なチャンクサイズの範囲を設定
            chunk_end = min(start + max_chunk_size, len(text))
            search_start = min(start + max_chunk_size // 2, len(text) - 1)
            
            # 最適な分割位置を探す
            best_pos = -1
            for marker in session_markers:
                try:
                    pos = text.find(marker, search_start, min(search_start + max_chunk_size, len(text)))
                    if pos > 0 and (best_pos == -1 or pos < best_pos):
                        best_pos = pos
                except Exception as e:
                    print(f"Warning: マーカー '{marker}' の検索中にエラー: {e}")
                    continue
            
            if best_pos > 0:
                chunk_end = best_pos
            
            # 最小サイズのチェック
            if chunk_end - start < 100:
                chunk_end = min(start + max_chunk_size, len(text))
            
            current_chunk = text[start:chunk_end].strip()
            if current_chunk:  # 空のチャンクを除外
                chunks.append(current_chunk)
            
            start = chunk_end
            print(f"Progress: チャンク {len(chunks)} 作成完了 ({chunk_end}/{len(text)} 文字処理済み)")
        
        return chunks
        
    except Exception as e:
        print(f"Error: テキスト分割中にエラー発生: {e}")
        return [text]  # エラー時は元のテキストを1つのチャンクとして返す
    
def clean_json_response(content):
    """APIレスポンスのJSONをクリーンアップする（より強化版）"""
    try:
        # Markdown装飾を削除
        content = re.sub(r'```json\s*|\s*```', '', content)
        content = content.strip()
        
        # 制御文字を削除（改行、タブ、復帰以外の制御文字）
        # 0x00-0x08: NULL～BS、0x0B: VT、0x0C: FF、0x0E-0x1F: SO～US の制御文字を削除
        content = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F]+', '', content)
        
        # エスケープされた引用符を一時的に通常の引用符に変換
        content = content.replace('\\"', '"')
        
        # 二重バックスラッシュを一時マーカーに変換
        content = content.replace('\\\\', '\\TEMP_BACKSLASH\\')
        
        # 不要なエスケープを削除 (例: \H → H)
        content = re.sub(r'\\([^"\\])', r'\1', content)
        
        # 一時マーカーを二重バックスラッシュに戻す
        content = content.replace('\\TEMP_BACKSLASH\\', '\\\\')
        
        # JSON形式を確認（単一オブジェクトの場合は配列に変換）
        if content.startswith('{') and content.endswith('}'):
            print("単一オブジェクトを配列に変換します")
            content = f"[{content}]"
        
        # 配列形式の確認
        if not (content.startswith('[') and content.endswith(']')):
            print("Warning: 無効なJSON形式（配列ではない）")
            content = f"[{content}]"  # 配列でない場合は配列に変換
        
        # JSONの検証
        try:
            json.loads(content)
            print("JSON検証: 成功")
        except json.JSONDecodeError as e:
            print(f"JSON検証: 失敗 - {str(e)}")
            print("デフォルトJSONを返します")
            return '[{"Session_Name":"Unknown","Session_Code":"Unknown","Paper_No":"Unknown"}]'
        
        return content
    except Exception as e:
        print(f"Error: JSONクリーンアップ中にエラー: {str(e)}")
        return '[{"Session_Name":"Unknown","Session_Code":"Unknown","Paper_No":"Unknown"}]'
    

def fix_json_errors(content):
    """JSONデータの一般的なエラーを修正する試み"""
    try:
        # 異常な制御文字をさらに削除
        content = re.sub(r'[\x00-\x1F]+', ' ', content)
        
        # エスケープの問題を修正
        content = content.replace('\\"', '"')  # 誤ってエスケープされた引用符を修正
        content = re.sub(r'([^\\])\\([^"\\bfnrtu])', r'\1\2', content)  # 無効なエスケープを削除

        # 引用符のエスケープを適切に行う
        content = re.sub(r'([^\\])"([^"]*)"', r'\1\\"\2\\"', content)
        content = content.replace('\\\\', '\\')  # 二重バックスラッシュを修正
        
        # 壊れた引用符を修正
        content = re.sub(r'([{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', content)
        
        # 値の引用符の問題を修正
        content = re.sub(r':\s*([a-zA-Z][a-zA-Z0-9_]*)\s*(,|})', r': "\1"\2', content)
        
        # 引用符で囲まれていないnull、true、falseは修正しない
        content = re.sub(r':\s*null\s*(,|})', r': null\1', content)
        content = re.sub(r':\s*true\s*(,|})', r': true\1', content)
        content = re.sub(r':\s*false\s*(,|})', r': false\1', content)
        
        # 構文エラーが発生しそうな箇所を特定して修正
        lines = content.split('\n')
        for i in range(len(lines)):
            # 行末の不完全な引用符を修正
            if lines[i].count('"') % 2 == 1:
                if i < len(lines) - 1:
                    # 次の行の先頭に引用符を追加
                    lines[i+1] = '"' + lines[i+1]
                else:
                    # 最終行の場合は行末に引用符を追加
                    lines[i] = lines[i] + '"'
        
        content = '\n'.join(lines)
        
        # 最後のJSONオブジェクトの閉じ括弧が欠けている場合の修正
        if content.count('{') > content.count('}'):
            content = content + '}'
        
        # 配列の閉じ括弧が欠けている場合の修正
        if content.count('[') > content.count(']'):
            content = content + ']'
        
        # 複雑なオブジェクトの場合、より単純なオブジェクトを抽出
        try:
            json.loads(content)
        except json.JSONDecodeError:
            # シンプルな手法: 単一オブジェクトを抽出
            if content.strip().startswith('[{') and '}]' in content:
                first_obj_end = content.find('}', content.find('{')) + 1
                if first_obj_end > 0:
                    simple_obj = content[:first_obj_end].replace('[{', '{') + '}'
                    try:
                        json.loads(simple_obj)
                        print("単一オブジェクトを抽出しました")
                        return f"[{simple_obj}]"
                    except:
                        pass
        
        print("JSONエラーの修正を試みました")
        return content
    except Exception as e:
        print(f"JSONエラー修正中に例外が発生: {e}")
        return content

def extract_single_paper(chunk_text):
    """単一の論文情報からデータを抽出する"""
    try:
        # セッション情報の抽出
        session_info = None
        if chunk_text.startswith("SESSION_INFO: "):
            session_info_end = chunk_text.find("\n")
            if session_info_end > 0:
                session_info_json = chunk_text[13:session_info_end]
                try:
                    session_info = json.loads(session_info_json)
                    chunk_text = chunk_text[session_info_end + 1:]
                except:
                    print("Warning: セッション情報のJSONパースに失敗")
        
        # セッション情報からOverviewを取得
        overview = None
        if session_info and session_info.get('overview'):
            overview = session_info['overview']
        else:
            # 現在のテキストからOverviewを探す
            overview_patterns = [
                r'(?:Room \d+[A-Z]*.*?\n)(.*?)(?=(?:Time|Organizers|\d{1,2}:\d{2}|$))',
                r'(?:This session.*?)(?=(?:Time|Organizers|\d{1,2}:\d{2}|$))',
                r'(?:Session\s+\d{1,2}:\d{2}\s*(?:a\.m\.|p\.m\.).*?\n)(.*?)(?=(?:Time|Organizers|\d{1,2}:\d{2}|$))'
            ]
            for pattern in overview_patterns:
                overview_match = re.search(pattern, chunk_text, re.DOTALL)
                if overview_match:
                    overview = overview_match.group(1).strip() if len(overview_match.groups()) > 0 else overview_match.group(0).strip()
                    if overview and len(overview) > 10:
                        break
        
        prompt = f"""
Extract information from the technical session text below following these precise rules:

Overview Extraction Rules:
1. Use this overview if provided: {overview if overview else 'Not provided'}
2. If no overview is provided above, try to find it in the text
3. Overview should be a complete sentence or paragraph describing the session
4. If no overview is found, use "No data"

1. Session Information:
   - Session_Name: Extract the line ABOVE "Session Code" (e.g., "Systems Engineering for Automotive - Part 1 of 2")
     * For Panel Discussion sessions, include the entire "Panel Discussion: [Title]" text
   - Session_Code: Extract ONLY the code that appears immediately after "Session Code" (e.g., "SS111"). Ignore any session codes mentioned elsewhere in the text
   - Overview: Extract the ENTIRE paragraph that appears below the "Room" line and before "Organizers" or "Time" (e.g., "A Systems Engineering approach recognizes...")

2. Special Handling for Panel Discussions:
   - If the session name starts with "Panel Discussion:" or "パネルディスカッション":
     * Extract Session_Name, Session_Code, Overview normally
     * Set ALL other fields (Paper_No, Title, Main_Author_Group, Main_Author_Affiliation, Co_Author_Group, Co_Author_Affiliation) to exactly "panel discussion"
     * Extract ONLY the text after "Organizers -" for the Organizers field
     * IGNORE Moderators and Panelists information
   
   Example Panel Discussion format:
   Panel Discussion: Hydrogen Fuel Utilisation, Challenges and Opportunities
   Session Code     PFL399
   Room 141                                          Session        1:30 p.m.
   [Overview text...]
   Organizers -     Richard Butcher, BP Castrol; Timothy Newcomb, Lubrizol Corp.; Derek Splitter, Oak Ridge National Laboratory
   Moderators -     [IGNORE THIS]
   Panelists -      [IGNORE THIS]

3. Regular Paper Information (for non-panel sessions):
   - Paper_No and Title appear in a table format with these patterns:
     Example 1:
     Time        Paper No.        Title
     1:30 p.m.   2024-01-2501    Scenario-Based Development and Meta-Level Design for Automotive Systems: An Explanatory Study
     
     Example 2:
     Time        Paper No.        Title
     2:00 p.m.   ORAL ONLY       Front Zone Control Unit for Propulsion and Chassis Domains in a Zonal E/E Architecture
   
   - Paper_No: Extract either:
     * The numeric code in format "20XX-XX-XXXX"
     * The text "ORAL ONLY"
   - Title: Extract the complete text that appears on the same line after Paper_No

4. Author Information (for non-panel sessions):
   - Main_Author_Group: Extract all names that:
     * Appear in the first line below the Title
     * End with a comma
     * Come BEFORE the first semicolon or paragraph break
     * IGNORE if the line starts with "Organizers -"
     * Example: "Julian Knödler, Philip Muhl,"
   - Main_Author_Affiliation: Extract institution names that:
     * Follow the main authors
     * End with a semicolon or paragraph break
     * Example: "Porsche AG;"
   
   - Co_Author_Group: Extract all names that:
     * Appear in the same paragraph as main authors
     * Come AFTER the first semicolon
     * End with a comma
     * Example: "Eric Sax, Lutz Eckstein,"
   - Co_Author_Affiliation: Extract institution names that:
     * Follow each co-author group
     * End with a semicolon or paragraph break
     * Example: "Karlsruher Institute of Technology (KIT); RWTH Aachen University"

5. Session Organization:
   - Organizers: Extract the complete text after "Organizers -" that appears below the Overview
     * Include all names and affiliations as they appear
     * Example: "Anne O'Neil, AOC Systems Consortium; Aleczander Jackson, Enola Technologies; Gary Rushton, General Motors LLC"
   - Chairperson: Extract the complete text after "Chairperson:" if present
     * Include all names and affiliations as they appear
     * Example: "Eric Krueger, General Motors LLC"
   Note: For Panel Discussions, extract ONLY Organizers information, ignore Moderators and Panelists

Output Format Rules:
1. Maintain exact punctuation (commas, semicolons) as shown in the examples
2. Keep original text case (do not convert to upper/lower case)
3. For missing fields, use exactly "No data" (not "N/A" or empty string)
4. For Panel Discussion sessions, use exactly "panel discussion" for paper/author fields
5. IGNORE and DO NOT extract any entries marked as "BREAK"
6. Remove any extra spaces at the start or end of fields
7. Keep organization names exactly as written, including abbreviations (LLC, AG, etc.)

Return the extracted data in this exact JSON format:
{
    "Session_Name": "string",
    "Session_Code": "string",
    "Overview": "string",
    "Paper_No": "string",
    "Title": "string",
    "Main_Author_Group": "string",
    "Main_Author_Affiliation": "string",
    "Co_Author_Group": "string",
    "Co_Author_Affiliation": "string",
    "Organizers": "string",
    "Chairperson": "string"
}

Additional Context Rules:
1. Use the following session information if provided:
   Session Code: {session_info['session_code'] if session_info else 'Not provided'}
   Overview: {session_info['overview'] if session_info and session_info['overview'] else 'Not provided'}
   All Paper Numbers in this session: {', '.join(session_info['all_paper_numbers']) if session_info else 'Not provided'}

2. When extracting Overview:
   - If not found in the current text but provided in session_info, use that
   - If found in both, use the one from the current text

3. When extracting Paper Numbers:
   - Ensure all paper numbers match the ones provided in session_info
   - If a paper number is found in the text but not in session_info, include it
   - If a paper number is in session_info but not in the text, it belongs to another page of the same session

Text to extract from:
{chunk_text}
"""
    
        try:
            max_retries = 3
            retry_count = 0
            
            while retry_count < max_retries:
                try:
                    response = openai.ChatCompletion.create(
                        deployment_id=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
                        messages=[
                            {"role": "system", "content": "You are a precise data extraction assistant. Return only valid JSON arrays with exact field names as specified. Ensure the JSON is correctly formatted with no control characters or backslashes in strings."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0,
                        max_tokens=2000,
                        n=1
                    )
                    
                    if not response.choices:
                        print("Error: APIからの応答がありません")
                        retry_count += 1
                        time.sleep(2)
                        continue
                        
                    content = response.choices[0].message.content.strip()
                    print(f"APIレスポンス長: {len(content)} 文字")
                    
                    if not content:
                        print("Error: 空の応答を受信")
                        retry_count += 1
                        time.sleep(2)
                        continue
                    
                    # JSONの整形とパース
                    cleaned_content = clean_json_response(content)
                    print(f"クリーニング後の長さ: {len(cleaned_content)} 文字")
                    
                    try:
                        data = json.loads(cleaned_content)
                        
                        if isinstance(data, list):
                            print(f"Success: {len(data)}件のレコードを抽出")
                            if data:
                                print(f"最初のレコードのフィールド: {list(data[0].keys())}")
                            return data
                        else:
                            print("Error: 応答が配列形式ではありません")
                            # 単一オブジェクトを配列に変換
                            if isinstance(data, dict):
                                print("辞書を配列に変換します")
                                return [data]
                            retry_count += 1
                            time.sleep(2)
                            
                    except json.JSONDecodeError as e:
                        print(f"Error: JSON解析エラー: {str(e)}")
                        print(f"Position: 行 {e.lineno}, 列 {e.colno}")
                        error_context = cleaned_content[max(0, e.pos-100):min(len(cleaned_content), e.pos+100)]
                        print(f"Error context:\n{error_context}")
                        
                        # より積極的な修正を試みる
                        # 全体のJSONが破損している場合は、空のリストを返す
                        if '{' not in cleaned_content or '}' not in cleaned_content:
                            print("有効なJSONオブジェクトが見つかりません")
                            retry_count += 1
                            time.sleep(2)
                            continue
                            
                        # 別の修正方法を試す
                        try:
                            # シンプルな手法: JSONテキストを直接修正
                            simple_obj = '{' + cleaned_content.split('{', 1)[1].split('}', 1)[0] + '}'
                            print("シンプルな抽出手法を試みます")
                            data = json.loads(simple_obj)
                            print("単一オブジェクトとして抽出成功")
                            return [data]
                        except:
                            print("シンプルな抽出にも失敗しました")
                        
                        # 最終的な対応策: 空の配列を返す
                        retry_count += 1
                        time.sleep(2)
                    
                except Exception as e:
                    print(f"Error: API呼び出しエラー: {type(e).__name__}")
                    print(f"Message: {str(e)}")
                    if hasattr(e, 'response'):
                        print(f"Response status: {e.response.status_code}")
                    retry_count += 1
                    time.sleep(3)
            
            print(f"Warning: {max_retries}回のリトライ後もデータを抽出できませんでした")
            # 空の配列を返す
            return []
            
        except Exception as e:
            print(f"Critical Error: データ抽出処理全体で例外が発生: {str(e)}")
            return []

def extract_structured_data(text):
    """テキストから構造化データを抽出する"""
    setup_azure_openai()
    
    print(f"\nテキスト処理開始 (長さ: {len(text)} 文字)")
    max_chars_per_request = 2000  # チャンクサイズを2000文字に削減
    
    if len(text) > max_chars_per_request:
        print(f"テキストを分割処理開始...")
        chunks = split_text(text, max_chars_per_request)
        print(f"{len(chunks)}個のチャンクに分割完了")
        
        all_results = []
        seen_sessions = set()  # 重複チェック用
        
        for i, chunk in enumerate(chunks, 1):
            print(f"\nチャンク {i}/{len(chunks)} を処理中")
            print(f"チャンクサイズ: {len(chunk)} 文字")
            print(f"チャンク内容プレビュー:\n{chunk[:200]}...")
            
            chunk_results = extract_single_paper(chunk)
            
            if chunk_results:
                # 重複を除去しながらデータを追加
                for result in chunk_results:
                    # フィールド名を修正
                    # APIの結果で返ってくるフィールド名が一致していない場合の対応
                    field_mapping = {
                        'Session_Name': 'Session_Name',
                        'Session_Code': 'Session_Code',
                        'session name': 'Session_Name',
                        'session code': 'Session_Code',
                        'Paper_No': 'Paper_No',
                        'paper no': 'Paper_No',
                        'paper_no': 'Paper_No',
                    }
                    
                    # キーを標準化
                    standardized_result = {}
                    for key, value in result.items():
                        std_key = field_mapping.get(key.lower(), key)
                        standardized_result[std_key] = value
                    
                    # セッションIDの生成（キーの有無をチェック）
                    session_code = standardized_result.get('Session_Code', '')
                    paper_no = standardized_result.get('Paper_No', '')
                    session_id = f"{session_code}_{paper_no}"
                    
                    if session_id not in seen_sessions and session_id != "_":
                        seen_sessions.add(session_id)
                        all_results.append(standardized_result)
                        print(f"新しいセッションを追加: {session_id}")
                
                print(f"Progress: 現在までに {len(all_results)} 件のユニークなレコードを抽出")
            else:
                print(f"Warning: チャンク {i} からデータを抽出できませんでした")
        
        print(f"\n処理完了: 合計 {len(all_results)} 件のユニークなレコードを抽出")
        return all_results
    else:
        return extract_single_paper(text)

# This is a partial update that shows where changes should be made in ai_extractor.py

# Update the save_to_json function to also consider the year in the filename
def save_to_json(data, output_file=None, year=None):
    """データをJSONファイルとして保存する"""
    try:
        # 日付を含むファイル名を生成
        if output_file is None:
            # 入力ファイル名から拡張子を除いた部分を取得
            base_name = os.path.splitext(os.path.basename("input.txt"))[0]
            
            if year:
                # 年を含むファイル名を生成
                output_file = f"{year}_{base_name}.json"
            else:
                # 従来の日付形式を使用
                current_date = datetime.now().strftime("%Y%m%d")
                output_file = f"{base_name}_{current_date}.json"
        
        # 出力ディレクトリの作成
        output_dir = "output"
        os.makedirs(output_dir, exist_ok=True)
        
        # 完全なパスを生成
        output_path = os.path.join(output_dir, output_file)
        
        # データを保存
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\nデータを {output_path} に保存しました")
        return output_path
    except Exception as e:
        print(f"Error: ファイル保存中にエラー: {e}")
        return None

# メイン実行部分を更新 (if __name__ == "__main__": 以下の部分)
if __name__ == "__main__":
    try:
        # テキストファイルから入力を読み込む
        input_file = "input.txt"  # 入力ファイル名を適宜変更
        with open(input_file, 'r', encoding='utf-8') as f:
            input_text = f.read()
        
        # excel_writer モジュールをインポート
        from excel_writer import write_to_excel, extract_year_from_text
        
        # 年を抽出
        year = extract_year_from_text(input_text)
        print(f"文書から抽出した年: {year}")
        
        # データ抽出の実行
        results = extract_structured_data(input_text)
        
        if results:
            # 結果をJSONに保存（年を含む）
            output_path = save_to_json(results, year=year)
            
            # 結果をExcelに保存（元のテキストを渡す）
            try:
                from config import OUTPUT_FOLDER, base_filename
                excel_output = os.path.join(OUTPUT_FOLDER, f"{base_filename}.xlsx")
                excel_file = write_to_excel(results, excel_output, input_text)
                print(f"Excelファイルを保存しました: {excel_file}")
            except Exception as e:
                print(f"Excel出力中にエラー: {e}")
            
            if output_path:
                print(f"処理が完了しました。JSONファイル: {output_path}")
            else:
                print("Error: JSONファイルの保存に失敗しました")
        else:
            print("Error: データの抽出に失敗しました")
            
    except Exception as e:
        print(f"Error: プログラム実行中にエラー: {e}")