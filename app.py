import io
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

# 設定網頁版面
st.set_page_config(
    page_title="丹尼爾波段主流股盤中監控系統", page_icon="📈", layout="wide"
)


def main():
  st.title("🚀 丹尼爾波段主流股盤中監控與互動圖表系統")
  st.markdown(
      "本系統根據丹尼爾波段主流股戰法設計，支援上傳個股 Excel 清單、自動化篩選、資金控管計算，以及個股互動式 K"
      " 線圖與均線檢視。"
  )

  # 側邊欄：檔案上傳與參數設定
  st.sidebar.header("📁 資料與策略設定")
  uploaded_file = st.sidebar.file_uploader(
      "上傳股票清單 Excel 檔案", type=["xlsx", "xls"]
  )

  st.sidebar.subheader("⚙️ 篩選條件設定")
  price_min = st.sidebar.number_input("推薦成交價下限", value=10.0, step=1.0)
  price_max = st.sidebar.number_input("推薦成交價上限", value=200.0, step=5.0)

  st.sidebar.subheader("💰 資金控管設定")
  total_capital = st.sidebar.number_input(
      "總資金 (元)", value=1000000, step=100000
  )
  max_risk_pct = (
      st.sidebar.slider("單筆最大虧損比例 (%)", 0.5, 3.0, 1.0, 0.5) / 100.0
  )

  if uploaded_file is not None:
    try:
      # 讀取 Excel 檔案
      xls = pd.ExcelFile(uploaded_file)
      sheet_name = st.sidebar.selectbox("選擇 Excel 分頁 (Sheet)", xls.sheet_names)

      # 讀取資料
      df = pd.read_excel(uploaded_file, sheet_name=sheet_name)

      # 針對表頭進行自動對齊清理
      if "Ticker symbol" not in df.columns and 0 in df.index:
        df.columns = df.iloc[0]
        df = df.drop(0).reset_index(drop=True)

      st.success(f"成功載入資料！共計 {len(df)} 檔股票。")

      # 資料欄位處理與防錯
      numeric_cols = [
          "Price",
          "High",
          "Low",
          "Change (%)",
          "Volume",
          "High (52wk)",
          "Low (52wk)",
      ]
      for col in numeric_cols:
        if col in df.columns:
          df[col] = pd.to_numeric(df[col], errors="coerce")

      # 執行篩選邏輯
      filtered_df = df.copy()

      if "Price" in filtered_df.columns:
        filtered_df = filtered_df[
            (filtered_df["Price"] >= price_min)
            & (filtered_df["Price"] <= price_max)
        ]

      st.markdown("---")
      st.subheader("🎯 篩選結果與資金控管對照表")

      if not filtered_df.empty:
        # 計算資金控管建議張數
        if "Price" in filtered_df.columns and "Low" in filtered_df.columns:
          filtered_df["假設停損價"] = filtered_df["Low"] * 0.98
          filtered_df["每張風險金額"] = (
              filtered_df["Price"] - filtered_df["假設停損價"]
          ) * 1000
          max_loss_amount = total_capital * max_risk_pct
          filtered_df["建議買進張數"] = np.where(
              filtered_df["每張風險金額"] > 0,
              np.floor(max_loss_amount / filtered_df["每張風險金額"]),
              0,
          )

        st.dataframe(filtered_df, use_container_width=True)

        # ---------------------------------------------------------
        # 新增：個股 K 線圖互動區塊
        # ---------------------------------------------------------
        st.markdown("---")
        st.subheader("📊 個股技術分析與 K 線圖 (搭配 20MA / 60MA / 120MA)")

        # 抓取可用股票代號清單
        ticker_col = (
            "Ticker symbol"
            if "Ticker symbol" in filtered_df.columns
            else filtered_df.columns[3]
        )
        stock_list = filtered_df[ticker_col].dropna().astype(str).tolist()

        if stock_list:
          selected_stock = st.selectbox(
              "選擇要檢視 K 線圖的股票代號", stock_list
          )

          if selected_stock:
            # 轉換為 yfinance 格式 (台股加上 .TW)
            yf_ticker = (
                selected_stock + ".TW"
                if not selected_stock.endswith((".TW", ".TWO"))
                else selected_stock
            )

            with st.spinner(f"正在載入 {yf_ticker} 的歷史股價資料..."):
              try:
                hist = yf.download(yf_ticker, period="6mo", interval="1d")
                if not hist.empty:
                  # 處理 MultiIndex 欄位名稱（yfinance有時會回傳多層欄位）
                  if isinstance(hist.columns, pd.MultiIndex):
                    hist.columns = hist.columns.droplevel(1)

                  # 計算均線
                  hist["MA20"] = hist["Close"].rolling(window=20).mean()
                  hist["MA60"] = hist["Close"].rolling(window=60).mean()
                  hist["MA120"] = hist["Close"].rolling(window=120).mean()

                  # 繪製 Plotly 圖表
                  fig = go.Figure()

                  # 1. K 線圖
                  fig.add_trace(
                      go.Candlestick(
                          x=hist.index,
                          open=hist["Open"],
                          high=hist["High"],
                          low=hist["Low"],
                          close=hist["Close"],
                          name="K線",
                      )
                  )

                  # 2. 均線
                  fig.add_trace(
                      go.Scatter(
                          x=hist.index,
                          y=hist["MA20"],
                          line=dict(color="orange", width=1.5),
                          name="20MA (月線)",
                      )
                  )
                  fig.add_trace(
                      go.Scatter(
                          x=hist.index,
                          y=hist["MA60"],
                          line=dict(color="blue", width=1.5),
                          name="60MA (季線)",
                      )
                  )
                  fig.add_trace(
                      go.Scatter(
                          x=hist.index,
                          y=hist["MA120"],
                          line=dict(color="purple", width=1.5),
                          name="120MA (半年線)",
                      )
                  )

                  fig.update_layout(
                      title=f"{selected_stock} 日 K 線圖與均線走勢",
                      yaxis_title="價格 (TWD)",
                      xaxis_rangeslider_visible=False,
                      height=600,
                      template="plotly_white",
                  )

                  st.plotly_chart(fig, use_container_width=True)
                else:
                  st.warning(
                      f"無法取得代號 {selected_stock} 的歷史資料，請確認代號是否正確。"
                  )
              except Exception as e:
                st.error(f下載歷史股價時發生錯誤: {e})

        # 下載篩選後的 CSV
        csv = filtered_df.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            label="📥 下載篩選後清單 (CSV)",
            data=csv,
            file_name="filtered_stocks.csv",
            mime="text/csv",
        )
      else:
        st.warning("沒有符合目前篩選條件的股票，請調整側邊欄的篩選參數。")

    except Exception as e:
      st.error(f"讀取或處理檔案時發生錯誤: {e}")
  else:
    st.info(
        "👈 請從左側側邊欄上傳您的股票清單 Excel 檔案（例如 Stocks_0914.xlsx）。"
    )

    st.markdown("### 📚 丹尼爾波段主流股操作口訣提醒")
    st.markdown(
        """
        1. **判斷大盤多空**：確認大盤／櫃買指數短線偏多時才積極進場。
        2. **選主流**：挑選族群強度高、法人籌碼青睞的強勢股。
        3. **進場點**：突破買（長紅突破平切線）或拉回買（突破隔天量縮拉回 10:30 走穩）。
        4. **資金控管**：單筆最大虧損嚴格控制在總資金的 1% ~ 2%。
        """
    )


if __name__ == "__main__":
  main()
