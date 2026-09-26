"""Run the real agent against the LangSmith regression dataset."""

import os
import sys
from pathlib import Path

from langsmith import Client, evaluate


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from database import get_user_by_email, migrate_database
from guardrails import REJECTION_MESSAGE, check_shopping_message
from main import run_agent
from evaluators import expected_tools, response_requirements


DATASET_NAME = "shopping-agent-regression-v1"
migrate_database()
email = os.getenv("EVAL_USER_EMAIL")
if not email:
    raise SystemExit("Set EVAL_USER_EMAIL to an existing registered account.")
user = get_user_by_email(email)
if user is None:
    raise SystemExit("EVAL_USER_EMAIL does not match a registered account.")


def target(inputs: dict) -> dict:
    message = inputs["message"]
    guardrail = check_shopping_message(message)
    if not guardrail.allowed:
        return {"response": REJECTION_MESSAGE}
    history = [{"role": "user", "content": message}]
    return {"response": run_agent(history, user["id"])}


evaluate(
    target,
    data=DATASET_NAME,
    evaluators=[response_requirements, expected_tools],
    experiment_prefix="shopping-agent",
    client=Client(),
)
