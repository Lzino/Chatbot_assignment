import json
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"


def _load_json(filename: str) -> list[dict]:
    with open(DATA_DIR / filename, "r", encoding="utf-8") as f:
        return json.load(f)


# ──────────────────────────────────────────
# 1. 상품 검색
# ──────────────────────────────────────────
def search_products(query: str, category: str = "") -> list[dict]:
    """키워드 또는 카테고리로 상품을 검색한다."""
    products = _load_json("products.json")
    results = []

    for product in products:
        match_query = query in product["name"] or query in product["description"]
        match_category = (not category) or (category == product["category"])

        if match_query and match_category:
            results.append(product)

    return results


# ──────────────────────────────────────────
# 2. 주문 조회
# ──────────────────────────────────────────
def check_order(order_id: str = "", customer_name: str = "") -> list[dict]:
    """주문번호 또는 고객 이름으로 주문을 조회한다."""
    orders = _load_json("orders.json")
    results = []

    for order in orders:
        if order_id and order["order_id"] == order_id:
            results.append(order)
        elif customer_name and order["customer_name"] == customer_name:
            results.append(order)

    return results


# ──────────────────────────────────────────
# 3. 장바구니 관리
# ──────────────────────────────────────────
def manage_cart(cart: dict, action: str, product_id: str = "", quantity: int = 1) -> dict:
    """장바구니에 상품을 추가/삭제/수량변경한다.

    Args:
        cart: 현재 장바구니 상태 {"P001": 2, "P003": 1, ...}
        action: "add" | "remove" | "clear"
        product_id: 상품 ID
        quantity: 수량 (add 시 사용)

    Returns:
        {"cart": 갱신된 장바구니, "message": 결과 메시지}
    """
    products = _load_json("products.json")
    product_map = {p["id"]: p for p in products}

    if action == "add":
        if product_id not in product_map:
            return {"cart": cart, "message": f"상품 {product_id}을 찾을 수 없습니다."}
        cart[product_id] = cart.get(product_id, 0) + quantity
        name = product_map[product_id]["name"]
        return {"cart": cart, "message": f"{name} {quantity}개를 장바구니에 담았습니다."}

    elif action == "remove":
        if product_id not in cart:
            return {"cart": cart, "message": f"장바구니에 해당 상품이 없습니다."}
        name = product_map.get(product_id, {}).get("name", product_id)
        del cart[product_id]
        return {"cart": cart, "message": f"{name}을(를) 장바구니에서 삭제했습니다."}

    elif action == "clear":
        return {"cart": {}, "message": "장바구니를 비웠습니다."}

    return {"cart": cart, "message": f"알 수 없는 action: {action}"}


def get_cart_summary(cart: dict) -> dict:
    """장바구니의 상품 목록과 총 금액을 계산한다."""
    products = _load_json("products.json")
    product_map = {p["id"]: p for p in products}

    items = []
    total_price = 0

    for product_id, quantity in cart.items():
        product = product_map.get(product_id)
        if not product:
            continue
        price = product["price"]
        discount = product["discount_rate"]
        final_price = int(price * (1 - discount / 100))
        subtotal = final_price * quantity

        items.append({
            "name": product["name"],
            "quantity": quantity,
            "unit_price": price,
            "discount_rate": discount,
            "final_price": final_price,
            "subtotal": subtotal,
        })
        total_price += subtotal

    return {"items": items, "total_price": total_price}


# ──────────────────────────────────────────
# 4. FAQ 조회
# ──────────────────────────────────────────
def search_faq(topic: str) -> list[dict]:
    """토픽 키워드로 FAQ를 검색한다."""
    faqs = _load_json("faq.json")
    results = []

    for faq in faqs:
        if topic in faq["topic"] or topic in faq["question"] or topic in faq["answer"]:
            results.append(faq)

    return results


# ──────────────────────────────────────────
# 5. 할인 상품 조회
# ──────────────────────────────────────────
def get_discounted_products(min_discount: int = 1) -> list[dict]:
    """할인율이 min_discount% 이상인 상품을 반환한다."""
    products = _load_json("products.json")
    results = []

    for product in products:
        if product["discount_rate"] >= min_discount:
            final_price = int(product["price"] * (1 - product["discount_rate"] / 100))
            results.append({
                **product,
                "final_price": final_price,
            })

    results.sort(key=lambda x: x["discount_rate"], reverse=True)
    return results
