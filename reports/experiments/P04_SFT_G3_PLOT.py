"""Replot the recorded G3 CSV metrics with matplotlib==3.10.7."""

import argparse
import csv
from pathlib import Path

import matplotlib


def read_csv(path):
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path,
                        default=Path(__file__).with_name("p04-sft-g3"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    training = read_csv(args.data_dir / "training.csv")
    validation = read_csv(args.data_dir / "validation.csv")
    matplotlib.use("Agg")
    from matplotlib import pyplot as plt

    plt.rcParams.update({"font.size": 10, "svg.fonttype": "none"})
    fig, axes = plt.subplots(2, 2, figsize=(11, 7), constrained_layout=True)
    for row, (profile, title) in enumerate([
        ("smoke", "Qwen3-0.6B"), ("formal", "Qwen3-1.7B")
    ]):
        train = [v for v in training if v["profile"] == profile]
        values = [v for v in validation if v["profile"] == profile and v["kind"] == "sft"]
        original = next(v for v in validation
                        if v["profile"] == profile and v["kind"] == "original")
        selected = min(values, key=lambda v: (float(v["validation_ce"]), int(v["optimizer_step"])))
        ax = axes[row, 0]
        ax.plot([int(v["optimizer_step"]) for v in train],
                [float(v["mean_example_completion_ce"]) for v in train],
                color="#376795", linewidth=0.8)
        ax.set(title=title + " | training", ylabel="Mean example completion CE",
               xlabel="Optimizer update")
        ax = axes[row, 1]
        ax.plot([int(v["optimizer_step"]) for v in values],
                [float(v["validation_ce"]) for v in values],
                color="#277868", marker="o", markersize=4, label="SFT validation")
        ax.scatter([0], [float(original["validation_ce"])], color="#b96b27", marker="D",
                   s=40, label="Original checkpoint")
        ax.scatter([int(selected["optimizer_step"])], [float(selected["validation_ce"])],
                   color="#1b554a", marker="*", s=130, label="Selected SFT", zorder=4)
        ax.set_yscale("log")
        ax.set(title=title + " | full validation", ylabel="Token-weighted CE (log scale)",
               xlabel="Optimizer update")
        ax.legend(frameon=False, fontsize=8)
        for axis in axes[row]:
            axis.grid(axis="y", alpha=0.2)
            axis.spines[["top", "right"]].set_visible(False)
    fig.savefig(args.output, dpi=180)


if __name__ == "__main__":
    main()
