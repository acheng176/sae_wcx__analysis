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

def categorize_session(overview, title):
    """セッションをカテゴリーとサブカテゴリーに分類する"""
    try:
        setup_azure_openai()
        prompt = f"""
Categorize the following automotive technical session based on its overview and title.

Overview: {overview}
Title: {title}

Main Categories (Choose exactly one):
- Internal Combustion Engine (内燃機関): Engine design, combustion, performance, emissions
- ADAS/AVS: Advanced Driver Assistance Systems, Autonomous Vehicle Systems
- Electrification (電動化): Electric powertrains, motors, power electronics
- Emissions Control (排気処理): Exhaust treatment, catalysts, emission reduction
- Vehicle Development (車両開発): Overall vehicle design and development
- Powertrain (駆動系): Transmission, driveline, powertrain integration
- Materials (材料): Advanced materials, composites, metallurgy
- Crash Safety (衝突安全): Passive safety, crash testing, occupant protection
- Vehicle Dynamics (ビークルダイナミクス): Handling, stability, ride comfort
- NVH: Noise, Vibration, and Harshness
- Reliability/Durability (信頼性/耐久性): Testing, validation, lifecycle
- Manufacturing (製造技術): Production processes, automation
- Body Engineering (車体系): Body structure, aerodynamics
- Electronics (電装): Vehicle electronics, sensors, ECUs
- Human Factors (人工): HMI, ergonomics, user experience
- Racing Technology (レース): Motorsports, racing applications
- Others (その他): Topics not covered above

Sub Categories (Choose one or none):
- Environmental Technology (環境): Sustainability, eco-friendly solutions
- AI/Machine Learning (AI, 機械学習): Artificial intelligence applications
- Cybersecurity: Vehicle and system security
- IoT: Connected vehicle technology
- HVAC (空調): Heating, ventilation, air conditioning
- Alternative Fuels (新燃料): Non-traditional fuel technologies
- Battery Technology (電池): Energy storage, battery management
- Connectivity (コネクティビティ): V2X, communication systems
- Cooling Systems (冷却): Thermal management
- Lubrication (潤滑): Tribology, lubrication systems
- Software Defined Vehicle: Software architecture, OTA
- Recycling (リサイクル): Material recovery, circular economy
- Hydrogen Technology (水素): Fuel cells, hydrogen infrastructure
- Ammonia Technology (アンモニア): Ammonia as fuel or energy carrier

Output Format:
{
    "category": "chosen main category (English)",
    "subcategory": "chosen sub category (English) or empty string if none applies"
}

Rules:
1. Always choose exactly one main category
2. Choose at most one sub category (can be empty if none applies)
3. Base the categorization on both overview and title content
4. If the content is unclear, use "Others" as the main category
5. Return category names in English
"""
        response = openai.ChatCompletion.create(
            deployment_id=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
            messages=[
                {"role": "system", "content": "You are a technical categorization assistant specializing in automotive engineering and technology."},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            max_tokens=150
        )

        if response.choices:
            content = response.choices[0].message.content.strip()
            result = json.loads(content)
            return result["category"], result.get("subcategory", "")
    except Exception as e:
        print(f"Warning: カテゴリー分類中にエラー: {e}")
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