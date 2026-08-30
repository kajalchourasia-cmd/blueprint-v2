# Blueprint Evidence Dev — Evaluations

`phase6-regression-cases.json` is the stable acceptance fixture set. `run-phase6-evals.js` executes the actual exported n8n Code nodes and adds workflow, security, isolation, and persistence contract checks. `latest-phase6-results.json` is the complete machine-readable report.

Current result: **66/66 PASS**. A non-zero exit code means at least one acceptance condition failed.

```powershell
& 'C:\Users\Hrishikesh\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' scripts\run-phase6-evals.js
```

The separate manual trigger in `BP-RESILIENCE-01` is the live n8n failure-injection matrix; its latest run passed 15/15.
