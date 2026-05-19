import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="宠物医院经营分析看板", layout="wide", page_icon="🐾")

@st.cache_data
def load_data():
    df = pd.read_csv('pet_hospital_data.csv', encoding='utf-8-sig')
    df['日期'] = pd.to_datetime(df['日期'])
    return df

df_raw = load_data()
today = datetime(2026, 5, 19)

all_doctors = list(df_raw['医生'].unique())
all_services = list(df_raw['服务项目'].unique())

# 从 query_params 中读取筛选值，如果没有则使用全选
params = st.query_params
if "doctors" in params:
    selected_doctors = params["doctors"].split(",")
else:
    selected_doctors = all_doctors
if "services" in params:
    selected_services = params["services"].split(",")
else:
    selected_services = all_services

# 侧边栏筛选器（不使用 key 绑定 session_state）
st.sidebar.header("🔍 全局筛选")

# 多选组件，值存储在临时变量中
new_doctors = st.sidebar.multiselect(
    "选择医生",
    options=all_doctors,
    default=selected_doctors
)
new_services = st.sidebar.multiselect(
    "选择服务项目",
    options=all_services,
    default=selected_services
)

# 重置按钮：清空 query_params
if st.sidebar.button("🔄 重置筛选"):
    st.query_params.clear()
    st.rerun()

# 当筛选器变化时，更新 query_params
if new_doctors != selected_doctors or new_services != selected_services:
    st.query_params["doctors"] = ",".join(new_doctors)
    st.query_params["services"] = ",".join(new_services)
    st.rerun()

# 使用最新的筛选值
filtered_df = df_raw[
    df_raw['医生'].isin(new_doctors) &
    df_raw['服务项目'].isin(new_services)
].copy()

if len(filtered_df) == 0:
    st.error("❌ 当前筛选条件下无数据")
    st.stop()

# 后续代码与之前相同（从客户RFM计算开始）...
# 为避免重复，下面只写关键部分，实际您可以将之前完整代码复制过来，只需替换数据过滤部分的前置逻辑。