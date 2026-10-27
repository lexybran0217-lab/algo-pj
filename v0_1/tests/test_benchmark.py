import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from v0_1.benchmark import load_cases, result_status, run_case, run_benchmark

ROOT = Path(__file__).resolve().parents[2]
SAMPLE = ROOT / 'v0_1/examples/sample.txt'


class BenchmarkTests(unittest.TestCase):
    def test_status_keeps_feasibility_and_time_separate(self):
        self.assertEqual(result_status(0, False, True, 30, 30), 'OK')
        self.assertEqual(result_status(0, False, True, 30.01, 30), 'OVERTIME')
        self.assertEqual(result_status(0, False, False, 1, 30), 'INVALID')
        self.assertEqual(result_status(2, False, False, 1, 30), 'ERROR')
        self.assertEqual(result_status(-9, True, False, 46, 30), 'TIMEOUT')

    def test_real_child_solution_is_checked_against_original_matrix(self):
        case = {'name': 'sample', 'input': SAMPLE, 'limit_s': 2.0}
        result = run_case(case, seed=0)
        self.assertTrue(result['feasible'], result)
        self.assertAlmostEqual(result['cost'], 21.8)
        self.assertEqual(result['routes'], 2)
        self.assertEqual(result['status'], 'OK' if result['wall_s'] <= 2 else 'OVERTIME')

    def test_suite_resolves_relative_inputs_and_budget_override(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            (folder / 'instance.data').write_bytes(SAMPLE.read_bytes())
            suite = folder / 'suite.json'
            suite.write_text(json.dumps({'cases': [
                {'name': 'small', 'input': 'instance.data', 'limit_s': 30}]}))
            cases = load_cases([], suite, None)
            self.assertEqual(cases[0]['input'], folder / 'instance.data')
            self.assertEqual(cases[0]['limit_s'], 30)
            self.assertEqual(load_cases([], suite, 2)[0]['limit_s'], 2)

    def test_timeout_stops_child_and_is_not_a_valid_solution(self):
        with patch('v0_1.benchmark.subprocess.Popen') as popen, \
             patch('v0_1.benchmark.stop_process') as stop:
            child = popen.return_value
            child.communicate.side_effect = [subprocess.TimeoutExpired('solve', 3), ('', '')]
            child.returncode = -9
            result = run_case({'name': 'sample', 'input': SAMPLE, 'limit_s': 2}, 0)
        stop.assert_called_once_with(child)
        self.assertTrue(result['timed_out'])
        self.assertFalse(result['feasible'])
        self.assertEqual(result['status'], 'TIMEOUT')

    def test_cases_and_seeds_run_serially_in_order(self):
        cases = [{'name': 'a', 'limit_s': 2}, {'name': 'b', 'limit_s': 2}]
        with patch('v0_1.benchmark.run_case', return_value={'status': 'OK'}) as run:
            results = run_benchmark(cases, [0, 1])
        self.assertEqual(len(results), 4)
        self.assertEqual(run.call_args_list, [
            unittest.mock.call(cases[0], 0), unittest.mock.call(cases[0], 1),
            unittest.mock.call(cases[1], 0), unittest.mock.call(cases[1], 1)])

    def test_cli_prints_results_without_writing_reports(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            source = folder / 'instance.data'
            source.write_bytes(SAMPLE.read_bytes())
            before = set(folder.iterdir())
            result = subprocess.run([sys.executable, '-B', '-m', 'v0_1', 'bench',
                str(source), '--time', '2'], cwd=ROOT, capture_output=True,
                text=True, timeout=15)
            self.assertIn(result.returncode, (0, 1), result.stderr)
            self.assertIn('21.8', result.stdout)
            self.assertIn('instance', result.stdout)
            self.assertEqual(set(folder.iterdir()), before)

    def test_bad_suite_shapes_raise_input_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            suite = Path(directory) / 'suite.json'
            for data in ({}, [], {'cases': [{}]}, {'cases': 'wrong'},
                         {'cases': [{'name': 7, 'input': 'a', 'limit_s': 30}]}):
                suite.write_text(json.dumps(data))
                with self.subTest(data=data), self.assertRaises(ValueError):
                    load_cases([], suite)

    def test_interrupt_stops_and_reaps_child(self):
        with patch('v0_1.benchmark.subprocess.Popen') as popen, \
             patch('v0_1.benchmark.stop_process') as stop:
            child = popen.return_value
            child.communicate.side_effect = KeyboardInterrupt
            with self.assertRaises(KeyboardInterrupt):
                run_case({'name': 'sample', 'input': SAMPLE, 'limit_s': 2}, 0)
        stop.assert_called_once_with(child)
        child.wait.assert_called_once_with(timeout=5)


if __name__ == '__main__':
    unittest.main()
