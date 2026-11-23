"""Journal-neutral style for future figures. This module does not load research data."""

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
import re
import warnings

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import to_rgb, to_rgba_array
from matplotlib.font_manager import FontProperties, findfont
from matplotlib.ft2font import FT2Font
from PIL import Image


# Lower-case keys preserve the interface of the supplied paper_style.py.
SERIES_COLORS = {
    "fuel": "#0072B2",
    "ppi": "#D55E00",
    "cpi": "#009E73",
    "oil": "#E69F00",
    "fx": "#56B4E9",
    "import": "#CC79A7",
}
SERIES_LINESTYLES = {
    "fuel": "-",
    "ppi": "--",
    "cpi": "-.",
    "oil": ":",
    "fx": (0, (5, 2, 1, 2, 1, 2)),
    "import": (0, (7, 3)),
}
SERIES_MARKERS = dict(zip(SERIES_COLORS, ("o", "s", "^", "D", "v", "P")))

# Coverage states are distinct from the fixed economic series identities.
AVAILABILITY = {
    "macro_levels": "#7CA3C4",
    "customs_levels": "#B98A56",
    "transformed": "#4A7298",
    "eligible_origin": "#1F3A5F",
    "outside": "#E9EDF1",
    "missing_edge": "#D55E00",
    "loss_firstdiff": "#E69F00",
    "loss_lag": "#CC79A7",
    "loss_truncation": "#D55E00",
}
LOSS_HATCH = {
    "loss_firstdiff": "...",
    "loss_lag": "///",
    "loss_truncation": r"\\",
    "missing": "xxx",
}

DOUBLE_COL = (7.0, 4.2)
SINGLE_COL = (3.5, 2.6)
CI_ALPHA = 0.16
ZERO_COLOR = "#4A4A4A"


@dataclass(frozen=True)
class JournalProfile:
    guide: str | None = None
    column_width_mm: tuple[float, float] | None = None
    bitmap_column_width_mm: tuple[float, float] | None = None
    panel_template: str = "({letter})"
    vector_format: str | None = None
    raster_format: str = "tiff"
    raster_dpi: int = 600
    min_stroke_pt: float = 0
    body_size_pt: float = 8.5


# Venue preferences are separate from project defaults. See FIGURE_STYLE_GUIDE.md.
JOURNAL_PROFILES = {
    "generic": JournalProfile(),
    "energies": JournalProfile(
        guide="https://www.mdpi.com/journal/energies/instructions",
        raster_format="png",
    ),
    "scientific_reports": JournalProfile(
        guide="https://www.nature.com/srep/author-instructions/submission-guidelines",
        panel_template="{letter}",
        vector_format="eps",
        raster_dpi=300,
        min_stroke_pt=1,
        body_size_pt=9,
    ),
    "hssc": JournalProfile(
        guide="https://www.nature.com/palcomms/author-instructions/submission-instructions",
        column_width_mm=(87.0, 180.0),
        bitmap_column_width_mm=(88.0, 180.0),
        panel_template="{letter}",
        vector_format="eps",
        raster_dpi=300,
        min_stroke_pt=1,
        body_size_pt=9,
    ),
}


def _profile(journal_profile):
    try:
        return JOURNAL_PROFILES[journal_profile]
    except KeyError as error:
        raise ValueError(f"Unknown journal profile: {journal_profile!r}") from error


def figure_size(columns=2, *, journal_profile="generic", artwork="vector", height=None):
    """Get final canvas size in inches; heights are project layout defaults."""
    if columns not in (1, 2):
        raise ValueError("columns must be 1 or 2")
    if artwork not in {"vector", "raster"}:
        raise ValueError("artwork must be 'vector' or 'raster'")
    profile = _profile(journal_profile)
    width, default_height = (SINGLE_COL, DOUBLE_COL)[columns - 1]
    widths = profile.column_width_mm
    if artwork == "raster" and profile.bitmap_column_width_mm is not None:
        widths = profile.bitmap_column_width_mm
    if widths is not None:
        width = widths[columns - 1] / 25.4
    return width, default_height if height is None else height


def apply_style(journal_profile="generic"):
    """Set Matplotlib style before creating figures; use rc_context for isolation."""
    import scienceplots  # noqa: F401  Registers the SciencePlots styles.

    profile = _profile(journal_profile)
    axis_width = max(0.65, profile.min_stroke_pt)
    plt.style.use(["science", "no-latex"])
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["DejaVu Sans", "Liberation Sans", "Arial"],
        "font.size": profile.body_size_pt,
        "mathtext.fontset": "dejavusans",
        "text.usetex": False,
        "text.color": "#171717",
        "axes.labelcolor": "#171717",
        "axes.labelsize": 9,
        "axes.labelpad": 5,
        "axes.titlesize": 9,
        "axes.titlepad": 7,
        "axes.unicode_minus": True,
        "axes.edgecolor": "#606460",
        "axes.linewidth": axis_width,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.prop_cycle": plt.cycler(color=list(SERIES_COLORS.values())),
        "axes.facecolor": "white",
        "axes.axisbelow": True,
        "axes.grid": True,
        "axes.grid.axis": "y",
        "axes.grid.which": "major",
        "grid.color": "#E4E7E5",
        "grid.linewidth": max(0.55, profile.min_stroke_pt),
        "grid.linestyle": "-",
        "xtick.direction": "out",
        "ytick.direction": "out",
        "xtick.top": False,
        "ytick.right": False,
        "xtick.minor.visible": False,
        "ytick.minor.visible": False,
        "xtick.major.width": axis_width,
        "ytick.major.width": axis_width,
        "xtick.labelsize": profile.body_size_pt,
        "ytick.labelsize": profile.body_size_pt,
        "lines.linewidth": 1.5,
        "lines.markersize": 4,
        "lines.markeredgewidth": max(0.7, profile.min_stroke_pt),
        "legend.fontsize": profile.body_size_pt,
        "legend.frameon": False,
        "legend.handlelength": 2.6,
        "figure.figsize": figure_size(journal_profile=journal_profile),
        "figure.facecolor": "white",
        "figure.autolayout": False,
        "figure.constrained_layout.use": True,
        "figure.constrained_layout.w_pad": 0.08,
        "figure.constrained_layout.h_pad": 0.08,
        "figure.constrained_layout.wspace": 0.08,
        "figure.constrained_layout.hspace": 0.08,
        "savefig.facecolor": "white",
        "savefig.bbox": None,
        "savefig.transparent": False,
        "pdf.fonttype": 42,
        "pdf.use14corefonts": False,
        "ps.fonttype": 42,
        "ps.useafm": False,
    })


PUBLICATION_FONTS = ("Arial", "Helvetica", "Liberation Sans")
PUBLICATION_INK = "#111111"


def publication_font(*, allow_fallback=False):
    """Resolve a real installed family for both normal and bold figure text."""
    symbols = {ord(c) for c in "AZaz09−%×Δ≤≥–·"}
    for family in PUBLICATION_FONTS:
        try:
            faces = [FT2Font(findfont(FontProperties(family=[family], weight=weight),
                                    fallback_to_default=False))
                     for weight in ("normal", "bold")]
        except ValueError:
            continue
        if all(face.family_name.casefold() == family.casefold()
               and symbols <= face.get_charmap().keys() for face in faces):
            return faces[0].family_name
    if not allow_fallback:
        raise ValueError("No complete Arial, Helvetica or Liberation Sans family is available.")
    font = FT2Font(findfont(FontProperties(family=["sans-serif"]))).family_name
    warnings.warn(f"Temporary figure font fallback: {font}", stacklevel=2)
    return font


def apply_style_v2(journal_profile="generic", *, base_size=8.5, allow_fallback=False):
    """Apply the publication style after the established SciencePlots base."""
    family = publication_font(allow_fallback=allow_fallback)
    apply_style(journal_profile)
    stroke = max(0.75, _profile(journal_profile).min_stroke_pt)
    plt.rcParams.update({
        "font.family": [family],
        "font.sans-serif": [family],
        "font.size": base_size,
        "mathtext.fontset": "custom",
        "mathtext.rm": family,
        "mathtext.it": f"{family}:italic",
        "mathtext.bf": f"{family}:bold",
        "mathtext.fallback": None,
        "text.color": PUBLICATION_INK,
        "axes.labelcolor": PUBLICATION_INK,
        "axes.titlecolor": PUBLICATION_INK,
        "xtick.color": PUBLICATION_INK,
        "ytick.color": PUBLICATION_INK,
        "legend.labelcolor": PUBLICATION_INK,
        "axes.edgecolor": ZERO_COLOR,
        "axes.labelsize": max(8.5, base_size),
        "axes.titlesize": 9.5,
        "axes.linewidth": stroke,
        "axes.formatter.use_mathtext": False,
        "xtick.major.width": stroke,
        "ytick.major.width": stroke,
        "xtick.labelsize": max(8, base_size - 0.5),
        "ytick.labelsize": max(8, base_size - 0.5),
        "legend.fontsize": max(8, base_size - 0.5),
        "svg.fonttype": "none",
    })
    return family


def tint(color, amount=0.72):
    """Mix a series color with the specified proportion of white."""
    if not 0 <= amount <= 1:
        raise ValueError("White mix must be between zero and one.")
    return tuple(channel + (1 - channel) * amount for channel in to_rgb(color))


def style_boxplot(artists, color, fill_amount=0.72, *, journal_profile="generic"):
    """Style a patch-artist boxplot without modifying statistical coordinates."""
    minimum = _profile(journal_profile).min_stroke_pt
    for patch in artists["boxes"]:
        patch.set(facecolor=tint(color, fill_amount), edgecolor=color, linewidth=1.1)
    for line in artists["whiskers"] + artists["caps"]:
        line.set(color=color, linewidth=1.0)
    for line in artists["medians"]:
        line.set(color="#000000", linewidth=1.3)
    for line in artists["fliers"]:
        line.set(marker="o", markersize=3.2, linestyle="none", markerfacecolor=color,
                 markeredgecolor=color, markeredgewidth=max(0.4, minimum))


def series_style(series, *, markevery=None):
    """Return stable line and marker settings for a named series."""
    key = series.lower()
    return {
        "color": SERIES_COLORS[key],
        "linestyle": SERIES_LINESTYLES[key],
        "marker": SERIES_MARKERS[key],
        "markevery": markevery,
    }


def interval_band(ax, series, x, lower, upper):
    """Draw supplied interval bounds. The caller owns interval semantics."""
    return ax.fill_between(
        x, lower, upper, color=SERIES_COLORS[series.lower()],
        alpha=CI_ALPHA, edgecolor="none", zorder=1.5,
    )


def zero_line(ax):
    """Draw the zero reference underneath estimates and above the grid."""
    width = max(0.8, plt.rcParams["axes.linewidth"])
    return ax.axhline(0, color=ZERO_COLOR, linewidth=width, zorder=1.8)


def panel_label(ax, letter, *, journal_profile="generic"):
    """Set a left-aligned lowercase panel identifier in the venue's form."""
    if not re.fullmatch("[a-z]", letter):
        raise ValueError("Panel letter must be a single lowercase ASCII letter")
    label = _profile(journal_profile).panel_template.format(letter=letter)
    return ax.set_title(label, loc="left", fontweight="bold")


def _has_partial_alpha(fig):
    """Detect transparency that the PostScript backend would flatten silently."""
    for artist in fig.findobj():
        if not artist.get_visible():
            continue
        alpha = artist.get_alpha()
        if alpha is not None:
            opacity = np.asarray(alpha)
            if np.any((opacity > 0) & (opacity < 1)):
                return True
        for getter in ("get_facecolor", "get_edgecolor", "get_color"):
            color = getattr(artist, getter, None)
            if color is None:
                continue
            opacity = to_rgba_array(color())[:, 3]
            if np.any((opacity > 0) & (opacity < 1)):
                return True
    return False


def _save_raster(fig, path, dpi, options):
    compression = {"compression": "tiff_lzw"} if path.suffix == ".tiff" else {}
    with BytesIO() as buffer:
        fig.savefig(buffer, format="png", dpi=dpi, **options)
        buffer.seek(0)
        with Image.open(buffer) as rendered:
            image = rendered if options["transparent"] else rendered.convert("RGB")
            image.save(path, dpi=(dpi, dpi), **compression)


def save_fig(fig, name, outdir="figures", tiff=False, *,
             journal_profile="generic", submission=False, artwork="vector",
             transparent=False, tight=False, preview_rgb=False):
    """Save PDF and 300 dpi PNG, plus explicitly requested submission assets.

    artwork selects the submission representation for line art or raster
    originals. tight changes the physical canvas and is off by default.
    Set preview_rgb=True for an opaque RGB preview.
    Returns a mapping from export role to file path.
    """
    profile = _profile(journal_profile)
    if artwork not in {"vector", "raster"}:
        raise ValueError("artwork must be 'vector' or 'raster'")
    if preview_rgb and transparent:
        raise ValueError("An RGB preview requires an opaque canvas.")
    needs_eps = submission and artwork == "vector" and profile.vector_format == "eps"
    if needs_eps and (transparent or _has_partial_alpha(fig)):
        raise ValueError(
            "EPS cannot preserve partial transparency. Keep the PDF master and "
            "use interval outlines or another verified opaque vector encoding for EPS."
        )

    folder = Path(outdir)
    folder.mkdir(parents=True, exist_ok=True)
    options = {
        "bbox_inches": "tight" if tight else None,
        "pad_inches": 0.08,
        "transparent": transparent,
        "facecolor": "none" if transparent else "white",
    }
    outputs = {"pdf": folder / f"{name}.pdf", "preview": folder / f"{name}.png"}
    with plt.rc_context({
        "savefig.bbox": None, "pdf.fonttype": 42, "pdf.use14corefonts": False,
        "ps.fonttype": 42, "ps.useafm": False,
    }):
        fig.savefig(outputs["pdf"], **options, metadata={"CreationDate": None})
        if preview_rgb:
            _save_raster(fig, outputs["preview"], 300, options)
        else:
            fig.savefig(outputs["preview"], dpi=300, **options)
        if tiff:
            outputs["tiff"] = folder / f"{name}.tiff"
            _save_raster(fig, outputs["tiff"], 600, options)
        if submission:
            mode = "eps" if needs_eps else profile.raster_format
            outputs["submission"] = folder / f"{name}_submission.{mode}"
            if needs_eps:
                fig.savefig(outputs["submission"], **options)
            else:
                submission_options = options
                if profile.guide is not None:
                    submission_options = {**options, "transparent": False, "facecolor": "white"}
                _save_raster(fig, outputs["submission"], profile.raster_dpi, submission_options)
    return outputs
