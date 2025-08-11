# app.py
import streamlit as st
import akshare as ak
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

st.set_page_config(page_title="基金日报", layout="wide")
st.title("📈 基金日报")

fund_type = st.selectbox("选择基金类型", options=["全部", "股票型", "混合型", "债券型", "指数型"], index=1)
period = st.selectbox("选择涨跌周期", options=["近1周", "近1月", "近3月"], index=1)
top_n = st.slider("涨跌榜数量", 3, 20, 5)

@st.cache_data(ttl=3600)
def get_top_funds(top_n, fund_type, period):
    df = ak.fund_em_open_fund_rank(fund_type, period)
    df = df.sort_values(period, ascending=False).head(top_n * 3)
    return df

df_rank = get_top_funds(top_n, fund_type, period)
fund_codes = df_rank["基金代码"].tolist()

def get_fund_recent_nav(fund_code, days=7):
    today = datetime.today()
    start_date = (today - timedelta(days=days)).strftime("%Y-%m-%d")
    try:
        df = ak.fund_em_open_fund_info(fund=fund_code, start_date=start_date, end_date=today.strftime("%Y-%m-%d"))
        df = df.sort_values(by=df.columns[0])
        return df
    except:
        return None

rows = []
for code in fund_codes:
    df = get_fund_recent_nav(code)
    if df is None or len(df) < 2:
        continue
    nav_col = next((c for c in df.columns if "单位净值" in c), df.columns[1])
    last = df.iloc[-1]
    prev = df.iloc[-2]
    change_pct = (float(last[nav_col]) - float(prev[nav_col])) / float(prev[nav_col]) * 100
    fund_name = next((last[c] for c in df.columns if "基金简称" in c or "基金名称" in c), "")
    rows.append({
        "基金代码": code,
        "基金名称": fund_name,
        "日期": last[df.columns[0]],
        "涨跌幅(%)": round(change_pct, 4)
    })

df_changes = pd.DataFrame(rows)
if df_changes.empty:
    st.warning("未获取到基金数据")
    st.stop()

df_up = df_changes.sort_values("涨跌幅(%)", ascending=False).head(top_n)
df_down = df_changes.sort_values("涨跌幅(%)", ascending=True).head(top_n)

st.subheader(f"涨幅前 {top_n} 名")
st.table(df_up)

st.subheader(f"跌幅前 {top_n} 名")
st.table(df_down)

import seaborn as sns
sns.set_style("whitegrid")

fig, ax = plt.subplots(figsize=(8, 5))
colors = df_changes["涨跌幅(%)"].apply(lambda x: "red" if x > 0 else "green")
ax.bar(df_changes["基金名称"], df_changes["涨跌幅(%)"], color=colors)
plt.xticks(rotation=45, ha="right")
plt.title(f"{datetime.today().strftime('%Y-%m-%d')} 基金涨跌幅")
plt.ylabel("涨跌幅(%)")
st.pyplot(fig)

st.info("基金数据由 Akshare 提供，数据可能有延迟，请注意。")
