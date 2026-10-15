"""One Desk in Tkinter: an Options Matrix Viewer-style window built only from the adapter.

    python demos/tk_demo.py                       # light
    python demos/tk_demo.py --mode dark           # or auto
    python demos/tk_demo.py --screenshot demos/out/tk
        # saves tk-light.png, switches live to dark, saves tk-dark.png, then exits

All numbers are made-up examples.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import tkinter as tk  # noqa: E402
from tkinter import ttk  # noqa: E402

from onedesk import fmt, status, tk_theme  # noqa: E402

STRIKES = [74, 75, 76, 77, 78, 79, 80]
WIDTHS = [1.0, 2.0, 3.0]
UNDERLYING = 77.40
MIDS = {
    (74, 1): 0.97, (74, 2): 1.93, (74, 3): 2.80,
    (75, 1): 0.94, (75, 2): 1.79, (75, 3): 2.37,
    (76, 1): 0.83, (76, 2): 1.40, (76, 3): 1.60,
    (77, 1): 0.55, (77, 2): 0.86, (77, 3): 0.94,
    (78, 1): 0.25, (78, 2): 0.39, (78, 3): 0.43,
    (79, 1): 0.11, (79, 2): 0.15, (79, 3): None,
    (80, 1): 0.04, (80, 2): 0.06, (80, 3): None,
}
SIGNALS = {(77, 2): ("S", 0.05), (78, 1): ("B", 0.04)}
EXITS = {(76, 3)}
FV_WAITING = {(78, 2)}
FAILED = {(79, 3)}
WAITING = {(80, 3)}
POSITIONS = {(76, 3), (80, 1)}
SELECTED = (78, 1)
POSITION_ROWS = [
    ("hit", ("USO Oct 17 '26 C 76/79", "Sold", "1.78", "0.17", "1.61", "1.60", "+0.18", "EXIT BUY — target reached")),
    ("", ("USO Oct 17 '26 C 80/81", "Bought", "0.03", "0.10", "0.13", "0.04", "+0.01", "Monitoring")),
    ("off", ("USO Oct 24 '26 P 76/77", "Sold", "0.40", "0.10", "0.30", fmt.MISSING, fmt.MISSING, "Paused — pair not loaded")),
]


def gauge_values(strike: int, width: int) -> tuple[float, float, float]:
    """Deterministic made-up (bracket, bid, ask) fractions for the liquidity gauge."""
    seed = (strike * 7 + width * 13) % 17
    return 0.15 + seed / 40, 0.25 + (seed % 5) / 10, 0.2 + ((seed * 3) % 6) / 12


class ViewerDemo:
    def __init__(self, root: tk.Tk, theme: tk_theme.TkTheme) -> None:
        self.root, self.theme = root, theme
        root.title("Options Matrix Viewer (work PC)")
        root.geometry("1040x700")
        root.minsize(1040, 620)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(4, weight=1)

        self._build_app_bar()
        self._build_banner()
        self._build_strip()
        self._build_chips()
        self.matrix = tk.Canvas(root, highlightthickness=0, bd=0)
        self.matrix.grid(row=4, column=0, sticky="nsew", padx=10, pady=(8, 0))
        self.matrix.bind("<Configure>", lambda _e: self.draw_matrix())
        self._build_tray()
        self._build_status_bar()
        theme.on_mode_change(self.on_mode_change)
        self.on_mode_change(theme)

    # -- app bar ------------------------------------------------------------------
    def _build_app_bar(self) -> None:
        t = self.theme
        bar = ttk.Frame(self.root, style="AppBar.TFrame", padding=(10, 6))
        bar.grid(row=0, column=0, sticky="ew")
        self.mark = tk.Canvas(bar, width=24, height=24, highlightthickness=0, bd=0)
        self.mark.pack(side="left")
        ttk.Label(bar, text="OPTIONS MATRIX VIEWER", style="AppName.Surface.TLabel").pack(side="left", padx=(9, 4))
        ttk.Label(bar, text="work PC", style="Muted.Surface.TLabel").pack(side="left")
        ttk.Separator(bar, orient="vertical").pack(side="left", fill="y", padx=10)
        ttk.Label(bar, text=fmt.join("USO", "Oct 17 '26", "C 74–81"), style="Ink2.Surface.TLabel").pack(side="left")
        self.mode_button = ttk.Button(bar, text="Dark mode", style="Ghost.TButton", command=self.theme.toggle)
        self.mode_button.pack(side="right", padx=(6, 0))
        ttk.Button(bar, text="Settings…").pack(side="right", padx=(6, 0))
        ttk.Button(bar, text="Connection…").pack(side="right", padx=(6, 0))
        for item in reversed([status.live("mini PC"), status.recording("12,345 rows"), status.needs("Auth", "2d")]):
            t.tag(bar, item).pack(side="right", padx=(6, 0))

    def draw_mark(self) -> None:
        p = self.theme.palette
        c = self.mark
        c.delete("all")
        c.configure(background=p.surface)
        c.create_rectangle(0, 0, 24, 24, fill=p.navy, outline="")
        dim = p.mix("on_navy", "navy", 0.5)
        for row in range(3):
            for col in range(3):
                x, y = 4 + col * 6, 4 + row * 6
                fill = p.on_navy if (row, col) == (1, 1) else dim
                c.create_rectangle(x, y, x + 4, y + 4, fill=fill, outline="")

    # -- exit banner --------------------------------------------------------------------
    def _build_banner(self) -> None:
        p = self.theme.palette
        self.banner = tk.Frame(self.root, background=p.up_tint, highlightthickness=0, padx=12, pady=6)
        self.banner.grid(row=1, column=0, sticky="ew")
        tk.Label(self.banner, text="EXIT BUY", background=p.up_tint, foreground=p.up,
                 font=self.theme.font_name("label")).pack(side="left")
        message = fmt.join("USO Oct 17 '26 C 76/79", f"mid {fmt.price(1.60)} is at or below target {fmt.price(1.61)}",
                           f"sold avg {fmt.price(1.78)}")
        tk.Label(self.banner, text=message, background=p.up_tint, foreground=p.ink).pack(side="left", padx=(12, 0))
        ttk.Button(self.banner, text="Show position").pack(side="right")

    # -- control strip -----------------------------------------------------------------
    def _build_strip(self) -> None:
        strip = ttk.Frame(self.root, style="Strip.TFrame", padding=(10, 6))
        strip.grid(row=2, column=0, sticky="ew")
        ttk.Label(strip, text="VIEW", style="Caps.Raised.TLabel").pack(side="left", padx=(0, 14))
        for label, values, value, width in (("SIDE", ["Calls", "Puts", "Both"], "Calls", 7),
                                            ("LOW", ["74", "75", "76"], "74", 5),
                                            ("HIGH", ["79", "80", "81"], "81", 5)):
            ttk.Label(strip, text=label, style="Caps.Raised.TLabel").pack(side="left", padx=(0, 5))
            box = ttk.Combobox(strip, values=values, width=width, state="readonly")
            box.set(value)
            box.pack(side="left", padx=(0, 12))
        ttk.Label(strip, text="WIDTHS", style="Caps.Raised.TLabel").pack(side="left", padx=(0, 5))
        self.width_vars = []
        for w in WIDTHS:
            var = tk.BooleanVar(value=True)
            self.width_vars.append(var)
            ttk.Checkbutton(strip, text=fmt.width(w), variable=var, style="Raised.TCheckbutton").pack(side="left", padx=(0, 6))
        ttk.Button(strip, text="Apply view", style="Primary.TButton").pack(side="left", padx=(10, 6))
        ttk.Button(strip, text="Show all").pack(side="left")

    # -- tab chips -----------------------------------------------------------------------
    def _build_chips(self) -> None:
        p = self.theme.palette
        row = tk.Frame(self.root, background=p.surface, padx=10, pady=6)
        row.grid(row=3, column=0, sticky="ew")
        self.chips = []
        for i, text in enumerate(["Oct 17 '26 C 74–81", "Oct 24 '26 P 72–79", "Oct 24 '26 C/P 75–80"]):
            active = i == 0
            chip = tk.Label(row, text=text, font=self.theme.font_name("num"), padx=9, pady=3,
                            background=p.navy_tint if active else p.raised,
                            foreground=p.ink if active else p.ink_2,
                            highlightthickness=2 if active else 1,
                            highlightbackground=p.navy if active else p.rule)
            chip.pack(side="left", padx=(0, 6))
            self.chips.append(chip)

    # -- matrix ----------------------------------------------------------------------------
    def draw_matrix(self) -> None:
        t, p, c = self.theme, self.theme.palette, self.matrix
        c.delete("all")
        c.configure(background=p.surface)
        width = max(c.winfo_width(), 900)
        strike_w, combo_w = 56, 86
        signal_w = (width - strike_w - combo_w * len(WIDTHS)) / len(WIDTHS) - 1
        head_h = 24
        row_h = t.row_height("matrix")
        label_font, num_font = t.font_name("label"), t.font_name("num")
        strong_font = t.font_name("num_strong")
        num = t.fonts["num"]

        def group_x(i: int) -> float:
            return strike_w + i * (combo_w + signal_w)

        # Headers.
        c.create_rectangle(0, 0, width, head_h * 2, fill=p.raised, outline="")
        c.create_text(strike_w / 2, head_h, text="STRIKE", font=label_font, fill=p.muted)
        for i, w in enumerate(WIDTHS):
            x = group_x(i)
            c.create_text(x + (combo_w + signal_w) / 2, head_h / 2, text=fmt.width(w), font=num_font, fill=p.ink)
            c.create_text(x + combo_w / 2, head_h * 1.5, text="COMBO", font=label_font, fill=p.muted)
            c.create_text(x + combo_w + signal_w / 2, head_h * 1.5, text="SIGNAL / PRICE", font=label_font, fill=p.muted)
            c.create_line(x, 0, x, head_h * 2, fill=p.rule)
            c.create_line(x, head_h, x + combo_w + signal_w, head_h, fill=p.rule)
            c.create_line(x + combo_w, head_h, x + combo_w, head_h * 2, fill=p.rule)
        c.create_line(0, head_h * 2, width, head_h * 2, fill=p.rule_strong)

        # Rows.
        for r, strike in enumerate(STRIKES):
            y0 = head_h * 2 + r * row_h
            y1 = y0 + row_h
            itm = strike < UNDERLYING
            c.create_rectangle(0, y0, strike_w, y1, fill=p.raised, outline="")
            c.create_text(strike_w / 2, (y0 + y1) / 2, text=fmt.strike(strike), font=strong_font, fill=p.ink)
            for i, w in enumerate(WIDTHS):
                key = (strike, int(w))
                x = group_x(i)
                cell_fill = p.itm if itm else p.surface
                c.create_rectangle(x, y0, x + combo_w, y1, fill=cell_fill, outline="")
                sx0, sx1 = x + combo_w, x + combo_w + signal_w
                signal_fill = p.up_tint if key in EXITS else (p.navy_tint if key == SELECTED else cell_fill)
                c.create_rectangle(sx0, y0, sx1, y1, fill=signal_fill, outline="")
                mid_y = (y0 + y1) / 2
                if key in POSITIONS:
                    c.create_text(x + 8, mid_y, text="●", font=t.font_name("ui_small"), fill=p.navy)
                text_color = p.ink_2 if itm else p.ink
                c.create_text(x + 18, mid_y, text=fmt.pair(strike, strike + int(w)), anchor="w",
                              font=num_font, fill=text_color)
                tx = sx0 + 8
                if key in FAILED:
                    tk_theme.draw_hatch(c, sx0 + 1, y0 + 1, sx1 - 1, y1 - 1, color=p.hatch)
                    c.create_text(tx, mid_y, text=fmt.MISSING, anchor="w", font=num_font, fill=p.muted)
                    continue
                if key in WAITING:
                    c.create_text(tx, mid_y, text=fmt.ELLIPSIS, anchor="w", font=num_font, fill=p.muted)
                    continue
                mid = MIDS[key]
                if key in EXITS:
                    c.create_text(tx, mid_y, text=f"EXIT BUY {fmt.price(mid)}", anchor="w", font=strong_font, fill=p.up)
                elif key in SIGNALS:
                    letter, edge = SIGNALS[key]
                    main = f"{letter} {fmt.price(mid)}"
                    c.create_text(tx, mid_y, text=main, anchor="w", font=strong_font,
                                  fill=p.up if letter == "B" else p.down)
                    c.create_text(tx + num.measure(main + " "), mid_y, text=f"({fmt.price(edge)})", anchor="w",
                                  font=num_font, fill=p.muted)
                else:
                    main = f"M {fmt.price(mid)}"
                    c.create_text(tx, mid_y, text=main, anchor="w", font=num_font, fill=text_color)
                    if key in FV_WAITING:
                        c.create_text(tx + num.measure(main + " "), mid_y, text="FV?", anchor="w",
                                      font=num_font, fill=p.model)
                self._gauge(sx1 - 34, mid_y, *gauge_values(strike, int(w)))
                if key == SELECTED:
                    c.create_rectangle(sx0 + 1, y0 + 1, sx1 - 1, y1 - 1, outline=p.navy, width=2)
            c.create_line(0, y1, width, y1, fill=p.rule)
        for i in range(len(WIDTHS)):
            x = group_x(i)
            c.create_line(x, head_h * 2, x, head_h * 2 + len(STRIKES) * row_h, fill=p.rule_strong)
            c.create_line(x + combo_w, head_h * 2, x + combo_w, head_h * 2 + len(STRIKES) * row_h, fill=p.rule)

    def _gauge(self, x: float, mid_y: float, bracket: float, bid: float, ask: float) -> None:
        p, c, w = self.theme.palette, self.matrix, 26
        top = mid_y - 5
        bx = w * min(bracket, 1.0)
        c.create_line(x, top, x + bx, top, fill=p.quote_2)
        c.create_line(x, top - 2, x, top + 3, fill=p.quote_2)
        c.create_line(x + bx, top - 2, x + bx, top + 3, fill=p.quote_2)
        center = x + w / 2
        c.create_rectangle(center - (w / 2) * bid, mid_y + 3, center, mid_y + 7, fill=p.quote, outline="")
        c.create_rectangle(center, mid_y + 3, center + (w / 2) * ask, mid_y + 7, fill=p.quote_2, outline="")
        c.create_line(center, mid_y + 1, center, mid_y + 8, fill=p.rule_strong)

    # -- tray ----------------------------------------------------------------------------
    def _build_tray(self) -> None:
        tray = ttk.Notebook(self.root)
        tray.grid(row=5, column=0, sticky="ew", padx=10, pady=(8, 0))
        signals = ttk.Frame(tray, style="Surface.TFrame", padding=0)
        positions = ttk.Frame(tray, style="Surface.TFrame", padding=0)
        tray.add(signals, text="Signals")
        tray.add(positions, text="Positions / exit alerts")
        tray.select(positions)

        cols = ("position", "entry", "avg", "edge", "target", "mid", "move", "status")
        heads = ("POSITION", "ENTRY", "AVG", "EDGE", "EXIT TARGET", "MID", "MOVE", "STATUS")
        widths = (210, 70, 70, 70, 100, 70, 80, 240)
        self.positions = ttk.Treeview(positions, columns=cols, show="headings", height=3)
        for col, head, width in zip(cols, heads, widths):
            anchor = "w" if col in ("position", "status") else "e"
            self.positions.heading(col, text=head, anchor=anchor)
            self.positions.column(col, width=width, anchor=anchor, stretch=col in ("position", "status"))
        for tag, values in POSITION_ROWS:
            self.positions.insert("", "end", values=values, tags=(tag,) if tag else ())
        self.positions.pack(fill="both", expand=True)

        self.signals = ttk.Treeview(signals, columns=("rank", "combo", "width", "signal", "price", "edge"),
                                    show="headings", height=3)
        for col, head in zip(self.signals["columns"], ("RANK", "COMBO", "WIDTH", "SIGNAL", "PRICE", "EDGE")):
            self.signals.heading(col, text=head)
            self.signals.column(col, width=110, anchor="e")
        self.signals.insert("", "end", values=("1", "78/79", fmt.width(1), "BUY", "0.25", "0.04"), tags=("buy",))
        self.signals.insert("", "end", values=("2", "77/79", fmt.width(2), "SELL", "0.86", "0.05"), tags=("sell",))
        self.signals.pack(fill="both", expand=True)

    def _tag_rows(self) -> None:
        p = self.theme.palette
        self.positions.tag_configure("hit", background=p.up_tint, foreground=p.up)
        self.positions.tag_configure("off", foreground=p.muted)
        self.signals.tag_configure("buy", foreground=p.up)
        self.signals.tag_configure("sell", foreground=p.down)

    # -- status bar ------------------------------------------------------------------------
    def _build_status_bar(self) -> None:
        bar = ttk.Frame(self.root, style="StatusBar.TFrame", padding=(10, 3))
        bar.grid(row=6, column=0, sticky="ew", pady=(8, 0))
        ttk.Label(bar, text="Showing Oct 17 '26 calls 74–81 at three widths", style="Status.Surface.TLabel").pack(side="left")
        right = fmt.join("mini PC 192.168.1.50:47210", "NYSE open, closes 4:00 PM ET", "12:42:10 ET")
        ttk.Label(bar, text=right, style="Status.Surface.TLabel").pack(side="right")

    def on_mode_change(self, theme: tk_theme.TkTheme) -> None:
        self.mode_button.configure(text="Light mode" if theme.mode == "dark" else "Dark mode")
        self.draw_mark()
        self.draw_matrix()
        self._tag_rows()


def capture(root: tk.Tk, path: Path) -> None:
    from PIL import ImageGrab

    root.update()
    x, y = root.winfo_rootx(), root.winfo_rooty()
    w, h = root.winfo_width(), root.winfo_height()
    path.parent.mkdir(parents=True, exist_ok=True)
    ImageGrab.grab(bbox=(x, y, x + w, y + h), all_screens=True).save(path)
    print(f"saved {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--mode", choices=["light", "dark", "auto"], default="light")
    parser.add_argument("--screenshot", metavar="PREFIX", help="save PREFIX-light.png and PREFIX-dark.png, then exit")
    args = parser.parse_args()

    tk_theme.enable_dpi_awareness()
    root = tk.Tk()
    theme = tk_theme.apply(root, mode="light" if args.screenshot else args.mode)
    ViewerDemo(root, theme)

    if args.screenshot:
        prefix = Path(args.screenshot)
        root.attributes("-topmost", True)

        def shoot_light() -> None:
            capture(root, prefix.with_name(prefix.name + "-light.png"))
            theme.set_mode("dark")
            root.after(700, shoot_dark)

        def shoot_dark() -> None:
            capture(root, prefix.with_name(prefix.name + "-dark.png"))
            root.destroy()

        root.after(1200, shoot_light)
    root.mainloop()


if __name__ == "__main__":
    main()
