import os
import json
import openai
from dotenv import load_dotenv
import re
import textwrap
from datetime import datetime
import time  # timeモジュールを追加

def split_text(text, max_chars=1500):
    """テキストをセッション単位で分割する"""
    # セッションの区切りパターン
    session_pattern = r'(?:^|\n)(?:.*?\n)?Session Code\s+[A-Z0-9]+.*?(?=(?:\n(?:.*?\n)?Session Code\s+[A-Z0-9]+|$))'
    
    # セッション単位で分割
    sessions = re.finditer(session_pattern, text, re.DOTALL)
    chunks = []
    current_chunk = ""
    
    for session in sessions:
        chunk = session.group(0)
        
        # 現在のチャンクのサイズをチェック
        if len(current_chunk) + len(chunk) > max_chars:
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = chunk
        else:
            current_chunk += ("\n" if current_chunk else "") + chunk
    
    # 最後のチャンクを追加
    if current_chunk:
        chunks.append(current_chunk)
    
    # デバッグ情報
    print(f"\nテキストを {len(chunks)} チャンクに分割しました")
    for i, chunk in enumerate(chunks, 1):
        print(f"\nチャンク {i}: {len(chunk)} 文字")
        # セッションコードを表示
        codes = re.findall(r'Session Code\s+([A-Z0-9]+)', chunk)
        if codes:
            print(f"含まれるセッションコード: {', '.join(codes)}")
    
    return chunks

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
    prompt = f"""
Extract information from the technical session text below following these precise rules:

1. Session Information:
   - Session_Name: Extract the line ABOVE "Session Code" (e.g., "Systems Engineering for Automotive - Part 1 of 2")
   - Session_Code: Extract ONLY the code that appears immediately after "Session Code" (e.g., "SS111"). Ignore any session codes mentioned elsewhere in the text
   - Overview: Extract the ENTIRE paragraph that appears below the "Room" line and before "Organizers" or "Time". If there is no text between "Room" and "Organizers", use "No data". Do not extract paper titles or other information as overview.
   - IMPORTANT: Each new "Session Code" indicates the start of a new session. DO NOT mix information from different sessions.
   - IMPORTANT: When you see a new "Session Code", all previous session information should be discarded.

2. Paper Information (multiple papers may exist per session):
   - Paper_No and Title appear in a table format with these patterns:
     Example 1:
     Time        Paper No.        Title
     1:30 p.m.   2024-01-2501    Scenario-Based Development and Meta-Level Design for Automotive Systems: An Explanatory Study
     2:00 p.m.   ORAL ONLY       Front Zone Control Unit for Propulsion and Chassis Domains in a Zonal E/E Architecture

     Example 2:
     Time        Paper No.        Title
     2:00 p.m.   ORAL ONLY       Front Zone Control Unit for Propulsion and Chassis Domains in a Zonal E/E Architecture
   
   - Paper_No: Extract either:
     * The numeric code in format "20XX-XX-XXXX"
     * The text "ORAL ONLY"
   - Title: Extract ONLY the title that appears in the same session as the current Session_Code
   - IMPORTANT: Do not extract titles from different sessions
   
3. Author Information:
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

4. Session Organization:
   - Organizers: Extract the complete text after "Organizers -" that appears below the Overview
     * Include all names and affiliations as they appear
     * Example: "Anne O'Neil, AOC Systems Consortium; Aleczander Jackson, Enola Technologies; Gary Rushton, General Motors LLC"
   - Chairperson: Extract the complete text after "Chairperson:" if present
     * Include all names and affiliations as they appear
     * Example: "Eric Krueger, General Motors LLC"

Output Format Rules:
1. Maintain exact punctuation (commas, semicolons) as shown in the examples
2. Keep original text case (do not convert to upper/lower case)
4. For missing fields, use exactly "No data" (not "N/A" or empty string)
5. IGNORE and DO NOT extract any entries marked as "BREAK"
6. Remove any extra spaces at the start or end of fields
7. Keep organization names exactly as written, including abbreviations (LLC, AG, etc.)

Return the extracted data in this exact JSON format:
{{
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
}}

Text to extract from:
{chunk_text}
"""
    max_retries = 5  # リトライ回数を増やす
    retry_count = 0
    retry_delay = 5  # リトライ間隔を5秒に設定
    
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
                print(f"Error: APIからの応答がありません (リトライ {retry_count + 1}/{max_retries})")
                retry_count += 1
                time.sleep(retry_delay)
                continue
            
            content = response.choices[0].message.content.strip()
            print(f"APIレスポンス長: {len(content)} 文字")
            
            if not content:
                print(f"Error: 空の応答を受信 (リトライ {retry_count + 1}/{max_retries})")
                retry_count += 1
                time.sleep(retry_delay)
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
                
                print(f"Error: 応答が配列形式ではありません (リトライ {retry_count + 1}/{max_retries})")
                if isinstance(data, dict):
                    print("辞書を配列に変換します")
                    return [data]
                retry_count += 1
                time.sleep(retry_delay)
                    
            except json.JSONDecodeError as e:
                print(f"Error: JSON解析エラー: {str(e)}")
                print(f"Position: 行 {e.lineno}, 列 {e.colno}")
                error_context = cleaned_content[max(0, e.pos-100):min(len(cleaned_content), e.pos+100)]
                print(f"Error context:\n{error_context}")
                
                try:
                    simple_obj = '{' + cleaned_content.split('{', 1)[1].split('}', 1)[0] + '}'
                    print("シンプルな抽出手法を試みます")
                    data = json.loads(simple_obj)
                    print("単一オブジェクトとして抽出成功")
                    return [data]
                except:
                    print(f"シンプルな抽出にも失敗しました (リトライ {retry_count + 1}/{max_retries})")
                    retry_count += 1
                    time.sleep(retry_delay)
                
        except Exception as e:
            print(f"Error: API呼び出しエラー: {type(e).__name__}")
            print(f"Message: {str(e)}")
            if hasattr(e, 'response'):
                print(f"Response status: {e.response.status_code}")
            retry_count += 1
            time.sleep(retry_delay)
    
    print(f"Warning: {max_retries}回のリトライ後もデータを抽出できませんでした")
    return []

def extract_structured_data(text):
    """テキストから構造化データを抽出する"""
    try:
        setup_azure_openai()
        
        print(f"\nテキスト処理開始 (長さ: {len(text)} 文字)")
        
        # セッションコードの総数を事前にカウント
        total_sessions = len(re.findall(r'Session Code\s+[A-Z0-9]+', text))
        print(f"\n文書全体のセッション数: {total_sessions}")
        
        # セッション単位で分割
        chunks = split_text(text)
        print(f"{len(chunks)}個のチャンクに分割完了")
        
        all_results = []
        seen_sessions = set()
        
        for i, chunk in enumerate(chunks, 1):
            try:
                print(f"\nチャンク {i}/{len(chunks)} を処理中")
                print(f"チャンクサイズ: {len(chunk)} 文字")
                
                # セッションコードを抽出して表示
                session_codes = re.findall(r'Session Code\s+([A-Z0-9]+)', chunk)
                if session_codes:
                    print(f"このチャンクに含まれるセッションコード: {', '.join(session_codes)}")
                
                # プロンプトの生成
                prompt = f"""
以下のテキストからセッション情報を抽出してください。各セッションは"Session Code"で区切られています。

抽出ルール:
1. 各セッションの情報を個別に抽出
2. セッション名は"Session Code"の直前の行から抽出
3. セッションコードは"Session Code"の直後のコードを抽出
4. 論文情報は各セッション内の表形式から抽出
5. 著者情報は論文タイトルの直後の行から抽出

出力形式:
[
    {{
        "session_name": "セッション名",
        "session_code": "セッションコード",
        "paper_no": "論文番号",
        "title": "論文タイトル",
        "main_author_group": "主著者グループ",
        "main_author_affiliation": "主著者の所属",
        "co_author_group": "共著者グループ",
        "co_author_affiliation": "共著者の所属",
        "organizers": "オーガナイザー",
        "chairperson": "議長"
    }}
]

テキスト:
{chunk}
"""
                
                # API呼び出し
                response = openai.ChatCompletion.create(
                    deployment_id=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
                    messages=[
                        {"role": "system", "content": "You are a precise data extraction assistant. Extract session and paper information from the text. Return ONLY valid JSON arrays with the exact structure specified."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0,
                    max_tokens=2000
                )
                
                if response.choices:
                    content = response.choices[0].message.content.strip()
                    print(f"APIレスポンス: {content[:200]}...")  # レスポンスの最初の200文字を表示
                    
                    try:
                        # JSONの整形
                        content = content.replace('```json', '').replace('```', '').strip()
                        
                        # 配列形式の確認
                        if not content.startswith('['):
                            print("Warning: レスポンスが配列形式ではありません。配列に変換します。")
                            content = f"[{content}]"
                        
                        data = json.loads(content)
                        
                        if isinstance(data, list):
                            print(f"Success: {len(data)}件のレコードを抽出")
                            all_results.extend(data)
                        else:
                            print("Warning: レスポンスが配列ではありません。単一オブジェクトとして処理します。")
                            all_results.append(data)
                            
                    except json.JSONDecodeError as e:
                        print(f"Error: JSON解析エラー: {str(e)}")
                        print(f"Position: 行 {e.lineno}, 列 {e.colno}")
                        print(f"問題のある部分: {content[max(0, e.pos-50):min(len(content), e.pos+50)]}")
                        continue
                
            except Exception as chunk_error:
                print(f"Error: チャンク {i} の処理中にエラーが発生: {str(chunk_error)}")
                continue
        
        print(f"\n処理完了: 合計 {len(all_results)} 件のレコードを抽出")
        print(f"抽出されたユニークなセッション数: {len({r['session_code'] for r in all_results})}")
        return all_results
            
    except Exception as e:
        print(f"Error: データ抽出処理全体でエラーが発生: {str(e)}")
        return []

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

# メイン実行部分を更新
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