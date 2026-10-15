r"""Light-mode screenshots of Options Matrix Studio and Viewer in every state they show.

    ..\matrix_hybrid\work_pc\.venv\Scripts\python.exe demos\matrix_states.py run demos\out\matrix-light-states

``run`` starts the mini PC role (which also hosts sharing) and the work PC role in two
processes, then builds the overview sheets and index.html with matrix_sheets.py. Real
windows open on the main monitor for about four minutes.

Safety: demo data only, throwaway settings folders, sharing bound to 127.0.0.1.
The Schwab token file is never read (its age is patched in). Recording is never
started; recorder states are set on the app the way its own code sets them.
Computer names and the Mini PC address are replaced with examples.
"""

from __future__ import annotations

import ctypes
import gc
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import traceback
from ctypes import wintypes
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
MX_ROOT = Path(r"C:\Users\Jance\Documents\Dev\matrix_hybrid")
MX_PYTHON = MX_ROOT / "work_pc" / ".venv" / "Scripts" / "python.exe"
PIL_PYTHON = r"C:\Users\Jance\Documents\Dev\Order_Parser\.venv\Scripts\python.exe"
GEOMETRY = "1260x760+30+30"
EXAMPLE_ADDRESS = "192.168.1.50   (computer name: MINI-PC)"
LIVE_STATUS = "Connected to DEMO market data (made-up prices)."

HELPER = r"""
import json, sys
from PIL import Image, ImageGrab
BG = (242, 244, 247)
for line in sys.stdin:
    job = json.loads(line)
    try:
        x0, y0, x1, y1 = job["bbox"]
        shot = ImageGrab.grab(bbox=(x0, y0, x1, y1), all_screens=True)
        keep = job.get("keep")
        if keep:
            canvas = Image.new("RGB", shot.size, BG)
            for left, top, right, bottom in keep:
                box = (max(0, left - x0), max(0, top - y0), min(shot.width, right - x0), min(shot.height, bottom - y0))
                if box[2] > box[0] and box[3] > box[1]:
                    canvas.paste(shot.crop(box), box[:2])
            shot = canvas
        shot.save(job["path"])
        print("ok", flush=True)
    except Exception as exc:
        print("error " + str(exc), flush=True)
"""

user32 = ctypes.windll.user32
dwmapi = ctypes.windll.dwmapi
user32.FindWindowW.restype = wintypes.HWND
user32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
WM_COMMAND = 0x0111
IDOK = 1
HWND_TOPMOST = -1
SWP_FLAGS = 0x0001 | 0x0002 | 0x0040  # no size, no move, show


class RECT(ctypes.Structure):
    _fields_ = [("left", wintypes.LONG), ("top", wintypes.LONG), ("right", wintypes.LONG), ("bottom", wintypes.LONG)]


def hwnd_rect(hwnd: int) -> tuple[int, int, int, int]:
    rect = RECT()
    if dwmapi.DwmGetWindowAttribute(wintypes.HWND(hwnd), 9, ctypes.byref(rect), ctypes.sizeof(rect)) != 0:
        user32.GetWindowRect(wintypes.HWND(hwnd), ctypes.byref(rect))
    return rect.left, rect.top, rect.right, rect.bottom


def free_port() -> int:
    probe = socket.socket()
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()
    return port


class Shooter:
    """Screen grabs through a Pillow helper process, plus a manifest of what each file shows."""

    def __init__(self, out: Path, role: str) -> None:
        self.out = out
        self.role = role
        self.items: list[dict[str, str]] = []
        self.lock = threading.Lock()
        self.proc = subprocess.Popen(
            [PIL_PYTHON, "-u", "-c", HELPER], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True
        )

    def grab(self, bbox, rel: str, caption: str, group: str, keep=None) -> None:
        path = self.out / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        job = {"bbox": [int(v) for v in bbox], "path": str(path)}
        if keep:
            job["keep"] = [[int(v) for v in rect] for rect in keep]
        with self.lock:
            self.proc.stdin.write(json.dumps(job) + "\n")
            self.proc.stdin.flush()
            reply = self.proc.stdout.readline().strip()
        if reply != "ok":
            print(f"[{self.role}] grab failed for {rel}: {reply}", flush=True)
            return
        self.items.append({"file": rel, "caption": caption, "group": group})
        (self.out / f"manifest-{self.role}.json").write_text(json.dumps(self.items, indent=1), encoding="utf-8")
        print(f"[{self.role}] saved {rel}", flush=True)

    def close(self) -> None:
        try:
            self.proc.stdin.close()
            self.proc.wait(5)
        except Exception:
            self.proc.kill()


class Screen:
    """Raising, settling and grabbing Tk windows of one app."""

    def __init__(self, shooter: Shooter, root) -> None:
        self.shooter = shooter
        self.root = root

    def pump(self, seconds: float, until=None) -> bool:
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            self.root.update()
            if until is not None and until():
                return True
            time.sleep(0.01)
        return bool(until()) if until is not None else True

    @staticmethod
    def _top(win, flag: bool) -> None:
        try:
            win.attributes("-topmost", flag)
        except Exception:
            pass

    def window(self, win, rel: str, caption: str, group: str, settle: float = 0.45) -> None:
        win.deiconify()
        win.lift()
        self._top(win, True)
        self.pump(settle)
        self.shooter.grab(hwnd_rect(int(win.wm_frame(), 16)), rel, caption, group)
        self._top(win, False)

    def widget(self, win, widget, rel: str, caption: str, group: str, pad: int = 5, extra=()) -> None:
        win.lift()
        self._top(win, True)
        for popup in extra:
            self._top(popup, True)
            popup.lift()
        self.pump(0.45)
        boxes = [(widget.winfo_rootx(), widget.winfo_rooty(),
                  widget.winfo_rootx() + widget.winfo_width(), widget.winfo_rooty() + widget.winfo_height())]
        popups = [(popup.winfo_rootx(), popup.winfo_rooty(),
                   popup.winfo_rootx() + popup.winfo_width(), popup.winfo_rooty() + popup.winfo_height())
                  for popup in extra]
        boxes += popups
        bbox = (min(b[0] for b in boxes) - pad, min(b[1] for b in boxes) - pad,
                max(b[2] for b in boxes) + pad, max(b[3] for b in boxes) + pad)
        keep = [hwnd_rect(int(win.wm_frame(), 16)), *popups] if popups else None
        self.shooter.grab(bbox, rel, caption, group, keep=keep)
        self._top(win, False)
        for popup in extra:
            self._top(popup, False)

    def native_dialog(self, title: str, rel: str, caption: str, group: str, button: int = IDOK):
        """Grab a native message box from a helper thread, then press its button."""

        def worker() -> None:
            hwnd = None
            try:
                deadline = time.monotonic() + 20
                while not hwnd and time.monotonic() < deadline:
                    hwnd = user32.FindWindowW("#32770", title)
                    if not hwnd:
                        time.sleep(0.05)
                if not hwnd:
                    print(f"[{self.shooter.role}] no message box titled {title!r}", flush=True)
                    return
                time.sleep(0.6)
                user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_FLAGS)
                time.sleep(0.3)
                self.shooter.grab(hwnd_rect(hwnd), rel, caption, group)
            except Exception:
                traceback.print_exc()
            finally:
                if hwnd:
                    user32.PostMessageW(hwnd, WM_COMMAND, button, 0)

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        return thread


def find_notebook(container, label: str):
    from tkinter import ttk

    stack = [container]
    while stack:
        widget = stack.pop()
        if isinstance(widget, ttk.Notebook):
            names = [widget.tab(tab_id, "text") for tab_id in widget.tabs()]
            if label in names:
                return widget, names.index(label)
        stack.extend(widget.winfo_children())
    return None, None


def find_toplevel(root, title: str):
    import tkinter as tk

    matches = [w for w in root.winfo_children() if isinstance(w, tk.Toplevel) and w.title() == title]
    return matches[-1] if matches else None


def descendants(widget):
    stack = list(widget.winfo_children())
    while stack:
        child = stack.pop()
        yield child
        stack.extend(child.winfo_children())


def open_settings(app, screen: Screen, prefix: str, group: str, read_only: bool = False) -> None:
    """Strategy Settings: Fair value, then the whole cell guide, a screenful at a time."""
    import tkinter as tk

    app._open_settings_dialog()
    dialog = find_toplevel(app.root, "Strategy Settings")
    dialog.geometry("980x900+30+30")
    screen.pump(0.6)
    notebook, _ = find_notebook(dialog, "Fair value")
    notebook.select(0)
    note = " (read-only on the work PC)" if read_only else ""
    screen.window(dialog, f"dialogs/{prefix}-settings-fair-value.png", f"Settings… > Fair value{note}", group)
    if not read_only:
        notebook.select(1)
        screen.pump(0.6)
        guide = notebook.nametowidget(notebook.tabs()[1])
        canvases = [w for w in descendants(guide) if isinstance(w, tk.Canvas)]
        canvas = max(canvases, key=lambda c: c.winfo_height()) if canvases else None
        position, part = 0.0, 1
        while True:
            if canvas is not None:
                canvas.yview_moveto(position)
                screen.pump(0.4)
            screen.window(dialog, f"dialogs/{prefix}-settings-cell-guide-{part}.png",
                          f"Settings… > Matrix cell guide, part {part}", group)
            if canvas is None:
                break
            top, bottom = canvas.yview()
            if bottom >= 0.999 or part >= 8:
                break
            position = top + (bottom - top) * 0.9
            part += 1
    dialog.grab_release()
    dialog.destroy()
    screen.pump(0.3)


# --------------------------------------------------------------------------
# Mini PC: Options Matrix Studio
# --------------------------------------------------------------------------
def studio_role(out: Path, control: Path) -> None:
    os.environ["OPTIONS_MATRIX_THEME"] = "light"
    socket.gethostname = lambda: "MINI-PC"
    sys.path.insert(0, str(MX_ROOT / "mini_pc"))
    import tkinter as tk

    import options_matrix.app as app_module
    from options_matrix import one_desk, studio_dialog
    from options_matrix.app import MarketDataQuoteCounts, MarketDataQuoteStatus, OptionsMatrixApp
    from options_matrix.demo_service import DemoMarketDataService
    from options_matrix.models import SIGNAL_BUY, SIGNAL_SELL, fair_value_edge_for_width
    from options_matrix.positions import PositionRecord, position_key_for_selection
    from options_matrix.recorder import RecorderStatus

    assert one_desk.MODE == "light", one_desk.MODE
    token = {"issued": datetime.now(timezone.utc) - timedelta(days=1)}
    app_module.refresh_token_issued_at = lambda path=None: token["issued"]
    studio_dialog.StudioSettingsDialog._address_text = staticmethod(lambda: EXAMPLE_ADDRESS)

    gc.collect()
    gc.disable()
    shooter = Shooter(out, "studio")
    work = Path(tempfile.mkdtemp(prefix="studio-", dir=control.parent))
    demo = DemoMarketDataService(seed=11, tick_seconds=0.25)
    studio = OptionsMatrixApp(settings_root=work, market_data_service=demo, demo=True)
    root = studio.root
    root.geometry(GEOMETRY)
    screen = Screen(shooter, root)
    pump = screen.pump
    studio.share_bind_host = "127.0.0.1"
    port = free_port()
    studio._update_studio_settings(share_port=port, share_enabled=True, record_every_trading_day=False,
                                   connect_at_startup=False, reload_tabs_after_connect=False)
    studio.record_daily_var.set(False)
    studio.start_services()
    bar = studio.connection_status_label.master

    W = "Studio windows"
    G_CONN, G_AUTH, G_REC = "Studio top bar: Schwab connection", "Studio top bar: authorization", "Studio top bar: recorder"
    G_SHARE, G_QUOTES = "Studio top bar: sharing with the work PC", "Studio top bar: quote footprint line"
    G_TIPS, G_DIALOGS, G_NATIVE = "Tooltips", "Dialogs", "Native Windows pop-ups"

    def shot(rel: str, caption: str, group: str = W) -> None:
        screen.window(root, rel, caption, group)

    def bar_shot(rel: str, caption: str, group: str) -> None:
        screen.widget(root, bar, rel, caption, group)

    def show_bottom(label: str) -> None:
        notebook, index = find_notebook(root, label)
        notebook.select(index)
        pump(0.2)

    def select_cell(tab, key) -> None:
        studio.active_tab_id = tab.tab_id
        tab.selected_cell_key = key
        studio._sync_view_from_active_tab()
        studio._redraw_matrix_tabs()
        studio._redraw_all()
        pump(0.3)

    def snapshot_items(tab):
        if tab.side_states:
            for right, side in tab.side_states.items():
                for key, snap in side.matrix_snapshots.items():
                    yield (right, *key), snap
        else:
            yield from list(tab.matrix_snapshots.items())

    def signal_cell(tab, otm_test):
        found = [(key, snap) for key, snap in snapshot_items(tab)
                 if snap.opportunity_direction in (SIGNAL_BUY, SIGNAL_SELL) and snap.anomaly_direction is None]
        preferred = [item for item in found if otm_test(item[0])]
        return (preferred or found or [(None, None)])[0][0]

    def anomaly_cell():
        """(tab, key, out_of_the_money) for an anomaly, preferring one out of the money."""
        spot_now = demo._spot.get("SPY", spot)
        found = []
        for tab in studio.matrix_tabs:
            side = str(getattr(tab.matrix_input, "side", "CALL")).upper()
            for key, snap in snapshot_items(tab):
                if snap.anomaly_direction is None:
                    continue
                right, lower, width = key if len(key) == 3 else (side, key[0], key[1])
                otm = lower > spot_now if str(right).upper().startswith("C") else lower + width < spot_now
                found.append((tab, key, otm))
        found.sort(key=lambda item: not item[2])
        return found[0] if found else None

    def load_tab(side: str, low: str, high: str, widths, expiry: str | None = None):
        if expiry is not None and studio.expiration_var.get() != expiry:
            studio.expiration_var.set(expiry)
            studio._load_expiration()
            raw = expiry.replace("-", "")
            pump(15, lambda: bool(studio.option_records) and studio.option_records[0].expiration == raw)
        studio.side_var.set(side)
        studio.low_strike_var.set(low)
        studio.high_strike_var.set(high)
        for band, variable in studio.width_vars.items():
            variable.set(band in widths)
        count = len(studio.matrix_tabs)
        studio._load_matrix()
        pump(15, lambda: len(studio.matrix_tabs) > count and not studio.matrix_tabs[-1].is_stale)
        return studio.matrix_tabs[-1]

    def set_connection(kind: str) -> None:
        studio._connect_inflight = kind == "connecting"
        studio._disconnect_inflight = kind == "disconnecting"
        studio._connection_active = kind != "offline"
        retry = {
            "retry": "Schwab stream dropped; reconnecting in 4s (attempt 2/5)",
            "stopped": "Reconnect attempts exhausted. Use Connect to try again.",
        }
        studio._connection_status_message = retry.get(kind, "")
        status = {**retry, "live": LIVE_STATUS, "connecting": "Connect ...", "disconnecting": "Disconnect ...",
                  "offline": "Disconnected."}
        studio._set_status(status[kind])
        OptionsMatrixApp._set_connected_state(studio, kind == "live")

    class FakeRecorder:
        def __init__(self, status) -> None:
            self._status = status

        @property
        def running(self) -> bool:
            return self._status.running

        def status(self):
            return self._status

        def stop(self, *args, **kwargs) -> None:
            return None

        def record_rows(self, *args, **kwargs) -> None:
            return None

    market_day = datetime.now(timezone.utc)
    session_dir = studio._recording_output_root() / "SPY" / market_day.strftime("%Y-%m-%d")
    recording_status = RecorderStatus(
        running=True, session_id="demo-session", session_dir=session_dir,
        current_part_path=session_dir / "part-0003.parquet", rows_enqueued=12_431, rows_written=12_345,
        last_snapshot_rows=96, started_at=market_day.replace(hour=13, minute=30, second=0, microsecond=0),
        last_write_at=market_day.replace(hour=15, minute=42, second=10, microsecond=0), writer_alive=True,
    )

    def set_recorder(kind: str) -> None:
        studio.recorder = None
        studio._recorder_armed = False
        studio._recorder_start_inflight = False
        studio._recorder_stop_inflight = False
        studio._recorder_error_message = None
        studio._recorder_market_status_message = ""
        message = "Recorder idle."
        if kind == "starting":
            studio._recorder_start_inflight = True
            message = "Checking Schwab market time ..."
        elif kind == "armed":
            studio._recorder_armed = True
            opens = (datetime.now(timezone.utc) + timedelta(days=1)).replace(hour=13, minute=30, second=0, microsecond=0)
            message = f"Armed - recording starts at {studio._format_recorder_time(opens)}."
        elif kind == "on":
            studio.recorder = FakeRecorder(recording_status)
            studio._recorder_market_status_message = "Market open until 4:00 PM ET."
            message = "Recording. Market open until 4:00 PM ET."
        elif kind == "stopping":
            studio.recorder = FakeRecorder(replace(recording_status, running=False, stopping=True))
            studio._recorder_stop_inflight = True
            message = "Stopping; flushing accepted rows ..."
        elif kind == "error":
            message = "Recording stopped: could not write part-0004.parquet (the disk is full)."
            studio._recorder_error_message = message
        studio.recorder_status_var.set(message)
        studio._set_status(message)
        studio._refresh_recorder_controls()
        pump(0.2)

    def tooltip(widget, rel: str, caption: str) -> None:
        widget.event_generate("<Enter>")
        pump(0.3)
        popups = [w for w in widget.winfo_children() if isinstance(w, tk.Toplevel)]
        screen.widget(root, bar, rel, caption, G_TIPS, extra=popups)
        widget.event_generate("<Leave>")
        pump(0.2)

    def guarded(name, func, *args) -> None:
        try:
            func(*args)
        except Exception:
            print(f"[studio] scenario {name} failed:", flush=True)
            traceback.print_exc()

    # 1. Starting up, before Connect -------------------------------------------------
    pump(1.5)
    shot("studio/01-offline-at-start.png", "Just opened: ○ OFFLINE, no tabs yet, Connect enabled")

    # 2. Connect, load SPY, then a CALL tab with quotes held back -------------------
    studio._connect()
    assert pump(15, lambda: demo.connected and not getattr(studio, "_connect_inflight", False)), "demo did not connect"
    pump(0.5)
    studio.ticker_var.set("SPY")
    studio._load_ticker()
    assert pump(15, lambda: bool(studio.option_records)), "no option records"
    expiries = list(studio.expiration_combo["values"])
    spot = demo._spot.get("SPY", 600.0)
    first_expiry = studio.expiration_var.get()

    demo._emit_quotes = lambda: None  # quotes held back
    tab1 = load_tab("CALL", "594", "607", (1.0, 2.0, 3.0))
    pump(1.5)
    shot("studio/02-loaded-no-quotes-yet.png",
         "Matrix just loaded, no quotes yet: gray -- (no usable mid), chart waiting for live quotes")

    full_legs = dict(demo._subscribed_legs)
    few_legs = dict(sorted(full_legs.items(), key=lambda item: item[1].strike)[6:10])
    demo._subscribed_legs = few_legs  # only four neighbouring strikes quote at first
    del demo._emit_quotes
    demo._emit_quotes()
    pump(3)
    shot("studio/03-few-quotes-fair-value-waits.png",
         "Only four strikes quoted so far: fair value cannot be fitted yet (amber M … FV?), the rest still --")
    demo._subscribed_legs = full_legs
    pump(6)

    # 3. Three tabs live ---------------------------------------------------------------
    tab2 = load_tab("PUT", "593", "606", (1.0, 2.0, 3.0))
    pump(3)
    second_expiry = expiries[1] if len(expiries) > 1 else first_expiry
    tab3 = load_tab("BOTH", "595", "605", (1.0, 2.0), expiry=second_expiry)
    pump(6)

    key = signal_cell(tab1, lambda k: k[0] >= spot)
    studio._activate_matrix_tab(tab1.tab_id)
    if key is not None:
        select_cell(tab1, key)
    show_bottom("Signals")
    shot("studio/04-live-call-tab.png",
         "Live CALL tab: green B and red S signals, ink M mids, gray ITM rows, the selected cell with its "
         "detail chart, ranked signals below")
    studio._activate_matrix_tab(tab2.tab_id)
    key2 = signal_cell(tab2, lambda k: k[0] + k[1] <= spot)
    if key2 is not None:
        select_cell(tab2, key2)
    shot("studio/05-live-put-tab.png", "Live PUT tab")
    studio._activate_matrix_tab(tab3.tab_id)
    key3 = signal_cell(tab3, lambda k: True)
    if key3 is not None:
        select_cell(tab3, key3)
    shot("studio/06-live-both-tab.png", "Live BOTH tab (calls and puts) on the next expiry")

    def anomaly() -> None:
        found = None
        deadline = time.monotonic() + 30
        while (found is None or not found[2]) and time.monotonic() < deadline:
            pump(0.5)
            found = anomaly_cell() or found
        if found is None:
            print("[studio] no anomaly appeared", flush=True)
            return
        tab, cell, otm = found
        studio._activate_matrix_tab(tab.tab_id)
        select_cell(tab, cell)
        shot("studio/06b-anomaly-selected.png",
             "Violet B/S: an anomaly signal took priority over the fair-value label; the detail chart's ANOM row shows it"
             if otm else
             "Anomaly on an in-the-money cell: muted gray in the grid, violet in the detail chart's ANOM row")

    guarded("anomaly", anomaly)
    studio._activate_matrix_tab(tab1.tab_id)
    if key is not None:
        select_cell(tab1, key)

    # 4. Stream states on the CALL tab -------------------------------------------------
    def leg_con_id(tab, strike: float):
        for selection in tab.matrix_plan.visible.values():
            for leg in selection.legs:
                if abs(leg.contract.strike - strike) < 1e-6:
                    return leg.contract.con_id
        return None

    def stream_states() -> None:
        diagnostics = studio._subscription_diagnostics_by_con_id
        plan = ((595.0, "pending_subscribe", 0), (598.0, "desired", 0), (601.0, "failed", 1), (604.0, "failed", 3))
        for strike, state, failures in plan:
            con_id = leg_con_id(tab1, strike)
            if con_id is None:
                continue
            diagnostics[con_id] = SimpleNamespace(state=state, quote_kind="leg")
            if failures:
                studio._subscription_failure_counts[con_id] = failures
        OptionsMatrixApp._apply_active_subscription_styles(studio, tab1)
        studio._redraw_all()
        pump(0.5)
        shot("studio/07-stream-states.png",
             "Stream health: thick navy = pending (strike 595), dashed navy = syncing (598), hatch = failed (601), "
             "dense hatch = failing again (604), dashed amber = fair-value context degraded around them")
        studio._subscription_failure_counts.clear()
        demo._emit_diagnostics()
        pump(2)

    guarded("stream states", stream_states)

    # 5. Positions and exit alerts -------------------------------------------------------
    def positions() -> None:
        settings = studio.formula_settings

        def mid(key):
            snap = OptionsMatrixApp._tab_cell_snapshot(tab1, key)
            return None if snap is None else snap.synthetic_mid

        def record(key, side: str, average: float, armed: bool = True):
            selection = OptionsMatrixApp._tab_cell_selection(tab1, key)
            item = PositionRecord(position_key_for_selection(selection), side, round(max(0.01, average), 2), armed)
            studio._store_position(item)
            return item

        def edge(k):
            return fair_value_edge_for_width(k[1], settings)

        keys = sorted(tab1.matrix_plan.visible)
        otm = [k for k in keys if k[0] > spot + 0.5 and (mid(k) or 0) > 0.18]
        itm = [k for k in keys if k[0] + k[1] < spot - 0.5 and (mid(k) or 0) > 0.6]
        exit_buy, monitoring, paused = otm[0], otm[1 % len(otm)], otm[2 % len(otm)]
        exit_sell = itm[0]
        sell_legs = {exit_sell[0], round(exit_sell[0] + exit_sell[1], 4)}
        apart = [k for k in itm[1:] if k[0] not in sell_legs and round(k[0] + k[1], 4) not in sell_legs]
        waiting = apart[0] if apart else itm[-1]  # shares no leg with the EXIT SELL position
        buy = record(exit_buy, "SOLD", mid(exit_buy) + edge(exit_buy) + 0.30)
        record(exit_sell, "BOUGHT", mid(exit_sell) - edge(exit_sell) - 0.30)
        record(monitoring, "SOLD", mid(monitoring) - 0.12)
        record(paused, "SOLD", mid(paused) + 0.20, armed=False)
        record(waiting, "BOUGHT", mid(waiting))
        lower = tab1.matrix_plan.visible[keys[0]].pair.lower
        studio._store_position(PositionRecord((lower.symbol, lower.expiration, "CALL", 612.0, 613.0), "SOLD", 0.20))
        con_id = leg_con_id(tab1, waiting[0])
        if con_id is not None:  # its leg is not confirmed yet, so its exit alert waits
            studio._subscription_diagnostics_by_con_id[con_id] = SimpleNamespace(state="pending_subscribe", quote_kind="leg")
            OptionsMatrixApp._apply_active_subscription_styles(studio, tab1)
        pump(3)
        show_bottom("Positions / exit alerts")
        tree = studio.position_tree
        children = tree.get_children()
        if children:
            tree.selection_set(children[0])
        pump(0.5)
        shot("studio/08-positions-tab.png",
             "Positions / exit alerts: EXIT BUY and EXIT SELL (target reached, green and red rows), Monitoring, "
             "Paused by you, Paused - pair not loaded, Waiting for confirmed live quotes")

        demo._emit_diagnostics()
        pump(3)
        select_cell(tab1, exit_buy)
        show_bottom("Signals")
        shot("studio/09-position-dots-and-exits.png",
             "In the matrix: navy dots mark saved positions; EXIT BUY and EXIT SELL cells light up; "
             "the summary under the chart shows the selected position")

        studio._open_position_editor(buy.key)
        dialog = find_toplevel(root, "Position exit alert")
        pump(0.5)
        screen.window(dialog, "dialogs/studio-position-editor.png", "Position… editor for a saved position", G_DIALOGS)
        entry = next(w for w in descendants(dialog) if w.winfo_class() == "TEntry")
        entry.delete(0, "end")
        entry.insert(0, "abc")
        save = next(w for w in descendants(dialog) if w.winfo_class() == "TButton" and w.cget("text") == "Save position")
        save.invoke()
        pump(0.4)
        screen.window(dialog, "dialogs/studio-position-editor-error.png",
                      "Position… editor after saving “abc” as the average entry", G_DIALOGS)
        dialog.grab_release()
        dialog.destroy()
        pump(1)

    guarded("positions", positions)

    # 6. Recorder: Recording tab and the REC indicator -----------------------------------
    def recorder() -> None:
        show_bottom("Recording")
        for kind, caption in (
            ("off", "Recording tab: idle, ○ REC OFF"),
            ("starting", "Recording tab: starting, ● REC STARTING"),
            ("armed", "Recording tab: armed until the open, ● REC ARMED"),
            ("on", "Recording tab: recording with progress, ● REC ON"),
            ("stopping", "Recording tab: flushing rows, ● REC STOPPING"),
            ("error", "Recording tab: failed, ! REC ERROR"),
        ):
            set_recorder(kind)
            shot(f"studio/10-recording-{kind}.png", caption)
            bar_shot(f"indicators/studio-rec-{kind}.png", caption.split(", ")[-1], G_REC)
        set_recorder("off")
        set_connection("live")
        show_bottom("Signals")

    guarded("recorder", recorder)

    # 7. Top bar variations ------------------------------------------------------------------
    def top_bar() -> None:
        for kind, caption in (
            ("live", "● LIVE: streaming"),
            ("connecting", "◐ CONNECTING"),
            ("disconnecting", "◐ DISCONNECTING"),
            ("retry", "↻ RETRY 2/5 · 4s: reconnecting on its own"),
            ("stopped", "! RETRY STOPPED: gave up; press Connect"),
            ("offline", "○ OFFLINE"),
        ):
            set_connection(kind)
            pump(0.2)
            bar_shot(f"indicators/studio-connection-{kind}.png", caption, G_CONN)
        set_connection("live")
        for days, caption in ((1, "No badge: authorization current"), (5, "⚠ AUTH 2d"), (6, "⚠ AUTH 1d"),
                              (8, "⚠ AUTH DUE: run authorize_schwab.bat")):
            token["issued"] = datetime.now(timezone.utc) - timedelta(days=days, hours=1)
            OptionsMatrixApp._set_connected_state(studio, True)
            pump(0.2)
            bar_shot(f"indicators/studio-auth-{days}d.png", caption, G_AUTH)
        token["issued"] = datetime.now(timezone.utc) - timedelta(days=1)
        OptionsMatrixApp._set_connected_state(studio, True)
        share = one_desk.SHARING_GLYPH
        studio._update_studio_settings(share_enabled=False)
        pump(0.8)
        bar_shot("indicators/studio-share-off.png", f"{share} SHARING OFF", G_SHARE)
        studio._update_studio_settings(share_enabled=True)
        pump(1.5)
        bar_shot("indicators/studio-share-0.png", f"{share} 0 VIEWERS: sharing, nobody connected", G_SHARE)
        for text, name, caption in (
            (f"{share} SHARING ERROR", "error",
             f"{share} SHARING ERROR: sharing could not start (for example, the port is taken)"),
            (f"{share} 2 VIEWERS", "2", f"{share} 2 VIEWERS"),
        ):
            studio.share_indicator_var.set(text)
            pump(0.2)
            bar_shot(f"indicators/studio-share-{name}.png", caption, G_SHARE)
        studio.services._refresh_share_indicator()
        pump(0.2)
        previous = studio._market_data_quote_status
        bar_shot("indicators/studio-quotes-live.png", "Quote footprint: live legs (L), underlying (U), spreads (S)", G_QUOTES)
        studio._set_market_data_quote_status(None)
        pump(0.2)
        bar_shot("indicators/studio-quotes-none.png", "Quote footprint: nothing subscribed (LIVE --)", G_QUOTES)
        studio._set_market_data_quote_status(MarketDataQuoteStatus(
            current=MarketDataQuoteCounts(combo_quotes=48, leg_quotes=18),
            preview_total=MarketDataQuoteCounts(combo_quotes=60, leg_quotes=24),
            added=MarketDataQuoteCounts(combo_quotes=14, leg_quotes=7),
            removed=MarketDataQuoteCounts(combo_quotes=2, leg_quotes=1),
        ))
        pump(0.2)
        bar_shot("indicators/studio-quotes-pending.png", "Quote footprint with staged changes (PENDING ADD / REMOVE)", G_QUOTES)
        studio._set_market_data_quote_status(previous)
        pump(0.2)

        set_connection("retry")
        tooltip(studio.connection_status_label, "tooltips/studio-connection.png", "Connection badge tooltip (retrying)")
        set_connection("live")
        token["issued"] = datetime.now(timezone.utc) - timedelta(days=8, hours=1)
        OptionsMatrixApp._set_connected_state(studio, True)
        tooltip(studio.auth_status_label, "tooltips/studio-auth.png", "AUTH badge tooltip (overdue)")
        token["issued"] = datetime.now(timezone.utc) - timedelta(days=1)
        OptionsMatrixApp._set_connected_state(studio, True)
        tooltip(studio.market_data_quote_status_label, "tooltips/studio-quotes.png", "Quote footprint tooltip")
        tooltip(studio.share_indicator_label, "tooltips/studio-share.png", "Sharing badge tooltip")

    guarded("top bar", top_bar)

    # 8. Dialogs and pop-ups -------------------------------------------------------------------
    guarded("settings", open_settings, studio, screen, "studio", G_DIALOGS)

    def tab_error() -> None:
        studio.side_var.set("CALL")
        studio.low_strike_var.set("596")
        studio.high_strike_var.set("604")
        thread = screen.native_dialog("Matrix Tabs", "dialogs/studio-matrix-tabs-error.png",
                                      "Matrix Tabs error when a new tab overlaps an open one (native pop-up)", G_NATIVE)
        studio._load_matrix()
        thread.join(10)
        pump(0.3)

    guarded("tab error", tab_error)
    studio._set_status(LIVE_STATUS)
    studio._activate_matrix_tab(tab1.tab_id)
    if key is not None:
        select_cell(tab1, key)
    pump(1)

    # 9. Host the work PC ---------------------------------------------------------------------
    (control / "host.json").write_text(
        json.dumps({"port": port, "password": studio.studio_settings.share_password}), encoding="utf-8"
    )
    print(f"[studio] sharing on 127.0.0.1:{port}; waiting for the viewer", flush=True)

    def handle(command: dict) -> object:
        name = command.get("cmd")
        if name == "shot":
            shot(command["rel"], command["caption"], command.get("group", W))
            if command.get("bar"):
                bar_shot(command["bar"], command["bar_caption"], command.get("bar_group", G_SHARE))
            return None
        if name == "mini_pc_dialog":
            dialog = studio_dialog.StudioSettingsDialog(studio)
            dialog.dialog.geometry("+60+60")
            pump(2.5)
            screen.window(dialog.dialog, "dialogs/studio-mini-pc-settings.png",
                          "Mini PC… settings with one work PC connected (example address and names)", G_DIALOGS)
            dialog.close()
            pump(0.3)
            return None
        if name == "rec":
            set_recorder(command["state"])
            if command["state"] == "off":
                studio._set_status(LIVE_STATUS)
            return None
        if name == "auth":
            token["issued"] = datetime.now(timezone.utc) - timedelta(days=command["days"], hours=1)
            OptionsMatrixApp._set_connected_state(studio, True)
            pump(0.2)
            return None
        if name == "disconnect":
            set_recorder("off")
            studio._disconnect()
            pump(8, lambda: not demo.connected and all(tab.is_stale for tab in studio.matrix_tabs))
            pump(1.5)
            shot("studio/11-disconnected-stale-tabs.png",
                 "After Disconnect: ○ OFFLINE, tabs kept but stale, Reload matrix button")
            return None
        if name == "quit":
            return None
        raise ValueError(f"unknown command {name!r}")

    def finish() -> None:
        try:
            studio.recorder = None
            studio.stop_services()
            demo._stop.set()
        finally:
            shooter.close()
            root.destroy()

    def poll_commands() -> None:
        for command_file in sorted(control.glob("cmd-*.json")):
            number = command_file.stem.split("-", 1)[1]
            ack = control / f"ack-{number}.json"
            if ack.exists():
                continue
            command = json.loads(command_file.read_text(encoding="utf-8"))
            try:
                result = handle(command)
                ack.write_text(json.dumps({"ok": True, "result": result}), encoding="utf-8")
            except Exception as exc:
                traceback.print_exc()
                ack.write_text(json.dumps({"ok": False, "error": str(exc)}), encoding="utf-8")
            if command.get("cmd") == "quit":
                root.after(50, finish)
                return
        root.after(100, poll_commands)

    root.after(100, poll_commands)
    root.mainloop()


# --------------------------------------------------------------------------
# Work PC: Options Matrix Viewer
# --------------------------------------------------------------------------
def viewer_role(out: Path, control: Path) -> None:
    os.environ["OPTIONS_MATRIX_THEME"] = "light"
    socket.gethostname = lambda: "WORK-PC"
    sys.path.insert(0, str(MX_ROOT / "work_pc"))
    sys.path.insert(0, str(MX_ROOT / "mini_pc"))
    import tkinter as tk

    import options_matrix.app as app_module
    from options_matrix import one_desk
    from options_matrix.models import SIGNAL_BUY, SIGNAL_SELL, fair_value_edge_for_width
    from options_matrix.positions import PositionRecord, position_key_for_selection
    from options_matrix.share_protocol import math_fingerprint

    from matrix_viewer.client import EVENT_DISCONNECTED, EVENT_STOPPED
    from matrix_viewer.connection_dialog import ConnectionDialog
    from matrix_viewer.viewer_app import LINK_LIVE, ViewerApp
    from matrix_viewer.viewer_settings import ViewerSettings

    assert one_desk.MODE == "light", one_desk.MODE
    app_module.refresh_token_issued_at = lambda path=None: None
    host = json.loads((control / "host.json").read_text(encoding="utf-8"))
    port, password = int(host["port"]), str(host["password"])

    gc.collect()
    gc.disable()
    shooter = Shooter(out, "viewer")
    work = Path(tempfile.mkdtemp(prefix="viewer-", dir=control.parent))
    viewer = ViewerApp(settings_root=work)
    root = viewer.root
    root.geometry(GEOMETRY)
    screen = Screen(shooter, root)
    pump = screen.pump
    bar = viewer.connection_status_label.master
    counter = {"n": 0}

    W = "Viewer windows"
    G_LINK, G_RELAY = "Viewer top bar: link to the mini PC", "Viewer top bar: relayed from the mini PC"
    G_TIPS, G_DIALOGS, G_NATIVE = "Tooltips", "Dialogs", "Native Windows pop-ups"

    def shot(rel: str, caption: str, group: str = W) -> None:
        screen.window(root, rel, caption, group)

    def bar_shot(rel: str, caption: str, group: str) -> None:
        screen.widget(root, bar, rel, caption, group)

    def send(command: dict, timeout: float = 90.0) -> dict:
        counter["n"] += 1
        number = f"{counter['n']:03d}"
        (control / f"cmd-{number}.json").write_text(json.dumps(command), encoding="utf-8")
        ack = control / f"ack-{number}.json"
        deadline = time.monotonic() + timeout
        while not ack.exists() and time.monotonic() < deadline:
            root.update()
            time.sleep(0.05)
        if not ack.exists():
            raise TimeoutError(f"mini PC did not answer {command}")
        time.sleep(0.05)
        return json.loads(ack.read_text(encoding="utf-8"))

    def show_bottom(label: str) -> None:
        notebook, index = find_notebook(root, label)
        notebook.select(index)
        pump(0.2)

    def guarded(name, func, *args) -> None:
        try:
            func(*args)
        except Exception:
            print(f"[viewer] scenario {name} failed:", flush=True)
            traceback.print_exc()

    def live() -> bool:
        return viewer._link_state == LINK_LIVE and any(not tab.is_stale for tab in viewer.matrix_tabs)

    def connect(settings) -> None:
        viewer.apply_viewer_settings(settings, connect=True)

    settings_ok = ViewerSettings(host="127.0.0.1", port=port, password=password)

    # 1. Not set up yet ------------------------------------------------------------------------
    viewer.start_services()
    pump(1.5)
    shot("viewer/01-not-set-up.png", "First start: no connection settings yet, ○ OFFLINE, waiting for the mini PC")
    bar_shot("indicators/viewer-link-offline.png", "○ OFFLINE", G_LINK)

    def connection_dialog() -> None:
        dialog = ConnectionDialog(viewer)
        dialog.host.set("192.168.1.50")
        dialog.port.set("47210")
        dialog.password.set("example-password")
        pump(0.5)
        screen.window(dialog.dialog, "dialogs/viewer-connection.png", "Connection… (example address)", G_DIALOGS)
        dialog.host.set("")
        dialog._save()
        pump(0.3)
        screen.window(dialog.dialog, "dialogs/viewer-connection-error.png", "Connection… with a missing address", G_DIALOGS)
        dialog.dialog.grab_release()
        dialog.dialog.destroy()
        pump(0.3)

    guarded("connection dialog", connection_dialog)

    # 2. Connecting, then live --------------------------------------------------------------------
    viewer.apply_viewer_settings(settings_ok, connect=False)
    viewer._set_status("Connecting to the mini PC ...")
    viewer._poll_studio_messages = lambda: None  # hold the welcome so CONNECTING stays up
    viewer._start_client()
    pump(0.5)
    shot("viewer/02-connecting.png", "Connecting to the mini PC: ◐ CONNECTING")
    bar_shot("indicators/viewer-link-connecting.png", "◐ CONNECTING", G_LINK)
    del viewer._poll_studio_messages
    assert pump(20, live), "viewer never went live"
    pump(4)

    def first_signal(tab):
        items = tab.matrix_snapshots.items() if not tab.side_states else (
            ((right, *key), snap) for right, side in tab.side_states.items() for key, snap in side.matrix_snapshots.items()
        )
        for key, snap in list(items):
            if snap.opportunity_direction in (SIGNAL_BUY, SIGNAL_SELL):
                return key
        return None

    tab = viewer._active_tab() or viewer.matrix_tabs[0]
    key = first_signal(tab)
    if key is not None:
        tab.selected_cell_key = key
        viewer._sync_view_from_active_tab()
        viewer._redraw_all()
    pump(0.5)
    shot("viewer/03-live.png", "Live from the mini PC: ● LIVE, the mini PC's health line, the same tabs and signals")
    bar_shot("indicators/viewer-link-live.png", "● LIVE", G_LINK)
    send({"cmd": "shot", "rel": "studio/12-sharing-one-viewer.png",
          "caption": f"Mini PC with the work PC connected: {one_desk.SHARING_GLYPH} 1 VIEWER",
          "bar": "indicators/studio-share-1.png", "bar_caption": f"{one_desk.SHARING_GLYPH} 1 VIEWER (a real connection)"})
    send({"cmd": "mini_pc_dialog"})

    # 3. Narrowed view, the View pop-up, read-only settings ---------------------------------------
    def narrowed() -> None:
        strikes = list(viewer.view_low_combo["values"])
        if len(strikes) >= 6:
            viewer.view_low_var.set(strikes[2])
            viewer.view_high_var.set(strikes[-3])
        widths = list(viewer.view_width_vars)
        if len(widths) > 1:
            viewer.view_width_vars[widths[-1]].set(False)
        viewer._apply_view_from_controls()
        pump(1)
        shot("viewer/04-narrowed-view.png", "This PC's own narrower view: the tab name gets a *")
        viewer._reset_view_filter()
        pump(0.5)
        for variable in viewer.view_width_vars.values():
            variable.set(False)
        thread = screen.native_dialog("View", "dialogs/viewer-view-error.png",
                                      "View error when no width is ticked (native pop-up)", G_NATIVE)
        viewer._apply_view_from_controls()
        thread.join(10)
        viewer._refresh_view_controls()
        pump(0.5)

    guarded("narrowed view", narrowed)
    guarded("viewer settings", open_settings, viewer, screen, "viewer", G_DIALOGS, True)

    # 4. Positions on the work PC ------------------------------------------------------------------
    def positions() -> None:
        display = viewer._active_tab() or viewer.matrix_tabs[0]
        mirror = viewer._mirror_tabs.get(display.tab_id, display)
        settings = viewer.formula_settings
        keys = sorted(mirror.matrix_plan.visible)
        snaps = mirror.matrix_snapshots
        priced = [k for k in keys if snaps.get(k) is not None and (snaps[k].synthetic_mid or 0) > 0.18]
        if len(priced) < 2:
            print("[viewer] not enough priced cells for positions", flush=True)
            return
        exit_key, monitor_key = priced[len(priced) // 2], priced[-1]
        for k, average in ((exit_key, snaps[exit_key].synthetic_mid + fair_value_edge_for_width(exit_key[1], settings) + 0.30),
                           (monitor_key, snaps[monitor_key].synthetic_mid - 0.12)):
            selection = mirror.matrix_plan.visible[k]
            viewer._store_position(PositionRecord(position_key_for_selection(selection), "SOLD", round(max(0.01, average), 2)))
        pump(3)
        display.selected_cell_key = exit_key
        viewer._sync_view_from_active_tab()
        viewer._redraw_all()
        show_bottom("Positions / exit alerts")
        children = viewer.position_tree.get_children()
        if children:
            viewer.position_tree.selection_set(children[0])
        pump(0.5)
        shot("viewer/05-positions.png", "Work PC positions: EXIT BUY lit in the matrix, Monitoring in the list")
        show_bottom("Signals")

    guarded("positions", positions)

    # 5. What the mini PC relays: recorder and authorization ----------------------------------------
    def relayed() -> None:
        for state, caption in (("on", "● REC ON with rows saved"), ("armed", "● REC ARMED"),
                               ("error", "! REC ERROR"), ("off", "○ REC OFF")):
            send({"cmd": "rec", "state": state})
            pump(2.5)
            bar_shot(f"indicators/viewer-relay-rec-{state}.png", caption, G_RELAY)
        for days, caption in ((5, "⚠ AUTH 2d from the mini PC"),
                              (8, "⚠ AUTH DUE from the mini PC (red, as on the mini PC)")):
            send({"cmd": "auth", "days": days})
            pump(2.5)
            bar_shot(f"indicators/viewer-relay-auth-{days}d.png", caption, G_RELAY)
        send({"cmd": "rec", "state": "on"})
        send({"cmd": "auth", "days": 5})
        pump(2.5)
        shot("viewer/06-relayed-recording-and-auth.png", "Mini PC recording and due for re-authorization, shown on the work PC")
        send({"cmd": "rec", "state": "off"})
        send({"cmd": "auth", "days": 1})
        pump(2.5)

    guarded("relayed", relayed)

    # 6. Disconnect -----------------------------------------------------------------------------------
    def disconnect() -> None:
        viewer._disconnect()
        pump(1.0)
        shot("viewer/07-after-disconnect.png",
             "After Disconnect: ○ OFFLINE, Connect enabled again, prices hidden until you connect")
        bar_shot("indicators/viewer-after-disconnect.png", "After Disconnect: ○ OFFLINE, Connect enabled", G_LINK)
        connect(settings_ok)
        pump(15, live)
        pump(2)

    guarded("disconnect", disconnect)

    # 7. Mini PC loses market data --------------------------------------------------------------------
    def no_market_data() -> None:
        send({"cmd": "disconnect"})
        pump(4)
        shot("viewer/08-mini-pc-no-market-data.png",
             "Mini PC disconnected from Schwab: ◐ MINI PC: NO MARKET DATA, tabs waiting")
        bar_shot("indicators/viewer-link-no-market-data.png", "◐ MINI PC: NO MARKET DATA", G_LINK)

    guarded("no market data", no_market_data)

    # 8. Link trouble ---------------------------------------------------------------------------------
    def link_trouble() -> None:
        viewer._inbound.put((EVENT_DISCONNECTED, "The mini PC closed the connection."))
        pump(1.0)
        shot("viewer/09-reconnecting.png", "Link dropped: ↻ RECONNECTING, prices hidden until the mini PC answers")
        bar_shot("indicators/viewer-link-reconnecting.png", "↻ RECONNECTING", G_LINK)

        connect(ViewerSettings(host="127.0.0.1", port=port, password="not-the-password"))
        pump(10, lambda: viewer._link_stop_reason == "password")
        pump(0.6)
        shot("viewer/10-wrong-password.png", "Wrong password: ✕ WRONG PASSWORD")
        bar_shot("indicators/viewer-link-wrong-password.png", "✕ WRONG PASSWORD", G_LINK)
        viewer.connection_status_label.event_generate("<Enter>")
        pump(0.3)
        popups = [w for w in viewer.connection_status_label.winfo_children() if isinstance(w, tk.Toplevel)]
        screen.widget(root, bar, "tooltips/viewer-link.png", "Link badge tooltip (wrong password)", G_TIPS, extra=popups)
        viewer.connection_status_label.event_generate("<Leave>")

        viewer._local_fingerprint = "0" * 16
        connect(settings_ok)
        pump(10, lambda: viewer._link_stop_reason == "version")
        pump(0.6)
        shot("viewer/11-update-needed.png", "Different program versions: ⚠ UPDATE NEEDED")
        bar_shot("indicators/viewer-link-update-needed.png", "⚠ UPDATE NEEDED", G_LINK)
        viewer._local_fingerprint = math_fingerprint()

        viewer._handle_link_event(EVENT_STOPPED, ("", "The mini PC refused the connection."))
        viewer._set_connected_state(False)
        pump(0.6)
        bar_shot("indicators/viewer-link-not-connected.png", "✕ NOT CONNECTED: refused for another reason", G_LINK)

    guarded("link trouble", link_trouble)

    try:
        send({"cmd": "quit"}, timeout=20)
    except Exception:
        traceback.print_exc()
    viewer.stop_services()
    shooter.close()
    root.destroy()


# --------------------------------------------------------------------------
def run(out: Path) -> int:
    out = out.resolve()
    if out.parent != HERE / "out":  # it empties OUT_DIR, so only a folder under demos\out
        raise SystemExit(f"refusing to clear {out}")
    out.mkdir(parents=True, exist_ok=True)
    for child in out.iterdir():  # empty it; the folder itself may be some shell's working directory
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()
    base = Path(tempfile.mkdtemp(prefix="matrix-states-"))  # settings folders and the command files
    control = base / "control"
    control.mkdir()
    me = str(Path(__file__).resolve())
    studio = subprocess.Popen([str(MX_PYTHON), "-B", "-X", "utf8", me, "studio", str(out), str(control)])
    deadline = time.monotonic() + 420
    while not (control / "host.json").exists():
        if studio.poll() is not None:
            print("studio role exited early", flush=True)
            return 1
        if time.monotonic() > deadline:
            studio.kill()
            print("studio role timed out", flush=True)
            return 1
        time.sleep(0.5)
    viewer = subprocess.run([str(MX_PYTHON), "-B", "-X", "utf8", me, "viewer", str(out), str(control)], timeout=600)
    try:
        studio.wait(60)
    except subprocess.TimeoutExpired:
        studio.kill()
    subprocess.run([PIL_PYTHON, "-B", str(HERE / "matrix_sheets.py"), str(out)], check=False)
    shutil.rmtree(base, ignore_errors=True)
    return viewer.returncode or (studio.returncode or 0)


if __name__ == "__main__":
    mode = sys.argv[1]
    target = Path(sys.argv[2])
    if mode == "run":
        raise SystemExit(run(target))
    if mode == "studio":
        studio_role(target, Path(sys.argv[3]))
    elif mode == "viewer":
        viewer_role(target, Path(sys.argv[3]))
