import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sqlite3
from db_handler import DatabaseHandler
import numpy as np

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
    
    # パーセンテージでソート
    category_counts = category_counts.sort_values('percentage', ascending=False)
    
    # カラーリストを作成
    colors = [COLOR_MAPPING.get(cat, '#95A5A6') for cat in category_counts['category_ja']]
    
    # パイチャートの作成
    fig = go.Figure(data=[go.Pie(
        labels=category_counts['category_ja'],
        values=category_counts['count'],
        hole=0.4,
        marker=dict(colors=colors),
        textinfo='none',  # テキストを非表示（外部注釈を使用するため）
        hovertemplate="%{label}<br>%{percent:.1%}<br>%{value:,}件<extra></extra>",
        showlegend=True
    )])
    
    # 注釈を追加
    annotations = []
    cumsum = 0
    
    for idx, row in category_counts.iterrows():
        percentage = row['percentage']
        # 現在のセグメントの中心角度を計算
        start_angle = 2 * np.pi * (cumsum / total)
        end_angle = 2 * np.pi * ((cumsum + row['count']) / total)
        angle = (start_angle + end_angle) / 2
        
        # 数学的な角度からPlotlyの座標系に変換
        adjusted_angle = -angle + np.pi/2
        
        if percentage >= 6:  # 6%以上のカテゴリには外部ラベルを表示
            # ラベルの位置（パイの外側）
            radius_factor = 0.8  # 中心から見た時の位置（1よりも小さい値にして円の近くに表示）
            x_pos = radius_factor * np.cos(adjusted_angle)
            y_pos = radius_factor * np.sin(adjusted_angle)
            
            # アンカーポイント（パイの上）
            inner_radius = 0.6  # パイ上の位置
            x_anchor = inner_radius * np.cos(adjusted_angle)
            y_anchor = inner_radius * np.sin(adjusted_angle)
            
            annotations.append(dict(
                x=x_pos,
                y=y_pos,
                text=f"{row['category_ja']}",
                showarrow=True,
                arrowhead=2,
                arrowsize=1,
                arrowwidth=1,
                arrowcolor='#888888',
                ax=x_anchor,
                ay=y_anchor,
                font=dict(size=10, color='black'),
                bgcolor='rgba(255, 255, 255, 0.8)',
                bordercolor='#cccccc',
                borderwidth=1,
                borderpad=2,
                xanchor='center',
                yanchor='middle'
            ))
        
        # 2%以上のカテゴリにはパーセントを表示
        if percentage >= 2:
            # パイ上のパーセント表示位置を調整
            radius_factor = 0.65  # ドーナツ中心からの距離を調整
            x_pos = radius_factor * np.cos(adjusted_angle)
            y_pos = radius_factor * np.sin(adjusted_angle)
            
            annotations.append(dict(
                x=x_pos,
                y=y_pos,
                text=f"{percentage:.1f}%",
                showarrow=False,
                font=dict(size=10, color='black', family="Arial, sans-serif", weight="bold"),
                xanchor='center',
                yanchor='middle',
                bgcolor='rgba(255, 255, 255, 0.7)',  # 背景を少し透明な白に
                borderpad=2  # テキストの周りのパディングを追加
            ))
        
        cumsum += row['count']
    
    fig.update_layout(
        title='技術カテゴリ分布',
        annotations=annotations,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="top",  # 凡例を上部に配置
            y=-0.1,  # グラフの下に配置
            xanchor="center",
            x=0.5,
            font=dict(size=10),
            itemwidth=40,  # 凡例アイテムの幅を小さく
            itemsizing="constant"  # 凡例のアイコンサイズを固定
        ),
        height=500,  # グラフの高さを減らす
        width=550,   # グラフの幅を減らす
        margin=dict(
            t=50,    # 上部余白
            b=150,   # 下部余白（凡例用に十分なスペース）
            l=30,    # 左余白
            r=30,    # 右余白
            pad=0    # 内部パディング
        )
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
    
    # 各年のトップ5カテゴリを特定
    top_categories = (
        trend_df.groupby('category_ja')['count']
        .sum()
        .sort_values(ascending=False)
        .head(5)
        .index
        .tolist()
    )
    
    # トップ5とその他で色分け
    trend_df['color_group'] = trend_df['category_ja'].apply(
        lambda x: x if x in top_categories else 'その他'
    )
    
    fig = go.Figure()
    
    # トップ5カテゴリを個別に表示
    for category in top_categories:
        cat_data = trend_df[trend_df['category_ja'] == category]
        fig.add_trace(go.Scatter(
            x=cat_data['year'],
            y=cat_data['count'],
            name=category,
            mode='lines+markers',
            line=dict(width=3),
            marker=dict(size=8),
            line_color=COLOR_MAPPING.get(category)
        ))
    
    # その他のカテゴリを薄い色で表示
    other_data = trend_df[~trend_df['category_ja'].isin(top_categories)]
    for category in other_data['category_ja'].unique():
        cat_data = other_data[other_data['category_ja'] == category]
        fig.add_trace(go.Scatter(
            x=cat_data['year'],
            y=cat_data['count'],
            name=category,
            mode='lines',
            line=dict(width=1, color='rgba(200,200,200,0.3)'),
            showlegend=False
        ))
    
    fig.update_layout(
        title=f'技術トレンド推移 - トップ5カテゴリ{" - " + selected_category if selected_category else ""}',
        xaxis_title='年',
        yaxis_title='論文数',
        hovermode='x unified'
    )
    
    return fig

def create_trend_area(df, selected_category=None):
    """カテゴリー別の年推移積み上げ面グラフを作成"""
    filtered_df = df.copy()
    if selected_category:
        filtered_df = filtered_df[filtered_df['category_ja'] == selected_category]
    
    trend_df = filtered_df.groupby(['year', 'category_ja'])['count'].sum().reset_index()
    
    fig = px.area(
        trend_df,
        x='year',
        y='count',
        color='category_ja',
        title=f'技術カテゴリの構成比推移{" - " + selected_category if selected_category else ""}',
        labels={'count': '論文数', 'year': '年', 'category_ja': 'カテゴリ'},
        color_discrete_map=COLOR_MAPPING
    )
    
    fig.update_layout(
        hovermode='x unified'
    )
    
    return fig

def calculate_yoy_changes(df):
    """前年比の構成比率の変化を計算"""
    # 年とカテゴリでグループ化
    yearly_counts = df.groupby(['year', 'category_ja'])['count'].sum().reset_index()
    
    # 各年の総論文数を計算
    yearly_totals = yearly_counts.groupby('year')['count'].sum().reset_index()
    yearly_counts = pd.merge(yearly_counts, yearly_totals, on='year', suffixes=('', '_total'))
    
    # 構成比率を計算
    yearly_counts['proportion'] = (yearly_counts['count'] / yearly_counts['count_total'] * 100).round(1)
    
    # 前年のデータを結合
    yearly_counts['prev_year'] = yearly_counts['year'] - 1
    changes = pd.merge(
        yearly_counts,
        yearly_counts[['year', 'category_ja', 'proportion']],
        left_on=['prev_year', 'category_ja'],
        right_on=['year', 'category_ja'],
        suffixes=('', '_prev')
    )
    
    # 構成比の変化を計算
    changes['change_points'] = (changes['proportion'] - changes['proportion_prev']).round(1)
    
    # 最新年のデータのみを抽出
    latest_year = changes['year'].max()
    latest_changes = changes[changes['year'] == latest_year]
    
    # TOP5を取得
    top_gainers = latest_changes.nlargest(5, 'change_points')[['category_ja', 'change_points']]
    top_losers = latest_changes.nsmallest(5, 'change_points')[['category_ja', 'change_points']]
    
    return top_gainers, top_losers

def display_yoy_changes(top_gainers, top_losers):
    """構成比の変化を表示"""
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
            <h3 style='color: #22C55E; margin-top: 0; margin-bottom: 20px; font-size: 20px; border-bottom: 2px solid #22C55E; padding-bottom: 10px;'>注目度上昇 TOP5<span style='font-size: 14px;'>（前年比構成比変化）</span></h3>
        """, unsafe_allow_html=True)
        
        for i, (category, change) in enumerate(zip(top_gainers['category_ja'], top_gainers['change_points'])):
            st.markdown(f"""
            <div style='display: flex; align-items: center; margin: 10px 0;'>
                <div style='background-color: #DCF8E7; border-radius: 50%; width: 32px; height: 32px; 
                          display: flex; align-items: center; justify-content: center; margin-right: 15px;'>
                    <span style='color: #22C55E; font-weight: bold;'>{i + 1}</span>
                </div>
                <div style='flex-grow: 1; display: flex; justify-content: space-between; align-items: center;'>
                    <div style='font-size: 16px; color: #333333;'>{category}</div>
                    <div style='color: #22C55E; font-weight: bold; font-size: 18px;'>+{change}%ポイント</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
            <h3 style='color: #EF4444; margin-top: 0; margin-bottom: 20px; font-size: 20px; border-bottom: 2px solid #EF4444; padding-bottom: 10px;'>注目度減少 TOP5<span style='font-size: 14px;'>（前年比構成比変化）</span></h3>
        """, unsafe_allow_html=True)
        
        for i, (category, change) in enumerate(zip(top_losers['category_ja'], top_losers['change_points'])):
            st.markdown(f"""
            <div style='display: flex; align-items: center; margin: 10px 0;'>
                <div style='background-color: #FEE2E2; border-radius: 50%; width: 32px; height: 32px; 
                          display: flex; align-items: center; justify-content: center; margin-right: 15px;'>
                    <span style='color: #EF4444; font-weight: bold;'>{i + 1}</span>
                </div>
                <div style='flex-grow: 1; display: flex; justify-content: space-between; align-items: center;'>
                    <div style='font-size: 16px; color: #333333;'>{category}</div>
                    <div style='color: #EF4444; font-weight: bold; font-size: 18px;'>{change}%ポイント</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    # 区切り線を追加
    st.markdown("""
        <hr style='margin-top: 30px; margin-bottom: 30px; border: none; height: 1px; background-color: #E2E8F0;'>
    """, unsafe_allow_html=True)

def display_category_distribution(df):
    """カテゴリの分布を表示"""
    # カテゴリごとの論文数を計算
    category_counts = df.groupby('category_ja')['count'].sum().sort_values(ascending=False)
    
    # カテゴリに対応する色のリストを作成
    colors = [COLOR_MAPPING.get(category, '#95A5A6') for category in category_counts.index]
    
    # 円グラフを作成
    fig = go.Figure(data=[go.Pie(
        labels=category_counts.index,
        values=category_counts.values,
        hole=.4,
        marker_colors=colors  # 辞書ではなく、リストを使用
    )])
    
    # レイアウトの設定
    fig.update_layout(
        title='技術カテゴリ分布',
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.5,
            xanchor="center",
            x=0.5
        ),
        height=500
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # 区切り線を追加
    st.markdown("""
        <hr style='margin-top: 30px; margin-bottom: 30px; border: none; height: 1px; background-color: #E2E8F0;'>
    """, unsafe_allow_html=True)

def display_subcategory_distribution(df):
    """サブカテゴリごとの論文数を表示"""
    # サブカテゴリごとの論文数を計算
    subcategory_counts = df.groupby('subcategory_ja')['count'].sum().sort_values(ascending=False)
    
    # 棒グラフを作成
    fig = go.Figure(data=[go.Bar(
        x=subcategory_counts.values,
        y=subcategory_counts.index,
        orientation='h',
        marker_color='#4A90E2'
    )])
    
    # レイアウトの設定
    fig.update_layout(
        title='サブカテゴリ論文数',
        xaxis_title='論文数',
        yaxis_title='サブカテゴリ',
        height=800,
        showlegend=False,
        yaxis={'categoryorder':'total ascending'}
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # 区切り線を追加
    st.markdown("""
        <hr style='margin-top: 30px; margin-bottom: 30px; border: none; height: 1px; background-color: #E2E8F0;'>
    """, unsafe_allow_html=True)

def main():
    st.set_page_config(
        page_title="SAE WCX分析ダッシュボード",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
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
    
    # 前年比の変化率を計算と表示
    top_gainers, top_losers = calculate_yoy_changes(df)
    display_yoy_changes(top_gainers, top_losers)
    
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
    
    # 区切り線を追加
    st.markdown("""
        <hr style='margin-top: 30px; margin-bottom: 30px; border: none; height: 1px; background-color: #E2E8F0;'>
    """, unsafe_allow_html=True)
    
    # トレンドグラフ
    st.plotly_chart(create_trend_line(df, category_filter), use_container_width=True)
    
    # 区切り線を追加
    st.markdown("""
        <hr style='margin-top: 30px; margin-bottom: 30px; border: none; height: 1px; background-color: #E2E8F0;'>
    """, unsafe_allow_html=True)
    
    st.plotly_chart(create_trend_area(df, category_filter), use_container_width=True)
    
    # 区切り線を追加
    st.markdown("""
        <hr style='margin-top: 30px; margin-bottom: 30px; border: none; height: 1px; background-color: #E2E8F0;'>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main() 