from __future__ import annotations

import ast
from typing import Any

import numpy as np
import pandas as pd


SAFE_FUNCTIONS = {"sum", "mean", "count", "safe_div"}
SAFE_BINOPS = (ast.Add, ast.Sub, ast.Mult, ast.Div)
SAFE_UNARYOPS = (ast.UAdd, ast.USub)


class UnsafeExpressionError(ValueError):
    pass


def validate_expression(expression: str, variables: dict[str, Any]) -> list[str]:
    tree = _parse(expression)
    _validate_node(tree, variables)
    return sorted(_names_in_tree(tree))


def evaluate_expression(expression: str, variables: dict[str, Any]) -> Any:
    tree = _parse(expression)
    _validate_node(tree, variables)
    return _eval_node(tree.body, variables)


def _parse(expression: str) -> ast.Expression:
    if not expression or not expression.strip():
        raise UnsafeExpressionError("Expression must not be empty.")
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise UnsafeExpressionError(f"Invalid expression syntax: {exc.msg}") from exc
    return tree


def _validate_node(node: ast.AST, variables: dict[str, Any]) -> None:
    if isinstance(node, ast.Expression):
        _validate_node(node.body, variables)
        return
    if isinstance(node, ast.BinOp):
        if not isinstance(node.op, SAFE_BINOPS):
            raise UnsafeExpressionError("Only +, -, *, / operators are allowed.")
        _validate_node(node.left, variables)
        _validate_node(node.right, variables)
        return
    if isinstance(node, ast.UnaryOp):
        if not isinstance(node.op, SAFE_UNARYOPS):
            raise UnsafeExpressionError("Only unary + and - are allowed.")
        _validate_node(node.operand, variables)
        return
    if isinstance(node, ast.Name):
        if node.id.startswith("__"):
            raise UnsafeExpressionError("Dunder names are not allowed.")
        if node.id not in variables:
            raise UnsafeExpressionError(f"Unknown variable or role: {node.id}")
        return
    if isinstance(node, ast.Constant):
        if not isinstance(node.value, (int, float)):
            raise UnsafeExpressionError("Only numeric constants are allowed.")
        return
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in SAFE_FUNCTIONS:
            raise UnsafeExpressionError("Only safe functions are allowed: sum, mean, count, safe_div.")
        if node.keywords:
            raise UnsafeExpressionError("Keyword arguments are not allowed.")
        for arg in node.args:
            _validate_node(arg, variables)
        if node.func.id == "safe_div" and len(node.args) != 2:
            raise UnsafeExpressionError("safe_div requires exactly two arguments.")
        if node.func.id in {"sum", "mean", "count"} and len(node.args) != 1:
            raise UnsafeExpressionError(f"{node.func.id} requires exactly one argument.")
        return
    raise UnsafeExpressionError(f"Unsupported expression element: {type(node).__name__}")


def _eval_node(node: ast.AST, variables: dict[str, Any]) -> Any:
    if isinstance(node, ast.BinOp):
        left = _eval_node(node.left, variables)
        right = _eval_node(node.right, variables)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            return _safe_div(left, right)
    if isinstance(node, ast.UnaryOp):
        value = _eval_node(node.operand, variables)
        return value if isinstance(node.op, ast.UAdd) else -value
    if isinstance(node, ast.Name):
        return variables[node.id]
    if isinstance(node, ast.Constant):
        return float(node.value)
    if isinstance(node, ast.Call):
        values = [_eval_node(arg, variables) for arg in node.args]
        function = node.func.id  # type: ignore[union-attr]
        if function == "sum":
            return _sum(values[0])
        if function == "mean":
            return _mean(values[0])
        if function == "count":
            return _count(values[0])
        if function == "safe_div":
            return _safe_div(values[0], values[1])
    raise UnsafeExpressionError(f"Unsupported expression element: {type(node).__name__}")


def _safe_div(left: Any, right: Any) -> Any:
    with np.errstate(divide="ignore", invalid="ignore"):
        if isinstance(left, pd.Series) or isinstance(right, pd.Series):
            result = left / right
            if isinstance(result, pd.Series):
                return result.replace([np.inf, -np.inf], np.nan)
            return np.nan if not np.isfinite(result) else result
        if right in {0, 0.0} or pd.isna(right):
            return np.nan
        result = left / right
        return np.nan if isinstance(result, float) and not np.isfinite(result) else result


def _sum(value: Any) -> float:
    if isinstance(value, pd.Series):
        return float(value.sum(skipna=True))
    return float(value) if pd.notna(value) else np.nan


def _mean(value: Any) -> float:
    if isinstance(value, pd.Series):
        return float(value.mean(skipna=True))
    return float(value) if pd.notna(value) else np.nan


def _count(value: Any) -> int:
    if isinstance(value, pd.Series):
        return int(value.count())
    return 0 if pd.isna(value) else 1


def _names_in_tree(tree: ast.AST) -> set[str]:
    return {node.id for node in ast.walk(tree) if isinstance(node, ast.Name) and node.id not in SAFE_FUNCTIONS}
