# 📦 필요한 패키지 설치: 
# pip install streamlit streamlit-autorefresh requests pandas

import streamlit as st
import requests
import pandas as pd
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# ✅ 설정
st.set_page_config(page_title="코인 가격 비교", layout="wide")
st.title("💹 실시간 코인 거래소 가격 비교 대시보드")

coin_symbols = {
    "BTC": "비트코인",
    "ETH": "이더리움",
    "XRP": "리플",
    "ADA": "에이다",
    "DOGE": "도지코인"
}

EXCHANGE_RATE = 1350  # USDT → KRW 환산

# 📡 거래소별 가격 조회 함수들
def get_upbit_price(symbol):
    try:
        url = f"https://api.upbit.com/v1/ticker?markets=KRW-{symbol}"
        return requests.get(url).json()[0]["trade_price"]
    except:
        return None

def get_bithumb_price(symbol):
    try:
        url = f"https://api.bithumb.com/public/ticker/{symbol}_KRW"
        return float(requests.get(url).json()["data"]["closing_price"])
    except:
        return None

def get_binance_price(symbol):
    try:
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}USDT"
        return float(requests.get(url).json()["price"]) * EXCHANGE_RATE
    except:
        return None

def get_bybit_price(symbol):
    try:
        url = f"https://api.bybit.com/v5/market/tickers?category=linear&symbol={symbol}USDT"
        r = requests.get(url).json()
        return float(r["result"]["list"][0]["lastPrice"]) * EXCHANGE_RATE
    except:
        return None

# 📊 가격 데이터 수집
def fetch_prices():
    rows = []
    for symbol, name in coin_symbols.items():
        prices = {
            "코인명": name,
            "업비트": get_upbit_price(symbol),
            "빗썸": get_bithumb_price(symbol),
            "바이낸스": get_binance_price(symbol),
            "바이비트": get_bybit_price(symbol)
        }
        rows.append(prices)
    return pd.DataFrame(rows)

# 퍼센트 차이 포함 포맷팅
def format_with_diff(row):
    values = row[1:]
    max_val = values.max(skipna=True)
    min_val = values.min(skipna=True)
    formatted = [row[0]]
    for val in values:
        if pd.isna(val):
            formatted.append("N/A")
        elif val == max_val and min_val > 0:
            pct = ((max_val - min_val) / min_val) * 100
            formatted.append(f"\u20a9{val:,.0f} (+{pct:.2f}%)")
        elif val == min_val and max_val > 0:
            pct = ((max_val - min_val) / max_val) * 100
            formatted.append(f"\u20a9{val:,.0f} (-{pct:.2f}%)")
        else:
            formatted.append(f"\u20a9{val:,.0f}")
    return formatted

# 스타일 강조 함수
def highlight_extremes(row):
    values = row[1:]
    max_val = values.max(skipna=True)
    min_val = values.min(skipna=True)
    styles = []
    for val in values:
        if pd.isna(val):
            styles.append("")
        elif val == max_val:
            styles.append("color: red; font-weight: bold; background-color: #ffe5e5;")
        elif val == min_val:
            styles.append("color: black; font-weight: bold; background-color: #ffff99;")
        else:
            styles.append("")
    return [""] + styles

# ⏱ 갱신 슬라이더
interval = st.sidebar.slider("🔁 자동 갱신 간격 (초)", 5, 60, 15)
st_autorefresh(interval=interval * 1000, key="refresh")

# 데이터 조회
raw_df = fetch_prices()
for col in raw_df.columns[1:]:
    raw_df[col] = pd.to_numeric(raw_df[col], errors='coerce')

formatted_df = pd.DataFrame([format_with_diff(row) for _, row in raw_df.iterrows()],
                            columns=raw_df.columns)
styled_df = formatted_df.style.apply(highlight_extremes, axis=1)

# 결과 표시
st.dataframe(styled_df, use_container_width=True)
st.caption(f"⏱ 마지막 업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")