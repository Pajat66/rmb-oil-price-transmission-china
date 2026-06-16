from __future__ import annotations

import csv
from pathlib import Path

from PIL import Image

from plos_figure_export import PLOS_DPI, PLOS_MAX_MB


ROOT = Path(__file__).resolve().parents[2]
SUBMISSION_DIR = ROOT / "04_results" / "figures_plos_submission"
REPORT_FILE = SUBMISSION_DIR / "plos_figure_check_report.csv"


def has_alpha(image: Image.Image) -> bool:
    if image.mode in ("RGBA", "LA"):
        return True
    return image.mode == "P" and "transparency" in image.info


def dpi_tuple(image: Image.Image) -> tuple[float, float]:
    dpi = image.info.get("dpi", (0, 0))
    if isinstance(dpi, (int, float)):
        return float(dpi), float(dpi)
    if len(dpi) < 2:
        return 0.0, 0.0
    return float(dpi[0] or 0), float(dpi[1] or 0)


def check_file(path: Path) -> dict:
    size_mb = path.stat().st_size / 1024 / 1024
    is_tiff_ext = path.suffix.lower() in {".tif", ".tiff"}

    try:
        with Image.open(path) as img:
            fmt = img.format or ""
            width, height = img.size
            mode = img.mode
            alpha = has_alpha(img)
            xdpi, ydpi = dpi_tuple(img)
            n_frames = getattr(img, "n_frames", 1)
    except Exception as exc:
        return {
            "file_name": path.name,
            "file_format": "ERROR",
            "file_size_mb": f"{size_mb:.3f}",
            "width_px": "",
            "height_px": "",
            "dpi": "",
            "color_mode": "",
            "has_alpha_channel": "",
            "is_tiff": is_tiff_ext,
            "passes_size_10mb": size_mb <= PLOS_MAX_MB,
            "passes_rgb_or_grayscale": False,
            "passes_no_alpha": False,
            "passes_dpi": False,
            "passes_single_page": False,
            "overall_pass": False,
            "notes": str(exc),
        }

    passes_tiff = is_tiff_ext and fmt.upper() == "TIFF"
    passes_size = size_mb <= PLOS_MAX_MB
    passes_mode = mode in {"RGB", "L"}
    passes_alpha = not alpha
    passes_dpi = xdpi >= PLOS_DPI and ydpi >= PLOS_DPI
    passes_single_page = n_frames == 1
    overall = (
        passes_tiff
        and passes_size
        and passes_mode
        and passes_alpha
        and passes_dpi
        and passes_single_page
    )

    notes = []
    if not passes_tiff:
        notes.append("not TIFF")
    if not passes_size:
        notes.append("above 10 MB")
    if not passes_mode:
        notes.append("not RGB/grayscale")
    if not passes_alpha:
        notes.append("alpha channel present")
    if not passes_dpi:
        notes.append("DPI below 300")
    if not passes_single_page:
        notes.append("multi-page TIFF")

    return {
        "file_name": path.name,
        "file_format": fmt,
        "file_size_mb": f"{size_mb:.3f}",
        "width_px": width,
        "height_px": height,
        "dpi": f"{xdpi:.0f}x{ydpi:.0f}",
        "color_mode": mode,
        "has_alpha_channel": alpha,
        "is_tiff": passes_tiff,
        "passes_size_10mb": passes_size,
        "passes_rgb_or_grayscale": passes_mode,
        "passes_no_alpha": passes_alpha,
        "passes_dpi": passes_dpi,
        "passes_single_page": passes_single_page,
        "overall_pass": overall,
        "notes": "; ".join(notes),
    }


def main() -> int:
    SUBMISSION_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(SUBMISSION_DIR.glob("Fig*.tif"))
    rows = [check_file(path) for path in files]

    fieldnames = [
        "file_name",
        "file_format",
        "file_size_mb",
        "width_px",
        "height_px",
        "dpi",
        "color_mode",
        "has_alpha_channel",
        "is_tiff",
        "passes_size_10mb",
        "passes_rgb_or_grayscale",
        "passes_no_alpha",
        "passes_dpi",
        "passes_single_page",
        "overall_pass",
        "notes",
    ]

    with REPORT_FILE.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Checked {len(rows)} figure file(s).")
    print(f"Report written to: {REPORT_FILE}")

    failed = [row for row in rows if not row["overall_pass"]]
    if failed:
        print("\nFigures that did not pass:")
        for row in failed:
            print(f"- {row['file_name']}: {row['notes']}")
        return 1

    print("All checked figure files passed the PLOS ONE export checks.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
