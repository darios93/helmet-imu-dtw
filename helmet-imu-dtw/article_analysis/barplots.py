"""
BAR PLOTS: mean RMSE (± SD) of every method, for each impact location.

One figure per impact energy. In each figure, one group of bars per location,
one bar per method (Raw, LP, Method 1 ... Method 4). All figures have the same
size and the same y-axis range, to be compared directly.

Input : RMSE of every impact (default: the reference results of the full dataset)
Output: article_analysis/output/barplot_33J.png, barplot_79J.png

Usage (from the main project folder):
    python article_analysis/barplots.py                            # reference results
    python article_analysis/barplots.py results/test_results.xlsx  # any file with the same columns
"""
import sys
from pathlib import Path

# make the shared code in the "common" folder importable
sys.path.append(str(Path(__file__).resolve().parents[1] / "common"))

import matplotlib
matplotlib.use("Agg")            # save the images without opening windows
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import config

LOCATIONS = ["Front", "Front-oblique", "Side", "Rear-oblique"]

# method -> (legend label, colour)
# grey: no DTW; blue: template by location and energy (Methods 1-2);
# orange: template by location (Methods 3-4); darker colour: low-pass filtered
METHODS = {
    "Raw":      ("Raw",      "#bdbdbd"),
    "LP":       ("LP 50 Hz", "#757575"),
    "Method 1": ("Method 1", "#2171b5"),
    "Method 2": ("Method 2", "#9ecae1"),
    "Method 3": ("Method 3", "#d94801"),
    "Method 4": ("Method 4", "#fdae6b"),
}

# figure layout [inches], the same for every figure
WIDTH_PER_LOCATION = 2.4
AXES_HEIGHT = 3.6
MARGIN_LEFT, MARGIN_RIGHT, MARGIN_BOTTOM, MARGIN_TOP = 0.9, 0.2, 0.75, 1.15
FONTSIZE = 12
DPI = 300


def plot_energy(summary, energy, n_slots, ymax):
    """Bar plot of one energy. n_slots: number of locations of the widest figure."""
    s = summary[summary["energy_J"] == energy].set_index("location")
    locations = [loc for loc in LOCATIONS if loc in s.index]

    # figure with a fixed size, the same for every energy
    axes_width = WIDTH_PER_LOCATION * n_slots
    fig_width = MARGIN_LEFT + axes_width + MARGIN_RIGHT
    fig_height = MARGIN_BOTTOM + AXES_HEIGHT + MARGIN_TOP
    fig = plt.figure(figsize=(fig_width, fig_height))
    ax = fig.add_axes([MARGIN_LEFT / fig_width, MARGIN_BOTTOM / fig_height,
                       axes_width / fig_width, AXES_HEIGHT / fig_height])

    # one group of bars per location, one bar per method
    x = np.arange(len(locations))
    width = 0.8 / len(METHODS)
    for k, (method, (label, color)) in enumerate(METHODS.items()):
        offset = (k - (len(METHODS) - 1) / 2) * width
        ax.bar(x + offset, s.loc[locations, (method, "mean")], width * 0.9,
               yerr=s.loc[locations, (method, "std")], color=color, label=label,
               capsize=2, error_kw={"elinewidth": 0.8, "ecolor": "#333333"})

    labels = [f"{loc}\n(n = {int(s.loc[loc, ('Raw', 'count')])})" for loc in locations]
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_xlim(-0.5, len(locations) - 0.5)
    ax.set_ylim(0, ymax)
    ax.set_ylabel("RMSE [deg/s]", fontsize=FONTSIZE)
    ax.set_title(f"Impact energy {energy} J", fontsize=FONTSIZE, pad=8)
    ax.yaxis.grid(True, linestyle="--", alpha=0.4)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(axis="both", labelsize=FONTSIZE - 1)

    # legend above the title, in two rows
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0 + 0.32 / AXES_HEIGHT), ncol=3,
              frameon=False, fontsize=FONTSIZE - 1, columnspacing=1.2)
    return fig


def main():
    input_file = sys.argv[1] if len(sys.argv) > 1 else config.REFERENCE_FILE
    results = pd.read_excel(input_file, sheet_name="per_impact")
    print(f"{len(results)} impacts read from {Path(input_file).name}")

    # mean, SD and number of impacts for every energy, location and method
    summary = results.groupby(["energy_J", "location"])[list(METHODS)].agg(["mean", "std", "count"])
    summary = summary.reset_index()

    # common y-axis maximum: largest mean + SD, rounded up to a multiple of 50
    top = max((summary[(m, "mean")] + summary[(m, "std")]).max() for m in METHODS)
    ymax = 50 * np.ceil(1.05 * top / 50)

    energies = sorted(summary["energy_J"].unique())
    n_slots = max((summary["energy_J"] == e).sum() for e in energies)

    for energy in energies:
        fig = plot_energy(summary, energy, n_slots, ymax)
        path = Path(str(config.BARPLOT_FILE).format(energy=energy))
        path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, dpi=DPI)
        plt.close(fig)
        print(f"  {path.name} saved (y axis 0-{ymax:g} deg/s)")


if __name__ == "__main__":
    main()
