# CODA-BBO: Research Pilot
# Copyright © 2026 Alireza Rahimipour Anaraki. All rights reserved.
# All rights reserved.

"""Run the stage-zero CODA-BBO optimization experiment.

This is a small, reproducible pilot—not the complete CODA-BBO research system.
It uses a fixed pool of operator sequences and a heuristic controller. There is
no learned program generator, calibrated transfer-risk model, or task memory.

Every objective call, including an unsuccessful candidate trial, is charged to
the same per-run budget. This is the main invariant of the experiment.
"""

import argparse
import json
import platform
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


FAMILIES = [
    "sphere",
    "ellipsoid",
    "rastrigin",
    "ackley",
    "rosenbrock",
    "griewank",
]
REFERENCE = FAMILIES[:3]
METHODS = ["Random", "DE", "Adaptive-DE", "CODA-pilot", "No-OOD", "No-edit"]

LOWER_BOUND = -5.0
UPPER_BOUND = 5.0
INITIAL_PROBES = 40
POPULATION_SIZE = 20
CHECKPOINT_INTERVAL = 200
TRIAL_CALLS_PER_BRANCH = 20


def objective(name, d, instance):
    """Return a shifted test function and its known minimizer.

    The shift is fixed by dimension and instance number, independent of the
    optimizer seed. Functions here are simple analytic benchmarks, not official
    COCO/BBOB transformations.
    """
    shift = np.random.default_rng(10000 + instance * 100 + d).uniform(-1, 1, d)

    def f(x):
        z = np.asarray(x) - shift

        if name == "sphere":
            return float(np.sum(z * z))
        if name == "ellipsoid":
            return float(np.sum(np.logspace(0, 4, d) * z * z))
        if name == "rastrigin":
            return float(10 * d + np.sum(z * z - 10 * np.cos(2 * np.pi * z)))
        if name == "ackley":
            return float(
                -20 * np.exp(-0.2 * np.sqrt(np.mean(z * z)))
                - np.exp(np.mean(np.cos(2 * np.pi * z)))
                + 20
                + np.e
            )
        if name == "rosenbrock":
            w = z + 1
            return float(np.sum(100 * (w[1:] - w[:-1] ** 2) ** 2 + (w[:-1] - 1) ** 2))
        if name == "griewank":
            return float(
                np.sum(z * z) / 4000
                - np.prod(np.cos(z / np.sqrt(np.arange(1, d + 1))))
                + 1
            )
        raise ValueError(name)

    return f, shift


class Budget:
    """Guard objective evaluations and remember the best value seen so far."""

    def __init__(self, f, b):
        self.f = f
        self.b = b
        self.n = 0
        self.best = np.inf
        self.trace = []

    def __call__(self, x):
        if self.n >= self.b:
            raise RuntimeError("budget exhausted")
        if not np.all(np.isfinite(x)) or np.any(np.abs(x) > 5 + 1e-10):
            raise ValueError("invalid point")

        y = self.f(x)
        if not np.isfinite(y):
            raise ValueError("nonfinite objective")

        self.n += 1
        self.best = min(self.best, y)
        self.trace.append(self.best)
        return y


@dataclass(frozen=True)
class Program:
    """A short, validated sequence of proposal operators."""

    ops: tuple

    def __post_init__(self):
        allowed = ("de", "local", "uniform")
        if not 1 <= len(self.ops) <= 3 or any(op not in allowed for op in self.ops):
            raise ValueError("invalid bounded program")


def proposal(pop, fit, rng, program, k, F=0.7, sigma=0.1):
    """Propose one point from the operator scheduled for iteration ``k``.

    DE uses rand/1 mutation and binomial crossover. Local search perturbs the
    current population best, while uniform search samples the entire box.
    All proposals are clipped before evaluation.
    """
    n, d = pop.shape
    i = k % n
    op = program.ops[k % len(program.ops)]

    if op == "uniform":
        x = rng.uniform(-5, 5, d)
    elif op == "local":
        x = pop[np.argmin(fit)] + rng.normal(0, 10 * sigma, d)
    else:
        ids = np.delete(np.arange(n), i)
        a, b, c = rng.choice(ids, 3, replace=False)
        mutant = pop[a] + F * (pop[b] - pop[c])
        mask = rng.random(d) < 0.9
        mask[rng.integers(d)] = True  # Force at least one mutant coordinate.
        x = np.where(mask, mutant, pop[i])

    return i, np.clip(x, -5, 5)


def features(x, y):
    """Summarize the initial probes without knowing the function identity.

    These four handcrafted features are only a novelty diagnostic. The last
    feature depends on probe order and should not be interpreted as a spatial
    landscape measure.
    """
    z = (y - np.mean(y)) / (np.std(y) + 1e-12)
    distance = np.linalg.norm(x - x[np.argmin(y)], axis=1)
    correlation = (
        0.0
        if np.std(distance) < 1e-12
        else float(np.corrcoef(distance, z)[0, 1])
    )
    return np.array(
        [
            correlation,
            np.mean(z**3),
            np.quantile(z, 0.9) - np.quantile(z, 0.5),
            np.mean(np.abs(np.diff(z))),
        ]
    )


def calibrate():
    """Fit a frozen novelty threshold using reference families only.

    For each dimension, 60 probe sets estimate feature location and scale,
    and another 30 sets determine an empirical 95th-percentile threshold.
    This is not probability calibration for harmful transfer.
    """
    models = {}
    for d in (5, 10):
        train = []
        calibration = []
        for name in REFERENCE:
            for j in range(30):
                rng = np.random.default_rng(90000 + j)
                x = rng.uniform(-5, 5, (INITIAL_PROBES, d))
                f, _ = objective(name, d, 100 + j)
                values = features(x, np.array([f(point) for point in x]))
                (train if j < 20 else calibration).append(values)

        mu = np.mean(train, axis=0)
        scale = np.maximum(np.std(train, axis=0), 0.05)
        scores = np.sqrt(np.mean(((np.array(calibration) - mu) / scale) ** 2, axis=1))
        models[d] = {
            "mu": mu.tolist(),
            "scale": scale.tolist(),
            "threshold": float(np.quantile(scores, 0.95)),
        }
    return models


def run(f, d, seed, method, model, budget=1000):
    """Execute one method on one task, returning metrics and a sampled curve.

    All methods start with the same initial probes for a given seed. A trial
    compares control and candidate programs from copies of one population.
    The shared evaluator keeps improvements from both branches, even if the
    corresponding branch is discarded (valid here for static objectives).
    """
    start = time.perf_counter()
    rng = np.random.default_rng(seed)
    evaluator = Budget(f, budget)

    # Initialization is part of the task budget, not a free warm start.
    x = rng.uniform(-5, 5, (INITIAL_PROBES, d))
    y = np.array([evaluator(point) for point in x])
    initial = float(min(y))

    observed_features = features(x, y)
    novelty = float(
        np.sqrt(
            np.mean(
                (
                    (observed_features - np.array(model["mu"]))
                    / np.array(model["scale"])
                ) ** 2
            )
        )
    )
    high_novelty = novelty > model["threshold"]

    best_ids = np.argsort(y)[:POPULATION_SIZE]
    population = x[best_ids].copy()
    fitness = y[best_ids].copy()

    program = Program(("de",))
    F = 0.7
    sigma = 0.1
    last_best = evaluator.best
    iteration = 0
    trials = accepted = tunes = trial_evals = 0
    next_checkpoint = CHECKPOINT_INTERVAL

    while evaluator.n < budget:
        # A 40-call trial must fit entirely in the remaining objective budget.
        if evaluator.n >= next_checkpoint and budget - evaluator.n >= 40:
            stalled = (last_best - evaluator.best) <= 0.01 * max(abs(last_best), 1e-12)
            last_best = evaluator.best
            next_checkpoint += CHECKPOINT_INTERVAL
            active = stalled or (high_novelty and method in ("CODA-pilot", "No-edit"))

            if method in ("Adaptive-DE", "CODA-pilot", "No-OOD", "No-edit") and active:
                F = 0.45 if F > 0.6 else 0.85
                sigma = max(0.01, sigma * 0.65)
                tunes += 1

            if method in ("CODA-pilot", "No-OOD") and active:
                # The candidate is chosen from a small fixed pool, not generated
                # by a trained model. Never compare the current program to itself.
                pool = [
                    Program(("de", "local")),
                    Program(("local", "de", "local")),
                    Program(("de", "uniform", "local")),
                ]
                pool = [candidate for candidate in pool if candidate != program]
                candidate = pool[int(rng.integers(len(pool)))]
                trials += 1

                branch_states = []
                for branch_program in (program, candidate):
                    branch_pop = population.copy()
                    branch_fit = fitness.copy()
                    for j in range(TRIAL_CALLS_PER_BRANCH):
                        i, point = proposal(
                            branch_pop, branch_fit, rng, branch_program,
                            iteration + j, F, sigma,
                        )
                        value = evaluator(point)
                        if value < branch_fit[i]:
                            branch_pop[i] = point
                            branch_fit[i] = value
                    branch_states.append((branch_pop, branch_fit))

                trial_evals += 40  # Both branches cost 20 evaluations each.
                candidate_wins = int(
                    np.min(branch_states[1][1]) < np.min(branch_states[0][1])
                )
                population, fitness = branch_states[candidate_wins]
                if candidate_wins:
                    program = candidate
                    accepted += 1
                iteration += 20
                continue

        if method == "Random":
            i = 0
            point = rng.uniform(-5, 5, d)
        else:
            i, point = proposal(population, fitness, rng, program, iteration, F, sigma)

        value = evaluator(point)
        if value < fitness[i]:
            population[i] = point
            fitness[i] = value
        iteration += 1

    trace = np.array(evaluator.trace)
    normalized = np.log1p(np.maximum(trace[39:], 0)) / max(
        np.log1p(max(initial, 0)), 1e-12
    )
    metrics = {
        "auc": float(np.mean(normalized)),
        "final": float(evaluator.best),
        "initial": initial,
        "novelty": novelty,
        "flag": int(high_novelty),
        "evaluations": evaluator.n,
        "trials": trials,
        "accepted": accepted,
        "tunes": tunes,
        "trial_evals": trial_evals,
        "seconds": time.perf_counter() - start,
    }
    return metrics, trace[np.arange(39, budget, 20)]


def main(out, seeds, budget):
    """Run the complete benchmark and write raw records plus a manifest."""
    output_dir = Path(out)
    output_dir.mkdir(parents=True, exist_ok=True)
    models = calibrate()
    rows = []
    curves = []
    start = time.perf_counter()

    for family in FAMILIES:
        for d in (5, 10):
            for instance in range(3):
                f, _ = objective(family, d, instance)
                for seed in range(seeds):
                    for method in METHODS:
                        metrics, curve = run(f, d, seed, method, models[d], budget)
                        metrics.update(
                            family=family,
                            dimension=d,
                            instance=instance,
                            seed=seed,
                            method=method,
                            split="reference" if family in REFERENCE else "held-out",
                        )
                        rows.append(metrics)
                        curves.append(curve)
        print(f"{family}: {len(rows)} runs completed", flush=True)

    pd.DataFrame(rows).to_csv(output_dir / "runs.csv", index=False)
    np.savez_compressed(output_dir / "curves.npz", curves=curves)
    manifest = {
        "budget": budget,
        "seeds": seeds,
        "families": FAMILIES,
        "reference": REFERENCE,
        "dimensions": [5, 10],
        "instances": 3,
        "methods": METHODS,
        "runs": len(rows),
        "objective_evaluations": sum(row["evaluations"] for row in rows),
        "calibration_evaluations": 7200,
        "calibration": models,
        "elapsed_seconds": time.perf_counter() - start,
        "python": platform.python_version(),
        "numpy": np.__version__,
        "platform": platform.platform(),
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps({k: v for k, v in manifest.items() if k != "calibration"}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="results", help="Directory for run outputs")
    parser.add_argument("--seeds", type=int, default=10, help="Seeds per task")
    parser.add_argument("--budget", type=int, default=1000, help="Evaluation calls per run")
    args = parser.parse_args()
    main(args.out, args.seeds, args.budget)
