# Volunteer Interview Session Protocol & Script (General / Non-Technical Track)

**Study:** Detecting Covert Real-Time AI Assistance in Video Interviews  
**Author:** Yoihenba (Thesis Project)  
**Target Audience:** General Volunteers, Students, or Participants without Programming / Work Experience  

---

## 1. Pre-Session Setup Checklist

### 1.1 Hardware & Environment
* [ ] **Camera Positioning:** Webcam mounted directly above the monitor at eye level. Volunteer framed from mid-chest up.
* [ ] **Lighting:** Front-facing diffuse light. Avoid strong backlighting or glare on eyeglasses.
* [ ] **Audio Setup:** USB mic, headset, or clean laptop mic recording in uncompressed 16-bit audio (16 kHz minimum).
* [ ] **Environment:** Quiet room with minimal acoustic echo and zero background speech.

### 1.2 Screen Arrangement
* **Unassisted Round:** Fullscreen video call window or interviewer window positioned centrally just below the webcam.
* **Assisted Round (The Covert Setup):**
  * The real-time AI assistant window (or browser overlay) is placed in a realistic position (e.g., top-left, top-right, or transparent overlay adjacent to the video call window).
  * The volunteer should not need to turn their head 90 degrees; real-world covert cheaters place the window on the same monitor or close to the camera.

---

## 2. Counterbalancing & Experimental Design

To prevent ordering and fatigue bias, alternate whether the participant does the Unassisted or Assisted round first:

| Volunteer ID | First Condition (Round 1) | Second Condition (Round 2) |
| :--- | :--- | :--- |
| `volunteer_01`, `03`, `05`, `07`, `09`, `11` | **Unassisted** (Set A) | **Assisted** (Set B) |
| `volunteer_02`, `04`, `06`, `08`, `10`, `12` | **Assisted** (Set A) | **Unassisted** (Set B) |

Within each round, the questions are not asked in the order listed below. The assistant tool mixes them up in a balanced way: across every four volunteers of the same group, each question comes first, second, third and last exactly once. Read the questions in the order the control panel shows.

---

## 3. Accessible Question Bank (General Knowledge & Everyday Situations)

These questions require **zero programming or technical background**. They are designed so anyone can answer naturally off the top of their head, while still eliciting a structured 45–90 second answer that an AI assistant can generate answers for.

### Question Set A

* **Q1 (Behavioral / Teamwork):**  
  *"Can you tell me about a time you worked on a group project, event, or team task where someone wasn't doing their share of the work? How did you handle that situation?"*
* **Q2 (Behavioral / Time Management):**  
  *"Describe a time when you had multiple assignments, tasks, or deadlines piling up at the same time. How did you prioritize what to do first?"*
* **Q3 (Everyday Tech & Society):**  
  *"In your opinion, what are the biggest advantages and disadvantages of using Artificial Intelligence tools (like ChatGPT) in schools and college education?"*
* **Q4 (Conceptual Reasoning):**  
  *"If someone asked you to explain how cloud storage (like Google Drive or iCloud) works compared to saving files on a USB pen drive, how would you explain it in simple words?"*

---

### Question Set B

* **Q1 (Behavioral / Problem Solving):**  
  *"Tell me about a situation where something you planned (like a trip, an event, or a project) went completely wrong. How did you adapt and deal with it?"*
* **Q2 (Behavioral / Learning):**  
  *"Describe an instance where you had to learn a completely new skill, hobby, or subject from scratch. What was your strategy for getting good at it?"*
* **Q3 (Everyday Tech & Society):**  
  *"What do you think are the positive and negative impacts of social media algorithms on how people discover news and spend their daily time?"*
* **Q4 (Conceptual Reasoning):**  
  *"Electric vehicles (EVs) are becoming very popular. What do you see as the main benefits and the main challenges or drawbacks of switching from petrol cars to electric cars?"*

---

## 4. Verbal Scripts for Interviewer

### 4.1 Welcome & Introduction (Read verbatim)
> *"Hi [Volunteer Name], thank you for joining today! A quick word on what this study is about: more and more candidates in online job interviews secretly read their answers from an AI tool while they talk. This project is building a system that can tell the difference between someone answering on their own and someone using AI help, and to build it we need recordings of the same person doing both. The session takes around 20 to 25 minutes. We will do two short mock interview rounds with 4 questions each. None of these questions require any technical or coding knowledge—they are just everyday situational and opinion questions. Please treat this exactly like a real interview: no outside help of any kind is allowed, so no notes, phones, web searches, other AI tools, or anyone helping you. The only help you may use is the assistant tool I give you, and only in the round where it is on. Before we begin, please make sure you've signed the consent form. You can pause or stop at any point if you wish."*

---

### 4.2 Before the Unassisted Round
> *"In this round, you will answer 4 questions purely off the top of your head, just like a casual conversation or job interview. Take a few seconds to think if you need to, and speak at your natural pace. No notes, phone, web search, other AI tools, or anyone else's help. Ready? Let's start with Question 1..."*

---

### 4.3 Before the Assisted Round (The Covert Game)
> *"In this round, you will have an AI assistant tool open on your screen. As I ask each question, the assistant will generate a suggested answer in real-time. It takes a moment to appear after each question: you can wait for it, or fill the moment naturally as you would in a real interview.*  
>  
> ***You must use the suggested answer for every question.*** *Read it and give it as your own: you can read it out, put it in your own words, or add a little of your own, but the main points should come from the assistant. Please don't ignore it and answer from your own head; this round only works for the study if you really use it.*  
>  
> ***At the same time, your challenge is to deceive me:*** *try your absolute best to pass as a completely natural, unassisted candidate. This assistant is the only help allowed: no notes, phone, other AI tools, or anyone else's help. Try to maintain natural eye contact and pacing so that anyone watching the video wouldn't guess you're using an AI. Ready? Here is Question 1..."*

---

## 5. Post-Interview File Handling Workflow

### 5.1 Trimming Clips
Trim each recording to isolate each individual answer (starting the moment the interviewer finishes speaking the question, and ending when the volunteer finishes their answer):

```powershell
# Example trimming:
ffmpeg -i session_raw.mp4 -ss 00:01:10 -to 00:01:55 -c:v copy -c:a copy data/raw/volunteer_01/unassisted_q1.mp4
```

### 5.2 Folder Organization Standard
Store the video clips under [data/raw/](../data/raw/):

```text
data/raw/
├── volunteer_01/
│   ├── unassisted_q1.mp4
│   ├── unassisted_q2.mp4
│   ├── unassisted_q3.mp4
│   ├── unassisted_q4.mp4
│   ├── assisted_q1.mp4
│   ├── assisted_q2.mp4
│   ├── assisted_q3.mp4
│   └── assisted_q4.mp4
├── volunteer_02/
│   └── ...
```

---

## 6. Pipeline Execution

Once clips are saved in `data/raw/`:

1. **Add clip metadata to [data/labels.csv](../data/labels.csv)**:
   ```csv
   clip_id,volunteer_id,condition,question_num,question_type,label,video_path,audio_path,question_end_time
   v01_unassisted_q1,volunteer_01,unassisted,1,behavioral,0,data/raw/volunteer_01/unassisted_q1.mp4,,0.0
   v01_assisted_q1,volunteer_01,assisted,1,behavioral,1,data/raw/volunteer_01/assisted_q1.mp4,,0.0
   ```
   **`question_end_time` must be `0.0`** for every clip trimmed per Section 5.1 (clip starts exactly when the
   question ends). It is what lets the pipeline measure `response_delay` — how long the volunteer takes to start
   answering — which is expected to be one of the strongest signals (an AI tool needs time to generate an answer).
   If the column is missing or blank, `response_delay` becomes NaN for every clip and is silently dropped from training.

2. **Extract Features:**
   ```powershell
   python src/build_features.py
   ```

3. **Train Classifier (Leave-Speaker-Out):**
   ```powershell
   python src/train_model.py
   ```

4. **Run Feature Group Ablation:**
   ```powershell
   python src/evaluate_model.py
   ```
