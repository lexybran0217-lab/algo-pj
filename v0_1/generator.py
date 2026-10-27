import math
import random

from .instance import Instance


def packing_count(demands, capacity):
    loads = []
    for demand in sorted(demands, reverse=True):
        fits = [i for i, load in enumerate(loads) if load + demand <= capacity]
        if fits:
            i = max(fits, key=loads.__getitem__)
            loads[i] += demand
        else:
            loads.append(demand)
    return len(loads)


def generate_instance(n, seed=0, layout='uniform', capacity=100, slack=1):
    if type(n) is not int or n < 1:
        raise ValueError('n must be a positive integer')
    if type(capacity) is not int or capacity < 1 or type(slack) is not int or slack < 0:
        raise ValueError('capacity must be a positive integer; slack must be nonnegative')
    if layout not in ('uniform', 'cluster', 'mixed'):
        raise ValueError('unknown layout')
    rng = random.Random(seed)
    points = [(50.0, 50.0)]
    centers = [(rng.uniform(10, 90), rng.uniform(10, 90)) for _ in range(max(2, n // 40))]
    for _ in range(n):
        mode = layout
        if mode == 'mixed':
            mode = rng.choice(('uniform', 'cluster'))
        if mode == 'uniform':
            point = (rng.uniform(0, 100), rng.uniform(0, 100))
        else:
            x, y = rng.choice(centers)
            point = (min(100, max(0, rng.gauss(x, 6))), min(100, max(0, rng.gauss(y, 6))))
        points.append(point)
    demands = [0] + [rng.randint(1, max(1, int(capacity * 0.3))) for _ in range(n)]
    vehicles = packing_count(demands[1:], capacity) + slack
    distances = [[round(math.dist(a, b), 1) for b in points] for a in points]
    return Instance(demands, distances, capacity, vehicles)
