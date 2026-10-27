# Assisted vs Unassisted: Volunteer Comparison

*De-Cue volunteer data, volunteers 02–10. Compiled 2026-10-10.*

## Summary

- **8 of 9 volunteers used the AI assistant in their assisted round.** Volunteer 08 did not use it at all, so their four "assisted" clips are effectively unassisted.
- For the 8 volunteers who used the assistant, five behavioural features changed in the **same direction for all 8**:
  - word variety up;
  - shorter sentences;
  - steadier gaze;
  - less looking away from the camera;
  - fewer blinks.
- Two more changed in the same direction for **7 of 8**: more time before starting to answer, and fewer filler words.
- **Volunteer 08 moved the opposite way on 4 of those 5 features**, and word variety barely changed. That suggests the changes come from reading the AI's answer, not from round order or fatigue. The pattern also appears whether the assisted round came first or second.
- **Pause features are inconsistent**, and **eye-jump rate looks unreliable** for browser-recorded sessions (see Cautions).
- Two data issues need action:
  - **Volunteer 08's assisted clips are mislabelled.**
  - **The round order is unbalanced:** volunteer 08 ran volunteer 09's plan.

## Dataset

| Volunteer | Session type | Briefing | Assisted round | Used the AI |
|---|---|---|---|---|
| 02 | Researcher-run | Verbal script | First | 4/4 |
| 03 | Researcher-run | Verbal script | Second | 4/4 |
| 04 | Researcher-run | Verbal script | First | 4/4 |
| 05 | Researcher-run | Verbal script | Second | 4/4 |
| 06 | Researcher-run | Verbal script | First | 4/4 |
| 07 | Researcher-run | Verbal script | Second | 4/4 |
| 08 | Automatic | Original page briefing | Second* | **0/4** |
| 09 | Automatic | New briefing | Second | 4/4 |
| 10 | Automatic | New briefing | First | 4/4 |

\* Volunteer 08 should have done the assisted round first (even number). Their session was created as volunteer 09 and renumbered, so they ran volunteer 09's plan: the same round order and the same question order.

Volunteer 01 is the pilot and is excluded. Each volunteer has 4 unassisted and 4 assisted clips, 72 clips in all. One clip's gaze features are excluded because the video froze for the whole clip (`v06_unassisted_q4`), as in training.

The "new briefing" (from volunteer 09's second session onward) explains the study, says that no outside help is allowed, and says that volunteers *must* use the suggested answer. It also shows an example answer in the assistant box before the assisted round.

## Did volunteers actually use the assistant?

**Measure.** Each transcript is compared with the suggested answer for that exact question. The figure is the share of the suggestion's three-word phrases that were spoken word for word. Reading aloud or close paraphrase produces many matches; just talking about the same topic almost never does.

**Baseline.** In unassisted answers, compared against the never-shown suggestion for the same question, the average is 0.3% and the maximum 2.3%.

| Volunteer | Assisted: phrases reused | Unassisted baseline | Assisted answers above every baseline clip |
|---|---|---|---|
| 02 | 71% | 0% | 4/4 |
| 03 | 55% | 0% | 4/4 |
| 04 | 79% | 1% | 4/4 |
| 05 | 63% | 1% | 4/4 |
| 06 | 89% | 0% | 4/4 |
| 07 | 80% | 0% | 4/4 |
| **08** | **0%** | 0% | **0/4** |
| 09 | 44% (22–73%) | 1% | 4/4 |
| 10 | 61% (55–70%) | 0% | 4/4 |

- **Volunteer 08 was shown every suggested answer** (0.5–2.0 s after each question, as designed), but matched neither question set. They ignored the assistant.
- **Volunteer 09 blended the suggestion with a lot of their own speech:** about 200 words per answer against a 65-word suggestion. That still counts as assisted, and the new briefing allows it.
- **Volunteers 02–07 and 10 mostly read the suggestion out**, with light rewording.
- **The suggested answers have not changed since 2 October.** That is before every real session, so the comparison is fair for all volunteers.

## Feature changes: unassisted → assisted

Values are per-volunteer means. Pause and language features are converted from stored z-scores back to real units using `models/baseline_stats.json`. Gaze features and response delay are stored raw.

### Consistent across the volunteers who used the AI

| Feature | V02 | V03 | V04 | V05 | V06 | V07 | V09 | V10 | Same direction | V08 (did not use AI) |
|---|---|---|---|---|---|---|---|---|---|---|
| Word variety | 0.57 → 0.77 | 0.74 → 0.77 | 0.75 → 0.79 | 0.44 → 0.79 | 0.58 → 0.77 | 0.63 → 0.84 | 0.46 → 0.50 | 0.47 → 0.77 | ↑ 8/8 | 0.58 → 0.60 |
| Words per sentence | 17.4 → 11.8 | 20.4 → 11.6 | 20.9 → 10.9 | 22.8 → 9.9 | 14.0 → 10.4 | 22.0 → 8.0 | 30.2 → 19.2 | 20.7 → 11.2 | ↓ 8/8 | 21.8 → 25.9 |
| Gaze steadiness (higher = steadier) | 456 → 944 | 1,181 → 2,167 | 315 → 1,913 | 140 → 533 | 223 → 2,449 | 223 → 3,560 | 381 → 451 | 1,792 → 2,380 | ↑ 8/8 | 1,485 → 840 |
| Looking away from the camera | 0.042 → 0.031 | 0.025 → 0.018 | 0.046 → 0.019 | 0.075 → 0.031 | 0.055 → 0.018 | 0.052 → 0.015 | 0.041 → 0.036 | 0.021 → 0.017 | ↓ 8/8 | 0.026 → 0.032 |
| Blinks per minute | 72 → 25 | 56 → 27 | 52 → 21 | 79 → 51 | 59 → 31 | 55 → 5 | 50 → 38 | 42 → 19 | ↓ 8/8 | 44 → 53 |
| Time before starting to answer (s) | 4.9 → 2.3 | 2.2 → 3.1 | 1.5 → 2.2 | 0.6 → 5.0 | 0.5 → 3.1 | 1.0 → 3.3 | 4.9 → 6.5 | 1.8 → 2.4 | ↑ 7/8 | 3.2 → 1.7 |
| Filler words per 100 words | 7.1 → 2.6 | 5.9 → 3.0 | 5.8 → 2.5 | 5.1 → 1.5 | 4.0 → 2.2 | 1.9 → 0.8 | 2.6 → 1.2 | 0.5 → 1.8 | ↓ 7/8 | 5.1 → 9.2 |

With the AI's help, volunteers held their gaze steadier, looked away less, blinked less, used shorter sentences with more varied words, and (all but one) said fewer "uh"s. That is the pattern expected from someone reading off a screen.

- **Volunteer 08 is a useful check.** They had the same round order and questions as volunteer 09 but did not read the suggestions. On word variety they barely moved (0.58 → 0.60); on the other four features shared by all 8, they went the opposite way. They also used more fillers and started answering *sooner*.
- **The changes don't depend on round order.** Volunteers 02, 04, 06 and 10 did the assisted round first; 03, 05, 07 and 09 did it second. The gaze, blink and language changes appear in both groups.
- **Response delay goes up, not down.** An earlier two-volunteer look suggested people start *sooner* with help. With 8 volunteers, 7 started **later**, by 0.6–4.4 s. Volunteer 02 is the only exception. With the assistant on, people appear to wait for the suggestion and read a little before speaking.
- **Volunteer 10 is the one exception on fillers** (0.5 → 1.8 per 100 words), from an unusually low base. Both values are very small next to the 2–7 typical of others.
- **Volunteer 09 changed least** on word variety and gaze, which fits their mixed reading-plus-own-words style.

### Mixed, with no reliable direction yet

| Feature | V02 | V03 | V04 | V05 | V06 | V07 | V09 | V10 | Direction |
|---|---|---|---|---|---|---|---|---|---|
| Speaking speed (words/min) | 116 → 138 | 113 → 121 | 129 → 140 | 139 → 113 | 154 → 136 | 151 → 123 | 116 → 127 | 123 → 132 | ↑ 5/8 |
| Pauses per minute | 15.6 → 11.9 | 16.5 → 16.0 | 21.2 → 17.0 | 10.2 → 12.1 | 7.3 → 10.8 | 12.7 → 11.9 | 18.0 → 17.6 | 11.7 → 9.1 | ↓ 6/8 |
| Average pause (s) | 0.72 → 0.74 | 0.78 → 0.75 | 0.56 → 0.51 | 0.57 → 0.80 | 0.47 → 0.52 | 0.56 → 0.90 | 0.59 → 0.61 | 0.46 → 0.59 | ↑ 6/8 |
| Pause unevenness (s²) | 0.22 → 1.17 | 0.16 → 0.10 | 0.09 → 0.07 | 0.11 → 0.57 | 0.21 → 0.05 | 0.08 → 1.61 | 0.13 → 0.20 | 0.03 → 0.13 | ↑ 5/8 |
| Eye jumps per second | 3.4 → 4.6 | 0.6 → 0.2 | 1.1 → 0.5 | 3.2 → 0.6 | 3.3 → 1.4 | 1.1 → 0.3 | 0.3 → 0.2 | 0.0 → 0.0 | ↓ 6/8 |

Pause behaviour still looks like an individual speaking habit; it may only become useful with more volunteers.

## Transcript examples

- **Volunteer 09, assisted:** "last year my friends and I planned a weekend trip and on the morning we left, our train was cancelled because of heavy rain…"
  - The suggestion: "Last year my friends and I planned a weekend trip, and on the morning we left, our train was cancelled because of heavy rain."
- **Volunteer 06, assisted:** "Last semester, I had two assignments and a club event in the same week. I listed every task with its deadline…" This is almost word for word from the suggestion.
- **Volunteer 06, unassisted:** "Completely wrong. I think it has to do with my personal stuff… uh, I, uh, two, three years back, I started to learn driving."
- **Volunteer 08, assisted:** "Sometimes, uh, sometimes in this situation, uh, we directly go to the Drift or we postpone the event…" This shares nothing with the suggestion.

## Cautions

1. **Word variety partly reflects answer length.** The type-token ratio rises naturally for shorter texts, and most assisted answers were shorter than unassisted ones. Volunteer 09, whose assisted answers were long, moved least (0.46 → 0.50).
2. **Shorter sentences partly reflect the suggestions' format.** Suggested answers are written as short bullet points, so reading them produces short sentences. A real AI copilot that writes long paragraphs might not cause this. Whisper's placement of full stops adds noise.
3. **Eye-jump rate depends on how the video was recorded.** Automatic (browser-recorded) sessions measure close to zero for everyone: 08 at 0.1, 09 at 0.2–0.3, 10 at 0.0. Researcher-run (video-call) sessions measure 0.2–4.6. The detection threshold likely behaves differently at a different frame rate or resolution. Volunteer 02's higher rate is consistent with their glasses confusing the eye tracking. Treat `saccade_rate` as unreliable until the threshold is validated on both recording types.
4. **Small sample.** These are within-person directions for 8 assisted volunteers, not tested effects. The model's cross-validated results remain the main evidence.

## Actions

1. **Volunteer 08:**
   - Leave their assisted clips (or the whole session) out of training.
   - Better: redo the session with the correct plan (assisted round first, question order 4) and the new briefing, after archiving the current one. That fixes both the mislabelled clips and the missing slot in the counterbalancing.
2. **Round order is unbalanced:** 5 unassisted-first and 4 assisted-first among volunteers 02–10. Volunteer 08's intended slot was never run. Redoing volunteer 08 restores the balance.
3. **Method section:** state that the briefing changed from volunteer 09's second session onward, and why: volunteer 08 ignored the assistant under the original briefing. Also state that the response-delay direction is "later with help".
4. **Validate the saccade threshold** on browser-recorded video before relying on eye-jump rate.

## Method notes

- Per-clip features come from each volunteer's `trial_features.csv`. Per-volunteer means are taken over 4 clips per condition.
- Conversion back to real units: z × SD + mean, from the Stage 1 baseline, for:
  - pause rate, average pause length and pause unevenness;
  - filler rate, speaking rate, word variety and words per sentence.
- Response delay has a baseline of mean 0, SD 1, so it is stored in seconds. Gaze features are stored raw (baseline flagged as a domain mismatch).
- Gaze features of clips listed in `data/gaze_exclusions.csv` are dropped, as in `build_features.py`.
- Assistant use: suggested answers from `assistant_tool/answers.json`, matched to each clip through the question set and number in that session's own plan.
