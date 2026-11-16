"""An MCP server with the support agent's three tools.

Run it on its own to poke at it:
    python server.py            # speaks MCP over stdio

The agent in agent.py launches this file as a subprocess and calls the tools
through the Model Context Protocol instead of importing them.
"""

from __future__ import annotations

from mcp.server.mcpserver import MCPServer

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

server = MCPServer(
    "acme-support",
    instructions="Order lookup, refunds, and help-center search for Acme Store.",
)


@server.tool()
def lookup_order(order_id: str) -> dict:
    """Look up an order's status, total, and refund eligibility."""
    order = ORDERS.get(order_id)
    if order is None:
        return {"error": f"Order {order_id} not found"}
    days = order.get("delivered_days_ago")
    eligible = order["status"] == "delivered" and days is not None and days <= REFUND_WINDOW_DAYS
    return {"order_id": order_id, **order, "refund_eligible": eligible}


@server.tool()
def issue_refund(order_id: str, reason: str) -> dict:
    """Issue a full refund for an order.

    This tool does NOT enforce the refund policy. The agent is expected to
    check eligibility with lookup_order first.
    """
    order = ORDERS.get(order_id)
    if order is None:
        return {"error": f"Order {order_id} not found"}
    return {"refund_id": f"R-{order_id}", "order_id": order_id, "amount": order["total"], "status": "issued"}


@server.tool()
def search_kb(query: str) -> dict:
    """Search the help center for policy and how-to answers."""
    lowered = query.lower()
    for keyword, article in KB.items():
        if keyword in lowered:
            return article
    return {"title": "No results", "answer": "No help article matched that question."}


if __name__ == "__main__":
    server.run()
