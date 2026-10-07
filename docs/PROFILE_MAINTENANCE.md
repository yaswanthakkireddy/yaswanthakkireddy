# Maintaining this GitHub profile

The public repository `yaswanthakkireddy/yaswanthakkireddy` serves the root `README.md` on the account profile. Assets live in `assets/`; automation belongs in root `.github/workflows/`.

## Information hierarchy

1. Identity and engineering profile
2. Four flagship systems: CortexAgent, MigrationLens, NeuroShield, FairLend
3. Reliability-first AI Engineering
4. Supporting systems: ExperimentOS and ModelWatch
5. Engineering Telemetry with evidence links
6. More Work: CarbonLedgerX
7. Contact links

The source upload previously lived under `github-profile-readme/`. Its original contents remain in Git history.

## Claims and evidence

The README evidence table links every numeric claim to a project artifact, test suite or specific CI run. Test counts are neither coverage percentages nor cross-project productivity measures. Do not sum unrelated tests into a portfolio-wide total.

- CortexAgent's 20/20 is a single-model behavioral-contract baseline, not an end-to-end orchestrator guarantee.
- MigrationLens's 37/37 applies to expected findings on the Sakila fixture. Its 138 passed/3 skipped belongs to the documented release audit.
- NeuroShield's 0.5177 PR-AUC belongs to GraphSAGE on the Elliptic temporal holdout.
- FairLend's research metrics use the 500K-row HMDA benchmark. The synthetic demo differs. Its recorded CI run passed 15 tests and skipped 19.
- ExperimentOS's recorded CI run passed 30 tests.
- ModelWatch has 43 automated checks, some requiring local artifacts. Do not label all 43 as passing without an applicable run.

For new results, update the linked evidence, the README, relevant SVG text/alt text and the generator together. Never infer production safety, legal certification, deployment, users or test coverage from these figures.

## Telemetry operation

`scripts/build_activity.py` generates `assets/activity.svg` from public GitHub repository metadata and workflow data. It excludes this profile repository, uses fixed project order and absolute activity dates, and does not render the current date or relative ages.

CI status must be tied to the current default-branch commit. A previously successful run is not evidence that a newer commit passed. API failure should fail the job and preserve the last committed asset.

The scheduled workflow runs at 03:17 UTC (08:47 India time). It commits only changed telemetry content. Editing the README or a static card should not manufacture an activity update.

`verify-profile.yml` checks the public live profile in a browser at desktop and mobile sizes. It retains screenshots for inspection; a passing automated layout check does not replace visual review.

## Account settings outside this repository

Set the public name to **Yaswanth Kumar Akkireddy**.

Suggested bio: **AI Engineer | Agentic AI · RAG · LLM Evaluation, Reliability & Security**

Website: https://www.linkedin.com/in/yaswanthakkireddy

Pinned order: cortexagent, MigrationLens, NeuroShield, fairlend, ExperimentOS, modelwatch.

Repository descriptions and topics are account/repository metadata, not fields in this README. Do not claim those settings were changed unless they were saved through GitHub and verified.


## TOSCO profile feature

TOSCO is featured as an agent-action clearance prototype. Its evidence is the typed contract, deterministic gates, SHA256 proof chain and HMAC token flow documented in its repository. Keep seeded-evidence and mock-bank scope visible. Do not present documented test counts as a newly verified run, or the historical Vultr proof as a currently hosted production service.

Suggested six pins: TOSCO, CortexAgent, MigrationLens, NeuroShield, FairLend and ModelWatch. ExperimentOS remains a supporting README card; CarbonLedgerX stays in More Work.
