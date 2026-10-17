# Figma handoff: assistant tool UI

Restyle `assistant_tool/control.html` and `assistant_tool/volunteer.html` to match the Figma file below.
This is a visual change only. Every behaviour listed under "Do not change" must still work afterwards.

Figma file: https://www.figma.com/design/tP7XH2gKKdT7DkXI1j1jl7/Assistant-Tool-UI

The Figma MCP server must be connected in the IDE so you can call `get_design_context`, `get_screenshot`
and `get_variable_defs` on the node IDs below.

## Screens (node IDs)

Page "Screens"

| Screen | Node | Link |
|---|---|---|
| Section: Control panel | `3:147` | [open](https://www.figma.com/design/tP7XH2gKKdT7DkXI1j1jl7/Assistant-Tool-UI?node-id=3-147) |
| Control / 1 Start (`phase === 'idle'`) | `1:83` | [open](https://www.figma.com/design/tP7XH2gKKdT7DkXI1j1jl7/Assistant-Tool-UI?node-id=1-83) |
| Control / 2 Waiting for question (`phase === 'waiting_question'`, recording not marked) | `1:96` | [open](https://www.figma.com/design/tP7XH2gKKdT7DkXI1j1jl7/Assistant-Tool-UI?node-id=1-96) |
| Control / 3 Answering (`phase === 'answering'`, window not focused) | `1:109` | [open](https://www.figma.com/design/tP7XH2gKKdT7DkXI1j1jl7/Assistant-Tool-UI?node-id=1-109) |
| Control / 4 Session complete (`phase === 'done'`) | `1:122` | [open](https://www.figma.com/design/tP7XH2gKKdT7DkXI1j1jl7/Assistant-Tool-UI?node-id=1-122) |
| Section: Volunteer window | `3:148` | [open](https://www.figma.com/design/tP7XH2gKKdT7DkXI1j1jl7/Assistant-Tool-UI?node-id=3-148) |
| Volunteer / 1 Opened (before Keep on top) | `1:498` | [open](https://www.figma.com/design/tP7XH2gKKdT7DkXI1j1jl7/Assistant-Tool-UI?node-id=1-498) |
| Volunteer / 2 Paused | `1:512` | [open](https://www.figma.com/design/tP7XH2gKKdT7DkXI1j1jl7/Assistant-Tool-UI?node-id=1-512) |
| Volunteer / 3 Listening | `1:521` | [open](https://www.figma.com/design/tP7XH2gKKdT7DkXI1j1jl7/Assistant-Tool-UI?node-id=1-521) |
| Volunteer / 4 Answer streaming | `1:537` | [open](https://www.figma.com/design/tP7XH2gKKdT7DkXI1j1jl7/Assistant-Tool-UI?node-id=1-537) |

Page "Components": Button `1:57`, Kbd `1:40`, Condition tag `1:62`, Connection status `1:69`, Plan row `1:82`.

The screens show sample data (volunteer_07, a sample question and answer, sample log lines).
All real text still comes from `state` and `answers.json`.

## Tokens

These come from the Figma variables (collection "Color", modes Light and Dark; collection "Dimension").
Replace the current `:root` block in both pages with this. The control panel keeps following the system theme.
The volunteer window is always dark, so in `volunteer.html` put the dark values directly in `:root`.

```css
:root {
  --bg-body: #f1f1f1;        --bg-surface: #ffffff;     --bg-muted: #ebebeb;
  --text: #171717;           --text-2: #737373;         --text-3: #a3a3a3;
  --border: #e2e2e2;         --border-strong: #d4d4d4;
  --accent: #262626;         --on-accent: #ffffff;
  --success: #007004;        --success-muted: #c5e5c0;
  --warn: #745b00;           --warn-bg: #f8da9d;
  --error: #a50c25;
  --assisted: #6e3500;       --assisted-bg: #fad0b5;
  --unassisted: #00458c;     --unassisted-bg: #c4ddfb;

  --space-1: 4px; --space-2: 8px; --space-3: 12px; --space-4: 16px;
  --space-5: 20px; --space-6: 24px; --space-8: 32px;
  --radius-sm: 4px; --radius-md: 6px; --radius-card: 8px;
  --control-h: 32px;

  --font: "Figtree", system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  --mono: "IBM Plex Mono", ui-monospace, Consolas, monospace;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg-body: #0f0f0f;      --bg-surface: #1a1a1a;     --bg-muted: #262626;
    --text: #ededed;         --text-2: #a3a3a3;         --text-3: #5c5c5c;
    --border: #2e2e2e;       --border-strong: #404040;
    --accent: #ededed;       --on-accent: #171717;
    --success: #5bbf5e;      --success-muted: #16301a;
    --warn: #e2c15a;         --warn-bg: #33290c;
    --error: #ff7b86;
    --assisted: #f0b48a;     --assisted-bg: #3a2112;
    --unassisted: #9cc4f5;   --unassisted-bg: #132a44;
  }
}
```

Fonts: load Figtree (400, 500, 600) and IBM Plex Mono (400, 500) from Google Fonts. The stacks fall back to
system fonts, so the page still works offline.

Type scale used in the frames:

| Use | Font | Size / line height | Weight |
|---|---|---|---|
| Page title | Figtree | 18 / 24 | 600 |
| Question | Figtree | 26 / 36 | 500 |
| Card heading (New session, Session complete) | Figtree | 20 / 28 and 26 / 36 | 600 |
| Body, hints | Figtree | 15 / 22 | 400 |
| Buttons | Figtree | 14 / 20 | 600 primary, 500 secondary |
| Meta line, labels | Figtree | 13 / 18 | 400 to 500 |
| Timer | IBM Plex Mono | 36 / 44 | 500 |
| URL, log, commands | IBM Plex Mono | 12 to 13 | 400 |
| Volunteer answer text | Figtree | 16 / 25 | 400 |

## Components to existing markup

| Figma component | Existing element | Notes |
|---|---|---|
| Button, type=Primary | `button.primary` | Fill `--accent`, text `--on-accent`, height 32, radius 6, padding 0 10 0 12, gap 8 between label and kbd |
| Button, type=Secondary | `button` | Fill `--bg-surface`, 1px `--border-strong` |
| Button, state=Disabled | `button:disabled` | opacity .45 (unchanged) |
| Kbd, tone=default | `kbd` | Mono 11/16, `--bg-muted`, 1px `--border`, radius 3, padding 1 5 |
| Kbd, tone=on-accent | `button.primary kbd` | white at 18% opacity, text `--on-accent` |
| Connection status | `.pill`, `.pill.ok` | Square 8px indicator (radius 1), not a round dot. Radius 4, not a full pill |
| Condition tag | `.tag.assisted`, `.tag.unassisted` | Filled background (`--assisted-bg` / `--unassisted-bg`), no border |
| Plan row | `ol.plan li` | Layout: `Q2` / type / state word on the right ("done", "now", empty). Current row gets `--bg-muted`. Replace the ✓ and › marks with the state words |
| Banner | `.banner` | Fill `--warn-bg`, text `--warn`, radius 6, **no border**. First sentence bold |

## Layout changes per screen

**Header (all control screens).** Title, connection status, then the link field filling the remaining width,
then "Copy link". Link text in mono.

**1 Start.** Card 520px wide: heading "New session", one line of help text, the volunteer number field
with the Start button beside it, then a bordered "round order" box. The box replaces the current
`#orderHint` paragraph: a mono line (`volunteer_07 · odd number, so unassisted goes first`) and one row per
round with its condition tag, set and question count. Build it from the same odd/even rule `orderHint()` uses.

**2 Waiting for question.** Recording banner full width with "Recording started R" button on the right.
Grid is `1fr 320px`, gap 20. Question card: meta row (condition tag, then
`Round 2 · Set B · Question 2 of 4 · Technical`), question, instruction line with inline kbd, action row,
then the answer preview. Action row order: primary action, the other main action, a 1px divider, Back,
Send test answer, Clear volunteer screen. The answer preview is a filled `--bg-body` box, not a bordered
`<details>`. Keep it a `<details>` element for the open/closed behaviour; style the summary as the
"What the volunteer will see ... Hide/Show" row.

**3 Answering.** Same layout. A timer block sits between the question and the instruction:
small label "Since question ended", the mono timer, and a line "Answer shown on volunteer screen at +1.61 s"
(assisted only, when that value is in state; hide the line if it isn't). "Answer finished Enter" becomes the
primary (first) button; the Space button becomes secondary and reads "Re-mark question end".
The focus banner replaces the recording banner position when shown.

**4 Session complete.** Heading, a summary line, a three-cell stats row (mean assistant latency,
latency range, longest answer), then numbered next steps with the two `make_clips.py` commands in a mono
box filled with the volunteer number and the log path from `state.log_path`, then
"Copy commands" (primary) and "Back one question B". If the server doesn't send latency stats yet, compute
them from `state.recent` only if that is reliable; otherwise leave the stats row out and note it.

**Log card.** Fills the remaining height of the side column and scrolls inside itself.

**Volunteer window.** 380 wide. Title bar ("Assistant" + status with square indicator), 1px divider,
body with 20px padding. States: Opened (heading, one line, Keep on top button, "Works in Chrome or Edge"),
Paused (centred), Listening (centred, a small static 7-bar level mark and one line), Answer streaming
("Suggested answer" label, then the streamed text at 16/25). No blinking cursor.

## Do not change

These are in the current `control.html` for reasons that matter to the data. Keep them exactly:

- Every press is queued with `client_t: Date.now()` at the moment of the key press (`act()` / `pump()`).
- Buttons keep `tabIndex = -1` so Space and Enter never double-fire.
- The keydown handler ignores repeats, modifier keys and input fields, and does no phase check.
- `refresh()` polls one at a time with the 3 s abort and the `actionGen` guard.
- `renderMain()` only rebuilds when `volunteer_id:phase:cursor` changes, so an open answer preview stays open.
- The focus banner logic (`syncFocus` on focus/blur).
- The 100 ms timer update from `state.last_question_end_t`.
- All element IDs used by the script (`conn`, `connText`, `url`, `copy`, `startView`, `vnum`, `startBtn`,
  `orderHint` if kept, `sessionView`, `focusBanner`, `recBanner`, `recBtn`, `mainCard`, `planTitle`,
  `plan`, `log`, `error`).
- No new dependencies. No server changes unless a screen needs a value that isn't in `state` yet;
  in that case say which field and add it in `server.py` separately.

## Style rules

No drop shadows, no gradients, no emojis, no icon libraries, no hover animations beyond the existing
border change, no em dashes in UI text. Radii stay at 4 to 8 px.

## Done when

- Both pages render like the frames above in Chrome and Edge, light and dark (control) and dark (volunteer).
- A practice run with volunteer number 99 works end to end: start, R, T, Space, Enter, B, all 8 questions,
  session complete, and `session_log.jsonl` timings look the same as before the restyle.
