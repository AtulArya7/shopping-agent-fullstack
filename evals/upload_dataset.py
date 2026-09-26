"""Upload the versioned local evaluation cases to LangSmith."""

import json
from pathlib import Path

from langsmith import Client


DATASET_NAME = "shopping-agent-regression-v1"
cases = json.loads((Path(__file__).parent / "dataset.json").read_text(encoding="utf-8"))
client = Client()

if client.has_dataset(dataset_name=DATASET_NAME):
    dataset = client.read_dataset(dataset_name=DATASET_NAME)
else:
    dataset = client.create_dataset(
        DATASET_NAME,
        description="Shopping, memory, tool-routing, and guardrail regression cases.",
    )

client.create_examples(
    dataset_id=dataset.id,
    examples=[{"inputs": case["input"], "outputs": case["expected"]} for case in cases],
)
print(f"Uploaded {len(cases)} cases to {DATASET_NAME}.")
