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
2. Add Flutterwave secrets in GitHub Actions repository secrets; never commit them.
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
- Approval is not a password and does not bypass provider controls. A real Flutterwave payout/external action must be separately configured and executed by a provider integration that honors the approved record.
- Rejecting a request keeps it from becoming an approved authorization.

## Payment provider
The farm is configured for Flutterwave in Cameroon with MTN/Orange mobile-money payout support. Verified incoming earnings are **multi-currency**: the original provider currency is preserved (for example USD, EUR, GBP, CAD, etc.) when the provider reports it. The project never adds unlike currencies together and never invents an exchange rate.

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
