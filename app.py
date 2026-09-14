import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go

# 設定網頁版面
st.set_page_config(page_title="個股技術分析與 K 線圖", layout="wide")

st.title("📊 個股技術分析與 K 線圖 (搭配 20MA / 60MA / 120MA)")

# 側邊欄：檔案上傳與市場別設定
st.sidebar.header("📁 資料設定")
uploaded_file = st.sidebar.file_uploader("上傳股票清單 Excel 檔案", type=["xlsx", "csv"])

market_suffix = st.sidebar.selectbox("市場別預設", [".TW (上市)", ".TWO (上櫃)"], index=0)
suffix = ".TW" if "TW (上市)" in market_suffix else ".TWO"

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
    # 自動尋找代號欄位
    code_col = None
    for col in df_stocks.columns:
        if any(k in str(col).lower() for k in ['代號', 'code', '股票', 'stock']):
            code_col = col
            break
    if code_col is None:
        code_col = df_stocks.columns[0]
        
    st.subheader("📋 上傳的股票清單 (點選下方表格任一列即可顯示該股票 K 線圖)")
    
    # 啟用 Streamlit 內建表格單行選取功能
    event = st.dataframe(
        df_stocks, 
        use_container_width=True, 
        selection_mode="single-row", 
        on_select="rerun",
        key="stock_table"
    )
    
    # 取得被點選的股票代號
    selected_rows = event.selection.rows if hasattr(event, 'selection') else []
    if selected_rows:
        idx = selected_rows[0]
        selected_code = str(df_stocks.iloc[idx][code_col]).strip()
    else:
        # 預設選取第一筆
        selected_code = str(df_stocks.iloc[0][code_col]).strip()
else:
    st.info("請從左側上傳 Excel 股票清單檔案。")
    selected_code = default_code

# 處理股票代號格式
selected_code = ''.join(filter(str.isdigit, selected_code)).zfill(4)
ticker_symbol = f"{selected_code}{suffix}"

st.divider()
st.subheader(f"📈 {selected_code} 日 K 線圖與均線走勢")

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

            # 加入均線
            fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], line=dict(color='orange', width=1.5), name='20MA (月線)'))
            fig.add_trace(go.Scatter(x=df.index, y=df['MA60'], line=dict(color='blue', width=1.5), name='60MA (季線)'))
            fig.add_trace(go.Scatter(x=df.index, y=df['MA120'], line=dict(color='purple', width=1.5), name='120MA (半年線)'))

            fig.update_layout(
                xaxis_rangeslider_visible=False,
                height=600,
                margin=dict(l=20, r=20, t=30, b=20),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )

            st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"下載歷史股價時發生錯誤: {e}")
