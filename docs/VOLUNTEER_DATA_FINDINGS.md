# Volunteer Data Findings

**Study:** De-Cue: Detecting Covert Real-Time AI Assistance in Video Interviews<br>
**Data covered:** 16 volunteer sessions (2026-10-02 to 2026-10-17), 128 clips<br>
**Last updated:** 2026-10-17 21:47, by `src/session_report.py`

> Sections 1–4 are regenerated after every session (`make_clips.py` runs the report), so edits to them are overwritten. Write interpretation in the sections after the end marker.

---

## 1. Summary

- **Session checks raised flags:** V01: not in labels.csv, saccade_rate 2.1× the others (glasses?); V02: 12 Back presses; last marks used, saccade_rate 10.9× the others (glasses?); V04: saccade_rate 2.1× the others (glasses?); V05: 4 Back presses; last marks used, video frozen in assisted_q4 47% (review; gaze may be invalid), saccade_rate 5.2× the others (glasses?); V06: 1 Back press; last marks used, video frozen in unassisted_q3 58% (review; gaze may be invalid), gaze excluded: unassisted_q4, saccade_rate 5.9× the others (glasses?); V12: saccade_rate 2.9× the others (glasses?).
- **1 of 12 features changed in the same direction for all 16 volunteers when the assistant was used:** `lexical_diversity` (↑ more varied).
- Round order: 7 of 16 volunteers did the assisted round first and 9 the unassisted round first. An effect that holds in both orders is not explained by fatigue or practice.
- **Split evenly between volunteers:** `speaking_rate`.
- With 16 speakers and 64 paired answers, these are directional observations, not statistically tested results.

---

## 2. Dataset

| Volunteer | Date | Protocol | Round order | Clips | In labels.csv | Flags |
| --- | --- | --- | --- | --- | --- | --- |
| V01 | 2026-10-02 | live | Unassisted → Assisted | 8 | no | not in labels.csv; saccade_rate 2.1× the others (glasses?) |
| V02 | 2026-10-02 | live | Assisted → Unassisted | 8 | yes | 12 Back presses; last marks used; saccade_rate 10.9× the others (glasses?) |
| V03 | 2026-10-03 | live | Unassisted → Assisted | 8 | yes | — |
| V04 | 2026-10-03 | live | Assisted → Unassisted | 8 | yes | saccade_rate 2.1× the others (glasses?) |
| V05 | 2026-10-09 | live | Unassisted → Assisted | 8 | yes | 4 Back presses; last marks used; video frozen in assisted_q4 47% (review; gaze may be invalid); saccade_rate 5.2× the others (glasses?) |
| V06 | 2026-10-09 | live | Assisted → Unassisted | 8 | yes | 1 Back press; last marks used; video frozen in unassisted_q3 58% (review; gaze may be invalid); gaze excluded: unassisted_q4; saccade_rate 5.9× the others (glasses?) |
| V07 | 2026-10-09 | live | Unassisted → Assisted | 8 | yes | — |
| V08 | 2026-10-09 | automatic | Unassisted → Assisted | 8 | yes | — |
| V09 | 2026-10-10 | automatic | Unassisted → Assisted | 8 | yes | — |
| V10 | 2026-10-10 | automatic | Assisted → Unassisted | 8 | yes | — |
| V11 | 2026-10-17 | automatic | Unassisted → Assisted | 8 | yes | — |
| V12 | 2026-10-17 | automatic | Assisted → Unassisted | 8 | yes | saccade_rate 2.9× the others (glasses?) |
| V13 | 2026-10-17 | automatic | Unassisted → Assisted | 8 | yes | — |
| V14 | 2026-10-17 | automatic | Assisted → Unassisted | 8 | yes | — |
| V15 | 2026-10-17 | automatic | Unassisted → Assisted | 8 | yes | — |
| V16 | 2026-10-17 | automatic | Assisted → Unassisted | 8 | yes | — |

- **Design:** within-subjects. Each volunteer answers 4 questions unassisted and 4 with the Wizard-of-Oz assistant. The first round always uses question Set A and the second Set B, so the sets swap conditions between odd and even volunteers. Each round has 2 behavioural, 1 opinion and 1 conceptual question.
- **Counterbalancing:** odd-numbered volunteers do the unassisted round first and even-numbered ones the assisted round first. Question order within a round follows a Williams design per volunteer pair.
- **Clips** start at the end of the question and end at the end of the answer.
- **Protocol:** *live* = the researcher read the questions over a video call, recorded with OBS; *automatic* = the web app presented the questions (on-screen text played from pre-recorded audio) and the browser recorded the webcam. Each volunteer did both rounds under one protocol, so the within-speaker comparisons are not mixed, but gaze values differ in scale between protocols (camera and resolution).

---

## 3. Session Quality Checks

### 3.1 Audio and recording alignment

| Volunteer | Mean / max volume | Recording length | Log span (recording start → session end) | Difference |
| --- | --- | --- | --- | --- |
| V01 | -23.1 / -0.3 dB | 409.0 s | 405.1 s | +3.9 s |
| V02 | -22.9 / -0.2 dB | 1042.4 s | 1025.5 s | +16.9 s |
| V03 | -21.5 / -0.0 dB | 390.9 s | 383.9 s | +7.0 s |
| V04 | -22.0 / -0.1 dB | 333.3 s | 329.7 s | +3.6 s |
| V05 | -22.9 / -0.2 dB | 1101.0 s | 1099.7 s | +1.4 s |
| V06 | -22.9 / -0.2 dB | 496.5 s | 488.2 s | +8.2 s |
| V07 | -25.4 / -0.4 dB | 488.1 s | 477.7 s | +10.5 s |
| V08 | -23.0 / -0.0 dB | 410.9 s | 409.3 s | +1.6 s |
| V09 | -22.2 / -0.0 dB | 1166.5 s | 1164.8 s | +1.6 s |
| V10 | -22.7 / -0.4 dB | 772.8 s | 771.2 s | +1.6 s |
| V11 | -24.8 / -0.1 dB | 776.7 s | 775.1 s | +1.6 s |
| V12 | -23.5 / -0.5 dB | 399.6 s | 398.0 s | +1.6 s |
| V13 | -26.8 / -0.5 dB | 397.6 s | 396.0 s | +1.6 s |
| V14 | -23.5 / -0.4 dB | 493.6 s | 492.1 s | +1.6 s |
| V15 | -22.5 / -0.5 dB | 460.9 s | 459.3 s | +1.6 s |
| V16 | -22.4 / -0.4 dB | 480.4 s | 478.8 s | +1.6 s |

A max volume below -60 dB would mean OBS recorded silence. The difference should be a few seconds: the time between the session ending and OBS being stopped.

### 3.2 Log completeness

| Volunteer | Planned questions | Complete | Missing | Back presses |
| --- | --- | --- | --- | --- |
| V01 | 8 | 8 | — | 0 |
| V02 | 8 | 8 | — | 12 |
| V03 | 8 | 8 | — | 0 |
| V04 | 8 | 8 | — | 0 |
| V05 | 8 | 8 | — | 4 |
| V06 | 8 | 8 | — | 1 |
| V07 | 8 | 8 | — | 0 |
| V08 | 8 | 8 | — | 0 |
| V09 | 8 | 8 | — | 0 |
| V10 | 8 | 8 | — | 0 |
| V11 | 8 | 8 | — | 0 |
| V12 | 8 | 8 | — | 0 |
| V13 | 8 | 8 | — | 0 |
| V14 | 8 | 8 | — | 0 |
| V15 | 8 | 8 | — | 0 |
| V16 | 8 | 8 | — | 0 |

After a Back press the clips use the last marks for each question.

### 3.3 When the assistant's answer appeared

| Difficulty | Configured delay | Observed delay (range) | Answers |
| --- | --- | --- | --- |
| Easy | 0.50 s | 0.50–1.00 s | 16 |
| Medium | 1.25 s | 1.25–1.81 s | 32 |
| Hard | 2.00 s | 2.00–3.06 s | 16 |

Observed delays are 0.0–1.1 s longer than configured (client and network overhead). This matters when reading `response_delay`.

### 3.4 Answer length

Mean time from `question_end` to `answer_end`, over the questions in each round.

| Volunteer | Unassisted | Assisted |
| --- | --- | --- |
| V01 | 37.2 s | 40.6 s |
| V02 | 30.1 s | 29.9 s |
| V03 | 28.9 s | 37.3 s |
| V04 | 22.8 s | 29.3 s |
| V05 | 101.0 s | 38.0 s |
| V06 | 35.0 s | 29.7 s |
| V07 | 50.0 s | 31.8 s |
| V08 | 29.6 s | 28.6 s |
| V09 | 125.9 s | 98.3 s |
| V10 | 106.0 s | 32.9 s |
| V11 | 37.9 s | 45.5 s |
| V12 | 36.1 s | 26.4 s |
| V13 | 17.7 s | 32.4 s |
| V14 | 41.8 s | 34.1 s |
| V15 | 32.0 s | 39.8 s |
| V16 | 34.2 s | 27.4 s |

### 3.5 Feature extraction

- 128 clips, 12 features, no missing values apart from the gaze exclusions below.
- Features come from `build_features.extract_clip_features()`, the same code that builds the training table, and are cached per volunteer in `data/raw/volunteer_XX/trial_features.csv`.
- Gaze features are raw values: the Stage 1 gaze baseline is flagged as a domain mismatch, so z-scoring is skipped for that group. They can be compared within a speaker, not across speakers.
- 1 clip(s) are listed in `data/gaze_exclusions.csv`. Their gaze features are treated as missing here, and training drops those clips (see Section 3.6).

### 3.6 Frozen video

Freezes of 3 s or longer, detected on each full recording and mapped onto the clips. Audio keeps recording during a freeze, so only the gaze features are affected.

| Clip | Frozen | Share of clip | Gaze excluded |
| --- | --- | --- | --- |
| v01_unassisted_q4 | 3.2 s | 5% | no |
| v05_assisted_q4 | 22.8 s | 47% | no |
| v06_unassisted_q3 | 17.5 s | 58% | no |
| v06_unassisted_q4 | 34.4 s | 100% | yes (whole clip frozen; audio intact) |

Clips with gaze excluded are dropped from training. Partly frozen clips that are kept have gaze values averaged over some still frames; state this as a limitation.

---

## 4. Results: Assisted vs Unassisted

### 4.1 Method

- Each assisted answer is paired with the same volunteer's unassisted answer to the question with the same number (64 pairs).
- The **difference** is the assisted value minus the unassisted value.
- The **standardised effect** divides each volunteer's mean difference by that volunteer's own standard deviation for the feature, then averages over volunteers. This compares each person with themselves, in line with the per-speaker centring used in the model.

### 4.2 Overview

| Group | Feature | Direction when assisted | Volunteers ↑ / ↓ | Pairs where assisted was higher | Standardised effect |
| --- | --- | --- | --- | --- | --- |
| Gaze | fixation_stability | ↑ steadier gaze (mostly) | 14 / 2 | 50 / 63 | +0.91 |
| Gaze | saccade_rate | ↓ lower (mostly) | 4 / 12 | 12 / 63 | -0.86 |
| Gaze | offcam_deviation | ↓ more on-camera (mostly) | 2 / 14 | 11 / 63 | -1.09 |
| Gaze | blink_rate | ↓ fewer blinks (mostly) | 2 / 14 | 14 / 63 | -1.10 |
| Latency | response_delay | ↑ higher (mostly) | 12 / 4 | 45 / 64 | +0.62 |
| Latency | pause_rate | ↓ lower (mostly) | 7 / 9 | 31 / 64 | -0.13 |
| Latency | avg_pause_length | ↑ higher (mostly) | 10 / 6 | 37 / 64 | +0.14 |
| Latency | pause_variance | ↑ higher (mostly) | 11 / 5 | 34 / 64 | +0.33 |
| Linguistic | filler_rate | ↓ fewer fillers (mostly) | 4 / 12 | 17 / 64 | -0.43 |
| Linguistic | speaking_rate | mixed | 8 / 8 | 32 / 64 | +0.15 |
| Linguistic | lexical_diversity | **↑ more varied** | 16 / 0 | 52 / 64 | +1.06 |
| Linguistic | sentence_complexity | ↓ lower (mostly) | 3 / 13 | 19 / 64 | -0.80 |

**Bold** marks the features where every volunteer moved in the same direction.

### 4.3 Mean difference per volunteer (assisted − unassisted)

| Feature | V01 | V02 | V03 | V04 | V05 | V06 | V07 | V08 | V09 | V10 | V11 | V12 | V13 | V14 | V15 | V16 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| fixation_stability | +841.99 | +487.75 | +986.14 | +1598.07 | +392.77 | +2127.76 | +3337.10 | -645.05 | +69.30 | +588.21 | +182.80 | +877.12 | +4077.69 | +50.89 | -1208.22 | +19.36 |
| saccade_rate | -0.45 | +1.24 | -0.40 | -0.64 | -2.67 | -1.81 | -0.77 | +0.02 | -0.10 | +0.01 | -0.12 | -1.34 | -0.53 | -0.35 | +0.11 | -0.25 |
| offcam_deviation | -0.02 | -0.01 | -0.01 | -0.03 | -0.04 | -0.04 | -0.04 | +0.01 | -0.00 | -0.00 | -0.01 | -0.02 | -0.01 | -0.01 | +0.01 | -0.00 |
| blink_rate | -13.11 | -46.28 | -28.55 | -30.92 | -28.52 | -28.25 | -50.35 | +9.00 | -11.10 | -23.42 | -16.42 | -3.08 | -54.83 | -4.15 | -21.63 | +17.37 |
| response_delay | -1.08 | -2.56 | +0.91 | +0.73 | +4.39 | +2.62 | +2.35 | -1.58 | +1.56 | +0.57 | +1.57 | +1.08 | -0.17 | +1.81 | +2.80 | +0.94 |
| pause_rate | +0.47 | -0.40 | -0.05 | -0.46 | +0.21 | +0.38 | -0.09 | -0.54 | -0.04 | -0.28 | +0.19 | -0.12 | -0.76 | +0.03 | +0.36 | +0.06 |
| avg_pause_length | -1.67 | +0.03 | -0.09 | -0.16 | +0.72 | +0.14 | +1.04 | -0.99 | +0.07 | +0.41 | +0.31 | -0.36 | +0.70 | +0.29 | -0.16 | +0.67 |
| pause_variance | -6.46 | +8.47 | -0.54 | -0.19 | +4.21 | -1.41 | +13.76 | +1.00 | +0.64 | +0.92 | +1.17 | -0.10 | +3.29 | +1.27 | +0.26 | +1.39 |
| filler_rate | -1.27 | -1.39 | -0.87 | -1.01 | -1.09 | -0.53 | -0.35 | +1.26 | -0.44 | +0.39 | -0.37 | +0.13 | -0.02 | +0.10 | -0.66 | -0.54 |
| speaking_rate | +0.43 | +0.44 | +0.16 | +0.22 | -0.52 | -0.34 | -0.54 | +0.41 | +0.22 | +0.17 | -0.31 | +0.76 | -0.24 | -0.21 | -0.16 | -0.04 |
| lexical_diversity | +0.27 | +1.11 | +0.15 | +0.23 | +1.96 | +1.04 | +1.16 | +0.11 | +0.24 | +1.70 | +0.42 | +0.74 | +0.01 | +0.62 | +0.37 | +0.88 |
| sentence_complexity | +0.79 | -0.64 | -1.00 | -1.14 | -1.46 | -0.41 | -1.59 | +0.46 | -1.25 | -1.07 | +0.23 | -2.08 | -2.78 | -0.39 | -0.97 | -0.53 |

### 4.4 Mean feature values per volunteer and condition

| Feature | V01 U | V01 A | V02 U | V02 A | V03 U | V03 A | V04 U | V04 A | V05 U | V05 A | V06 U | V06 A | V07 U | V07 A | V08 U | V08 A | V09 U | V09 A | V10 U | V10 A | V11 U | V11 A | V12 U | V12 A | V13 U | V13 A | V14 U | V14 A | V15 U | V15 A | V16 U | V16 A |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| fixation_stability | 407.86 | 1249.86 | 456.25 | 944.00 | 1180.84 | 2166.98 | 314.51 | 1912.58 | 140.03 | 532.80 | 223.32 | 2448.57 | 223.24 | 3560.34 | 1485.01 | 839.95 | 381.32 | 450.62 | 1792.12 | 2380.33 | 790.58 | 973.38 | 292.64 | 1169.76 | 1758.87 | 5836.56 | 276.37 | 327.25 | 1892.24 | 684.02 | 1947.16 | 1966.52 |
| saccade_rate | 1.00 | 0.55 | 3.38 | 4.62 | 0.57 | 0.17 | 1.09 | 0.45 | 3.24 | 0.56 | 3.29 | 1.36 | 1.07 | 0.30 | 0.05 | 0.07 | 0.29 | 0.19 | 0.03 | 0.03 | 0.39 | 0.27 | 1.73 | 0.38 | 0.56 | 0.02 | 0.66 | 0.31 | 0.02 | 0.13 | 0.31 | 0.07 |
| offcam_deviation | 0.04 | 0.02 | 0.04 | 0.03 | 0.03 | 0.02 | 0.05 | 0.02 | 0.07 | 0.03 | 0.05 | 0.02 | 0.05 | 0.01 | 0.03 | 0.03 | 0.04 | 0.04 | 0.02 | 0.02 | 0.03 | 0.02 | 0.05 | 0.03 | 0.03 | 0.01 | 0.05 | 0.04 | 0.02 | 0.03 | 0.02 | 0.02 |
| blink_rate | 45.36 | 32.24 | 71.59 | 25.31 | 55.62 | 27.07 | 51.74 | 20.82 | 79.05 | 50.53 | 58.50 | 30.57 | 55.26 | 4.91 | 43.59 | 52.59 | 49.55 | 38.45 | 42.38 | 18.96 | 44.89 | 28.47 | 25.78 | 22.70 | 69.09 | 14.26 | 38.27 | 34.12 | 49.54 | 27.91 | 24.43 | 41.80 |
| response_delay | 4.59 | 3.51 | 4.88 | 2.33 | 2.23 | 3.13 | 1.46 | 2.19 | 0.65 | 5.04 | 0.47 | 3.10 | 0.96 | 3.31 | 3.24 | 1.66 | 4.91 | 6.47 | 1.84 | 2.42 | 2.44 | 4.00 | 1.14 | 2.22 | 1.87 | 1.69 | 1.41 | 3.22 | 1.78 | 4.58 | 0.97 | 1.91 |
| pause_rate | 1.95 | 2.42 | 1.09 | 0.69 | 1.19 | 1.14 | 1.70 | 1.24 | 0.51 | 0.72 | 0.19 | 0.57 | 0.78 | 0.69 | 0.20 | -0.34 | 1.35 | 1.31 | 0.67 | 0.39 | 1.65 | 1.84 | 0.80 | 0.68 | 1.60 | 0.84 | 1.35 | 1.38 | 1.59 | 1.95 | 0.54 | 0.61 |
| avg_pause_length | 2.86 | 1.19 | 1.62 | 1.65 | 1.77 | 1.68 | 1.12 | 0.96 | 1.13 | 1.85 | 0.86 | 0.99 | 1.11 | 2.15 | 1.03 | 0.04 | 1.22 | 1.28 | 0.80 | 1.22 | 1.01 | 1.33 | 1.03 | 0.67 | 1.36 | 2.06 | 1.17 | 1.46 | 1.36 | 1.19 | 0.98 | 1.65 |
| pause_variance | 6.95 | 0.49 | 1.86 | 10.33 | 1.33 | 0.79 | 0.68 | 0.49 | 0.80 | 5.01 | 1.69 | 0.28 | 0.57 | 14.33 | 0.01 | 1.01 | 0.98 | 1.62 | 0.13 | 1.05 | 0.16 | 1.33 | 0.16 | 0.06 | 0.87 | 4.17 | 0.66 | 1.93 | 0.72 | 0.98 | 0.20 | 1.58 |
| filler_rate | 2.30 | 1.03 | 1.51 | 0.12 | 1.12 | 0.24 | 1.11 | 0.10 | 0.89 | -0.21 | 0.53 | 0.01 | -0.09 | -0.44 | 0.90 | 2.15 | 0.13 | -0.30 | -0.52 | -0.13 | -0.23 | -0.60 | -0.12 | 0.01 | -0.56 | -0.57 | -0.50 | -0.40 | 0.44 | -0.22 | 0.65 | 0.11 |
| speaking_rate | -1.30 | -0.87 | -0.67 | -0.23 | -0.74 | -0.58 | -0.42 | -0.20 | -0.21 | -0.73 | 0.08 | -0.27 | 0.01 | -0.53 | -0.88 | -0.47 | -0.66 | -0.45 | -0.53 | -0.36 | -0.22 | -0.53 | -0.63 | 0.13 | -0.19 | -0.43 | 0.34 | 0.14 | -0.42 | -0.58 | 0.26 | 0.21 |
| lexical_diversity | -0.47 | -0.21 | -1.26 | -0.15 | -0.34 | -0.19 | -0.30 | -0.07 | -2.02 | -0.05 | -1.24 | -0.19 | -0.96 | 0.20 | -1.22 | -1.10 | -1.90 | -1.66 | -1.87 | -0.17 | -0.88 | -0.46 | -0.81 | -0.07 | -0.17 | -0.16 | -1.16 | -0.54 | -0.76 | -0.39 | -1.15 | -0.27 |
| sentence_complexity | 0.42 | 1.21 | 0.63 | -0.01 | 0.97 | -0.03 | 1.03 | -0.11 | 1.23 | -0.23 | 0.24 | -0.17 | 1.14 | -0.44 | 1.13 | 1.59 | 2.08 | 0.83 | 0.99 | -0.08 | 0.26 | 0.49 | 1.99 | -0.09 | 3.14 | 0.36 | 0.91 | 0.53 | 1.80 | 0.83 | 0.82 | 0.29 |

U = unassisted, A = assisted.

### 4.5 By question type (pairs where assisted was higher)

| Feature | Behavioral (32 pairs) | Conceptual (16 pairs) | Opinion (16 pairs) |
| --- | --- | --- | --- |
| fixation_stability | 26/32 | 11/15 | 13/16 |
| saccade_rate | 5/32 | 2/15 | 5/16 |
| offcam_deviation | 5/32 | 4/15 | 2/16 |
| blink_rate | 7/32 | 4/15 | 3/16 |
| response_delay | 22/32 | 10/16 | 13/16 |
| pause_rate | 16/32 | 6/16 | 9/16 |
| avg_pause_length | 15/32 | 12/16 | 10/16 |
| pause_variance | 13/32 | 12/16 | 9/16 |
| filler_rate | 5/32 | 7/16 | 5/16 |
| speaking_rate | 22/32 | 7/16 | 3/16 |
| lexical_diversity | 26/32 | 12/16 | 14/16 |
| sentence_complexity | 8/32 | 6/16 | 5/16 |

---

<!-- END AUTO-GENERATED: everything below this line is hand-written and kept -->

> Sections 5–7 are hand-written. Last revised 2026-10-17, after volunteer 16. Sections 1–4 cover every recorded session, including the V01 pilot and the excluded V08, so their counts differ from this analysis. It uses the 14 analysed volunteers (V02–V07 and V09–V16, 111 clips). Feature values come from `data/features.csv`, built from scratch in one `build_features.py` run on 2026-10-17.

## 5. Interpretation

### 5.1 Who is analysed

- **V01** is the pilot session and is not in `labels.csv`.
- **V08 is excluded entirely** (`data/volunteer_exclusions.csv`). They answered the assisted round from their own knowledge: 0% of the suggestions' three-word phrases reused (Section 5.2). No run that includes V08 is reported.
- **V11 is kept.** During their first round the researcher explained the page's controls. That speech falls between question plays, outside the clips. V11 replayed unassisted q2 four times and q1 three times and practised before the final take, which is what those two clips contain.
- **V14 assisted q3, V15 unassisted q1 and V16 assisted q4** have speech between repeated plays, so the volunteer probably started answering and then restarted. The clips hold the final attempt and are kept.
- **Gaze is excluded for `v06_unassisted_q4`** (frozen for the whole clip), so training drops that clip.
- **Round order is balanced:** 7 volunteers did the assisted round first and 7 the unassisted round first. Because the first round always uses question Set A, question sets are balanced across conditions too.

### 5.2 Did volunteers use the assistant?

Each answer is compared with the suggested answer for that question: the figure is the share of the suggestion's three-word phrases spoken word for word. Unassisted answers are compared with the suggestion for the same question, which they never saw.

- **Assisted answers:** per-volunteer means of 30–89%. The lowest single answer is 18% (V11).
- **Unassisted answers:** mean 0.3%, highest 4.1%.
- **All 56 assisted clips are above every unassisted clip.**
- V09, V11 and V13 mixed the suggestion with their own words (means 30–44%). V06 and V07 read it almost word for word (80–89%).

### 5.3 Consistent signals

Unassisted → assisted, as the mean of per-volunteer means. Pause and language features are in real units (converted back from the Stage 1 z-scores); gaze features are raw. *dz* is the mean within-person change divided by its standard deviation.

| Feature | Unassisted → assisted | Same direction | Sign test p | dz | Exceptions |
| --- | --- | --- | --- | --- | --- |
| Word variety (type-token ratio) | 0.61 → 0.75 ↑ | 14/14 | < 0.001 | +1.30 | — |
| Words per sentence | 22.7 → 13.3 ↓ | 13/14 | 0.002 | −1.42 | V11 |
| Gaze steadiness | 834 → 1,811 ↑ | 13/14 | 0.002 | +0.69 | V15 |
| Looking away from the camera | 0.039 → 0.024 ↓ | 13/14 | 0.002 | −0.96 | V15 |
| Blinks per minute | 51 → 28 ↓ | 13/14 | 0.002 | −1.20 | V16 |
| Response delay (s) | 1.9 → 3.3 ↑ | 12/14 | 0.013 | +0.83 | V02, V13 |
| Fillers per 100 words | 3.2 → 1.7 ↓ | 11/14 | 0.057 | −0.93 | V10, V12, V14 |

This is the pattern expected from reading off a screen: a steadier gaze, suppressed blinking, short well-formed sentences with more varied words, and fewer fillers. Answer length barely differs (median 78 assisted vs 83 unassisted words), so the rise in word variety is not mainly a length effect.

### 5.4 Response delay

This replaces the earlier note about a split between volunteers 01–02 and 03–04. With 14 volunteers, 12 started later with the assistant (1.9 → 3.3 s). The assistant's answer appears 0.5–2.0 s after the question by design, and volunteers seem to wait for it and read a little before speaking.

### 5.5 Gaze depends on the setup

Mean within-person effect size of the gaze change, by session type:

| Group | Gaze steadiness | Looking away | Blinks |
| --- | --- | --- | --- |
| Researcher-run video calls (V02–V07) | 3.5 | 4.5 | 3.2 |
| Automatic browser sessions (V09–V12) | 1.3 | 2.3 | 2.4 |
| Automatic browser sessions (V13–V16) | 0.1 | 0.6 | 1.9 |

In a video call, a volunteer answering alone has nothing to read, so their eyes wander; reading the assistant steadies them. On the automatic page the question stays on screen in both rounds, so the contrast is smaller, and for V15 it reversed. This explanation has not been checked against the video. In the model, gaze alone reaches AUC 0.878, and the combined model reaches 0.993 on video-call clips against 0.933 on browser clips.

### 5.6 Mixed features

Speaking rate (8/14), pause rate (8/14), average pause length and pause variance (10/14) and saccade rate (11/14) show no reliable direction. Pauses look like an individual speaking habit. Saccade rate is unvalidated on webcam video (the "glasses?" flags in Section 1); the detector's AUC is unchanged without it.

### 5.7 Detector results

Logistic regression on speaker-centred features, leave-one-speaker-out cross-validation, pooled out-of-fold predictions. 95% confidence intervals come from a speaker bootstrap; p from 1000 within-speaker label shuffles (0.001 is the smallest possible value).

| Model | ROC-AUC [95% CI] | Balanced accuracy | p |
| --- | --- | --- | --- |
| **All 12 features** | **0.961** [0.927, 0.986] | **0.892** | ≤ 0.001 |
| Gaze only | 0.878 [0.737, 0.974] | 0.802 | ≤ 0.001 |
| Language only | 0.905 [0.819, 0.963] | 0.829 | ≤ 0.001 |
| Timing only | 0.787 [0.664, 0.888] | 0.775 | ≤ 0.001 |
| All features, no speaker centering | 0.949 [0.906, 0.981] | 0.838 | ≤ 0.001 |
| XGBoost, all features | 0.907 [0.819, 0.975] | 0.811 | ≤ 0.001 |
| Majority-class baseline | 0.500 | 0.492 | — |

Checks: without V11, AUC 0.957; without `saccade_rate`, 0.965; without word variety and sentence length, 0.907. Per volunteer, 6–8 of 8 clips are classified correctly; V15 and V16 are lowest at 6/8.

---

## 6. Limitations

- **Sample size:** 14 speakers. Speaker-bootstrap confidence intervals are still optimistic at this size, and every p-value is at the floor of the permutation test, so report p ≤ 0.001.
- **Scripted suggestions:** the suggested answers are short (50–80 words) and written in short sentences, so word variety and sentence length partly measure reading this particular script. Without those two features the AUC drops to 0.907. A real AI copilot that writes long paragraphs may look different.
- **Gaze depends on the setup** (Section 5.5).
- **Per-speaker centering** needs several answers from the same candidate, with both conditions present. Someone who used an assistant on every answer would be centred away. Without centering the AUC is 0.949.
- **Two protocols and a changing briefing:** 6 researcher-run video calls (V02–V07) and 8 automatic browser sessions (V09–V16). The briefing changed from V09's redone session onward. From V12 the instructions could be skipped after 5 s, and V12–V16 skipped every briefing (logged as `instructions_skipped`).
- **Wizard-of-Oz:** the assistant showed fixed, pre-written answers after set delays, not a live language model.
- **Feature scales:** gaze features are raw because the gaze baseline is domain-mismatched. They compare within a speaker, not across speakers.
- **Transcription:** Whisper's fallback decoding is not seeded. Rebuilding the table transcribed 1 of 72 earlier clips slightly differently (one filler word).

---

## 7. Next Steps

1. No further data collection is needed for the thesis.
2. Report only runs without V08, and justify the exclusion with the assistant-use check (Section 5.2), not the model's score.
3. Don't quote volunteers' answers: the consent form covers numerical data only.
4. After grading, delete `data/raw/` and drop the `transcript` column from `data/features.csv` (see the README).
5. Optional: validate `SACCADE_VELOCITY_THRESHOLD`, and seed Whisper's decoding (this needs Stage 1 rerun).
6. The web dashboard must reproduce per-candidate centering (see `models/detector_meta.json`).
