"""
Settings shared by the scripts of this repository.
All values are the ones used to obtain the reference results.
"""
from pathlib import Path

# ----------------------------------------------------------------------------
# Files (relative to the main project folder)
# ----------------------------------------------------------------------------
PROJECT = Path(__file__).resolve().parents[1]

# Segmented impacts to test (see README.md)
IMPACTS_FILE = PROJECT / "data" / "impacts_subset.npz"

# DTW optimal alignment paths of all the impacts of the full dataset
PATHS_FILE = PROJECT / "data" / "dtw_paths.json"

# Reference RMSE of every impact of the full dataset (for the comparison)
REFERENCE_FILE = PROJECT / "reference_results" / "DTW_results.xlsx"

# Outputs
RESULTS_FILE = PROJECT / "results" / "test_results.xlsx"

# Outputs of the article analysis (statistics and bar plots)
STATISTICS_FILE = PROJECT / "article_analysis" / "output" / "statistics.xlsx"
BARPLOT_FILE = PROJECT / "article_analysis" / "output" / "barplot_{energy}J.png"   # one per energy

# ----------------------------------------------------------------------------
# Signal processing
# ----------------------------------------------------------------------------
# Low-pass filter applied to the helmet signal (Methods 1 and 3, and "LP" alone)
LOWPASS_HZ = 50
FILTER_ORDER = 2          # Butterworth filter, applied forward and backward (zero phase)

# Impact onset: the first peak is the first local maximum above a fraction of the
# absolute peak; the onset is where the signal crosses 5% of that first peak.
ONSET_LEVEL = 0.05

# Comparison window: 0.01 s before and 0.09 s after the onset
WINDOW_PRE_S = 0.01
WINDOW_POST_S = 0.09
WINDOW_PEAK_FRACTION = 0.1   # first-peak threshold used to find the onset of this window

# ----------------------------------------------------------------------------
# Reconstruction methods
#   group   : training impacts averaged into the template
#             "location_energy" -> same impact location and same energy
#             "location"        -> same impact location, both energies
#   lowpass : True if the helmet signal is low-pass filtered
# ----------------------------------------------------------------------------
METHODS = {
    "Method 1": {"group": "location_energy", "lowpass": True},
    "Method 2": {"group": "location_energy", "lowpass": False},
    "Method 3": {"group": "location", "lowpass": True},
    "Method 4": {"group": "location", "lowpass": False},
}
