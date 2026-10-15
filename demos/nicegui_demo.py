"""One Desk in NiceGUI: a Playback-style page built from the adapter.

From the Design folder:

    python demos/nicegui_demo.py        # then open http://127.0.0.1:8602

The "Dark mode" button switches Quasar's dark mode and re-renders the Plotly
figures with the dark template. Playback keeps its own time zone (Central,
unlabeled), so the times here carry no zone. All numbers are made-up examples.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from nicegui import ui  # noqa: E402

from onedesk import fmt, nicegui_theme, plotly_theme, status  # noqa: E402

PAIRS = ["74/75", "75/76", "76/77", "77/78", "78/79", "79/80", "80/81", "81/82"]
MID = [0.97, 0.94, 0.86, 0.55, 0.25, 0.11, 0.04, 0.02]
FAIR = [0.94, 0.91, 0.80, 0.57, 0.31, 0.13, 0.05, 0.02]
LOWER = [max(0.0, v - 0.05) for v in FAIR]
UPPER = [v + 0.05 for v in FAIR]
VOL = [28, 26, 24, 23, 21, 20, 19, 18.5, 18, 17, 16.5, 17, 18, 19.5, 18, 17, 16, 15.5, 15, 14.5,
       15, 16, 15, 14, 13.5, 13, 13.5, 14, 15, 16.5, 18, 19, 18, 17, 16, 17, 18.5, 20, 22, 24]
TIMES = [f"{8 + (30 + i * 10) // 60:02d}:{(30 + i * 10) % 60:02d}" for i in range(len(VOL))]
PLAYHEAD = "11:40"


def snapshot_figure(mode: str) -> dict:
    r = plotly_theme.roles(mode)
    return {
        "data": [
            {"type": "scatter", "x": PAIRS, "y": UPPER, "name": "Upper endpoint", "mode": "lines",
             "line": {"color": r["upper_endpoint"], "dash": "dash", "shape": "hvh", "width": 1.5}},
            {"type": "scatter", "x": PAIRS, "y": LOWER, "name": "Lower endpoint", "mode": "lines",
             "line": {"color": r["lower_endpoint"], "dash": "dash", "shape": "hvh", "width": 1.5}},
            {"type": "scatter", "x": PAIRS, "y": FAIR, "name": "Fair value", "mode": "lines+markers",
             "line": {"color": r["fair_value"]}, "marker": {"size": 5, "color": r["fair_value"]}},
            {"type": "scatter", "x": PAIRS, "y": MID, "name": "Synthetic mid", "mode": "lines+markers",
             "line": {"color": r["mid"], "dash": "dot", "width": 1}, "marker": {"size": 8, "color": r["mid"]},
             "hovertemplate": "%{x}<br>Mid %{y:.2f}<extra></extra>"},
            {"type": "scatter", "x": ["78/79"], "y": [0.21], "name": "Buy", "mode": "markers",
             "marker": {"symbol": "triangle-up", "size": 12, "color": r["buy"]}},
            {"type": "scatter", "x": ["76/77"], "y": [0.91], "name": "Sell", "mode": "markers",
             "marker": {"symbol": "triangle-down", "size": 12, "color": r["sell"]}},
        ],
        "layout": {
            "height": 300,
            "margin": {"t": 36},
            "xaxis": {"title": {"text": "Strike pair"}},
            "yaxis": {"title": {"text": "Mid price"}, "range": [0, 1.05], "tickformat": ".2f"},
            "shapes": [
                {"type": "rect", "xref": "x", "yref": "paper", "x0": -0.5, "x1": 3.4, "y0": 0, "y1": 1,
                 "fillcolor": r["itm"], "line": {"width": 0}, "layer": "below"},
                {"type": "line", "xref": "x", "yref": "paper", "x0": 3.4, "x1": 3.4, "y0": 0, "y1": 1,
                 "line": {"color": r["reference"], "dash": "dot", "width": 1}},
            ],
            "annotations": [{"text": "USO 77.40", "xref": "x", "yref": "paper", "x": 3.45, "y": 0.98,
                             "xanchor": "left", "showarrow": False}],
        },
    }


def indicator_figure(mode: str) -> dict:
    r = plotly_theme.roles(mode)
    return {
        "data": [{"type": "scatter", "x": TIMES, "y": VOL, "mode": "lines", "name": "5-min realized vol",
                  "line": {"color": r["count"]}, "hovertemplate": "%{x}<br>%{y:.1f}%<extra></extra>"}],
        "layout": {
            "height": 150, "margin": {"t": 8, "b": 28}, "showlegend": False,
            "yaxis": {"ticksuffix": "%", "range": [10, 30]},
            "xaxis": {"nticks": 6},
            "shapes": [{"type": "line", "xref": "x", "yref": "paper", "x0": PLAYHEAD, "x1": PLAYHEAD,
                        "y0": 0, "y1": 1, "line": {"color": r["playhead"], "dash": "dash", "width": 1.5}}],
        },
    }


nicegui_theme.apply()


@ui.page("/")
def index() -> None:
    dark = ui.dark_mode(False)
    state = {"mode": "light"}

    with ui.row().classes("w-full items-center no-wrap gap-2").style(
            "background: var(--od-surface); border-bottom: 1px solid var(--od-rule); padding: 6px 12px"):
        ui.html('<span style="display:inline-block;width:24px;height:24px;border-radius:var(--od-radius);'
                'background:var(--od-navy)"></span>', tag="span")
        ui.label("Market Synthetic Playback").classes("od-label").style(
            "font-size: var(--od-text-control); color: var(--od-ink)")
        ui.label(fmt.join("USO", "Tue Jul 21 '26", fmt.plural(76, "file"))).classes("od-ink2").style(
            "border-left: 1px solid var(--od-rule); padding-left: 10px")
        ui.space()
        nicegui_theme.status_tag(status.Status("Cache ready", "ok"))
        nicegui_theme.status_tag(status.Status("Needs sync", "warn", "2", glyph=status.WORKING_GLYPH))
        ui.button("Open…").props("outline dense")
        ui.button("Market library…").props("outline dense")
        mode_button = ui.button("Dark mode").props("flat dense")

    with ui.row().classes("w-full no-wrap items-start gap-3").style("padding: 12px"):
        with ui.column().classes("gap-3").style("width: 240px; flex: none"):
            with ui.card().classes("w-full gap-2"):
                ui.label("Filters").classes("od-label")
                ui.select(["USO"], value="USO", label="Ticker").props("dense outlined options-dense").classes("w-full")
                ui.select(["Tue Jul 21 '26"], value="Tue Jul 21 '26", label="Date").props(
                    "dense outlined options-dense").classes("w-full")
                with ui.row().classes("w-full no-wrap gap-2"):
                    ui.select(["Call", "Put"], value="Call", label="Right").props("dense outlined").classes("w-1/2")
                    ui.select([fmt.width(1), fmt.width(2)], value=fmt.width(1), label="Width").props(
                        "dense outlined").classes("w-1/2")
                ui.button("Apply").props("unelevated color=primary").classes("w-full")
            with ui.card().classes("w-full gap-2"):
                ui.label("Chart layers").classes("od-label")
                ui.toggle(["Curve", "Sizing"], value="Curve").props("dense unelevated")
                ui.checkbox("Synthetic mid", value=True)
            with ui.card().classes("w-full gap-2"):
                ui.label("Methodology").classes("od-label")
                ui.select(["Reference bands · v1.0.0"], value="Reference bands · v1.0.0",
                          label="Cached result").props("dense outlined").classes("w-full")
                nicegui_theme.status_tag(status.ready("12,345 rows"))
                ui.button("Import / sync…").props("outline dense").classes("w-full")

        with ui.column().classes("gap-3").style("flex: 1; min-width: 0"):
            with ui.card().classes("w-full gap-1"):
                with ui.row().classes("items-center gap-2"):
                    ui.label("Snapshot").classes("od-label")
                    ui.label("11:42:10.25").classes("od-num")
                snapshot = ui.plotly(nicegui_theme.figure(snapshot_figure("light"))).classes("w-full")
            with ui.card().classes("w-full gap-1"):
                with ui.row().classes("items-center gap-2"):
                    ui.label("5-min realized vol").classes("od-label")
                    ui.label(fmt.percent(14.6)).classes("od-num")
                indicator = ui.plotly(nicegui_theme.figure(indicator_figure("light"))).classes("w-full")
            with ui.card().classes("w-full gap-2"):
                ui.label("Market library").classes("od-label")
                ui.aggrid({
                    "columnDefs": [
                        {"headerName": "Name", "field": "name", "flex": 2},
                        {"headerName": "Files", "field": "files", "type": "rightAligned", "cellClass": "od-num"},
                        {"headerName": "Last sync", "field": "synced", "cellClass": "od-num"},
                        {"headerName": "Status", "field": "status"},
                    ],
                    "rowData": [
                        {"name": "2026-07-20 USO", "files": 21, "synced": "Jul 23 '26 15:03", "status": "Ready"},
                        {"name": "2026-07-21 USO", "files": 76, "synced": "Jul 23 '26 16:41", "status": "Needs sync"},
                    ],
                    "rowSelection": {"mode": "multiRow"},
                }).classes("w-full").style("height: 140px")
                ui.label("Status tags").classes("od-label")
                nicegui_theme.status_tags([
                    status.live("mini PC"), status.reconnecting("2/5"), status.needs("Source changed"),
                    status.failed("Blocked", "1"), status.offline(), status.stale("cache"), status.demo(),
                ])

    with ui.row().classes("w-full items-center gap-3").style(
            "background: var(--od-surface); border-top: 1px solid var(--od-rule); padding: 3px 12px;"
            "font-size: var(--od-text-caption); color: var(--od-ink-2)"):
        ui.label("Loaded 2,412,800 rows from 76 files from the Playback cache in " + fmt.elapsed(1.84))
        ui.space()
        ui.label(fmt.join("Frame 11,531 / 23,400", "v1.2.0")).classes("od-num")

    def toggle_mode() -> None:
        state["mode"] = "dark" if state["mode"] == "light" else "light"
        dark.set_value(state["mode"] == "dark")
        snapshot.update_figure(nicegui_theme.figure(snapshot_figure(state["mode"]), state["mode"]))
        indicator.update_figure(nicegui_theme.figure(indicator_figure(state["mode"]), state["mode"]))
        mode_button.set_text("Light mode" if state["mode"] == "dark" else "Dark mode")

    mode_button.on_click(toggle_mode)


if __name__ in {"__main__", "__mp_main__"}:
    ui.run(host="127.0.0.1", port=8602, show=False, reload=False, title="One Desk · NiceGUI demo",
           dark=nicegui_theme.dark_setting("light"))
