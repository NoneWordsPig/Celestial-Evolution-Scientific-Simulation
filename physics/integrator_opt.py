"""实时 RK4：CPU 复用共享内核，GPU/阶段计时复用基础积分器。"""
import numpy as np
from .integrator import RK4Integrator
from .kernels import rk4_step


class RK4IntegratorOpt(RK4Integrator):
    def step(self, bodies, dt):
        if not bodies:
            return
        if self.gravity_solver.use_gpu or self.gravity_solver._timing is not None:
            return super().step(bodies, dt)

        positions = np.array([b.position for b in bodies], dtype=np.float64)
        velocities = np.array([b.velocity for b in bodies], dtype=np.float64)
        masses = np.array([b.mass for b in bodies], dtype=np.float64)
        positions, velocities = rk4_step(
            positions, velocities, masses, dt, self.gravity_solver.softening ** 2
        )
        for i, body in enumerate(bodies):
            body.position = positions[i]
            body.velocity = velocities[i]
