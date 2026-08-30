# Blueprint data package

## What each file does

| File | Purpose | Used for |
|---|---|---|
| `blueprint_idea_master.csv` | 70 online-first synthetic planning priors with 60 founder, market, cost, risk, and validation fields | Matching an idea to an initial archetype, assumptions, risks, and suggested tests |
| `blueprint_evidence_events.csv` | Append-only observations from completed interviews, tests, payments, and launches | Evidence strength, positive signals, readiness, and Key Signal values |
| `blueprint_phase_actions.csv` | Exact actions within every phase, including target people, channels, outreach copy, framework, deliverable, thresholds, time, cost, and resources | Expandable roadmap instructions |
| `blueprint_signal_benchmarks.csv` | Weak, developing, and strong evidence thresholds by archetype and phase | Key Signal scoring and decision gates |
| `blueprint_financial_models.csv` | Recommended cash allocation by idea archetype and stage | Financial allocation panel |
| `founder_journeys.csv` | Comparable founder paths and outcomes | Reality-check references |
| `cost_templates.csv` | Cash, time, relationship, health, and opportunity-cost ranges | Real Cost Ledger |
| `gap_library.csv` | Unseen questions, missing voices, and real-cost prompts | Gap layers |

## Important data rule

Synthetic seed rows are labeled as synthetic. They are product-test fixtures, not claimed market facts. A new project therefore starts at zero evidence. Only rows recorded in `blueprint_evidence_events.csv` may increase evidence strength, positive signals, readiness, or Key Signal values. The production version should combine user-generated evidence, licensed/public benchmark sources, and transparent source dates rather than presenting generated numbers as objective truth.
