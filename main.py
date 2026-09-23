import streamlit as st
import requests
import re
import pandas as pd
from datetime import datetime, timedelta

# Page Configuration
st.set_page_config(page_title="고단백 급식 메뉴 탐색기", layout="wide")

# NEIS API KEY 설정
NEIS_API_KEY = "6b62a20c6ac34b50b5e112d8e0b0e8e9"

st.title("🍗 학교별 고단백 메인 요리 & 추정 단백질 함량 탐색기")
st.caption("나이스 공공 급식 API 데이터를 활용하여 메인 요리를 감지하고 추정 단백질 함량을 계산합니다.")

# 1. 고단백 식재료 키워드 및 100g 당 평균 단백질 함량(g) 데이터베이스
PROTEIN_DATABASE = {
    "닭": ("닭고기류", 23.0),
    "치킨": ("치킨/닭튀김", 20.0),
    "돈까스": ("돈가스", 15.0),
    "돼지": ("돼지고기류", 18.0),
    "돈육": ("돼지고기류", 18.0),
    "제육": ("제육볶음", 16.0),
    "불고기": ("불고기류", 17.0),
    "삼겹": ("삼겹살", 14.0),
    "보쌈": ("수육/보쌈", 19.0),
    "소고기": ("소고기류", 22.0),
    "우육": ("소고기류", 22.0),
    "갈비": ("갈비구이/찜", 17.0),
    "함박": ("함박스테이크", 14.0),
    "계란": ("계란 요리", 12.0),
    "달걀": ("계란 요리", 12.0),
    "메추리알": ("메추리알 조림", 11.0),
    "두부": ("두부 요리", 8.0),
    "콩": ("콩 요리", 13.0),
    "오리": ("오리고기", 18.0),
    "생선": ("생선구이/조림", 20.0),
    "고등어": ("고등어 요리", 20.0),
    "삼치": ("삼치 요리", 19.0),
    "연어": ("연어 요리", 20.0),
    "오징어": ("오징어 요리", 18.0),
    "새우": ("새우 요리", 16.0),
    "장어": ("장어 구이", 21.0)
}

# 2. 헬퍼 함수: 메뉴명 정제 및 단백질 함량 추정
def parse_and_find_main_dish(ddish_nm):
    if not ddish_nm:
        return [], [], 0.0
    
    # <br/> 태그 분할 및 알레르기 번호 제거
    raw_dishes = ddish_nm.split("<br/>")
    cleaned_dishes = []
    protein_details = []
    total_est_protein = 0.0
    
    for dish in raw_dishes:
        clean_name = re.sub(r'\([^)]*\)', '', dish).strip()
        if clean_name:
            cleaned_dishes.append(clean_name)
            
            # 고단백 키워드 검사
            for keyword, (category, protein_per_100g) in PROTEIN_DATABASE.items():
                if keyword in clean_name:
                    protein_details.append(f"{clean_name} (약 {protein_per_100g}g/100g 기준)")
                    total_est_protein += protein_per_100g
                    break # 한 메뉴당 대표 키워드 하나만 적용
                
    return cleaned_dishes, protein_details, round(total_est_protein, 1)

# 3. 사용자 입력 화면
col1, col2, col3 = st.columns([3, 2, 2])
with col1:
    school_name = st.text_input("학교 이름", "서울고등학교")
with col2:
    start_date = st.date_input("조회 시작일", datetime.now() - timedelta(days=30))
with col3:
    end_date = st.date_input("조회 종료일", datetime.now())

search_button = st.button("검색 및 분석 실행", type="primary")

if search_button and school_name:
    from_ymd = start_date.strftime("%Y%m%d")
    to_ymd = end_date.strftime("%Y%m%d")

    # Step 1: 학교 기본 정보 조회
    school_api_url = "https://open.neis.go.kr/hub/schoolInfo"
    school_params = {
        "KEY": NEIS_API_KEY,
        "Type": "json",
        "SCHUL_NM": school_name
    }
    
    try:
        res_school = requests.get(school_api_url, params=school_params).json()
        
        if "RESULT" in res_school and res_school["RESULT"]["CODE"] == "INFO-200":
            st.error(f"'{school_name}'에 대한 검색 결과가 없습니다.")
        elif "schoolInfo" in res_school:
            school_row = res_school["schoolInfo"][1]["row"][0]
            atpt_code = school_row["ATPT_OFCDC_SC_CODE"]
            sd_code = school_row["SD_SCHUL_CODE"]
            full_school_name = school_row["SCHUL_NM"]
            location = school_row["LCTN_SC_NM"]
            
            st.success(f"🏫 **{full_school_name}** ({location}) 정보를 불러왔습니다.")
            
            # Step 2: 급식 식단 정보 조회
            meal_api_url = "https://open.neis.go.kr/hub/mealServiceDietInfo"
            meal_params = {
                "KEY": NEIS_API_KEY,
                "Type": "json",
                "ATPT_OFCDC_SC_CODE": atpt_code,
                "SD_SCHUL_CODE": sd_code,
                "MMEAL_SC_CODE": "2",  # 중식
                "MLSV_FROM_YMD": from_ymd,
                "MLSV_TO_YMD": to_ymd,
                "pSize": 1000
            }
            
            res_meal = requests.get(meal_api_url, params=meal_params).json()
            
            if "RESULT" in res_meal and res_meal["RESULT"]["CODE"] == "INFO-200":
                st.warning("선택하신 기간 동안의 급식 데이터가 없습니다.")
            elif "mealServiceDietInfo" in res_meal:
                meal_rows = res_meal["mealServiceDietInfo"][1]["row"]
                total_count = res_meal["mealServiceDietInfo"][0]["head"][0]["list_total_count"]
                
                st.info(f"총 {total_count}건의 급식 데이터를 조회했습니다.")
                
                parsed_data = []
                for row in meal_rows:
                    date = row.get("MLSV_YMD", "")
                    raw_menu = row.get("DDISH_NM", "")
                    calorie = row.get("CAL_INFO", "정보 없음")
                    
                    cleaned_menu, protein_main, est_protein = parse_and_find_main_dish(raw_menu)
                    
                    parsed_data.append({
                        "급식일자": f"{date[:4]}-{date[4:6]}-{date[6:]}" if len(date) == 8 else date,
                        "추단백질 함량(합계)": f"약 {est_protein}g",
                        "고단백 메인 요리 (추정 함량)": ", ".join(protein_main) if protein_main else "특이사항 없음",
                        "전체 식단": ", ".join(cleaned_menu),
                        "칼로리": calorie,
                        "_protein_val": est_protein
                    })
                
                # 단백질 추정 함량이 높은 순서대로 정렬 가능
                df = pd.DataFrame(parsed_data)
                df_display = df.drop(columns=["_protein_val"])
                
                st.subheader("📊 고단백 메인 요리 및 단백질 함량 분석 결과")
                st.dataframe(df_display, use_container_width=True)
                
                # TOP 3 단백질 식단 하이라이트
                top3 = sorted(parsed_data, key=lambda x: x["_protein_val"], reverse=True)[:3]
                st.subheader("🏆 해당 기간 단백질 추정 함량 TOP 3 날짜")
                
                top_cols = st.columns(3)
                for idx, item in enumerate(top3):
                    if item['_protein_val'] > 0:
                        with top_cols[idx]:
                            st.metric(
                                label=f"TOP {idx+1} ({item['급식일자']})", 
                                value=f"{item['추단백질 함량(합계)']}",
                                delta=item['칼로리']
                            )
                            st.write(f"**메인:** {item['고단백 메인 요리 (추정 함량)']}")
                            st.caption(f"전체 메뉴: {item['전체 식단']}")
            else:
                st.error("급식 정보를 가져오는 중 오류가 발생했습니다.")
        else:
            st.error("학교 정보를 불러올 수 없습니다.")
            
    except Exception as e:
        st.error(f"API 요청 중 에러가 발생했습니다: {e}")
