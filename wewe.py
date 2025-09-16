import streamlit as st
from pyzbar.pyzbar import decode
from PIL import Image

st.title("📷 바코드 스캐너 (Streamlit 카메라)")

# 카메라 열기
img_file = st.camera_input("바코드를 카메라에 비추고 촬영하세요")

if img_file:
    # Streamlit이 BytesIO 형태로 제공 → PIL로 열기
    img = Image.open(img_file)

    # 바코드 해석
    decoded = decode(img)
    if decoded:
        for d in decoded:
            st.success(f"인식된 바코드: {d.data.decode('utf-8')}")
    else:
        st.error("❌ 바코드를 인식하지 못했습니다. 다시 시도해주세요.")
