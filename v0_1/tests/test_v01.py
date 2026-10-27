import math
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
from pathlib import Path

from v0_1.instance import parse_instance, format_instance, format_solution
from v0_1.generator import generate_instance
from v0_1.check import check_solution
from v0_1.solver import solve, savings, build_initial_solution, Solution

ROOT = Path(__file__).resolve().parents[2]
SAMPLE = '''0 2 2 3
0 2.5 5.6 6
2.5 0 3.9 6.5
5.6 3.9 0 5.2
6 6.5 5.2 0
Capacity: 5
Vehicles: 2
'''


class VersionTests(unittest.TestCase):
    def test_instance_round_trip_preserves_matrix(self):
        problem = parse_instance(SAMPLE)
        other = parse_instance(format_instance(problem))
        self.assertEqual(other.demands, problem.demands)
        self.assertEqual(other.distances, problem.distances)
        self.assertEqual(other.vehicles, 2)

    def test_bad_input_is_rejected(self):
        invalid = [SAMPLE.replace('Vehicles: 2', 'Vehicles: 1.5'),
                   SAMPLE.replace('2.5 0 3.9 6.5', '9 0 3.9 6.5'),
                   SAMPLE.replace('0 2 2 3', '1 2 2 3'),
                   SAMPLE.replace('0 2.5 5.6 6', '0 nan 5.6 6'),
                   SAMPLE + '0 0 0 0\n']
        for text in invalid:
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_instance(text)

    def test_generator_seed_and_feasibility(self):
        first = generate_instance(20, seed=7, layout='mixed')
        second = generate_instance(20, seed=7, layout='mixed')
        self.assertEqual(format_instance(first), format_instance(second))
        self.assertEqual(len(first.demands), 21)
        routes = solve(first, time_limit=0.15, seed=0)
        self.assertIsNotNone(routes)
        self.assertTrue(check_solution(first, format_solution(first, routes))[0])

    def test_solver_can_be_called_twice(self):
        problem = parse_instance(SAMPLE)
        for _ in range(2):
            routes = solve(problem, time_limit=0.03, seed=0)
            self.assertIsNotNone(routes)
            valid, errors, cost = check_solution(problem, format_solution(problem, routes))
            self.assertTrue(valid, errors)
            self.assertAlmostEqual(cost, 21.8)

    def test_savings_32_routes_are_repaired_to_31(self):
        fixture = Path(__file__).with_name('fixtures') / 'instance_200.txt'
        problem = parse_instance(fixture.read_text())
        problem.build_neighbors()
        self.assertEqual(len(savings(problem)), 32)
        import random
        routes = build_initial_solution(problem, time.perf_counter() + 1, random.Random(0))
        self.assertIsNotNone(routes)
        valid, errors, _ = check_solution(problem, format_solution(problem, routes))
        self.assertTrue(valid, errors)
        self.assertEqual(len(routes), 31)

    def test_nonmetric_matrix_uses_original_distances(self):
        problem = parse_instance('''0 1 1 1
0 1 1 50
1 0 100 1
1 100 0 1
50 1 1 0
Capacity: 3
Vehicles: 1
''')
        routes = solve(problem, time_limit=0.05, seed=0)
        self.assertIsNotNone(routes)
        valid, errors, cost = check_solution(problem, format_solution(problem, routes))
        self.assertTrue(valid, errors)
        self.assertEqual(cost, 4)

    def test_checker_rejects_bad_routes_and_costs(self):
        problem = parse_instance(SAMPLE)
        for solution in ('', 'nan\n0 1 0\n0 2 3 0\n',
                         '21.8\n0 1 0\n0 2 99 0\n',
                         '0\n0 1 0\n0 2 3 0\n',
                         '21.8\n0 1 0\n0 1 3 0\n',
                         '21.8\n0 1 2 3 0\n'):
            with self.subTest(solution=solution):
                self.assertFalse(check_solution(problem, solution)[0])

    def test_infeasible_and_expired_search_return_no_solution(self):
        impossible = parse_instance(SAMPLE.replace('Vehicles: 2', 'Vehicles: 1'))
        self.assertIsNone(solve(impossible, time_limit=0.1))
        self.assertIsNone(solve(parse_instance(SAMPLE), time_limit=1,
                                started_at=time.perf_counter() - 2))
        for limit in (0, -1, math.inf):
            with self.assertRaises(ValueError):
                solve(parse_instance(SAMPLE), time_limit=limit)

    def test_cli_generate_solve_check_without_site_packages(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            instance = folder / 'input.txt'
            solution = folder / 'solution.txt'
            commands = [['generate', '--n', '20', '--seed', '7', '--out', str(instance)],
                        ['solve', str(instance), '--time', '2', '--seed', '0', '--out', str(solution)],
                        ['check', str(instance), str(solution)]]
            for args in commands:
                result = subprocess.run([sys.executable, '-S', '-B', '-m', 'v0_1', *args],
                    cwd=ROOT, capture_output=True, text=True, timeout=15)
                self.assertEqual(result.returncode, 0, result.stderr)
            problem = parse_instance(instance.read_text())
            self.assertTrue(check_solution(problem, solution.read_text())[0])

    def test_cli_failure_emits_no_solution(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'input.txt'
            target = Path(directory) / 'solution.txt'
            source.write_text(SAMPLE.replace('Vehicles: 2', 'Vehicles: 1'))
            result = subprocess.run([sys.executable, '-S', '-B', '-m', 'v0_1',
                'solve', str(source), '--time', '0.1', '--out', str(target)],
                cwd=ROOT, capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout, '')
            self.assertFalse(target.exists())

    def test_zero_cost_and_depot_only_instances(self):
        zero = parse_instance('0 1 1\n0 0 0\n0 0 0\n0 0 0\nCapacity: 2\nVehicles: 1\n')
        routes = solve(zero, time_limit=0.05)
        self.assertIsNotNone(routes)
        self.assertEqual(check_solution(zero, format_solution(zero, routes))[2], 0)
        depot = parse_instance('0\n0\nCapacity: 1\nVehicles: 0\n')
        self.assertEqual(solve(depot, time_limit=0.05), [])

    def test_repair_failure_leaves_time_for_packing(self):
        import random
        problem = parse_instance(SAMPLE)
        deadline = time.perf_counter() + 1
        with patch('v0_1.solver.savings', return_value=[[1], [2], [3]]), \
             patch('v0_1.solver.repair_routes', return_value=None) as repair:
            routes = build_initial_solution(problem, deadline, random.Random(0))
        self.assertTrue(problem.verify_routes(routes)[0])
        self.assertLess(repair.call_args.args[2], deadline)

    def test_solution_rollback_restores_routes_cost_and_positions(self):
        problem = parse_instance(SAMPLE)
        state = Solution(problem, [[1], [2, 3]])
        original, cost = state.snapshot(), state.cost
        state.begin()
        state.set_route(0, [1, 2])
        state.set_route(1, [3])
        state.rollback()
        self.assertEqual(state.snapshot(), original)
        self.assertEqual(state.cost, cost)
        for r, route in enumerate(state.routes):
            for position, customer in enumerate(route):
                self.assertEqual((state.route_of[customer], state.position[customer]), (r, position))


if __name__ == '__main__':
    unittest.main()
