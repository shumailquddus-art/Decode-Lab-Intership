# ✍️ Automated Copywriting & Tone Transformer

**DecodeLabs — Generative AI Industrial Training, Project 2**

Takes a raw product description and programmatically generates professional
marketing copy tailored to different platforms — LinkedIn, Instagram, Email,
Twitter/X — with full control over tone and inference parameters
(Temperature, Top_P). Supports both single one-off generations and
concurrent bulk processing from a CSV of products.

**Key features:**
- 🧩 Dynamic prompt compiler — injects `Product_Name`, `Platform`, `Tone`, and
  a raw description into a locked master instruction template via f-strings
- 🔒 Structured, validated output — every generation is checked against a
  Pydantic schema (`GeneratedCopy`) before it's accepted
- 📏 Platform-aware constraints — character limits and style rules baked
  into the prompt per platform (e.g. 280 chars for Twitter/X), with a
  hard-truncate safety net if the model overshoots anyway
- ⚡ Dual pipeline — single generations run synchronously; bulk CSV jobs
  fan out concurrently through `asyncio.gather` behind an
  `asyncio.Semaphore`, so you control exactly how many requests run at once
- 🔁 Retry shield — `tenacity` retries transient failures (rate limits,
  malformed output) with exponential backoff + jitter, so one bad response
  doesn't kill an entire batch
- ✅ Offline self-test — verifies prompt compilation, validation, retry
  recovery, and concurrency ordering without spending API credits

## Setup

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
```

## Single generation

```bash
python3 copywriter.py \
    --product "Wireless Earbuds" \
    --description "Noise-cancelling earbuds with 30hr battery" \
    --platform linkedin \
    --tone professional \
    --temperature 0.7 \
    --top-p 1.0
```

Outputs JSON matching the `GeneratedCopy` schema:
```json
{
  "product_name": "Wireless Earbuds",
  "platform": "linkedin",
  "tone": "professional",
  "headline": "...",
  "body": "...",
  "hashtags": ["#WirelessEarbuds", "#TechLaunch"],
  "character_count": 842
}
```

## Bulk generation (CSV)

CSV must have columns: `product_name,description,platform,tone`
(see `products_sample.csv` for an example).

```bash
python3 copywriter.py --csv products_sample.csv --concurrency 5 --output results.json
```

Each row is generated concurrently (capped by `--concurrency`), with
per-row error isolation — one failing row won't take down the batch — and
results are returned in the same order as the input CSV.

## Offline self-test (no API key needed)

```bash
python3 copywriter.py --test
```

Runs four checks: prompt variable injection, platform validation, the async
retry-and-recover path (simulates one bad model response before success),
and character-limit enforcement.

## How it maps to the project requirements

| Requirement (from the brief) | Where it lives |
|---|---|
| Python script taking `Product_Name`, `Platform`, `Tone` | `argparse` in `main()` |
| Inject variables into a dynamic string template | `build_prompt()` — the Master Instruction Template |
| Handle `Temperature` and `Top_P` | Passed straight through in `generate_single()` / `_generate_one_async()` |
| Platform-specific formatting (LinkedIn, Instagram, Email) | `PLATFORM_SPECS` dict, folded into the prompt |
| Scalable content pipelines | `generate_bulk_async()` — Semaphore-gated concurrency via `asyncio.gather` |

## Notes / extensions

- **Twitter/X was added as a fourth platform** beyond the brief's three
  (LinkedIn, Instagram, Email) to exercise the hard character-limit path —
  280 characters is the tightest constraint and a good stress test for the
  truncation safety net.
- The deck's "Ultimate Scale" slide references OpenAI's dedicated Batch API
  (50% cost reduction, 24hr window) for very large jobs. This project uses
  Anthropic's Claude API, which has an equivalent **Message Batches API**
  for the same use case — a natural next step if bulk volume grows past
  what the semaphore-gated async pipeline comfortably handles.
- Temperature is worth experimenting with per the deck's suggestion: try
  `--temperature 0.9` on Instagram copy vs `--temperature 0.2` on Email copy
  and compare brand consistency.

---

Built as part of the [DecodeLabs](https://www.decodelabs.tech) Generative AI
Industrial Training Kit, Batch 2026.
