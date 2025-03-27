import json
import re

def split_text(text, max_chars=2000):
    """テキストを適切なサイズに分割する"""
    # セッション区切りで分割
    sessions = text.split("\n\n")
    chunks = []
    current_chunk = []
    current_length = 0
    
    for session in sessions:
        session_length = len(session)
        
        # セッションが単体で最大サイズを超える場合は、さらに分割
        if session_length > max_chars:
            # ピリオドで分割
            sentences = re.split(r'(?<=[.!?])\s+', session)
            current_sentence_chunk = []
            current_sentence_length = 0
            
            for sentence in sentences:
                if current_sentence_length + len(sentence) <= max_chars:
                    current_sentence_chunk.append(sentence)
                    current_sentence_length += len(sentence)
                else:
                    if current_sentence_chunk:
                        chunks.append(" ".join(current_sentence_chunk))
                    current_sentence_chunk = [sentence]
                    current_sentence_length = len(sentence)
            
            if current_sentence_chunk:
                chunks.append(" ".join(current_sentence_chunk))
            continue
        
        # 現在のチャンクに追加可能かチェック
        if current_length + session_length <= max_chars:
            current_chunk.append(session)
            current_length += session_length
        else:
            # 現在のチャンクを保存
            if current_chunk:
                chunks.append("\n\n".join(current_chunk))
            # 新しいチャンクを開始
            current_chunk = [session]
            current_length = session_length
    
    # 最後のチャンクを追加
    if current_chunk:
        chunks.append("\n\n".join(current_chunk))
    
    return chunks

def setup_azure_openai():
    """Azure OpenAIの設定"""
    print("\nSetting up Azure OpenAI client...")
    openai.api_key = config.AZURE_OPENAI_API_KEY
    openai.api_version = config.AZURE_OPENAI_API_VERSION
    openai.api_base = config.AZURE_OPENAI_ENDPOINT
    openai.api_type = 'azure'
    print(f"Azure OpenAI API Base: {config.AZURE_OPENAI_ENDPOINT}")
    print(f"Azure OpenAI API Version: {config.AZURE_OPENAI_API_VERSION}")
    print(f"Azure OpenAI Deployment: {config.AZURE_OPENAI_DEPLOYMENT_NAME}")
    print(f"Azure OpenAI API Key (first 10 chars): {config.AZURE_OPENAI_API_KEY[:10]}...")
    # APIキーの存在確認（値は表示しない）
    if not config.AZURE_OPENAI_API_KEY:
        print("WARNING: Azure OpenAI API Key is missing!")
    else:
        print("Azure OpenAI API Key is set")

def clean_json_response(content):
    """APIレスポンスのJSONを整形する"""
    try:
        # Markdown装飾を削除
        content = content.replace('```json', '').replace('```', '')
        
        # 最初の[から最後の]までを抽出
        start = content.find('[')
        end = content.rfind(']') + 1
        if start >= 0 and end > start:
            json_str = content[start:end]
            
            # 一般的なJSON形式の問題を修正
            json_str = json_str.replace('\n', ' ')  # 改行を削除
            json_str = re.sub(r'\s+', ' ', json_str)  # 複数の空白を1つに
            json_str = re.sub(r',\s*}', '}', json_str)  # 末尾のカンマを削除
            json_str = re.sub(r',\s*]', ']', json_str)  # 配列末尾のカンマを削除
            json_str = re.sub(r'"\s*,\s*"', '", "', json_str)  # カンマの周りの空白を整理
            
            # 引用符の修正
            json_str = re.sub(r'(?<!\\)"', '\\"', json_str)  # エスケープされていない引用符をエスケープ
            json_str = re.sub(r'\\"([^"]*)\\"', r'"\1"', json_str)  # 正しい引用符に戻す
            
            return json_str
    except Exception as e:
        print(f"Error cleaning JSON: {e}")
        print(f"Original content: {content[:200]}...")
    return content

def extract_structured_data(text):
    """AIを使ってテキストから構造化データを抽出する"""
    setup_azure_openai()
    
    # テキスト長の確認
    print(f"\nExtracting structured data from text (length: {len(text)} chars)")
    
    # テキストをセッション単位で分割
    sessions = text.split("\nSession Code")
    if len(sessions) > 1:
        sessions = ["Session Code" + s if i > 0 else s for i, s in enumerate(sessions)]
    
    print(f"Split text into {len(sessions)} sessions")
    
    # セッションを小さなチャンクに分割
    chunks = []
    for session in sessions:
        if len(session.strip()) > 0:
            session_chunks = split_text(session, max_chars=2000)
            chunks.extend(session_chunks)
    
    print(f"Created {len(chunks)} chunks for processing")
    
    all_data = []
    for i, chunk in enumerate(chunks, 1):
        print(f"\nProcessing chunk {i}/{len(chunks)} (length: {len(chunk)} chars)")
        
        # プロンプトの準備
        prompt = f"""
            以下のテキストからセッション情報を抽出し、JSON形式で返してください。
            必ず以下のフィールドを含む有効なJSONを返してください：

            - Session Name: セッション名
            - Session Code: セッションコード
            - Paper No.: 論文番号
            - Title: 発表タイトル
            - Abstract: セッションの説明文
            - Main-author GR: 発表の主著者名
            - Main-author affiliation: 主著者の所属機関名
            - Co-author & Affiliation GR: 共著者名と所属機関
            - Region: 主著者の国

            テキスト:
            '''
            {chunk}
            '''

            必ず配列形式の有効なJSONを返してください。
            """
        
        print("Sending request to Azure OpenAI API...")
        
        try:
            response = openai.ChatCompletion.create(
                deployment_id=config.AZURE_OPENAI_DEPLOYMENT_NAME,
                messages=[
                    {"role": "system", "content": "You are a data extraction assistant. Always return valid JSON array, even if empty."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                max_tokens=2000,
                n=1,
                stop=None
            )
            
            if not response.choices:
                print("Error: No response choices received from API")
                continue
                
            content = response.choices[0].message.content.strip()
            if not content:
                print("Error: Empty response content received from API")
                continue
            
            # JSONの整形とパース
            try:
                # まずMarkdownの装飾を削除
                content = content.replace('```json', '').replace('```', '').strip()
                
                # 空の配列の場合はスキップ
                if content == '[]':
                    print("Empty array received, skipping...")
                    continue
                
                # 配列の開始と終了を確認
                if not (content.startswith('[') and content.endswith(']')):
                    print("Invalid JSON format (not an array)")
                    continue
                
                data = json.loads(content)
                if isinstance(data, list) and len(data) > 0:
                    print(f"Successfully parsed JSON with {len(data)} records")
                    print(f"Sample record: {json.dumps(data[0], indent=2, ensure_ascii=False)[:200]}...")
                    all_data.extend(data)
                else:
                    print("No valid records found in response")
                
            except json.JSONDecodeError as e:
                print(f"Failed to parse JSON response: {e}")
                print(f"Problematic content: {content[:200]}...")
                continue
                
        except Exception as e:
            print(f"Error calling Azure OpenAI API: {e}")
            print(f"Error type: {type(e).__name__}")
            if hasattr(e, 'response'):
                print(f"Response status: {e.response.status_code}")
                print(f"Response body: {e.response.text}")
            continue
    
    print(f"\nTotal records extracted: {len(all_data)}")
    return all_data 