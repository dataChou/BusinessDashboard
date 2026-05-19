import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="宠物医院经营分析看板", layout="wide", page_icon="🐾")

# ------------------------------
# 1. 加载数据
# ------------------------------
@st.cache_data
def load_data():
    df = pd.read_csv('pet_hospital_data.csv', encoding='utf-8-sig')
    df['日期'] = pd.to_datetime(df['日期'])
    return df

df = load_data()
today = datetime(2026, 5, 19)

# ------------------------------
# 2. 客户指标 & RFM
# ------------------------------
last_visit = df.groupby('宠主ID')['日期'].max().reset_index()
last_visit['R'] = last_visit['日期'].apply(lambda x: (today - x).days)

freq = df.groupby('宠主ID').size().reset_index(name='F')
amount = df.groupby('宠主ID')['消费金额'].sum().reset_index(name='M')

customer_data = last_visit.merge(freq, on='宠主ID').merge(amount, on='宠主ID')
customer_data = customer_data.merge(df[['宠主ID', '宠主姓名']].drop_duplicates(), on='宠主ID')

# 分层函数
def classify(r):
    if r <= 30:
        return '高价值客户'
    elif r <= 90:
        return '活跃客户'
    elif r <= 180:
        return '沉睡客户'
    else:
        return '流失客户'

customer_data['分层'] = customer_data['R'].apply(classify)

# ------------------------------
# 3. KPI 指标
# ------------------------------
total_customers = customer_data['宠主ID'].nunique()
total_revenue = df['消费金额'].sum()
total_orders = len(df)
lost_customers = len(customer_data[customer_data['R'] > 180])
lost_rate = lost_customers / total_customers
avg_ticket = total_revenue / total_orders

# ------------------------------
# 4. 服务项目分析
# ------------------------------
service_stats = df.groupby('服务项目').agg(
    总金额=('消费金额', 'sum'),
    订单数=('宠主ID', 'count'),
    客单价=('消费金额', 'mean')
).round(2).sort_values('总金额', ascending=False)

service_stats['金额占比'] = (service_stats['总金额'] / service_stats['总金额'].sum() * 100).round(1)

# ------------------------------
# 5. 医生绩效 (修复：直接命名列)
# ------------------------------
doctor_stats = df.groupby('医生').agg(
    接诊量=('宠主ID', 'count'),
    总业绩=('消费金额', 'sum'),
    客单价=('消费金额', 'mean')
).round(2).sort_values('接诊量', ascending=False)

# ------------------------------
# 6. 月度趋势
# ------------------------------
df['月份'] = df['日期'].dt.to_period('M').astype(str)
monthly = df.groupby('月份').agg(
    营收=('消费金额', 'sum'),
    订单数=('宠主ID', 'count')
).reset_index()

# ------------------------------
# 7. UI 布局
# ------------------------------
st.title("🐾 宠物医院经营分析看板")
st.caption(f"数据更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}")

# KPI 卡片
col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.metric("🐕 总客户数", f"{total_customers:,}")
with col2:
    st.metric("💰 总营收", f"{total_revenue/10000:.1f}万")
with col3:
    st.metric("⚠️ 流失率", f"{lost_rate*100:.1f}%")
with col4:
    st.metric("💳 客单价", f"{avg_ticket:.0f}元")
with col5:
    st.metric("📋 总订单数", f"{total_orders:,}")

st.divider()

# 第一行：客户分层 & 服务项目
col1, col2 = st.columns(2)
with col1:
    st.subheader("📊 客户分层分析")
    layer_counts = customer_data['分层'].value_counts().reindex(['高价值客户', '活跃客户', '沉睡客户', '流失客户'])
    fig = px.pie(values=layer_counts.values, names=layer_counts.index,
                 title="客户分层占比",
                 color_discrete_sequence=['#2ECC71', '#3498DB', '#F39C12', '#E74C3C'])
    fig.update_traces(textposition='inside', textinfo='percent+label')
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("🏥 服务项目盈利分析")
    fig = px.bar(service_stats, x=service_stats.index, y='总金额',
                 title="各项目营收（元）",
                 color=service_stats.index,
                 color_discrete_sequence=['#1ABC9C', '#2ECC71', '#3498DB', '#9B59B6', '#E74C3C'])
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# 第二行：医生绩效 & 客单价
col1, col2 = st.columns(2)
with col1:
    st.subheader("👨‍⚕️ 医生绩效排名")
    fig = px.bar(doctor_stats, x=doctor_stats.index, y='接诊量',
                 title="医生接诊量排行",
                 color=doctor_stats.index,
                 color_discrete_sequence=px.colors.sequential.Blues_r)
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("💰 各项目客单价对比")
    item_price = df.groupby('服务项目')['消费金额'].mean().round(0).sort_values()
    fig = px.bar(x=item_price.values, y=item_price.index, orientation='h',
                 title="服务项目客单价（元）",
                 color=item_price.values,
                 color_continuous_scale='Viridis')
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# ------------------------------
# 8. 流失客户列表（修复关键点）
# ------------------------------
st.subheader(f"⚠️ 流失客户预警（超过6个月未消费）- 共{lost_customers}人")

# 直接从 customer_data 中筛选流失客户，并选择存在的列
lost_list = customer_data[customer_data['R'] > 180].sort_values('R', ascending=False)

# 选择列（不使用可能缺失的“最近消费金额”，改用总消费金额 M）
# 显示：宠主ID, 宠主姓名, 最后消费日期, 总消费金额(M), 消费次数(F), 未登录天数(R)
lost_display = lost_list[['宠主ID', '宠主姓名', '日期', 'M', 'F', 'R']].head(100)

# 重命名为中文表头
lost_display.columns = ['宠主ID', '宠主姓名', '最近消费日期', '总消费金额', '总消费次数', '未登录天数']

st.dataframe(lost_display, use_container_width=True)

if lost_customers > 100:
    st.caption(f"仅显示前100人，共{lost_customers}人")

st.divider()

# ------------------------------
# 9. 月度趋势
# ------------------------------
st.subheader("📈 月度营收趋势")
fig = go.Figure()
fig.add_trace(go.Scatter(x=monthly['月份'], y=monthly['营收'],
                         mode='lines+markers', name='营收',
                         line=dict(color='#2ECC71', width=3)))
fig.add_trace(go.Bar(x=monthly['月份'], y=monthly['订单数'],
                     name='订单数', yaxis='y2',
                     marker_color='#3498DB', opacity=0.6))
fig.update_layout(
    title='月度营收与订单数趋势',
    xaxis_title='月份',
    yaxis_title='营收（元）',
    yaxis2=dict(title='订单数', overlaying='y', side='right')
)
st.plotly_chart(fig, use_container_width=True)

# ------------------------------
# 10. 侧边栏筛选器
# ------------------------------
st.sidebar.header("🔍 数据筛选")
selected_doctor = st.sidebar.multiselect(
    "选择医生",
    options=df['医生'].unique(),
    default=df['医生'].unique()
)
selected_service = st.sidebar.multiselect(
    "选择服务项目",
    options=df['服务项目'].unique(),
    default=df['服务项目'].unique()
)

filtered_df = df[df['医生'].isin(selected_doctor) & df['服务项目'].isin(selected_service)]
st.sidebar.metric("筛选后营收", f"{filtered_df['消费金额'].sum()/10000:.1f}万")