# Agent Evolution — GitHub-first setup

## 1. Upload
Upload the contents of this folder to the root of a GitHub repository.

## 2. Secrets
Add only the credentials you are legitimately authorized to use as GitHub Actions Secrets/Variables. Never commit passwords, API keys, session cookies, or tokens.

Typical optional secrets/variables used by this build include:
- `EXA_API_KEY`
- `MTN_CLIENT_ID`
- `MTN_CLIENT_SECRET`
- `PAYOUT_DESTINATION_ID`
- `PAYOUT_MOBILE_MONEY_NETWORK`

Keep live payout disabled until the provider has approved the account and the owner has completed any required verification.

## 3. Run manually
GitHub Actions → **Agent Evolution - Autonomous Agent Survival Farm** → **Run workflow**.

The workflow performs a preflight and then runs the autonomous cycle with checkpoints and stage timeouts.

## 4. What persists
The workflow commits state files such as agent memory, opportunity records, work queues, business state, economy ledgers, reputation, and orchestrator state back to the repository.

## 5. Internet capability
Agents can use the configured public web/API capability and ordinary permitted browser actions. They must use authorized accounts and cannot bypass CAPTCHA, authentication, KYC/age controls, paywalls, rate limits, or other security controls.

## 6. Important limitation
GitHub Actions is a cloud CI runner. It cannot behave like an always-on human desktop or Android phone. This build therefore focuses the farm on cloud-executable research, planning, digital work, business logic, accounting, learning, and persistence. The Android/game subsystem is retained as optional code but is **not part of the GitHub workflow**.

## 7. Money truth
Discovery or completed internal work never creates money. Only provider-confirmed incoming payments enter the verified ledger. The project does not fabricate customers, sales, conversions, or payment confirmations.
