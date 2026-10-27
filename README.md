# CVRP v0.1

A standard-library Python solver, generator, checker, and timing runner for the group project.
The core Savings and ILS algorithms are based on teammates' contributions; v0_1 organizes the code and testing entry points.

Requires Python 3.13. From this repository root:

```sh
python -B -m v0_1 test
python -B -m v0_1 bench --suite v0_1/datasets/suite.json --time 2
```

The second command is a short smoke test. For the 30/60/180-second budgets:

```sh
python -B -m v0_1 bench --suite v0_1/datasets/suite.json --seeds 0
```

Results print to the terminal; no benchmark reports or solution files are saved.

- [Usage and file structure](v0_1/README.md)
- [Meeting, responsibilities, and submission checklist](v0_1/SUBMISSION.md)

This is a candidate version for team review, not a final submission.
