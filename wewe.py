import streamlit as st
from pyzbar.pyzbar import decode
from PIL import Image
import requests
import base64

st.title("📷 바코드 / QR 코드 인식")
API_KEY = "YOUR_GOOGLE_CLOUD_API_KEY"
url = f"https://vision.googleapis.com/v1/images:annotate?key={API_KEY}"

st.title("📷 바코드 스캐너 (Google Vision API)")

img_file = st.camera_input("코드를 카메라로 찍어주세요")

if img_file:
    img = Image.open(img_file)
    decoded = decode(img)

    if decoded:
        for d in decoded:
            st.success(f"인식된 코드: {d.data.decode('utf-8')}")
    else:
        st.error("❌ 코드를 인식하지 못했습니다.")
    content = base64.b64encode(img_file.getvalue()).decode("utf-8")
    body = {
        "requests": [
            {
                "image": {"content": content},
                "features": [{"type": "DOCUMENT_TEXT_DETECTION"}]  # 또는 "BARCODE_DETECTION"
            }
        ]
    }
    response = requests.post(url, json=body)
    result = response.json()
    st.write(result)
