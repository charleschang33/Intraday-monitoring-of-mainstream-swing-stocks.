import io
import numpy as np
import pandas as pd
import streamlit as st

# 設定網頁版面
st.set_page_config(
    page_title="丹尼爾波段主流股盤中監控系統", page_icon="📈", layout="wide"
)


def main():
  st.title("🚀 丹尼爾波段主流股盤中監控與篩選系統")
  st.markdown(
      "本系統根據丹尼爾波段主流股戰法設計，支援上傳個股 Excel 清單，並依據技術面與籌碼條件進行自動化篩選與資金控管計算。"
  )

  # 側邊欄：檔案上傳與參數設定
  st.sidebar.header("📁 資料與策略設定")
  uploaded_file = st.sidebar.file_uploader(
      "上傳股票清單 Excel 檔案", type=["xlsx", "xls"]
  )

  st.sidebar.subheader("⚙️ 篩選條件設定")
  price_min = st.sidebar.number_input(推薦成交價下限, value=10.0, step=1.0)
  price_max = st.sidebar.number_input(推薦成交價上限, value=200.0, step=5.0)

  enable_new_high = st.sidebar.checkbox("股價創 10 日新高", value=True)
  enable_ma_tight = st.sidebar.checkbox("股價與 20MA / 60MA 糾結", value=False)

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
      # 支援多個分頁選擇
      xls = pd.ExcelFile(uploaded_file)
      sheet_name = st.sidebar.selectbox("選擇 Excel 分頁 (Sheet)", xls.sheet_names)

      # 讀取資料
      df = pd.read_excel(uploaded_file, sheet_name=sheet_name)

      # 針對表頭進行自動對齊清理 (相容不同的匯出格式)
      if "Ticker symbol" not in df.columns and 0 in df.index:
        df.columns = df.iloc[0]
        df = df.drop(0).reset_index(drop=True)

      st.success(f"成功載入資料！共計 {len(df)} 檔股票。")

      # 顯示原始資料預覽
      with st.expander("🔍 檢視原始資料預覽"):
        st.dataframe(df.head(10))

      # 資料欄位處理與防錯
      # 假設欄位包含：Ticker symbol, Price, High, Low, Change (%), Volume, Industry 等
      # 確保數值欄位為 float / int
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

      # 模擬 10 日新高條件 (若資料表有 High 及 High (10d) 或簡化以 High >= High (10wk) 等替代，此處提供介面與邏輯擴充點)
      st.markdown("---")
      st.subheader("🎯 篩選結果與資金控管對照表")

      if not filtered_df.empty:
        # 計算資金控管建議張數
        # 假設停損價以當日低點或自訂估算 (示範：以 Low 作為停損參考價)
        if "Price" in filtered_df.columns and "Low" in filtered_df.columns:
          filtered_df["假設停損價"] = filtered_df["Low"] * 0.98  # 範例估算
          filtered_df["每張風險金額"] = (
              filtered_df["Price"] - filtered_df["假設停損價"]
          ) * 1000
          max_loss_amount = total_capital * max_risk_pct
          filtered_df["建議買進張數"] = np.where(
              filtered_df["每張風險金額"] > 0,
              np.floor(
                  max_loss_amount / filtered_df["每張風險金額"]
              ),  #[cite: 1]
              0,
          )

        st.dataframe(filtered_df, use_container_width=True)

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
        "👈 請從左側側邊欄上傳您的股票清單 Excel 檔案（例如包含價量、籌碼與技術指標的檔案）。"
    )

    # 顯示戰法操作提醒
    st.markdown("### 📚 丹尼爾波段主流股操作口訣提醒")
    st.markdown(
        """
        1. **判斷大盤多空**：確認大盤／櫃買指數短線偏多時才積極進場[cite: 1]。
        2. **選主流**：挑選族群強度高、法人籌碼青睞的強勢股[cite: 1]。
        3. **進場點**：突破買（長紅突破平切線）或拉回買（突破隔天量縮拉回 10:30 走穩）[cite: 1]。
        4. **資金控管**：單筆最大虧損嚴格控制在總資金的 1% ~ 2%[cite: 1]。
        """
    )


if __name__ == "__main__":
  main()
