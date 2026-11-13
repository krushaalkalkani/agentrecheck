"""A deterministic, offline stand-in for the OpenAI client.

It returns objects shaped like Chat Completions responses and follows a simple
policy that *reads the system prompt*: it only verifies an order before
refunding when the prompt tells it to. That makes prompt regressions
reproducible without an API key — swap the prompt, and the behavior changes.
"""

from __future__ import annotations

import json
import re
import time
from types import SimpleNamespace as NS


def _tool_call(index: int, name: str, args: dict) -> NS:
    return NS(id=f"call_{index}", type="function", function=NS(name=name, arguments=json.dumps(args)))


def _kb_topic(text: str) -> str | None:
    if "password" in text:
        return "reset password"
    if "how long" in text and "refund" in text:
        return "refund processing time"
    if "shipping" in text:
        return "shipping policy"
    return None


class _Completions:
    def create(self, *, model: str, messages: list[dict], tools: list | None = None, **_: object) -> NS:
        time.sleep(0.02)  # stand in for network latency so timings are non-zero
        system = next((m["content"] for m in messages if m["role"] == "system"), "")
        user = next((m["content"] for m in messages if m["role"] == "user"), "")
        lowered = user.lower()

        # Tool results so far, keyed by tool name.
        names = {
            call["id"]: call["function"]["name"]
            for m in messages
            if m["role"] == "assistant"
            for call in m.get("tool_calls") or []
        }
        results = {
            names[m["tool_call_id"]]: json.loads(m["content"]) for m in messages if m["role"] == "tool"
        }

        match = re.search(r"\b([A-Z]\d{4})\b", user)
        order_id = match.group(1) if match else None
        wants_refund = "refund" in lowered and order_id is not None
        wants_status = order_id is not None and any(
            k in lowered for k in ("where is", "status", "track", "arrive")
        )
        topic = _kb_topic(lowered)
        verify_first = "always call lookup_order" in system.lower()

        call: tuple[str, dict] | None = None
        order = results.get("lookup_order")
        if wants_refund:
            if verify_first and order is None:
                call = ("lookup_order", {"order_id": order_id})
            elif "issue_refund" not in results and (order is None or order.get("refund_eligible")):
                reason = "arrived damaged" if "damaged" in lowered else "customer request"
                call = ("issue_refund", {"order_id": order_id, "reason": reason})
        elif wants_status and order is None:
            call = ("lookup_order", {"order_id": order_id})
        if call is None and topic and "search_kb" not in results:
            call = ("search_kb", {"query": topic})

        if call is not None:
            message = NS(content=None, tool_calls=[_tool_call(len(names), *call)])
        else:
            message = NS(content=self._answer(order_id, results, wants_refund), tool_calls=None)

        prompt_chars = len(json.dumps(messages)) + len(json.dumps(tools or []))
        output_chars = len(message.content or json.dumps(call))
        return NS(
            model=model,
            choices=[NS(message=message, finish_reason="tool_calls" if call else "stop")],
            usage=NS(prompt_tokens=prompt_chars // 4, completion_tokens=max(1, output_chars // 4)),
        )

    @staticmethod
    def _answer(order_id: str | None, results: dict, wants_refund: bool) -> str:
        parts: list[str] = []
        order = results.get("lookup_order")
        refund = results.get("issue_refund")
        if order and "error" in order:
            parts.append(f"I couldn't find order {order_id}. Could you double-check the order number?")
        elif refund and "error" not in refund:
            parts.append(
                f"Your refund of ${refund['amount']:.2f} for order {order_id} has been issued "
                f"(reference {refund['refund_id']})."
            )
        elif wants_refund and order:
            parts.append(
                f"I'm sorry — order {order_id} was delivered {order['delivered_days_ago']} days ago, "
                "which is outside our 30-day refund window, so I'm unable to refund it."
            )
        elif order:
            status = f"Order {order_id} ({order['item']}) is {order['status']}"
            parts.append(f"{status} and should arrive in {order['eta']}." if order.get("eta") else f"{status}.")
        if "search_kb" in results:
            parts.append(results["search_kb"]["answer"])
        return " ".join(parts) or "Happy to help! Could you share your order number or question?"


class MockOpenAI:
    """Drop-in for ``openai.OpenAI()`` covering ``chat.completions.create``."""

    def __init__(self) -> None:
        self.chat = NS(completions=_Completions())
