"""Minima 2-min demo: "The $-saved counter".

One kwarg (baseline_model_id) turns an ordinary recommend() loop into an honest,
ledger-grade savings figure. Run mixed tasks, let Minima pick the cheapest capable
model per task, close the loop with feedback, then print what your default would
have cost.

  make run       -> dry-run cost path (no model calls, free). The ESTIMATED savings
                    line is real server-truth from recommend(); realized mirrors it.
  make run-live  -> real Anthropic calls (picks constrained to anthropic so they are
                    runnable here): realized cost is priced from ACTUAL token usage,
                    and you can watch the router learn to downgrade as evidence lands.
"""

import os
import uuid

# Load .env if python-dotenv is available (so `python demo.py` works standalone too).
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from minima_client import MinimaClient

URL = os.environ.get("MINIMA_URL", "https://api.minima.sh")
DEFAULT = "claude-opus-4-8"  # what a naive setup would send EVERYTHING to
NS = os.environ.get("MINIMA_DEMO_NS") or f"demo-{uuid.uuid4().hex[:8]}"  # clean ledger
REPEAT = int(os.environ.get("MINIMA_DEMO_REPEAT", "4"))
LIVE = os.environ.get("MINIMA_DEMO_LIVE") == "1"

if not os.environ.get("MUBIT_API_KEY"):
    raise SystemExit(
        "MUBIT_API_KEY is not set. Copy .env.example -> .env and fill in your keys "
        "(see README.md), then re-run `make run`."
    )
if LIVE and not os.environ.get("ANTHROPIC_API_KEY"):
    raise SystemExit("ANTHROPIC_API_KEY is required for `make run-live`. Add it to .env.")

TASKS = [
    ("Classify this support ticket by urgency: 'card declined at checkout twice'.",
     "classification"),
    ("Extract the order id and total from: 'Order #A-9931 totalling $48.20 shipped.'",
     "extraction"),
    ("Summarize this incident report into 3 bullets: a DB failover at 02:14 UTC caused "
     "12 minutes of 5xx on checkout; mitigated by promoting the replica.", "summarization"),
    ("Design a retry policy with jitter for a flaky payment webhook; justify the math.",
     "reasoning"),
] * REPEAT

acli = None
CONSTRAINTS = None
if LIVE:
    import anthropic

    from minima_client import Constraints

    acli = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    # LIVE picks must be runnable through the Anthropic SDK -> constrain to anthropic
    # (also the on-brand Claude->Claude downgrade story: haiku/sonnet vs the opus default).
    CONSTRAINTS = Constraints(allowed_providers=["anthropic"])


def price_map(client):
    """model_id -> (input $/Mtok, output $/Mtok) from the live catalog."""
    out = {}
    for m in client.models().models:
        i = getattr(m, "input_cost_per_mtok", None)
        o = getattr(m, "output_cost_per_mtok", None)
        if i is not None and o is not None:
            out[m.model_id] = (i, o)
    return out


fb_accepted = 0
with MinimaClient(URL, api_key=os.environ["MUBIT_API_KEY"]) as minima:
    rates = price_map(minima) if LIVE else {}
    for text, ttype in TASKS:
        # The ONE kwarg: declare the model you'd have used anyway -> honest savings.
        rec = minima.recommend(
            {"task": text, "task_type": ttype},
            cost_quality_tradeoff=3,
            namespace=NS,
            baseline_model_id=DEFAULT,
            constraints=CONSTRAINTS,
        )
        model = rec.recommended_model.model_id
        est = rec.recommended_model.est_cost_usd

        if LIVE:
            msg = acli.messages.create(
                model=model, max_tokens=256,
                messages=[{"role": "user", "content": text}],
            )
            in_tok, out_tok = msg.usage.input_tokens, msg.usage.output_tokens
            ir, orate = rates.get(model, (None, None))
            actual = (in_tok * ir + out_tok * orate) / 1e6 if ir is not None else est
            print(f"{ttype:14s} -> {model:22s}  est ${est:.6f}  REAL ${actual:.6f} "
                  f"({in_tok}+{out_tok} tok)  basis={rec.decision_basis}")
        else:
            in_tok, out_tok, actual = 0, 0, est  # dry-run: realized mirrors estimate
            print(f"{ttype:14s} -> {model:22s}  est ${est:.6f}  (basis={rec.decision_basis})")

        fb = minima.feedback(
            rec.recommendation_id, model, "success",
            quality_score=0.95,
            input_tokens=in_tok,
            output_tokens=out_tok,
            actual_cost_usd=actual,
            verified_in_production=True,
        )
        fb_accepted += int(getattr(fb, "accepted", False))

    # ===== THE WOW LINE =====
    report = minima.savings(namespace=NS, days=1, group_by="task_type")
    e = report.summary.estimated
    r = report.summary.realized
    cov = report.health.get("feedback_coverage", 0.0)
    print(f"\nnamespace: {NS}   (mode: {'LIVE' if LIVE else 'dry-run'})")
    print(f"feedback accepted: {fb_accepted}/{len(TASKS)}")
    # Headline = ESTIMATED projection (server-computed from declared baseline vs picks;
    # no feedback needed). This is the number that always works.
    print(f"\nestimated: would save ${e.savings_vs_declared_usd:.4f} vs your default "
          f"({DEFAULT}) over {e.n_declared} routed calls")
    print(f"           (generous vs-premium baseline: ${e.savings_vs_premium_usd:.4f})")
    # Realized only exists once feedback reconciles (needs a real prod Mubit key).
    if r.n_reconciled:
        print(f"realized:  saved ${r.savings_vs_declared_est_usd:.4f} over "
              f"{r.n_reconciled} reconciled calls (coverage {cov:.0%})")
    else:
        print(f"realized:  n/a — 0 reconciled (coverage {cov:.0%}); feedback isn't "
              f"persisting. Are you using a real prod Mubit key (not mbt_local_*)?")
