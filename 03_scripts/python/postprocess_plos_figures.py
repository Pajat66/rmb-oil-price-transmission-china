from __future__ import annotations

import csv
from pathlib import Path

from plos_figure_export import PLOS_DPI, PLOS_MAX_MB, normalize_plos_tiff


ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = ROOT / "04_results" / "figures_english"
SUBMISSION_DIR = ROOT / "04_results" / "figures_plos_submission"


# Fig1 is a manually prepared conceptual schematic and is intentionally
# excluded from automated figure conversion.
FIGURE_MAP = [
    {
        "fig_no": 2,
        "stem": "fig2_1_sample_coverage_english",
        "title": "Sample coverage.",
        "required": True,
    },
    {
        "fig_no": 3,
        "stem": "fig2_2_standardized_trend_lowess_english",
        "title": "Standardized trend and LOWESS smoothing.",
        "required": True,
    },
    {
        "fig_no": 4,
        "stem": "fig3_2_correlation_matrix_bar_english",
        "title": "Correlation structure of core variables.",
        "required": True,
    },
    {
        "fig_no": 5,
        "stem": "fig3_3_rolling_correlation_english",
        "title": "Rolling correlation.",
        "required": True,
    },
    {
        "fig_no": 6,
        "stem": "fig4_1_dlm_path_english",
        "title": "Distributed-lag coefficient paths.",
        "required": True,
    },
    {
        "fig_no": 7,
        "stem": "fig4_2_cumulative_effect_english",
        "title": "Cumulative effect.",
        "required": True,
    },
    {
        "fig_no": 8,
        "stem": "fig4_3_3d_effect_compare_english",
        "title": "3D comparison of dynamic effects.",
        "required": True,
    },
    {
        "fig_no": 9,
        "stem": "fig5_2_mechanism_3dbar_english",
        "title": "Mechanism 3D bar figure.",
        "required": True,
    },
    {
        "fig_no": 10,
        "stem": "fig6_2_lp_irf_band_english",
        "title": "Dynamic response band chart based on local projections.",
        "required": True,
    },
    {
        "fig_no": 11,
        "stem": "fig6_1_mantel_network_bubble_english",
        "title": "Mantel test correlation graph for imported inflation transmission.",
        "required": True,
    },
]


def find_source(stem: str | None) -> Path | None:
    if not stem:
        return None
    for suffix in (".png", ".tif", ".tiff"):
        candidate = SOURCE_DIR / f"{stem}{suffix}"
        if candidate.exists():
            return candidate
    return None


def main() -> int:
    SUBMISSION_DIR.mkdir(parents=True, exist_ok=True)

    rows = []
    missing = []
    warnings = []

    for item in FIGURE_MAP:
        fig_no = item["fig_no"]
        source = find_source(item["stem"])
        output = SUBMISSION_DIR / f"Fig{fig_no}.tif"

        if source is None:
            message = (
                f"Missing Fig{fig_no}: {item['title']} "
                "No independent source image was found in figures_english."
            )
            missing.append(message)
            rows.append({
                "figure": f"Fig{fig_no}",
                "title": item["title"],
                "source": "",
                "output": str(output),
                "status": "missing",
                "size_mb": "",
                "width_px": "",
                "height_px": "",
                "mode": "",
                "dpi": "",
                "warning": message,
            })
            print("WARNING:", message)
            continue

        result = normalize_plos_tiff(
            source,
            output,
            dpi=PLOS_DPI,
            max_mb=PLOS_MAX_MB,
        )
        if result["warning"]:
            warnings.append(result["warning"])
            print("WARNING:", result["warning"])

        rows.append({
            "figure": f"Fig{fig_no}",
            "title": item["title"],
            "source": str(source),
            "output": str(output),
            "status": "created",
            "size_mb": f"{result['size_mb']:.3f}",
            "width_px": result["width_px"],
            "height_px": result["height_px"],
            "mode": result["mode"],
            "dpi": result["dpi"],
            "warning": result["warning"],
        })
        print(
            f"Created {output.name} from {source.name}: "
            f"{result['width_px']}x{result['height_px']}px, "
            f"{result['mode']}, {result['size_mb']:.2f} MB"
        )

    manifest = SUBMISSION_DIR / "plos_figure_mapping.csv"
    with manifest.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nMapping report written to: {manifest}")
    if missing:
        print("\nMissing required figures:")
        for message in missing:
            print(f"- {message}")
    if warnings:
        print("\nSize or conversion warnings:")
        for message in warnings:
            print(f"- {message}")

    return 1 if missing or warnings else 0


if __name__ == "__main__":
    raise SystemExit(main())
