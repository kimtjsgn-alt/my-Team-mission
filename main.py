import re
from datetime import datetime
import pytz
import requests
import streamlit as st

# 페이지 기본 설정
st.set_page_config(
    page_title="학교 급식 찾아보기", page_icon="🍱", layout="centered"
)

st.title("🍱 학교 급식 찾아보기")


# 1. 줄임말 보정 함수
def normalize_school_name(name: str) -> list[str]:
    """입력된 학교 이름과 줄임말 보정 후 이름을 순서대로 반환합니다."""
    candidates = [name]

    replacements = [
        ("여고", "여자고등학교"),
        ("남고", "남자고등학교"),
        ("여중", "여자중학교"),
        ("남중", "남자중학교"),
        ("여초", "여자초등학교"),
        ("고", "고등학교"),
        ("중", "중학교"),
        ("초", "초등학교"),
    ]

    converted = name
    for short, full in replacements:
        if short in converted:
            converted = converted.replace(short, full)
            break

    if converted != name:
        candidates.append(converted)

    return candidates


# 2. 학교 정보 검색 함수
def search_school(school_name: str):
    """나이스 API를 통해 학교 정보를 검색합니다."""
    url = "https://open.neis.go.kr/hub/schoolInfo"
    search_names = normalize_school_name(school_name)

    for search_term in search_names:
        params = {"Type": "json", "SCHUL_NM": search_term}
        try:
            response = requests.get(url, params=params, timeout=5)
            data = response.json()

            if "schoolInfo" in data:
                rows = data["schoolInfo"][1]["row"]
                return rows, search_term
        except Exception:
            continue

    return [], None


# 3. 급식 정보 검색 함수
def get_meal_info(office_code: str, school_code: str, date_str: str):
    """나이스 API를 통해 특정 날짜의 중식 정보를 가져옵니다."""
    url = "https://open.neis.go.kr/hub/mealServiceDietInfo"
    params = {
        "Type": "json",
        "ATPT_OFCDC_SC_CODE": office_code,
        "SD_SCHUL_CODE": school_code,
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


# --- UI 구성 ---

# 검색어 입력
input_name = st.text_input("학교 이름을 입력하세요", placeholder="예: 수도여고, 서울고")

if input_name:
    schools, used_term = search_school(input_name.strip())

    if not schools:
        st.warning(
            f"'{input_name}'에 해당하는 학교를 찾을 수 없습니다. 정확한 이름을 입력해 주세요."
        )
    else:
        # 줄임말 보정 안내 문구
        if used_term != input_name.strip():
            st.info(
                f"💡 '{input_name}' 검색 결과가 없어 '{used_term}'(으)로 검색한 결과입니다."
            )

        # 학교 선택 셀렉트박스 옵션 생성
        school_options = {
            f"{s['SCHUL_NM']} ({s.get('LCTN_SC_NM', '지역정보 없음')})": s
            for s in schools
        }

        selected_label = st.selectbox(
            "학교를 선택하세요", options=list(school_options.keys())
        )

        selected_school = school_options[selected_label]

        # 한국 시간(KST) 기준 오늘 날짜 구하기
        kst = pytz.timezone("Asia/Seoul")
        today_kst = datetime.now(kst).date()

        # 날짜 선택기 (기본값: 한국 시간 오늘)
        selected_date = st.date_input("조회할 날짜를 선택하세요", value=today_kst)

        if selected_date:
            date_str = selected_date.strftime("%Y%m%d")

            # 급식 정보 조회
            meal = get_meal_info(
                selected_school["ATPT_OFCDC_SC_CODE"],
                selected_school["SD_SCHUL_CODE"],
                date_str,
            )

            st.markdown("---")
            st.subheader(
                f"📅 {selected_date.strftime('%Y년 %m월 %d일')} 중식 메뉴"
            )

            if meal:
                # <br/> 태그 전처리 및 알레르기 번호 정리
                raw_menu = meal.get("DDISH_NM", "")
                clean_menu_items = raw_menu.split("<br/>")

                # 메뉴 표시
                st.write("**[메뉴 및 알레르기 정보]**")
                for item in clean_menu_items:
                    st.text(f"• {item.strip()}")

                # 칼로리 정보 표시
                calorie = meal.get("CAL_INFO", "정보 없음")
                st.success(f"🔥 **열량:** {calorie}")
            else:
                st.info("해당 날짜에는 등록된 중식 급식 정보가 없습니다.")
