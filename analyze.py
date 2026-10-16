"""Summarize the CODA-BBO pilot results and recreate its five figures.

The main AUC summary gives every function family equal weight. Exploratory
confidence intervals resample the six family means, not individual runs; with
only six families, these intervals should not be read as broad guarantees.

Run this script from the repository root after ``pilot.py`` has produced the
complete default benchmark. The original raw run data is never overwritten.
"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # Save figures on machines without a graphical display.
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import rankdata

from pilot import FAMILIES, METHODS

RESULTS_DIR = Path("results")
FIGURES_DIR = Path("figures")
BOOTSTRAP_SEED = 20261016
BOOTSTRAP_SAMPLES = 10_000
COLORS = ["#9a9a9a", "#245b91", "#dd8e32", "#188a79", "#b65372", "#8265a7"]


def load_results():
    """Load run records, their ordered trajectories, and the experiment manifest."""
    runs = pd.read_csv(RESULTS_DIR / "runs.csv")
    curves = np.load(RESULTS_DIR / "curves.npz")["curves"]
    manifest = json.loads((RESULTS_DIR / "manifest.json").read_text())
    return runs, curves, manifest


def summarize_auc(runs):
    """Average over seeds and instances before giving equal weight to families."""
    task_auc = (
        runs.groupby(["family", "dimension", "instance", "method"], sort=False)
        .auc.mean()
        .unstack("method")[METHODS]
    )
    family_auc = task_auc.groupby("family").mean().reindex(FAMILIES)

    # Pair the bootstrap draws across methods to preserve the comparison.
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    sampled_ids = rng.integers(0, 6, (BOOTSTRAP_SAMPLES, 6))
    sampled_means = family_auc.values[sampled_ids].mean(axis=1)

    summary_rows = []
    for j, method in enumerate(METHODS):
        method_runs = runs[runs.method == method]
        summary_rows.append(
            {
                "method": method,
                "mean_auc": family_auc[method].mean(),
                "ci_low": np.quantile(sampled_means[:, j], 0.025),
                "ci_high": np.quantile(sampled_means[:, j], 0.975),
                "median_seconds": method_runs.seconds.median(),
                "mean_trial_evals": method_runs.trial_evals.mean(),
            }
        )

    summary = pd.DataFrame(summary_rows)
    summary.to_csv(RESULTS_DIR / "summary.csv", index=False)
    family_auc.to_csv(RESULTS_DIR / "family_auc.csv")
    return task_auc, family_auc, sampled_means, summary


def compare_methods(task_auc, family_auc, sampled_means):
    """Compare the pilot with each baseline using the same bootstrap draws."""
    pilot_index = METHODS.index("CODA-pilot")
    comparisons = []

    for j, method in enumerate(METHODS):
        if j == pilot_index:
            continue

        reduction = (
            100
            * (family_auc[method].mean() - family_auc["CODA-pilot"].mean())
            / family_auc[method].mean()
        )
        bootstrap_reductions = (
            100 * (sampled_means[:, j] - sampled_means[:, pilot_index])
            / sampled_means[:, j]
        )
        differences = task_auc[method] - task_auc["CODA-pilot"]
        comparisons.append(
            {
                "baseline": method,
                "relative_auc_reduction_pct": reduction,
                "ci_low": np.quantile(bootstrap_reductions, 0.025),
                "ci_high": np.quantile(bootstrap_reductions, 0.975),
                "wins": int((differences > 1e-12).sum()),
                "ties": int((abs(differences) <= 1e-12).sum()),
                "losses": int((differences < -1e-12).sum()),
            }
        )

    table = pd.DataFrame(comparisons)
    table.to_csv(RESULTS_DIR / "comparisons.csv", index=False)
    return table


def novelty_diagnostics(runs):
    """Score family-label separation once per task/seed using the DE records."""
    # Repeating the shared initial novelty value for all six methods would
    # artificially inflate the apparent number of independent observations.
    baseline = runs[runs.method == "DE"].copy()
    held_out = (baseline.split == "held-out").values
    scores = baseline.novelty.values
    n_positive = sum(held_out)
    n_negative = sum(~held_out)

    auroc = (
        rankdata(scores)[held_out].sum() - n_positive * (n_positive + 1) / 2
    ) / (n_positive * n_negative)
    report = {
        "auroc": float(auroc),
        "reference_flag_rate_pct": float(
            100 * baseline[baseline.split == "reference"].flag.mean()
        ),
        "heldout_flag_rate_pct": float(
            100 * baseline[baseline.split == "held-out"].flag.mean()
        ),
        "independent_seed_task_records": len(baseline),
        "family_clusters": 6,
    }
    (RESULTS_DIR / "ood.json").write_text(json.dumps(report, indent=2))
    return baseline, auroc, report


def save_figures(runs, curves, manifest, family_auc, summary, comparisons, baseline, auroc):
    """Reproduce the aggregate, trajectory, heatmap, comparison and OOD plots."""
    FIGURES_DIR.mkdir(exist_ok=True)
    plt.rcParams.update(
        {
            "font.size": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "savefig.dpi": 200,
        }
    )

    # Figure 1: family-level uncertainty around each mean AUC.
    fig, ax = plt.subplots(figsize=(7.2, 3.7))
    ax.bar(summary.method, summary.mean_auc, color=COLORS)
    ax.errorbar(
        summary.method,
        summary.mean_auc,
        yerr=[summary.mean_auc - summary.ci_low, summary.ci_high - summary.mean_auc],
        fmt="none",
        color="black",
        capsize=3,
    )
    ax.set_ylabel("Normalized log-error AUC ↓")
    ax.set_title("Measured pilot performance with family bootstrap intervals")
    ax.tick_params(axis="x", rotation=20)
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "aggregate.png")
    plt.close(fig)

    # Figure 2: every curve comes from objective calls, including trial calls.
    fig, axes = plt.subplots(2, 3, figsize=(9, 5.4), sharex=True)
    for ax, family in zip(axes.flat, FAMILIES):
        for method, color in zip(METHODS, COLORS):
            selected = (runs.family == family) & (runs.method == method)
            sampled_curves = curves[selected]
            initial = runs.loc[selected, "initial"].values
            normalized = np.log1p(np.maximum(sampled_curves, 0)) / np.log1p(
                initial[:, None]
            )
            ax.plot(
                np.arange(40, manifest["budget"] + 1, 20),
                normalized.mean(axis=0),
                label=method,
                color=color,
                lw=1.5,
            )
        ax.set_title(family)
        ax.set_ylim(0, 1.03)
        ax.grid(alpha=0.15)
    axes[1, 1].set_xlabel("Objective evaluations including trials")
    axes[0, 0].set_ylabel("Normalized log error")
    axes[1, 0].set_ylabel("Normalized log error")
    legend_handles, legend_labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(legend_handles, legend_labels, loc="lower center", ncol=6, fontsize=8)
    fig.tight_layout(rect=[0, 0.06, 1, 1])
    fig.savefig(FIGURES_DIR / "convergence.png")
    plt.close(fig)

    # Figure 3: which function families drive the aggregate differences?
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    image = ax.imshow(family_auc.values, aspect="auto", cmap="YlGnBu", vmin=0, vmax=1)
    ax.set_xticks(range(6), METHODS, rotation=25, ha="right")
    ax.set_yticks(range(6), FAMILIES)
    for i in range(6):
        for j in range(6):
            value = family_auc.values[i, j]
            ax.text(
                j, i, f"{value:.3f}", ha="center", va="center",
                color="white" if value > 0.6 else "black",
            )
    fig.colorbar(image, ax=ax, label="AUC ↓")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "heatmap.png")
    plt.close(fig)

    # Figure 4: positive values mean lower CODA-pilot AUC than a baseline.
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    ax.barh(comparisons.baseline, comparisons.relative_auc_reduction_pct, color="#188a79")
    ax.errorbar(
        comparisons.relative_auc_reduction_pct,
        comparisons.baseline,
        xerr=[
            comparisons.relative_auc_reduction_pct - comparisons.ci_low,
            comparisons.ci_high - comparisons.relative_auc_reduction_pct,
        ],
        fmt="none",
        color="black",
        capsize=3,
    )
    ax.axvline(0, color="gray", lw=1)
    ax.set_xlabel("CODA-pilot relative AUC reduction (%) → better")
    ax.set_title("Exploratory 95% intervals resample six function families")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "percentages.png")
    plt.close(fig)

    # Figure 5: novelty separation and the actual number of structural trials.
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.3))
    axes[0].boxplot(
        [baseline[baseline.split == split].novelty for split in ("reference", "held-out")],
        tick_labels=["Reference", "Held-out"],
    )
    axes[0].set_ylabel("Initial novelty score")
    axes[0].set_title(f"Family-label AUROC = {auroc:.3f}")
    activity = (
        runs[runs.method.isin(["CODA-pilot", "No-OOD"])]
        .groupby("method")[["trials", "accepted"]]
        .mean()
    )
    activity.plot.bar(ax=axes[1], color=["#245b91", "#188a79"], rot=0)
    axes[1].set_ylabel("Mean count per run")
    axes[1].set_title("Candidate trials and accepted edits")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "diagnostics.png")
    plt.close(fig)


def main():
    """Recreate the published result tables and figures from existing raw data."""
    runs, curves, manifest = load_results()
    task_auc, family_auc, boot, summary = summarize_auc(runs)
    comparisons = compare_methods(task_auc, family_auc, boot)
    final_errors = (
        runs.groupby(["family", "method"])
        .final.median()
        .unstack()
        .reindex(FAMILIES)[METHODS]
    )
    final_errors.to_csv(RESULTS_DIR / "final_errors.csv")
    baseline, auroc, ood = novelty_diagnostics(runs)
    save_figures(
        runs, curves, manifest, family_auc, summary, comparisons, baseline, auroc
    )
    print(summary.to_string(index=False))
    print(comparisons.to_string(index=False))
    print(ood)
    print("FINAL ERRORS", final_errors.to_string())


if __name__ == "__main__":
    main()
