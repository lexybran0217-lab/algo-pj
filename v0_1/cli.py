import argparse
import sys
from pathlib import Path

from . import __version__
from .check import check_solution
from .generator import generate_instance
from .instance import parse_instance, format_instance, format_solution
from .solver import solve


def main(argv=None, started_at=None):
    parser = argparse.ArgumentParser(prog='python -m v0_1')
    parser.add_argument('--version', action='version', version=__version__)
    commands = parser.add_subparsers(dest='command', required=True)
    solver = commands.add_parser('solve')
    solver.add_argument('instance', type=Path)      #input file: input.txt
    solver.add_argument('--time', type=float, default=30)
    solver.add_argument('--seed', type=int, default=0)
    solver.add_argument('--out', type=Path)
    solver.add_argument('--verbose', action='store_true')
    generator = commands.add_parser('generate')
    generator.add_argument('--n', type=int, required=True, help='number of customers')
    generator.add_argument('--seed', type=int, default=0)
    generator.add_argument('--layout', choices=['uniform', 'cluster', 'mixed'], default='uniform')
    generator.add_argument('--capacity', type=int, default=100)
    generator.add_argument('--slack', type=int, default=1)
    generator.add_argument('--out', type=Path)
    checker = commands.add_parser('check')
    checker.add_argument('instance', type=Path)
    checker.add_argument('solution', type=Path)
    commands.add_parser('test')
    benchmark = commands.add_parser('bench')
    benchmark.add_argument('instances', nargs='*', type=Path)
    benchmark.add_argument('--suite', type=Path)
    benchmark.add_argument('--time', type=float)
    benchmark.add_argument('--seeds', nargs='+', type=int, default=[0])
    args = parser.parse_args(argv)  #real input

    try:
        if args.command == 'bench':
            from .benchmark import load_cases, print_result, run_benchmark
            cases = load_cases(args.instances, args.suite, args.time)
            print('Serial full-process timing; validation is outside the timer.')
            print('Hard stop: 1.5L. No result files are written.')
            results = run_benchmark(cases, args.seeds, print_result)
            passed = sum(row['status'] == 'OK' for row in results)
            print(f'PASS {passed}/{len(results)}')
            return 0 if passed == len(results) else 1
        if args.command == 'test':
            import unittest
            folder = Path(__file__).resolve().parent / 'tests'
            suite = unittest.defaultTestLoader.discover(str(folder), top_level_dir=str(folder.parents[1]))
            result = unittest.TextTestRunner(verbosity=2).run(suite)
            return 0 if result.wasSuccessful() else 1
        if args.command == 'generate':
            problem = generate_instance(args.n, args.seed, args.layout, args.capacity, args.slack)
            text = format_instance(problem)
            if args.out:
                args.out.write_text(text, encoding='utf-8', newline='\n')
            else:
                sys.stdout.write(text)
            print(f'generated n={args.n} seed={args.seed} vehicles={problem.vehicles}', file=sys.stderr)
            return 0
        problem = parse_instance(args.instance.read_text(encoding='utf-8-sig'))
        if args.command == 'check':
            valid, errors, cost = check_solution(problem, args.solution.read_text(encoding='utf-8-sig'))
            if valid:
                print(f'VALID cost={cost}')
            else:
                print('INVALID: ' + '; '.join(errors))
            return 0 if valid else 1
        log = (lambda line: print(line, file=sys.stderr)) if args.verbose else None
        routes = solve(problem, args.time, args.seed, log, started_at)
        if routes is None:
            print('no feasible solution found within the search budget', file=sys.stderr)
            return 2
        text = format_solution(problem, routes)
        valid, errors, _ = check_solution(problem, text)
        if not valid:
            print('solution check failed: ' + '; '.join(errors), file=sys.stderr)
            return 2
        if args.out:
            args.out.write_text(text, encoding='utf-8', newline='\n')
        else:
            sys.stdout.write(text)
        return 0
    except (OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print('interrupted', file=sys.stderr)
        return 130
