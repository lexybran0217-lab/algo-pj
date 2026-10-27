# Submission checklist

Candidate version: standard library Python, Savings → repair/BFD → local search/ILS.
Savings and ILS come from teammates' contributions. This refactoring provides module boundaries,
a common entry point, validation, and reproducible tests.
Discuss HGS and KD-tree as exploration findings; do not add them as submission dependencies.

## Team meeting: Wednesday, 28 October 2026

Goal: choose one candidate version, assign the remaining checks, and agree to freeze the final version on Thursday, 29 October. Allow 30–45 minutes.

Suggested opening:

> v0_1 provides a common generator, solver, checker, and timing command. The local seed=0 run passed all three candidate cases within the 30/60/180-second budgets. Today we need to select the algorithm and inputs, assign acceptance tasks, and agree on a Thursday freeze.

Meeting actions:

- [ ] Confirm v0_1 as the baseline and identify teammates' existing optimizations to compare.
- [ ] Agree on the comparison rule: same inputs, budgets, and seeds; feasibility first, then cost and time. Do not merge unverified changes.
- [ ] Confirm the candidate inputs in `datasets/suite.json` and check for later course instructions on input sizes or submission format.
- [ ] Assign names to the five roles below and agree on handoff times.
- [ ] Confirm the submission platform, deadline, and required files.
- [ ] Agree on one candidate version by Wednesday evening and a final freeze on Thursday afternoon.

Keep HGS and KD-tree as brief exploration findings. Pause new algorithm directions during acceptance.

## Proposed responsibilities

Assign roles according to existing contributions; the original algorithm contributors should review their sections.

- **Member 1 — Integration:** Maintain the common entry point, coordinate merges, and track remaining tasks and contributions. Deliver one candidate version and an updated checklist.
  - Files: `cli.py`, `__main__.py`, `__init__.py`, `instance.py`, `README.md`, `PLAN.md`, and `SUBMISSION.md`.
  - Coordinate changes to shared interfaces and `solve()` in `solver.py`.

- **Member 2 — Construction:** Review Savings and repair/BFD, including cases where route count exceeds K. Complete the construction review and necessary fixes.
  - File: `solver.py`, construction functions only: `build_initial_solution()`, `savings()`, `best_fit_decreasing()`, `nearest_neighbor_order()`, `best_insert_position()`, and `repair_routes()`.
  - Finish and hand off the file before Member 3 starts editing.

- **Member 3 — Improvement:** Review local search/ILS and compare existing optimizations. Recommend which changes to include, supported by tests.
  - File: `solver.py`, improvement sections only: `Solution`, `local_search()`, `try_moves()`, `ruin()`, and `recreate()`.
  - Review the ILS loop in `solve()` with Member 1. Start editing after Member 2's handoff.

- **Member 4 — Testing:** Run multiple seeds, additional inputs, and target VM time/memory checks. Provide acceptance conclusions and reproducible failure cases.
  - Files: `benchmark.py`, `check.py`, and `tests/`.
  - Send solver or generator fixes to their owners instead of directly editing those files.

- **Member 5 — Delivery:** Check generator inputs, seeds, and course requirements. Independently run and package the code. Deliver a runnable submission archive and confirm submission.
  - Files: `generator.py`, `datasets/`, and `examples/`, including their manifests.
  - Confirm input changes with Member 4 before testing. Send documentation updates to Member 1.

All paths are relative to `v0_1/`.

- Only one person edits `solver.py` at a time: Member 2 first, then Member 3, then Member 1 integrates.
- For changes outside your assigned files or sections, arrange a handoff with the owner first.
- Keep input/output formats, CLI options, and the `solve()` signature fixed unless the team agrees on a change.
- Do not change code, inputs, or budgets during an acceptance test round.

## Schedule

- **Wednesday, 28 October:** Agree on the algorithm, inputs, and owners; select one candidate version.
- **Thursday, 29 October:** Complete tests, fix blocking issues, and freeze the final version. Keep any unavailable VM checks pending.
- **Before the submission deadline:** Verify the package and submit. After the freeze, only fix correctness, environment, or submission issues.

## Acceptance and packaging

The candidate inputs total about 5.3 MB and include matrices, generation commands, seeds, and hashes.
100 / 300 / 1000?? are customer counts, not official size boundaries.
The corresponding matrices have 101 / 301 / 1001 nodes.

After confirming the version, run:

```powershell
python -B -m v0_1 test
python -B -m v0_1 bench --suite v0_1/datasets/suite.json --seeds 0
python -B -m v0_1 bench --suite v0_1/datasets/suite.json --seeds 0 1 2
```

The second command runs one acceptance round; the third checks variation across seeds.
bench saves no reports or solution files by default.
For course or other teams' inputs, use `bench input.txt --time 60`, adjusting the budget for the applicable size category.

- [x] Run the 21 tests for core functions and timing tools.
- [x] Pass feasibility and timing checks on all three candidate inputs with a 2-second budget each.
- [x] Check the timeout termination path.
- [ ] Confirm the final code and candidate inputs with the team.
- [ ] Complete final 30 / 60 / 180-second tests, checking capacity, coverage, vehicle count, cost, and time.
- [ ] Check the environment and memory on the target VM; the current runner neither measures peak memory nor enforces a 16 GB limit.
- [ ] Copy `v0_1/` to a clean directory and run the commands from its parent directory, confirming no dependency on old folders or third-party packages.
- [ ] Package the source, generator, actual inputs, and generation commands/seeds as required by the course; exclude virtual environments and caches.
- [ ] Confirm the submission platform, deadline, and member contributions; inspect the archive before submitting.

Freeze the version after final acceptance tests. Limit later changes to correctness or submission fixes.
Do not add new algorithms, frameworks, or large experiments at this stage.
