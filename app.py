import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 設定網頁版面
st.set_page_config(page_title="個股技術分析與 K 線圖", layout="wide")

st.title("📊 個股技術分析與 K 線圖 (搭配 20MA / 60MA / 120MA 與技術指標)")

# 側邊欄：檔案上傳與指標設定
st.sidebar.header("📁 資料設定與指標")
uploaded_file = st.sidebar.file_uploader("上傳股票清單 Excel 檔案", type=["xlsx", "csv"])

market_suffix = st.sidebar.selectbox("市場別預設", [".TW (上市)", ".TWO (上櫃)"], index=0)
suffix = ".TW" if "TW (上市)" in market_suffix else ".TWO"

# 選擇附圖技術指標
sub_indicator = st.sidebar.selectbox("選擇下方附圖指標", ["MACD", "KD", "RSI", "DMI"], index=0)

# 讀取 Excel 檔案
df_stocks = None
default_code = "2330"

if uploaded_file is not None:
    try:
        if uploaded_file.name.endswith('.csv'):
            df_stocks = pd.read_csv(uploaded_file)
        else:
            df_stocks = pd.read_excel(uploaded_file)
    except Exception as e:
        st.sidebar.error(f"讀取檔案發生錯誤: {e}")

# 主畫面：顯示股票表格並支援點擊選股
if df_stocks is not None:
    code_col = None
    for col in df_stocks.columns:
        if any(k in str(col).lower() for k in ['代號', 'code', '股票', 'stock', 'ticker']):
            code_col = col
            break
            
    if code_col is None:
        best_col = df_stocks.columns[0]
        max_valid_count = -1
        for col in df_stocks.columns:
            s_cleaned = df_stocks[col].dropna().astype(str).str.strip()
            valid_count = s_cleaned.str.match(r'^\d{4,6}$').sum()
            if valid_count > max_valid_count:
                max_valid_count = valid_count
                best_col = col
        code_col = best_col
        
    st.subheader("📋 上傳的股票清單 (點選下方表格任一列即可顯示該股票 K 線圖與技術指標)")
    
    event = st.dataframe(
        df_stocks, 
        use_container_width=True, 
        selection_mode="single-row", 
        on_select="rerun",
        key="stock_table"
    )
    
    selected_rows = event.selection.rows if hasattr(event, 'selection') else []
    if selected_rows:
        idx = selected_rows[0]
        selected_code = str(df_stocks.iloc[idx][code_col]).strip()
    else:
        selected_code = str(df_stocks.iloc[0][code_col]).strip()
else:
    st.info("請從左側上傳 Excel 股票清單檔案。")
    selected_code = default_code

selected_code = ''.join(filter(str.isdigit, str(selected_code))).zfill(4)
ticker_symbol = f"{selected_code}{suffix}"

st.divider()
st.subheader(f"📈 {selected_code} 技術分析圖表 ({sub_indicator})")

# 下載歷史股價資料並繪圖
try:
    df = yf.download(ticker_symbol, period="1Y")
    
    if df.empty:
        st.error(f"找不到 {ticker_symbol} 的歷史股價資料，請檢查代號或市場別。")
    else:
        if hasattr(df.columns, 'levels') and len(df.columns.levels) > 1:
            df.columns = df.columns.get_level_values(0)
            
        df.columns = [str(col).capitalize() for col in df.columns]
        
        if 'Close' not in df.columns:
            st.error(f"資料欄位異常，找不到 Close 欄位。現有欄位: {list(df.columns)}")
        else:
            # 確保資料為數值型態
            for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # 計算均線 (20MA, 60MA, 120MA)
            df['MA20'] = df['Close'].rolling(window=20).mean()
            df['MA60'] = df['Close'].rolling(window=60).mean()
            df['MA120'] = df['Close'].rolling(window=120).mean()

            # 計算成交量顏色 (紅漲綠跌)
            df['VolColor'] = ['red' if c >= o else 'green' for c, o in zip(df['Close'], df['Open'])]

            # 計算 MACD
            exp12 = df['Close'].ewm(span=12, adjust=False).mean()
            exp26 = df['Close'].ewm(span=26, adjust=False).mean()
            df['MACD_ DIF'] = exp12 - exp26
            df['MACD_DEM'] = df['MACD_ DIF'].ewm(span=9, adjust=False).mean()
            df['MACD_OSC'] = (df['MACD_ DIF'] - df['MACD_DEM']) * 2

            # 計算 KD (9日)
            low_min = df['Low'].rolling(window=9).min()
            high_max = df['High'].rolling(window=9).max()
            rsv = (df['Close'] - low_min) / (high_max - low_min) * 100
            rsv = rsv.fillna(50)
            k_list, d_list = [50.0], [50.0]
            for r in rsv[1:]:
                k_val = (2/3) * k_list[-1] + (1/3) * r
                d_val = (2/3) * d_list[-1] + (1/3) * k_val
                k_list.append(k_val)
                d_list.append(d_val)
            df['K'] = k_list
            df['D'] = d_list

            # 計算 RSI (14日)
            delta = df['Close'].diff()
            gain = delta.clip(lower=0)
            loss = -delta.clip(upper=0)
            avg_gain = gain.rolling(window=14).mean()
            avg_loss = loss.rolling(window=14).mean()
            rs = avg_gain / avg_loss
            df['RSI'] = 100 - (100 / (1 + rs))

            # 計算 DMI (14日)
            df['H-L'] = df['High'] - df['Low']
            df['H-PC'] = abs(df['High'] - df['Close'].shift(1))
            df['L-PC'] = abs(df['Low'] - df['Close'].shift(1))
            df['TR'] = df[['H-L', 'H-PC', 'L-PC']].max(axis=1)
            df['+DM'] = df['High'].diff()
            df['-DM'] = -df['Low'].diff()
            df['+DM'] = df.apply(lambda row: row['+DM'] if row['+DM'] > row['-DM'] and row['+DM'] > 0 else 0, axis=1)
            df['-DM'] = df.apply(lambda row: row['-DM'] if row['-DM'] > row['+DM'] and row['-DM'] > 0 else 0, axis=1)
            
            tr14 = df['TR'].rolling(window=14).sum()
            plus_di = 100 * (df['+DM'].rolling(window=14).sum() / tr14)
            minus_di = 100 * (df['-DM'].rolling(window=14).sum() / tr14)
            dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
            adx = dx.rolling(window=14).mean()
            df['+DI'] = plus_di
            df['-DI'] = minus_di
            df['ADX'] = adx

            # 建立多子圖版面 (Row 1: K線+均線, Row 2: 成交量, Row 3: 選擇的技術指標)
            fig = make_subplots(
                rows=3, cols=1, 
                shared_xaxes=True, 
                vertical_spacing=0.03,
                row_heights=[0.5, 0.2, 0.3]
            )

            # 1. K線圖與均線 (Row 1)
            fig.add_trace(
                go.Candlestick(
                    x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
                    name='K線', increasing_line_color='red', decreasing_line_color='green'
                ), row=1, col=1
            )
            fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], line=dict(color='orange', width=1.5), name='20MA'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['MA60'], line=dict(color='blue', width=1.5), name='60MA'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['MA120'], line=dict(color='purple', width=1.5), name='120MA'), row=1, col=1)

            # 2. 成交量 (Row 2)
            fig.add_trace(
                go.Bar(
                    x=df.index, y=df['Volume'], name='成交量',
                    marker_color=df['VolColor']
                ), row=2, col=1
            )

            # 3. 技術指標 (Row 3)
            if sub_indicator == "MACD":
                fig.add_trace(go.Scatter(x=df.index, y=df['MACD_ DIF'], line=dict(color='orange', width=1), name='DIF'), row=3, col=1)
                fig.add_trace(go.Scatter(x=df.index, y=df['MACD_DEM'], line=dict(color='blue', width=1), name='DEM'), row=3, col=1)
                fig.add_trace(go.Bar(x=df.index, y=df['MACD_OSC'], name='MACD柱狀圖', marker_color=['red' if val >= 0 else 'green' for val in df['MACD_OSC']]), row=3, col=1)
            elif sub_indicator == "KD":
                fig.add_trace(go.Scatter(x=df.index, y=df['K'], line=dict(color='orange', width=1.2), name='K值'), row=3, col=1)
                fig.add_trace(go.Scatter(x=df.index, y=df['D'], line=dict(color='blue', width=1.2), name='D值'), row=3, col=1)
            elif sub_indicator == "RSI":
                fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='purple', width=1.2), name='RSI (14)'), row=3, col=1)
            elif sub_indicator == "DMI":
                fig.add_trace(go.Scatter(x=df.index, y=df['+DI'], line=dict(color='red', width=1.2), name='+DI'), row=3, col=1)
                fig.add_trace(go.Scatter(x=df.index, y=df['-DI'], line=dict(color='green', width=1.2), name='-DI'), row=3, col=1)
                fig.add_trace(go.Scatter(x=df.index, y=df['ADX'], line=dict(color='orange', width=1.2), name='ADX'), row=3, col=1)

            # 圖表排版設定
            fig.update_layout(
                xaxis_rangeslider_visible=False,
                height=750,
                margin=dict(l=20, r=20, t=30, b=20),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )

            st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"下載歷史股價時發生錯誤: {e}")
