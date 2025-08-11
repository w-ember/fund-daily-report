import streamlit as st
import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

st.set_page_config(page_title="基金涨跌及持仓建议", layout="wide")
st.title("📊 基金涨跌及持仓建议")

# 配置参数
FUND_TYPE = st.selectbox("选择基金类型", ["股票型", "混合型", "债券型", "指数型", "全部"], index=0)
TOP_N = st.slider("显示涨跌排名数量", 3, 20, 5)
PERIOD = st.selectbox("涨跌周期", ["近1周", "近1月", "近3月"], index=1)

@st.cache_data(ttl=3600)
def get_fund_rank(fund_type, period, top_n=50):
    try:
        df = ak.fund_em_open_fund_rank(fund_type=fund_type, period_type=period)
        df = df.sort_values(period, ascending=False).head(top_n)
        return df[["基金代码", "基金简称", period]]
    except Exception as e:
        st.error(f"获取基金排行失败：{e}")
        return pd.DataFrame()

fund_rank = get_fund_rank(FUND_TYPE, PERIOD, top_n=TOP_N*3)
if fund_rank.empty:
    st.warning("暂无基金排行数据，请稍后重试")
    st.stop()

fund_codes = fund_rank["基金代码"].tolist()

def get_nav_history(code, days=60):
    today = datetime.today()
    start_date = (today - timedelta(days=days)).strftime("%Y-%m-%d")
    try:
        df = ak.fund_em_open_fund_info(fund=code, start_date=start_date, end_date=today.strftime("%Y-%m-%d"))
        df = df.sort_values(by=df.columns[0])
        nav_col = next((c for c in df.columns if "单位净值" in c), None)
        if nav_col is None:
            return None
        df["净值"] = pd.to_numeric(df[nav_col], errors="coerce")
        return df[["净值"]].dropna()
    except:
        return None

def compute_indicators(nav_series):
    # 计算5日均线和20日均线
    ma5 = nav_series.rolling(window=5).mean()
    ma20 = nav_series.rolling(window=20).mean()
    # 计算14日RSI
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

# 抓取基金最新涨跌幅和建议
results = []
for code in fund_codes[:TOP_N*3]:  # 先多抓一些，筛选后显示TOP_N
    nav_hist = get_nav_history(code, days=60)
    if nav_hist is None or len(nav_hist) < 20:
        continue
    ma5, ma20, rsi = compute_indicators(nav_hist["净值"])
    suggestion = make_suggestion(ma5, ma20, rsi)

    # 计算最近两个交易日涨跌幅
    change_pct = (nav_hist["净值"].iloc[-1] - nav_hist["净值"].iloc[-2]) / nav_hist["净值"].iloc[-2] * 100
    fund_name = fund_rank.loc[fund_rank["基金代码"] == code, "基金简称"].values[0]

    results.append({
        "基金代码": code,
        "基金名称": fund_name,
        "最新涨跌幅(%)": round(change_pct, 4),
        "建议": suggestion
    })

df_results = pd.DataFrame(results)
if df_results.empty:
    st.warning("未获取到足够的基金净值数据")
    st.stop()

# 排序并取前N涨跌
df_up = df_results.sort_values("最新涨跌幅(%)", ascending=False).head(TOP_N)
df_down = df_results.sort_values("最新涨跌幅(%)", ascending=True).head(TOP_N)

st.subheader(f"涨幅前 {TOP_N} 名")
st.table(df_up)

st.subheader(f"跌幅前 {TOP_N} 名")
st.table(df_down)

# 绘图展示涨跌幅
import seaborn as sns
sns.set_style("whitegrid")

fig, ax = plt.subplots(figsize=(10, 6))
colors = df_results["最新涨跌幅(%)"].apply(lambda x: "red" if x > 0 else "green")
ax.bar(df_results["基金名称"], df_results["最新涨跌幅(%)"], color=colors)
plt.xticks(rotation=45, ha="right")
plt.ylabel("涨跌幅(%)")
plt.title(f"{datetime.today().strftime('%Y-%m-%d')} 基金最新涨跌幅")
st.pyplot(fig)

st.info("数据来源：Akshare，因接口及数据延迟，结果仅供参考。")

