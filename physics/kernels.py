"""共享 float64 数值内核：数组输入，无 Body/UI 依赖；Numba 可选。"""
import math
import numpy as np
from .constants import G, COLLISION_FACTOR

try:
    from numba import njit
except ImportError:
    njit = None

NUMBA_AVAILABLE = njit is not None

def accelerations_numpy(pos, mass, softening_sq: float) -> np.ndarray:
    """NumPy 向量化引力加速度（与 GravitySolver 相同公式，2D 差分避免 3D 临时数组）。"""
    n = pos.shape[0]
    if n == 0:
        return np.zeros((0, 2), dtype=np.float64)
    if n == 1:
        return np.zeros((1, 2), dtype=np.float64)
    x = pos[:, 0]
    y = pos[:, 1]
    dx = x[None, :] - x[:, None]          # dx[i, j] = pos[j] - pos[i]
    dy = y[None, :] - y[:, None]
    dist_sq = dx * dx + dy * dy + softening_sq
    idx = np.arange(n)
    dist_sq[idx, idx] = 1.0
    inv_cube = dist_sq ** -1.5
    inv_cube[idx, idx] = 0.0
    weights = mass[None, :] * inv_cube    # weights[i, j] = mass[j] * inv_cube
    ax = (weights * dx).sum(axis=1) * G
    ay = (weights * dy).sum(axis=1) * G
    return np.column_stack((ax, ay))


def rk4_step_numpy(pos, vel, mass, dt, softening_sq):
    """与 RK4IntegratorOpt 完全相同的 RK4 步进。"""
    n = pos.shape[0]
    if n == 0:
        return pos, vel
    half = 0.5 * dt
    sixth = dt / 6.0

    a1 = accelerations_numpy(pos, mass, softening_sq)
    v1 = vel.copy()

    p2 = pos + half * v1
    v2 = vel + half * a1
    a2 = accelerations_numpy(p2, mass, softening_sq)

    p3 = pos + half * v2
    v3 = vel + half * a2
    a3 = accelerations_numpy(p3, mass, softening_sq)

    p4 = pos + dt * v3
    v4 = vel + dt * a3
    a4 = accelerations_numpy(p4, mass, softening_sq)

    new_pos = pos + sixth * (v1 + 2.0 * v2 + 2.0 * v3 + v4)
    new_vel = vel + sixth * (a1 + 2.0 * a2 + 2.0 * a3 + a4)
    return new_pos, new_vel


def _overlap(pos, radii, i, j, factor):
    dx = pos[i, 0] - pos[j, 0]
    dy = pos[i, 1] - pos[j, 1]
    threshold = (radii[i] + radii[j]) * factor
    return dx * dx + dy * dy < threshold * threshold


def collision_pairs(pos, radii, factor=COLLISION_FACTOR):
    """按 i、j 升序返回碰撞对，保留贪心融合顺序。"""
    pairs = []
    for i in range(len(pos)):
        for j in range(i + 1, len(pos)):
            if _overlap(pos, radii, i, j, factor):
                pairs.append((i, j))
    return pairs


def has_collision(pos, radii, factor=COLLISION_FACTOR):
    """命中后立即返回，不分配碰撞对列表。"""
    for i in range(len(pos)):
        for j in range(i + 1, len(pos)):
            if _overlap(pos, radii, i, j, factor):
                return True
    return False


if NUMBA_AVAILABLE:
    _overlap = njit(cache=True, inline='always')(_overlap)
    collision_pairs = njit(cache=True)(collision_pairs)
    has_collision = njit(cache=True)(has_collision)
else:
    def _collision_mask(pos, radii, factor):
        i, j = np.triu_indices(len(pos), 1)
        dx = pos[i, 0] - pos[j, 0]
        dy = pos[i, 1] - pos[j, 1]
        threshold = (radii[i] + radii[j]) * factor
        return i, j, dx * dx + dy * dy < threshold * threshold

    def collision_pairs(pos, radii, factor=COLLISION_FACTOR):
        i, j, mask = _collision_mask(pos, radii, factor)
        return list(zip(i[mask].tolist(), j[mask].tolist()))

    def has_collision(pos, radii, factor=COLLISION_FACTOR):
        return bool(np.any(_collision_mask(pos, radii, factor)[2]))


if NUMBA_AVAILABLE:
    @njit(cache=True)
    def accelerations_numba(p, mass, softening_sq):
        """对称上三角 Numba 引力加速度（成对仅计算一次，无临时数组）。"""
        n = p.shape[0]
        acc = np.zeros((n, 2), dtype=np.float64)
        for i in range(n):
            xi = p[i, 0]
            yi = p[i, 1]
            for j in range(i + 1, n):
                dx = p[j, 0] - xi
                dy = p[j, 1] - yi
                dsq = dx * dx + dy * dy + softening_sq
                inv = 1.0 / (dsq * math.sqrt(dsq))
                wi = mass[j] * inv
                wj = mass[i] * inv
                acc[i, 0] += wi * dx
                acc[i, 1] += wi * dy
                acc[j, 0] -= wj * dx
                acc[j, 1] -= wj * dy
        return acc * G

    @njit(cache=True)
    def rk4_step_numba(pos, vel, mass, dt, softening_sq):
        """数组 RK4 步进，与 NumPy 路径使用相同公式。"""
        n = pos.shape[0]
        half = 0.5 * dt
        sixth = dt / 6.0

        # k1（v1 = vel）
        a1 = accelerations_numba(pos, mass, softening_sq)

        # k2
        p2 = np.empty((n, 2), dtype=np.float64)
        v2 = np.empty((n, 2), dtype=np.float64)
        for i in range(n):
            p2[i, 0] = pos[i, 0] + half * vel[i, 0]
            p2[i, 1] = pos[i, 1] + half * vel[i, 1]
            v2[i, 0] = vel[i, 0] + half * a1[i, 0]
            v2[i, 1] = vel[i, 1] + half * a1[i, 1]
        a2 = accelerations_numba(p2, mass, softening_sq)

        # k3
        p3 = np.empty((n, 2), dtype=np.float64)
        v3 = np.empty((n, 2), dtype=np.float64)
        for i in range(n):
            p3[i, 0] = pos[i, 0] + half * v2[i, 0]
            p3[i, 1] = pos[i, 1] + half * v2[i, 1]
            v3[i, 0] = vel[i, 0] + half * a2[i, 0]
            v3[i, 1] = vel[i, 1] + half * a2[i, 1]
        a3 = accelerations_numba(p3, mass, softening_sq)

        # k4
        p4 = np.empty((n, 2), dtype=np.float64)
        v4 = np.empty((n, 2), dtype=np.float64)
        for i in range(n):
            p4[i, 0] = pos[i, 0] + dt * v3[i, 0]
            p4[i, 1] = pos[i, 1] + dt * v3[i, 1]
            v4[i, 0] = vel[i, 0] + dt * a3[i, 0]
            v4[i, 1] = vel[i, 1] + dt * a3[i, 1]
        a4 = accelerations_numba(p4, mass, softening_sq)

        new_pos = np.empty((n, 2), dtype=np.float64)
        new_vel = np.empty((n, 2), dtype=np.float64)
        for i in range(n):
            new_pos[i, 0] = pos[i, 0] + sixth * (vel[i, 0] + 2.0 * v2[i, 0] + 2.0 * v3[i, 0] + v4[i, 0])
            new_pos[i, 1] = pos[i, 1] + sixth * (vel[i, 1] + 2.0 * v2[i, 1] + 2.0 * v3[i, 1] + v4[i, 1])
            new_vel[i, 0] = vel[i, 0] + sixth * (a1[i, 0] + 2.0 * a2[i, 0] + 2.0 * a3[i, 0] + a4[i, 0])
            new_vel[i, 1] = vel[i, 1] + sixth * (a1[i, 1] + 2.0 * a2[i, 1] + 2.0 * a3[i, 1] + a4[i, 1])

        return new_pos, new_vel


def accelerations(pos, mass, softening_sq):
    if NUMBA_AVAILABLE:
        return accelerations_numba(pos, mass, softening_sq)
    return accelerations_numpy(pos, mass, softening_sq)


def rk4_step(pos, vel, mass, dt, softening_sq):
    if NUMBA_AVAILABLE:
        return rk4_step_numba(pos, vel, mass, dt, softening_sq)
    return rk4_step_numpy(pos, vel, mass, dt, softening_sq)


def rk4_step_and_check(pos, vel, mass, radii, dt, softening_sq):
    new_pos, new_vel = rk4_step(pos, vel, mass, dt, softening_sq)
    return new_pos, new_vel, has_collision(new_pos, radii)
