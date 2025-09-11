import streamlit as st
import pandas as pd
from datetime import datetime
import os

# CSV 파일 경로
file_path = "products.csv"

# CSV 불러오기
@st.cache_data
def load_data():
    if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
        st.error(f"❌ {file_path} 파일이 없거나 비어있습니다.")
        return pd.DataFrame()
    df = pd.read_csv(file_path)
    return df

df = load_data()

# EA 환산 함수
def convert_to_ea(row):
    if "Box" in str(row["단위"]):
        try:
            count = int(str(row["단위"]).split("(")[1].replace("EA)", ""))
        except Exception:
            count = 1
        return float(row["가격"]) / max(count, 1)
    else:
        return float(row["가격"])

if not df.empty:
    # EA가격 계산
    df["가격"] = pd.to_numeric(df["가격"], errors="coerce").fillna(0)
    df["이전EA가격"] = pd.to_numeric(df.get("이전EA가격", 0), errors="coerce").fillna(0)
    df["EA가격"] = df.apply(convert_to_ea, axis=1)

    # 표준상품
    df["표준상품"] = df["브랜드"].astype(str) + " " + df["품명"].astype(str) + " " + df["규격"].astype(str)

    # UI 시작
    st.title("📦 식자재 가격 비교 대시보드 (CSV + 이력관리)")

    keyword = st.text_input("🔍 상품 검색 (예: 참깨)", "")

    if keyword:
        filtered = df[df["품명"].astype(str).str.contains(keyword, case=False, na=False)]

        if filtered.empty:
            st.warning("검색된 상품이 없습니다.")
        else:
            unique_products = filtered["표준상품"].unique()
            selected_product = st.selectbox("📌 브랜드 선택", unique_products)

            if selected_product:
                sub_df = filtered[filtered["표준상품"] == selected_product].reset_index(drop=True)

                # 최저가 찾기
                min_price = sub_df["EA가격"].min()

                st.subheader(f"🔍 {selected_product} 판매처별 가격")

                # 복사본 생성
                sub_df_display = sub_df.copy()

                # 포맷 적용 (천단위 콤마, 원 단위)
                sub_df_display["가격"] = sub_df_display["가격"].apply(lambda x: f"{int(x):,}원")
                sub_df_display["EA가격"] = sub_df_display.apply(
                    lambda r: f"{int(r['EA가격']):,}원 ⭐" if r["EA가격"] == min_price else f"{int(r['EA가격']):,}원",
                    axis=1
                )

                st.dataframe(sub_df_display[["판매처", "단위", "가격", "EA가격", "갱신일"]], use_container_width=True)

                # 판매처 선택
                selected_index = st.selectbox(
                    "📌 판매처 선택",
                    sub_df.index,
                    format_func=lambda x: f"{sub_df.loc[x, '판매처']} | {int(sub_df.loc[x, '가격']):,}원 | EA:{int(sub_df.loc[x, 'EA가격']):,}원"
                )

                # 상세 정보
                row = sub_df.loc[selected_index]

                st.subheader("📋 상세 정보 (선택된 판매처)")

                diff_val = float(row["EA가격"]) - float(row["이전EA가격"])
                if diff_val < 0:
                    diff_text = f"⬇️ {int(abs(diff_val)):,}원 하락"
                elif diff_val > 0:
                    diff_text = f"⬆️ {int(diff_val):,}원 상승"
                else:
                    diff_text = "변동 없음"

                detail_table = pd.DataFrame({
                    "항목": [
                        "브랜드", "상품명", "규격", "판매처", "판매단위",
                        "원시가격", "EA 환산가격(현재)", "이전 EA가격", "가격 변동", "갱신일", "URL"
                    ],
                    "값": [
                        str(row["브랜드"]),
                        str(row["품명"]),
                        str(row["규격"]),
                        str(row["판매처"]),
                        str(row["단위"]),
                        f"{int(row['가격']):,}원",
                        f"{int(row['EA가격']):,}원" + (" ⭐" if row["EA가격"] == min_price else ""),
                        f"{int(row['이전EA가격']):,}원",
                        diff_text,
                        str(row["갱신일"]),
                        str(row["url"])
                    ]
                })

                st.table(detail_table)

                # 최저가 안내
                if row["EA가격"] == min_price:
                    st.success(f"⭐ 이 상품은 현재 최저가 ({int(min_price):,}원)")
                else:
                    st.info(f"이 상품의 최저가는 {int(min_price):,}원 입니다.")
