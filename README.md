# Minima savings demo — "the $-saved counter"

A ~2-minute live demo of [Minima](https://docs.minima.sh): add **one kwarg**
(`baseline_model_id`) to an ordinary `recommend()` loop and let it print a real,
ledger-grade figure for the money your default model would have spent.

It runs a batch of mixed tasks (classify / extract / summarize / reason), lets Minima
pick the cheapest capable model per task, closes the loop with `feedback()`, then prints
**estimated** and **realized** savings vs `claude-opus-4-8`.

## Quickstart

```bash
cp .env.example .env      # then fill in MUBIT_API_KEY (+ ANTHROPIC_API_KEY for live)
make run                  # dry-run: no model calls, free
make run-live             # true live: real Anthropic calls, real token costs
make health               # check the Minima API is reachable
make help                 # list targets
```

`make` builds a local `.venv`, installs `minima-cli` + `anthropic`, and runs `demo.py`.

## What you'll see

- **`make run`** — each pick streamed (`classification -> gpt-4o-mini …`), then:
  ```
  estimated: would save $0.2x vs your default (claude-opus-4-8) over 16 routed calls
  realized:  saved $0.2x over 16 reconciled calls (coverage 100%)
  ```
  The **estimated** line is pure `recommend()` accounting (no feedback needed) — it always works.

- **`make run-live`** — picks are constrained to Anthropic so they're runnable here, and realized
  cost is priced from **actual token usage**. Watch the `basis` column flip `prior -> memory`, and
  the hard "reasoning" task **downgrade from Opus to Haiku** once Minima has evidence — the learning
  loop, live.

## Notes

- **Use a real prod Mubit key** (`mbt_<instance>_<key_id>_<secret>`). A local-dev key
  (`mbt_local_*`) routes to a non-existent prod tenant and 503s, so `feedback()` silently fails
  and realized/coverage stay at 0.
- **`.env` is gitignored.** It holds secrets — never commit it, and **rotate the Mubit key** when
  you're done demoing.
- Tunables (in `.env`): `MINIMA_DEMO_REPEAT` (batch repeats), `MINIMA_DEMO_NS` (pin a namespace),
  `MINIMA_URL` (staging/self-host).
