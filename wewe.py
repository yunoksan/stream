import streamlit as st
import cv2
import numpy as np
from PIL import Image
import requests
import json

# QR 코드 및 바코드 검출기 초기화
qr_detector = cv2.QRCodeDetector()

# 바코드 검출을 위한 기본 설정
def detect_barcode_opencv(image):
    """OpenCV를 사용한 바코드 검출 (기본적인 형태 검출)"""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # 바코드의 수직선 검출을 위한 커널
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (21, 7))
    
    # 그라디언트 계산
    grad_x = cv2.Sobel(gray, ddepth=cv2.CV_32F, dx=1, dy=0, ksize=-1)
    grad_y = cv2.Sobel(gray, ddepth=cv2.CV_32F, dx=0, dy=1, ksize=-1)
    
    gradient = cv2.subtract(grad_x, grad_y)
    gradient = cv2.convertScaleAbs(gradient)
    
    # 블러 및 쓰레시홀드 적용
    blurred = cv2.blur(gradient, (9, 9))
    (_, thresh) = cv2.threshold(blurred, 225, 255, cv2.THRESH_BINARY)
    
    # 모폴로지 연산
    closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
    closed = cv2.erode(closed, None, iterations=4)
    closed = cv2.dilate(closed, None, iterations=4)
    
    # 컨투어 검출
    contours, _ = cv2.findContours(closed.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    barcode_regions = []
    for contour in contours:
        (x, y, w, h) = cv2.boundingRect(contour)
        # 바코드 비율 확인 (가로가 세로보다 훨씬 긴 형태)
        if w > 100 and h > 20 and w / h > 3:
            barcode_regions.append((x, y, w, h))
    
    return barcode_regions

try:
    from pyzbar import pyzbar
    PYZBAR_AVAILABLE = True
    print("pyzbar 사용 가능")
except ImportError:
    PYZBAR_AVAILABLE = False
    print("pyzbar 사용 불가능 - OpenCV로 대체")

# 페이지 설정
st.set_page_config(
    page_title="바코드 스캐너",
    page_icon="📱",
    layout="wide"
)

def decode_barcode(image):
    """이미지에서 바코드를 디코딩하는 함수"""
    # PIL Image를 OpenCV 형식으로 변환
    if isinstance(image, Image.Image):
        image = np.array(image)
    
    # BGR에서 RGB로 변환 (필요한 경우)
    if len(image.shape) == 3 and image.shape[2] == 3:
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
    
    results = []
    
    if PYZBAR_AVAILABLE:
        # pyzbar를 사용한 바코드 디코딩
        barcodes = pyzbar.decode(image)
        
        for barcode in barcodes:
            # 바코드 데이터 추출
            barcode_data = barcode.data.decode('utf-8')
            barcode_type = barcode.type
            
            # 바코드 위치 정보
            (x, y, w, h) = barcode.rect
            
            results.append({
                'data': barcode_data,
                'type': barcode_type,
                'rect': (x, y, w, h)
            })
    else:
        # OpenCV를 사용한 QR 코드 검출 (대안)
        try:
            data, bbox, _ = qr_detector.detectAndDecode(image)
            if data:
                results.append({
                    'data': data,
                    'type': 'QRCODE',
                    'rect': tuple(map(int, bbox[0][0])) if bbox is not None else (0, 0, 100, 100)
                })
        except:
            pass
        
        # 바코드 영역 검출 (데이터 추출은 불가능하지만 위치는 표시)
        barcode_regions = detect_barcode_opencv(image)
        for i, (x, y, w, h) in enumerate(barcode_regions):
            results.append({
                'data': f'바코드 검출됨 #{i+1} (데이터 추출 불가)',
                'type': 'BARCODE_DETECTED',
                'rect': (x, y, w, h)
            })
    
    return results, image

def get_product_info(barcode_data):
    """바코드 데이터로 제품 정보를 가져오는 함수 (선택사항)"""
    try:
        # Open Food Facts API 사용 예시
        url = f"https://world.openfoodfacts.org/api/v0/product/{barcode_data}.json"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 1:
                product = data.get('product', {})
                return {
                    'name': product.get('product_name', 'Unknown'),
                    'brand': product.get('brands', 'Unknown'),
                    'categories': product.get('categories', 'Unknown')
                }
    except:
        pass
    
    return None

def main():
    st.title("📱 바코드 스캐너")
    st.markdown("휴대폰 카메라로 바코드를 스캔하세요!")
    
    # pyzbar 상태 표시
    if not PYZBAR_AVAILABLE:
        st.warning("⚠️ pyzbar 라이브러리가 설치되지 않았습니다. QR코드만 인식 가능합니다.")
        st.info("완전한 바코드 지원을 위해 다음 명령어로 zbar을 설치하세요: `brew install zbar`")
    
    # 사이드바에서 옵션 설정
    st.sidebar.header("설정")
    scan_mode = st.sidebar.selectbox(
        "스캔 모드 선택",
        ["실시간 카메라", "이미지 업로드"]
    )
    
    show_product_info = st.sidebar.checkbox("제품 정보 표시", value=True)
    
    if scan_mode == "실시간 카메라":
        st.header("실시간 카메라 스캔")
        
        # 카메라 입력
        camera_input = st.camera_input("바코드를 카메라에 비춰주세요")
        
        if camera_input is not None:
            # 이미지 처리
            image = Image.open(camera_input)
            
            # 바코드 디코딩
            results, processed_image = decode_barcode(image)
            
            # 결과 표시
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("캡처된 이미지")
                st.image(image, use_column_width=True)
            
            with col2:
                st.subheader("스캔 결과")
                
                if results:
                    for i, result in enumerate(results):
                        st.success(f"바코드 #{i+1} 감지됨!")
                        st.write(f"**타입:** {result['type']}")
                        st.write(f"**데이터:** `{result['data']}`")
                        
                        # 제품 정보 표시
                        if show_product_info and result['type'] in ['EAN13', 'EAN8', 'UPCA', 'UPCE']:
                            with st.spinner("제품 정보 조회 중..."):
                                product_info = get_product_info(result['data'])
                                
                                if product_info:
                                    st.write("**제품 정보:**")
                                    st.write(f"- 제품명: {product_info['name']}")
                                    st.write(f"- 브랜드: {product_info['brand']}")
                                    st.write(f"- 카테고리: {product_info['categories']}")
                                else:
                                    st.info("제품 정보를 찾을 수 없습니다.")
                        
                        st.markdown("---")
                else:
                    st.warning("바코드를 찾을 수 없습니다. 다시 시도해주세요.")
    
    else:  # 이미지 업로드 모드
        st.header("이미지 업로드 스캔")
        
        uploaded_file = st.file_uploader(
            "바코드가 포함된 이미지를 업로드하세요",
            type=['png', 'jpg', 'jpeg']
        )
        
        if uploaded_file is not None:
            # 이미지 로드
            image = Image.open(uploaded_file)
            
            # 바코드 디코딩
            results, processed_image = decode_barcode(image)
            
            # 결과 표시
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("업로드된 이미지")
                st.image(image, use_column_width=True)
            
            with col2:
                st.subheader("스캔 결과")
                
                if results:
                    for i, result in enumerate(results):
                        st.success(f"바코드 #{i+1} 감지됨!")
                        st.write(f"**타입:** {result['type']}")
                        st.write(f"**데이터:** `{result['data']}`")
                        
                        # 바코드 데이터를 클립보드에 복사할 수 있는 버튼
                        if st.button(f"데이터 복사 #{i+1}", key=f"copy_{i}"):
                            st.write("📋 클립보드에 복사되었습니다!")
                        
                        # 제품 정보 표시
                        if show_product_info and result['type'] in ['EAN13', 'EAN8', 'UPCA', 'UPCE']:
                            with st.spinner("제품 정보 조회 중..."):
                                product_info = get_product_info(result['data'])
                                
                                if product_info:
                                    st.write("**제품 정보:**")
                                    st.write(f"- 제품명: {product_info['name']}")
                                    st.write(f"- 브랜드: {product_info['brand']}")
                                    st.write(f"- 카테고리: {product_info['categories']}")
                                else:
                                    st.info("제품 정보를 찾을 수 없습니다.")
                        
                        st.markdown("---")
                else:
                    st.warning("바코드를 찾을 수 없습니다. 다른 이미지를 시도해보세요.")
    
    # 사용법 안내
    with st.expander("사용법 및 팁"):
        st.markdown("""
        ### 사용법:
        1. **실시간 카메라**: 'Take Photo' 버튼을 눌러 바코드 사진을 찍으세요
        2. **이미지 업로드**: 바코드가 포함된 이미지 파일을 업로드하세요
        
        ### 팁:
        - 바코드가 선명하고 완전히 보이도록 촬영하세요
        - 충분한 조명을 확보하세요
        - 바코드가 기울어지지 않도록 주의하세요
        - 여러 바코드가 있는 경우 모두 인식됩니다
        
        ### 지원하는 바코드 형식:
        - **pyzbar 설치시**: EAN-13, EAN-8, UPC-A, UPC-E, Code-128, Code-39, QR Code, Data Matrix
        - **pyzbar 미설치시**: QR Code만 지원 (바코드 영역 검출은 가능)
        
        ### zbar 라이브러리 설치 방법 (macOS):
        ```bash
        brew install zbar
        ```
        """)

if __name__ == "__main__":
    main()
