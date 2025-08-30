# 📂 FileWise Jarvis – Voice-Activated File Management Assistant

FileWise Jarvis is a voice-controlled AI assistant that helps you **manage files and folders** using natural language.  
It integrates **FastAPI** for backend execution, **Streamlit** for the UI, and supports **speech recognition (STT)** + **text-to-speech (TTS)** for a hands-free experience.

---

## 🚀 Features
- 🎤 **Voice Activation with Wake Word** ("Jarvis")  
- 📂 **File & Folder Management** (create, delete, rename, move, etc.)  
- 🖥️ **FastAPI Backend** for command execution  
- 💬 **Streamlit Frontend** with chat-like interface  
- 🔊 **Text-to-Speech Summaries** (auto speaks results)  
- ⚡ **Always-On Background Listener**  
- ✍️ **Natural Language Commands** (e.g., "create a folder named reports")

---

## 🛠️ Tech Stack
- [FastAPI](https://fastapi.tiangolo.com/) – backend API  
- [Streamlit](https://streamlit.io/) – frontend UI  
- [SpeechRecognition](https://pypi.org/project/SpeechRecognition/) – speech-to-text  
- [PyAudio](https://people.csail.mit.edu/hubert/pyaudio/) – microphone input  
- [pyttsx3](https://pypi.org/project/pyttsx3/) – text-to-speech  
- [Requests](https://docs.python-requests.org/) – API communication  

---

## 📂 Project Structure
```
FileWise-Jarvis/
│── backend/
│ └── main.py # FastAPI backend logic
│── frontend/
│ └── app.py # Streamlit frontend with voice control
│── requirements.txt
│── README.md
```


---

## ⚙️ Installation

### 1. Clone Repo
```bash
git clone https://github.com/<your-username>/FileWise-Jarvis.git
cd FileWise-Jarvis
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate   # Mac/Linux
venv\Scripts\activate      # Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Install Extra System Dependencies (if needed)


- Windows:
```bash
pip install pyaudio
```

If error: 
```bash
pip install pipwin && pipwin install pyaudio
```
- Linux (Debian/Ubuntu):
```bash
sudo apt-get install portaudio19-dev
```

- Mac (brew):
```bash
brew install portaudio
```

### 5. ▶️ Running the App
- Start backend
  
```bash
uvicorn backend.main:app --reload --port 8000
```
- Start Frontend (Streamlit)

```bash
streamlit run frontend/app.py
```

### 6. Usage

 - Say “Jarvis” to wake up the assistant
 - Speak a command like:
 - "Create a folder named reports"
 - "Delete the file notes.txt"
 - The agent will execute it and speak back the summary

### 7. Roadmap
 - Multi-user support
 - Secure file permissions
 - Cloud integration (Google Drive, OneDrive, S3)
 - Whisper/OpenAI API for better STT
 - Smarter intent detection

### 🤝 Contributing

Pull requests are welcome! For major changes, please open an issue first to discuss what you would like to change.



---

📜 License

MIT License © 2025

