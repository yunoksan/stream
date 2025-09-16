import streamlit as st
import cv2
import numpy as np
from PIL import Image

st.title("📷 바코드 스캐너 (OpenCV QRCodeDetector)")

img_file = st.camera_input("QR/바코드를 카메라로 찍어주세요")

if img_file:
    img = Image.open(img_file)
    cv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

    detector = cv2.QRCodeDetector()
    data, vertices, _ = detector.detectAndDecode(cv_img)

    if data:
        st.success(f"인식된 코드: {data}")
    else:
        st.error("❌ 인식 실패")
