import os
import json
import openai
from dotenv import load_dotenv
import re
import textwrap
from datetime import datetime
import time  # timeモジュールを追加

def validate_session_name(session_name, session_code, chunk):
    """セッション名の妥当性を検証"""
    # 空のセッション名をチェック
    if not session_name.strip():
        return False
    
    # セッション名が異常に長いケースをチェック
    if len(session_name) > 200:
        return False
    
    # 不適切なパターンをより詳細にチェック
    invalid_patterns = [
        r'Room\s+',
        r'Paper No\.',
        r'Time\s+',
        r'Title\s+',
        r'Organizers\s*-',
        r'Chairperson\s*:',
        r'\d{1,2}:\d{2}\s*(?:a\.m\.|p\.m\.)',  # 時刻のパターン
        r'Session\s+Code',
    ]
    
    for pattern in invalid_patterns:
        if re.search(pattern, session_name, re.IGNORECASE):
            return False
    
    return True

def split_text(text):
    """テキストをセッション単位で分割する"""
    # まず、ページヘッダーを完全に除去
    text = re.sub(
        r'(?:^|\n)\s*WCX SAE World Congress Experience\s*\n'
        r'\s*Technical Session Schedule\s*\n'
        r'\s*As of\s+[A-Za-z]+\s+\d+,\s+\d{4}\s+\d{1,2}:\d{2}:\d{2}\s*(?:AM|PM)?\s*\n',
        '\n',
        text,
        flags=re.MULTILINE | re.IGNORECASE
    )
    
    # セッションの区切りパターン
    session_pattern = r'(?:^|\n\n)([^\n]+)\n\s*Session Code\s+([A-Z0-9]+)'
    sessions = re.finditer(session_pattern, text, re.MULTILINE)
    
    chunks = []
    session_starts = []  # セッション開始位置を保存
    
    # まずセッションの開始位置をすべて取得
    for match in sessions:
        session_starts.append((match.start(), match.group(1).strip(), match.group(2)))
    
    # 各セッションの範囲を決定
    for i, (start, session_name, session_code) in enumerate(session_starts):
        # セッション名の妥当性をチェック
        if not validate_session_name(session_name, session_code, text[start:]):
            print(f"Warning: セッション名の検証に失敗しました: {session_name}")
            # より厳密な代替セッション名の検索
            lines_before = text[:start].split('\n')
            valid_lines = [
                line.strip() for line in reversed(lines_before[-5:])
                if line.strip() and validate_session_name(line.strip(), session_code, text[start:])
                and not re.match(r'.*\d{1,2}:\d{2}\s*(?:a\.m\.|p\.m\.)', line)
            ]
            
            if valid_lines:
                session_name = valid_lines[0]
                print(f"Info: 代替のセッション名を使用: {session_name}")
            else:
                print(f"Error: 有効なセッション名が見つかりませんでした: {session_code}")
                continue
        
        # セッションの終了位置を決定
        if i < len(session_starts) - 1:
            # 次のセッションの直前まで
            next_session_start = session_starts[i + 1][0]
            session_content = text[start:next_session_start].strip()
        else:
            # 最後のセッションは文書の最後まで
            session_content = text[start:].strip()
        
        # 残っているページヘッダーやフッターを削除
        session_content = re.sub(r'\n\s*(?:Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|Monday),\s+[A-Za-z]+\s+\d+\s*\n', '\n', session_content)
        session_content = re.sub(r'\n\s*Page\s+\d+\s+of\s+\d+\s*\n', '\n', session_content)
        
        # 連続する空行を1つの空行に置換
        session_content = re.sub(r'\n\s*\n\s*\n+', '\n\n', session_content)
        
        # チャンクを構築
        chunk = f"{session_name}\n{session_content}"
        chunks.append(chunk)
        
        # デバッグ情報
        print(f"\nセッション検出:")
        print(f"Session Code: {session_code}")
        print(f"Session Name: {session_name}")
        print(f"チャンクサイズ: {len(chunk)} 文字")
        
        # セッションの境界を表示
        content_preview = session_content[:100] + "..." if len(session_content) > 100 else session_content
        print(f"セッション内容プレビュー:\n{content_preview}")
    
    print(f"\n合計 {len(chunks)} 個のセッションを検出しました")
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
    
    chunks = []
    try:
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

def get_extraction_prompt(text):
    """Generate the extraction prompt"""
    return f"""
Please extract structured data from the following text according to these specific rules:

1. Session Information:
   - Session Code: Extract the code that follows "Session Code" (e.g., PFL750)
   - Session Name: Extract the complete session name from the line before "Session Code"
   - Overview: Extract the complete paragraph that appears after "Room" and before the first "Time" or "Paper No."

2. Paper Information:
   - Paper Number (paper_no): Extract the number in format "202x-xx-xxxx" or "ORAL ONLY"
   - Title: Extract the complete title text that appears after the paper number
   
   - Author Information Rules:
     * For each paper's author line:
       - Main Author Group: Extract ALL names that appear BEFORE the first institution
         Example: "Xiaofeng Yin, Hong Li, Xihua University" → "Xiaofeng Yin, Hong Li"
       
       - Main Author Affiliation: Extract the FIRST institution that appears
         Example: "Xiaofeng Yin, Hong Li, Xihua University" → "Xihua University"
       
       - Co-Author Group: Extract ALL names that appear AFTER the first institution and BEFORE their institutions
         Example: "Xiaofeng Yin, Hong Li, Xihua University; Jinhong Zhang, Jeely Auto Research" → "Jinhong Zhang"
       
       - Co-Author Affiliation: Extract ALL institutions that appear after co-author names
         Example: "Xiaofeng Yin, Hong Li, Xihua University; Jinhong Zhang, Jeely Auto Research" → "Jeely Auto Research"

3. Additional Session Information:
   - Organizers: 
     * Look for lines starting with "Organizers -" or "Organizers:"
     * Extract the ENTIRE text that follows, including all names and affiliations
     * Keep all semicolons (;) and commas (,) in their original positions
     * Example: "Organizers - John Smith, Company A; Jane Doe, Company B" → "John Smith, Company A; Jane Doe, Company B"

   - Chairperson:
     * Look for text starting with "Chairperson -" or "Chairperson:"
     * Extract the COMPLETE text that follows, including all names and affiliations
     * Example: "Chairperson - Dan DeMescovo, Oakland University" → "Dan DeMescovo, Oakland University"

Text to process:
{text}

Required Output Format:
[
    {{
        "session_name": "",
        "session_code": "",
        "overview": "",
        "paper_no": "",
        "title": "",
        "main_author_group": "",
        "main_author_affiliation": "",
        "co_author_group": "",
        "co_author_affiliation": "",
        "organizers": "",
        "chairperson": ""
    }}
]

Important Requirements:
1. Output MUST be in valid JSON format
2. Extract ALL information exactly as it appears in the text
3. Do not modify, reformat, or clean any extracted text
4. Keep all original punctuation (commas, semicolons)
5. For author information:
   - Main authors are those appearing BEFORE the first institution
   - Co-authors are those appearing AFTER the first institution
   - Keep exact name order and grouping
6. For organizers and chairperson:
   - Extract the COMPLETE text as it appears
   - Keep all original formatting and punctuation
   - Include ALL names and affiliations

Please process the text and return ONLY the JSON output without any additional explanation or formatting."""

def extract_structured_data(text, debug_mode=False, debug_chunk_count=5):
    """テキストから構造化データを抽出する
    
    Args:
        text (str): 処理するテキスト
        debug_mode (bool): デバッグモードの場合True
        debug_chunk_count (int): デバッグモード時に処理するチャンク数
    """
    try:
        setup_azure_openai()
        
        print(f"\nテキスト処理開始 (長さ: {len(text)} 文字)")
        
        # セッションコードの総数を事前にカウント
        total_sessions = len(re.findall(r'Session Code\s+[A-Z0-9]+', text))
        print(f"\n文書全体のセッション数: {total_sessions}")
        
        # セッション単位で分割
        chunks = split_text(text)
        print(f"{len(chunks)}個のチャンクに分割完了")
        
        # デバッグモードの場合はチャンク数を制限
        if debug_mode:
            chunks = chunks[:debug_chunk_count]
            print(f"\nデバッグモード: 最初の{debug_chunk_count}個のチャンクのみを処理します")
        
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
                prompt = get_extraction_prompt(chunk)
                
                # API呼び出し（バージョン0.28の書き方）
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
        
        return None
    except Exception as e:
        print(f"Warning: 年の抽出中にエラー: {e}")
        return None

def save_to_json(data, output_file=None):
    """データをJSONファイルとして保存する"""
    try:
        # 入力ファイルから年を抽出
        with open("input.txt", 'r', encoding='utf-8') as f:
            input_text = f.read()
            year = extract_year_from_text(input_text)
        
        # 出力ファイル名の生成
        if year:
            output_file = f"{year}_wcx_sessions.json"
        else:
            current_date = datetime.now().strftime("%Y%m%d")
            output_file = f"wcx_sessions_{current_date}.json"
        
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

def validate_data_format(data):
    """データの形式を検証する
    
    Args:
        data (list): 検証するデータのリスト
        
    Returns:
        bool: データが有効な場合はTrue、そうでない場合はFalse
    """
    if not isinstance(data, list):
        print("Error: データはリストである必要があります")
        return False
    
    required_fields = [
        "session_name",
        "session_code",
        "overview",
        "paper_no",
        "title"
    ]
    
    for item in data:
        if not isinstance(item, dict):
            print("Error: 各データ項目は辞書である必要があります")
            return False
            
        for field in required_fields:
            if field not in item:
                print(f"Error: 必須フィールド '{field}' が欠けています")
                return False
                
            if not isinstance(item[field], str):
                print(f"Error: フィールド '{field}' は文字列である必要があります")
                return False
    
    return True

def main():
    try:
        # テキストファイルから入力を読み込む
        input_file = "input.txt"
        with open(input_file, 'r', encoding='utf-8') as f:
            input_text = f.read()
        
        # 年を抽出して表示
        year = extract_year_from_text(input_text)
        if year:
            print(f"文書から抽出した年: {year}")
        else:
            print("Warning: 文書から年を抽出できませんでした")
        
        # データ抽出の実行
        results = extract_structured_data(input_text)
        
        if results:
            # カテゴリー分類の実行
            from categorizer import add_categories_to_data
            results = add_categories_to_data(results)
            
            # 結果をJSONに保存
            output_path = save_to_json(results)
            
            # 結果をExcelに保存
            try:
                from excel_writer import write_to_excel
                excel_output = os.path.join("output", f"{year}_wcx_sessions.xlsx")
                excel_file, df = write_to_excel(results, excel_output)
                print(f"Excelファイルを保存しました: {excel_file}")
                
                # SQLiteデータベースに保存
                from db_handler import DatabaseHandler
                db = DatabaseHandler()
                if db.store_data(df, year):
                    # カテゴリー分布のグラフを作成
                    graph_file = db.create_visualization(year)
                    if graph_file:
                        print(f"カテゴリー分布グラフを作成しました: {graph_file}")
            except Exception as e:
                print(f"出力処理中にエラー: {e}")
            
            if output_path:
                print(f"処理が完了しました。JSONファイル: {output_path}")
            else:
                print("Error: JSONファイルの保存に失敗しました")
        else:
            print("Error: データの抽出に失敗しました")
            
    except Exception as e:
        print(f"Error: プログラム実行中にエラー: {e}")

if __name__ == "__main__":
    main()