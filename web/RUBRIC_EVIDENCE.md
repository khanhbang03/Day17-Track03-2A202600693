# Rubric evidence map

This document maps each Day 17 rubric requirement to concrete, inspectable
evidence. The `100/100` label in the showcase is a self-audit of rubric coverage;
the final score remains the reviewer’s decision.

## 0–60: Complete basic implementation

| Requirement | Evidence |
|---|---|
| Baseline remembers only within one thread | `src/agent_baseline.py`; `test_cross_session_recall` confirms it forgets in a new thread |
| Advanced Agent has persistent `User.md` | `UserProfileStore` in `src/memory_store.py`; `AdvancedAgent.profile_store` |
| Compact memory genuinely activates | `CompactMemoryManager`; `test_compact_trigger` |
| Vietnamese benchmark dataset | `data/conversations.json`, `data/advanced_long_context.json` |
| Clear repository documentation | `README.md`, `Guide.md`, `Rubric.md`, `src/README.md`, `web/README.md` |

## 60–75: Benchmark and core tests

`src/benchmark.py` runs the same conversations through Baseline and Advanced.
Its output includes all required columns:

- Agent tokens only
- Prompt tokens processed
- Cross-session recall
- Response quality
- Memory growth (bytes)
- Compactions

Behavioral tests in `src/test_agents.py` cover:

1. `User.md` read/write/edit
2. compact trigger
3. cross-session recall
4. prompt-load reduction on long threads
5. correction replacement
6. rejection of questions and noisy statements

## 75–90: Real compact-memory analysis

Both required suites are implemented:

- Standard Benchmark: `data/conversations.json`
- Long-Context Stress Benchmark: `data/advanced_long_context.json`

Verified offline results:

| Suite | Agent | Agent tokens | Prompt tokens | Recall | Quality | Memory bytes | Compactions |
|---|---:|---:|---:|---:|---:|---:|---:|
| Standard | Baseline | 1,080 | 12,852 | 0.036 | 0.161 | 0 | 0 |
| Standard | Advanced | 2,005 | 23,699 | 1.000 | 1.000 | 341 | 0 |
| Stress | Baseline | 192 | 21,718 | 0.000 | 0.125 | 0 | 0 |
| Stress | Advanced | 391 | 15,362 | 1.000 | 1.000 | 248 | 7 |

Interpretation:

- Advanced costs more in short conversations because loading persistent memory is
  overhead and compaction has not activated.
- In long conversations, compaction cuts prompt tokens processed by 29.3%.
- The main optimization is input/context processing, not generated output.
- Persistent memory introduces file-growth and false-fact risks.

## 90–100: Useful production bonuses

### Confidence threshold

`extract_profile_updates()` only persists explicit assertions. Questions,
jokes, temporary travel, and negated facts are rejected.

Benefit: fewer false memories. Risk: conservative patterns can miss valid facts.

### Structured entity extraction

Facts are stored as named fields such as `name`, `location`, `profession`,
`response_style`, `favorite_food`, and `interests`.

Benefit: inspectable recall and bounded profile growth. Risk: the schema may not
cover every user preference.

### Conflict handling

`UserProfileStore.upsert_fact()` keeps one current value per field. A correction
from `backend engineer` to `MLOps engineer` removes the stale profession.

Benefit: higher corrected-fact recall. Risk: a mistaken correction can overwrite
a valid value without provenance or human confirmation.

### Bounded compact summary

The summary has a hard size bound, preventing compaction from merely moving
unbounded growth into another string.

Benefit: stable long-context cost. Risk: old low-salience details can be lost.

## Required reviewer story

1. Baseline forgets across a fresh session.
2. Advanced loads `User.md`, raising recall to 1.000.
3. Long conversations drive Baseline prompt cost upward.
4. Seven compactions reduce Advanced stress prompt cost to 15,362 tokens.
5. Confidence filtering, conflict handling, and bounded storage address the new
   complexity introduced by persistent memory.
