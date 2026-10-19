# Newly implemented: the remaining plan-doc issues

Branch `features/greek_identifiers`, cut 2026-10-19 from `features/word_renderer` at `8a07fb9`.
This file records what was implemented, the decisions taken on open questions, and the
coordination with the Word renderer session.

## Scope

The plan docs in the repo root list three outstanding items:

| Plan | Issue | Status on this branch |
|---|---|---|
| `plan_222_word_renderer.md` | #222 Word renderer | **Not touched.** It's owned by the Word session on `features/word_renderer`. |
| `plan_117_greek_identifiers.md` | #117 Greek letters joined to text | **Implemented** (see below). |
| `plan_258_trailing_zeros_pr.md` | #258 v1 `trailing_zeros` PR | **No code.** See [#258](#258-no-code-change). |

## #117: Greek identifiers

### Decisions on the plan's open questions

Nobody had answered these, so I went with the plan's recommendations. Each is easy to reverse.

1. R3 (the prefix split) is **on by default**. Turn it off with `GREEK_PREFIXES = False` in a
   renderer subclass.
2. A prefix splits before an **uppercase letter or a digit** (`alpha2` → α2).
3. #101 (comma subscripts) is **not** included and stays a separate PR.

### Progress

- [x] Step 1: `src/handcalcs/renderers/identifiers.py` and `tests/test_identifiers.py`

## #258: no code change

The memory notes from the batch-1 session say that #221 (trailing zeros in v2) was dropped
because "v2 already implements it". Plan option A ("port to v2") is therefore already met. What's
left is a GitHub action that I haven't taken: close PR #258 with the reply drafted in
`plan_258_trailing_zeros_pr.md`, adjusted to say the feature already exists in v2. I left it for
you because it's outward-facing.

## Coordination with the Word renderer session

- The Word session is running twice, as `handcalcs-fd` and `handcalcs-c3`. Both have the same
  session id, `128aef54…`, because of the ttyd orphan issue, and both are waiting for your input.
  I sent messages to `handcalcs-fd` only.
- 2026-10-19, message 1 (sent before any code changed): announced the branch, the shared
  `identifiers.py`, `BaseRenderer.GREEK_PREFIXES`, and the identifier output changes. I asked it
  to build the OMML identifier code on `identifiers.split_greek` instead of copying a Greek table,
  and to rebase onto or merge this branch once it lands. No action is needed on its branch now.
