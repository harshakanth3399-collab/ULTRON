# ⚡ ULTRON - Personal AI Assistant & Holographic Visualizer

> **A 100% Private, Real-Time AI Assistant & 150,000 Particle Holographic Visualizer for Harsha.**

[![GitHub Live Demo](https://img.shields.io/badge/Live_Demo-GitHub_Pages-00d9ff?style=for-the-badge&logo=github)](https://harshakanth3399-collab.github.io/ULTRON/)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![OpenGL](https://img.shields.io/badge/ModernGL-4.6-555555?style=for-the-badge&logo=opengl)](https://moderngl.readthedocs.io/)
[![Speech](https://img.shields.io/badge/Speech-Faster_Whisper-ffbf26?style=for-the-badge)](https://github.com/SYSTRAN/faster-whisper)

---

## 🌐 Live Web Preview & GitHub Link

Check out the interactive live web preview here:  
👉 **[https://harshakanth3399-collab.github.io/ULTRON/](https://harshakanth3399-collab.github.io/ULTRON/)**

---

## 📁 Crystal-Clear Project Layout (Simple & Easy to Understand)

```
ULTRON/
├── 🚀 main.py                <-- START HERE: Double-click or run 'python main.py'
├── 🎨 app.py                 <-- Desktop Holographic GUI Window
├── 🧪 test_renderer.py       <-- Test graphics renderer window
│
├── 🧠 core/                  <-- AI Brain & Speech Core
│   ├── ai.py                 <-- Connects to local Ollama LLM
│   ├── speech.py             <-- Listens to microphone & transcribes speech
│   ├── speech_engine.py      <-- Speaks back to you in TTS voice
│   └── router.py             <-- Command router & memory checker
│
├── 🔒 security/              <-- Voice Security & Intruder Shield
│   └── voice_auth.py         <-- Verifies Harsha's voice print & rejects intruders
│
├── 🌌 graphics/              <-- 150,000 Particle J.A.R.V.I.S. Visualizer
│   ├── jarvis_visualizer.py  <-- 4 Concentric 3D Rotating Rings + 3D Oscilloscope
│   ├── renderer.py           <-- Hardware-accelerated ModernGL GPU pipeline
│   └── particle_engine.py    <-- 150,000 audio-reactive particles
│
├── 💾 memory/                <-- Private Local Storage (100% Private)
│   └── profile.json          <-- Harsha's saved notes and preferences
│
└── 🌐 docs/                  <-- Live Web Link for GitHub Pages
    └── index.html            <-- Interactive WebGL browser visualizer
```

---

## ✨ Features

- 🔒 **Biometric Voice Authentication**: Encodes Harsha's spectral voice print. If anyone else speaks, ULTRON detects the intruder and rejects them.
- 🌌 **150,000 Particle Visualizer**: 3D Concentric Rotating Rings & 3D Audio Frequency Oscilloscope running at 60 FPS in ModernGL.
- ⚡ **Instant Real-Time Audio Reactivity**: PyAudio background mic stream updates GPU visualizer 60 times per second.
- 🧠 **100% Local & Private**: Zero data leaks, zero cloud training, 100% private on Harsha's computer.

---

## 🚀 Quick Start

1. Install Python dependencies:
   ```bash
   pip install PySide6 moderngl numpy PyOpenGL faster-whisper speechrecognition pyaudio ollama
   ```

2. Launch ULTRON:
   ```bash
   python main.py
   ```