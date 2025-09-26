import streamlit as st
import requests
import os
import speech_recognition as sr
import pyttsx3

# --- Backend API URL ---
API_URL = "http://127.0.0.1:8002/file-agent"

# --- Page Configuration with Nebula Theme ---
st.set_page_config(
    page_title="Jarvis",
    page_icon="🌀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Nebula Theme CSS Styling ---
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 1rem;
        font-weight: bold;
    }
    .sidebar .sidebar-content {
        background: linear-gradient(180deg, #2d3748 0%, #1a202c 100%);
    }
    .stButton button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 0.5rem 1rem;
        width: 100%;
        transition: all 0.3s ease;
    }
    .stButton button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
    }
    .chat-user {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 15px 15px 5px 15px;
        margin: 0.5rem 0;
        max-width: 80%;
        margin-left: auto;
    }
    .chat-agent {
        background: linear-gradient(135deg, #4a5568 0%, #2d3748 100%);
        color: white;
        padding: 1rem;
        border-radius: 15px 15px 15px 5px;
        margin: 0.5rem 0;
        max-width: 80%;
    }
    .command-card {
        background: linear-gradient(135deg, #2d3748 0%, #4a5568 100%);
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        border-left: 4px solid #667eea;
        cursor: pointer;
        transition: all 0.3s ease;
    }
    .command-card:hover {
        transform: translateX(5px);
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
    }
    .voice-section {
        background: linear-gradient(135deg, #1a202c 0%, #2d3748 100%);
        padding: 1.5rem;
        border-radius: 15px;
        margin-top: 2rem;
    }
    .current-dir {
        background: linear-gradient(135deg, #2d3748 0%, #1a202c 100%);
        padding: 0.5rem 1rem;
        border-radius: 10px;
        font-family: monospace;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# --- Suggested Commands ---
SUGGESTED_COMMANDS = {
    "File Operations": [
        "Create a new file named 'report.txt'",
        "List all files in the current directory",
        "Delete the file 'temp.txt'",
        "Rename 'old_name.txt' to 'new_name.txt'"
    ],
    "Directory Operations": [
        "Create a folder called 'documents'",
        "Change to the parent directory",
        "Show the current working directory",
        "List all subdirectories"
    ],
    "Content Operations": [
        "Read the content of 'notes.txt'",
        "Write 'Hello World' to 'greeting.txt'",
        "Append text to an existing file",
        "Search for 'error' in all text files"
    ],
    "System Operations": [
        "Show disk usage statistics",
        "Check file permissions for 'script.py'",
        "Get system information",
        "Find files larger than 1MB"
    ]
}

# --- Sidebar with Suggested Commands ---
with st.sidebar:
    st.markdown('<div class="main-header">🚀 Jarvis</div>', unsafe_allow_html=True)
    st.markdown("### 💡 Suggested Commands")
    st.markdown("Click any command below to execute it instantly.")
    
    # Current Directory Display
    st.markdown("### 📁 Current Directory")
    st.markdown(f'<div class="current-dir">{st.session_state.get("cwd", os.getcwd())}</div>', unsafe_allow_html=True)
    
    # Command Categories
    for category, commands in SUGGESTED_COMMANDS.items():
        with st.expander(f"📂 {category}", expanded=True):
            for cmd in commands:
                if st.button(cmd, key=f"cmd_{category}_{cmd}"):
                    # Store the command to be executed
                    st.session_state.queued_command = cmd
                    st.rerun()

# --- Main Content Area ---
st.markdown('<div class="main-header">Jarvis AI Assistant</div>', unsafe_allow_html=True)
st.markdown("💬 Type or speak to your Jarvis agent to manage files interactively.")

# --- Session State ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "cwd" not in st.session_state:
    st.session_state.cwd = os.getcwd()
if "queued_command" not in st.session_state:
    st.session_state.queued_command = None

# --- Text-to-Speech Engine ---
def speak_text(text):
    try:
        engine = pyttsx3.init()
        engine.setProperty('rate', 150)
        engine.setProperty('volume', 0.8)
        engine.say(text)
        engine.runAndWait()
    except Exception as e:
        st.error(f"Text-to-speech error: {e}")

# --- Chat Function ---
def send_to_agent(user_input):
    """Send request to backend and update chat history"""
    try:
        with st.spinner("🔄 Processing your request..."):
            response = requests.post(
                API_URL,
                json={"prompt": user_input, "current_dir": st.session_state.cwd},
                timeout=6000,
            )

        if response.status_code == 200:
            result = response.json()

            # Extract results
            agent_cmd = result.get("agent_command", {})
            exec_result = result.get("result", {})
            summary_result = result.get("summary", "")

            # Update cwd if needed
            if "directory" in exec_result:
                st.session_state.cwd = exec_result["directory"]

            # Build reply
            if "error" in exec_result:
                reply = f"❌ **Failure**: {exec_result['error']}"
            else:
                reply = f"✅ **Success**: Operation completed successfully"

            # Store conversation
            st.session_state.chat_history.append({"role": "user", "text": user_input})
            st.session_state.chat_history.append(
                {
                    "role": "agent",
                    "text": reply,
                    "command": agent_cmd,
                    "raw_result": exec_result,
                    "summary": summary_result,
                }
            )

            # 🔊 Speak the summary automatically
            if summary_result:
                speak_text(summary_result)

        else:
            st.session_state.chat_history.append(
                {"role": "agent", "text": f"❌ **Error {response.status_code}**: {response.text}"}
            )

    except Exception as e:
        st.session_state.chat_history.append(
            {"role": "agent", "text": f"⚠️ **Request failed**: {e}"}
        )

# --- Display Chat History ---
chat_container = st.container()

with chat_container:
    for msg in st.session_state.chat_history:
        if msg["role"] == "user":
            st.markdown(f'<div class="chat-user"><strong>You:</strong> {msg["text"]}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="chat-agent"><strong>Agent:</strong> {msg["text"]}</div>', unsafe_allow_html=True)
            
            if "command" in msg and msg["command"]:
                with st.expander("🔧 **Agent Command Details**", expanded=False):
                    st.json(msg["command"])
            
            if "raw_result" in msg and msg["raw_result"]:
                with st.expander("📊 **Execution Results**", expanded=False):
                    st.json(msg["raw_result"])
            
            if "summary" in msg and msg["summary"]:
                st.success(f"🎯 **Summary**: {msg['summary']}")
                
                # Voice playback option
                col1, col2 = st.columns([1, 10])
                with col1:
                    if st.button("🔊 Play", key=f"play_{len(st.session_state.chat_history)}"):
                        speak_text(msg['summary'])
                with col2:
                    st.caption("Click to hear the summary")

# --- Handle Queued Command from Sidebar ---
if st.session_state.queued_command:
    send_to_agent(st.session_state.queued_command)
    st.session_state.queued_command = None
    st.rerun()

# --- Input Section ---
st.markdown("---")
col1, col2 = st.columns([4, 1])

with col1:
    if prompt := st.chat_input("💭 Type your file management request here..."):
        send_to_agent(prompt)
        st.rerun()

with col2:
    if st.button("🔄 Clear Chat", use_container_width=True):
        st.session_state.chat_history = []
        st.rerun()

# --- Voice Input Section ---
st.markdown('<div class="voice-section">', unsafe_allow_html=True)
st.markdown("### 🎤 Voice Command")

voice_col1, voice_col2, voice_col3 = st.columns([1, 1, 2])

with voice_col1:
    if st.button("🎙️ Start Recording", use_container_width=True):
        st.session_state.recording = True

with voice_col2:
    if st.button("⏹️ Stop Recording", use_container_width=True):
        st.session_state.recording = False

if st.session_state.get('recording', False):
    st.info("🎙️ **Listening...** Speak your command now.")
    
    r = sr.Recognizer()
    try:
        with sr.Microphone() as source:
            r.adjust_for_ambient_noise(source, duration=1)
            audio = r.listen(source, timeout=10, phrase_time_limit=15)
            
        with st.spinner("🔍 Processing audio..."):
            text = r.recognize_google(audio)
            st.success(f"✅ **Recognized**: {text}")
            
            # Auto-send to agent
            send_to_agent(text)
            st.session_state.recording = False
            st.rerun()

    except sr.WaitTimeoutError:
        st.error("⏰ No speech detected within timeout. Try again.")
        st.session_state.recording = False
    except sr.UnknownValueError:
        st.error("❌ Could not understand the audio. Please try again.")
        st.session_state.recording = False
    except Exception as e:
        st.error(f"⚠️ Speech recognition error: {e}")
        st.session_state.recording = False

st.markdown('</div>', unsafe_allow_html=True)

# --- Footer ---
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; font-size: 0.8rem;">
    <p>🚀 Powered by Jarvis AI Agent | 💡 Use the sidebar commands for quick actions</p>
</div>
""", unsafe_allow_html=True)