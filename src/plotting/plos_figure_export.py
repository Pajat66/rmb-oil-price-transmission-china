from __future__ import annotations

from pathlib import Path
from tempfile import NamedTemporaryFile

from PIL import Image


PLOS_DPI = 300
PLOS_MAX_MB = 10.0
PLOS_MAX_BYTES = int(PLOS_MAX_MB * 1024 * 1024)
PLOS_FONT_FAMILY = "Arial"
PLOS_MIN_FONT_PT = 8
PLOS_MAX_FONT_PT = 12


def _standardize_matplotlib_text(fig) -> None:
    """Keep Matplotlib text within PLOS-readable body-figure sizing."""
    try:
        from matplotlib.text import Text
    except Exception:
        return

    for artist in fig.findobj(match=Text):
        size = artist.get_fontsize()
        artist.set_fontsize(min(max(size, PLOS_MIN_FONT_PT), PLOS_MAX_FONT_PT))
        artist.set_fontfamily(PLOS_FONT_FAMILY)


def _white_background_rgb(image: Image.Image) -> Image.Image:
    """Return an RGB/grayscale image with alpha composited onto white."""
    if image.mode in ("RGBA", "LA") or (
        image.mode == "P" and "transparency" in image.info
    ):
        rgba = image.convert("RGBA")
        background = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
        background.alpha_composite(rgba)
        return background.convert("RGB")
    if image.mode == "CMYK":
        return image.convert("RGB")
    if image.mode in ("RGB", "L"):
        return image.copy()
    return image.convert("RGB")


def normalize_plos_tiff(
    source_path: str | Path,
    output_path: str | Path,
    dpi: int = PLOS_DPI,
    max_mb: float = PLOS_MAX_MB,
    min_long_edge_px: int = 1200,
) -> dict:
    """Convert an image to a single-page white-background LZW TIFF for PLOS upload.

    The function preserves the image meaning and aspect ratio. If LZW compression
    alone does not keep the output under the requested file-size limit, the pixel
    dimensions are reduced while the DPI metadata remains at the requested value.
    """
    source_path = Path(source_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with Image.open(source_path) as img:
        image = _white_background_rgb(img)

    max_bytes = int(max_mb * 1024 * 1024)
    scale = 1.0
    warning = ""
    attempts = 0

    while True:
        attempts += 1
        if scale < 1.0:
            width = max(1, int(round(image.width * scale)))
            height = max(1, int(round(image.height * scale)))
            candidate = image.resize((width, height), Image.Resampling.LANCZOS)
        else:
            candidate = image

        with NamedTemporaryFile(
            suffix=".tif",
            delete=False,
            dir=output_path.parent,
        ) as tmp:
            tmp_path = Path(tmp.name)

        try:
            candidate.save(
                tmp_path,
                format="TIFF",
                compression="tiff_lzw",
                dpi=(dpi, dpi),
                save_all=False,
            )
            size = tmp_path.stat().st_size
            if size <= max_bytes:
                tmp_path.replace(output_path)
                break

            long_edge = max(candidate.size)
            if long_edge <= min_long_edge_px:
                tmp_path.replace(output_path)
                warning = (
                    f"{output_path.name} remains above {max_mb:.1f} MB after "
                    f"LZW compression and resizing to {candidate.width}x{candidate.height}px."
                )
                break

            tmp_path.unlink(missing_ok=True)
            scale *= 0.90
        finally:
            if tmp_path.exists() and tmp_path != output_path:
                tmp_path.unlink(missing_ok=True)

    with Image.open(output_path) as final:
        mode = final.mode
        width, height = final.size
        dpi_info = final.info.get("dpi", (dpi, dpi))
        n_frames = getattr(final, "n_frames", 1)

    return {
        "source": str(source_path),
        "output": str(output_path),
        "width_px": width,
        "height_px": height,
        "dpi": dpi_info,
        "mode": mode,
        "size_mb": output_path.stat().st_size / 1024 / 1024,
        "attempts": attempts,
        "n_frames": n_frames,
        "warning": warning,
    }


def save_plos_figure(
    fig,
    output_path: str | Path,
    dpi: int = PLOS_DPI,
    preview_png: bool = True,
    pad_inches: float = 0.08,
    max_mb: float = PLOS_MAX_MB,
) -> dict:
    """Save a Matplotlib figure as PLOS-ready TIFF plus optional PNG preview."""
    output_path = Path(output_path)
    if output_path.suffix.lower() not in {".tif", ".tiff"}:
        output_path = output_path.with_suffix(".tif")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    _standardize_matplotlib_text(fig)

    preview_path = output_path.with_suffix(".png")
    temp_png = preview_path if preview_png else output_path.with_suffix(".plos_tmp.png")

    fig.savefig(
        temp_png,
        dpi=dpi,
        bbox_inches="tight",
        pad_inches=pad_inches,
        transparent=False,
        facecolor="white",
        edgecolor="white",
    )

    result = normalize_plos_tiff(temp_png, output_path, dpi=dpi, max_mb=max_mb)
    if not preview_png:
        temp_png.unlink(missing_ok=True)
    return result
