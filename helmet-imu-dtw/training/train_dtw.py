"""
TRAINING: computation of the DTW paths.

As only a subset of the dataset is provided in this repository, the training
cannot be reproduced here. The DTW paths computed on the full dataset are
provided in data/dtw_paths.json and are used by the test.

This script is not required to reproduce the test. It illustrates the
training procedure in general terms and can be applied to any dataset of
segmented impacts.

Input data
    helmet : array of shape (n_impacts, n_samples, 3)
             triaxial angular velocity measured by the helmet IMU
    head   : array of shape (n_impacts, n_samples, 3)
             triaxial angular velocity of the reference (e.g. headform)
    fs     : sampling frequency [Hz], common to both arrays

    The two arrays must have the same shape, with impact k of helmet paired
    with impact k of head. Any number of impacts and samples is accepted.

Example
    from train_dtw import train
    records = train(helmet, head, fs)

For each impact:
    1. helmet and headform angular velocities are projected on their principal
       rotation axis (PCA);
    2. the DTW path between helmet and headform is computed twice:
           "lowpass" : helmet signal low-pass filtered at 50 Hz (Methods 1 and 3)
           "raw"     : helmet signal as measured              (Methods 2 and 4)

Optional labels (location, energy_J, trial, impact: one value per impact) are
saved with each path. They are needed to group the paths into templates (see
METHODS in config.py) and for the leave-one-trial-out. If they are not given,
every impact is treated as a separate trial.

From the command line, with an .npz file containing "helmet", "head" and "fs"
(and optionally "location", "energy_J", "trial", "impact"):
    python training/train_dtw.py my_impacts.npz my_paths.json
"""
import json
import sys
from pathlib import Path

# make the shared code in the "common" folder importable
sys.path.append(str(Path(__file__).resolve().parents[1] / "common"))

import numpy as np

from dtw_core import dtw_path, low_pass, main_direction


def train(helmet, head, fs, location=None, energy_J=None, trial=None, impact=None):
    """DTW paths of all the impacts (two per impact: low-pass and raw)."""
    helmet = np.asarray(helmet, dtype=float)
    head = np.asarray(head, dtype=float)
    n_impacts = len(helmet)

    # labels not given: same placeholder for all, every impact its own trial
    if location is None:
        location = ["unknown"] * n_impacts
    if energy_J is None:
        energy_J = [0] * n_impacts
    if trial is None:
        trial = list(range(n_impacts))
    if impact is None:
        impact = [0] * n_impacts

    records = []
    for k in range(n_impacts):
        # 1. projection on the principal rotation axis (PCA)
        x = main_direction(helmet[k])        # helmet
        y = main_direction(head[k])          # headform (reference)

        # 2. DTW paths, with and without the low-pass filter on the helmet
        x_lp = low_pass(x, fs)
        for variant, x_variant in [("lowpass", x_lp), ("raw", x)]:
            records.append({
                "location": str(location[k]),
                "energy_J": int(energy_J[k]),
                "trial": int(trial[k]),
                "impact": int(impact[k]),
                "variant": variant,
                "path": dtw_path(x_variant, y),
            })
        print(f"  impact {k}: done")
    return records


def main():
    if len(sys.argv) != 3:
        print("Usage: python training/train_dtw.py my_impacts.npz my_paths.json")
        return

    data = np.load(sys.argv[1])
    helmet = data["helmet"]          # (n_impacts, n_samples, 3)
    head = data["head"]              # (n_impacts, n_samples, 3)
    fs = float(data["fs"])
    print(f"{len(helmet)} impacts, arrays of shape {helmet.shape}")

    # optional labels: used only if they are in the file
    location = data["location"] if "location" in data else None
    energy_J = data["energy_J"] if "energy_J" in data else None
    trial = data["trial"] if "trial" in data else None
    impact = data["impact"] if "impact" in data else None

    records = train(helmet, head, fs, location, energy_J, trial, impact)

    with open(sys.argv[2], "w") as f:
        json.dump(records, f)
    print(f"{len(records)} paths saved to {sys.argv[2]}")


if __name__ == "__main__":
    main()
