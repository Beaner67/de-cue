# Volunteer Interview Session Protocol & Script

**Study:** Detecting Covert Real-Time AI Assistance in Video Interviews  
**Author:** Yoihenba Mongjam (Thesis Project)  
**Target Sample:** 10–12 Volunteers (Minimum 5–7 for Pilot Validation)  

---

## 1. Pre-Session Setup Checklist

### 1.1 Hardware & Environment
* [ ] **Camera Positioning:** Webcam mounted directly above the monitor at eye level. Volunteer framed from mid-chest up.
* [ ] **Lighting:** Front-facing diffuse light. Avoid strong backlighting or glare on eyeglasses.
* [ ] **Audio Setup:** External USB mic or high-quality headset/laptop mic recording in uncompressed 16-bit audio (16 kHz minimum).
* [ ] **Environment:** Quiet room with minimal acoustic reverberation and zero background speech.

### 1.2 Screen Arrangement
* **Unassisted Round:** Fullscreen video call window or interviewer window positioned centrally just below the webcam.
* **Assisted Round (The Covert Setup):**
  * The real-time AI assistant window (or browser overlay) must be placed in a realistic position (e.g., top-left, top-right, or transparent overlay adjacent to the video window).
  * Ensure the volunteer does not need to turn their entire head 90 degrees; real-world covert cheaters place the window on the same monitor or a secondary monitor close to the camera.

---

## 2. Counterbalancing & Experimental Design

To prevent **ordering effects** (e.g., fatigue, relaxation, or getting accustomed to the questions):
* **Within-Subjects Design:** Every volunteer completes both conditions (**Unassisted** vs. **Assisted**).
* **Counterbalanced Order:**

| Volunteer ID | First Condition (Round 1) | Second Condition (Round 2) |
| :--- | :--- | :--- |
| `volunteer_01`, `03`, `05`, `07`, `09`, `11` | **Unassisted** (Set A) | **Assisted** (Set B) |
| `volunteer_02`, `04`, `06`, `08`, `10`, `12` | **Assisted** (Set A) | **Unassisted** (Set B) |

---

## 3. Standardized Question Bank

Each volunteer answers **4 questions per round** (2 behavioral, 2 technical). The question sets are matched for conceptual complexity and expected answer duration (~45–90 seconds).

### Question Set A

* **Q1 (Behavioral):**  
  *"Can you tell me about a time you had to work under a tight deadline with incomplete requirements? How did you prioritize what to build first?"*
* **Q2 (Behavioral):**  
  *"Describe a situation where you had a technical disagreement with a teammate or peer. How did you communicate your perspective and resolve it?"*
* **Q3 (Technical):**  
  *"Can you explain the key differences between SQL (relational) and NoSQL databases, and what factors guide your decision to choose one over the other in a system architecture?"*
* **Q4 (Technical):**  
  *"What is the difference between concurrency and parallelism, and how does Python's Global Interpreter Lock (GIL) affect them in CPU-bound vs. I/O-bound tasks?"*

---

### Question Set B

* **Q1 (Behavioral):**  
  *"Tell me about a complex project where something went critically wrong in production or testing. How did you diagnose the root cause and handle it?"*
* **Q2 (Behavioral):**  
  *"Can you describe an instance where you had to quickly learn an unfamiliar technology, language, or framework to complete an assignment? What was your learning strategy?"*
* **Q3 (Technical):**  
  *"Can you explain what happens under the hood when a user types a URL (like `https://example.com`) into a browser and presses Enter, from DNS lookup to DOM rendering?"*
* **Q4 (Technical):**  
  *"Explain the concept of containerization using Docker versus traditional virtual machines (VMs). What are the advantages and security trade-offs?"*

---

## 4. Verbal Scripts for Interviewer

### 4.1 Welcome & Introduction (Read verbatim)
> *"Hi [Volunteer Name], thank you for participating in this research study today. The entire session will take around 25 minutes. We will conduct two short mock interview rounds with 4 questions each. Before we begin, please make sure you have reviewed and signed the consent form. You can stop or take a break at any point."*

---

### 4.2 Before the Unassisted Round
> *"In this round, you will answer 4 standard interview questions purely off the top of your head, just like a normal job interview. Speak naturally at your normal pace. If you need a moment to think before speaking, that is completely fine. Ready? Let's start with Question 1..."*

---

### 4.3 Before the Assisted Round (The Covert Incentive)
> *"In this round, you will have an AI assistant tool active on your screen. As I ask each question, the assistant will generate an answer in real-time.*  
>  
> ***Your primary objective in this round is to deceive the interviewer:*** *try your best to pass as a completely natural, unassisted candidate. You may read from the assistant, rephrase its points, or blend it with your own words. Maintain normal eye contact and conversational rhythm so that someone reviewing your video wouldn't suspect you are using an AI. Ready? Here comes Question 1..."*

---

## 5. Post-Interview File Handling Workflow

### 5.1 Splitting & Trimming Clips
Slice the continuous recording into individual question clips using `ffmpeg` or any video editor. Trim each clip so it starts **immediately when the interviewer finishes speaking the question** and ends when the volunteer finishes their answer:

```powershell
# Example trimming:
ffmpeg -i session_raw.mp4 -ss 00:01:23 -to 00:02:15 -c:v copy -c:a copy data/raw/volunteer_01/unassisted_q1.mp4
```

### 5.2 Folder Organization Standard
Store the video clips under [data/raw/](file:///e:/Yoihenba/Thesis%20project/model%20training/ai-interview-detection/data/raw/) using this standardized directory tree:

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

## 6. Updating `labels.csv` & Running the Model

Once clips are saved in `data/raw/`:

1. **Add the entries to [data/labels.csv](file:///e:/Yoihenba/Thesis%20project/model%20training/ai-interview-detection/data/labels.csv):**
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

3. **Train & Cross-Validate Model (leave-speaker-out, pooled out-of-fold metrics, permutation test):**
   ```powershell
   python src/train_model.py
   ```

4. **Generate Ablation Evaluation Table:**
   ```powershell
   python src/evaluate_model.py
   ```
