"""Exact conditional count comparisons; no exposure or causal interpretation."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parents[1] / "ml-dependencies"))
from scipy.stats import binomtest


def compare(x, y):
    if x + y == 0:
        return dict(ratio=None, low=None, high=None, p=1.0)
    test = binomtest(y, x + y, p=0.5)
    ci = test.proportion_ci(confidence_level=0.95, method="exact")
    return dict(ratio=y / x if x else None,
                low=ci.low / (1 - ci.low) if ci.low < 1 else None,
                high=ci.high / (1 - ci.high) if ci.high < 1 else None,
                p=float(test.pvalue))


def holm(ps):
    result = [0.0] * len(ps)
    previous = 0
    for rank, i in enumerate(sorted(range(len(ps)), key=lambda i: ps[i])):
        previous = max(previous, min(1, (len(ps) - rank) * ps[i]))
        result[i] = previous
    return result


def main():
    data = json.loads((ROOT / "dist/data/explorer.json").read_text())
    labels = json.loads((ROOT / "dist/data/labels.json").read_text())
    cols = {k: i for i, k in enumerate(data["columns"])}
    rows = []
    for i, age in enumerate(labels["age"]):
        counts = [sum(r[cols["n"]] for r in data["rows"]
                      if r[cols["year"]] == year and r[cols["age"]] == i and r[cols["severity"]] == 1)
                  for year in (2024, 2025)]
        rows.append(dict(age=age, before=counts[0], after=counts[1],
                         **compare(*counts)))
    for row, adjusted in zip(rows, holm([r["p"] for r in rows])):
        row["p_holm"] = adjusted
    out = dict(scope="2024 versus 2025; motorcycle riders and passengers; all capacities; Great Britain",
               method="Exact conditional Poisson count-ratio interval (95%); two-sided binomial test; Holm adjustment across all nine age categories including unknown age.",
               assumptions="Independent Poisson counts and equal one-year observation periods. Casualties in the same collision may be correlated. No adjustment for mileage, demographics, reporting bias or confounding. Intervals are individual, not simultaneous.",
               rows=rows)
    (ROOT / "dist/data/uncertainty.json").write_text(json.dumps(out, indent=2, allow_nan=False))
    # Numerical edge cases and adjustment checks.
    assert compare(20, 20)["p"] == 1
    assert compare(0, 0)["ratio"] is None
    assert compare(0, 5)["high"] is None
    assert compare(5, 0)["low"] == 0
    assert holm([0.01, 0.04, 0.03]) == [0.03, 0.06, 0.06]
    annual = json.loads((ROOT / "dist/data/annual.json").read_text())
    for year, key in [(2024, "before"), (2025, "after")]:
        assert sum(r[key] for r in rows) == next(r["fatal"] for r in annual if r["year"] == year)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
