"""One Desk in Streamlit: an Order Parser-style Day page built from the adapter.

From the Design folder:

    python -m onedesk.streamlit_theme --write .streamlit/config.toml
    python -m streamlit run demos/streamlit_demo.py

Switch light/dark from Streamlit's settings menu (top right). All numbers are made-up examples.
"""

from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402

from onedesk import fmt, plotly_theme, status, streamlit_theme  # noqa: E402

st.set_page_config(page_title="USO scalp dashboard", layout="wide")
mode = streamlit_theme.inject()
roles = plotly_theme.roles(mode)
DAY = dt.date(2026, 10, 13)

# -- app bar: name, context, status tags -------------------------------------------------
tags = streamlit_theme.status_tags_html([
    status.Status("Checks ok", "ok", "11"),
    status.Status("390 pace", "ok", "343/day"),
])
st.markdown(f"""
<div class="od-panel" style="display:flex;align-items:center;gap:10px;padding:8px 12px;margin-bottom:4px">
  <span style="width:24px;height:24px;border-radius:var(--od-radius);background:var(--od-navy);flex:none"></span>
  <span class="od-label" style="font-size:var(--od-text-control);color:var(--od-ink)">USO scalp dashboard</span>
  <span class="od-ink2" style="border-left:1px solid var(--od-rule);padding-left:10px">
    {fmt.join("USO", fmt.session_date(DAY), "Flat-to-flat runs")}</span>
  <span style="flex:1"></span>{tags}
</div>""", unsafe_allow_html=True)

st.segmented_control("Section", ["Day", "390 Rule", "Fees", "Execution", "History", "Data health"],
                     default="Day", label_visibility="collapsed")

# -- sidebar rail -------------------------------------------------------------------------------
with st.sidebar:
    st.markdown('<div class="od-label">Trading day</div>', unsafe_allow_html=True)
    st.selectbox("Trading day", [fmt.session_date(DAY), fmt.session_date(DAY - dt.timedelta(days=1))],
                 label_visibility="collapsed")
    st.markdown('<div class="od-label">Trade definition</div>', unsafe_allow_html=True)
    st.radio("Trade definition", ["Flat-to-flat runs", "FIFO round trips"], label_visibility="collapsed")
    st.markdown('<div class="od-label">Import</div>', unsafe_allow_html=True)
    streamlit_theme.status_tags(status.Status("Up to date", "ok", fmt.plural(41, "file")))
    st.button("Rescan statements", use_container_width=True)

# -- readouts -----------------------------------------------------------------------------------
st.markdown(f'<div class="od-title" style="font-size:var(--od-text-heading)">Daily performance</div>'
            f'<div class="od-muted">{fmt.join(fmt.session_date(DAY), "USO options only", "net of fees")}</div>',
            unsafe_allow_html=True)


def readout(label: str, value: str, detail: str, tone: str = "") -> str:
    return (f'<div class="od-panel" style="padding:10px 12px"><div class="od-label">{label}</div>'
            f'<div class="od-readout {tone}">{value}</div>'
            f'<div class="od-muted" style="font-size:var(--od-text-caption)">{detail}</div></div>')


cols = st.columns(4)
cards = [
    readout("USO net P&amp;L", fmt.pnl(412.50), "Net of all fees", "od-up"),
    readout("USO fees", fmt.fee(86.40), f"{fmt.percent(17.3)} of gross", "od-down"),
    readout("Trades", fmt.count(37), fmt.join("22 wins", "15 losses")),
    readout("Orders placed", fmt.count(412), fmt.join("198 filled", "211 canceled")),
]
for col, card in zip(cols, cards):
    col.markdown(card, unsafe_allow_html=True)

# -- charts -------------------------------------------------------------------------------------
minutes = [1, 8, 15, 24, 33, 45, 58, 70, 85, 99, 118, 135, 150, 172, 190, 208, 228, 247, 266, 290, 312, 334, 360, 384]
net = [0, 12, 30, 22, 48, 75, 66, 90, 118, 104, 140, 168, 150, 190, 230, 214, 260, 288, 270, 310, 352, 338, 384, 412.5]
open_time = dt.datetime.combine(DAY, dt.time(9, 30))
times = [open_time + dt.timedelta(minutes=m) for m in minutes]
left, right = st.columns([1.6, 1])
with left:
    fig = go.Figure(go.Scatter(x=times, y=net, mode="lines+markers", line={"color": roles["gain"]},
                               marker={"size": 6, "color": roles["gain"]}, name="Net",
                               hovertemplate="%{x|%H:%M:%S}<br>%{y:$,.2f}<extra></extra>"))
    fig.update_layout(title={"text": "Realized P&L through the day"}, height=300, showlegend=False,
                      yaxis={"tickprefix": "$"}, xaxis={"tickformat": "%H:%M"})
    streamlit_theme.plotly_chart(fig, mode)
with right:
    spreads = {"76/77 C": 186.20, "77/78 C": 142.80, "75/76 C": 96.40, "78/79 C": 31.10,
               "77/78 P": -20.60, "78/79 P": -23.40}
    bar = go.Figure(go.Bar(y=list(spreads), x=list(spreads.values()), orientation="h",
                           marker={"color": [roles["gain"] if v > 0 else roles["loss"] for v in spreads.values()]},
                           text=[fmt.pnl(v) for v in spreads.values()], textposition="outside", cliponaxis=False,
                           hovertemplate="%{y}: %{x:$,.2f}<extra></extra>"))
    bar.update_layout(title={"text": "Net by spread"}, height=300, showlegend=False, margin={"r": 64},
                      yaxis={"autorange": "reversed"},
                      xaxis={"tickprefix": "$", "range": [-90, 230], "zeroline": True})
    streamlit_theme.plotly_chart(bar, mode)

# -- status grammar and Streamlit's own alerts ---------------------------------------------------------
st.markdown('<div class="od-label">Status tags</div>', unsafe_allow_html=True)
streamlit_theme.status_tags(
    status.live("mini PC"), status.connecting(), status.reconnecting("2/5"), status.offline(),
    status.needs("Needs review", "2"), status.failed("Over 390", "396/day"), status.recording("12,345 rows"),
    status.hit("Exit buy", "target reached"), status.stale("no report"), status.no_data(), status.demo(),
)
a, b = st.columns(2)
with a:
    st.success("All 11 checks passed for " + fmt.session_date(DAY) + ".")
    st.warning("2 checks need review. Open Data health for the details.")
with b:
    st.error("Running balance checksum failed: " + fmt.money(-12.34) + " unexplained.")
    st.info("3 non-USO orders were left out of this view.")

st.markdown('<div class="od-label">Trade log</div>', unsafe_allow_html=True)
st.dataframe(
    {
        "Entry": ["09:31:12", "09:38:40", "09:45:03"],
        "Exit": ["09:33:20", "09:41:58", "09:52:31"],
        "Spread": ["USO 77/78 C", "USO 76/77 C", "USO 78/79 P"],
        "Net": [fmt.pnl(12.0), fmt.pnl(18.0), fmt.pnl(-8.0)],
        "Fees": [fmt.fee(2.6), fmt.fee(2.6), fmt.fee(1.3)],
        "Hold": [fmt.duration(128), fmt.duration(198), fmt.duration(448)],
    },
    use_container_width=True, hide_index=True,
)
c1, c2, _ = st.columns([1, 1, 4])
c1.button("Export trades", type="primary")
c2.button("Open statement folder")
st.caption(fmt.join("Cache is up to date with the folder", "Statements through " + fmt.session_date(DAY),
                    f"mode: {mode}"))
