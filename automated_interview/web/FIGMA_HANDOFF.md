# Figma handoff: automatic interview page

Restyle `automated_interview/web/public/index.html` to match the Figma file below. This is a visual change only.
Every behaviour listed under "Do not change" must still work afterwards, because the timing data
depends on it.

Figma file: https://www.figma.com/design/uTzXnhGgo47ObVxTn8Ls7h/De-Cue-Automatic-Interview

The Figma MCP server must be connected so you can call `get_design_context`, `get_screenshot`
and `get_variable_defs` on the node IDs below. The file uses components from the Astryx library
(Button, Badge, Banner, ProgressBar, Kbd, StatusDot, Skeleton, Link) in its **Neutral Dark** mode.
Do not add Astryx or any other library to the page: rebuild the look in plain CSS, as the page does now.

## Screens (node IDs)

Page "Automatic interview". Sample data: session code `7C1E-08`, volunteer 08 (even, so the
assisted round comes first), sample questions from `assistant_tool/answers.json`.

| Screen | Code | Node | Link |
|---|---|---|---|
| 01 Turn your sound on | `soundGate()` | `14:376` | [open](https://www.figma.com/design/uTzXnhGgo47ObVxTn8Ls7h/De-Cue-Automatic-Interview?node-id=14-376) |
| 02 Welcome (narration playing, buttons locked) | `welcome()` | `5:2688` | [open](https://www.figma.com/design/uTzXnhGgo47ObVxTn8Ls7h/De-Cue-Automatic-Interview?node-id=5-2688) |
| 03 Check your setup (camera and mic ready, sound and link waiting) | `deviceCheck()` | `5:2763` | [open](https://www.figma.com/design/uTzXnhGgo47ObVxTn8Ls7h/De-Cue-Automatic-Interview?node-id=5-2763) |
| 04 Round 1 intro, assisted (narration playing) | `roundIntro()` | `13:244` | [open](https://www.figma.com/design/uTzXnhGgo47ObVxTn8Ls7h/De-Cue-Automatic-Interview?node-id=13-244) |
| 05 Answering, assisted (answer streaming) | `askQuestion()` after `question_end` | `13:332` | [open](https://www.figma.com/design/uTzXnhGgo47ObVxTn8Ls7h/De-Cue-Automatic-Interview?node-id=13-332) |
| 06 Round 2 intro, unassisted (narration played) | `roundIntro()` | `13:407` | [open](https://www.figma.com/design/uTzXnhGgo47ObVxTn8Ls7h/De-Cue-Automatic-Interview?node-id=13-407) |
| 07 Listening to the question, unassisted | `present()` before `question_end` | `13:472` | [open](https://www.figma.com/design/uTzXnhGgo47ObVxTn8Ls7h/De-Cue-Automatic-Interview?node-id=13-472) |
| 08 Sending your recording | `finish()`, upload loop | `10:203` | [open](https://www.figma.com/design/uTzXnhGgo47ObVxTn8Ls7h/De-Cue-Automatic-Interview?node-id=10-203) |
| 09 All done | `finish()`, end | `10:238` | [open](https://www.figma.com/design/uTzXnhGgo47ObVxTn8Ls7h/De-Cue-Automatic-Interview?node-id=10-238) |
| S1 Loading the session | initial `#app` content | `10:268` | [open](https://www.figma.com/design/uTzXnhGgo47ObVxTn8Ls7h/De-Cue-Automatic-Interview?node-id=10-268) |
| S2 Link not available | `load()`, `!r.ok` | `10:309` | [open](https://www.figma.com/design/uTzXnhGgo47ObVxTn8Ls7h/De-Cue-Automatic-Interview?node-id=10-309) |
| S3 Session interrupted | `load()`, `status !== 'created'` | `10:326` | [open](https://www.figma.com/design/uTzXnhGgo47ObVxTn8Ls7h/De-Cue-Automatic-Interview?node-id=10-326) |
| S4 Could not load the session | `load()`, `catch` | `14:413` | [open](https://www.figma.com/design/uTzXnhGgo47ObVxTn8Ls7h/De-Cue-Automatic-Interview?node-id=14-413) |
| S5 Screen too narrow (375 wide) | `#narrow` | `10:345` | [open](https://www.figma.com/design/uTzXnhGgo47ObVxTn8Ls7h/De-Cue-Automatic-Interview?node-id=10-345) |

Page "Local components": Assistant overlay `12:307` (Paused, Listening, Generating, Answer),
Narration status `12:263` (Playing, Played), Check row `4:299` (Ready, Waiting, Failed),
Site header `4:300`, Site footer `4:305`, Interview bottom bar `12:308`.

All text that is read aloud comes from `automated_interview/web/public/instructions.json`. The frames show that text
word for word, but **keep loading it from the JSON** (`paras()` / `INSTR`). Never hardcode it.

## Tokens

Resolved from the Astryx variables in Neutral Dark mode. Replace the current `:root` block with this.
The page stays dark only (`color-scheme: dark`).

```css
:root {
  --bg-body: #1b1b1b;        --bg-surface: #262626;
  --text: #fafafa;           --text-2: #a3a3a3;         --text-3: #525252;
  --border: rgba(255,255,255,.10);                      --border-strong: #525252;
  --accent: #ebebeb;         --on-accent: #171717;
  --neutral: rgba(255,255,255,.10);   /* secondary button fill, kbd fill, Waiting badge */
  --success: #64af4c;        /* status dot "live", Ready badge (text #171717) */
  --success-fill: #198100;   /* microphone level bar */
  --warn: #fdcf4f;           --warn-bg: rgba(222,180,51,.24);   /* banner tint over --bg-surface */
  --error: #ffc6c1;          --error-bg: rgba(255,158,151,.24);
  --error-badge: #ff705d;    /* "Not working" badge, text #171717 */
  --rec: #e3193b;
  --skeleton: #525252;

  --space-1: 4px; --space-2: 8px; --space-3: 12px; --space-4: 16px;
  --space-5: 20px; --space-6: 24px; --space-8: 32px; --space-12: 48px;
  --radius: 4px;             /* everything: buttons, badges, banner, boxes, kbd, skeleton */

  --font: "Figtree", system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  --serif: "Instrument Serif", Georgia, "Times New Roman", serif;
  --mono: "IBM Plex Mono", ui-monospace, Consolas, monospace;
}
```

Fonts: add Instrument Serif (400) and IBM Plex Mono (400) to the existing Google Fonts link, and add
Figtree 700. Keep the link non-blocking (`media="print" onload="this.media='all'"`): a slow font
server must never delay the timing code.

### Type scale

| Use | Font | Size / line height | Weight | Colour |
|---|---|---|---|---|
| Screen heading: sound gate, all done | Instrument Serif | 64 / 68 | 400 | `--text` |
| Screen heading: sending, error screens | Instrument Serif | 56 / 62 | 400 | `--text` |
| Screen heading: welcome | Instrument Serif | 60 / 64 | 400 | `--text` |
| Screen heading: check your setup | Instrument Serif | 48 / 56 | 400 | `--text` |
| Question text | Instrument Serif | 40 / 50 | 400 | `--text` |
| Round intro heading | Instrument Serif | 36 / 44 | 400 | `--text` |
| Narrow screen heading | Instrument Serif | 40 / 44 | 400 | `--text` |
| Instruction paragraphs | Figtree | 17 / 27 | 400 | `--text-2` |
| Round script (in a box) | Figtree | 16 / 25 | 400 | `--text` |
| Assistant answer | Figtree | 16 / 25 | 400 | `--text` |
| Labels, button text, check titles | Figtree | 14 / 20 | 500 | `--text` |
| Body, list items | Figtree | 14 / 20 | 400 | `--text-2` or `--text` |
| Supporting: hints, footer, check descriptions, status words | Figtree | 12 / 20 | 400 | `--text-2` |
| "De-Cue" in the header | Figtree | 14 / 20 | 700 | `--text` |
| "Paused" in the overlay | Figtree | 17 / 24 | 700 | `--text` |
| Eyebrows ("Round 1 of 2", "Question 2"), timer, session code, step numbers | IBM Plex Mono | 13 / 20 | 400 | `--text-2` |
| Session code chip (interrupted screen) | IBM Plex Mono | 24 / 32 | 400 | `--text` |

Replace the current uppercase, letter-spaced `.q-label` with the mono eyebrow.

## Components to markup

| Figma | Markup | Notes |
|---|---|---|
| Button, Primary | `.primary` | Height 36, padding 0 12, radius 4, fill `--accent`, text `--on-accent` 14/500, no border |
| Button, Secondary | `.secondary` | Same size, fill `--neutral`, text `--text`, no border. Hover may lighten the fill; nothing else |
| Button, Disabled | `:disabled` | `opacity: .5` for both kinds |
| Kbd ("Space") | new `kbd` | Mono 12, fill `--neutral`, 1px `--border-strong`, radius 4, padding 0 4, height 20. Shown after "or press" beside the answer buttons; the hint gets `opacity: .45` while the buttons are disabled |
| Status dot | `.dot`, `.dot.live` | Square 8px, radius 1, `--text-3` off / `--success` live. Also replaces `.pulse` in the answer state line: static, **no pulse animation** |
| Check row | `.check` | One row per check: title (14/500) and description (12) on the left, badge on the right, 1px `--border` under each row, padding 12 0. Badge text: "Ready" (`--success`), "Waiting" (`--neutral`, text #e5e5e5), "Not working" (`--error-badge`). Maps to the existing `tick` / `tick ok` / `tick bad` states |
| ProgressBar | `.meter` | Track 8px high, radius 2, `--border`. Mic fill `--success-fill`. Upload fill `--text-3`, with a label row above: "Uploading" (14/500) and "184 of 312 MB" (12, `--text-2`) |
| Banner | `.error-box` | Radius 4, fill `--warn-bg` over `--bg-surface`, padding 12 16, warning triangle 20px, title 14/500 and description 12, both `--warn`. First sentence is the title. Use the warning style for "Waiting for the researcher's computer" and the error style (`--error`, `--error-bg`) for camera or speech failures |
| Narration status | new | 5 bars 3px wide (heights 6, 12, 8, 14, 6, gap 2) + "Reading aloud" + mono "0:21 / 0:53". Played: flat bars in `--text-3` + "Read aloud once. Replay it any time." See below |
| Skeleton | loading screen | Blocks in `--skeleton`, radius 4, laid out like the welcome screen (node `10:268`) |
| Site header | new | 56 high, padding 0 48, 1px `--border` below: "De-Cue", "Research interview" (`--text-2`), then on the right "Session" + mono session code. Shown on every non-interview screen |
| Site footer | new | Padding 16 48, 1px `--border` above: privacy line on the left, links "Consent form" and "Contact the researcher" on the right (underlined, `--text-2`) |
| Assistant overlay | `.overlay` | See "Interview layout" |
| Interview bottom bar | `.bottombar` | 48 high, padding 0 24, 1px `--border` above. Left: square `--rec` indicator + "Recording". Right: progress text (12, `--text-2`) then 8 segments 20×4 (radius 1, gap 4, extra 4px gap between rounds): done `--text-2`, current `--text`, upcoming `--text-3` |

## Layout per screen

**Message screens** (sound gate, sending, done, errors): header, then a left-aligned column 640px wide,
starting 96px down and 120px from the left, gap 24, then the footer pinned to the bottom. Not centred
in the window, unlike the current `.page`.

**01 Turn your sound on.** Eyebrow "Before you start", heading, paragraph, then Start with
"Use Chrome or Edge on a laptop or desktop." beside it.

**02 Welcome.** Two columns: left 600px (eyebrow, heading "Your mock interview", the `welcome` paragraphs,
then the buttons and the narration status under them), right fills the rest with a 112px gap.
The right column is the numbered "What happens" list (see "Open questions").

**03 Check your setup.** Heading, `setup` paragraph (max 880px), then two columns with a 64px gap:
the camera preview (16:9, `--bg-surface`, 1px `--border`, radius 4, plus the caption
"Mirrored preview. Only you see it until the interview begins.") and a 440px check column:
Camera, Microphone + level bar, Sound + "Play test voice", Connection, the banner, then
"Begin interview" and "Replay instructions", then the narration status.
The dashed face guide (208×264, 1px dashed `--border-strong`, "Keep your face inside") is an overlay
**on top of** the `<video>`. Do not put it inside the mirrored element, or its text will be mirrored too.

**Interview layout** (round intros and questions), replacing the current overlay styles:

- The overlay stays docked at the top centre, `width: min(680px, calc(100% - 32px))`,
  `height: 36vh`, `min-height: 220px`, the same size in both rounds.
- **Remove the `box-shadow`, `backdrop-filter` and the translucent background.** Use solid
  `--bg-surface`, 1px `--border-strong` on the left, right and bottom, and radius `0 0 4px 4px`.
  This is a deliberate design rule (no shadows, no glass, small radii).
- Overlay title bar: padding 12 16, "Assistant" 14/500, status dot + status word 12 on the right.
  Body padding 16 20. Answer label "Suggested answer" 12 in `--text-3`.
- Under the overlay, 8px below it: a one-line caption (`.overlay-note`, 12/20 `--text-2`, centred, overlay width, fixed 20px height in both rounds) saying what to do with the assistant. Display only, not read aloud.
- A secondary "Mute voice" / "Unmute voice" toggle sits in the controls row on the welcome, setup, round-briefing and question screens (after the other buttons). It sets the voice's volume to 0 and changes nothing else: narration still gates the buttons for its full length, and `question_end` still comes from the end of playback.
- Question area: 820px wide, centred horizontally, content vertically centred in the space between
  the overlay and the bottom bar, gap 20. Order: mono eyebrow, serif question, state line, controls.
- State line: square dot + "Answer now" (14/500 `--text`) + mono timer, or the neutral dot +
  "Listening to the question" in `--text-2`.
- Controls: "Done answering" (primary), "Repeat question" (secondary), then "or press [Space]".
- Round intro: eyebrow "Round 1 of 2", serif heading ("The assistant is on for this round." or
  "Answer this round on your own."), the round script in a box (`--bg-surface`, 1px `--border`,
  radius 4, padding 20 24, paragraph gap 12), then "Start round N", "Replay instructions" and the
  narration status.

**08 Sending.** Eyebrow "Interview finished", heading, the `uploading` paragraph, narration status,
the upload bar with its label row, then one line in `--text-2`:
"If the connection drops, leave the page open. Sending carries on by itself when it comes back."
When `finish` can't reach the laptop, replace that line with the existing
"Waiting for the researcher's computer…" text.

**09 All done.** Eyebrow "Session 7C1E-08 · saved", heading "All done. Thank you!", the `done` paragraph,
narration status, then the numbered "What happens next" list (see "Open questions").

**S3 Session interrupted.** As now, plus the session code in a mono chip (`--bg-surface`, 1px `--border`,
radius 4, padding 16 20) so the volunteer can quote it.

**S5 Narrow.** Plain header ("De-Cue", "Research interview"), padding 48 16, serif heading, two paragraphs.

### Narration status

Shown beside or under the buttons on every screen whose text is read aloud. It needs state the page
already has:

- While `narrating` is true: "Reading aloud" + `currentTime / duration` of the playing recorded
  instruction, formatted `m:ss / m:ss`, updated a few times a second. If the browser voice is reading
  (no recording, so no duration), show "Reading aloud" without the time.
- After the first full playback: the "Played" variant. After a skip: "Skipped. Replay it any time."

This is display only. Do not change how `narrate()` gates the buttons.

## Do not change

- `now()` and every `log()` call: names, fields, order. `question_end` is the clip start.
- `speak()`, `playRecorded()`, `speakBrowser()` and their fallback timers.
- `narrate()` gating: the next button stays disabled until the instruction has played once or been
  skipped. While it plays, Replay is "Skip instructions", enabled after `SKIP_AFTER_S` (5 s) with no
  countdown shown; a skip is logged as `instructions_skipped`. `stopNarration()` on every exit.
- The microphone check ignores the bar while `narrating`.
- The recorder starts and logs `recording_start` before `buildInterview()`. In `finish()`, the recorder
  stops **before** the uploading narration plays, so the voice never leaks into the last clip.
- The Space handler (`e.code === 'Space' && !e.repeat`), the 2 s guard before "Done answering"
  unlocks, `renderId` cancellation, and `ui.panel.scrollTop = 0` on a new answer (no auto-scroll while
  it streams).
- The overlay keeps the same size and position in both rounds. Only its contents change.
- Upload, retry and mirror logic, the `beforeunload` warning, and loading `instructions.json` before
  starting.
- The plan comes from the server (`server.build_plan()`). No counterbalancing in JavaScript.
- The 900px breakpoint for `#narrow`.
- No new dependencies and no build step. The page stays one static file served by Vercel.

## Style rules

No drop shadows, gradients, glass or blur, emojis, icon libraries, or em dashes in UI text.
Radii 4px (2px on bar tracks, 1px on dots and segments). Hover states only on buttons and links,
with no motion beyond a colour change. The mic meter's existing width transition can stay.

## Open questions (ask the user before shipping)

1. **Session code.** The header shows a short code (`7C1E-08` in the frames). The page has
   `session.session_id` and `session.volunteer_id`. Ask how the code should be formed; if there's
   no answer, use the first 4 characters of `session_id` in upper case plus the two-digit volunteer
   number. On the loading screen, before the session has loaded, show `····`.
2. **Footer links.** "Consent form" and "Contact the researcher" have no URLs yet. Ask for them;
   leave the links out until they exist.
3. **Unnarrated lists.** Welcome's "What happens" list (with estimated minutes 2 / 7 / 7 / 2) and
   All done's "What happens next" list are not in `instructions.json`, so they are shown but not read
   aloud. The All done list paraphrases `docs/VOLUNTEER_CONSENT_FORM.md` (encrypted local storage,
   only feature numbers kept, withdrawal within 14 days). Confirm that the user wants them and that
   the wording matches the consent form.
4. **Progress label during round intros.** The frames show "Round 1 · Instructions". The current code
   leaves it empty before round 1 and still showing "Question 4 of 4" during the round 2 intro.
   Setting it in `roundIntro()` is a text change only.
5. **Palette shift.** The old comment says the palette matched `volunteer.html` so the assistant looked
   like the floating window volunteers 01 to 07 used. The new tokens are slightly lighter
   (`#1b1b1b` / `#262626` instead of `#0f0f0f` / `#1a1a1a`), and the overlay already moved to the top.
   Confirm this is acceptable for the data before shipping.

## Done when

- All 14 frames match in Chrome and Edge at 1440×900, and the narrow message shows below 900px wide.
- A local practice run works end to end (see "Testing locally" in `automated_interview/web/README.md`, volunteer 99,
  `--no-tunnel --no-clips`): sound gate, welcome narration and replay, all four checks, both rounds,
  upload, All done.
- The rebuilt `session_log.jsonl` has the same events and fields as before the restyle, and
  `make_clips.py --dry-run` accepts it.
- Afterwards, delete `data/raw/volunteer_99/` and the test `automated_interview/web/.devdata/`, then put back
  the real `.devdata` you parked before testing (it holds real session timings; never delete it).
