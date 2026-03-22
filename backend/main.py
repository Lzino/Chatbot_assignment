import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from backend.agent import chat

load_dotenv()

app = FastAPI(title="StyleShop Chatbot API")

API_KEY = os.getenv("OPENAI_API_KEY", "")

# 세션별 상태 저장 (메모리 기반)
sessions: dict[str, dict] = {}


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ChatResponse(BaseModel):
    reply: str
    cart: dict


@app.post("/chat", response_model=ChatResponse)
def handle_chat(request: ChatRequest):
    if not API_KEY:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY가 설정되지 않았습니다.")

    # 세션 초기화 또는 불러오기
    if request.session_id not in sessions:
        sessions[request.session_id] = {
            "history": [],
            "cart": {},
        }

    session = sessions[request.session_id]

    reply, updated_history, updated_cart = chat(
        user_message=request.message,
        conversation_history=session["history"],
        cart=session["cart"],
        api_key=API_KEY,
    )

    # 세션 상태 갱신
    session["history"] = updated_history
    session["cart"] = updated_cart

    return ChatResponse(reply=reply, cart=updated_cart)


@app.post("/reset")
def reset_session(session_id: str):
    """세션 초기화 (대화 기록 + 장바구니 삭제)"""
    sessions.pop(session_id, None)
    return {"message": "세션이 초기화되었습니다."}


@app.get("/health")
def health_check():
    return {"status": "ok"}
