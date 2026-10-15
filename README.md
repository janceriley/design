# One Desk

Shared design tokens and toolkit adapters for the four trading programs:

| Program | Folder | Toolkit | Adapter |
|---|---|---|---|
| Options Matrix Studio (mini PC) and Options Matrix Viewer (work PC) | `matrix_hybrid` | Tkinter | `onedesk.tk_theme` |
| Market Synthetic Playback | `Insight/Playback` | NiceGUI | `onedesk.nicegui_theme` |
| USO scalp dashboard | `Order_Parser` | Streamlit | `onedesk.streamlit_theme` |

The design ideas and decisions are on the One Desk page: https://claude.ai/artifact/6m4ioJgKyvhq8J7TPuTDEe

**Status:** the package, adapters, tests and demos are built and verified here, and all three projects use it (see "Adopting it, project by project" below).

## Decisions built in

- **Light and dark.** Every color token has both values.
- **Flat panels.** Corners are 0 px in Tk and 3 px on the web, rules are 1 px, and nothing has a shadow. Order Parser's cards go flat.
- **Sentence-case buttons everywhere**, the Matrix included. Caps are only for labels and status words.
- **Each program keeps its own time zone.** The Matrix stays in ET and Playback stays in Central, unlabeled. `onedesk.fmt` never converts times; callers pass the zone label they already show, or none.
- **Names stay as they are.**

## What's here

```
onedesk/
  tokens.json        the single source: colors (light/dark), chart series, faces, sizes, glyphs, formats
  tokens.py          loader and validator; Palette, fonts, type sizes, chart scales, light/dark/auto
  color.py           color math: mixing, WCAG contrast, OKLab
  fmt.py             one way to write money, prices, strikes, widths, dates, times, counts
  status.py          the status grammar: glyph + caps word + detail, and tag colors per kind
  css.py             --od-* CSS variables and component classes for the web programs
  plotly_theme.py    the shared Plotly template, semantic trace roles, empty-chart figure
  tk_theme.py        Tkinter adapter
  streamlit_theme.py Streamlit adapter
  nicegui_theme.py   NiceGUI adapter
tests/               unittest suite (runs under pytest too)
demos/               one demo per toolkit; screenshots land in demos/out/
.streamlit/          theme config generated for the Streamlit demo
.claude/launch.json  starts the two web demos in the desktop app's browser pane
```

The core has no third-party dependencies. Each adapter imports its toolkit only when called, so the package works in all three projects' environments.

## Tokens

Colors live in four groups, and each token has one job:

| Group | Tokens |
|---|---|
| Chrome | `canvas`, `surface`, `raised`, `sunken`, `rule`, `rule_strong`, `ink`, `ink_2`, `muted`, `faint` |
| Accent | `navy` (controls, selection, the playhead; never data), `navy_hover`, `navy_tint`, `on_navy`, `focus` |
| Market data | `up` (gain, buy), `down` (loss, sell, fees), `count` (neutral quantities), `model` (fair value), `quote` / `quote_2` (bid and ask), `itm`, plus tints |
| Status, in tags only | `ok`, `warn`, `bad`, `off`, `rec`, `hatch`, `stripe`, plus tints |

`python -c "from onedesk import load; print(load().describe('model'))"` prints any token's values and purpose.

Four values differ from the first version of the design page; the page has been updated to match:

| Token | Mode | Was | Now | Why |
|---|---|---|---|---|
| `count` | dark | `#4794ec` | `#3987e5` | Matches chart slot 1 |
| `model` | dark | `#a88ff0` | `#c39af5` | Too close to `count` for protanopes |
| `quote` | dark | `#a9b8c9` | `#b8bcc2` | Too close to `navy` |
| `quote_2` | light | `#93a1b3` | `#8794a6` | Reaches 3:1 on white for chart marks |

Chart series are new. The five categorical slots (blue, orange, aqua, yellow, magenta) leave out the green, red and violet that carry meaning. They pass the data-viz validator's adjacent-pair checks in both modes. That allows five series for lines and bars and three for scatter-type charts. In light mode, aqua, yellow and magenta sit below 3:1 on white, so label those series directly or offer a table.

## Using it

### Tkinter: Studio and Viewer

```python
import tkinter as tk
from tkinter import ttk
from onedesk import fmt, status, tk_theme

tk_theme.enable_dpi_awareness()          # optional; see the DPI note below
root = tk.Tk()
theme = tk_theme.apply(root, mode="light")   # "dark" or "auto" (follows Windows)

ttk.Button(root, text="Load matrix", style="Primary.TButton")
ttk.Label(root, text="STRIKE", style="Caps.Raised.TLabel")
theme.tag(root, status.live("mini PC")).pack(side="right")
theme.on_mode_change(lambda t: redraw_matrix(t.palette))  # canvases redraw from the palette
theme.set_mode("dark")                                     # live switch
```

- ttk switches from the native "vista" look, which ignores colors, to "clam". Every widget class is styled from the palette.
- **Frame styles:** `AppBar`, `Strip`, `StatusBar`, `Surface`, `Raised`, `Sunken` and `Panel`, each with a `.TFrame` suffix.
- **Label styles:**
  - Name them `<Role>.<Surface>.TLabel`, for example `Caps.Raised.TLabel`.
  - Roles: `AppName`, `Caps`, `Muted`, `Ink2`, `Status`, `Num`, `NumStrong`, `Up`, `Down`, `Model`, `Title`, `Heading`, `Readout`, `ReadoutUp`, `ReadoutDown`.
  - Surfaces: none (the canvas), `Surface`, `Raised` or `Sunken`.
- **Button styles:** `Primary.TButton` and `Ghost.TButton`.
- **Table styles:** `Treeview` uses the number face; `Text.Treeview` uses the UI face.
- **Named fonts:**
  - `OneDeskUI`, `OneDeskLabel` and `OneDeskNum`, plus small, strong, title, heading and readout variants.
  - Tk's own default fonts are re-pointed to the same faces.
  - If a PC lacks Segoe UI Variable or Cascadia Mono, the fonts fall back to Segoe UI and Consolas.
- **Classic `tk` widgets:**
  - New widgets get palette defaults from the option database.
  - `set_mode` recolors existing widgets and canvas items whose colors are tokens.
  - Anything else should redraw in an `on_mode_change` listener.
- **Other helpers:**
  - `draw_hatch` and `draw_stripes` draw the "don't trust this" and "demo data" patterns on canvases.
  - `row_height("matrix")` and `row_height("table")` give pixel heights from the number face, so they scale with DPI.
- **Fingerprint:** the Viewer fingerprints `options_matrix/app.py` and `models.py`, so keep this package, or the Matrix's bridge to it, outside those files. Adopting the theme still changes `app.py` once, and both PCs need that update together. After that, look changes happen in the theme files, and the Viewer won't show "UPDATE NEEDED".
- **DPI:** `enable_dpi_awareness()` makes text crisp on scaled displays, but fonts then grow with the display. Turn it on in the Matrix only after its fixed pixel geometry (20 px rows, the 64 px strike column) comes from `row_height()` and font metrics.

### Streamlit: Order Parser

```powershell
python -m onedesk.streamlit_theme --write .streamlit/config.toml   # [theme], [theme.light], [theme.dark]
```

```python
import streamlit as st
from onedesk import status, streamlit_theme

mode = streamlit_theme.inject()            # variables for the mode Streamlit shows + Plotly template
streamlit_theme.status_tags(status.Status("Checks ok", "ok", "11"))
streamlit_theme.plotly_chart(fig)          # One Desk template, theme=None, shared config
```

- The config uses only Streamlit 1.60 option names; a test checks every key against Streamlit's registry.
- With both modes defined, Streamlit follows the viewer's light/dark setting unless the address picks one: `?embed_options=light_theme` (or `dark_theme`) opens that mode and remembers nothing. Order Parser's launcher uses it to open light. Pass `--mode light` for a single-mode config.
- Existing `st.plotly_chart` calls need `theme=None`; otherwise Streamlit's chart theme overrides the template.
- `inject()` also fixes primary-button text, which Streamlit always draws white. In dark mode that would be unreadable on the light navy.

### NiceGUI: Playback

```python
from nicegui import ui
from onedesk import nicegui_theme, status

nicegui_theme.apply()                                   # brand colors + stylesheet, once, before ui.run
ui.run(dark=nicegui_theme.dark_setting("light"))        # "light" | "dark" | "auto"

# inside a page
nicegui_theme.status_tag(status.ready("12,345 rows"))
plot = ui.plotly(nicegui_theme.figure(fig_dict, mode))  # re-render with the new mode on a switch
```

- Light values sit on `:root` and dark values on `body.body--dark`, which Quasar toggles. Everything written against the `--od-*` variables switches by itself.
- NiceGUI writes Quasar's brand colors inline on `<body>`, so their dark overrides use `!important`.
- Quasar's text-color classes are layered `!important` rules that an unlayered `!important` cannot beat. The stylesheet therefore colors button and chip labels directly, so primary-button labels stay readable in dark mode.
- AG Grid follows the tokens through its `--ag-*` variables. Give number columns `cellClass: "od-num"` for the mono face.
- Buttons drop Quasar's default caps, and cards go flat.

### Plotly, both web programs

`plotly_theme.template(mode)` is a plain dict:

- Order Parser registers it with `plotly_theme.register(mode)`.
- Playback puts it on each figure dict with `plotly_theme.apply(fig, mode)`.

`plotly_theme.roles(mode)` names the semantic trace colors (`mid`, `fair_value`, `lower_endpoint`, `upper_endpoint`, `bid`, `ask`, `gain`, `loss`, `fees`, `count`, `playhead`), so no program picks its own hex for those jobs. Bars keep square corners to match Tk.

### Formats and status

```python
from onedesk import fmt, status
fmt.pnl(412.5)        # '+$412.50'          fmt.fee(86.4)         # '−$86.40'
fmt.price(0.42)       # '0.42'              fmt.width(1)          # 'W1.00'
fmt.session_date(d)   # "Tue Oct 13 '26"    fmt.expiry(d)         # "Oct 17 '26"
fmt.time_of_day(t, zone="ET")  # '12:42:10 ET' (Matrix); no zone for Playback
fmt.plural(21, "file")         # '21 files'  (never 'file(s)')
status.needs("Auth", "2d").text()  # '⚠ AUTH · 2d'
```

## Checks

The tests run under each project's existing environment; nothing is installed here.

```powershell
# from this folder
..\Order_Parser\.venv\Scripts\python.exe -B -m unittest discover -s tests -t .           # Tk, Streamlit 1.60, Plotly
..\Insight\Playback\.venv\Scripts\python.exe -B -m unittest discover -s tests -t .       # NiceGUI 3.14
python -B -m unittest discover -s tests -t .                                             # core only
```

They cover:

- **Token file:** structure and validation.
- **Contrast:** WCAG ratios for every text and mark pairing, in both modes.
- **Separation:** colors with different meanings stay apart.
- **Formatters:** every case, including missing values.
- **Plotly:** the template is checked by Plotly's own validator.
- **Streamlit:** every config key is a real Streamlit 1.60 option.
- **NiceGUI:** the brand colors match `app.colors()`.
- **Tk:** styles, fonts, live mode switching, recoloring, hatching and the status tag, using a real Tk root.

## Demos

```powershell
..\Order_Parser\.venv\Scripts\python.exe demos\tk_demo.py --screenshot demos\out\tk   # tk-light.png, tk-dark.png
..\Order_Parser\.venv\Scripts\python.exe -m streamlit run demos\streamlit_demo.py      # http://localhost:8501
..\Insight\Playback\.venv\Scripts\python.exe demos\nicegui_demo.py                     # http://127.0.0.1:8602
```

In the desktop app, `.claude/launch.json` starts `streamlit-demo` (port 8601) and `nicegui-demo` (port 8602) in the browser pane. All demo numbers are made up.

## Adopting it, project by project

All three projects are adopted (Oct 14, 2026). None of them is committed yet. Every program opens light; each note below says how to get dark.

- **Order_Parser** (done)
  - A pinned copy lives in `onedesk/` at the project root (see its `VENDORED.md`).
  - `.streamlit/config.toml` holds the generated `[theme...]` tables above the original `[server]` and `[browser]` tables. Don't regenerate it with `--write`, which would drop them.
  - `order_parser/ui.py` calls `streamlit_theme.inject()` inside `inject_concept_a_css()`, which now returns the mode. The `--op-*` variables point at `--od-*`.
  - Cards, KPI readouts and metrics are flat: 3 px corners, no shadows, stripes or letter chips. Money readouts turn green or red by their sign; everything else stays ink.
  - `palette.colors(mode)` reads the tokens and `plotly_theme.roles()`, and `app.py` rebinds the chart colors on every run. `apply_plotly_theme` puts the One Desk template on each figure, and `st.plotly_chart` gets `theme=None`.
  - `app.py` has:
    - the app bar (name, context, CHECKS and 390 PACE tags) with the sections as tabs under it
    - the rail (Trading day, Trade definition, Import, Data quality)
    - a status bar pinned to the bottom edge
  - The History calendar reads the `--od-*` variables and takes `mode` for its inline tints.
  - `format_money` uses One Desk money (true minus); dates are `Tue Oct 13 '26`; plurals are real words.
  - The window opens light: `run_app.py` adds `?embed_options=light_theme` to the address. `ORDER_PARSER_THEME=dark` opens it dark, and `auto` follows Windows. Streamlit's own theme menu stays hidden, as before.
- **Insight/Playback** (done)
  - A pinned copy lives in `src/onedesk` (see its `VENDORED.md`); re-copy it there after changing the package here.
  - `web/server.py` calls `nicegui_theme.apply()` once per process (`install_theme`), so the hard-coded `#f3f5f8` and card CSS are gone from `web/layout.py`.
  - `web/theme.py` and `playback_logic.py` read the tokens and `plotly_theme.roles()`; every figure builder takes `mode` and starts from the One Desk template.
  - `web/playback_view.py` has the app bar (mark, name, source, tags, actions, light/dark switch), the status bar (message, chart summary, version) and the methodology tag. The old five status lines are gone.
  - The dialogs and file picker use status tags, sentence-case buttons and `fmt.plural`.
  - Windows open light (`theme.DEFAULT_MODE`). The app-bar switch changes the mode, and windows opened later follow the last choice until Playback restarts.
- **matrix_hybrid** (done)
  - A pinned copy lives in `mini_pc/options_matrix/onedesk/` (see its `VENDORED.md`), inside the package so both PCs' editable installs find it without re-running setup.
  - The bridge `mini_pc/options_matrix/one_desk.py` holds every color name the Matrix uses, the fonts, `apply()` (the ttk theme) and the hatch. `app.py` imports from it, so later restyling never changes the math fingerprint.
  - `app.py` changed once, so the fingerprint is now `d1d07bc092818b7a` (was `7e820aec33cc6660`). Copy the folder to both PCs together, or the Viewer says UPDATE NEEDED.
  - Buttons are sentence case, and fixed ALL-CAPS labels get the caps-label face.
  - Healthy cells keep the grid hairline. Failed streams are hatched (denser when the failure recurs) instead of outlined in red.
  - Both programs open light. `OPTIONS_MATRIX_THEME=dark` opens them dark, and `auto` follows Windows.
  - Before and after: `demos/out/matrix-*.png`, captured on demo data.

To share the package: on this PC, `pip install -e ..\Design` into a project's venv works. Each project carries its own pinned copy instead, so it travels with the project.

## Known limits

- **Control borders:** `rule_strong` is about 1.9:1 against the surface in both modes, below WCAG's 3:1 for component boundaries. A darker `rule_strong` is a one-line change if you want it.
- **Tk drawing:** Tk has no letter-spacing, gradients or rounded corners. The stale and demo tags fall back to solid fills in Tk; canvases use `draw_hatch` and `draw_stripes`.
- **Streamlit:** chart color lists apply to both modes, because Streamlit only accepts them under `[theme]`. The primary-button fix relies on Streamlit's `kind="primary"` attribute.
- **Cascadia Mono:** on this PC it arrives with Windows Terminal rather than as a system font. Other PCs fall back to Consolas.
