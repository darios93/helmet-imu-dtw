# helmet-imu-dtw

Dynamic Time Warping (DTW) reconstruction of head angular velocity from a single
helmet-mounted Inertial Measurement Unit (IMU).

This repository contains the code for the article (currently under review):

> D. Sciacca, J.-P. Thiran, A. Ionescu, "Dynamic Time Warping for Ice Hockey Impact
> Kinematics: Addressing Helmet–Head Decoupling in Single-IMU Angular Velocity Signals",
> IEEE Open Journal of Engineering in Medicine and Biology (2026).

A subset of 28 impacts is included to run the test and to verify that the results
match the reference values. The reference results of the full dataset are also
provided, together with the scripts for the statistical analysis and the bar plots.

## Overview

During an impact, the helmet can move relative to the head, and the angular velocity
measured by a helmet IMU therefore differs from the true head motion. The method corrects the
helmet signal using DTW templates learned from paired helmet and headform recordings.

**Pipeline**

1. **Projection** – the 3D angular velocities of helmet and headform are projected on
   their principal rotation axis (PCA), giving one signal each.
2. **Training** – for each training impact, DTW finds the optimal alignment (path)
   between the helmet and headform signals.
3. **Template** – the paths of similar impacts (same location, with or without the same
   energy) are averaged into a time-warping template.
4. **Reconstruction** – the template is applied to a new helmet signal to map it onto the
   headform time scale.
5. **Evaluation** – the reconstructed signal is compared with the headform using the
   root mean square error (RMSE) over a 100-ms window around the impact onset.

The templates are built with a **leave-one-trial-out** approach: the trial of the impact
under test is never used to build its template.

**Methods compared**

| Method | Template built from | Helmet signal |
|---|---|---|
| Method 1 | same location and energy | low-pass filtered (50 Hz) |
| Method 2 | same location and energy | raw |
| Method 3 | same location, both energies | low-pass filtered (50 Hz) |
| Method 4 | same location, both energies | raw |

The unprocessed helmet signal (Raw) and the low-pass filtered signal without DTW (LP) are
also reported as baselines.

## Repository structure

```
helmet-imu-dtw/
├── common/
│   ├── config.py             settings (files, filter, comparison window, methods)
│   └── dtw_core.py           shared functions (PCA, filter, onset, DTW, reconstruction, RMSE)
├── testing/
│   ├── test_dtw.py           reconstruction and RMSE of every impact
│   └── compare_results.py    comparison with the reference results
├── training/
│   └── train_dtw.py          computation of the DTW paths (general example)
├── data/
│   ├── impacts_subset.npz    28 impacts (helmet and headform, 3D)
│   └── dtw_paths.json        DTW paths computed on the full dataset
├── article_analysis/
│   ├── statistics.py         statistical comparison of the methods (Wilcoxon test)
│   ├── barplots.py           bar plots of the RMSE per location and energy
│   └── output/               created by the two scripts
├── reference_results/
│   └── DTW_results.xlsx  reference RMSE of every impact of the full dataset
└── requirements.txt
```

## Data

**`data/impacts_subset.npz`** – 28 segmented impacts, sampled at 512 Hz.

| Array | Shape | Content |
|---|---|---|
| `helmet` | (28, 127, 3) | helmet angular velocity x, y, z [deg/s] |
| `head` | (28, 127, 3) | headform angular velocity x, y, z [deg/s] |
| `location` | (28,) | Front, Front-oblique, Side, Rear-oblique |
| `energy_J` | (28,) | impact energy, 33 or 79 J |
| `trial` | (28,) | trial number (within each location and energy) |
| `impact` | (28,) | impact number within the trial |
| `fs` | () | sampling frequency [Hz] |

**`data/dtw_paths.json`** – the DTW paths of all the impacts of the full dataset (sample
index pairs only, no signals), with location, energy, trial and impact number.

**`reference_results/DTW_results.xlsx`** – the reference RMSE of every impact of the
full dataset, for Raw, LP and Methods 1–4.

## Training

As only a subset of the dataset is provided, the full training cannot be reproduced here.
The DTW paths computed on the full dataset are provided in `data/dtw_paths.json` and
are used directly by the test.

`training/train_dtw.py` is not required to reproduce the results. It shows how the
paths are computed and can be applied to any dataset given as two 3D arrays of shape
(n_impacts, n_samples, 3), one for the helmet and one for the reference:

```python
from train_dtw import train
records = train(helmet, head, fs)
```

or from the command line:

```
python training/train_dtw.py my_impacts.npz my_paths.json
```

## Installation

Python 3.8–3.10 is required by the package versions listed in `requirements.txt`.

```
pip install -r requirements.txt
```

## Usage

Run the scripts from the `helmet-imu-dtw` folder:

```
python testing/test_dtw.py               # 1. test
python testing/compare_results.py        # 2. comparison with the reference results
python article_analysis/statistics.py    # 3. statistical analysis
python article_analysis/barplots.py      # 4. bar plots
```

1. **Test** – reconstructs each of the 28 impacts with Methods 1–4 and saves the RMSE in
   `results/test_results.xlsx` (one row per impact, plus mean and SD per location and energy).
2. **Comparison** – finds each tested impact in the reference file (by location, energy,
   trial and impact) and prints, for each impact, the difference between the test and the
   reference RMSE. Differences close to zero (about 1e-13 deg/s, numerical precision)
   confirm that the results are reproduced.
3. **Statistical analysis** – using the reference results of the full dataset, compares
   LP and Methods 1–4 with the raw signal for each energy and location (and all locations
   pooled). Wilcoxon signed-rank test, paired, two-sided, on trial means (impacts of the
   same trial are averaged), with Bonferroni correction within each energy and location.
   The table (mean ± SD with significance) and the details of every comparison are saved
   in `article_analysis/output/statistics.xlsx`.
4. **Bar plots** – mean RMSE (± SD) of every method for each location, one figure per
   energy, saved as `article_analysis/output/barplot_33J.png` and `barplot_79J.png`.

Both analysis scripts use the reference results by default; another file with the same
columns can be given as argument (e.g. `python article_analysis/statistics.py results/test_results.xlsx`).
