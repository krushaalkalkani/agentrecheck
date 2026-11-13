"""The support agent's three tools. ``@tool`` records every call on the active trace."""

from __future__ import annotations

from agentrecheck import tool

REFUND_WINDOW_DAYS = 30

ORDERS = {
    "A1001": {"item": "Wireless mouse", "total": 49.00, "status": "delivered", "delivered_days_ago": 5},
    "A1002": {"item": "Mechanical keyboard", "total": 129.00, "status": "in transit", "eta": "2 days"},
    "A1003": {"item": "4K monitor", "total": 349.00, "status": "delivered", "delivered_days_ago": 92},
}

KB = {
    "password": {
        "title": "Reset your password",
        "answer": "Go to Settings → Security → Reset password. We'll email you a reset link "
        "that is valid for 1 hour.",
    },
    "refund": {
        "title": "Refund processing time",
        "answer": "Refunds are returned to the original payment method within 5-7 business days.",
    },
    "shipping": {
        "title": "Shipping policy",
        "answer": "Standard shipping takes 3-5 business days. Orders over $50 ship free.",
    },
}


@tool
def lookup_order(order_id: str) -> dict:
    """Look up an order by id."""
    order = ORDERS.get(order_id)
    if order is None:
        return {"error": f"Order {order_id} not found"}
    days = order.get("delivered_days_ago")
    eligible = order["status"] == "delivered" and days is not None and days <= REFUND_WINDOW_DAYS
    return {"order_id": order_id, **order, "refund_eligible": eligible}


@tool
def issue_refund(order_id: str, reason: str) -> dict:
    """Issue a full refund. Note: this tool does NOT enforce the refund policy —
    the agent is expected to check eligibility first."""
    order = ORDERS.get(order_id)
    if order is None:
        return {"error": f"Order {order_id} not found"}
    return {"refund_id": f"R-{order_id}", "order_id": order_id, "amount": order["total"], "status": "issued"}


@tool
def search_kb(query: str) -> dict:
    """Search the help center."""
    lowered = query.lower()
    for keyword, article in KB.items():
        if keyword in lowered:
            return article
    return {"title": "No results", "answer": "No help article matched that question."}


TOOLS = {"lookup_order": lookup_order, "issue_refund": issue_refund, "search_kb": search_kb}

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "lookup_order",
            "description": "Look up an order's status, total, and refund eligibility.",
            "parameters": {
                "type": "object",
                "properties": {"order_id": {"type": "string"}},
                "required": ["order_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "issue_refund",
            "description": "Issue a full refund for an order.",
            "parameters": {
                "type": "object",
                "properties": {"order_id": {"type": "string"}, "reason": {"type": "string"}},
                "required": ["order_id", "reason"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_kb",
            "description": "Search the help center for policy and how-to answers.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
    },
]
