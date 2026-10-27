import math
import random
import time

from .instance import EPS

INF = float("inf")


def now():
    return time.perf_counter()


def build_initial_solution(problem, deadline, rng, log=None):
    routes = savings(problem)
    if log:
        log(f'savings routes={len(routes)}')
    if problem.verify_routes(routes)[0]:
        return routes
    if now() >= deadline:
        return None
    # Keep time for a packing fallback if geographic repair stalls.
    repair_deadline = now() + (deadline - now()) / 2
    routes = repair_routes(problem, routes, repair_deadline, rng)
    order = sorted(range(1, problem.n + 1), key=lambda c: -problem.demands[c])
    tries = 0
    while routes is None and now() < deadline:
        tries += 1
        if tries > 1:
            noise = min(0.5, 0.05 * tries)
            order = sorted(order, key=lambda c: -problem.demands[c] * (1 + rng.uniform(-noise, noise)))
        groups = best_fit_decreasing(problem, order)
        groups = [nearest_neighbor_order(problem, group) for group in groups]
        routes = groups if len(groups) <= problem.vehicles else repair_routes(problem, groups, deadline, rng)
    if routes is None or not problem.verify_routes(routes)[0]:
        return None
    return routes


def solve(problem, time_limit=30.0, seed=0, log=None, started_at=None):
    if not math.isfinite(time_limit) or time_limit <= 0:
        raise ValueError('time limit must be positive and finite')
    if problem.n == 0:
        return []
    if max(problem.demands) > problem.capacity + EPS:
        return None
    if sum(problem.demands) > problem.vehicles * problem.capacity + EPS:
        return None
    start = now() if started_at is None else started_at
    deadline = start + time_limit * 0.92
    if now() >= deadline:
        return None
    if not problem.neighbor_count:
        problem.build_neighbors()
    if now() >= deadline:
        return None
    rng = random.Random(seed)
    initial = build_initial_solution(problem, deadline, rng, log)
    if initial is None:
        return None
    if log:
        log(f'feasible routes={len(initial)}')
    solution = Solution(problem, initial)
    local_search(solution, range(1, problem.n + 1), deadline, rng)
    best, best_cost = solution.snapshot(), solution.cost
    if best_cost <= EPS:
        return best
    average_edge = best_cost / (problem.n + len(solution.routes))
    initial_temperature, final_temperature = 0.3 * average_edge, 0.003 * average_edge
    search_start = now()
    span = max(deadline - search_start, 1e-6)
    iterations = 0
    while now() < deadline:
        iterations += 1
        progress = (now() - search_start) / span
        temperature = initial_temperature * (final_temperature / initial_temperature) ** progress
        previous_cost = solution.cost
        solution.begin()
        removed = ruin(solution, rng)
        if not recreate(solution, removed, rng):
            solution.rollback()
            continue
        active = set(removed)
        for customer in removed:
            active.add(solution.predecessor(customer))
            active.add(solution.successor(customer))
        active.discard(0)
        local_search(solution, active, deadline, rng)
        if solution.cost < previous_cost - temperature * math.log(1 - rng.random() + 1e-300):
            solution.commit()
            if solution.cost < best_cost - EPS:
                best, best_cost = solution.snapshot(), solution.cost
        else:
            solution.rollback()
    if log:
        log(f'ils iterations={iterations} cost={best_cost:.6f}')
    return best if problem.verify_routes(best)[0] else initial


def savings(problem):
    n, distances, demands, capacity = problem.n, problem.distances, problem.demands, problem.capacity
    d0 = distances[0]
    pairs = []
    if n <= 800:
        for i in range(1, n + 1):
            Di, d0i = distances[i], d0[i]
            for j in range(i + 1, n + 1):
                s = d0i + d0[j] - Di[j]
                if s > 0:
                    pairs.append((s, i, j))
    else:
        seen = set()
        for i in range(1, n + 1):
            for j in problem.neighbors[i]:
                a, b = (i, j) if i < j else (j, i)
                if (a, b) not in seen:
                    seen.add((a, b))
                    s = d0[a] + d0[b] - distances[a][b]
                    if s > 0:
                        pairs.append((s, a, b))
    pairs.sort(reverse=True)
    route = {i: [i] for i in range(1, n + 1)}
    loads = {i: demands[i] for i in range(1, n + 1)}
    rid = list(range(n + 1))
    for _, i, j in pairs:
        ri, rj = rid[i], rid[j]
        if ri == rj or loads[ri] + loads[rj] > capacity + EPS:
            continue
        Ri, Rj = route[ri], route[rj]
        if Ri[-1] != i:
            if Ri[0] == i:
                Ri.reverse()
            else:
                continue
        if Rj[0] != j:
            if Rj[-1] == j:
                Rj.reverse()
            else:
                continue
        Ri.extend(Rj)
        for c in Rj:
            rid[c] = ri
        loads[ri] += loads[rj]
        del route[rj], loads[rj]
    return list(route.values())


def best_fit_decreasing(problem, order):
    demands, capacity = problem.demands, problem.capacity
    bins, loads = [], []
    for c in order:
        pick, best = -1, INF
        for b in range(len(bins)):
            rem = capacity - loads[b] - demands[c]
            if -EPS <= rem < best:
                pick, best = b, rem
        if pick < 0:
            bins.append([c])
            loads.append(demands[c])
        else:
            bins[pick].append(c)
            loads[pick] += demands[c]
    return bins


def nearest_neighbor_order(problem, group):
    distances = problem.distances
    left, cur, out = set(group), 0, []
    while left:
        nxt = min(left, key=distances[cur].__getitem__)
        out.append(nxt)
        left.remove(nxt)
        cur = nxt
    return out


def best_insert_position(problem, r, c):
    distances = problem.distances
    best, bp, prev = INF, 0, 0
    for t in range(len(r) + 1):
        nxt = r[t] if t < len(r) else 0
        v = distances[prev][c] + distances[c][nxt] - distances[prev][nxt]
        if v < best:
            best, bp = v, t
        prev = nxt
    return best, bp


def repair_routes(problem, routes, deadline, rng):
    demands, capacity, vehicles = problem.demands, problem.capacity, problem.vehicles
    routes = [r[:] for r in routes if r]
    pool = []
    while len(routes) > vehicles:
        k = min(range(len(routes)), key=lambda i: problem.route_load(routes[i]))
        pool.extend(routes.pop(k))
    loads = [problem.route_load(r) for r in routes]
    R = len(routes)
    rid = {}
    for k, r in enumerate(routes):
        for c in r:
            rid[c] = k

    def put(c, b):
        _, position = best_insert_position(problem, routes[b], c)
        routes[b].insert(position, c)
        loads[b] += demands[c]
        rid[c] = b

    def take(c, b):
        routes[b].remove(c)
        loads[b] -= demands[c]

    def near_routes(b):
        s = set()
        for c in routes[b]:
            for j in problem.neighbors[c][:10]:
                k = rid.get(j)
                if k is not None and k != b:
                    s.add(k)
        return s or set(range(R)) - {b}

    def place(u):
        free = [capacity - l for l in loads]
        fit = [b for b in range(R) if free[b] >= demands[u] - EPS]
        if fit:
            put(u, min(fit, key=lambda b: best_insert_position(problem, routes[b], u)[0]))
            pool.remove(u)
            return True
        order = sorted(range(R), key=lambda b: best_insert_position(problem, routes[b], u)[0])[:20]
        for b in order:                                    # (b) move out
            need = demands[u] - free[b]
            for v in sorted(routes[b], key=lambda v: demands[v]):
                if demands[v] < need - EPS:
                    continue
                cs = [c for c in range(R) if c != b and free[c] >= demands[v] - EPS]
                if cs:
                    take(v, b)
                    put(v, min(cs, key=lambda c: best_insert_position(problem, routes[c], v)[0]))
                    put(u, b)
                    pool.remove(u)
                    return True
        best = None                                        # (c) swap with a smaller one
        for b in order:
            need = demands[u] - free[b]
            for v in routes[b]:
                if need - EPS <= demands[v] < demands[u] - EPS:
                    key = (demands[v], rng.random())
                    if best is None or key < best[0]:
                        best = (key, b, v)
        if best is None:
            return False
        _, b, v = best
        take(v, b)
        put(u, b)
        pool.remove(u)
        pool.append(v)
        return True

    def consolidate():                                     # (d) raise sum(free^2) via nearby routes
        free = [capacity - l for l in loads]
        best = (EPS, None)
        for b in range(R):
            fb = free[b]
            for c in near_routes(b):
                fc = free[c]
                for x in routes[b]:
                    dx = demands[x]
                    if dx <= fc + EPS:
                        gain = (fb + dx) ** 2 + (fc - dx) ** 2 - fb * fb - fc * fc
                        if gain > best[0]:
                            best = (gain, ("move", x, b, c))
                    if b < c:
                        for y in routes[c]:
                            dl = dx - demands[y]
                            if dl == 0 or fc - dl < -EPS or fb + dl < -EPS:
                                continue
                            gain = (fb + dl) ** 2 + (fc - dl) ** 2 - fb * fb - fc * fc
                            if gain > best[0]:
                                best = (gain, ("swap", x, b, c, y))
            if now() > deadline:
                break
        mv = best[1]
        if mv is None:
            return False
        if mv[0] == "move":
            _, x, b, c = mv
            take(x, b)
            put(x, c)
        else:
            _, x, b, c, y = mv
            take(x, b)
            take(y, c)
            put(x, c)
            put(y, b)
        return True

    stall = 0
    while pool:
        if now() > deadline:
            return None
        pool.sort(key=lambda c: -demands[c])
        if any(place(u) for u in list(pool)):
            stall = 0
            continue
        if not consolidate():
            return None
        stall += 1
        if stall > 10 * R + 100:
            return None
    return routes


class Solution:

    def __init__(self, problem, routes):
        self.problem = problem
        vehicles = min(problem.vehicles, problem.n)
        routes = [r[:] for r in routes if r]
        assert len(routes) <= vehicles
        self.routes = routes + [[] for _ in range(vehicles - len(routes))]
        self.route_of = [-1] * (problem.n + 1)
        self.position = [0] * (problem.n + 1)
        self.loads = [0.0] * vehicles
        self.route_costs = [0.0] * vehicles
        for r in range(vehicles):
            self._index_route(r)
        self.cost = sum(self.route_costs)
        self.backup = None

    def _index_route(self, r):
        rt = self.routes[r]
        ro, ps, demands = self.route_of, self.position, self.problem.demands
        ld = 0.0
        for i, c in enumerate(rt):
            ro[c] = r
            ps[c] = i
            ld += demands[c]
        self.loads[r] = ld
        self.route_costs[r] = self.problem.route_cost(rt)

    def set_route(self, r, new):
        if self.backup is not None and r not in self.backup:
            self.backup[r] = self.routes[r]
        old = self.route_costs[r]
        self.routes[r] = new
        self._index_route(r)
        self.cost += self.route_costs[r] - old

    def begin(self):
        self.backup = {}
        self.saved_cost = self.cost

    def rollback(self):
        for r, lst in self.backup.items():
            for c in self.routes[r]:
                self.route_of[c] = -1
            self.routes[r] = lst
        for r in self.backup:
            self._index_route(r)
        self.cost = self.saved_cost
        self.backup = None

    def commit(self):
        self.backup = None

    def predecessor(self, c):
        p = self.position[c]
        return self.routes[self.route_of[c]][p - 1] if p > 0 else 0

    def successor(self, c):
        rt = self.routes[self.route_of[c]]
        p = self.position[c]
        return rt[p + 1] if p + 1 < len(rt) else 0

    def snapshot(self):
        return [r[:] for r in self.routes if r]


def local_search(solution, active, deadline, rng, neighbor_limit=12):
    problem = solution.problem
    distances, demands, capacity, symmetric = problem.distances, problem.demands, problem.capacity, problem.symmetric
    queue = list(active)
    rng.shuffle(queue)
    inq = set(queue)
    steps = 0
    while queue:
        steps += 1
        if steps % 64 == 0 and now() > deadline:
            return
        u = queue.pop()
        inq.discard(u)
        if solution.route_of[u] < 0:
            continue
        touched = try_moves(
            solution, u, problem.neighbors[u][:neighbor_limit],
            distances, demands, capacity, symmetric,
        )
        if touched:
            for c in touched:
                if c and c not in inq and solution.route_of[c] >= 0:
                    inq.add(c)
                    queue.append(c)


def try_moves(solution, u, nbrs, distances, demands, capacity, symmetric):
    ru = solution.route_of[u]
    for v in nbrs:
        rv = solution.route_of[v]
        if rv < 0:
            continue
        Ru, Rv = solution.routes[ru], solution.routes[rv]
        pu, pv = solution.position[u], solution.position[v]
        a_u = Ru[pu - 1] if pu > 0 else 0          # pred(u)
        b_u = Ru[pu + 1] if pu + 1 < len(Ru) else 0  # succ(u)
        a_v = Rv[pv - 1] if pv > 0 else 0
        b_v = Rv[pv + 1] if pv + 1 < len(Rv) else 0

        if ru != rv:
            # relocate u next to v (after v, or before v)
            if solution.loads[rv] + demands[u] <= capacity + EPS:
                rem = distances[a_u][u] + distances[u][b_u] - distances[a_u][b_u]
                add_after = distances[v][u] + distances[u][b_v] - distances[v][b_v]
                add_before = distances[a_v][u] + distances[u][v] - distances[a_v][v]
                if add_after <= add_before:
                    if add_after - rem < -1e-9:
                        solution.set_route(ru, Ru[:pu] + Ru[pu + 1:])
                        solution.set_route(rv, Rv[:pv + 1] + [u] + Rv[pv + 1:])
                        return (u, v, a_u, b_u, b_v)
                elif add_before - rem < -1e-9:
                    solution.set_route(ru, Ru[:pu] + Ru[pu + 1:])
                    solution.set_route(rv, Rv[:pv] + [u] + Rv[pv:])
                    return (u, v, a_u, b_u, a_v)
            # swap u and v
            if (solution.loads[ru] - demands[u] + demands[v] <= capacity + EPS
                    and solution.loads[rv] - demands[v] + demands[u] <= capacity + EPS):
                delta = (distances[a_u][v] + distances[v][b_u] - distances[a_u][u] - distances[u][b_u]
                         + distances[a_v][u] + distances[u][b_v] - distances[a_v][v] - distances[v][b_v])
                if delta < -1e-9:
                    nu, nv = Ru[:], Rv[:]
                    nu[pu], nv[pv] = v, u
                    solution.set_route(ru, nu)
                    solution.set_route(rv, nv)
                    return (u, v, a_u, b_u, a_v, b_v)
            # 2-opt*: swap tails  (u->b_v , v->b_u)
            delta = distances[u][b_v] + distances[v][b_u] - distances[u][b_u] - distances[v][b_v]
            if delta < -1e-9:
                lu = sum(demands[c] for c in Ru[:pu + 1])
                lv = sum(demands[c] for c in Rv[:pv + 1])
                if lu + solution.loads[rv] - lv <= capacity + EPS and lv + solution.loads[ru] - lu <= capacity + EPS:
                    solution.set_route(ru, Ru[:pu + 1] + Rv[pv + 1:])
                    solution.set_route(rv, Rv[:pv + 1] + Ru[pu + 1:])
                    return (u, v, b_u, b_v)
            # 2-opt* variant: make u adjacent to v (u->v , b_u->b_v), needs symmetry
            if symmetric:
                delta = distances[u][v] + distances[b_u][b_v] - distances[u][b_u] - distances[v][b_v]
                if delta < -1e-9:
                    lu = sum(demands[c] for c in Ru[:pu + 1])
                    lv = sum(demands[c] for c in Rv[:pv + 1])
                    n1 = lu + lv
                    n2 = solution.loads[ru] - lu + solution.loads[rv] - lv
                    if n1 <= capacity + EPS and n2 <= capacity + EPS:
                        solution.set_route(ru, Ru[:pu + 1] + Rv[:pv + 1][::-1])
                        solution.set_route(rv, Ru[pu + 1:][::-1] + Rv[pv + 1:])
                        return (u, v, b_u, b_v)
            # or-opt: move segment u..u+L-1 (L = 2, 3) next to v
            for L in (2, 3):
                if pu + L > len(Ru):
                    break
                seg = Ru[pu:pu + L]
                sl = sum(demands[c] for c in seg)
                if solution.loads[rv] + sl > capacity + EPS:
                    continue
                last = seg[-1]
                after = Ru[pu + L] if pu + L < len(Ru) else 0
                rem = distances[a_u][u] + distances[last][after] - distances[a_u][after]
                ins = distances[v][u] + distances[last][b_v] - distances[v][b_v]
                ins_r = distances[v][last] + distances[u][b_v] - distances[v][b_v] if symmetric else INF
                if min(ins, ins_r) - rem < -1e-9:
                    put = seg if ins <= ins_r else seg[::-1]
                    solution.set_route(ru, Ru[:pu] + Ru[pu + L:])
                    solution.set_route(rv, Rv[:pv + 1] + put + Rv[pv + 1:])
                    return (u, v, a_u, after, b_v, last)
        else:
            # same route: 2-opt (reverse between), relocate, or-opt -> evaluate by rebuilding
            if not symmetric or len(Ru) < 3:
                continue
            i, j = (pu, pv) if pu < pv else (pv, pu)
            a = Ru[i - 1] if i > 0 else 0
            b = Ru[j + 1] if j + 1 < len(Ru) else 0
            # reverse Ru[i..j]
            delta = distances[a][Ru[j]] + distances[Ru[i]][b] - distances[a][Ru[i]] - distances[Ru[j]][b]
            if delta < -1e-9:
                solution.set_route(ru, Ru[:i] + Ru[i:j + 1][::-1] + Ru[j + 1:])
                return (u, v, a, b)
            # relocate u right after v inside the route
            if pv + 1 != pu and pv != pu:
                new = Ru[:pu] + Ru[pu + 1:]
                k = new.index(v)
                new = new[:k + 1] + [u] + new[k + 1:]
                if solution.problem.route_cost(new) < solution.route_costs[ru] - 1e-9:
                    solution.set_route(ru, new)
                    return (u, v, a_u, b_u, b_v)
    return None


def ruin(solution, rng, max_strings=3, Lmax=10):
    problem = solution.problem
    seed = rng.randint(1, problem.n)
    ks = rng.randint(1, max_strings)
    removed, done = [], set()
    for c in [seed] + problem.neighbors[seed]:
        r = solution.route_of[c]
        if r < 0 or r in done:
            continue
        rt = solution.routes[r]
        L = rng.randint(1, min(Lmax, len(rt)))
        p = solution.position[c]
        lo, hi = max(0, p - L + 1), min(p, len(rt) - L)
        st = rng.randint(lo, hi)
        seg = rt[st:st + L]
        solution.set_route(r, rt[:st] + rt[st + L:])
        for x in seg:
            solution.route_of[x] = -1
        removed.extend(seg)
        done.add(r)
        if len(done) >= ks:
            break
    return removed


def recreate(solution, removed, rng, blink=0.01):
    problem = solution.problem
    distances, demands, capacity = problem.distances, problem.demands, problem.capacity
    mode = rng.randrange(4)
    if mode == 0:
        rng.shuffle(removed)
    elif mode == 1:
        removed.sort(key=lambda c: -demands[c])
    elif mode == 2:
        removed.sort(key=lambda c: -distances[0][c])
    else:
        removed.sort(key=lambda c: distances[0][c])
    for c in removed:
        cand = {solution.route_of[j] for j in problem.neighbors[c] if solution.route_of[j] >= 0}
        best = None
        for full in (False, True):
            routes_to_try = cand if not full else range(len(solution.routes))
            for r in routes_to_try:
                rt = solution.routes[r]
                if solution.loads[r] + demands[c] > capacity + EPS:
                    continue
                if not rt and full is False:
                    continue
                prev = 0
                for t in range(len(rt) + 1):
                    nxt = rt[t] if t < len(rt) else 0
                    v = distances[prev][c] + distances[c][nxt] - distances[prev][nxt]
                    if (best is None or v < best[0]) and rng.random() >= blink:
                        best = (v, r, t)
                    prev = nxt
            if best is not None:
                break
        if best is None:
            return False
        _, r, t = best
        rt = solution.routes[r]
        solution.set_route(r, rt[:t] + [c] + rt[t:])
    return True
