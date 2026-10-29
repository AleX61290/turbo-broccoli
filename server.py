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

PORT = int(os.environ.get("PORT", 7999))
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
          'TECHM', 'TITAN', 'TRENT', 'ULTRACEMCO', 'WIPRO'
]

NEXT50_EXACT = [
          'ABB', 'ADANIENSOL', 'ADANIGREEN', 'AMBUJACEM', 'APLAPOLLO',
          'ASHOKLEY', 'AUROPHARMA', 'AXISBANK', 'BALKRISIND', 'BANKBARODA',
          'BDL', 'BHEL', 'BPCL', 'CANBK', 'CHOLAFIN',
          'COLPAL', 'CONCOR', 'CUMMINSIND', 'DIVISLAB', 'DLF',
          'EICHERMOT', 'GAIL', 'GODREJCP', 'HAVELLS',
          'HINDPETRO', 'ICICIGI', 'ICICIPRULI', 'IOC', 'IRCTC',
          'IRFC', 'JINDALSTEL', 'LODHA', 'LUPIN', 'M&MFIN',
          'MARICO', 'MOTHERSON', 'MUTHOOTFIN', 'NAUKRI', 'NHPC',
          'NMDC', 'OBEROIRLTY', 'OFSS', 'PAGEIND', 'PATANJALI',
          'PFC', 'PGHH', 'PIDILITE', 'POLYCAB',
          'RECLTD', 'SBICARD', 'SIEMENS', 'SRF',
          'TVSMOTOR', 'UNITDSPR', 'VBL', 'VEDL', 'ZOMATO'
]

ALL_SYMBOLS = [ s + '.NS' for s in N50_EXACT + NEXT50_EXACT]
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
                df_yesterday = data.loc[data.index.strftime('%Y-%m-%d'] < today_str]
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
                                                                                                                                                                    if (a1 + d1) >= 60:
                                                                                                                                                                                                  h100.append({'t': t_str, 'adv': a1, 'dec': d1})
                                                                                                                                                                                          
                                                                                                    latest_row = df_today.iloc[-1]
                                                                                                    t_str = df_today.index[-1].strftime('%H:%M')
                                                                                                    a5 = d5 = a1 = d1 = 0
                                                                                                    gainers = []
                                                                                                    losers = []
                                                                                                    for sym in N50_EXACT + NEXT50_EXACT:
                                                                                                                              y_sym = sym + '.NS'
                                                                                                                              p = latest_row.get(y_sym)
                                                                                                                              pc = prev_close.get(y_sym)
                                                                                                                              if pd.isna(p) or pd.isna(pc) or pc == 0:
                                                                                                                                                            continue
                                                                                                                                                        pct = ((p - pc) / pc) * 100
                                                                                                                              is_n50 = sym in N50_SET
                                                                                                                              diff = p - pc
                                                                                                                              if diff > 0.001:
                                                                                                                                                            a1 += 1
                                                                                                                                                            if is_n50: a5 += 1
                                                                                                                                    elif diff < -0.001:
                        d1 += 1
                        if is_n50: d5 += 1
                                                  item = {"symbol": sym, "price": round(float(p), 2), "change": round(float(pct), 2)}
                    if pct > 0:
                                                  gainers.append(item)
elif pct < 0:
                        losers.append(item)

                gainers.sort(key=lambda x: x['change'], reverse=True)
                losers.sort(key=lambda x: x['change'])

                payload = {
                            "n50": {"adv": a5, "dec": d5, "unch": 50 - a5 - d5},
                          "n100": {"adv": a1, "dec": d1, "unch": 100 - a1 - d1},
                          "gainers": gainers[:10],
                          "losers": losers[:10],
                          "h50": h50,
                          "h100": h100,
                          "timestamp": t_str
                }
with DATA_LOCK:
          LATEST_PAYLOAD = payload
try:
          with open(history_file, "w") as f:
                        json.dump(payload, f)
except Exception:
    pass
except Exception as e:
            print("Cache update error:", e)
        time.sleep(60)

threading.Thread(target=update_yfinance_cache, daemon=True).start()

class Handler(http.server.SimpleHTTPRequestHandler):
          def do_GET(self):
                        if self.path == '/api/data':
                                          self.send_response(200)
                                          self.send_header('Content-Type', 'application/json')
                                          self.end_headers()
                                          with DATA_LOCK:
                                                                self.wfile.write(json.dumps(LATEST_PAYLOAD).encode('utf-8'))
                        else:
                                          super().do_GET()

                if __name__ == '__main__':
                          with socketserver.TCPServer(("", PORT), Handler) as httpd:
                                        print("Serving at port", PORT)
                                        httpd.serve_forever()
                                
