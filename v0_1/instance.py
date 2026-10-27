import heapq
import math

EPS = 1e-9


class Instance:
    def __init__(self, demands, distances, capacity, vehicles):
        size = len(demands)
        if not size or len(distances) != size or any(len(row) != size for row in distances):
            raise ValueError('distance matrix size does not match demands')
        if not math.isfinite(capacity) or capacity <= 0:
            raise ValueError('capacity must be positive and finite')
        if type(vehicles) is not int or vehicles < 0:
            raise ValueError('vehicles must be a nonnegative integer')
        if any(not math.isfinite(d) or d < 0 for d in demands) or demands[0] != 0:
            raise ValueError('demands must be nonnegative and depot demand must be zero')
        for i, row in enumerate(distances):
            if any(not math.isfinite(d) or d < 0 for d in row):
                raise ValueError('distances must be nonnegative and finite')
            if abs(row[i]) > EPS:
                raise ValueError('distance matrix diagonal must be zero')
            if any(abs(row[j] - distances[j][i]) > EPS for j in range(i)):
                raise ValueError('distance matrix must be symmetric')
        self.demands = demands
        self.distances = distances
        self.capacity = capacity
        self.vehicles = vehicles
        self.n = size - 1
        self.symmetric = True
        self.neighbors = [[] for _ in demands]
        self.neighbor_count = 0

    def build_neighbors(self, count=20):
        count = min(count, max(0, self.n - 1))
        self.neighbor_count = count
        for i, row in enumerate(self.distances):
            candidates = (j for j in range(1, self.n + 1) if j != i)
            self.neighbors[i] = heapq.nsmallest(count, candidates, key=row.__getitem__)

    def route_cost(self, route):
        if not route:
            return 0.0
        D = self.distances
        return D[0][route[0]] + sum(D[a][b] for a, b in zip(route, route[1:])) + D[route[-1]][0]

    def route_load(self, route):
        return sum(self.demands[c] for c in route)

    def verify_routes(self, routes):
        if sum(bool(route) for route in routes) > self.vehicles:
            return False, 'too many routes'
        seen = [0] * (self.n + 1)
        for route in routes:
            if any(type(c) is not int or not 1 <= c <= self.n for c in route):
                return False, 'invalid customer'
            if self.route_load(route) > self.capacity + EPS:
                return False, 'capacity exceeded'
            for c in route:
                seen[c] += 1
        if any(count != 1 for count in seen[1:]):
            return False, 'customer missing or repeated'
        return True, 'ok'


def parse_instance(text):
    rows = []
    capacity = vehicles = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        key, separator, value = line.partition(':')
        if separator and key.lower() == 'capacity':
            if capacity is not None:
                raise ValueError('duplicate capacity')
            capacity = float(value)
        elif separator and key.lower() == 'vehicles':
            if vehicles is not None:
                raise ValueError('duplicate vehicles')
            vehicles = int(value)
        else:
            rows.append([float(token) for token in line.split()])
    if not rows or capacity is None or vehicles is None:
        raise ValueError('expected demands, matrix, Capacity and Vehicles')
    if len(rows) != len(rows[0]) + 1:
        raise ValueError('unexpected number of matrix rows')
    return Instance(rows[0], rows[1:], capacity, vehicles)


def number(value):
    return str(int(value)) if float(value).is_integer() else repr(float(value))


def format_instance(problem):
    lines = [' '.join(number(d) for d in problem.demands)]
    lines += [' '.join(number(d) for d in row) for row in problem.distances]
    lines += [f'Capacity: {number(problem.capacity)}', f'Vehicles: {problem.vehicles}']
    return '\n'.join(lines) + '\n'


def format_solution(problem, routes):
    cost = sum(problem.route_cost(route) for route in routes)
    lines = [number(cost)]
    lines += ['0 ' + ' '.join(map(str, route)) + ' 0' for route in routes if route]
    return '\n'.join(lines) + '\n'
