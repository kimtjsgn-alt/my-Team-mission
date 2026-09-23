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
    """괄호 안의 알레르기 번호를 제거합니다. 예: '치킨마요덮밥 (1.5.6)' -> '치킨마요덮밥'"""
    return re.sub(r"\s*\([\d\.\s]+\)", "", menu_item).strip()


# 대표 단백질 메인 메뉴 추정 함수
def find_protein_main_menu(items: list[str]) -> str:
    """메뉴 목록 중 고기, 생선, 닭, 계란, 두부 등의 키워드나 알레르기 번호(닭고기, 돼지고기, 쇠고기, 오징어 등)를 기반으로 메인 메뉴를 찾습니다."""
    protein_keywords = [
        "치킨",
        "고기",
        "불고기",
        "갈비",
        "돈까스",
        "까스",
        "스테이크",
        "탕수육",
        "닭",
        "찜닭",
        "오리",
        "삼겹",
        "제육",
        "장조림",
        "함박",
        "너겟",
        "훈제",
        "장어",
        "새우",
        "오징어",
        "문어",
        "두부",
        "계란",
        "달걀",
    ]

    for item in items:
        clean_item = remove_allergy_info(item)
        for kw in protein_keywords:
            if kw in clean_item:
                return item

    # 키워드 매칭이 없을 경우 첫 번째 메뉴(주식/메인) 반환
    return items[0] if items else "정보 없음"


# 한국 시간(KST) 기준 오늘 날짜 구하기
kst = pytz.timezone("Asia/Seoul")
today_kst = datetime.now(kst).date()

# 컨트롤 영역 (날짜 선택 및 알레르기 스위치 나란히 배치)
col_control1, col_control2 = st.columns([2, 1])

with col_control1:
    selected_date = st.date_input("조회할 날짜를 선택하세요", value=today_kst)

with col_control2:
    st.write(" ")  # 높이 맞춤용 여백
    st.write(" ")
    show_allergy = st.toggle("알레르기 정보 보기", value=True)

st.markdown("---")

if selected_date:
    date_str = selected_date.strftime("%Y%m%d")
    meal_data = get_songtan_meal(date_str)

    if meal_data:
        # 1. 메뉴 데이터 전처리
        raw_menu = meal_data.get("DDISH_NM", "")
        raw_items = [
            item.strip() for item in raw_menu.split("<br/>") if item.strip()
        ]

        # 단백질 대표 메인 메뉴 선정
        main_protein_item = find_protein_main_menu(raw_items)
        display_main_protein = (
            main_protein_item
            if show_allergy
            else remove_allergy_info(main_protein_item)
        )

        # 표시용 메뉴 리스트 구성 (스위치 여부 적용)
        processed_items = [
            item if show_allergy else remove_allergy_info(item)
            for item in raw_items
        ]

        calorie_info = meal_data.get("CAL_INFO", "정보 없음")

        # 2. 메인 단백질 메뉴 카드로 강조 표시
        st.info(f"🍖 **오늘 단백질 함량이 가장 높은 메인 메뉴:** {display_main_protein}")

        # 3. 요약 정보 카드 (큰 숫자 카드로 표시)
        m_col1, m_col2 = st.columns(2)

        with m_col1:
            st.metric(label="🍱 메뉴 가짓수", value=f"{len(raw_items)}개")

        with m_col2:
            st.metric(label="🔥 총 열량", value=calorie_info)

        st.markdown("### 🍽️ 전체 식단 메뉴")

        # 4. 전체 메뉴를 카드 여러 개로 나란히 배치
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
