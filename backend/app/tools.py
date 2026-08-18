

from __future__ import annotations

import ast
import operator
from typing import Any, Callable

from app.models import ToolCall, ToolName, ToolResult
from app.vectorstore import knowledge_base

_SAFE_OPS: dict[type, Callable[..., float]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
}


def _safe_eval(node: ast.AST) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _SAFE_OPS:
        return _SAFE_OPS[type(node.op)](_safe_eval(node.left), _safe_eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _SAFE_OPS:
        return _SAFE_OPS[type(node.op)](_safe_eval(node.operand))
    raise ValueError(f"Unsupported expression node: {ast.dump(node)}")


def run_calculator(arguments: dict[str, Any]) -> tuple[bool, str, str | None]:
    expression = str(arguments.get("expression", ""))
    try:
        tree = ast.parse(expression, mode="eval")
        result = _safe_eval(tree.body)
        return True, str(result), None
    except Exception as exc:  # noqa: BLE001 - surfaced to caller as tool error
        return False, "", f"Could not evaluate '{expression}': {exc}"


def run_knowledge_base_search(arguments: dict[str, Any]) -> tuple[bool, str, str | None]:
    query = str(arguments.get("query", ""))
    if not query:
        return False, "", "Missing 'query' argument"
    hits = knowledge_base.search(query, top_k=2)
    if not hits:
        return True, "No relevant documents found.", None
    formatted = "\n".join(f"- ({score:.2f}) {text}" for text, score in hits)
    return True, formatted, None


def run_web_search(arguments: dict[str, Any]) -> tuple[bool, str, str | None]:
    # Mocked: no outbound network call. Swap for a real search API client
    # (kept behind the same signature) without touching the orchestrator.
    query = str(arguments.get("query", ""))
    return True, f"[demo mode] Web search is mocked. Would have searched for: '{query}'", None


_HANDLERS: dict[ToolName, Callable[[dict[str, Any]], tuple[bool, str, str | None]]] = {
    ToolName.CALCULATOR: run_calculator,
    ToolName.KNOWLEDGE_BASE_SEARCH: run_knowledge_base_search,
    ToolName.WEB_SEARCH: run_web_search,
}


def execute_tool(call: ToolCall) -> ToolResult:
    handler = _HANDLERS[call.tool]
    success, output, error = handler(call.arguments)
    return ToolResult(call_id=call.id, tool=call.tool, success=success, output=output, error=error)
