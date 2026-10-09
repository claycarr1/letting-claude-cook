"""Shared figure rules for every current figure (from 2026-10-08):

- text at least 12 pt (tick labels, axis labels, direct labels), panel titles 16 pt, the main
  title 18 pt;
- the main title is a plain-language takeaway sentence;
- no footnote in the image: setup details and caveats go in the figure's caption in report.md.
"""

TICK = 12
LABEL = 13
PANEL_TITLE = 16
TITLE = 18
MIN_TEXT = 12  # tests check that no visible text in a current figure is smaller than this


def title(fig, text: str):
    """The main title: a takeaway sentence, left-aligned, wrapped to the figure width. Dollar signs
    are escaped so matplotlib doesn't read two of them as maths."""
    import textwrap

    from decision_map import INK

    width_chars = int(fig.get_size_inches()[0] * 6.2)  # about 6 bold 18 pt characters per inch
    lines = [line for part in text.split("\n") for line in textwrap.wrap(part, width_chars)]
    fig.suptitle("\n".join(lines).replace("$", r"\$"), color=INK, fontsize=TITLE, x=0.01, ha="left", weight="bold")


def all_text(fig):
    """Every visible, non-empty Text artist in the figure (for the font-size tests)."""
    from matplotlib.text import Text

    return [t for t in fig.findobj(Text) if t.get_visible() and t.get_text().strip()]
