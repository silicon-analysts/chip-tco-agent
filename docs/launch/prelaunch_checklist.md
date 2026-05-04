# Pre-launch validation checklist

Walk through this top-to-bottom before pushing the chip-tco-agent repo
public, submitting to MCP registries, or posting on Show HN. Any
unchecked item is a blocker.

Each item ends with the **specific command or page** to verify it. If you
can't verify in 30 seconds, the launch isn't ready.

---

## 1. Code & repo hygiene

### Secrets and history

- [ ] `.env` is gitignored
  - Verify: `cat .gitignore | grep '^\.env$'` returns a hit
- [ ] `.env` is not present in git history
  - Verify: `git log --all --full-history -- .env` returns nothing
- [ ] No API keys (`sa_live_`, `sk-ant-`), no Supabase URLs, no Stripe
      secrets in any committed file
  - Verify: `git grep -E '(sa_live_|sk-ant-api|sb_secret|sk_live_|whsec_)' -- '*' ':!docs/launch/show_hn_post.md' ':!docs/launch/blog_post.md'`
    returns nothing (the launch posts may mention `sa_live_` as a placeholder)
- [ ] No internal Slack channel names, internal product codenames, or
      unreleased-feature references in any committed file
  - Verify: read through `README.md`, `docs/`, and `notebook-spec-tco-agent.md`
    once

### `notebook-spec-tco-agent.md` decision

- [ ] Decision made: **keep in repo root** (transparency about the build
      brief) **OR move to `docs/internal/` and gitignore** (keep it private)
  - The current state is "kept in repo root." If you want it private,
    `git mv notebook-spec-tco-agent.md docs/internal/` and add
    `docs/internal/` to `.gitignore`.
  - Recommendation: keep it. The transparency signal is on-brand and the
    spec doesn't contain anything genuinely confidential.

### Build & runtime

- [ ] `uv sync` resolves cleanly on a fresh clone
  - Verify: `cd /tmp && rm -rf chip-tco-agent-test && git clone <repo> chip-tco-agent-test && cd chip-tco-agent-test && uv sync`
- [ ] Python 3.10, 3.11, 3.12 all work
  - Verify: `uv run --python 3.10 python -c "import chip_tco_agent"`,
    same for `3.11` and `3.12`
- [ ] Step 0 fixes have been verified end-to-end with real API keys
  - Verify: `bash scripts/regenerate_example_outputs.sh` (cost: ~$1.50,
    time: ~15 min)
  - Spot-check: `examples/outputs/03_edge_inference.txt` has
    `WARNING: No option in this analysis meets the user's stated 10ms
    TTFT constraint` as the FIRST sentence of `rationale_short` (or
    similar phrasing the agent chooses given the prompt rule)
  - Spot-check: `examples/outputs/02_8b_finetune.txt` displays
    `Horizon: 30 days` (not `1 months`)
  - Spot-check: `examples/outputs/02_8b_finetune.txt` does NOT show a
    `$/M tok` column (suppressed for short-horizon queries)
- [ ] All five examples + the headline run without errors
  - Verify: `bash scripts/regenerate_example_outputs.sh` finishes with
    exit 0 and all 5 transcript files are non-empty
- [ ] The notebook (`chip_tco_agent.ipynb`) executes end-to-end in Jupyter
  - Verify: `uv run jupyter nbconvert --to notebook --execute chip_tco_agent.ipynb --output /tmp/notebook_smoke_test.ipynb`
    completes (or run interactively in a kernel)
- [ ] Pydantic schema validation works on the actual agent output
  - Verify: this was verified in Phase 2; only re-test if the schema or
    system prompt changed in Phase 3 (it did — the `horizon_original`
    field was added). Run `python3 -c "import chip_tco_agent; chip_tco_agent.respond_with_recommendation_tool()"`
    to confirm no exceptions.

### Links

- [ ] Every link in `README.md` returns 200
  - Verify: extract URLs from the README and `curl -sI <url> | head -1`
    each one. The links that matter most:
    - https://siliconanalysts.com (homepage)
    - https://siliconanalysts.com/developers (key signup)
    - https://siliconanalysts.com/api/mcp (MCP endpoint — should respond
      to a properly-authenticated `initialize` POST)
    - https://siliconanalysts.com/pro (paid tier page; create if it
      doesn't exist before linking from the README)
    - https://console.anthropic.com (Anthropic key signup)
- [ ] Every link in `docs/launch/*.md` resolves
  - Verify: same approach. Two known TBDs to fill in before submission:
    - mcp.so registry submission URL
    - Anthropic connector directory submission URL

---

## 2. Content review

### README

- [ ] No marketing superlatives ("revolutionary", "game-changing", "world's first")
  - Verify: `grep -iE 'revolutionary|game.?changing|world.?s first|breakthrough' README.md`
    returns nothing
- [ ] "Limitations" section is present and genuinely honest
  - Verify: read it once. The current draft includes the B200 estimate,
    cloud-pricing snapshot, EU coverage gap, multi-modal weakness, and
    bring-your-own-LLM caveats. Don't soften any of them.
- [ ] Every number in the README ties back to an actual run
  - Verify: cross-reference the "Cost per query" table against
    `demo_output.txt` and `examples/outputs/*.txt` footers
- [ ] B200 FP8 benchmark is consistently flagged as estimated, not measured
  - Verify: `grep -iE 'b200.{0,200}(estimat|medium.confidence|extrapolat|halv)' README.md docs/launch/*.md`
    finds the flag in the right places

### Show HN post

- [ ] Body is ≤500 words
  - Verify: count words in the body section of `docs/launch/show_hn_post.md`
- [ ] All numbers in the post body match real measurements (the `19 tool
      calls / 4 turns / 150s / $0.39` from `demo_output.txt`)
- [ ] The "honest paragraph" is intact (B200 estimate, snapshot freshness,
      bring-your-own-LLM)
- [ ] All three asks are present (defensibility, framework choice,
      snapshot vs. scrape)
- [ ] Title is ≤80 characters
  - Verify: `wc -c <<< 'Show HN: An MCP agent that compares H100/H200/B200/MI300X TCO in 30 seconds'`
    returns ≤80 (it returns 78)

### Blog post

- [ ] Length is 1500–2500 words
  - Verify: `wc -w docs/launch/blog_post.md` returns a number in that range
- [ ] Hook line distinct from the README and Show HN (each artifact uses a
      different framing)
- [ ] Section 5 ("What's still hard") is honest and specific, not a softened
      list of "future work"
- [ ] PydanticAI variant claim removed or replaced with "if there's interest"
      (we did not actually ship a `pydantic_ai_variant.py`)

### Registry submissions

- [ ] All three describe **Silicon Analysts** as the MCP server (not
      chip-tco-agent, which is the demo)
- [ ] All three list 6 tools with consistent descriptions
- [ ] All three link to chip-tco-agent as the demo
- [ ] All three are honest about the snapshot data freshness model
- [ ] TBD URLs are clearly marked so they don't accidentally get submitted
      with placeholder values

---

## 3. Operational readiness

### Silicon Analysts production health

- [ ] Better Stack monitors are green for the past 24 hours
  - Verify: log into Better Stack dashboard
- [ ] Sentry is wired and capturing errors (if applicable)
  - Verify: trigger a test 401 from `curl -i https://siliconanalysts.com/api/v1/accelerators`
    and see the event land in Sentry within 60s
- [ ] Upstash rate limiting is functional (Pro tier verified working)
  - Verify: a Pro-tier key returns `x-ratelimit-limit: 10000` (this was
    fixed earlier in this session — the api_keys.tier authoritative-vs-
    profile bug)
  - Verify: a free-tier key on the 101st call of the day returns 429 with
    a `Retry-After` header

### API endpoints

- [ ] `GET https://siliconanalysts.com/api/v1/accelerators` with a valid
      key returns 200 with the expected envelope
  - Verify: `curl -i -H "x-api-key: $SA_KEY" https://siliconanalysts.com/api/v1/accelerators | head -10`
- [ ] `POST https://siliconanalysts.com/api/mcp` with a valid bearer
      responds to `initialize` cleanly
  - Verify: the chip-tco-agent demo run succeeds end-to-end against
    production
- [ ] 429 responses include the upgrade link
  - Verify: read `lib/utils/apiMiddleware.ts` and confirm the message
    points at /pro

### Account / signup flow

- [ ] `/developers` page lets a brand-new user sign up, generate a key,
      and copy it without errors
  - Verify: do this end-to-end in an incognito window with a throwaway
    email. Time it — if it takes >2 minutes, the launch will lose
    conversion.
- [ ] The bug from Phase 2 (PostgREST embedded join error → silent
      validateApiKey failure → -32004) stays fixed
  - Verify: a freshly-created free-tier key successfully calls
    `get_accelerator_costs` once

### Status & docs

- [ ] Status page (status.siliconanalysts.com or Better Stack public page)
      is reachable and shows current state
- [ ] `/data-quality` page is up and accurate
- [ ] `/developers` page documents the 6 tools, free tier limits, paid
      tier link, and links to the chip-tco-agent demo

### A backup Pro-tier key

- [ ] At least one Pro-tier API key exists and is in your password manager
      so you can demonstrate Pro features during launch (e.g., the
      betterstack-monitor key from earlier in the conversation)

---

## 4. GitHub repo presentation

- [ ] Repo is public on github.com/silicon-analysts/chip-tco-agent
- [ ] Repo title: "Chip TCO Comparison Agent" (matches README H1)
- [ ] Repo description (the one-line under the title): "Compare H100, H200,
      B200, MI300X TCO across cloud providers and on-prem — open-source
      MCP agent."
- [ ] Repo topics added (helps discovery): `mcp`, `agent`, `anthropic`,
      `pydantic`, `gpu`, `tco`, `finops`, `semiconductor`, `llm`,
      `infrastructure`
- [ ] Social card image set (use a clean screenshot of the headline
      query's ranked-options table; 1200×630 PNG, file at
      `docs/screenshots/social_card.png`, configured via repo settings →
      Social preview)
- [ ] README renders cleanly on github.com/silicon-analysts/chip-tco-agent
      on both mobile and desktop
  - Verify: open in your phone's browser
- [ ] First-time visitor experience: someone landing on the repo can
      identify what it does, see a sample output, and reach the
      Quickstart in <30 seconds
  - Verify: ask a friend who hasn't seen it; time them
- [ ] License file present and correctly attributed
  - Verify: `head -3 LICENSE` shows MIT and `Silicon Analysts`

---

## 5. Launch sequencing

The order matters. Submit registry entries first so they're indexed by
the time Show HN traffic lands; that turns Show HN viewers into Smithery
discoveries 24 hours later.

### Suggested order

1. **Day 1 (Monday)**: push repo public. Check that everything in
   sections 1–4 above is green. Don't announce yet.
2. **Day 1 evening**: open PRs / submissions to the three registries:
   - Smithery (fastest turnaround historically)
   - mcp.so (PR-based; merge takes 1–3 days)
   - Anthropic connector directory (TBD; may be longer)
3. **Day 2 (Tuesday)**: start Twitter / LinkedIn pre-announcement —
   share the headline screenshot and a link to the repo. No Show HN yet.
   Watch for any first-day issues from organic traffic.
4. **Day 3 (Wednesday) at 8:00 AM Eastern**: post on Show HN. Be at the
   keyboard for the next 4 hours minimum. Have the comment-thread
   responses (in `docs/launch/show_hn_post.md`) ready to copy-paste.
5. **Day 3 evening**: publish the companion blog post on
   `siliconanalysts.com/blog/engineering`. Cross-link from the Show HN
   thread once it's live.
6. **Day 4–7**: respond to GitHub issues, register on additional
   directories that surface in HN comments, watch the rate-limit
   metrics, decide whether to enable prompt caching now or later.

### Sequencing checklist

- [ ] Monday: repo public, sections 1–4 of this checklist green
- [ ] Monday evening: 3 registry submissions sent
- [ ] Tuesday: Twitter / LinkedIn pre-announcement
- [ ] Wednesday 8 AM ET: Show HN post
- [ ] Wednesday evening: blog post published
- [ ] Thursday–Sunday: monitor + respond

### Bail-out criteria

If on Monday any of the following are true, push the launch by a week
rather than ship something half-broken:

- [ ] Better Stack shows a P1/P2 incident in the past 24 hours
- [ ] /developers signup flow takes >2 minutes for a fresh user
- [ ] The bug from Phase 2 (validateApiKey -32004) is regressing in any way
- [ ] Any of the 5 example queries fails to produce a valid recommendation
- [ ] B200 estimate caveat is missing from any launch artifact

---

## 6. Post-launch (first 7 days)

Not a launch blocker, but worth pre-deciding so you're not improvising:

- [ ] Decide policy on PRs that update `cloud_prices.json` for non-US
      regions (likely volume after Show HN)
- [ ] Decide whether to enable prompt caching this week (cost lever:
      $0.30 → $0.04 per query)
- [ ] Decide whether to ship the PydanticAI variant or close that as
      out-of-scope
- [ ] Watch the free-tier rate-limit hit rate; tune up if launch traffic
      is starving legitimate evaluators
