"""
TEST: reconstruct the helmet angular velocity of each impact with the four
methods in config.py and compare it with the headform (reference).

Inputs : data/impacts_subset.npz   segmented impacts (helmet and headform, 3D)
         data/dtw_paths.json       DTW paths of all the impacts of the full dataset
Output : results/test_results.xlsx RMSE of every impact (sheet "per_impact")
                                   and mean / SD per location and energy ("summary")

For each impact and method:
    1. the template is built from the paths of the same group (same location and
       energy, or same location only), leaving out the whole trial of the impact
       (leave-one-trial-out);
    2. the warping functions of these paths are averaged;
    3. the helmet signal is reconstructed on the headform time grid;
    4. the RMSE with the headform is computed on a 100-ms window.

Usage (from the main project folder):
    python testing/test_dtw.py
"""
import sys
from pathlib import Path

# make the shared code in the "common" folder importable
sys.path.append(str(Path(__file__).resolve().parents[1] / "common"))

import pandas as pd

import config
from dtw_core import reconstruct_impact, comparison_window, load_paths, read_impacts, rmse


def test_impact(impact, records):
    """RMSE of the raw, low-pass and reconstructed helmet signals for one impact."""
    fs = impact["fs"]
    signals = reconstruct_impact(impact, records)
    reference = comparison_window(signals.pop("Headform"), fs)

    result = {"location": impact["location"], "energy_J": impact["energy_J"],
              "trial": impact["trial"], "impact": impact["impact"]}
    for name, sig in signals.items():
        result[name] = rmse(comparison_window(sig, fs), reference)
    return result


def main():
    impacts = read_impacts(config.IMPACTS_FILE)
    records = load_paths(config.PATHS_FILE)
    print(f"{len(impacts)} impacts to test, {len(records)} DTW paths")

    results = pd.DataFrame([test_impact(imp, records) for imp in impacts])

    # mean and standard deviation for each location and energy
    columns = ["Raw", "LP"] + list(config.METHODS)
    summary = results.groupby(["location", "energy_J"])[columns].agg(["mean", "std"]).round(1)
    summary.columns = [f"{name}_{stat}" for name, stat in summary.columns]
    summary = summary.reset_index()
    pd.set_option("display.width", 200)
    print("\nRMSE [deg/s]:\n", summary.to_string(index=False))

    Path(config.RESULTS_FILE).parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(config.RESULTS_FILE) as writer:
        results.to_excel(writer, sheet_name="per_impact", index=False)
        summary.to_excel(writer, sheet_name="summary", index=False)
    print(f"\nResults saved to {config.RESULTS_FILE}")


if __name__ == "__main__":
    main()