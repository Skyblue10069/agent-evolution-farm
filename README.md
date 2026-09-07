# Agent Evolution — Full Autonomous Agent Survival Farm

The farm now combines autonomous discovery, work-first funding control, owner approvals, agent trust and activity history:

1. **Full autonomous brain** — each living agent keeps memory, goals, experiments, observations and lessons and generates its own hypotheses. There is no fixed action/earning menu.
2. **Deep worldwide discovery** — the farm searches public web signals globally, including businesses and other valuable opportunities. Search seeds are discovery prompts, not a fixed opportunity catalogue.
3. **True competition + business evolution** — every living agent evaluates discovered opportunities; work preparation is awarded to the strongest current fit. Agent-owned business strategies evolve from observed demand, work history and verified revenue.

## Money and owner control
- Agents start at $0 and verified revenue is independent per agent.
- Only provider-confirmed incoming payments count as money.
- Receiving is the only automatic money direction.
- Agents cannot debit/withdraw owner funds.
- Any proposed use of funds must be written as an owner-review request before any withdrawal/use can happen.
- No fake money, fake customers, spam, impersonation, credential theft, CAPTCHA bypass or payment fraud.
- Platform eligibility, age, geographic and account rules must be respected.

## No fixed opportunity menu
Agents are not presented with a predefined list of things they can do. They inspect discovered signals, form hypotheses, compare value/effort/eligibility, learn from outcomes and propose their own next steps. Safety rules are hard constraints, not opportunities.

## Run
`python daily_money_engine.py`

## Setup from a phone
1. Put the project files in the GitHub repository.
2. Add MTN sandbox credentials in GitHub Actions repository secrets; never commit API keys. Keep live payout disabled until the provider has legitimately approved the account.
3. Use `python approval_system.py serve` for the owner dashboard when running locally.
4. Keep the payout destination/network configured only in server-side secrets/environment.
5. Test with provider sandbox/test events before enabling any live payout capability.

The repository is multi-currency for verified earnings, but the Cameroon mobile-money payout executor intentionally accepts **XAF only** unless an actual provider-reported conversion/settlement has been recorded.


The six-run schedule remains in `.github/workflows/survival.yml`.


## One-click owner approval
- Agents begin with zero money and are expected to **work first** using their available capabilities and discovered opportunities.
- They do not stop immediately to ask the owner for money. Owner-funding requests are a later-stage escalation when the agent can explain why the expense is needed now.
- Agents can create spending/use proposals in `approval_queue.json`.
- Open the owner approval screen with `python approval_system.py serve`.
- Each pending request shows much more than just “opportunity”: the reason, why now, what the money buys, work already completed, evidence, expected result/revenue, cost breakdown, alternatives, risks, deadline and success condition.
- Pressing **Approve** records the owner decision; no code is required for each approval.
- Approval is not a password and does not bypass provider controls. A real MTN payout/external action must be separately configured and executed by a provider integration that honors the approved record.
- Rejecting a request keeps it from becoming an approved authorization.

## Payment provider
The farm is configured for MTN in Cameroon with MTN/Orange mobile-money payout support. Verified incoming earnings are **multi-currency**: the original provider currency is preserved (for example USD, EUR, GBP, CAD, etc.) when the provider reports it. The project never adds unlike currencies together and never invents an exchange rate.

If Flutterwave actually reports an XAF settlement/conversion, that XAF amount is stored separately and may be used for an approved Cameroon mobile-money payout. A non-XAF earning cannot be silently treated as XAF. Provider/account eligibility, supported currencies, FX and settlement rules remain subject to the live Flutterwave account.

For the current project, verified incoming money is receive-only. Agents cannot withdraw or debit the owner account. Any later use requires explicit owner approval and a separate provider execution step.


## Agent trust and activity history
- Every agent starts with zero money and zero developed skills.
- Agents must record work before they can request owner funding.
- A funding request is blocked until the agent has at least two recorded work activities and reaches the configured trust threshold (35/100 by default).
- Trust is based on recorded successful runs, verified revenue and completed work, with failures reducing trust. It is a gate, not an automatic spending permission.
- `agent_activity_history.json` stores the agent's work/earning/run/funding history.
- The phone-friendly owner screen has an **Agent history** tab showing trust, work count, successful runs, verified revenue and recent events.
- Owner approval remains separate from payout execution.

## Agent rankings and progress graphs
- The owner dashboard now includes a **Rankings** tab with a live leaderboard for every active agent.
- Ranking priority is verified revenue first, then trust, total developed skill and wins.
- The **Graphs** tab lets the owner select any agent and view trust over time, verified earnings over time, and any individual skill over time.
- Time-series checkpoints are stored in `agent_activity_history.json` as snapshots. New runs append snapshots; old installations begin collecting graph history from the next run onward.

## Multi-currency earnings
- Agents may pursue legitimate opportunities paying in any currency that the configured payment provider/account actually supports.
- Every verified payment keeps its original three-letter currency code.
- Dashboard totals show separate currency buckets instead of falsely combining USD/EUR/GBP/XAF.
- No conversion is simulated. Only an explicit provider-reported settlement/conversion record creates a converted amount.
- Cameroon mobile-money payouts require an actual XAF balance for this route.


## Work-completion guarantee

The farm now separates discovery from execution. Opportunity discovery has a hard **10-minute maximum**. After discovery, living agents compete for discovered work and the work executor creates a persisted work item. An item cannot be marked `COMPLETED` until its artifact exists and quality checks pass. Unfinished items remain in `work_queue.json` and are resumed on the next workflow cycle; they are never silently abandoned.

### Maximum improvement plan
- **10-minute discovery timebox** so GitHub Actions time is protected.
- **Open-ended discovery**: discovered signals, not a hard-coded job menu, drive opportunities.
- **Worldwide search** with deduplication and obvious-risk filtering.
- **Competition**: every living agent can evaluate the same opportunity pool.
- **Zero-start economy**: no starting cash and no developed skills.
- **Hard execution state machine**: queued → in progress → QA → completed, or externally blocked.
- **No silent abandonment**: unfinished work persists across runs.
- **Completion proof**: each completed internal work artifact receives a deterministic proof hash.
- **Quality gates** before completion.
- **Skill growth only from completed work**, not from merely discovering or selecting an opportunity.
- **Real-payment-only accounting**: completion never creates money; only provider-confirmed payments create verified revenue.
- **Multi-currency separation** with live FX quotes treated as quotes until an actual provider-confirmed settlement exists.
- **Agent-owned businesses** evolve from observed demand, completed work, experiments and verified revenue.
- **Persistent memory and experiments** let agents learn from outcomes.
- **Trust system** rewards observed successful work and penalizes failures.
- **Permanent death** remains a farm mechanic; dead agents are not respawned.
- **Champion cloning** remains enabled under the editable owner rules.
- **Human/owner approval gates** remain for external spending and payout execution.
- **Safety gates** prohibit spam, impersonation, credential theft, payment fraud, CAPTCHA bypass and unauthorized accounts.

> Important: the farm can automate preparation and lawful digital work inside the repository, but it cannot truthfully claim an external client accepted a submission or paid unless that external system confirms it.


## Cactus Needle — main-character AI
- **Cactus Needle** is the farm's named main-character AI, distinct from ordinary agents by identity and a persistent **14 MB memory core**.
- It follows the same safety, payment-verification and owner-approval gates as every other participant. It is **not** granted automatic money, automatic wins or immunity from the farm's economic rules.
- Its memory journal is stored in `cactus_needle_memory.bin` and its inspectable cognitive state is stored in `state.json` under the Cactus Needle record.
- Maximum-improvement systems include self-modeling, self-critique, adaptive planning, evidence-first completion, failure learning, emergent specialization, persistent work, QA gates and experience-based skill growth.
- The 14 MB figure is a persistent memory capacity, not a claim that a 14 MB file is itself an intelligent model.


## Ultimate intelligence, business and economy upgrade

The farm now adds a superintelligence decision layer, evidence-weighted counterfactual planning, strategy calibration, business portfolio/capacity management, offer lifecycle experiments, and economic liquidity/currency-exposure intelligence. These systems strengthen decisions and accounting without inventing customers, sales, payments, or external success.

### Cactus Needle full upgrade
Cactus Needle remains the protected main-character AI with a bounded 14,000,000-byte memory journal. It now has an integrity self-test, evidence-only mentor lessons from other agents, a strategy map, and memory health checks. It still receives no free skills, automatic wins, automatic payments, or bypass of owner/provider controls.

## Internet Capability Layer
Each agent now has a bounded Internet operator (`internet_agent.py`) capable of public HTTPS browsing/API access plus normal browser interactions: navigate, read/extract, click, type, select, upload, download and screenshots. Actions are audited with hashes and per-task limits. Account identities remain separate from secrets; credentials/tokens must be supplied through authorized environment/secret storage and are never committed to the repository.

The layer deliberately does not bypass CAPTCHAs, authentication, paywalls, rate limits, platform safeguards, or age/KYC requirements. It can only act with accounts and permissions that are legitimately available to the runner.


## Android device control
A companion `android_controller/` project and `android_control.py` bridge are included. The controller can launch apps, open HTTPS URLs, tap/type through Accessibility, and use normal Android navigation. It cannot silently install APKs or bypass device/app security. A GitHub Actions runner cannot directly control a physical phone; use a local Android runtime or an authenticated relay if cloud-to-device control is needed.

## Full game-playing AI
The project now includes `game_ai/` with Android screenshot vision, autonomous touch/swipe decisions, persistent learning, exploration/exploitation, and bounded per-session evolution. The Android companion provides a localhost-only command server on `127.0.0.1:8787` and exposes screenshots, active-window data, taps, and swipes to the local agent runtime.

Game AI is intentionally rule-respecting: it does not bypass anti-cheat, DRM, app permissions, CAPTCHAs, or network protections.

## Game File Editing
The game agent now has a user-authorized game-data editor. It can inspect and edit supported save/config/mod/add-on data inside directories explicitly granted to the local runtime, create automatic backups, verify SHA-256 hashes, and audit every edit. It does not bypass Android scoped storage, DRM, anti-cheat, authentication, or protected/executable game binaries. Configure `game_file_policy.json` with directories the device owner has explicitly granted.

## Automatic game-file discovery and field learning
`game_file_discovery.py` adds an automatic, permission-gated inventory of accessible game save/config data. It scans only `allowed_roots`, detects safe text formats, parses JSON structures, inventories nested fields, and generates explainable meaning hypotheses from field names and value types. Results persist in `game_file_schemas.json` and `game_file_discovery_state.json` so agents can learn across sessions.

Use:
```bash
python game_file_discovery.py discover
python game_file_discovery.py experiment-copy /authorized/path/to/save.json
```

Experiments, when enabled later, are performed on copies rather than silently modifying the original save. Android scoped-storage, encryption, DRM, anti-cheat, credentials, and executable/APK/DEX/native files remain outside the capability boundary.

## GitHub-first Ultimate Cycle
The current workflow uses `farm_orchestrator.py` as the single controlled entry point. It checkpoints after every stage, records stage outcomes in `orchestrator_state.json`, and appends an audit trail to `orchestrator_audit.jsonl`. The discovery stage has a 540-second internal deadline and a 570-second subprocess timeout.

`integrity_check.py` performs a compile/security preflight before the farm runs. The workflow uses Node 24-compatible GitHub Actions (`actions/checkout@v6` and `actions/setup-python@v6`) and prevents overlapping scheduled runs with workflow concurrency.

The Android/game modules remain in the repository as optional future components, but the GitHub workflow does not depend on a physical phone or Android emulator.

### Agent self-modification
Each agent has a private strategy-code surface under `agent_code/`. Agents can evolve that code through bounded mutations. Candidate code is AST-validated, syntax-checked, restricted to a tiny scoring function, and atomically replaced only when valid. Core safety, payment, accounting, orchestration, authentication, and security code is not agent-editable. A maximum of 100 agents self-edit per cycle by default so large populations remain practical; every agent gets turns over repeated cycles.

The default population target is `7777` agents. Existing smaller farms are expanded without resetting accumulated history. Use `AGENT_POPULATION_SIZE` to override the target and `SELF_MOD_BATCH` to change the per-cycle self-modification batch.


## Maximum agent-improvement layer
The farm includes `evolution_upgrade.py`, a bounded improvement layer that runs after the main survival cycle. It adds:
- smarter confidence/uncertainty profiles and fallback planning;
- earned specialization without locking agents to roles;
- discovery-signal classification from real discovered opportunities;
- A/B-style strategy experiments measured only from observed outcomes;
- batch tournaments for scalable competition;
- knowledge sharing from observed agent lessons;
- business adaptation metrics based on observed state;
- economy concentration/risk telemetry without combining unlike currencies;
- rolling recovery checkpoints;
- long-term learning journal;
- security telemetry;
- modular provider/API adapter registry;
- scaling metadata for 7,777+ agents and worker sharding;
- a generated read-only `dashboard.html` for quick owner inspection.

The improvement layer never creates fake customers, fake sales, fake payments, or fake completion. External credentials stay in environment/secret storage.

## Continuous improvement layer
The farm now includes additional bounded improvement systems:
- **Evolution genetics:** measurable traits, mutations, generations, and lineage metadata.
- **Experiment lab:** observational A/B experiments using existing agent outcomes only; no synthetic revenue.
- **Agent marketplace:** internal offers/capacity records for agents to discover and cooperate on work.
- **Recovery checkpoints:** compact integrity-digested checkpoints for operational recovery metadata.
- **Static dashboard:** generates `dashboard.html` from persisted state with alive/dead counts, verified XAF and top agents.
- **Stronger self-modification guard:** strategy editing remains sandboxed and cannot import or invoke system/process APIs.

These additions improve learning, competition, cooperation, observability, and recovery while keeping payment verification and security controls protected.

## Adaptive skills, multitasking and dynamic teams
The farm now includes a dedicated adaptive skill engine. All agents still begin with zero developed skills and no fixed profession, but experience can develop 30 meta-skills covering reasoning, planning, research, creativity, decision-making, adaptability, negotiation, leadership, teamwork, resource management, risk management, business strategy, quality control, meta-learning and self-improvement. Behavioral traits evolve alongside these skills.

Agents can also multitask: each living agent receives a learned, bounded concurrent-task capacity (up to 6). Multiple work items can remain active at once and are tracked independently. Existing completion gates remain mandatory, so multitasking never counts as free success or creates money.

Leadership/delegation can produce dynamic internal teams, while the recursive hierarchy lets a child independently create children of its own. Child and champion lineage now carries evolving traits rather than only copying basic metadata.

## MAX+ Evolution layer

The MAX+ layer adds a coordinator-controlled shard workflow and deeper evolution telemetry:
- **Coordinator:** partitions agents into isolated shard jobs, prevents concurrent canonical-state mutation, validates ownership, and performs the only merge into `state.json`.
- **Causal learning:** computes conservative observational relationships and labels them as non-causal until experiments support stronger conclusions.
- **Counterfactual engine:** compares bounded alternative strategies using observed history only; estimates are never recorded as real revenue/results.
- **Strategy trees:** bounded multi-step plans with evidence-only decision policy.
- **Immune system:** quarantines impossible IDs, invalid skill values, negative verified cash, and similar state anomalies.
- **Generation store:** immutable, hashed generation snapshots with bounded index retention.
- **Evolution observatory:** read-only aggregate telemetry for population, survival, skills, verified revenue and top agents.

### How the coordinator works
GitHub Actions runs one trusted coordinator. The coordinator creates isolated shard workers; workers **read** the canonical state and write only `coordinator_runs/<run>/result-*.json`. The coordinator verifies every agent appears at most once, merges only approved telemetry, writes a merge digest, and then the normal GitHub persistence step commits the canonical state.

This is intentionally safer than having multiple runners simultaneously edit `state.json`. A future multi-runner version can use artifact upload/download or another durable job store for the same shard-result contract. The current repository remains correct on a single GitHub runner while still being ready for larger populations.
