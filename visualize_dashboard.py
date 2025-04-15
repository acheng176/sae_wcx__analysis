import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sqlite3
from db_handler import DatabaseHandler
import numpy as np
from datetime import datetime
import os
from dotenv import load_dotenv

# openai_insightsモジュールをインポート
try:
    from openai_insights import display_ai_insights
    insights_available = True
except ImportError:
    insights_available = False

# 環境変数の読み込み
load_dotenv()

# OpenAI APIキーが設定されているか確認
has_openai_config = all([
    os.getenv("AZURE_OPENAI_API_KEY"),
    os.getenv("AZURE_OPENAI_ENDPOINT"),
    os.getenv("AZURE_OPENAI_API_VERSION"),
    os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
])

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
    'IoT': 'IoT',  # 英語のまま
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
    'Human Factors': 'ヒューマンファクター',
    'Reliability/Durability': '信頼性/耐久性',
    'Racing Technology': 'レース技術',
    'Emissions Control': '排出ガス制御',
    'Manufacturing': '製造技術',
    'Materials': '材料技術',
    'Body Engineering': '車体工学',
    'NVH': 'NVH',  # 英語のまま
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

def create_category_distribution(df, selected_year=None, selected_categories=None):
    """カテゴリー分布の円グラフを作成（サイズ最適化版）"""
    filtered_df = df.copy()
    if selected_year:
        filtered_df = filtered_df[filtered_df['year'] == selected_year]
    if selected_categories:
        filtered_df = filtered_df[filtered_df['category_ja'].isin(selected_categories)]
    
    # カテゴリー別の集計
    category_counts = filtered_df.groupby('category_ja')['count'].sum().reset_index()
    total = category_counts['count'].sum()
    category_counts['percentage'] = (category_counts['count'] / total * 100).round(1)
    
    # パーセンテージでソート
    category_counts = category_counts.sort_values('percentage', ascending=False)
    
    # カラーリストを作成
    colors = [COLOR_MAPPING.get(cat, '#95A5A6') for cat in category_counts['category_ja']]
    
    # 単一の円グラフ（パーセンテージラベル付き）のみを作成
    fig = go.Figure(data=[go.Pie(
        labels=category_counts['category_ja'],
        values=category_counts['percentage'],
        hole=0.4,
        marker=dict(colors=colors),
        textposition='auto',
        texttemplate='%{value:.1f}%',  # パーセンテージを表示
        textinfo='text',  # テキストのみ表示
        hovertemplate="%{label}<br>%{value:.1f}%<extra></extra>",
        showlegend=True,
        sort=False
    )])
    
    # 2%未満のラベルを非表示にする
    fig.update_traces(
        textposition=['auto' if val >= 2 else 'none' for val in category_counts['percentage']]
    )
    
    # タイトルの設定
    title = '技術カテゴリ分布'
    if selected_year:
        title += f' ({selected_year}年)'
    if selected_categories and len(selected_categories) <= 3:
        title += f' - {", ".join(selected_categories)}'
    elif selected_categories and len(selected_categories) > 3:
        title += f' - {len(selected_categories)}カテゴリ選択中'
    
    fig.update_layout(
        title='あああ',
        title_font=dict(size=14),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.2,  # 凡例の位置を下に調整
            xanchor="center",
            x=0.5,
            font=dict(size=9),  # フォントサイズを小さく
            itemsizing='constant'
        ),
        height=400,  # 高さを小さく
        width=450,  # 幅を小さく
        margin=dict(
            t=30,  # 上の余白
            b=80,  # 下の余白（凡例のスペース）
            l=10,  # 左の余白
            r=10,  # 右の余白
            pad=4
        ),
        autosize=False  # 自動サイズ調整を無効化
    )
    
    return fig

def create_subcategory_bar(df, selected_year=None, selected_categories=None):
    """サブカテゴリーの棒グラフを作成（行間最適化版）"""
    filtered_df = df.copy()
    if selected_year:
        filtered_df = filtered_df[filtered_df['year'] == selected_year]
    if selected_categories:
        filtered_df = filtered_df[filtered_df['category_ja'].isin(selected_categories)]
    
    # サブカテゴリーごとの集計
    subcategory_counts = filtered_df.groupby('subcategory_ja')['count'].sum().reset_index()
    
    # 値が0のサブカテゴリーを除外
    subcategory_counts = subcategory_counts[subcategory_counts['count'] > 0]
    
    # 値で降順ソート
    subcategory_counts = subcategory_counts.sort_values('count', ascending=True)
    
    # 表示するサブカテゴリーの最大数を制限（オプション）
    max_items = 15
    if len(subcategory_counts) > max_items:
        subcategory_counts = subcategory_counts.tail(max_items)  # 上位15項目のみ表示
    
    # 棒グラフの作成
    fig = go.Figure(data=[
        go.Bar(
            x=subcategory_counts['count'],
            y=subcategory_counts['subcategory_ja'],
            orientation='h',
            text=subcategory_counts['count'],
            textposition='outside',
            hovertemplate="<b>%{y}</b><br>件数: %{x:,}<extra></extra>",
            marker=dict(color='#4A6FA5')
        )
    ])
    
    # タイトルの設定
    title = 'サブカテゴリー分布'
    if selected_year:
        title += f' ({selected_year}年)'
    if selected_categories and len(selected_categories) <= 3:
        title += f' - {", ".join(selected_categories)}'
    elif selected_categories and len(selected_categories) > 3:
        title += f' - {len(selected_categories)}カテゴリ選択中'
    
    # 表示するサブカテゴリー数に応じて高さを動的に調整
    bar_height = min(max(25 * len(subcategory_counts), 300), 500)  # 最小300px、最大500px
    
    fig.update_layout(
        title='あああ',
        title_font=dict(size=14),
        xaxis_title='件数',
        yaxis=dict(
            title='サブカテゴリー',
            tickfont=dict(size=10),  # Y軸のフォントサイズを小さく
            automargin=True
        ),
        height=bar_height,  # 動的に高さを調整
        width=450,  # 幅を指定
        margin=dict(
            t=30,  # 上の余白
            b=50,  # 下の余白
            l=180,  # 左の余白（サブカテゴリー名のスペース）
            r=10,  # 右の余白
            pad=4
        ),
        showlegend=False,
        yaxis_categoryorder='total ascending',  # カテゴリーを値の小さい順に並べる
        bargap=0.1,  # バー間のギャップを小さく
        uniformtext=dict(minsize=8, mode='hide'),  # テキストの最小サイズ
        autosize=False  # 自動サイズ調整を無効化
    )
    
    # バーチャートのテキストスタイルを調整
    fig.update_traces(
        texttemplate='%{text:,}',
        textfont=dict(size=9),  # テキストサイズを小さく
        textposition='outside'
    )
    
    return fig

def create_trend_line(df, selected_categories=None):
    """トレンドラインを作成"""
    # 年ごとの合計を計算
    yearly_total = df.groupby('year')['count'].sum().reset_index()
    
    # カテゴリーごとの年間データを計算し、構成比を算出
    category_yearly = df.groupby(['year', 'category_ja'])['count'].sum().reset_index()
    category_yearly = category_yearly.merge(yearly_total, on='year', suffixes=('', '_total'))
    category_yearly['share'] = category_yearly['count'] / category_yearly['count_total'] * 100
    
    # 前年比の変化を計算
    category_yearly = category_yearly.sort_values(['category_ja', 'year'])
    category_yearly['prev_share'] = category_yearly.groupby('category_ja')['share'].shift(1)
    category_yearly['yoy_change'] = (category_yearly['share'] - category_yearly['prev_share']).round(1)
    
    # トレンドスコアの計算
    # 1. 全体の変化の大きさ（絶対値）
    category_yearly['total_change'] = category_yearly.groupby('category_ja')['yoy_change'].transform('sum').abs()
    
    # 2. 変化の持続性（標準偏差）
    category_yearly['change_std'] = category_yearly.groupby('category_ja')['yoy_change'].transform('std')
    
    # 3. 平均シェア
    category_yearly['avg_share'] = category_yearly.groupby('category_ja')['share'].transform('mean')
    
    # 最終的なスコア計算
    # 変化の大きさ × 持続性 × シェアの重み付け
    category_scores = category_yearly.groupby('category_ja').agg({
        'total_change': 'first',
        'change_std': 'first',
        'avg_share': 'first'
    }).reset_index()
    
    # スコアの正規化
    category_scores['change_score'] = (category_scores['total_change'] / category_scores['total_change'].max())
    category_scores['consistency_score'] = (1 - category_scores['change_std'] / category_scores['change_std'].max())
    category_scores['share_score'] = (category_scores['avg_share'] / category_scores['avg_share'].max())
    
    # 総合スコアの計算（重み付け）
    category_scores['final_score'] = (
        category_scores['change_score'] * 0.4 +  # 変化の大きさ
        category_scores['consistency_score'] * 0.3 +  # 持続性
        category_scores['share_score'] * 0.3  # シェアの重み
    )
    
    # 変化の大きい上位10カテゴリーを選択
    top_categories = category_scores.nlargest(10, 'final_score')['category_ja'].tolist()
    
    # データをフィルタリング
    plot_data = category_yearly[category_yearly['category_ja'].isin(top_categories)]
    
    # グラフを作成
    fig = go.Figure()
    
    for category in top_categories:
        cat_data = plot_data[plot_data['category_ja'] == category]
        # 前年比の変化に応じて色を設定
        yoy_colors = []
        for change in cat_data['yoy_change']:
            if pd.isna(change):
                yoy_colors.append('#666666')  # 灰色（最初の年）
            elif change > 0:
                yoy_colors.append('#22C55E')  # 緑色（増加）
            else:
                yoy_colors.append('#EF4444')  # 赤色（減少）
        
        fig.add_trace(go.Scatter(
            x=cat_data['year'],
            y=cat_data['share'],
            name=category,
            mode='lines+markers',
            line=dict(color=COLOR_MAPPING.get(category, '#95A5A6')),
            hovertemplate="<b>%{text}</b><br>年: %{x}<br>構成比: %{y:.1f}%<br>前年比: <span style='color: %{customdata[1]}'>%{customdata[0]}</span>pt<extra></extra>",
            text=[category] * len(cat_data),
            customdata=list(zip(
                cat_data['yoy_change'].fillna('-').astype(str),
                yoy_colors
            ))
        ))
    
    # レイアウトを設定
    fig.update_layout(
        title='あああ',
        title_font=dict(size=14),
        xaxis=dict(
            tickmode='array',
            ticktext=sorted(df['year'].unique()),
            tickvals=sorted(df['year'].unique()),
            dtick=1,
            showgrid=True,
            gridwidth=1,
            gridcolor='#E2E8F0'
        ),
        yaxis_title='構成比 (%)',
        height=350,  # 高さを小さく
        width=600,  # 幅を指定
        margin=dict(t=30, b=50, l=50, r=50),
        showlegend=True,
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=-0.3,
            xanchor='center',
            x=0.5,
            font=dict(size=9)
        ),
        hovermode='closest'
    )
    
    # サブタイトルを作成
    subtitle = f"""
        <div style='text-align: center; color: #666666; font-size: 8px; margin-top: 10px;'>
            ※ 選定基準：全体割合の変化の大きさ（40%の重み）と全体に占めるシェアの大きさ（30%の重み）の合計スコアで上位10カテゴリーを表示<br>
        </div>
    """
    
    return fig, subtitle

def calculate_yoy_changes(df):
    """カテゴリーごとの前年比変化率を計算"""
    # 年ごとのカテゴリー別集計
    yearly_counts = df.groupby(['year', 'category_ja'])['count'].sum().reset_index()
    
    # 各年の総数を計算
    yearly_totals = yearly_counts.groupby('year')['count'].sum().reset_index()
    yearly_counts = yearly_counts.merge(yearly_totals, on='year', suffixes=('', '_total'))
    
    # 構成比を計算
    yearly_counts['share'] = (yearly_counts['count'] / yearly_counts['count_total'] * 100).round(2)
    
    # 最新年を取得
    latest_year = yearly_counts['year'].max()
    previous_year = latest_year - 1
# 最新年と前年のデータを抽出
    latest_data = yearly_counts[yearly_counts['year'] == latest_year][['category_ja', 'share']]
    previous_data = yearly_counts[yearly_counts['year'] == previous_year][['category_ja', 'share']]
    
    # 前年比の変化を計算
    changes = latest_data.merge(
        previous_data,
        on='category_ja',
        suffixes=('_current', '_prev'),
        how='left'
    )
    
    # 変化ポイントを計算
    changes['change_points'] = (changes['share_current'] - changes['share_prev']).round(1)
    
    # 上位10件と下位10件を抽出
    top_gainers = changes.nlargest(10, 'change_points')[['category_ja', 'change_points']]
    top_losers = changes.nsmallest(10, 'change_points')[['category_ja', 'change_points']]
    
    return top_gainers, top_losers

def display_yoy_changes(df, top_gainers, top_losers):
    """構成比の変化を表示"""
    # ランキング表示用に2カラムに分割
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
            <div style='font-size: 14px; color: #333333; font-weight: bold; margin-bottom: 5px;'>注目度上昇</div>
            <div style='font-size: 12px; color: #666666; font-weight: normal; margin-bottom: 10px; border-bottom: 2px solid #22C55E; padding-bottom: 6px;'>前年からの構成比変化（%ポイント）</div>
        """, unsafe_allow_html=True)
        
        for i, (category, change) in enumerate(zip(top_gainers['category_ja'], top_gainers['change_points'])):
            # トップ3の場合は薄い緑色の背景を追加
            bg_color = '#F0FDF4' if i < 3 else 'transparent'
            # トップ3の場合は太字、それ以外は通常の太さ
            font_weight = 'bold' if i < 3 else 'normal'
            st.markdown(f"""
            <div style='display: flex; align-items: center; margin: 1px 0; padding: 2px; background-color: {bg_color}; border-radius: 4px;'>
                <div style='background-color: #DCF8E7; border-radius: 50%; width: 24px; height: 24px; 
                          display: flex; align-items: center; justify-content: center; margin-right: 8px;'>
                    <span style='color: #22C55E; font-weight: bold; font-size: 12px;'>{i + 1}</span>
                </div>
                <div style='flex-grow: 1; display: flex; justify-content: space-between; align-items: center;'>
                    <div style='font-size: 14px; color: #333333;'>{category}</div>
                    <div style='color: #22C55E; font-weight: {font_weight}; font-size: 14px;'>+{change}pt</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
            <div style='font-size: 14px; color: #333333; font-weight: bold; margin-bottom: 5px;'>注目度減少</div>
            <div style='font-size: 12px; color: #666666; font-weight: normal; margin-bottom: 10px; border-bottom: 2px solid #EF4444; padding-bottom: 6px;'>前年からの構成比変化（%ポイント）</div>
        """, unsafe_allow_html=True)
        
        for i, (category, change) in enumerate(zip(top_losers['category_ja'], top_losers['change_points'])):
            # トップ3の場合は薄い赤色の背景を追加
            bg_color = '#FEF2F2' if i < 3 else 'transparent'
            # トップ3の場合は太字、それ以外は通常の太さ
            font_weight = 'bold' if i < 3 else 'normal'
            st.markdown(f"""
            <div style='display: flex; align-items: center; margin: 1px 0; padding: 2px; background-color: {bg_color}; border-radius: 4px;'>
                <div style='background-color: #FEE2E2; border-radius: 50%; width: 24px; height: 24px; 
                          display: flex; align-items: center; justify-content: center; margin-right: 8px;'>
                    <span style='color: #EF4444; font-weight: bold; font-size: 12px;'>{i + 1}</span>
                </div>
                <div style='flex-grow: 1; display: flex; justify-content: space-between; align-items: center;'>
                    <div style='font-size: 14px; color: #333333;'>{category}</div>
                    <div style='color: #EF4444; font-weight: {font_weight}; font-size: 14px;'>{change}pt</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    # 区切り線を追加
    st.markdown("""
        <hr style='margin: 20px 0; border: none; height: 1px; background-color: #E2E8F0;'>
    """, unsafe_allow_html=True)
    
    # トレンドグラフを表示（フル幅）
    fig, subtitle = create_trend_line(df, None)
    st.plotly_chart(fig, use_container_width=True, config={
        'displayModeBar': False,
        'responsive': True
    })
    st.markdown(subtitle, unsafe_allow_html=True)
    
    # 区切り線を追加
    st.markdown("""
        <hr style='margin: 20px 0; border: none; height: 1px; background-color: #E2E8F0;'>
    """, unsafe_allow_html=True)

def display_ai_button():
    """AIボタンを表示"""
    if not insights_available:
        return False
    
    button_style = """
    <style>
    div.stButton > button {
        background-color: #4F46E5;
        color: white;
        font-weight: bold;
        padding: 0.6rem 1rem;
        border-radius: 0.5rem;
        border: none;
        width: 100%;
        margin-top: 10px;
    }
    div.stButton > button:hover {
        background-color: #4338CA;
    }
    </style>
    """
    st.markdown(button_style, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        if has_openai_config:
            show_ai_report = st.button('AIによる分析レポート生成', use_container_width=True)
            return show_ai_report
        else:
            st.info("AIによる分析レポートを使用するには、Azure OpenAI APIの設定が必要です。.envファイルにAPIキーとエンドポイントを設定してください。")
            return False

def main():
    st.set_page_config(
        page_title=" SAE WCX 技術トレンド分析",
        page_icon="🚗",
        layout="wide"
    )
    
    # ヘッダーの配置
    header_col1, header_col2 = st.columns([3, 1])
    with header_col2:
        try:
            st.image("data/Honda_Logo.svg.webp", width=150)
        except:
            st.write("Hondaロゴを表示するには、data/Honda_Logo.svg.webpが必要です")
    
    with header_col1:
        st.title("Honda SAE WCX 技術トレンド分析")
        st.markdown("""
            <div style='
                color: #666666;
                font-size: 16px;
                margin: -5px 0 25px 2px;
                font-family: sans-serif;
                line-height: 1.7;
                letter-spacing: 0.3px;
            '>
                SAE WCXにおける技術発表論文の分析に基づく自動車業界の技術動向分析・重点領域の可視化
            </div>
            <hr style='margin: 0 0 30px 0; border: none; height: 1px; background-color: #E2E8F0;'>
        """, unsafe_allow_html=True)
    
    # データの読み込み
    df = load_data()
    
    # AIボタンの表示
    show_ai_report = display_ai_button()
    
    # AIレポートの表示（ボタンがクリックされた場合）
    if show_ai_report:
        try:
            # 前年比の変化率を計算
            top_gainers, top_losers = calculate_yoy_changes(df)
            
            # AIレポートを表示
            display_ai_insights(df, top_gainers, top_losers)
            
            # 区切り線を追加
            st.markdown("""
                <hr style='margin-top: 30px; margin-bottom: 30px; border: none; height: 1px; background-color: #E2E8F0;'>
            """, unsafe_allow_html=True)
        except Exception as e:
            st.error(f"AIレポート生成中にエラーが発生しました: {str(e)}")
    
    # 前年比の変化率を計算と表示
    top_gainers, top_losers = calculate_yoy_changes(df)
    display_yoy_changes(df, top_gainers, top_losers)
    
    # 区切り線を追加
    st.markdown("""
        <hr style='margin: 20px 0; border: none; height: 1px; background-color: #E2E8F0;'>
    """, unsafe_allow_html=True)
    
    # フィルター
    col1, col2 = st.columns(2)
    with col1:
        years = sorted(df['year'].unique())
        selected_year = st.selectbox('表示年を選択', ['すべて'] + list(years))
    
    with col2:
        # カテゴリごとの総数を計算してソート
        category_totals = df.groupby('category_ja')['count'].sum().sort_values(ascending=False)
        categories = category_totals.index.tolist()
        selected_categories = st.multiselect('カテゴリを選択（複数選択可）', categories)
    
    # フィルタの下に区切り線を追加
    st.markdown("""
        <hr style='margin: 20px 0; border: none; height: 1px; background-color: #E2E8F0;'>
    """, unsafe_allow_html=True)
    
    # 選択値の処理
    year_filter = None if selected_year == 'すべて' else selected_year
    category_filter = None if not selected_categories else selected_categories
    
    # グラフの表示
    display_data_visualizations(df, year_filter, category_filter)
    
    # 区切り線を追加
    st.markdown("""
        <hr style='margin-top: 30px; margin-bottom: 30px; border: none; height: 1px; background-color: #E2E8F0;'>
    """, unsafe_allow_html=True)
    
    # フッター
    st.markdown("""
        <div style='text-align: center; color: #718096; padding: 20px; font-size: 14px;'>
            <p>© 2025 Honda R&D Co., Ltd. | 最終更新: 2025年4月</p>
        </div>
    """, unsafe_allow_html=True)

def display_data_visualizations(df, year_filter, category_filter):
    """データ可視化セクションを表示"""
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
            <div style='font-size: 14px; color: #333333; font-weight: bold; margin-bottom: 5px;'>カテゴリ分布</div>
            <div style='font-size: 12px; color: #666666; font-weight: normal; margin-bottom: 10px;'>全体に占める各カテゴリの割合</div>
        """, unsafe_allow_html=True)
        
        # 表示用フィルター情報
        filter_info = ""
        if year_filter:
            filter_info += f"【{year_filter}年】"
        if category_filter and len(category_filter) <= 3:
            filter_info += f"【{', '.join(category_filter)}】"
        elif category_filter:
            filter_info += f"【{len(category_filter)}カテゴリ選択中】"
        
        if filter_info:
            st.markdown(f"<div style='text-align: center; color: #666666; font-size: 12px; margin-bottom: 10px;'>{filter_info}</div>", unsafe_allow_html=True)
        
        # カテゴリ分布の円グラフを表示
        cat_fig = create_category_distribution(df, year_filter, category_filter)
        st.plotly_chart(
            cat_fig,
            use_container_width=True,
            config={
                'displayModeBar': False,
                'responsive': True
            }
        )
    
    with col2:
        st.markdown("""
            <div style='font-size: 14px; color: #333333; font-weight: bold; margin-bottom: 5px;'>サブカテゴリ分布</div>
            <div style='font-size: 12px; color: #666666; font-weight: normal; margin-bottom: 10px;'>各サブカテゴリの件数</div>
        """, unsafe_allow_html=True)
        
        # 表示用フィルター情報（同じ内容を表示）
        if filter_info:
            st.markdown(f"<div style='text-align: center; color: #666666; font-size: 12px; margin-bottom: 10px;'>{filter_info}</div>", unsafe_allow_html=True)
        
        # サブカテゴリ分布の棒グラフを表示
        sub_fig = create_subcategory_bar(df, year_filter, category_filter)
        st.plotly_chart(
            sub_fig,
            use_container_width=True,
            config={
                'displayModeBar': False,
                'responsive': True
            }
        )

if __name__ == "__main__":
    main()