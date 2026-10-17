# Participant Information Sheet & Informed Consent Form

**Project Title:** Detecting Covert Real-Time AI Assistance in Video Interviews  
**Principal Investigator / Student:** Yoihenba Mongjam (Final Year Undergraduate / Postgraduate Thesis)  
**Academic Institution:** Department of Computer Science & Engineering  

---

## Part 1: Participant Information Sheet

### 1. Purpose of the Research
With the widespread availability of large language models (LLMs) and real-time audio-visual transcription tools, covert AI assistance during remote job interviews has become a growing concern. The goal of this research project is to study the subtle behavioral, timing, and linguistic differences between natural, unassisted spoken answers and answers delivered while consulting real-time AI assistance tools.

### 2. What Will Happen If You Participate
If you agree to take part in this study, you will participate in a mock remote video interview lasting approximately **20–30 minutes**:
1. **Briefing & Setup (~5 mins):** The researcher will explain the session, verify your webcam/microphone setup, and explain the tools.
2. **Round 1 (~8–10 mins):** You will answer a set of standard behavioral and technical interview questions under one condition (either natural/unassisted or using a covert real-time AI assistant).
3. **Round 2 (~8–10 mins):** You will answer a second set of questions under the alternative condition.
4. **Debriefing (~3 mins):** Short feedback and questions about your experience.

**Interview rule:** Treat the mock interview exactly like a real interview. No outside help of any kind is allowed: no notes, phones, web searches, other AI tools, or other people helping you. The only help you may use is the AI assistant provided by the researcher, and only in the round where it is switched on.

### 3. What Data Will Be Collected
* **Webcam Video Recording:** Used to extract head posture and eye gaze metrics (e.g., pupil fixation stability, saccadic jump rate, blink rate) via automated computer vision models (MediaPipe FaceMesh).
* **Audio Recording:** Used to compute speech timing metrics (response delay, pauses via voice activity detection) and linguistic fluency metrics (filler word rates, speaking rate via Whisper transcription).
* **Demographic Metadata (Optional):** Age group, primary spoken language, and tech background (for accent and baseline diversity analysis).

### 4. Confidentiality, Privacy & Data Security
* **Anonymization:** You will be assigned an anonymous participant code (e.g., `volunteer_01`). Your real name, contact details, and student ID will never be linked to the feature tables or published results.
* **Strict Storage Security:** Raw video and audio files will be stored exclusively on an encrypted, password-protected local hard drive. **No raw video clips will ever be committed to public repositories (such as GitHub) or uploaded to cloud storage.**
* **Destruction / Retention:** Only anonymized numerical feature matrices (`features.csv`) will be retained for model evaluation in the thesis report. Raw video files will be permanently deleted upon thesis examination and grading completion.
* **No Public Video Playback:** Your video will not be shown or replayed during presentations without your separate, explicit written consent.

### 5. Voluntary Participation & Right to Withdraw
Participation in this study is **completely voluntary**. You may choose to stop the interview, decline to answer any specific question, or withdraw from the study at any point during or up to 14 days after the session without giving any reason and without any penalty or academic consequences. Upon withdrawal, all your video and audio recordings will be immediately deleted.

---

## Part 2: Informed Consent Statement

Please review each statement and check the boxes to indicate your agreement:

- [ ] **I confirm** that I have read and understood the Participant Information Sheet for this study and have had the opportunity to ask questions.
- [ ] **I understand** that my participation is voluntary and that I am free to withdraw at any time without giving a reason.
- [ ] **I agree** to treat the mock interview as a real interview and not to use any outside help, other than the AI assistant provided in the assisted round.
- [ ] **I agree** to have my video and audio recorded during the mock interview session for automated feature extraction purposes.
- [ ] **I understand** that raw video/audio recordings will be stored securely, kept strictly confidential, and anonymized under a participant ID.
- [ ] **I understand** that anonymized numerical data derived from my recording will be used in a thesis report and related academic presentations.

---

### Participant Sign-off

**Participant Full Name (Printed):** ____________________________________________  

**Participant Signature:** ___________________________   **Date:** _______________  

**Email Address (for withdrawal requests):** ____________________________________  

---

### Researcher Confirmation

I confirm that I have explained the nature and purpose of this study to the participant named above and provided an opportunity to discuss any questions or concerns.

**Researcher Name:** Yoihenba  

**Researcher Signature:** ___________________________   **Date:** _______________  
