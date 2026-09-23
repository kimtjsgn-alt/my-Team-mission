import streamlit as st
import requests
import re
import pandas as pd

# Page Configuration
st.set_page_config(page_title="고단백 급식 메뉴 탐색기", layout="wide")

st.title("🍗 학교별 고단백 메인 요리 탐색기")
st.caption("나이스 공공 급식 API 데이터를 활용하여 고단백 급식 식단을 분석합니다.")

# 1. 고단백 식재료 키워드 정의
PROTEIN_KEYWORDS = [
    "닭", "치킨", "돈까스", "돼지", "돈육", "제육", "불고기", "삼겹", "보쌈", 
    "소고기", "우육", "갈비", "함박", "계란", "달걀", "메추리알", 
    "두부", "콩", "오리", "생선", "고등어", "삼치", "연어", "오징어", "새우", "장어"
]

# 2. 헬퍼 함수: 메뉴명 정제 및 고단백 메인 요리 추론
def parse_and_find_main_dish(ddish_nm):
    if not ddish_nm:
        return "정보 없음", []
    
    # <br/> 태그 분할 및 알레르기 번호(괄호 안 숫자 및 특수문자) 제거
    raw_dishes = ddish_nm.split("<br/>")
    cleaned_dishes = []
    protein_dishes = []
    
    for dish in raw_dishes:
        # 정규식으로 괄호와 괄호 안의 알레르기 숫자 제거
        clean_name = re.sub(r'\([^)]*\)', '', dish).strip()
        if clean_name:
            cleaned_dishes.append(clean_name)
            # 고단백 키워드 포함 여부 확인
            if any(keyword in clean_name for keyword in PROTEIN_KEYWORDS):
                protein_dishes.append(clean_name)
                
    return cleaned_dishes, protein_dishes

# 3. 사용자 입력 화면
col1, col2 = st.columns([3, 2])
with col1:
    school_name = st.text_input("학교 이름을 입력하세요 (예: 서울고등학교, 한빛중)", "")
with col2:
    search_button = st.button("검색 및 분석 실행", type="primary")

if search_button and school_name:
    # --- Step 1: 학교 기본 정보 조회 ---
    school_api_url = "https://open.neis.go.kr/hub/schoolInfo"
    school_params = {
        "Type": "json",
        "SCHUL_NM": school_name
    }
    
    try:
        res_school = requests.get(school_api_url, params=school_params).json()
        
        # 예외 처리: 데이터 없음 (INFO-200)
        if "RESULT" in res_school and res_school["RESULT"]["CODE"] == "INFO-200":
            st.error(f"'{school_name}'에 대한 검색 결과가 없습니다. 학교명을 정확히 입력해 주세요.")
        elif "schoolInfo" in res_school:
            school_row = res_school["schoolInfo"][1]["row"][0]
            atpt_code = school_row["ATPT_OFCDC_SC_CODE"]
            sd_code = school_row["SD_SCHUL_CODE"]
            full_school_name = school_row["SCHUL_NM"]
            location = school_row["LCTN_SC_NM"]
            
            st.success(f"🏫 **{full_school_name}** ({location}) 정보를 불러왔습니다.")
            
            # --- Step 2: 급식 식단 정보 조회 ---
            meal_api_url = "https://open.neis.go.kr/hub/mealServiceDietInfo"
            meal_params = {
                "Type": "json",
                "ATPT_OFCDC_SC_CODE": atpt_code,
                "SD_SCHUL_CODE": sd_code,
                "MMEAL_SC_CODE": "2"  # 중식
            }
            
            res_meal = requests.get(meal_api_url, params=meal_params).json()
            
            if "RESULT" in res_meal and res_meal["RESULT"]["CODE"] == "INFO-200":
                st.warning("해당 학교의 등록된 급식 데이터가 없습니다.")
            elif "mealServiceDietInfo" in res_meal:
                meal_rows = res_meal["mealServiceDietInfo"][1]["row"]
                
                st.info("ℹ️ 인증키가 없는 요청 특성상 최근 5건의 급식 데이터를 기반으로 분석합니다.")
                
                parsed_data = []
                for row in meal_rows:
                    date = row.get("MLSV_YMD", "")
                    raw_menu = row.get("DDISH_NM", "")
                    calorie = row.get("CAL_INFO", "정보 없음")
                    
                    cleaned_menu, protein_main = parse_and_find_main_dish(raw_menu)
                    
                    parsed_data.append({
                        "급식일자": f"{date[:4]}-{date[4:6]}-{date[6:]}" if len(date) == 8 else date,
                        "추론된 고단백 메인 요리": ", ".join(protein_main) if protein_main else "특이사항 없음 (채식/일반 식단)",
                        "전체 식단": ", ".join(cleaned_menu),
                        "칼로리": calorie
                    })
                
                df = pd.DataFrame(parsed_data)
                
                # 결과 출력
                st.subheader("📊 고단백 메인 요리 분석 결과")
                st.dataframe(df, use_container_width=True)
                
                # 요약 카드 출력
                st.subheader("💡 고단백 식단 요약")
                for item in parsed_data:
                    with st.expander(f"📅 {item['급식일자']} - 메인 요리: {item['추론된 고단백 메인 요리']}"):
                        st.write(f"**전체 메뉴:** {item['전체 식단']}")
                        st.write(f"**칼로리 정보:** {item['칼로리']}")
            else:
                st.error("급식 정보를 가져오는 중 오류가 발생했습니다.")
        else:
            st.error("학교 정보를 불러올 수 없습니다.")
            
    except Exception as e:
        st.error(f"API 요청 중 에러가 발생했습니다: {e}")
