import os
import json
import openai
from dotenv import load_dotenv
import re
import textwrap
from datetime import datetime

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
    """APIレスポンスのJSONをクリーンアップする"""
    try:
        # Markdown装飾を削除
        content = re.sub(r'```json\s*|\s*```', '', content)
        content = content.strip()
        
        # 一般的なJSON形式の問題を修正
        content = re.sub(r',(\s*[}\]])', r'\1', content)  # 末尾のカンマを削除
        content = re.sub(r'(?<!\\)"(?=(,|\s*[}\]]))', '\\"', content)  # エスケープされていない引用符を修正
        
        # 配列形式の確認
        if not (content.startswith('[') and content.endswith(']')):
            print("Warning: 無効なJSON形式（配列ではない）")
            content = f"[{content}]"  # 配列でない場合は配列に変換
        
        return content
    except Exception as e:
        print(f"Error: JSONクリーンアップ中にエラー: {e}")
        return content

def extract_single_chunk(chunk_text):
    """単一のテキストチャンクからデータを抽出する"""
    prompt = f"""
Extract session information from the text below and return as a JSON array. Each object must have these exact fields:
"Session Name", "Session Code", "Paper No.", "Title", "Abstract", "Main-author GR", "Main-author affiliation", "Co-author & Affiliation GR", "Region"

Rules:
1. Return ONLY valid JSON array
2. Use empty string ("") for missing values
3. Ensure all field names match exactly
4. Keep responses concise
5. Do not include any markdown or extra text

Text to process:
{chunk_text}
"""
    
    try:
        response = openai.ChatCompletion.create(
            deployment_id=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
            messages=[
                {"role": "system", "content": "You are a precise data extraction assistant. Return only valid JSON arrays with exact field names."},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            max_tokens=2000,
            n=1
        )
        
        if not response.choices:
            print("Error: APIからの応答がありません")
            return None
            
        content = response.choices[0].message.content.strip()
        print(f"APIレスポンス長: {len(content)} 文字")
        
        if not content:
            print("Error: 空の応答を受信")
            return None
        
        # JSONの整形とパース
        try:
            cleaned_content = clean_json_response(content)
            print(f"クリーニング後の長さ: {len(cleaned_content)} 文字")
            
            data = json.loads(cleaned_content)
            
            if isinstance(data, list):
                print(f"Success: {len(data)}件のレコードを抽出")
                if data:
                    print(f"最初のレコードのフィールド: {list(data[0].keys())}")
                return data
            else:
                print("Error: 応答が配列形式ではありません")
                return None
                
        except json.JSONDecodeError as e:
            print(f"Error: JSON解析エラー: {str(e)}")
            print(f"Position: 行 {e.lineno}, 列 {e.colno}")
            error_context = content[max(0, e.pos-100):min(len(content), e.pos+100)]
            print(f"Error context:\n{error_context}")
            return None
            
    except Exception as e:
        print(f"Error: API呼び出しエラー: {type(e).__name__}")
        print(f"Message: {str(e)}")
        if hasattr(e, 'response'):
            print(f"Response status: {e.response.status_code}")
        return None

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
                    session_id = f"{result.get('Session Code', '')}_{result.get('Paper No.', '')}"
                    if session_id not in seen_sessions and session_id != "_":
                        seen_sessions.add(session_id)
                        all_results.append(result)
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