"""
Functions shared by the testing and training scripts.

Notation:
    x    : helmet signal,   indexed by i
    y    : reference signal (headform), indexed by j
    path : DTW optimal alignment path, a list of (i, j) index pairs
"""
import json

import numpy as np
from scipy.signal import butter, filtfilt
from sklearn.decomposition import PCA

import config


# =============================================================================
# 1. Reading the data
# =============================================================================
def read_impacts(npz_file):
    """
    Read an .npz file of segmented impacts.

    The file contains (n = number of impacts, N = samples per impact):
        helmet    (n, N, 3)  helmet angular velocity, x y z [deg/s]
        head      (n, N, 3)  reference angular velocity, x y z [deg/s]
        location  (n,)       impact location
        energy_J  (n,)       impact energy [J]
        trial     (n,)       trial number (within each location and energy)
        impact    (n,)       impact number within the trial
        fs        ()         sampling frequency [Hz]

    Returns a list of dictionaries, one per impact.
    """
    data = np.load(npz_file)
    impacts = []
    for k in range(len(data["helmet"])):
        impacts.append({
            "location": str(data["location"][k]),
            "energy_J": int(data["energy_J"][k]),
            "trial": int(data["trial"][k]),
            "impact": int(data["impact"][k]),
            "fs": float(data["fs"]),
            "helmet": data["helmet"][k],
            "head": data["head"][k],
        })
    return impacts


def load_paths(json_file):
    """Read a .json file of DTW paths (list of records, one per path)."""
    with open(json_file) as f:
        return json.load(f)


# =============================================================================
# 2. Signal processing
# =============================================================================
def main_direction(gyr):
    """
    Project a 3D angular velocity (N, 3) on its principal rotation axis,
    i.e. the first principal component (PCA). Returns a 1D signal.

    The direction (sign) of a principal axis is arbitrary, and different
    versions of scikit-learn choose it differently. The sign is therefore set
    explicitly: the centred projection must be positive at its largest
    absolute value. This makes the result independent of the library version.
    """
    pca = PCA(n_components=3).fit(gyr)
    first_axis = pca.components_[0, :]

    scores = (gyr - pca.mean_) @ first_axis
    if scores[np.argmax(np.abs(scores))] < 0:
        first_axis = -first_axis
    return gyr @ first_axis


def low_pass(x, fs, cutoff=config.LOWPASS_HZ, order=config.FILTER_ORDER):
    """Zero-phase Butterworth low-pass filter."""
    b, a = butter(order, cutoff / (fs / 2), btype="low")
    return filtfilt(b, a, x)


def find_onset(x, peak_fraction):
    """
    Impact onset of a 1D signal.

    1. The baseline (mean of the first 10 samples) is removed.
    2. The first peak is the first local maximum larger than
       peak_fraction * absolute peak (if none, the absolute peak is used).
    3. Going backwards from the first peak, the onset is the first sample
       below ONSET_LEVEL (fraction of the peak value, see config.py).
    """
    x = x - np.mean(x[:10])

    # first local maximum above the threshold, before the absolute peak
    i_max = int(np.argmax(x))
    first_peak = i_max
    for i in range(1, i_max):
        is_local_max = x[i - 1] < x[i] > x[i + 1]
        if is_local_max and x[i] > peak_fraction * x[i_max]:
            first_peak = i
            break

    # walk backwards from the first peak until the signal falls below the level
    level = config.ONSET_LEVEL * np.max(x[:first_peak + 1])
    for k in range(first_peak, -1, -1):
        if x[k] <= level:
            return k
    return 0


def comparison_window(x, fs):
    """
    Cut x around its own onset, from WINDOW_PRE_S before to WINDOW_POST_S
    after it (see config.py). This window is used for the RMSE.
    """
    onset = find_onset(x, config.WINDOW_PEAK_FRACTION)
    start = max(onset - int(fs * config.WINDOW_PRE_S), 0)
    return x[start: onset + int(fs * config.WINDOW_POST_S)]


def rmse(a, b):
    """Root mean square error between two signals (cut to the same length)."""
    n = min(len(a), len(b))
    return float(np.sqrt(np.mean((a[:n] - b[:n]) ** 2)))


# =============================================================================
# 3. DTW path (used for training)
# =============================================================================
def dtw_path(x, y):
    """DTW optimal alignment path between helmet x and reference y: list of (i, j) pairs."""
    from dtaidistance import dtw
    _, cost_matrix = dtw.warping_paths(x, y, use_c=False)
    return [(int(i), int(j)) for i, j in dtw.best_path(cost_matrix)]


# =============================================================================
# 4. DTW templates and reconstruction
# =============================================================================
def warping_function(path):
    """
    Warping function of one DTW path: for every reference sample j, the mean
    of the helmet indices i matched to it by the path.
    """
    n_head = max(j for i, j in path) + 1     # number of reference samples
    sums = np.zeros(n_head)                  # sum of the helmet indices matched to each j
    counts = np.zeros(n_head)                # how many helmet indices are matched to each j
    for i, j in path:
        sums[j] += i
        counts[j] += 1
    return sums / counts                     # DTW matches every j at least once


def average_warping(paths):
    """
    Template: average of the warping functions of the training paths, sample
    by sample. If the reference windows differ in length, the common part is used.
    """
    warps = [warping_function(p) for p in paths]
    n = min(len(w) for w in warps)
    return np.mean([w[:n] for w in warps], axis=0)


def reconstruct(x, w_mean, n_out):
    """
    Reconstructed helmet signal on the reference time grid (n_out samples).
    x is read at the (non-integer) positions w_mean, with linear interpolation
    between adjacent helmet samples.
    """
    # If the template is shorter than the reference window (rare), extend it by
    # one helmet sample per reference sample.
    while len(w_mean) < n_out:
        w_mean = np.append(w_mean, w_mean[-1] + 1)
    positions = w_mean[:n_out]

    # value of x at each position, by linear interpolation between samples
    sample_numbers = np.arange(len(x))
    return np.interp(positions, sample_numbers, x)


def training_paths(records, impact, method):
    """
    Paths used to build the template of one method for one impact:
    same group (location and energy, or location only), same variant
    (low-pass or raw), and NOT from the trial of the impact (leave-one-trial-out).
    A trial is identified by location, energy and trial number.
    """
    variant = "lowpass" if method["lowpass"] else "raw"
    selected = []
    for r in records:
        same_group = r["location"] == impact["location"]
        if method["group"] == "location_energy":
            same_group = same_group and r["energy_J"] == impact["energy_J"]
        same_trial = (r["location"] == impact["location"]
                      and r["energy_J"] == impact["energy_J"]
                      and r["trial"] == impact["trial"])
        if same_group and r["variant"] == variant and not same_trial:
            selected.append(r["path"])
    return selected


def reconstruct_impact(impact, records):
    """
    Reconstruct the helmet signal of one impact with each method in config.METHODS.

    Inputs:
        impact  : one impact (dictionary from read_impacts), with its 3D helmet
                  and reference angular velocities
        records : DTW paths used for training (from load_paths)

    Steps:
        1. helmet (x) and reference (y) are projected on their principal
           rotation axis (PCA); x is also low-pass filtered (x_lp);
        2. for each method:
           a. select the training paths: same group and variant, NOT from the
              trial of this impact (leave-one-trial-out)    -> training_paths
           b. average their warping functions (template)    -> average_warping
           c. apply the template to the helmet signal       -> reconstruct

    Output: dictionary of 1D signals, all on the principal rotation axis:
        "Headform"            : reference
        "Raw"                 : helmet, as measured (no DTW)
        "LP"                  : helmet, low-pass filtered (no DTW)
        "Method 1" ... "Method 4" : helmet reconstructed with each method
    """
    fs = impact["fs"]

    # 1. projection on the principal rotation axis, and low-pass filter
    x = main_direction(impact["helmet"])     # helmet
    y = main_direction(impact["head"])       # reference
    x_lp = low_pass(x, fs)

    signals = {"Headform": y, "Raw": x, "LP": x_lp}

    # 2. reconstruction with each method
    for name, method in config.METHODS.items():
        paths = training_paths(records, impact, method)      # a. training paths
        w_mean = average_warping(paths)                      # b. template
        x_in = x_lp if method["lowpass"] else x              #    filtered or raw helmet
        signals[name] = reconstruct(x_in, w_mean, len(y))    # c. reconstructed helmet
    return signals