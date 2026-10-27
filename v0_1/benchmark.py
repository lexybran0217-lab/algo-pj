import json
import math
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from .check import check_solution
from .instance import parse_instance


def load_cases(inputs, suite=None, time_limit=None):
    if inputs and suite:
        raise ValueError('use input files or --suite, not both')
    if suite:
        data = json.loads(suite.read_text(encoding='utf-8-sig'))
        if not isinstance(data, dict) or not isinstance(data.get('cases'), list):
            raise ValueError('suite must contain a cases list')
        cases = []
        for item in data['cases']:
            if (not isinstance(item, dict)
                    or not isinstance(item.get('name'), str) or not item['name']
                    or not isinstance(item.get('input'), str) or not item['input']
                    or type(item.get('limit_s')) not in (int, float)):
                raise ValueError('each case needs name, input and numeric limit_s')
            cases.append(dict(name=item['name'], input=(suite.parent / item['input']).resolve(),
                              limit_s=item['limit_s']))
    else:
        cases = [dict(name=path.stem, input=path.resolve(), limit_s=30) for path in inputs]
    if not cases:
        raise ValueError('provide input files or --suite')
    for case in cases:
        limit = time_limit if time_limit is not None else case['limit_s']
        if type(limit) not in (int, float) or not math.isfinite(limit) or limit <= 0:
            raise ValueError('time limit must be positive and finite')
        case['limit_s'] = float(limit)
        if not case['input'].is_file():
            raise ValueError(f'input file not found: {case["input"]}')
    return cases


def result_status(returncode, timed_out, feasible, wall_s, limit_s):
    if timed_out:
        return 'TIMEOUT'
    if returncode != 0:
        return 'ERROR'
    if not feasible:
        return 'INVALID'
    return 'OK' if wall_s <= limit_s else 'OVERTIME'


def stop_process(process):
    if process.poll() is not None:
        return
    if os.name == 'nt':
        # Kill the interpreter launcher and its Python child, if present.
        try:
            subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
        except (OSError, subprocess.SubprocessError):
            pass
        if process.poll() is None:
            process.kill()
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


def run_case(case, seed):
    limit = case['limit_s']
    source = case['input']
    command = [sys.executable, '-B', '-m', 'v0_1', 'solve', str(source),
               '--time', str(limit), '--seed', str(seed)]
    options = {'creationflags': subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == 'nt' else {'start_new_session': True}
    started = time.perf_counter()
    process = subprocess.Popen(command, cwd=Path(__file__).resolve().parents[1],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               text=True, encoding='utf-8', **options)
    timed_out, finished = False, False
    try:
        try:
            output, error = process.communicate(timeout=limit * 1.5)
        except subprocess.TimeoutExpired:
            timed_out = True
            stop_process(process)
            try:
                output, error = process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.stdout.close()
                process.stderr.close()
                process.wait(timeout=5)
                output, error = '', 'process cleanup exceeded five seconds'
        finished = True
    finally:
        if not finished:
            stop_process(process)
            try:
                process.wait(timeout=5)
            except subprocess.SubprocessError:
                pass
    wall = time.perf_counter() - started
    feasible, errors, cost = False, [], None
    routes = None
    if not timed_out and process.returncode == 0:
        try:
            problem = parse_instance(source.read_text(encoding='utf-8-sig'))
            feasible, errors, cost = check_solution(problem, output)
            if feasible:
                routes = len(output.strip().splitlines()) - 1
        except (OSError, ValueError) as exc:
            errors = [str(exc)]
    if error.strip():
        errors.append(error.strip()[:300])
    return dict(case=case['name'], input=str(source), seed=seed, limit_s=limit,
                wall_s=wall, feasible=feasible, routes=routes,
                cost=cost if feasible else None, returncode=process.returncode,
                timed_out=timed_out, errors=errors,
                status=result_status(process.returncode, timed_out, feasible, wall, limit))


def print_result(row):
    cost = '-' if row['cost'] is None else f"{row['cost']:.6f}"
    print(f"{row['case']} seed={row['seed']} L={row['limit_s']:g}s "
          f"wall={row['wall_s']:.3f}s feasible={row['feasible']} "
          f"routes={row['routes']} cost={cost} {row['status']}", flush=True)
    if row['errors']:
        print('  ' + '; '.join(row['errors']), flush=True)


def run_benchmark(cases, seeds, on_result=None):
    results = []
    for case in cases:
        for seed in seeds:
            print(f"RUN {case['name']} seed={seed} L={case['limit_s']:g}s", flush=True)
            row = run_case(case, seed)
            results.append(row)
            if on_result:
                on_result(row)
    return results
