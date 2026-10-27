import math


def check_solution(problem, text):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return False, ['empty solution'], None
    try:
        reported = float(lines[0])
        routes = [list(map(int, line.split())) for line in lines[1:]]
    except ValueError:
        return False, ['invalid solution number'], None
    if not math.isfinite(reported):
        return False, ['cost must be finite'], None
    errors = []
    if len(routes) > problem.vehicles:
        errors.append('too many routes')
    seen = [0] * (problem.n + 1)
    total = 0.0
    for route in routes:
        if len(route) < 3 or route[0] != 0 or route[-1] != 0:
            errors.append('route must start and end at depot')
            continue
        if any(not 1 <= c <= problem.n for c in route[1:-1]):
            errors.append('invalid customer')
            continue
        load = 0.0
        for c in route[1:-1]:
            seen[c] += 1
            load += problem.demands[c]
        if load > problem.capacity + 1e-9:
            errors.append('capacity exceeded')
        total += sum(problem.distances[a][b] for a, b in zip(route, route[1:]))
    if any(count != 1 for count in seen[1:]):
        errors.append('customer missing or repeated')
    if not math.isclose(total, reported, rel_tol=1e-9, abs_tol=1e-6):
        errors.append('reported cost does not match matrix')
    return not errors, errors, total
