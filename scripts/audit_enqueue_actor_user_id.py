#!/usr/bin/env python3
"""Audit: find every ``queue.enqueue(QueueName.AI_NORMAL, ...)`` site in
``backend/src`` whose payload dict literal does NOT include an
``actor_user_id`` key.

Phase 70 Wave 0 precursor to the RLS fix: Wave 1 Task 1 consumes this
report to know which enqueue call sites must be patched so that
``MemoryWorker`` can restore per-workspace RLS context before processing
each job (PROD-01 / blocking real-PG test).

Usage:
    python scripts/audit_enqueue_actor_user_id.py

Exit code is always 0 (report-only). Output is line-oriented:

    [MISSING] path:line  <snippet>
    [OK]      path:line  <snippet>
    ...
    Summary: N sites; M missing actor_user_id

The parser is deliberately lenient — it walks the ``ast`` module and
treats any ``Call`` whose ``.func`` ends in ``enqueue`` or ``send`` with
a literal Dict as its 2nd positional arg (or ``payload=`` kwarg) as a
candidate. Calls not on ``QueueName.AI_NORMAL`` are skipped (PR review
queue carries repo/pr identifiers, not user ids — Wave 1 handles).
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "backend" / "src" / "pilot_space"

# Task types whose payloads bypass RLS (cross-workspace system jobs).
# Sites that enqueue ONLY these task types are allowed to omit actor_user_id.
# Must stay in sync with _RLS_BYPASS_TASKS in memory_worker.py.
_ALLOWLISTED_TASK_TYPES = frozenset({
    "graph_expiration",
    "artifact_cleanup",
    "send_invitation_email",
    "github_webhook",
})


def _is_ai_normal(arg: ast.expr) -> bool:
    """Return True when arg looks like ``QueueName.AI_NORMAL`` or ``"ai_normal"``."""
    if isinstance(arg, ast.Attribute) and arg.attr == "AI_NORMAL":
        return True
    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
        return arg.value == "ai_normal"
    return False


_TRUSTED_PAYLOAD_FACTORIES = frozenset({"_build_kg_payload"})


def _is_trusted_factory_call(expr: ast.expr) -> bool:
    if isinstance(expr, ast.Call):
        if isinstance(expr.func, ast.Name) and expr.func.id in _TRUSTED_PAYLOAD_FACTORIES:
            return True
        if isinstance(expr.func, ast.Attribute) and expr.func.attr in _TRUSTED_PAYLOAD_FACTORIES:
            return True
    return False


def _payload_dict(call: ast.Call) -> ast.Dict | None:
    # 2nd positional arg, if a Dict literal.
    if len(call.args) >= 2 and isinstance(call.args[1], ast.Dict):
        return call.args[1]
    for kw in call.keywords:
        if kw.arg in ("payload", "message") and isinstance(kw.value, ast.Dict):
            return kw.value
    return None


def _dict_has_key(d: ast.Dict, key: str) -> bool:
    return any(isinstance(k, ast.Constant) and k.value == key for k in d.keys)


def _dict_task_type(d: ast.Dict) -> str | None:
    """Extract task_type literal value from a payload dict literal, if present."""
    for k, v in zip(d.keys, d.values):
        if isinstance(k, ast.Constant) and k.value == "task_type":
            if isinstance(v, ast.Constant) and isinstance(v.value, str):
                return v.value
    return None


def _call_func_name(call: ast.Call) -> str:
    # .enqueue / .send — we want the attribute name.
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    return ""


def audit_file(path: Path) -> list[tuple[int, str, bool, bool]]:
    """Return (lineno, snippet, is_ai_normal, has_actor_user_id) for each candidate."""
    try:
        tree = ast.parse(path.read_text())
    except SyntaxError:
        return []
    source_lines = path.read_text().splitlines()
    results: list[tuple[int, str, bool, bool]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fname = _call_func_name(node)
        if fname not in ("enqueue", "send"):
            continue
        if not node.args:
            continue
        is_ai = _is_ai_normal(node.args[0])
        payload = _payload_dict(node)
        if payload is None:
            # Trusted payload factory calls are considered OK — the factory
            # signature is audited separately (it must include actor_user_id).
            second_arg = node.args[1] if len(node.args) >= 2 else None
            if second_arg is not None and _is_trusted_factory_call(second_arg):
                snippet = source_lines[node.lineno - 1].strip() if node.lineno - 1 < len(source_lines) else ""
                results.append((node.lineno, snippet, is_ai, True))
                continue
            # No literal dict at the call — try to resolve a local assignment
            # of the form `name = {...}` within the enclosing function scope.
            snippet = source_lines[node.lineno - 1].strip() if node.lineno - 1 < len(source_lines) else ""
            # Accept an inline marker comment to assert human-audited correctness.
            has_marker = "actor_user_id" in snippet or (
                node.lineno - 2 >= 0
                and "actor_user_id" in source_lines[node.lineno - 2]
            )
            has_key = has_marker
            if not has_key:
                # Walk the enclosing function/module body for a dict literal
                # assigned to the same name containing 'actor_user_id'.
                name_arg = None
                if len(node.args) >= 2 and isinstance(node.args[1], ast.Name):
                    name_arg = node.args[1].id
                else:
                    for kw in node.keywords:
                        if kw.arg in ("payload", "message") and isinstance(kw.value, ast.Name):
                            name_arg = kw.value.id
                            break
                if name_arg is not None:
                    for assign in ast.walk(tree):
                        dval: ast.Dict | None = None
                        targets: list[ast.expr] = []
                        if isinstance(assign, ast.Assign) and isinstance(assign.value, ast.Dict):
                            dval = assign.value
                            targets = list(assign.targets)
                        elif (
                            isinstance(assign, ast.AnnAssign)
                            and isinstance(assign.value, ast.Dict)
                            and assign.target is not None
                        ):
                            dval = assign.value
                            targets = [assign.target]
                        if dval is None:
                            continue
                        for tgt in targets:
                            if isinstance(tgt, ast.Name) and tgt.id == name_arg:
                                if _dict_has_key(dval, "actor_user_id"):
                                    has_key = True
                                tt = _dict_task_type(dval)
                                if tt in _ALLOWLISTED_TASK_TYPES:
                                    has_key = True
                                break
            results.append((node.lineno, snippet, is_ai, has_key))
            continue
        has_key = _dict_has_key(payload, "actor_user_id")
        # Allowlisted task types bypass RLS in the worker; treat as OK.
        if not has_key:
            tt = _dict_task_type(payload)
            if tt in _ALLOWLISTED_TASK_TYPES:
                has_key = True
        snippet = source_lines[node.lineno - 1].strip() if node.lineno - 1 < len(source_lines) else ""
        results.append((node.lineno, snippet, is_ai, has_key))
    return results


def main() -> int:
    total = 0
    missing = 0
    for path in sorted(SRC_ROOT.rglob("*.py")):
        findings = audit_file(path)
        for lineno, snippet, is_ai, has_key in findings:
            if not is_ai:
                continue  # Non-AI_NORMAL queues skipped per Wave 0 scope.
            total += 1
            rel = path.relative_to(REPO_ROOT)
            status = "[OK]     " if has_key else "[MISSING]"
            if not has_key:
                missing += 1
            print(f"{status} {rel}:{lineno}  {snippet}")
    print()
    print(f"Summary: {total} AI_NORMAL enqueue sites; {missing} missing actor_user_id")
    return 0


if __name__ == "__main__":
    sys.exit(main())
