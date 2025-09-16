import streamlit as st
from pyzbar.pyzbar import decode
from PIL import Image

st.title("📷 바코드 / QR 코드 인식")

img_file = st.camera_input("코드를 카메라로 찍어주세요")

if img_file:
    img = Image.open(img_file)
    decoded = decode(img)

    if decoded:
        for d in decoded:
            st.success(f"인식된 코드: {d.data.decode('utf-8')}")
    else:
        st.error("❌ 코드를 인식하지 못했습니다.")
