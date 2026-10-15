r"""One Desk on Qt (PySide6): a small window with every piece, light and dark.

    ..\Equity_Recorder\.venv\Scripts\python.exe demos\qt_demo.py                            # opens the window
    ..\Equity_Recorder\.venv\Scripts\python.exe demos\qt_demo.py --screenshot demos\out\qt   # qt-light.png, qt-dark.png

Screenshots render off screen. All numbers are made up.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import (  # noqa: E402
    QApplication, QComboBox, QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QMainWindow,
    QPushButton, QSpinBox, QTableWidget, QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget,
)

from onedesk import fmt, qt_theme, status  # noqa: E402

ROWS = [  # ticker, bid, ask, change %, last, stale
    ("AAPL", 228.41, 228.43, 1.02, 228.42, False),
    ("MSFT", 424.03, 424.05, -1.61, 424.05, False),
    ("NVDA", 120.32, 120.34, 1.36, 120.32, False),
    ("AMD", None, None, None, None, True),
]


def build(theme: qt_theme.QtTheme) -> QMainWindow:
    window = QMainWindow()
    window.setWindowTitle("One Desk on Qt")
    central = QWidget(window)
    outer = QVBoxLayout(central)
    outer.setContentsMargins(12, 12, 12, 10)
    outer.setSpacing(10)

    head = QHBoxLayout()
    name = QLabel("One Desk · Qt", central)
    name.setFont(theme.font("label_large"))
    head.addWidget(name)
    for item in (status.live("paper"), status.connecting(), status.reconnecting(), status.needs("Auth", "2d"),
                 status.failed("Error"), status.offline(), status.recording(), status.stale("AMD"), status.demo()):
        head.addWidget(theme.tag(item, central))
    head.addStretch(1)
    outer.addLayout(head)

    controls = QHBoxLayout()
    ticker = QLineEdit(central)
    ticker.setPlaceholderText("US stock ticker (for example, AAPL)")
    controls.addWidget(ticker, 1)
    view = QComboBox(central)
    view.addItems(("Overview", "Quotes", "All columns"))
    controls.addWidget(view)
    depth = QSpinBox(central)
    depth.setRange(1, 5)
    depth.setValue(5)
    controls.addWidget(depth)
    connect = QPushButton("Connect", central)
    connect.setProperty("onedesk", "primary")
    controls.addWidget(connect)
    controls.addWidget(QPushButton("Add", central))
    remove = QPushButton("Remove selected", central)
    remove.setEnabled(False)
    controls.addWidget(remove)
    details = QPushButton("Show details", central)
    details.setCheckable(True)
    details.setChecked(True)
    controls.addWidget(details)
    outer.addLayout(controls)

    tabs = QTabWidget(central)
    table = QTableWidget(len(ROWS), 5)
    table.setHorizontalHeaderLabels(["Ticker", "Bid", "Ask", "Day change", "Last trade"])
    table.verticalHeader().setVisible(False)
    table.setShowGrid(False)
    table.setAlternatingRowColors(True)
    theme.style_table(table)
    table.horizontalHeader().setStretchLastSection(True)

    def paint_rows(t: qt_theme.QtTheme) -> None:
        for row, (symbol, bid, ask, change, last, stale) in enumerate(ROWS):
            cells = [symbol, fmt.price(bid), fmt.price(ask),
                     "—" if change is None else f"{change:+.2f}%".replace("-", "−"), fmt.price(last)]
            for column, text in enumerate(cells):
                item = QTableWidgetItem(text)
                align = Qt.AlignmentFlag.AlignLeft if column == 0 else Qt.AlignmentFlag.AlignRight
                item.setTextAlignment(align | Qt.AlignmentFlag.AlignVCenter)
                if stale:
                    item.setBackground(t.hatch_brush())
                    item.setForeground(t.color("muted"))
                elif column == 3 and change:
                    item.setForeground(t.color("up" if change > 0 else "down"))
                table.setItem(row, column, item)

    paint_rows(theme)
    theme.on_mode_change(paint_rows)
    table.selectRow(0)
    tabs.addTab(table, "Watchlist")

    recorder = QWidget()
    recorder_layout = QHBoxLayout(recorder)
    session = QGroupBox("Session", recorder)
    form = QFormLayout(session)
    for label, value in (("Session ID", "20260915-093000"), ("Started", "Tue Sep 15 '26 09:30:00"),
                         ("Rows written", f"{12_345:,}"), ("Writer", "Running")):
        field = QLabel(value, session)
        field.setFont(theme.font("num"))
        form.addRow(label, field)
    recorder_layout.addWidget(session)
    capture = QGroupBox("Capture", recorder)
    capture_form = QFormLayout(capture)
    capture_form.addRow("Active tickers", QLabel("3", capture))
    capture_form.addRow("Snapshot interval", QLabel("250 ms (fixed)", capture))
    recorder_layout.addWidget(capture)
    tabs.addTab(recorder, "Recorder")
    tabs.addTab(QWidget(), "Recording review")
    tabs.addTab(QWidget(), "Issues (2)")
    outer.addWidget(tabs, 1)
    window.setCentralWidget(central)

    window.statusBar().showMessage("Connected to IB Gateway (paper).")
    window.statusBar().addPermanentWidget(theme.tag(status.recording("12,345 rows"), window))
    window.statusBar().addPermanentWidget(theme.tag(status.Status("Connected", status.Kind.OK), window))
    window.resize(1100, 520)
    return window


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--screenshot", metavar="PREFIX", help="write PREFIX-light.png and PREFIX-dark.png and exit")
    args = parser.parse_args(argv)
    if args.screenshot:
        os.environ.setdefault("QT_QPA_PLATFORM", "windows" if sys.platform == "win32" else "offscreen")
    app = QApplication(sys.argv[:1])
    theme = qt_theme.apply(app, "light")
    window = build(theme)
    if not args.screenshot:
        window.show()
        return app.exec()
    window.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    window.show()
    prefix = Path(args.screenshot)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    for mode in ("light", "dark"):
        theme.set_mode(mode)
        app.processEvents()
        path = prefix.with_name(f"{prefix.name}-{mode}.png")
        window.grab().save(str(path))
        print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
