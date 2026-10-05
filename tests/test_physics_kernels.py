import unittest
from unittest.mock import patch

import numpy as np

from physics import Body, CollisionHandler, PhysicsEngine
from physics.gravity import GravitySolver
from physics.integrator import RK4Integrator
from physics.integrator_opt import RK4IntegratorOpt
from physics.gravity_opt import GravitySolverOpt
from physics import kernels
from scientific.simulator import InitialState, SimulationConfig, run_simulation


class PhysicsKernelTests(unittest.TestCase):
    def bodies(self):
        return [
            Body(mass=1, physical_radius=1e-5, position=(-1, 0), velocity=(0, -.2)),
            Body(mass=2, physical_radius=1e-5, position=(1, 0), velocity=(0, .1)),
            Body(mass=.1, physical_radius=1e-5, position=(0, 3), velocity=(.1, 0)),
        ]

    def test_force_and_rk4_match_reference(self):
        original, optimized = self.bodies(), self.bodies()
        reference = GravitySolver(softening=1e-4)
        solver = GravitySolverOpt(softening=1e-4, use_gpu=False)
        np.testing.assert_allclose(solver.compute_accelerations(optimized),
                                   reference.compute_accelerations(original), rtol=1e-13, atol=1e-15)
        old, new = RK4Integrator(reference), RK4IntegratorOpt(solver)
        for _ in range(100):
            old.step(original, .001)
            new.step(optimized, .001)
        np.testing.assert_allclose([b.position for b in optimized],
                                   [b.position for b in original], rtol=1e-12, atol=1e-14)
        np.testing.assert_allclose([b.velocity for b in optimized],
                                   [b.velocity for b in original], rtol=1e-12, atol=1e-14)

    def test_collision_boundary_order_and_merge_conservation(self):
        bodies = [Body(name=str(i), mass=i + 1, physical_radius=1,
                       position=(x, 0), velocity=(i, -i))
                  for i, x in enumerate((0, .5, 1, 3))]
        handler = CollisionHandler()
        # 距离恰等于半径和时不碰撞；重叠对保持原来的遍历顺序。
        self.assertEqual(handler.detect_collisions(bodies), [(0, 1), (0, 2), (1, 2)])
        mass = sum(b.mass for b in bodies)
        momentum = sum(b.momentum() for b in bodies)
        merged = handler.resolve_collisions(bodies)
        self.assertEqual([b.name for b in merged], ['0+1', '2', '3'])
        self.assertEqual(sum(b.mass for b in merged), mass)
        np.testing.assert_allclose(sum(b.momentum() for b in merged), momentum)

    def test_verlet_cache_in_both_timing_paths(self):
        class Timing:
            def record(self, *args): pass
            def record_count(self, *args): pass
        for timing in (None, Timing()):
            engine = PhysicsEngine(use_gpu=False)
            for b in self.bodies(): engine.add_body(b)
            engine.set_timing(timing)
            with patch.object(engine.gravity_solver, 'compute_accelerations',
                              wraps=engine.gravity_solver.compute_accelerations) as force:
                for _ in range(5): engine._single_step()
                self.assertEqual(force.call_count, 6)
                engine.add_body(Body(position=(10, 10), physical_radius=1e-5))
                engine._single_step()
                self.assertEqual(force.call_count, 8)
            engine.bodies[0].position = engine.bodies[1].position.copy()
            engine.dt = 1e-12
            engine._cached_accelerations = None
            engine._single_step()
            self.assertIsNone(engine._cached_accelerations)

    def test_numpy_dispatch_and_empty_states(self):
        pos = np.array([b.position for b in self.bodies()])
        vel = np.zeros_like(pos)
        mass = np.array([1., 2., .1])
        with patch.object(kernels, 'NUMBA_AVAILABLE', False):
            np.testing.assert_allclose(kernels.accelerations(pos, mass, 1e-8),
                                       GravitySolver(softening=1e-4).compute_accelerations(self.bodies()))
            p, v = kernels.rk4_step(pos, vel, mass, .001, 1e-8)
            self.assertTrue(np.isfinite(p).all() and np.isfinite(v).all())
            self.assertEqual(kernels.accelerations(np.empty((0, 2)), np.empty(0), 1e-8).shape, (0, 2))
        self.assertEqual(kernels.collision_pairs(np.empty((0, 2)), np.empty(0)), [])
        self.assertFalse(kernels.has_collision(np.empty((0, 2)), np.empty(0)))

    def test_offline_simulation_matches_shared_rk4(self):
        bodies = self.bodies()
        initial = InitialState(bodies, ['1', '.1'])
        result = run_simulation(initial, SimulationConfig(.01, .001, 1))
        integrator = RK4IntegratorOpt(GravitySolverOpt(use_gpu=False))
        for _ in range(10): integrator.step(bodies, .001)
        self.assertEqual(result.total_steps, 10)
        np.testing.assert_allclose(result.frame_positions[-1], [b.position for b in bodies], atol=1e-14)
        np.testing.assert_allclose(result.frame_velocities[-1], [b.velocity for b in bodies], atol=1e-14)


if __name__ == '__main__':
    unittest.main()
