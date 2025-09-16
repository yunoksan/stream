import streamlit as st
import requests
import base64

API_KEY = "YOUR_GOOGLE_CLOUD_API_KEY"
url = f"https://vision.googleapis.com/v1/images:annotate?key={API_KEY}"

st.title("📷 바코드 스캐너 (Google Vision API)")

img_file = st.camera_input("코드를 카메라로 찍어주세요")

if img_file:
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
