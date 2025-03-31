import os
import json
import openai
from dotenv import load_dotenv
import re
import textwrap
from datetime import datetime
import time  # timeモジュールを追加

def split_text(text, max_chars=2000):
    """テキストを適切なサイズに分割する"""
    # セッションコードで分割
    sessions = re.split(r'(Session Code [A-Z0-9]+)', text)
    chunks = []
    current_chunk = ""
    
    for i in range(0, len(sessions)):
        if i > 0 and sessions[i].startswith("Session Code"):
            # セッションコードを前のチャンクに含める
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = sessions[i]
            if i + 1 < len(sessions):
                current_chunk += sessions[i + 1]
        elif i == 0 or not sessions[i-1].startswith("Session Code"):
            if len(current_chunk) + len(sessions[i]) > max_chars:
                # さらに小さく分割
                sentences = re.split(r'(?<=[.!?])\s+', sessions[i])
                temp_chunk = ""
                for sentence in sentences:
                    if len(temp_chunk) + len(sentence) > max_chars:
                        if temp_chunk:
                            chunks.append(temp_chunk.strip())
                        temp_chunk = sentence
                    else:
                        temp_chunk += " " + sentence if temp_chunk else sentence
                if temp_chunk:
                    current_chunk += temp_chunk
            else:
                current_chunk += sessions[i]
    
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    # 空のチャンクを除去
    chunks = [chunk for chunk in chunks if chunk.strip()]
    
    # デバッグ情報
    print(f"テキストを {len(chunks)} チャンクに分割しました")
    for i, chunk in enumerate(chunks):
        print(f"チャンク {i+1}: {len(chunk)} 文字")
        print(f"プレビュー: {chunk[:100]}...\n")
    
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

def extract_single_chunk(chunk_text):
    """単一のテキストチャンクからデータを抽出する（改良版）"""
    prompt = f"""
Extract information from the technical session text below. Return ONLY a valid JSON array containing objects with these exact fields:

1. "Session_Name": The main session title at the start of the text
2. "Session_Code": The code after "Session Code" (e.g., "PFL750")
3. "Abstract": The paragraph starting with "This session..."
4. "Paper_No": Either a code like "2025-01-8582" or "ORAL ONLY"
5. "Title": The paper title that appears after the Paper_No on the same line
6. "Authors": An array of author names. For each author:
    - Must end with a comma
    - If there's only one author, it should still be in an array
    - Example: ["John Smith,"] or ["John Smith,", "Jane Doe,"]
7. "Affiliations": An array of affiliations. For each affiliation:
    - Must end with a semicolon OR be followed by a new paragraph
    - If there's only one affiliation, it should still be in an array
    - Example: ["Honda R&D;"] or ["Honda R&D"]
8. "Organizers": The full text after "Organizers:" until the next section
9. "Chairperson": The full text after "Chairperson:" until the next section (if present)

Important Rules:
1. Session Structure:
   - Each session starts with a title and ends with "Planned by..." text
   - Multiple papers can exist within one session
   - Each paper entry starts with a time (e.g., "8:00 a.m.")

2. Paper Information Structure:
   - Paper_No and Title appear on the next line
   - Authors and Affiliations follow on subsequent lines

3. Format Rules:
   - Return a valid JSON array, even if there's only one object
   - Use double quotes for all strings and field names
   - Each author name MUST end with a comma
   - Each affiliation MUST either end with a semicolon OR be followed by a new paragraph
   - Keep arrays even for single entries
   - Maintain the exact order of authors and their corresponding affiliations

Return ONLY a valid JSON array with these exact field names. No explanation text or markdown formatting.

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
            
            chunk_results = extract_single_chunk(chunk)
            
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
        return extract_single_chunk(text)

def save_to_json(data, output_file=None):
    """データをJSONファイルとして保存する"""
    try:
        # 日付を含むファイル名を生成
        if output_file is None:
            # 入力ファイル名から拡張子を除いた部分を取得
            base_name = os.path.splitext(os.path.basename("input.txt"))[0]
            # 現在の日付を取得
            current_date = datetime.now().strftime("%Y%m%d")
            # 新しいファイル名を生成
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

if __name__ == "__main__":
    try:
        # テキストファイルから入力を読み込む
        input_file = "input.txt"  # 入力ファイル名を適宜変更
        with open(input_file, 'r', encoding='utf-8') as f:
            input_text = f.read()
        
        # データ抽出の実行
        results = extract_structured_data(input_text)
        
        if results:
            # 結果を保存
            output_path = save_to_json(results)
            if output_path:
                print(f"処理が完了しました。出力ファイル: {output_path}")
            else:
                print("Error: ファイルの保存に失敗しました")
        else:
            print("Error: データの抽出に失敗しました")
            
    except Exception as e:
        print(f"Error: プログラム実行中にエラー: {e}")