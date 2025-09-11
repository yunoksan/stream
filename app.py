import streamlit as st
import pandas as pd
import os
import re
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

# CSV 파일 경로
FILE_PATH = "products.csv"

@st.cache_data
def load_data():
    if not os.path.exists(FILE_PATH) or os.path.getsize(FILE_PATH) == 0:
        st.error(f"❌ {FILE_PATH} 파일이 없거나 비어있습니다.")
        return pd.DataFrame()
    return pd.read_csv(FILE_PATH)

df = load_data()

# EA 환산
def convert_to_ea(row):
    unit = str(row.get("단위", ""))
    price = float(row.get("가격", 0))
    if "Box" in unit:
        try:
            count_str = unit.split("(")[1].split("EA")[0].replace(")", "")
            count = int(count_str)
        except Exception:
            count = 1
        return price / max(count, 1)
    return price

# 규격 정렬용 (g/kg/ml/l → g/ml 기준 1000배 환산)
def size_to_base(size_str):
    s = str(size_str).lower().strip()
    m = re.match(r"(\d+)(g|kg|ml|l)", s)
    if not m:
        return float("inf")
    num, unit = m.groups()
    num = int(num)
    if unit in ("kg", "l"):
        num *= 1000
    return num

# ------- 데이터 전처리 -------
if not df.empty:
    df["가격"] = pd.to_numeric(df["가격"], errors="coerce").fillna(0)
    df["이전EA가격"] = pd.to_numeric(df.get("이전EA가격", 0), errors="coerce").fillna(0)
    df["EA가격"] = df.apply(convert_to_ea, axis=1)
    df["표준상품"] = df["브랜드"].astype(str) + " " + df["품명"].astype(str) + " " + df["규격"].astype(str)

st.title("📦 식자재 가격 비교 대시보드")

# ================= 좌측 패널(사이드바) =================
with st.sidebar:
    st.header("📂 단계별 검색 패널")

    # 1) 상품
    all_products = sorted(df["품명"].dropna().unique()) if not df.empty else []
    selected_product = st.selectbox("상품명", [""] + list(all_products), key="sel_product")

    # 2) 브랜드 (상품 선택에 종속)
    if selected_product:
        brand_options = sorted(df[df["품명"] == selected_product]["브랜드"].dropna().unique())
    else:
        brand_options = sorted(df["브랜드"].dropna().unique()) if not df.empty else []
    brand_widget_key = f"sel_brand__{selected_product or 'ALL'}"
    selected_brand = st.selectbox("브랜드", [""] + list(brand_options), key=brand_widget_key)

    # 3) 규격 (상품/브랜드 종속, 작은 단위 → 큰 단위 정렬)
    size_options = []
    if selected_product and selected_brand:
        size_options = df[(df["품명"] == selected_product) & (df["브랜드"] == selected_brand)]["규격"].dropna().unique()
    elif selected_product:
        size_options = df[df["품명"] == selected_product]["규격"].dropna().unique()
    elif selected_brand:
        size_options = df[df["브랜드"] == selected_brand]["규격"].dropna().unique()

    size_options = sorted(size_options, key=size_to_base)

    size_widget_key = f"sel_size__{selected_product or 'ALL'}__{selected_brand or 'ALL'}"
    if len(size_options) > 0:
        selected_size = st.selectbox("규격", [""] + list(size_options), key=size_widget_key)
    else:
        selected_size = ""

    # 선택 검색어를 우측 키워드창으로 전달
    if st.button("➡️ 선택 검색어를 키워드창으로 보내기"):
        terms = []
        if selected_product: terms.append(selected_product)
        if selected_brand:   terms.append(selected_brand)
        if selected_size:    terms.append(selected_size)
        keyword_str = " ".join(terms)
        if keyword_str.strip():
            st.session_state["keyword"] = keyword_str
            st.success(f"키워드창에 '{keyword_str}' 입력됨")
            try:
                st.rerun()
            except Exception:
                st.experimental_rerun()
        else:
            st.warning("선택 조건이 비어있습니다.")

# ================= 우측: 키워드 검색 & 비교 =================
keyword = st.text_input("🔍 키워드 검색 (예: 참깨, 또는 '참 5k')",
                        value=st.session_state.get("keyword", ""),
                        key="keyword_input")

if keyword and not df.empty:
    kws = keyword.split()
    filtered = df.copy()
    for kw in kws:
        mask = (
            filtered["브랜드"].astype(str).str.contains(kw, case=False, na=False)
            | filtered["품명"].astype(str).str.contains(kw, case=False, na=False)
            | filtered["규격"].astype(str).str.contains(kw, case=False, na=False)
            | filtered["판매처"].astype(str).str.contains(kw, case=False, na=False)
        )
        filtered = filtered[mask]
else:
    filtered = pd.DataFrame()

if filtered.empty:
    st.info("좌측에서 선택 후 키워드창으로 보내거나, 키워드를 입력하세요.")
else:
    # 브랜드/규격별 최저 EA 요약
    product_summary = filtered.groupby(["규격", "표준상품"])["EA가격"].min().reset_index()
    product_summary["규격정렬"] = product_summary["규격"].apply(size_to_base)
    product_summary = product_summary.sort_values(by=["규격정렬", "EA가격"]).reset_index(drop=True)
    product_summary["규격별최저"] = product_summary.groupby("규격")["EA가격"].transform("min")

    # 셀렉트 옵션(규격별 최저가 ⭐)
    options_map = {
        row["표준상품"]: f"[{row['규격']}] {row['표준상품']} | 최저가 {int(row['EA가격']):,}원" +
                         (" ⭐" if row["EA가격"] == row["규격별최저"] else "")
        for _, row in product_summary.iterrows()
    }

    selected_std = st.selectbox("📌 브랜드 선택", options=list(options_map.keys()),
                                format_func=lambda x: options_map[x], key="std_select")

    if selected_std:
        sub = filtered[filtered["표준상품"] == selected_std].copy()
        # 판매처 내 중복 단위는 EA 최저가만 남기기
        sub = sub.loc[sub.groupby("판매처")["EA가격"].idxmin()].reset_index(drop=True)
        min_ea = sub["EA가격"].min()

        st.subheader(f"🔍 {selected_std} 판매처별 가격")

        disp = sub.copy()
        disp["가격"] = disp["가격"].apply(lambda v: f"{int(v):,}원")
        disp["EA가격"] = disp.apply(
            lambda r: f"{int(r['EA가격']):,}원 ⭐" if r["EA가격"] == min_ea else f"{int(r['EA가격']):,}원", axis=1
        )

        # 선택 행 반전 스타일 + 최초 로딩 시 ⭐ 자동 선택
        highlight_selected = JsCode("""
        function(params){
            if (params.node.isSelected()){
                const isDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
                if (isDark)  { return {'color':'white','backgroundColor':'black','fontWeight':'bold'}; }
                else         { return {'color':'black','backgroundColor':'white','fontWeight':'bold'}; }
            }
        }""")

        auto_select_min = JsCode("""
        function(e){
            const api = e.api;
            let done = false;
            api.forEachNode((node) => {
                const val = node.data && node.data["EA가격"];
                if (!done && typeof val === "string" && val.indexOf("⭐") !== -1){
                    node.setSelected(true);
                    api.ensureIndexVisible(node.rowIndex);
                    done = true;
                }
            });
        }""")

        gb = GridOptionsBuilder.from_dataframe(disp[["판매처", "단위", "가격", "EA가격", "갱신일"]])
        gb.configure_selection("single", use_checkbox=False)
        gb.configure_grid_options(getRowStyle=highlight_selected, onGridReady=auto_select_min)
        grid_options = gb.build()

        grid_resp = AgGrid(
            disp[["판매처", "단위", "가격", "EA가격", "갱신일"]],
            gridOptions=grid_options,
            enable_enterprise_modules=False,
            theme="streamlit",
            fit_columns_on_grid_load=True,
            update_mode="MODEL_CHANGED",
            allow_unsafe_jscode=True,
            height=300
        )

        # 선택 행 → 상세
        sel_rows = grid_resp.get("selected_rows")
        if isinstance(sel_rows, list) and len(sel_rows) > 0:
            sel = sel_rows[0]
        else:
            sel = disp.loc[disp["EA가격"].str.contains("⭐")].iloc[0].to_dict()

        base_row = sub[sub["판매처"] == sel["판매처"]].iloc[0]
        diff_val = float(base_row["EA가격"]) - float(base_row["이전EA가격"])
        if diff_val < 0:
            diff_txt = f"⬇️ {int(abs(diff_val)):,}원 하락"
        elif diff_val > 0:
            diff_txt = f"⬆️ {int(diff_val):,}원 상승"
        else:
            diff_txt = "변동 없음"

        detail = pd.DataFrame({
            "항목": ["브랜드","상품명","규격","판매처","판매단위","원시가격","EA 환산가격(현재)","이전 EA가격","가격 변동","갱신일","URL"],
            "값": [
                str(base_row["브랜드"]),
                str(base_row["품명"]),
                str(base_row["규격"]),
                str(base_row["판매처"]),
                str(base_row["단위"]),
                f"{int(base_row['가격']):,}원",
                f"{int(base_row['EA가격']):,}원" + (" ⭐" if base_row["EA가격"] == min_ea else ""),
                f"{int(base_row['이전EA가격']):,}원",
                diff_txt,
                str(base_row["갱신일"]),
                str(base_row["url"])
            ]
        })
        st.table(detail)
