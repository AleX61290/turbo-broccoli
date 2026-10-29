import http.server
import socketserver
import json
import os
import threading
import time
import datetime
import yfinance as yf
import pandas as pd

PORT = int(os.environ.get("PORT", 7799))
DIR = os.path.dirname(os.path.abspath(__file__))

N50_EXACT = [
    'ADANIENT', 'ADANIPORTS', 'APOLLOHOSP', 'ASIANPAINT', 'AXISBANK',
    'BAJAJ-AUTO', 'BAJFINANCE', 'BAJAJFINSV', 'BEL', 'BHARTIARTL',
    'BSE', 'CIPLA', 'COALINDIA', 'DRREDDY', 'EICHERMOT',
    'ETERNAL', 'GRASIM', 'HCLTECH', 'HDFCBANK', 'HDFCLIFE',
    'HINDALCO', 'HINDUNILVR', 'ICICIBANK', 'INDIGO', 'INFY',
    'ITC', 'JIOFIN', 'JSWSTEEL', 'KOTAKBANK', 'LT',
    'M&M', 'MARUTI', 'MAXHEALTH', 'NESTLEIND', 'NTPC',
    'ONGC', 'POWERGRID', 'RELIANCE', 'SBILIFE', 'SBIN',
    'SHRIRAMFIN', 'SUNPHARMA', 'TATACONSUM', 'TATASTEEL', 'TCS',
    'TECHM', 'TITAN', 'TMPV', 'TRENT', 'ULTRACEMCO'
]

NEXT50_EXACT = [
    'ABB', 'ADANIENSOL', 'ADANIGREEN', 'ADANIPOWER', 'AMBUJACEM',
    'DMART', 'BAJAJHLDNG', 'BANKBARODA', 'BOSCHLTD', 'CANBK',
    'CHOLAFIN', 'COLPAL', 'CUMMINSIND', 'DLF', 'GAIL',
    'GODREJCP', 'HDFCAMC', 'HAL', 'HAVELLS', 'HINDZINC',
    'ICICIGI', 'LICI', 'IOC', 'IRFC', 'JINDALSTEL',
    'JSWENERGY', 'LODHA', 'MOTHERSON', 'NAUKRI',
    'NHPC', 'PFC', 'PIDILITIND', 'PNB', 'POLYCAB',
    'RECLTD', 'SBICARD', 'SIEMENS', 'SOLARINDS', 'SRF',
    'TVSMOTOR', 'TATAPOWER', 'TORNTPHARM', 'TORNTPOWER', 'UNIONBANK',
    'VBL', 'VEDL', 'IDEA', 'ZYDUSLIFE', 'CGPOWER', 'DIVISLAB'
]

ALL_SYMBOLS = [s + '.NS' for s in N50_EXACT + NEXT50_EXACT]
N50_SET = set(N50_EXACT)

DATA_LOCK = threading.Lock()
LATEST_PAYLOAD = {
    "n50": {"adv": 39, "dec": 11, "unch": 0},
    "n100": {"adv": 80, "dec": 20, "unch": 0},
    "gainers": [],
    "losers": [],
    "h50": [],
    "h100": [],
    "timestamp": ""
}

def update_yfinance_cache():
    global LATEST_PAYLOAD
    today_str = datetime.date.today().strftime('%Y-%m-%d')
    while True:
        try:
            data = yf.download(ALL_SYMBOLS, period='2d', interval='5m', progress=False)['Close']
            if not data.empty:
                data = data.ffill().bfill()
                df_today = data.loc[data.index.strftime('%Y-%m-%d') == today_str]
                df_yesterday = data.loc[data.index.strftime('%Y-%m-%d') < today_str]
                prev_close = df_yesterday.iloc[-1] if not df_yesterday.empty else df_today.iloc[0]

                h50, h100 = [], []
                for dt, row in df_today.iterrows():
                    t_str = dt.strftime('%H:%M')
                    a5 = d5 = a1 = d1 = 0
                    for sym in N50_EXACT + NEXT50_EXACT:
                        p = row.get(sym + '.NS')
                        pc = prev_close.get(sym + '.NS')
                        if pd.isna(p) or pd.isna(pc) or pc == 0:
                            continue
                        diff = p - pc
                        is_n50 = sym in N50_SET
                        if diff > 0.001:
                            a1 += 1
                            if is_n50: a5 += 1
                        elif diff < -0.001:
                            d1 += 1
                            if is_n50: d5 += 1
                    if (a5 + d5) >= 30:
                        h50.append({'t': t_str, 'adv': a5, 'dec': d5})
                    if (a1 + d1) >= 60:
                        h100.append({'t': t_str, 'adv': a1, 'dec': d1})

                latest = df_today.iloc[-1]
                cur_a5, cur_d5, cur_u5 = 0, 0, 0
                cur_a1, cur_d1, cur_u1 = 0, 0, 0
                stocks = []
                for sym in N50_EXACT + NEXT50_EXACT:
                    p = latest.get(sym + '.NS')
                    pc = prev_close.get(sym + '.NS')
                    if pd.isna(p) or pd.isna(pc) or pc == 0:
                        continue
                    chg = float(((p - pc) / pc) * 100)
                    is_n50 = sym in N50_SET
                    if chg > 0.001:
                        cur_a1 += 1
                        if is_n50: cur_a5 += 1
                    elif chg < -0.001:
                        cur_d1 += 1
                        if is_n50: cur_d5 += 1
                    else:
                        cur_u1 += 1
                        if is_n50: cur_u5 += 1
                    stocks.append({'s': sym, 'p': f'{float(p):,.1f}', 'c': f'{chg:.2f}', 'raw': chg})

                stocks.sort(key=lambda x: x['raw'], reverse=True)
                payload = {
                    "n50": {"adv": cur_a5, "dec": cur_d5, "unch": cur_u5},
                    "n100": {"adv": cur_a1, "dec": cur_d1, "unch": cur_u1},
                    "gainers": stocks[:10],
                    "losers": list(reversed(stocks[-10:])),
                    "h50": h50,
                    "h100": h100,
                    "timestamp": datetime.datetime.now().strftime('%H:%M:%S')
                }
                if (cur_a5 + cur_d5 + cur_u5) >= 45:
                    with DATA_LOCK:
                        LATEST_PAYLOAD = payload
                    print(f"[{payload['timestamp']}] YF update: N50 {cur_a5}/{cur_d5}, {len(h50)} candles", flush=True)
        except Exception as e:
            print("Worker error:", e, flush=True)
        time.sleep(30)

class FastHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIR, **kwargs)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        super().end_headers()

    def do_GET(self):
        if self.path.startswith("/api/data"):
            with DATA_LOCK:
                p = dict(LATEST_PAYLOAD)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(p).encode("utf-8"))
        else:
            super().do_GET()

if __name__ == "__main__":
    t = threading.Thread(target=update_yfinance_cache, daemon=True)
    t.start()
    with socketserver.TCPServer(("0.0.0.0", PORT), FastHandler) as httpd:
        print(f"Live on port {PORT}", flush=True)
        httpd.serve_forever()
