"""Qt adapter (PySide6): palette, fonts, style sheet and status tags for Equity Recorder.

    from PySide6.QtWidgets import QApplication
    from onedesk import qt_theme, status

    app = QApplication(sys.argv)
    theme = qt_theme.apply(app, mode="light")       # "dark" or "auto" (follows Windows)
    badge = theme.tag(status.live("paper"))         # a QLabel showing ● LIVE paper
    theme.set_tag(badge, status.offline())          # change it later; mode switches restyle it
    theme.style_table(table)                        # numbers in Cascadia Mono, caps column heads
    theme.on_mode_change(lambda t: table.viewport().update())
    theme.set_mode("dark")                          # live switch

How it works:

* Fusion style. Qt's Windows styles ignore most palette colors; Fusion draws
  everything from the palette.
* A QPalette from the tokens, plus one application style sheet for what the
  palette cannot reach: flat buttons and inputs, tabs, group boxes, column
  heads, the status bar and scroll bars. Corners use the web radius (3 px);
  nothing has a shadow.
* The Windows title bar follows the mode through Qt's color-scheme hint.
* Status tags are QLabels with rich text: the glyph in the kind's color, the
  word in caps (label face) and the detail in the number face.

Targets PySide6 6.8 or newer.
"""

from __future__ import annotations

import tempfile
import weakref
from collections.abc import Callable, Mapping
from html import escape
from pathlib import Path

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QFontDatabase, QImage, QPainter, QPalette, QPen, QPixmap, QPolygonF
from PySide6.QtWidgets import QAbstractItemView, QApplication, QLabel, QWidget

from . import status as _status
from .tokens import FontSpec, Palette, Tokens, resolve_mode
from .tokens import load as _load

# Font role -> (font spec role, type size role); the same roles as tk_theme.FONTS.
FONTS: dict[str, tuple[str, str]] = {
    "ui": ("ui", "body"),
    "ui_small": ("ui", "caption"),
    "ui_strong": ("ui_strong", "body"),
    "control": ("ui", "control"),
    "title": ("display", "title"),
    "heading": ("display", "heading"),
    "label": ("label", "caption"),
    "label_large": ("label", "control"),
    "num": ("num", "body"),
    "num_small": ("num", "caption"),
    "num_strong": ("num_strong", "body"),
    "readout": ("label", "readout"),
}

_GENERIC = {"serif", "sans-serif", "monospace", "system-ui", "ui-monospace", "-apple-system"}
_WEIGHTS = {
    300: QFont.Weight.Light,
    400: QFont.Weight.Normal,
    500: QFont.Weight.Medium,
    600: QFont.Weight.DemiBold,
    700: QFont.Weight.Bold,
}

_CURRENT: QtTheme | None = None


# -- fonts ----------------------------------------------------------------------------
def available_families() -> dict[str, str]:
    """Installed font families, keyed by lower-case name."""
    return {name.lower(): name for name in QFontDatabase.families()}


def resolve_family(spec: FontSpec, families: dict[str, str] | None = None) -> str:
    """The first installed family in ``spec``'s stack; the application font as a last resort."""
    families = families if families is not None else available_families()
    for name in spec.css:
        if name in _GENERIC:
            continue
        found = families.get(name.lower())
        if found:
            return found
    return QApplication.font().family()


def make_font(spec: FontSpec, point_size: float, families: dict[str, str] | None = None) -> QFont:
    """A QFont for one token role: family, size, weight, width, spacing, and caps for labels."""
    font = QFont(resolve_family(spec, families))
    font.setPointSizeF(point_size)
    font.setWeight(_WEIGHTS.get(spec.weight, QFont.Weight.Normal))
    if spec.stretch:
        font.setStretch(int(float(spec.stretch.rstrip("%"))))
    if spec.letter_spacing_em:
        font.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 100 + spec.letter_spacing_em * 100)
    if spec.role == "label":
        font.setCapitalization(QFont.Capitalization.AllUppercase)
    return font


# -- palette and style sheet ----------------------------------------------------------
def qpalette(p: Palette) -> QPalette:
    """A QPalette from one mode's tokens. Selection is the navy tint with ink text."""
    R = QPalette.ColorRole
    roles = {
        R.Window: p.canvas, R.WindowText: p.ink, R.Base: p.surface, R.AlternateBase: p.raised,
        R.ToolTipBase: p.ink, R.ToolTipText: p.surface, R.PlaceholderText: p.faint,
        R.Text: p.ink, R.Button: p.surface, R.ButtonText: p.ink, R.BrightText: p.on_navy,
        R.Light: p.surface, R.Midlight: p.raised, R.Mid: p.rule_strong, R.Dark: p.rule_strong,
        R.Shadow: p.rule_strong, R.Highlight: p.navy_tint, R.HighlightedText: p.ink,
        R.Link: p.navy, R.LinkVisited: p.navy,
    }
    if hasattr(R, "Accent"):
        roles[R.Accent] = p.navy
    palette = QPalette()
    for role, value in roles.items():
        palette.setColor(role, QColor(value))
    disabled = QPalette.ColorGroup.Disabled
    for role in (R.WindowText, R.Text, R.ButtonText):
        palette.setColor(disabled, role, QColor(p.faint))
    for role in (R.Base, R.Button, R.Highlight):
        palette.setColor(disabled, role, QColor(p.raised))
    return palette


def _arrow_image(direction: str, color: str, scale: int) -> QImage:
    width, height = 9 * scale, 5 * scale
    image = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(color))
    if direction == "up":
        points = [QPointF(0, height), QPointF(width / 2, 0), QPointF(width, height)]
    else:
        points = [QPointF(0, 0), QPointF(width, 0), QPointF(width / 2, height)]
    painter.drawPolygon(QPolygonF(points))
    painter.end()
    return image


def arrow_images(p: Palette, folder: Path | None = None) -> dict[str, str]:
    """Up/down arrow PNGs (plus @2x copies) in this mode's muted and faint inks.

    Style sheets that restyle spin boxes and combo boxes must draw the arrows
    themselves; Qt draws them from image files. Keys: up, down, up_off, down_off.
    """
    folder = folder or Path(tempfile.gettempdir()) / "onedesk-qt"
    folder.mkdir(parents=True, exist_ok=True)
    paths: dict[str, str] = {}
    for key, direction, color in (("up", "up", p.muted), ("down", "down", p.muted),
                                  ("up_off", "up", p.faint), ("down_off", "down", p.faint)):
        stem = f"arrow-{direction}-{color.lstrip('#').lower()}"
        for scale, suffix in ((1, ""), (2, "@2x")):
            path = folder / f"{stem}{suffix}.png"
            if not path.exists():
                _arrow_image(direction, color, scale).save(str(path))
        paths[key] = (folder / f"{stem}.png").as_posix()
    return paths


def _arrow_rules(p: Palette, r: int, arrows: Mapping[str, str]) -> str:
    spins = ("QSpinBox", "QDoubleSpinBox", "QDateTimeEdit")

    def sub(name: str) -> str:
        return ", ".join(f"{s}::{name}" for s in spins)

    return f"""QComboBox {{ padding-right: 22px; }}
QComboBox::drop-down {{ subcontrol-origin: padding; subcontrol-position: top right; width: 20px; border: none; }}
QComboBox::down-arrow {{ image: url("{arrows['down']}"); width: 9px; height: 5px; }}
QComboBox::down-arrow:disabled {{ image: url("{arrows['down_off']}"); }}
{", ".join(spins)} {{ padding-right: 20px; }}
{sub("up-button")} {{ subcontrol-origin: border; subcontrol-position: top right; width: 18px; border: none;
    border-left: 1px solid {p.rule}; border-top-right-radius: {r}px; background: transparent; }}
{sub("down-button")} {{ subcontrol-origin: border; subcontrol-position: bottom right; width: 18px; border: none;
    border-left: 1px solid {p.rule}; border-bottom-right-radius: {r}px; background: transparent; }}
{sub("up-button:hover")}, {sub("down-button:hover")} {{ background: {p.raised}; }}
{sub("up-arrow")} {{ image: url("{arrows['up']}"); width: 9px; height: 5px; }}
{sub("down-arrow")} {{ image: url("{arrows['down']}"); width: 9px; height: 5px; }}
{sub("up-arrow:disabled")}, {sub("up-arrow:off")} {{ image: url("{arrows['up_off']}"); }}
{sub("down-arrow:disabled")}, {sub("down-arrow:off")} {{ image: url("{arrows['down_off']}"); }}"""


def stylesheet(p: Palette, *, radius: int = 3, control_pt: float = 10, title_pt: float = 11,
               title_family: str = "Segoe UI Variable Display", arrows: Mapping[str, str] | None = None) -> str:
    """The application style sheet for one mode: the parts a QPalette cannot reach.

    ``arrows`` (from :func:`arrow_images`) styles spin and combo boxes too; without
    it they keep the style's own frames and arrows.
    """
    r = radius
    inputs = "QLineEdit, QComboBox" if arrows is None else "QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QDateTimeEdit"
    boxes = f"{inputs}, QPlainTextEdit, QTextEdit"

    def each(selectors: str, state: str) -> str:
        return ", ".join(f"{s.strip()}:{state}" for s in selectors.split(","))

    return f"""
QToolTip {{ color: {p.surface}; background: {p.ink}; border: 1px solid {p.ink}; padding: 4px 6px; }}
QPushButton {{ background: {p.surface}; color: {p.ink}; border: 1px solid {p.rule_strong}; border-radius: {r}px;
    padding: 4px 12px; font-size: {control_pt}pt; }}
QPushButton:hover {{ background: {p.raised}; }}
QPushButton:pressed {{ background: {p.sunken}; }}
QPushButton:checked {{ background: {p.navy_tint}; border-color: {p.navy}; }}
QPushButton:focus {{ border-color: {p.focus}; }}
QPushButton:disabled {{ background: {p.raised}; color: {p.faint}; border-color: {p.rule}; }}
QPushButton[onedesk="primary"] {{ background: {p.navy}; color: {p.on_navy}; border-color: {p.navy}; }}
QPushButton[onedesk="primary"]:hover {{ background: {p.navy_hover}; border-color: {p.navy_hover}; }}
QPushButton[onedesk="primary"]:disabled {{ background: {p.raised}; color: {p.faint}; border-color: {p.rule}; }}
{boxes} {{ background: {p.surface}; color: {p.ink}; border: 1px solid {p.rule_strong}; border-radius: {r}px;
    selection-background-color: {p.navy_tint}; selection-color: {p.ink}; }}
{inputs} {{ padding: 3px 6px; font-size: {control_pt}pt; }}
{each(boxes, "focus")} {{ border-color: {p.focus}; }}
{each(boxes, "disabled")} {{ background: {p.raised}; color: {p.faint}; border-color: {p.rule}; }}
QComboBox QAbstractItemView {{ background: {p.surface}; color: {p.ink}; border: 1px solid {p.rule_strong};
    selection-background-color: {p.navy_tint}; selection-color: {p.ink}; }}
{_arrow_rules(p, r, arrows) if arrows is not None else ""}
QGroupBox {{ background: {p.surface}; color: {p.ink}; border: 1px solid {p.rule}; border-radius: {r}px;
    margin-top: 20px; padding: 10px 8px 8px 8px;
    font-family: "{title_family}"; font-size: {title_pt}pt; font-weight: 600; }}
QGroupBox::title {{ subcontrol-origin: margin; subcontrol-position: top left; left: 1px; padding: 0 2px;
    color: {p.ink}; }}
QTabWidget::pane {{ background: {p.surface}; border: 1px solid {p.rule}; border-radius: {r}px; top: -1px; }}
QTabBar::tab {{ background: transparent; color: {p.ink_2}; border: none; border-bottom: 2px solid transparent;
    padding: 6px 12px; margin-right: 2px; font-size: {control_pt}pt; }}
QTabBar::tab:selected {{ color: {p.ink}; border-bottom: 2px solid {p.navy}; }}
QTabBar::tab:hover:!selected {{ color: {p.ink}; background: {p.raised}; }}
QHeaderView::section {{ background: {p.raised}; color: {p.muted}; border: none;
    border-bottom: 1px solid {p.rule_strong}; border-right: 1px solid {p.rule}; padding: 4px 6px; }}
QTableCornerButton::section {{ background: {p.raised}; border: none; border-bottom: 1px solid {p.rule_strong}; }}
QTableView, QTreeView, QListView {{ background: {p.surface}; alternate-background-color: {p.raised};
    gridline-color: {p.rule}; border: 1px solid {p.rule}; border-radius: {r}px; }}
QStatusBar {{ background: {p.surface}; color: {p.ink_2}; border-top: 1px solid {p.rule}; }}
QStatusBar::item {{ border: none; }}
QSplitter::handle {{ background: {p.rule}; }}
QMenu {{ background: {p.surface}; color: {p.ink}; border: 1px solid {p.rule_strong}; }}
QMenu::item:selected {{ background: {p.navy_tint}; color: {p.ink}; }}
QProgressBar {{ background: {p.sunken}; color: {p.ink}; border: 1px solid {p.rule_strong}; border-radius: {r}px;
    text-align: center; }}
QProgressBar::chunk {{ background: {p.navy}; border-radius: {r}px; }}
QScrollBar:vertical {{ background: transparent; width: 11px; margin: 0; }}
QScrollBar:horizontal {{ background: transparent; height: 11px; margin: 0; }}
QScrollBar::handle:vertical {{ background: {p.rule_strong}; border-radius: 4px; min-height: 24px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: {p.rule_strong}; border-radius: 4px; min-width: 24px; margin: 2px; }}
QScrollBar::handle:hover {{ background: {p.muted}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
QLabel[onedesk="muted"] {{ color: {p.muted}; }}
QLabel[onedesk="ink2"] {{ color: {p.ink_2}; }}
"""


def set_color_scheme(app: QApplication, mode: str) -> bool:
    """Tell Qt (and with it the Windows title bar) which mode is showing. False on Qt older than 6.8."""
    hints = app.styleHints()
    if not hasattr(hints, "setColorScheme"):
        return False
    hints.setColorScheme(Qt.ColorScheme.Dark if mode == "dark" else Qt.ColorScheme.Light)
    return True


# -- status tags ---------------------------------------------------------------------
def tag_html(item: _status.Status, p: Palette, *, number_family: str = "Cascadia Mono") -> str:
    """Rich text for one tag: colored glyph, caps word, detail in the number face."""
    colors = _status.tag_colors(item.kind, p)
    parts = []
    glyph = item.shown_glyph
    if glyph:
        parts.append(f'<span style="color:{colors.glyph}">{escape(glyph)}</span>&nbsp;')
    parts.append(escape(item.label))
    if item.detail:
        parts.append(f'&nbsp;<span style="font-family:\'{escape(number_family)}\';">{escape(item.detail)}</span>')
    return "".join(parts)


def tag_stylesheet(kind: _status.Kind | str, p: Palette, *, radius: int = 3) -> str:
    """The QLabel style for a tag of ``kind``: quiet outline when healthy, tint when it needs you."""
    colors = _status.tag_colors(kind, p)
    line = "dashed" if colors.pattern else "solid"  # hatch and stripes become a dashed outline
    return (f"QLabel {{ color: {colors.text}; background: {colors.background}; "
            f"border: 1px {line} {colors.border}; border-radius: {radius}px; padding: 2px 7px; }}")


# -- drawing ---------------------------------------------------------------------------
def hatch_brush(color: str | QColor, spacing: int = 6, width: float = 1.0) -> QBrush:
    """A tiling brush of diagonal lines: the One Desk mark for data you should not trust."""
    spacing = max(3, int(spacing))
    tile = QPixmap(spacing, spacing)
    tile.fill(Qt.GlobalColor.transparent)
    painter = QPainter(tile)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setPen(QPen(QColor(color), width))
    for shift in (-spacing, 0, spacing):  # the neighbours' segments keep the tiles seamless
        painter.drawLine(QPointF(shift, spacing), QPointF(shift + spacing, 0))
    painter.end()
    return QBrush(tile)


# -- the theme -----------------------------------------------------------------------
class QtTheme:
    """The One Desk look applied to one QApplication. Create it with :func:`apply`."""

    def __init__(self, app: QApplication, mode: str = "light", *, style: str | None = "Fusion",
                 color_scheme_hint: bool = True) -> None:
        self.app = app
        self.tokens: Tokens = _load()
        self.mode = resolve_mode(mode)
        self.palette: Palette = self.tokens.palette(self.mode)
        self.radius = self.tokens.radius("web")
        self._hint = color_scheme_hint
        self._listeners: list[Callable[[QtTheme], None]] = []
        self._tags: weakref.WeakKeyDictionary[QLabel, _status.Status] = weakref.WeakKeyDictionary()
        families = available_families()
        self.fonts: dict[str, QFont] = {
            role: make_font(self.tokens.font(spec_role), self.tokens.type_size(size_role).pt, families)
            for role, (spec_role, size_role) in FONTS.items()
        }
        if style:
            app.setStyle(style)
        app.setFont(self.fonts["ui"])
        self._apply_palette()

    # fonts and colors --------------------------------------------------------------
    def font(self, role: str = "ui") -> QFont:
        """A copy of the QFont for ``role`` (see :data:`FONTS`)."""
        return QFont(self.fonts[role])

    def color(self, name: str) -> QColor:
        """A token color for the current mode, e.g. ``theme.color("up")``."""
        return QColor(self.palette[name])

    def mix(self, a: str, b: str, t: float) -> QColor:
        """``a`` mixed into ``b`` (``t`` is the weight of ``a``) for the current mode."""
        return QColor(self.palette.mix(a, b, t))

    def hatch_brush(self, spacing: int = 6) -> QBrush:
        return hatch_brush(self.palette.hatch, spacing)

    # palette -------------------------------------------------------------------------
    def _apply_palette(self) -> None:
        self.app.setPalette(qpalette(self.palette))
        self.app.setStyleSheet(stylesheet(
            self.palette, radius=self.radius,
            control_pt=self.tokens.type_size("control").pt,
            title_pt=self.tokens.type_size("title").pt,
            title_family=self.fonts["title"].family(),
            arrows=arrow_images(self.palette),
        ))
        if self._hint:
            set_color_scheme(self.app, self.mode)
        for label, item in list(self._tags.items()):
            self._style_tag(label, item)

    def set_mode(self, mode: str) -> bool:
        """Switch light/dark live. Returns True if the mode changed; listeners run last."""
        new_mode = resolve_mode(mode)
        if new_mode == self.mode:
            return False
        self.mode = new_mode
        self.palette = self.tokens.palette(new_mode)
        self._apply_palette()
        for callback in list(self._listeners):
            callback(self)
        return True

    def toggle(self) -> str:
        self.set_mode("dark" if self.mode == "light" else "light")
        return self.mode

    def on_mode_change(self, callback: Callable[[QtTheme], None]) -> None:
        self._listeners.append(callback)

    # tags --------------------------------------------------------------------------------
    def tag(self, item: _status.Status, parent: QWidget | None = None) -> QLabel:
        """A new QLabel showing ``item`` as a One Desk tag."""
        return self.set_tag(QLabel(parent), item)

    def set_tag(self, label: QLabel, item: _status.Status) -> QLabel:
        """Show ``item`` on ``label`` (any QLabel); it is restyled on mode switches."""
        self._tags[label] = item
        self._style_tag(label, item)
        return label

    def _style_tag(self, label: QLabel, item: _status.Status) -> None:
        font = self.font("label")
        font.setCapitalization(QFont.Capitalization.MixedCase)  # the word is already caps; details are not
        try:
            label.setTextFormat(Qt.TextFormat.RichText)
            label.setFont(font)
            label.setText(tag_html(item, self.palette, number_family=self.fonts["num"].family()))
            label.setStyleSheet(tag_stylesheet(item.kind, self.palette, radius=self.radius))
            label.setAccessibleName(item.text())
            label.setProperty("onedeskStatus", item.text())
        except RuntimeError:  # the Qt object is already gone
            self._tags.pop(label, None)

    # tables ------------------------------------------------------------------------------
    def header_font(self) -> QFont:
        """The caps label face for column heads.

        Qt draws header text in the font the model gives for ``Qt.FontRole``, not
        in the header widget's font, so a model's ``headerData`` should return
        this for horizontal sections. :meth:`style_table` sets it on the header
        items of a ``QTableWidget`` itself.
        """
        return self.font("label")

    def style_table(self, view: QAbstractItemView, *, numbers: bool = True) -> None:
        """Number face for the cells (``numbers=True``) and caps label face for the column heads."""
        if numbers:
            view.setFont(self.font("num"))
        header = getattr(view, "horizontalHeader", None)
        if callable(header):
            header().setFont(self.header_font())
        header_item = getattr(view, "horizontalHeaderItem", None)
        if callable(header_item):  # QTableWidget: its items carry their own font
            for column in range(view.columnCount()):
                item = header_item(column)
                if item is not None:
                    item.setFont(self.header_font())


def apply(app: QApplication, mode: str = "light", **kwargs: object) -> QtTheme:
    """Apply One Desk to ``app`` and return the :class:`QtTheme` (also kept as :func:`current`)."""
    global _CURRENT
    _CURRENT = QtTheme(app, mode, **kwargs)
    return _CURRENT


def current() -> QtTheme | None:
    """The theme applied last in this process, or ``None``."""
    return _CURRENT
