import yfinance as yf
from rich.live import Live
from rich.table import Table
from rich import box
import time
import datetime
import warnings
import os

warnings.filterwarnings("ignore")

TICKERS = ["SPY", "QQQ", "SNDK", "SNXX", "MU", "GEV"]

# Keep track of previous signals to avoid spamming notifications
PREVIOUS_SIGNALS = {t: "HOLD" for t in TICKERS}

def send_mac_notification(title, text):
    os.system(f"""osascript -e 'display notification "{text}" with title "{title}"'""")

def fetch_data():
    data = {}
    try:
        # Fetch enough history for a 5-day SMA
        df = yf.download(TICKERS, period="10d", interval="1d", progress=False, threads=False)
        if df.empty:
            return {t: (0, 0, "HOLD", 0) for t in TICKERS}
            
        for symbol in TICKERS:
            try:
                close_series = df['Close'][symbol].dropna()
                if len(close_series) >= 2:
                    current_price = close_series.iloc[-1]
                    prev_close = close_series.iloc[-2]
                elif len(close_series) == 1:
                    current_price = close_series.iloc[0]
                    prev_close = current_price
                else:
                    prev_close, current_price = 0, 0
                
                # Calculate 5-day SMA
                if len(close_series) >= 5:
                    sma_5 = close_series.tail(5).mean()
                else:
                    sma_5 = current_price

                # Signal Logic
                if current_price > sma_5:
                    signal = "BUY"
                    limit_price = current_price * 0.995 # Buy limit slightly below market
                elif current_price < sma_5:
                    signal = "SELL"
                    limit_price = current_price * 1.005 # Sell limit slightly above market
                else:
                    signal = "HOLD"
                    limit_price = current_price
                
                if prev_close > 0:
                    pct_change = ((current_price - prev_close) / prev_close) * 100
                else:
                    pct_change = 0
                    
                data[symbol] = (current_price, pct_change, signal, limit_price)
            except Exception:
                data[symbol] = (0, 0, "HOLD", 0)
    except Exception as e:
        pass
    return data

def generate_table(data) -> Table:
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    table = Table(box=box.ROUNDED, expand=True, title=f"[bold cyan]EUREKA LIVE DASHBOARD[/bold cyan] - {now_str}")
    table.add_column("Ticker", justify="center", style="cyan", no_wrap=True)
    table.add_column("Price", justify="right", style="white")
    table.add_column("Change (%)", justify="right")
    table.add_column("Signal", justify="center")
    table.add_column("Limit Price", justify="right", style="yellow")
    
    for symbol in TICKERS:
        price, change, signal, limit = data.get(symbol, (0, 0, "HOLD", 0))
        
        # Format Change
        if change > 0:
            change_str = f"[green]+{change:.2f}%[/green]"
        elif change < 0:
            change_str = f"[red]{change:.2f}%[/red]"
        else:
            change_str = f"[yellow]0.00%[/yellow]"
            
        # Format Signal
        if signal == "BUY":
            signal_str = "[bold green]BUY[/bold green]"
        elif signal == "SELL":
            signal_str = "[bold red]SELL[/bold red]"
        else:
            signal_str = "[bold white]HOLD[/bold white]"
            
        table.add_row(symbol, f"${price:.2f}", change_str, signal_str, f"${limit:.2f}")
        
    return table

def process_notifications(data):
    global PREVIOUS_SIGNALS
    for symbol, values in data.items():
        if not values: continue
        _, _, signal, limit = values
        
        # If signal changed to BUY or SELL
        if signal != "HOLD" and signal != PREVIOUS_SIGNALS.get(symbol):
            send_mac_notification(
                f"Eureka Alert: {symbol} {signal}",
                f"Limit Price: ${limit:.2f}"
            )
            PREVIOUS_SIGNALS[symbol] = signal
        elif signal == "HOLD":
            PREVIOUS_SIGNALS[symbol] = "HOLD"

def main():
    print("Initializing Eureka Live Dashboard with Signals...")
    initial_data = fetch_data()
    process_notifications(initial_data)
    
    with Live(generate_table(initial_data), refresh_per_second=1) as live:
        while True:
            time.sleep(30) # Refresh every 30 seconds to avoid yfinance rate limits
            data = fetch_data()
            process_notifications(data)
            live.update(generate_table(data))

if __name__ == "__main__":
    main()
