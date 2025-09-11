import streamlit as st
import pandas as pd
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
    # 숫자형 변환
    df["가격"] = pd.to_numeric(df["가격"], errors="coerce").fillna(0)
    df["이전EA가격"] = pd.to_numeric(df.get("이전EA가격", 0), errors="coerce").fillna(0)
    df["EA가격"] = df.apply(convert_to_ea, axis=1)

    # 표준상품
    df["표준상품"] = df["브랜드"].astype(str) + " " + df["품명"].astype(str) + " " + df["규격"].astype(str)

    # UI 시작
    st.title("📦 식자재 가격 비교 대시보드 (CSV + 이력관리)")

    # 검색창
    keyword = st.text_input("🔍 상품 검색 (예: 참깨, 또는 '참 5k')", "")

    if keyword:
        # 여러 단어로 나눠서 모두 포함하는 데이터 필터링 (AND 방식)
        keywords = keyword.split()
        filtered = df.copy()
        for kw in keywords:
            mask = (
                filtered["브랜드"].astype(str).str.contains(kw, case=False, na=False)
                | filtered["품명"].astype(str).str.contains(kw, case=False, na=False)
                | filtered["규격"].astype(str).str.contains(kw, case=False, na=False)
                | filtered["판매처"].astype(str).str.contains(kw, case=False, na=False)
            )
            filtered = filtered[mask]

        if filtered.empty:
            st.warning("검색된 상품이 없습니다.")
        else:
            # 브랜드/규격별 최저가 요약
            product_summary = (
                filtered.groupby("표준상품")["EA가격"].min().reset_index()
            )

            # 상품명과 최저가를 EM SPACE( )로 간격 넣어서 표시
            product_options = {
                row["표준상품"]: f"{row['표준상품']}  | 최저가 {int(row['EA가격']):,}원"
                for _, row in product_summary.iterrows()
            }

            # 브랜드 선택 드롭다운
            selected_product = st.selectbox(
                "📌 브랜드 선택",
                options=list(product_options.keys()),
                format_func=lambda x: product_options[x]
            )

            if selected_product:
                sub_df = filtered[filtered["표준상품"] == selected_product].reset_index(drop=True)
                min_price = sub_df["EA가격"].min()

                st.subheader(f"🔍 {selected_product} 판매처별 가격")

                # 테이블 표시 (EA가격 최저가에 ⭐ 표시)
                sub_df_display = sub_df.copy()
                sub_df_display["가격"] = sub_df_display["가격"].apply(lambda x: f"{int(x):,}원")
                sub_df_display["EA가격"] = sub_df_display.apply(
                    lambda r: f"{int(r['EA가격']):,}원 ⭐" if r["EA가격"] == min_price else f"{int(r['EA가격']):,}원",
                    axis=1
                )

                st.dataframe(sub_df_display[["판매처", "단위", "가격", "EA가격", "갱신일"]], use_container_width=True)

                # 최저가 판매처를 기본 선택
                default_index = int(sub_df[sub_df["EA가격"] == min_price].index[0])
                selected_index = st.selectbox(
                    "📌 판매처 선택",
                    [int(i) for i in sub_df.index],
                    format_func=lambda x: f"{sub_df.loc[x, '판매처']} | {int(sub_df.loc[x, '가격']):,}원 | EA:{int(sub_df.loc[x, 'EA가격']):,}원",
                    index=[int(i) for i in sub_df.index].index(default_index)
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
