# 📄 파일: btc_price_backend.py

import json
import time
import threading
import requests
from websocket import WebSocketApp
from datetime import datetime

PRICE_FILE = "btc_prices.json"
COINS = ["BTC", "ETH", "XRP", "SOL", "DOGE"]
EXCHANGES = ["업비트", "빗썸", "코인원", "바이낸스", "바이비트"]

lock = threading.Lock()

def save_prices(prices):
    with lock:
        with open(PRICE_FILE, "w", encoding="utf-8") as f:
            json.dump(prices, f, ensure_ascii=False, indent=2)

def fetch_rest_price_bithumb(coin):
    try:
        url = f"https://api.bithumb.com/public/ticker/{coin}_KRW"
        r = requests.get(url)
        data = r.json()
        price = float(data["data"]["closing_price"])
        volume = float(data["data"]["acc_trade_value_24H"])
        return {"가격": price, "거래량": volume, "보유수량": None, "업데이트": now()}
    except:
        return None

def fetch_rest_price_coinone(coin):
    try:
        url = f"https://api.coinone.co.kr/ticker?currency={coin.lower()}"
        r = requests.get(url)
        data = r.json()
        price = float(data["last"])
        volume = float(data["volume"])
        return {"가격": price, "거래량": None, "보유수량": volume, "업데이트": now()}
    except:
        return None

def upbit_ws(prices):
    def on_message(ws, message):
        data = json.loads(message)
        code = data['code']
        for coin in COINS:
            if code == f"KRW-{coin}":
                price = data['trade_price']
                volume = data.get('acc_trade_volume', None)
                prices.setdefault(coin, {})['업비트'] = {
                    "가격": price,
                    "거래량": volume,
                    "보유수량": 1.2,  # 예시 수량
                    "업데이트": now()
                }
                save_prices(prices)

    ws = WebSocketApp(
        "wss://api.upbit.com/websocket/v1",
        on_message=on_message
    )
    ws.on_open = lambda ws: ws.send(json.dumps([
        {"ticket": "test"},
        {"type": "trade", "codes": [f"KRW-{coin}" for coin in COINS]}
    ]))
    ws.run_forever()

def now():
    return datetime.now().strftime("%H:%M:%S")

def start_backend():
    prices = {}
    threading.Thread(target=upbit_ws, args=(prices,), daemon=True).start()

    while True:
        for coin in COINS:
            bithumb_data = fetch_rest_price_bithumb(coin)
            coinone_data = fetch_rest_price_coinone(coin)
            if bithumb_data:
                prices.setdefault(coin, {})["빗썸"] = bithumb_data
            if coinone_data:
                prices.setdefault(coin, {})["코인원"] = coinone_data
        save_prices(prices)
        time.sleep(10)

if __name__ == "__main__":
    print("[✔] 백엔드 작동 중... Ctrl+C로 종료")
    start_backend()
