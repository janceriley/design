r"""Render Equity Recorder's window states to PNGs without showing anything on screen.

    ..\Equity_Recorder\.venv\Scripts\python.exe demos\equity_states.py demos\out\equity-recorder\after-light light
    ..\Equity_Recorder\.venv\Scripts\python.exe demos\equity_states.py demos\out\equity-recorder\after-dark dark

Uses the tests' fake service and recorder (no IBKR), a throwaway settings file
and made-up quotes; the real watchlist settings are never read. Windows render
with WA_DontShowOnScreen, so nothing appears on the desktop. Set ER_ROOT to
render another copy of the project (for example an export of an older commit);
its One Desk bridge is applied only if that copy has one.
"""

from __future__ import annotations

import math
import os
import random
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

OUT = Path(sys.argv[1])
MODE = sys.argv[2] if len(sys.argv) > 2 else "light"
os.environ["QT_QPA_PLATFORM"] = "windows"  # real fonts; windows stay off screen
os.environ["EQUITY_RECORDER_THEME"] = MODE
ROOT = Path(os.environ.get("ER_ROOT", r"C:\Users\Jance\Documents\Dev\Equity_Recorder"))
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QSettings, Qt  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication([])
# Only the copy under ROOT counts: the editable install could otherwise find the working tree's bridge.
if (ROOT / "equity_recorder" / "one_desk.py").is_file():
    from equity_recorder import one_desk  # noqa: E402

    one_desk.apply(app)
    print("One Desk applied:", one_desk.theme_mode())
else:
    print("No One Desk bridge yet (before)")

from equity_recorder.broker_clock import ClockEstimate  # noqa: E402
from equity_recorder.issues import IssueNotice  # noqa: E402
from equity_recorder.market_hours import RegularHoursSchedule  # noqa: E402
from equity_recorder.models import ConnectionState, MarketDataType, QuoteRow, RowState  # noqa: E402
from equity_recorder.ui import MainWindow  # noqa: E402
import equity_recorder  # noqa: E402
print("equity_recorder from", Path(equity_recorder.__file__).parent)
from tests.test_ui import FakeRecorder, FakeService  # noqa: E402

CLOCK = {"ns": 1_000_000_000_000}
BROKER_UTC = datetime(2026, 9, 9, 15, 0, tzinfo=timezone.utc)
SESSION = "20260909:0930-1600"


def now_ns() -> int:
    return CLOCK["ns"]


def snapshot(row_id: str, ticker: str, mid: float, *, prior_close: float, low: float, high: float,
             state: str = "Live", data_type: str = "Live", spread: float = 0.02,
             trade_age: float = 0.4, depth_valid: bool = True) -> dict:
    stamp = BROKER_UTC + timedelta(microseconds=(CLOCK["ns"] - 1_000_000_000_000) // 1000)
    bid, ask = round(mid - spread / 2, 2), round(mid + spread / 2, 2)
    return {
        "row_id": row_id, "ticker": ticker, "captured_at_utc": stamp,
        "captured_monotonic_ns": CLOCK["ns"], "connection_epoch": 1,
        "row_state": state, "market_data_type": data_type,
        "bid": bid, "ask": ask, "bid_size": float(random.randint(1, 30) * 100),
        "ask_size": float(random.randint(1, 30) * 100), "mid": round(mid, 3),
        "microprice": round(mid, 3), "spread": round(ask - bid, 2), "min_tick": 0.01,
        "bid_updated_at_utc": stamp, "ask_updated_at_utc": stamp,
        "quote_age_seconds": 0.2, "trade_age_seconds": trade_age,
        "last_trade_age_seconds": trade_age, "depth_age_seconds": 0.3,
        "last_trade_price": round(mid + random.choice((-0.01, 0.0, 0.01)), 2),
        "last_trade_size": float(random.randint(1, 9) * 100), "last_trade_exchange": "NASDAQ",
        "trade_source": "TICK_BY_TICK_ALL_LAST", "quote_source": "TICK_BY_TICK_BID_ASK",
        "prior_close": prior_close, "day_low": low, "day_high": high, "depth_valid": depth_valid,
        "bid_depth_rows": 3, "ask_depth_rows": 3, "bid_depth_5": 1200.0, "ask_depth_5": 900.0,
        "bid_l1_price": bid, "bid_l1_size": 400.0, "bid_l1_exchange": "NSDQ",
        "bid_l2_price": round(bid - 0.01, 2), "bid_l2_size": 300.0, "bid_l2_exchange": "IEX",
        "ask_l1_price": ask, "ask_l1_size": 300.0, "ask_l1_exchange": "NYSE",
        "ask_l2_price": round(ask + 0.01, 2), "ask_l2_size": 500.0, "ask_l2_exchange": "ARCA",
    }


LIVE_ROWS = [
    # row_id, ticker, prior close, start mid, drift per step, state, data type
    ("aapl", "AAPL", 226.10, 228.40, 0.035, "Live", MarketDataType.LIVE),
    ("msft", "MSFT", 431.00, 427.10, -0.040, "Live", MarketDataType.LIVE),
    ("nvda", "NVDA", 118.70, 119.90, 0.010, "Live", MarketDataType.LIVE),
    ("tsla", "TSLA", 250.40, 247.80, -0.020, "Delayed", MarketDataType.DELAYED),
]


def build_window() -> tuple[MainWindow, FakeRecorder]:
    folder = tempfile.mkdtemp(prefix="er-capture-")
    settings = QSettings(str(Path(folder) / "capture.ini"), QSettings.Format.IniFormat)
    recorder = FakeRecorder()
    window = MainWindow(service=FakeService(), recorder=recorder, settings=settings, event_interval_ms=60_000)
    window._event_timer.stop()
    window._recorder_status_timer.stop()
    window.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    window.resize(1380, 740)
    window.show()
    app.processEvents()
    return window, recorder


def populate(window: MainWindow) -> None:
    random.seed(7)
    model = window._model
    for row_id, ticker, *_rest, data_type in LIVE_ROWS:
        state = RowState.DELAYED if data_type is MarketDataType.DELAYED else RowState.LIVE
        model.add_quote_row(QuoteRow(row_id, ticker, ticker, state=state, market_data_type=data_type))
    model.add_quote_row(QuoteRow("amd", "AMD", "AMD", state=RowState.STALE))
    model.add_quote_row(QuoteRow("pltr", "PLTR", "PLTR", state=RowState.SUBSCRIBING))
    model.add_quote_row(QuoteRow("xyzq", "XYZQ", "XYZQ", state=RowState.RESOLVING))
    model._broker_clock = lambda: ClockEstimate(
        utc=BROKER_UTC, state="SYNCHRONIZED", sync_id="capture", uncertainty_seconds=0.0, age_seconds=0,
    )
    window._set_connection_state(ConnectionState.CONNECTED)
    schedule = RegularHoursSchedule.from_ibkr(SESSION, "US/Eastern")
    model.set_market_hours({row.row_id: schedule for row in model.rows})
    mids = {row_id: start for row_id, _t, _c, start, _d, _s, _dt in LIVE_ROWS}
    with patch("time.monotonic_ns", side_effect=now_ns):
        for step in range(200):  # five minutes of quotes, 1.5 s apart (gaps over 2 s break the trend)
            CLOCK["ns"] += 1_500_000_000
            for row_id, ticker, close, _start, drift, state, data_type in LIVE_ROWS:
                mids[row_id] += 0.4 * drift + random.gauss(0, 0.035) + 0.02 * math.sin(step / 17)
                low, high = round(min(close, mids[row_id]) - 1.2, 2), round(max(close, mids[row_id]) + 1.5, 2)
                model.apply_snapshot(snapshot(row_id, ticker, mids[row_id], prior_close=close, low=low, high=high,
                                              state=state, data_type=data_type.value))
        model.mark_error("xyzq", "No security definition has been found for the request.")
        model.refresh_quote_ages()
    app.processEvents()


def grab(widget, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    app.processEvents()
    widget.grab().save(str(OUT / name))
    print("saved", name)


def main() -> None:
    window, recorder = build_window()
    grab(window, "01-disconnected-empty.png")
    with patch("time.monotonic_ns", side_effect=now_ns):
        populate(window)
        window._table.selectRow(0)
        grab(window, "02-watchlist.png")
        window._details_button.setChecked(True)
        app.processEvents()
        grab(window, "03-watchlist-details.png")
        window._details_button.setChecked(False)

        window._tabs.setCurrentIndex(1)
        grab(window, "04-recorder-idle.png")
        recorder.start()
        recorder.batches = [[{}] * 7 for _ in range(240)]
        window._refresh_recorder_status()
        grab(window, "05-recorder-recording.png")

        window._tabs.setCurrentIndex(2)
        grab(window, "06-recording-review.png")

        window._issues.add_entries([
            IssueNotice("No security definition has been found for the request.", ticker="XYZQ",
                        feed="contract", code=200, severity="Error"),
            IssueNotice("Market data farm connection is inactive but should be available upon demand.",
                        feed="market_data", code=2108, severity="Warning"),
            IssueNotice("Connection: Connected.", source="Application", feed="Connection", severity="Info"),
            IssueNotice("Delayed market data is being shown for TSLA.", ticker="TSLA", feed="quotes",
                        code=10167, severity="Warning"),
        ])
        window._tabs.setCurrentIndex(3)
        grab(window, "07-issues.png")
        window._tabs.setCurrentIndex(0)

        bar = window.statusBar()
        for state in ConnectionState:
            window._set_connection_state(state)
            grab(bar, f"badge-connection-{state.name.lower()}.png")
        for mode in ("off", "waiting", "armed", "on", "stopping", "error"):
            window._set_recorder_badge(mode)
            grab(bar, f"badge-rec-{mode}.png")
    window.close()


if __name__ == "__main__":
    main()
