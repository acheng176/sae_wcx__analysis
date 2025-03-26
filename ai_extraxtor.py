import openai
import json
from tqdm import tqdm
import config

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
    # APIキーの存在確認（値は表示しない）
    if not config.AZURE_OPENAI_API_KEY:
        print("WARNING: Azure OpenAI API Key is missing!")
    else:
        print("Azure OpenAI API Key is set")

def extract_structured_data(text):
    """AIを使ってテキストから構造化データを抽出する"""
    setup_azure_openai()
    
    # テキスト長の確認
    print(f"\nExtracting structured data from text (length: {len(text)} chars)")
    
    # プロンプトの準備
    prompt = f"""
    あなたは、SAE WCXのプログラムから情報を抽出するアシスタントです。
    以下のテキストから、セッション情報（Session Code、Session Name）、
    発表情報（Paper No、Title、Authors、Affiliation、Time、Date、Room）、
    セッション運営者情報（Session Organizers、Session Chairperson）を抽出してJSON形式で返してください。
    
    複数のセッションや発表がある場合はリスト形式で全て抽出してください。
    発表がORAL ONLYの場合は、Paper Noとして"ORAL ONLY"を設定してください。
    
    テキスト:
    '''
    {text}
    '''
    
    JSONフォーマット:
    ```
    [
      {{
        "Session Code": "セッションコード",
        "Session Name": "セッション名",
        "Paper No": "論文番号",
        "Title": "タイトル",
        "Authors": "著者名",
        "Affiliation": "所属",
        "Time": "発表時間",
        "Date": "発表日",
        "Room": "部屋",
        "Session Organizers": "セッションオーガナイザー",
        "Session Chairperson": "セッション座長"
      }},
      ...
    ]
    ```
    
    JSONだけを返してください。説明は不要です。
    """
    
    print("Sending request to Azure OpenAI API...")
    
    try:
        response = openai.ChatCompletion.create(
            deployment_id=config.AZURE_OPENAI_DEPLOYMENT_NAME,
            messages=[
                {"role": "system", "content": "You are an AI assistant that extracts structured data from SAE WCX program information."},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            max_tokens=4000
        )
        
        content = response.choices[0].message.content
        print(f"Response received, length: {len(content)} chars")
        print(f"Sample of response: {content[:200]}")
        
        # JSONデータを抽出
        json_start = content.find('[')
        json_end = content.rfind(']') + 1
        
        if json_start >= 0 and json_end > json_start:
            json_str = content[json_start:json_end]
            try:
                data = json.loads(json_str)
                print(f"Successfully parsed JSON with {len(data)} records")
                # 最初のレコードの内容をサンプル表示
                if data:
                    print(f"Sample record: {json.dumps(data[0], indent=2, ensure_ascii=False)[:500]}...")
                return data
            except json.JSONDecodeError as e:
                print(f"Failed to parse JSON response: {e}")
                print(f"Problematic JSON: {json_str[:200]}...")
                return []
        else:
            print(f"No JSON found in response. JSON markers: start={json_start}, end={json_end}")
            return []
            
    except Exception as e:
        print(f"Error calling Azure OpenAI API: {e}")
        return []

def process_all_texts(all_texts):
    """全てのテキストから構造化データを抽出する"""
    print("\nStarting to process all extracted texts with AI...")
    all_data = []
    
    for idx, text_item in enumerate(tqdm(all_texts, desc="Extracting data with AI")):
        print(f"\nProcessing file {idx+1}/{len(all_texts)}: {text_item['filename']}")
        extracted_data = extract_structured_data(text_item["text"])
        
        # ファイル名を各レコードに追加
        for data in extracted_data:
            data["Source File"] = text_item["filename"]
            all_data.append(data)
        
        print(f"Extracted {len(extracted_data)} records from {text_item['filename']}")
    
    print(f"\nTotal extracted records: {len(all_data)}")
    return all_data