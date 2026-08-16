"""
独立校验 shiyan/cases.json 中各案例的参考最优值(ground truth)。
用暴力/精确方法独立计算，避免论文里用错误的 ground truth。与被测智能体完全独立。
"""
from __future__ import annotations
import itertools, math


def knapsack():
    w = [2, 3, 4, 5, 9]; v = [3, 4, 5, 8, 10]; cap = 20
    best = 0
    for r in range(len(w) + 1):
        for combo in itertools.combinations(range(len(w)), r):
            if sum(w[i] for i in combo) <= cap:
                best = max(best, sum(v[i] for i in combo))
    return best


def tsp():
    pts = {"A": (0, 0), "B": (0, 4), "C": (4, 4), "D": (4, 0), "E": (2, 2)}
    d = lambda a, b: math.dist(pts[a], pts[b])
    best = float("inf")
    others = ["B", "C", "D", "E"]
    for perm in itertools.permutations(others):
        route = ["A"] + list(perm) + ["A"]
        dist = sum(d(route[i], route[i + 1]) for i in range(len(route) - 1))
        best = min(best, dist)
    return round(best, 4)


def assignment():
    cost = [[9, 2, 7], [6, 4, 3], [5, 8, 1]]
    best = float("inf")
    for perm in itertools.permutations(range(3)):
        best = min(best, sum(cost[i][perm[i]] for i in range(3)))
    return best


def scheduling():
    # 单机总延误最小，枚举所有顺序
    p = [3, 1, 2, 4]; due = [4, 2, 6, 8]
    best = float("inf")
    for perm in itertools.permutations(range(4)):
        t = 0; tardiness = 0
        for j in perm:
            t += p[j]
            tardiness += max(0, t - due[j])
        best = min(best, tardiness)
    return best


def uflp():
    open_cost = [4, 3, 5]
    serve = [[2, 3, 1, 4], [5, 4, 2, 1], [3, 2, 4, 2]]
    n_fac, n_cust = 3, 4
    best = float("inf")
    for r in range(1, n_fac + 1):
        for opened in itertools.combinations(range(n_fac), r):
            total = sum(open_cost[i] for i in opened)
            for j in range(n_cust):
                total += min(serve[i][j] for i in opened)
            best = min(best, total)
    return best


if __name__ == "__main__":
    print("C01 knapsack   =", knapsack(), "(expect 26)")
    print("C02 tsp        =", tsp(), "(expect ~16.0)")
    print("C03 assignment =", assignment(), "(expect 8)")
    print("C06 scheduling =", scheduling(), "(expect 2)")
    print("C10 uflp       =", uflp(), "(expect 13)")
