import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go

# 設定網頁版面
st.set_page_config(page_title="個股技術分析與 K 線圖", layout="wide")

st.title("📊 個股技術分析與 K 線圖 (搭配 20MA / 60MA / 120MA)")

# 側邊欄：資料與策略設定
st.sidebar.header("📁 資料與策略設定")
uploaded_file = st.sidebar.file_uploader("上傳股票清單 Excel 檔案", type=["xlsx", "csv"])

# 預設股票代號清單
stock_list = ["2305", "2330", "6226", "2317"]
df_stocks = None

if uploaded_file is not None:
    try:
        if uploaded_file.name.endswith('.csv'):
            df_stocks = pd.read_csv(uploaded_file)
        else:
            df_stocks = pd.read_excel(uploaded_file)
        
        # 尋找可能包含股票代號的欄位
        code_col = None
        for col in df_stocks.columns:
            if any(k in str(col).lower() for k in ['代號', 'code', '股票', 'stock']):
                code_col = col
                break
        if code_col is None:
            code_col = df_stocks.columns[0]
            
        # 清理並過濾掉 NaN 或空值
        raw_list = df_stocks[code_col].dropna().astype(str).str.zfill(4).tolist()
        stock_list = [s for s in raw_list if s.lower() != 'nan' and s.strip() != '']
        if not stock_list:
            stock_list = ["2305", "2330", "6226", "2317"]
    except Exception as e:
        st.sidebar.error(f"讀取上傳檔案發生錯誤: {e}")

# 選擇要檢視 K 線圖的股票代號
selected_code = st.sidebar.selectbox("選擇要檢視 K 線圖的股票代號", stock_list)

# 加上台股代號後綴 (預設上市用 .TW，若無法抓取可自行切換)
market_suffix = st.sidebar.selectbox("市場別", [".TW (上市)", ".TWO (上櫃)"], index=0)
suffix = ".TW" if "TW (上市)" in market_suffix else ".TWO"

# 防呆處理：確保 selected_code 有值且不是 nan
if selected_code is None or pd.isna(selected_code) or str(selected_code).lower() == 'nan':
    selected_code = "2330"

ticker_symbol = f"{str(selected_code).strip()}{suffix}"

st.subheader(f"📈 {selected_code} 日 K 線圖與均線走勢")

# 下載歷史股價資料並繪圖
try:
    # 下載近 1 年資料
    df = yf.download(ticker_symbol, period="1Y")
    
    if df.empty:
        st.error(f"找不到 {ticker_symbol} 的歷史股價資料，請檢查代號或市場別。")
    else:
        # 1. 處理 yfinance 可能產生的 MultiIndex 欄位
        if hasattr(df.columns, 'levels') and len(df.columns.levels) > 1:
            df.columns = df.columns.get_level_values(0)
            
        # 2. 將所有欄位名稱統一轉為首字大寫 (確保有 Open, High, Low, Close)
        df.columns = [str(col).capitalize() for col in df.columns]
        
        if 'Close' not in df.columns:
            st.error(f"資料欄位異常，找不到 Close 欄位。現有欄位: {list(df.columns)}")
        else:
            # 計算均線 (20MA, 60MA, 120MA)
            df['MA20'] = df['Close'].rolling(window=20).mean()
            df['MA60'] = df['Close'].rolling(window=60).mean()
            df['MA120'] = df['Close'].rolling(window=120).mean()

            # 建立 Plotly 圖表
            fig = go.Figure()

            # 加入 K 線圖 (設定紅漲綠跌)
            fig.add_trace(
                go.Candlestick(
                    x=df.index,
                    open=df['Open'],
                    high=df['High'],
                    low=df['Low'],
                    close=df['Close'],
                    name='K線',
                    increasing_line_color='red',   # 上漲為紅色
                    decreasing_line_color='green'  # 下跌為綠色
                )
            )

            # 加入 20MA (月線)
            fig.add_trace(go.Scatter(
                x=df.index, y=df['MA20'], line=dict(color='orange', width=1.5), name='20MA (月線)'
            ))

            # 加入 60MA (季線)
            fig.add_trace(go.Scatter(
                x=df.index, y=df['MA60'], line=dict(color='blue', width=1.5), name='60MA (季線)'
            ))

            # 加入 120MA (半年線)
            fig.add_trace(go.Scatter(
                x=df.index, y=df['MA120'], line=dict(color='purple', width=1.5), name='120MA (半年線)'
            ))

            # 圖表排版設定
            fig.update_layout(
                xaxis_rangeslider_visible=False,
                height=600,
                margin=dict(l=20, r=20, t=30, b=20),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )

            st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"下載歷史股價時發生錯誤: {e}")
