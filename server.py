import http.server
import socketserver
import json
import socket
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
      'JSWENERGY', 'LODHA', 'MOTHERSON', 'NAUKRI', 'NHPC',
      'PFC', 'PIDILITIND', 'PNB', 'POLYCAB', 'RECLTD',
      'SBICARD', 'SIEMENS', 'SOLARINDS', 'SRF', 'TVSMOTOR',
      'TATAPOWER', 'TORNTPHARM', 'TORNTPOWER', 'UNIONBANK', 'VBL',
      'VEDL', 'IDEA', 'ZYDUSLIFE', 'CGPOWER', 'DIVISLAB'
]

ALL_SYMBOLS = [s + '.NS' for s in N50_EXACT + NEXT50_EXACT]
N50_SET = set(N50_EXACT)

DATA_LOCK = threading.Lock()
history_file = os.path.join(DIR, "actual_today_history.json")
LATEST_PAYLOAD = {
      "n50": {"adv": 32, "dec": 17, "unch": 1},
      "n100": {"adv": 68, "dec": 31, "unch": 1},
      "gainers": [],
      "losers": [],
      "h50": [],
      "h100": [],
      "timestamp": ""
}

if os.path.exists(history_file):
      try:
                with open(history_file, "r") as f:
                              LATEST_PAYLOAD = json.load(f)
      except Exception:
                pass

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

                h50 = []
                h100 = []
                for dt, row in df_today.iterrows():
                                      t_str = dt.strftime('%H:%M')
                                      a5 = d5 = a1 = d1 = 0
                                      for sym in N50_EXACT + NEXT50_EXACT:
                                                                y_sym = sym + '.NS'
                                                                p = row.get(y_sym)
                                                                pc = prev_close.get(y_sym)
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
                                                                                                                    h100.append({'t': t_str, 'adv': a1, 'dec': d1})
                                                                                                            
                                                        latest_prices = df_today.iloc[-1]
                stocks = []
                cur_a50 = cur_d50 = cur_u50 = 0
                cur_a100 = cur_d100 = cur_u100 = 0
                for sym in N50_EXACT + NEXT50_EXACT:
                                      y_sym = sym + '.NS'
                    p = latest_prices.get(y_sym)
                    pc = prev_close.get(y_sym)
                    if pd.isna(p) or pd.isna(pc) or pc == 0:
                                              continue
                                          chg = float(((p - pc) / pc) * 100)
                    is_n50 = sym in N50_SET
                    if chg > 0.001:
                                              cur_a100 += 1
                                              if is_n50: cur_a50 += 1
                    elif chg < -0.001:
                        cur_d100 += 1
                        if is_n50: cur_d50 += 1
else:
                        cur_u100 += 1
                        if is_n50: cur_u50 += 1
                                              stocks.append({
                                                                        's': sym,
                                                                        'p': f'{float(p):,.1f}',
                                                                        'c': f'{chg:.2f}',
                                                                        'rawChg': chg
                                              })
                stocks.sort(key=lambda x: x['rawChg'], reverse=True)
                gainers = stocks[:10]
                losers = list(reversed(stocks[-10:]))

                payload = {
                                      "n50": {"adv": cur_a50, "dec": cur_d50, "unch": cur_u50},
                                      "n100": {"adv": cur_a100, "dec": cur_d100, "unch": cur_u100},
                                      "gainers": gainers,
                                      "losers": losers,
                                      "h50": h50,
                                      "h100": h100,
                                      "date": today_str,
                                      "timestamp": datetime.datetime.now().strftime('%H:%M:%S')
                }
                if (cur_a50 + cur_d50 + cur_u50) >= 48:
                                      with DATA_LOCK:
                                                                   with DATA_LOCK:
                                                                                             LATEST_PAYLOAD = payload
                                                                                         with open(history_file, "w") as f:
                                                                                                                   json.dump(payload, f, indent=2)
                                                                                                           print(f"[{payload['timestamp']}] yfinance update complete: N50 {cur_a50}/{cur_d50}, N100 {cur_a100}/{cur_d100}, {len(h50)} candles.", flush=True)
except Exception as e:
            print("yfinance worker error:", e)
        time.sleep(30)

class FastHandler(http.server.SimpleHTTPRequestHandler):
      def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=DIR, **kwargs)
    def end_headers(self):
              self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()
    def do_GET(self):
              if self.path.startswith("/api/data"):
                            with DATA_LOCK:
                                              payload = dict(LATEST_PAYLOAD)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(payload).encode("utf-8"))
else:
            super().do_GET()

def get_ip():
      try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                ip = s.getsockname()[0]
                s.close()
                return ip
except Exception:
          return "127.0.0.1"

  if __name__ == "__main__":
        worker = threading.Thread(target=update_yfinance_cache, daemon=True)
        worker.start()
        ip = get_ip()
        socketserver.TCPServer.allow_reuse_address = True
        with socketserver.TCPServer(("0.0.0.0", PORT), FastHandler) as httpd:
                  print(f"Server live on port {PORT} with pure yfinance engine")
                  print(f"Local: http://localhost:{PORT}")
                  print(f"Android: http://{ip}:{PORT}")
                  httpd.serve_forever()
          
