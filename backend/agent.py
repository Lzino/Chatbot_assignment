import json
from openai import OpenAI
from backend.tools import (
    search_products,
    check_order,
    manage_cart,
    get_cart_summary,
    search_faq,
    get_discounted_products,
)

SYSTEM_PROMPT = """당신은 이커머스 쇼핑몰 'StyleShop'의 AI 상담원입니다.

역할:
- 고객의 상품 검색, 주문 조회, 장바구니 관리, FAQ 응대, 할인 안내를 도와줍니다.
- 항상 친절하고 간결하게 한국어로 응답합니다.
- 상품 추천 시 가격과 할인 정보를 함께 안내합니다.
- 장바구니에 상품을 담으면 현재 장바구니 상태를 요약해줍니다.

주의:
- 모르는 정보는 추측하지 말고 "확인이 어렵습니다"라고 안내하세요.
- tool 호출 결과가 빈 리스트이면 "검색 결과가 없습니다"라고 안내하세요.
"""

# OpenAI Function Calling에 전달할 tool 정의
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "search_products",
            "description": "키워드 또는 카테고리로 상품을 검색한다",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "검색 키워드 (예: 티셔츠, 가방)"},
                    "category": {
                        "type": "string",
                        "description": "카테고리 필터 (상의/하의/아우터/신발/가방/액세서리)",
                        "default": "",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_order",
            "description": "주문번호 또는 고객 이름으로 주문 상태를 조회한다",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "주문번호 (예: ORD-240301-001)"},
                    "customer_name": {"type": "string", "description": "고객 이름 (예: 김민수)"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "manage_cart",
            "description": "장바구니에 상품을 추가, 삭제, 또는 비운다",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["add", "remove", "clear"],
                        "description": "add: 추가, remove: 삭제, clear: 전체 비우기",
                    },
                    "product_id": {"type": "string", "description": "상품 ID (예: P001)"},
                    "quantity": {"type": "integer", "description": "수량 (기본 1)", "default": 1},
                },
                "required": ["action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_cart_summary",
            "description": "현재 장바구니의 상품 목록과 총 금액을 조회한다",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_faq",
            "description": "반품, 교환, 배송, 결제, 쿠폰 등 자주 묻는 질문을 검색한다",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "description": "검색 키워드 (예: 반품, 배송비, 쿠폰)"},
                },
                "required": ["topic"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_discounted_products",
            "description": "현재 할인 중인 상품 목록을 조회한다",
            "parameters": {
                "type": "object",
                "properties": {
                    "min_discount": {
                        "type": "integer",
                        "description": "최소 할인율 (기본 1%)",
                        "default": 1,
                    },
                },
                "required": [],
            },
        },
    },
]


def _execute_tool(tool_name: str, arguments: dict, cart: dict) -> tuple[str, dict]:
    """tool 이름과 인자를 받아 실행하고 결과 JSON 문자열과 갱신된 cart를 반환한다."""

    if tool_name == "search_products":
        result = search_products(**arguments)
    elif tool_name == "check_order":
        result = check_order(**arguments)
    elif tool_name == "manage_cart":
        result = manage_cart(cart, **arguments)
        cart = result["cart"]
    elif tool_name == "get_cart_summary":
        result = get_cart_summary(cart)
    elif tool_name == "search_faq":
        result = search_faq(**arguments)
    elif tool_name == "get_discounted_products":
        result = get_discounted_products(**arguments)
    else:
        result = {"error": f"알 수 없는 tool: {tool_name}"}

    return json.dumps(result, ensure_ascii=False), cart


def chat(user_message: str, conversation_history: list[dict], cart: dict, api_key: str) -> tuple[str, list[dict], dict]:
    """사용자 메시지를 받아 에이전트 응답을 반환한다.

    Args:
        user_message: 사용자 입력
        conversation_history: 지금까지의 대화 기록
        cart: 현재 장바구니 상태
        api_key: OpenAI API 키

    Returns:
        (assistant_reply, updated_history, updated_cart)
    """
    client = OpenAI(api_key=api_key)

    conversation_history.append({"role": "user", "content": user_message})

    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + conversation_history

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        tools=TOOL_DEFINITIONS,
    )

    assistant_message = response.choices[0].message

    # tool 호출이 필요한 경우 반복 처리
    while assistant_message.tool_calls:
        conversation_history.append(assistant_message.model_dump())

        for tool_call in assistant_message.tool_calls:
            tool_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)

            result_json, cart = _execute_tool(tool_name, arguments, cart)

            conversation_history.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result_json,
            })

        # tool 결과를 포함해 다시 LLM 호출
        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + conversation_history

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=TOOL_DEFINITIONS,
        )
        assistant_message = response.choices[0].message

    reply = assistant_message.content
    conversation_history.append({"role": "assistant", "content": reply})

    return reply, conversation_history, cart
