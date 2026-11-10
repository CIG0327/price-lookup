import os
import sqlite3
import pandas as pd
import streamlit as st

# 페이지 설정 (반응형, 모바일 최적화)
st.set_page_config(
    page_title="판가 검색 시스템",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 커스텀 CSS (모던 & 모바일 친화적 카드 스타일)
st.markdown("""
<style>
    .main-title {
        font-size: 1.8rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 0.95rem;
        color: #6B7280;
        margin-bottom: 1.5rem;
    }
    .price-card-partner {
        background: linear-gradient(135deg, #1E40AF 0%, #3B82F6 100%);
        color: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        text-align: center;
        margin-bottom: 12px;
    }
    .price-card-consumer {
        background: linear-gradient(135deg, #4338CA 0%, #6366F1 100%);
        color: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        text-align: center;
        margin-bottom: 12px;
    }
    .card-label {
        font-size: 0.95rem;
        font-weight: 600;
        opacity: 0.9;
        margin-bottom: 4px;
    }
    .card-value {
        font-size: 1.85rem;
        font-weight: 800;
        letter-spacing: -0.5px;
    }
    .info-badge {
        display: inline-block;
        background-color: #E0E7FF;
        color: #3730A3;
        font-size: 0.85rem;
        font-weight: 600;
        padding: 4px 10px;
        border-radius: 6px;
        margin-right: 6px;
    }
</style>
""", unsafe_allow_html=True)

DB_PATH = os.path.join(os.path.dirname(__file__), "agent_price.db")

# 접속 인증 비밀번호 (필요시 수정 가능)
ACCESS_PIN = os.environ.get("AGENT_ACCESS_PIN", "1234")

# 세션 상태 초기화
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

def check_pin():
    if st.session_state.pin_input == ACCESS_PIN:
        st.session_state.authenticated = True
        st.session_state.pin_error = False
    else:
        st.session_state.pin_error = True

# 로그인/인증 화면
if not st.session_state.authenticated:
    st.markdown("<div class='main-title'>🔒 판가 검색 시스템</div>", unsafe_allow_html=True)
    st.markdown("<div class='sub-title'>인가된 에이전트(지정점/대리점) 전용 시스템입니다. 접속 PIN 번호를 입력해주세요.</div>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.text_input("접속 PIN 번호", type="password", key="pin_input", on_change=check_pin, placeholder="PIN 4자리 입력")
        st.button("접속하기", on_click=check_pin, type="primary", use_container_width=True)
        if st.session_state.get("pin_error"):
            st.error("PIN 번호가 일치하지 않습니다. 다시 확인해주세요.")
    st.stop()

# --- 메인 검색 화면 ---
col_head, col_logout = st.columns([5, 1])
with col_head:
    st.markdown("<div class='main-title'>🔍 부품 판가 실시간 검색</div>", unsafe_allow_html=True)
    st.markdown("<div class='sub-title'>자재번호 또는 품명을 입력하여 우수지정점 판가 및 소비자가를 확인하세요.</div>", unsafe_allow_html=True)
with col_logout:
    if st.button("로그아웃", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

# DB 연결 함수 (캐싱)
@st.cache_resource
def get_db_connection():
    if not os.path.exists(DB_PATH):
        return None
    return sqlite3.connect(DB_PATH, check_same_thread=False)

conn = get_db_connection()
if conn is None:
    st.error(f"데이터베이스 파일(`agent_price.db`)을 찾을 수 없습니다. 관리자에게 문의하세요.")
    st.stop()

# 검색창
search_query = st.text_input(
    "자재번호(숫자) 또는 품명(영문/한글) 검색",
    placeholder="예: 20020558 또는 FIXING DIE (공백으로 다중 검색 가능)",
    help="자재번호를 정확히 입력하거나, 품명의 일부 단어들을 띄어쓰기로 입력하세요."
).strip()

def search_price(query, limit=50):
    if not query:
        return []
    
    cursor = conn.cursor()
    # 1. 숫자만 있는 경우: 자재번호 검색
    if query.isdigit():
        # 완전 일치 우선
        cursor.execute("""
            SELECT material_code, material_name, price_partner, price_consumer
            FROM price_master
            WHERE material_code = ?
        """, (query,))
        exact_match = cursor.fetchall()
        if exact_match:
            return exact_match
        
        # 앞자리 또는 부분 일치
        cursor.execute("""
            SELECT material_code, material_name, price_partner, price_consumer
            FROM price_master
            WHERE material_code LIKE ?
            LIMIT ?
        """, (f"{query}%", limit))
        return cursor.fetchall()

    # 2. 문자열 검색: 품명 다중 키워드 AND 검색
    keywords = query.split()
    conditions = []
    params = []
    for kw in keywords:
        conditions.append("material_name LIKE ?")
        params.append(f"%{kw}%")
    
    sql = f"""
        SELECT material_code, material_name, price_partner, price_consumer
        FROM price_master
        WHERE {' AND '.join(conditions)}
        LIMIT ?
    """
    params.append(limit)
    cursor.execute(sql, params)
    return cursor.fetchall()

if search_query:
    results = search_price(search_query)

    if not results:
        st.warning(f"'{search_query}'에 대한 검색 결과가 없습니다. 자재번호 또는 품명 철자를 확인해주세요.")
    elif len(results) == 1:
        # 단일 품목 조회 시: 대형 카드 뷰
        item = results[0]
        code, name, partner_price, consumer_price = item
        
        partner_str = f"{partner_price:,.0f}원" if partner_price is not None else "판가 미등록"
        consumer_str = f"{consumer_price:,.0f}원" if consumer_price is not None else "판가 미등록"

        st.success(f"검색 성공: 자재번호 [{code}]")
        st.markdown(f"**품명(규격):** {name}")

        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"""
            <div class="price-card-partner">
                <div class="card-label">우수지정점 판가</div>
                <div class="card-value">{partner_str}</div>
            </div>
            """, unsafe_allow_html=True)
        with c2:
            st.markdown(f"""
            <div class="price-card-consumer">
                <div class="card-label">소비자가 (국내)</div>
                <div class="card-value">{consumer_str}</div>
            </div>
            """, unsafe_allow_html=True)

        # 복사 편의 텍스트 영역
        copy_text = f"자재번호: {code} | 품명: {name} | 우수지정점가: {partner_str} | 소비자가: {consumer_str}"
        st.text_input("복사용 텍스트 (클릭 후 Ctrl+C)", value=copy_text, label_visibility="collapsed")

    else:
        # 여러 건 조회 시: 상단 요약 + 목록 테이블
        st.info(f"총 **{len(results)}건**의 부품이 검색되었습니다. (최대 50건 표시)")

        # DataFrame 변환
        df = pd.DataFrame(results, columns=["자재번호", "품명(규격)", "우수지정점 판가", "소비자가(국내)"])
        
        # 포맷팅
        df["우수지정점 판가"] = df["우수지정점 판가"].apply(lambda x: f"{x:,.0f}원" if pd.notnull(x) else "-")
        df["소비자가(국내)"] = df["소비자가(국내)"].apply(lambda x: f"{x:,.0f}원" if pd.notnull(x) else "-")

        # 테이블 표시
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "자재번호": st.column_config.TextColumn("자재번호", width="medium"),
                "품명(규격)": st.column_config.TextColumn("품명(규격)", width="large"),
                "우수지정점 판가": st.column_config.TextColumn("우수지정점 판가", width="medium"),
                "소비자가(국내)": st.column_config.TextColumn("소비자가(국내)", width="medium"),
            }
        )

        # 선택하여 상세 보기
        st.markdown("---")
        selected_code = st.selectbox("상세 판가를 확인할 자재를 선택하세요:", df["자재번호"] + " - " + df["품명(규격)"])
        if selected_code:
            code_only = selected_code.split(" - ")[0]
            matched = df[df["자재번호"] == code_only].iloc[0]
            
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"""
                <div class="price-card-partner">
                    <div class="card-label">우수지정점 판가 ({matched['자재번호']})</div>
                    <div class="card-value">{matched['우수지정점 판가']}</div>
                </div>
                """, unsafe_allow_html=True)
            with c2:
                st.markdown(f"""
                <div class="price-card-consumer">
                    <div class="card-label">소비자가 (국내)</div>
                    <div class="card-value">{matched['소비자가(국내)']}</div>
                </div>
                """, unsafe_allow_html=True)
else:
    # 검색 전 기본 안내
    st.markdown("""
    ---
    ### 💡 검색 도움말
    - **자재번호 검색**: `20020558`과 같이 자재번호 숫자만 입력하시면 바로 조회됩니다.
    - **품명 검색**: `CP FIXING`, `DIE 250E` 등 부품명에 포함된 단어를 띄어쓰기로 입력하시면 해당 단어가 모두 포함된 부품을 찾아줍니다.
    - **보안 안내**: 본 시스템은 지정점/에이전트 권한에 맞추어 **우수지정점 판가** 및 **소비자가(국내)**만 제공합니다.
    """)

