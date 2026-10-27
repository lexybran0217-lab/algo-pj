# CVRP v0.1.0

Python 3.13, standard library only. Adapted from the existing B version for team review and testing.

Run from the repository root:

```powershell
python -m v0_1 test
python -m v0_1 generate --n 20 --seed 7 --layout mixed --out input_v01.txt
python -m v0_1 solve input_v01.txt --time 5 --seed 0 --out solution_v01.txt --verbose
python -m v0_1 check input_v01.txt solution_v01.txt
```

If `python` is unavailable on this machine, use the existing interpreter:

```powershell
& .\contribution\.venv\Scripts\python.exe -m v0_1 test
```

| File | Purpose |
|---|---|
| `instance.py` | Instance data, input/output, exact nearest neighbors |
| `solver.py` | Savings → repair/BFD → local search/ILS |
| `generator.py` | Seeded matrices; one BFD pass determines a feasible vehicle count |
| `check.py` | Customer coverage, capacity, vehicle count, and cost checks |
| `cli.py` | solve / generate / check / test / bench |
| `benchmark.py` | Separate process timing, timeout handling, and result checks |
| `datasets/` | Three candidate inputs, generation commands, seeds, and hashes |
| `tests/` | Format, solver, generator, failure cases, and CLI tests |
| `examples/` | Small inputs, solutions, generation commands, and hashes |

An input has N nodes including the depot, with an N×N distance matrix.
The generator's `--n` counts customers, so N = n+1.
Inputs are read as text regardless of file extension. Output starts with the cost,
followed by routes in the form `0 ... 0`.

Exit codes: solve returns 0 on success and 2 for invalid input or no feasible solution;
check returns 1 for an invalid solution.
The search uses 92% of the budget; the CLI timer includes imports and input reading.
This does not guarantee completion within the time limit.

The same generator seed and parameters reproduce the same input.
K is a feasible packing count, not necessarily the minimum.
The solver stops by time, so routes can differ across machines or system loads even with the same seed.

This package does not depend on KD-tree, HGS, the old ALNS, or exploration code.
The old entry points and experiments remain elsewhere in the repository.
Final acceptance testing is pending; global optimality is not claimed.

Run timing tests from the repository root:

```powershell
# Smoke test: 2 seconds per case, not formal acceptance
python -B -m v0_1 bench --suite v0_1/datasets/suite.json --time 2
# Formal budgets: 30 / 60 / 180 seconds; 4.5 minutes total for one seed
python -B -m v0_1 bench --suite v0_1/datasets/suite.json --seeds 0
# Multiple seeds; 13.5 minutes total budget
python -B -m v0_1 bench --suite v0_1/datasets/suite.json --seeds 0 1 2
# Test another team's text input
python -B -m v0_1 bench path/to/input.txt --time 60 --seeds 0
```

Cases run serially. Timing includes child process startup, input reading, solving, and output.
The parent checks each solution afterward; that check is outside the timer.
Results go to the terminal only. No reports or solution files are saved.
At 1.5L, the runner initiates process tree termination; cleanup can take additional time.

Statuses: `OK` means feasible and within L; `OVERTIME` means feasible but over L;
`INVALID` means the output failed validation; `ERROR` means the solver process failed;
`TIMEOUT` means the termination threshold was reached.
bench returns 0 if all cases are OK, 1 otherwise, 2 for invalid input, and 130 on interruption.

The candidate cases have 100 / 300 / 1000 customers.
**These are proposed team sizes, not official size boundaries.**
Generation parameters and seeds are in `datasets/suite.json`.
Edit that manifest to change inputs or budgets.
The runner does not measure peak memory; acceptance on the 16 GB VM remains separate.
`verification.json` is an earlier baseline snapshot; use `python -B -m v0_1 test` for current checks.
See [SUBMISSION.md](SUBMISSION.md) for remaining submission tasks.
