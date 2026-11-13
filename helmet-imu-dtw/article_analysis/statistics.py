"""
STATISTICS: comparison of every method with the raw helmet signal.

For each impact energy and location (and for all locations pooled), the RMSE of
LP and Methods 1-4 is compared with the RMSE of the raw helmet signal:

    - test       : Wilcoxon signed-rank test, paired, two-sided
    - unit       : trial. The impacts of the same trial are not independent, so
                   their RMSE values are averaged first (one value per trial)
    - correction : Bonferroni, within each energy and location (p x number of
                   comparisons, maximum 1)

Input : RMSE of every impact (default: the reference results of the full dataset)
Output: article_analysis/output/statistics.xlsx
            sheet "table"   : mean ± SD of every method (over impacts), with
                              significance stars
            sheet "details" : one row per comparison (n, means, change, W, p)

Usage (from the main project folder):
    python article_analysis/statistics.py                            # reference results
    python article_analysis/statistics.py results/test_results.xlsx  # any file with the same columns
"""
import sys
from pathlib import Path

# make the shared code in the "common" folder importable
sys.path.append(str(Path(__file__).resolve().parents[1] / "common"))

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon

import config

BASELINE = "Raw"
COMPARED = ["LP"] + list(config.METHODS)        # LP, Method 1 ... Method 4
LOCATIONS = ["Front", "Front-oblique", "Side", "Rear-oblique"]


def significance(p):
    """Stars for a corrected p-value."""
    if np.isnan(p):
        return ""
    if p < 0.001:
        return "***"
    if p < 0.01:
        return "**"
    if p < 0.05:
        return "*"
    return "ns"


def groups(results):
    """(energy, location, rows) for every energy and location, plus 'All' locations."""
    for energy in sorted(results["energy_J"].unique()):
        same_energy = results[results["energy_J"] == energy]
        for location in LOCATIONS:
            rows = same_energy[same_energy["location"] == location]
            if len(rows) > 0:
                yield energy, location, rows
        yield energy, "All", same_energy


def compare_group(energy, location, rows):
    """Wilcoxon test of every method against Raw for one group of impacts."""
    # one value per trial: mean of the impacts of the same trial
    trials = rows.groupby(["location", "trial"])[[BASELINE] + COMPARED].mean()

    comparisons = []
    for method in COMPARED:
        test = wilcoxon(trials[method], trials[BASELINE], alternative="two-sided")
        comparisons.append({
            "energy_J": energy,
            "location": location,
            "method": method,
            "n_trials": len(trials),
            "n_impacts": len(rows),
            "Raw_mean": rows[BASELINE].mean(),
            "Raw_std": rows[BASELINE].std(),
            "mean": rows[method].mean(),
            "std": rows[method].std(),
            "change_pct": 100 * (rows[method].mean() - rows[BASELINE].mean()) / rows[BASELINE].mean(),
            "W": test.statistic,
            "p": test.pvalue,
        })

    # Bonferroni correction within the group
    for c in comparisons:
        c["p_corrected"] = min(1.0, c["p"] * len(COMPARED))
        c["significance"] = significance(c["p_corrected"])
    return comparisons


def summary_table(details):
    """One row per energy and location: 'mean ± SD' of every method, with stars."""
    rows = []
    for (energy, location), d in details.groupby(["energy_J", "location"], sort=False):
        first = d.iloc[0]
        row = {"energy_J": energy, "location": location,
               "n_trials": first["n_trials"], "n_impacts": first["n_impacts"],
               BASELINE: f"{first['Raw_mean']:.1f} ± {first['Raw_std']:.1f}"}
        for _, c in d.iterrows():
            stars = "" if c["significance"] == "ns" else " " + c["significance"]
            row[c["method"]] = f"{c['mean']:.1f} ± {c['std']:.1f}{stars}"
        rows.append(row)
    return pd.DataFrame(rows)


def main():
    input_file = sys.argv[1] if len(sys.argv) > 1 else config.REFERENCE_FILE
    results = pd.read_excel(input_file, sheet_name="per_impact")
    print(f"{len(results)} impacts read from {Path(input_file).name}\n")

    details = []
    for energy, location, rows in groups(results):
        details += compare_group(energy, location, rows)
    details = pd.DataFrame(details)
    table = summary_table(details)

    note = ("RMSE [deg/s], mean ± SD over impacts. Wilcoxon signed-rank test against Raw on trial "
            "means, two-sided, Bonferroni-corrected within each energy and location: "
            "* p<0.05, ** p<0.01, *** p<0.001; no star = not significant.")

    Path(config.STATISTICS_FILE).parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(config.STATISTICS_FILE) as writer:
        table.to_excel(writer, sheet_name="table", index=False)
        pd.DataFrame({"note": [note]}).to_excel(writer, sheet_name="table", index=False,
                                                header=False, startrow=len(table) + 2)
        rounded = details.round({"Raw_mean": 2, "Raw_std": 2, "mean": 2, "std": 2, "change_pct": 1})
        rounded.to_excel(writer, sheet_name="details", index=False)

    pd.set_option("display.width", 250)
    print(table.to_string(index=False))
    print("\n" + note)
    print(f"\nResults saved to {config.STATISTICS_FILE}")


if __name__ == "__main__":
    main()
