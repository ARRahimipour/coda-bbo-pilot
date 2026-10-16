"""Regression tests for the budget, operators, and reproducibility contracts."""

import unittest

import numpy as np

from pilot import (
    Budget,
    FAMILIES,
    METHODS,
    Program,
    REFERENCE,
    calibrate,
    features,
    objective,
    proposal,
    run,
)


class PilotTests(unittest.TestCase):
    """Checks that are independent of a particular hardware timing result."""

    @classmethod
    def setUpClass(cls):
        # Calibrate once because all tests use the same frozen reference model.
        cls.models = calibrate()

    def test_known_minima(self):
        for name in FAMILIES:
            f, optimum = objective(name, 5, 0)
            self.assertAlmostEqual(f(optimum), 0, places=9)

    def test_nonnegative(self):
        for name in FAMILIES:
            f, _ = objective(name, 5, 0)
            self.assertGreaterEqual(f(np.zeros(5)), -1e-12)

    def test_budget_guard(self):
        budget = Budget(lambda x: 1, 1)
        budget(np.zeros(5))
        with self.assertRaises(RuntimeError):
            budget(np.zeros(5))

    def test_invalid_program(self):
        for operators in ((), ("eval",), ("de",) * 4):
            with self.assertRaises(ValueError):
                Program(operators)

    def test_proposal_bounds(self):
        rng = np.random.default_rng(3)
        population = rng.uniform(-5, 5, (20, 5))
        for operator in ("de", "local", "uniform"):
            for iteration in range(50):
                _, candidate = proposal(
                    population, np.arange(20), rng,
                    Program((operator,)), iteration, F=3, sigma=5,
                )
                self.assertTrue(np.all(np.abs(candidate) <= 5))

    def test_all_methods_exact_budget(self):
        f, _ = objective("ackley", 5, 0)
        for method in METHODS:
            results, curve = run(f, 5, 4, method, self.models[5], 260)
            self.assertEqual(results["evaluations"], 260)
            self.assertTrue(np.all(np.diff(curve) <= 1e-12))

    def test_determinism(self):
        f, _ = objective("sphere", 5, 0)
        first, curve1 = run(f, 5, 2, "CODA-pilot", self.models[5], 300)
        second, curve2 = run(f, 5, 2, "CODA-pilot", self.models[5], 300)
        np.testing.assert_array_equal(curve1, curve2)
        self.assertEqual(first["final"], second["final"])

    def test_trial_accounting(self):
        f, _ = objective("sphere", 5, 0)
        model = dict(self.models[5])
        model["threshold"] = -1  # Force the novelty trigger at every checkpoint.
        results, _ = run(f, 5, 2, "CODA-pilot", model, 1000)
        self.assertEqual(results["trials"], 4)
        self.assertEqual(results["trial_evals"], 160)
        self.assertLessEqual(results["accepted"], 4)

    def test_reference_excludes_holdout(self):
        held_out = {"ackley", "rosenbrock", "griewank"}
        self.assertEqual(set(REFERENCE) & held_out, set())

    def test_common_probe(self):
        f, _ = objective("sphere", 5, 0)
        initial_values = [
            run(f, 5, 7, method, self.models[5], 80)[0]["initial"]
            for method in METHODS
        ]
        self.assertEqual(len(set(initial_values)), 1)

    def test_reject_invalid_point(self):
        budget = Budget(lambda x: 1, 10)
        with self.assertRaises(ValueError):
            budget(np.array([6.0]))
        self.assertEqual(budget.n, 0)  # Invalid inputs must not be charged.

    def test_feature_affine_fitness_invariance(self):
        rng = np.random.default_rng(1)
        points = rng.normal(size=(40, 5))
        values = np.sum(points * points, axis=1)
        np.testing.assert_allclose(
            features(points, values),
            features(points, 4 * values + 3),
            atol=1e-10,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
