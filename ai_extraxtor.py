def extract_structured_data(text):
    """AIを使ってテキストから構造化データを抽出する"""
    setup_azure_openai()
    
    # テキスト長の確認
    print(f"\nExtracting structured data from text (length: {len(text)} chars)")
    
    # トークン制限を考慮したテキスト分割
    max_chars_per_request = 8000  # 安全な制限値
    if len(text) > max_chars_per_request:
        print(f"Warning: Text length ({len(text)} chars) exceeds safe limit. Processing may be incomplete.")
    
    # プロンプトの準備
    prompt = f"""
        あなたは、SAE WCXの技術セッションスケジュール情報から構造化データを抽出する専門家です。
        以下のテキストから各セッションと論文の情報を抽出し、JSON形式で返してください。

        テキストは複数のセッションを含んでいます。各セッションは以下の形式で表示されています：
        - セッション名（例：「Controls for Hybrids and Electric Powertrains Part 1 of 3」）
        - セッションコード（例：「PFL750」）
        - 開催場所と時間（例：「Room 140 A」「8:00 a.m.」）
        - セッションの説明文（1段落のテキスト）
        - オーガナイザー情報
        - 各発表の情報（時間、論文番号、タイトル、著者、所属機関）

        各セッションと発表の情報から以下のデータを抽出してください：
        1. Session Name: セッション名（例：「Controls for Hybrids and Electric Powertrains Part 1 of 3」）
        2. Session Code: セッションコード（例：「PFL750」）
        3. Paper No.: 論文番号（「ORAL ONLY」または「2025-01-XXXX」形式）
        4. Title: 発表タイトル
        5. Abstract: セッションの説明文（「This session covers...」から始まる段落全体）
        6. Main-author GR: 発表の主著者名（複数名の場合もある）
        7. Main-author affiliation: 主著者の所属機関名
        8. Co-author & Affiliation GR: 共著者名と所属機関
        9. Region: 主著者の国

        注意事項：
        - 一つのPDFに複数のセッションが含まれていることがあります。それぞれを別々のレコードとして抽出してください。
        - 各セッション内の各発表も別々のレコードとして抽出してください。
        - 「ORAL ONLY」はPaper No.として扱ってください。
        - セッション説明が「This session covers...」や「This session features...」で始まるテキスト全体をAbstractとして抽出してください。
        - 主著者（Main-author GR）は複数人いる場合があります。すべて抽出してください。
        - 所属機関（affiliation）は主著者名の後に記載されています。

        テキスト:
        '''
        {text}
        '''
        JSON形式で結果を返してください:
        """
    
    print("Sending request to Azure OpenAI API...")
    
    try:
        response = openai.chat.completions.create(
            model=config.AZURE_OPENAI_DEPLOYMENT_NAME,
            messages=[
                {"role": "system", "content": "You are an AI assistant that extracts structured data from SAE WCX program information."},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            max_tokens=4000
        )
        
        if not response.choices:
            print("Error: No response choices received from API")
            return []
            
        content = response.choices[0].message.content
        if not content:
            print("Error: Empty response content received from API")
            return []
            
        print(f"Response received, length: {len(content)} chars")
        print(f"Sample of response: {content[:200]}")
        
        # JSONデータを抽出（より堅牢な方法）
        try:
            # まず全体をJSONとして解析を試みる
            data = json.loads(content)
        except json.JSONDecodeError:
            # 失敗した場合、配列を探して解析
            json_start = content.find('[')
            json_end = content.rfind(']') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = content[json_start:json_end]
                try:
                    data = json.loads(json_str)
                except json.JSONDecodeError as e:
                    print(f"Failed to parse JSON response: {e}")
                    print(f"Problematic JSON: {json_str[:200]}...")
                    return []
            else:
                print("No valid JSON found in response")
                return []
        
        print(f"Successfully parsed JSON with {len(data)} records")
        if data:
            print(f"Sample record: {json.dumps(data[0], indent=2, ensure_ascii=False)[:500]}...")
        return data
            
    except Exception as e:
        print(f"Error calling Azure OpenAI API: {e}")
        return [] 