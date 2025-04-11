import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sqlite3
from db_handler import DatabaseHandler

# カラーパレット
COLOR_MAPPING = {
    '電動化技術': '#2C5282',
    '自動運転・ADAS': '#4A6FA5',
    '内燃機関技術': '#718096',
    '排出ガス制御': '#90CDF4',
    '車両開発': '#553C9A',
    '材料技術': '#805AD5',
    '衝突安全': '#B794F4',
    '車両ダイナミクス': '#D6BCFA',
    'パワートレイン': '#9F7AEA',
    '電装技術': '#667EEA',
    '製造技術': '#7F9CF5',
    '車体技術': '#A3BFFA',
    'NVH': '#C3DAFE',
    '信頼性/耐久性': '#EBF4FF',
    'その他': '#95A5A6'  # グレーを維持
}

# カテゴリの日本語マッピング
CATEGORY_MAPPING = {
    'Internal Combustion Engine': '内燃機関技術',
    'ADAS/AVS': '自動運転・ADAS',
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
    'Others': 'その他'
}

def translate_category(category):
    """カテゴリ名を日本語に変換"""
    return CATEGORY_MAPPING.get(category, category)

def translate_subcategory(subcategory):
    """サブカテゴリ名を日本語に変換"""
    return SUBCATEGORY_MAPPING.get(subcategory, subcategory)

def load_data():
    """データベースからデータを読み込む"""
    db = DatabaseHandler()
    with sqlite3.connect(db.db_path) as conn:
        query = """
        SELECT year, category, subcategory, COUNT(*) as count
        FROM sessions
        WHERE category IS NOT NULL
        GROUP BY year, category, subcategory
        ORDER BY year, category, subcategory
        """
        df = pd.read_sql_query(query, conn)
        
        # カテゴリとサブカテゴリを日本語に変換
        df['category_ja'] = df['category'].apply(translate_category)
        df['subcategory_ja'] = df['subcategory'].apply(translate_subcategory)
        
    return df

def create_category_distribution(df, selected_year=None, selected_category=None):
    """カテゴリー分布の円グラフを作成"""
    filtered_df = df.copy()
    if selected_year:
        filtered_df = filtered_df[filtered_df['year'] == selected_year]
    if selected_category:
        filtered_df = filtered_df[filtered_df['category_ja'] == selected_category]
    
    category_counts = filtered_df.groupby('category_ja')['count'].sum().reset_index()
    total = category_counts['count'].sum()
    category_counts['percentage'] = (category_counts['count'] / total * 100).round(1)
    
    # 6%以上のカテゴリのみテキストを表示
    category_counts['text'] = category_counts.apply(
        lambda x: f"{x['category_ja']}<br>{x['percentage']}%" if x['percentage'] >= 6 else '',
        axis=1
    )
    
    fig = px.pie(
        category_counts,
        values='count',
        names='category_ja',
        title=f'技術カテゴリ分布 ({selected_year if selected_year else "全年"}{", " + selected_category if selected_category else ""})',
        labels={'count': '論文数', 'category_ja': 'カテゴリ'},
        hole=0.3,
        color='category_ja',
        color_discrete_map=COLOR_MAPPING
    )
    
    # テキストの設定
    fig.update_traces(
        text=category_counts['text'],
        textposition='outside',
        textinfo='text',
        insidetextorientation='radial',
        hovertemplate='%{label}<br>論文数: %{value}<br>割合: %{percent:.1%}<extra></extra>'
    )
    
    return fig

def create_subcategory_bar(df, selected_year=None, selected_category=None):
    """サブカテゴリー別の棒グラフを作成"""
    filtered_df = df.copy()
    if selected_year:
        filtered_df = filtered_df[filtered_df['year'] == selected_year]
    if selected_category:
        filtered_df = filtered_df[filtered_df['category_ja'] == selected_category]
    
    subcategory_counts = filtered_df.groupby(['subcategory_ja', 'category_ja'])['count'].sum().reset_index()
    subcategory_counts = subcategory_counts.sort_values('count', ascending=True)
    
    fig = px.bar(
        subcategory_counts,
        x='count',
        y='subcategory_ja',
        orientation='h',
        title=f'サブカテゴリ論文数 ({selected_year if selected_year else "全年"}{", " + selected_category if selected_category else ""})',
        labels={'count': '論文数', 'subcategory_ja': 'サブカテゴリ'},
        color_discrete_sequence=['#2C5282']  # 単色（青系）を使用
    )
    return fig

def create_trend_line(df, selected_category=None):
    """カテゴリー別の年推移線グラフを作成"""
    filtered_df = df.copy()
    if selected_category:
        filtered_df = filtered_df[filtered_df['category_ja'] == selected_category]
    
    trend_df = filtered_df.groupby(['year', 'category_ja'])['count'].sum().reset_index()
    
    fig = px.line(
        trend_df,
        x='year',
        y='count',
        color='category_ja',
        title=f'技術トレンド推移{" - " + selected_category if selected_category else ""}',
        labels={'count': '論文数', 'year': '年', 'category_ja': 'カテゴリ'},
        color_discrete_map=COLOR_MAPPING
    )
    
    # 線の太さとマーカーの設定
    fig.update_traces(
        line=dict(width=2),
        marker=dict(size=8)
    )
    return fig

def main():
    st.set_page_config(page_title="SAE WCX分析ダッシュボード", layout="wide")
    st.title("SAE WCX分析ダッシュボード")
    
    # データの読み込み
    df = load_data()
    
    # フィルター
    col1, col2 = st.columns(2)
    with col1:
        years = sorted(df['year'].unique())
        selected_year = st.selectbox('年を選択', ['すべて'] + list(years))
    
    with col2:
        categories = sorted(df['category_ja'].unique())
        selected_category = st.selectbox('カテゴリを選択', ['すべて'] + list(categories))
    
    # 選択値の処理
    year_filter = None if selected_year == 'すべて' else selected_year
    category_filter = None if selected_category == 'すべて' else selected_category
    
    # グラフの表示
    col1, col2 = st.columns(2)
    
    with col1:
        st.plotly_chart(
            create_category_distribution(df, year_filter, category_filter),
            use_container_width=True
        )
    
    with col2:
        st.plotly_chart(
            create_subcategory_bar(df, year_filter, category_filter),
            use_container_width=True
        )
    
    # トレンドグラフ
    st.plotly_chart(create_trend_line(df, category_filter), use_container_width=True)

if __name__ == "__main__":
    main() 