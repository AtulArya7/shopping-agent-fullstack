# Agent evaluations

1. Set `LANGSMITH_API_KEY`, `LANGSMITH_TRACING=true`, and
   `LANGSMITH_PROJECT=shopping-agent`.
2. Register a local test account and set `EVAL_USER_EMAIL` to that email.
3. Upload cases once with `python evals/upload_dataset.py`.
4. Run an experiment with `python evals/run_evaluation.py`.

The dataset covers search, ratings, order history, preferences, guardrails,
and expected tool trajectories. Add production failures to `dataset.json`
before the next agent or prompt change.
