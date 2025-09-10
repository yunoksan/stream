

# 📄 파일: btc_dashboard_app.py

import streamlit as st
import json
import pandas as pd
import time
from datetime import datetime

st.set_page_config(page_title="실시간 코인 가격판", layout="wide", page_icon="📈")

PRICE_FILE = "btc_prices.json"
COINS = ["BTC", "ETH", "XRP", "SOL", "DOGE"]

# 💡 가격 비교 시각 강조용 함수
def highlight_prices(df):
    prices = df["가격"].astype(float)
    max_price = prices.max()
    min_price = prices.min()
    def color(val):
        if val == max_price:
            return "color: red; font-weight: bold"
        elif val == min_price:
            return "color: orange; font-weight: bold"
        return ""
    return df.style.applymap(color, subset=["가격"])

# 📊 각 코인 섹션 렌더링
def render_coin_section(coin, data):
    st.markdown(f"### 📉 실시간 {coin} 가격 비교")
    rows = []
    for exchange, info in data.get(coin, {}).items():
        if isinstance(info, list):
            price, volume, balance = info
        else:
            price = info.get("가격")
            volume = info.get("거래량")
            balance = info.get("보유수량")
        rows.append([exchange, price, volume, balance])

    df = pd.DataFrame(rows, columns=["거래소", "가격", "거래량", "보유수량"])
    df["가격"] = pd.to_numeric(df["가격"], errors="coerce")

    # 🚨 퍼센트 차이 표시용
    try:
        max_price = df["가격"].max()
        min_price = df["가격"].min()
        df["가격"] = df["가격"].apply(lambda x: f"₩{int(x):,}" if pd.notna(x) else "-")
        df["차이"] = df["거래소"].apply(lambda x: "")
        for i in df.index:
            if df.loc[i, "가격"] != "-":
                price_val = pd.to_numeric(df.loc[i, "가격"].replace("₩", "").replace(",", ""))
                if price_val == max_price:
                    percent = ((price_val - min_price) / min_price) * 100
                    df.loc[i, "차이"] = f"▲ {percent:.2f}%"
                elif price_val == min_price:
                    percent = ((max_price - price_val) / max_price) * 100
                    df.loc[i, "차이"] = f"▼ {percent:.2f}%"
    except:
        pass

    st.dataframe(
        df,
        use_container_width=True
    )

# 🔁 메인 루프
st.title("📊 실시간 코인 거래소 가격 비교")

placeholder = st.empty()
while True:
    with placeholder.container():
        try:
            with open(PRICE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            for coin in COINS:
                render_coin_section(coin, data)
        except Exception as e:
            st.error(f"❌ 데이터 로딩 오류: {e}")

    time.sleep(5)
    placeholder.empty()