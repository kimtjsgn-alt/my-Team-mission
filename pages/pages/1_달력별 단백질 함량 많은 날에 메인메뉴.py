import re
from datetime import datetime
import pytz
import requests
import streamlit as st

# 페이지 기본 설정
st.set_page_config(
    page_title="우리 학교 달력별 급식", page_icon="📅", layout="wide"
)

st.title("📅 우리 학교 달력별 급식")
st.caption("송탄고등학교 중식 메뉴 및 영양 정보 조회")

# 송탄고등학교 고정 정보
OFFICE_CODE = "J10"  # 경기도교육청
SCHOOL_CODE = "7530480"  # 송탄고등학교


# 급식 정보 조회 함수
def get_songtan_meal(date_str: str):
    """나이스 API를 통해 송탄고등학교의 특정 날짜 중식 정보를 가져옵니다."""
    url = "https://open.neis.go.kr/hub/mealServiceDietInfo"
    params = {
        "Type": "json",
        "ATPT_OFCDC_SC_CODE": OFFICE_CODE,
        "SD_SCHUL_CODE": SCHOOL_CODE,
        "MMEAL_SC_CODE": "2",  # 중식
        "MLSV_FROM_YMD": date_str,
        "MLSV_TO_YMD": date_str,
        "pIndex": 1,
        "pSize": 100,
    }

    try:
        response = requests.get(url, params=params, timeout=5)
        data = response.json()

        if "mealServiceDietInfo" in data:
            rows = data["mealServiceDietInfo"][1]["row"]
            return rows[0] if rows else None
    except Exception:
        return None

    return None


# 알레르기 번호 제거 함수
def remove_allergy_info(menu_item: str) -> str:
    """괄호 안의 알레르기 번호를 제거합니다. 예: '쌀밥 (1.2.3)' -> '쌀밥'"""
    return re.sub(r"\s*\([\d\.\s]+\)", "", menu_item).strip()


# 한국 시간(KST) 기준 오늘 날짜 구하기
kst = pytz.timezone("Asia/Seoul")
today_kst = datetime.now(kst).date()

# 컨트롤 영역 (날짜 선택 및 알레르기 스위치 나란히 배치)
col_control1, col_control2 = st.columns([2, 1])

with col_control1:
    selected_date = st.date_input("조회할 날짜를 선택하세요", value=today_kst)

with col_control2:
    st.write(" ")  # 레이아웃 높이 맞춤용 여백
    st.write(" ")
    show_allergy = st.toggle("알레르기 정보 보기", value=True)

st.markdown("---")

if selected_date:
    date_str = selected_date.strftime("%Y%m%d")
    meal_data = get_songtan_meal(date_str)

    if meal_data:
        # 1. 메뉴 데이터 전처리
        raw_menu = meal_data.get("DDISH_NM", "")
        # <br/> 태그 분할
        items = [
            item.strip() for item in raw_menu.split("<br/>") if item.strip()
        ]

        # 스위치 여부에 따라 메뉴 문자열 구성
        processed_items = [
            item if show_allergy else remove_allergy_info(item)
            for item in items
        ]

        calorie_info = meal_data.get("CAL_INFO", "정보 없음")

        # 2. 요약 정보 카드 (큰 숫자 카드로 표시)
        m_col1, m_col2 = st.columns(2)

        with m_col1:
            st.metric(label="🍱 메뉴 가짓수", value=f"{len(items)}개")

        with m_col2:
            st.metric(label="🔥 총 열량", value=calorie_info)

        st.markdown("### 🍽️ 오늘의 식단 메뉴")

        # 3. 메뉴를 카드(Container/Column) 여러 개로 나란히 배치
        num_items = len(processed_items)
        cols_per_row = 4

        for i in range(0, num_items, cols_per_row):
            row_items = processed_items[i : i + cols_per_row]
            grid_cols = st.columns(cols_per_row)

            for idx, menu_text in enumerate(row_items):
                with grid_cols[idx]:
                    with st.container(border=True):
                        st.markdown(f"**{menu_text}**")

    else:
        st.info("급식이 없는 날입니다.")
