import uuid
import streamlit as st
import httpx

# ──────────────────────────────────────────
# 설정
# ──────────────────────────────────────────
API_URL = "http://localhost:8000"

st.set_page_config(page_title="StyleShop 챗봇", page_icon="🛍️")
st.title("🛍️ StyleShop 상담 챗봇")
st.caption("상품 검색 · 주문 조회 · 장바구니 · FAQ · 할인 안내")

# ──────────────────────────────────────────
# 세션 초기화
# ──────────────────────────────────────────
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []
if "cart" not in st.session_state:
    st.session_state.cart = {}

# ──────────────────────────────────────────
# 사이드바: 장바구니 + 새 대화
# ──────────────────────────────────────────
with st.sidebar:
    st.header("장바구니")
    if st.session_state.cart:
        for product_id, qty in st.session_state.cart.items():
            st.write(f"• {product_id}: {qty}개")
    else:
        st.write("비어 있습니다")

    st.divider()

    if st.button("새 대화 시작"):
        try:
            httpx.post(f"{API_URL}/reset", params={"session_id": st.session_state.session_id})
        except httpx.ConnectError:
            pass
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.session_state.cart = {}
        st.rerun()

# ──────────────────────────────────────────
# 대화 기록 표시
# ──────────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ──────────────────────────────────────────
# 사용자 입력 처리
# ──────────────────────────────────────────
user_input = st.chat_input("무엇을 도와드릴까요?")

if user_input:
    # 사용자 메시지 표시
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # FastAPI 호출
    with st.chat_message("assistant"):
        with st.spinner("답변 생성 중..."):
            try:
                response = httpx.post(
                    f"{API_URL}/chat",
                    json={
                        "session_id": st.session_state.session_id,
                        "message": user_input,
                    },
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()

                reply = data["reply"]
                st.session_state.cart = data["cart"]

            except httpx.ConnectError:
                reply = "⚠️ 서버에 연결할 수 없습니다. FastAPI 서버가 실행 중인지 확인해주세요."
            except httpx.HTTPStatusError as e:
                reply = f"⚠️ 서버 오류: {e.response.text}"
            except Exception as e:
                reply = f"⚠️ 오류 발생: {str(e)}"

        st.markdown(reply)

    st.session_state.messages.append({"role": "assistant", "content": reply})
