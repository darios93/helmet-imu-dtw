"""
COMPARISON: check that the test reproduces the reference results.

The reference file (REFERENCE_FILE in config.py) contains the RMSE of every
impact of the full dataset. Each impact is identified by location, energy,
trial and impact number. The impacts tested in results/test_results.xlsx
(created by test_dtw.py) are looked up in this file with these four columns.

For each tested impact, the difference between the test RMSE and the
reference RMSE is printed for each column (Raw, LP, Method 1 ... Method 4).

Usage (from the main project folder, after running test_dtw.py):
    python testing/compare_results.py
"""
import sys
from pathlib import Path

# make the shared code in the "common" folder importable
sys.path.append(str(Path(__file__).resolve().parents[1] / "common"))

import pandas as pd

import config

KEYS = ["location", "energy_J", "trial", "impact"]   # columns identifying an impact


def main():
    test = pd.read_excel(config.RESULTS_FILE, sheet_name="per_impact")
    reference = pd.read_excel(config.REFERENCE_FILE, sheet_name="per_impact")

    # find the tested impacts in the reference results
    both = test.merge(reference, on=KEYS, suffixes=("_test", "_reference"))
    if len(both) != len(test):
        print("Some tested impacts were not found in the reference results.")
        return

    # difference test - reference for every impact and column
    columns = ["Raw", "LP"] + list(config.METHODS)
    differences = both[KEYS].copy()
    for name in columns:
        differences[name] = both[name + "_test"] - both[name + "_reference"]

    pd.set_option("display.width", 200)
    pd.set_option("display.float_format", "{:.2e}".format)
    print("Difference between test and reference RMSE for each impact [deg/s]:\n")
    print(differences.to_string(index=False))


if __name__ == "__main__":
    main()