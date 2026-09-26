"""Deterministic LangSmith evaluators for response and tool behavior."""


def response_requirements(run, example):
    response = str((run.outputs or {}).get("response", "")).lower()
    expected = example.outputs or {}
    required = [value.lower() for value in expected.get("must_contain", [])]
    forbidden = [value.lower() for value in expected.get("must_not_contain", [])]
    refusal = expected.get("refusal", False)
    passed = all(value in response for value in required)
    passed = passed and all(value not in response for value in forbidden)
    if refusal:
        passed = passed and "only help with shopping" in response
    return {"key": "response_requirements", "score": int(passed)}


def expected_tools(run, example):
    expected = set((example.outputs or {}).get("tools", []))
    observed = set()

    def visit(node):
        name = getattr(node, "name", None)
        if name in expected:
            observed.add(name)
        for child in getattr(node, "child_runs", None) or []:
            visit(child)

    visit(run)
    passed = observed == expected if not expected else expected.issubset(observed)
    return {
        "key": "expected_tools",
        "score": int(passed),
        "comment": f"expected={sorted(expected)}, observed={sorted(observed)}",
    }
