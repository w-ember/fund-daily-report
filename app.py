import streamlit as st
import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

st.set_page_config(page_title="基金涨跌及持仓建议", layout="wide")
st.title("📊 基金涨跌及持仓建议")

FUND_TYPE = st.selectbox("选择基金类型", ["股票型", "混合型", "债券型", "指数型", "全部"], index=0)
TOP_N = st.slider("显示涨跌排名数量", 3, 20, 5)
PERIOD_DAYS = st.selectbox("涨跌周期（天）", [7, 14, 30], index=2)

@st.cache_data(ttl=3600)
def get_fund_list():
    df = ak.fund_em_fund_name_code()
    if FUND_TYPE != "全部":
        df = df[df["基金类型"] == FUND_TYPE]
    return df

fund_list = get_fund_list()
if fund_list.empty:
    st.warning("无基金列表数据")
    st.stop()

def get_nav_df(code):
    try:
        df = ak.fund_open_fund_daily_nav(code)
        df["净值"] = pd.to_numeric(df["单位净值"], errors="coerce")
        df = df.dropna(subset=["净值"])
        return df
    except:
        return pd.DataFrame()

def calc_change(nav_df, days):
    if nav_df.empty or len(nav_df) < days + 1:
        return None
    nav_df = nav_df.sort_values("净值日期")
    start_nav = nav_df.iloc[-(days+1)]["净值"]
    end_nav = nav_df.iloc[-1]["净值"]
    change_pct = (end_nav - start_nav) / start_nav * 100
    return round(change_pct, 4)

def compute_indicators(nav_series):
    ma5 = nav_series.rolling(window=5).mean()
    ma20 = nav_series.rolling(window=20).mean()
    delta = nav_series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return ma5, ma20, rsi

def make_suggestion(ma5, ma20, rsi):
    if len(ma5) == 0 or len(ma20) == 0 or len(rsi) == 0:
        return "无足够数据"
    if ma5.iloc[-1] < ma20.iloc[-1] and rsi.iloc[-1] > 70:
        return "建议减仓"
    elif ma5.iloc[-1] > ma20.iloc[-1] and rsi.iloc[-1] < 30:
        return "建议加仓"
    else:
        return "建议持有"

results = []
count = 0
for idx, row in fund_list.iterrows():
    if count >= TOP_N * 5:  # 多抓一些筛选
        break
    code = row["基金代码"]
    name = row["基金简称"]
    nav_df = get_nav_df(code)
    if nav_df.empty or len(nav_df) < 30:
        continue
    change = calc_change(nav_df, PERIOD_DAYS)
    if change is None:
        continue
    ma5, ma20, rsi = compute_indicators(nav_df["净值"])
    suggestion = make_suggestion(ma5, ma20, rsi)
    results.append({
        "基金代码": code,
        "基金名称": name,
        f"{PERIOD_DAYS}天涨跌幅(%)": change,
        "建议": suggestion
    })
    count += 1

df_results = pd.DataFrame(results)
if df_results.empty:
    st.warning("未获取到足够数据")
    st.stop()

df_up = df_results.sort_values(f"{PERIOD_DAYS}天涨跌幅(%)", ascending=False).head(TOP_N)
df_down = df_results.sort_values(f"{PERIOD_DAYS}天涨跌幅(%)", ascending=True).head(TOP_N)

st.subheader(f"涨幅前 {TOP_N} 名")
st.table(df_up)

st.subheader(f"跌幅前 {TOP_N} 名")
st.table(df_down)

import seaborn as sns
sns.set_style("whitegrid")

fig, ax = plt.subplots(figsize=(10, 6))
colors = df_results[f"{PERIOD_DAYS}天涨跌幅(%)"].apply(lambda x: "red" if x > 0 else "green")
ax.bar(df_results["基金名称"], df_results[f"{PERIOD_DAYS}天涨跌幅(%)"], color=colors)
plt.xticks(rotation=45, ha="right")
plt.ylabel("涨跌幅(%)")
plt.title(f"{datetime.today().strftime('%Y-%m-%d')} 基金{PERIOD_DAYS}天涨跌幅")
st.pyplot(fig)

st.info("数据来源 Akshare，结果仅供参考。")
