import streamlit as st
import requests
import os
import speech_recognition as sr
import pyttsx3


# --- Backend API URL ---
API_URL = "http://127.0.0.1:8001/file-agent"  # Update if backend runs elsewhere

st.set_page_config(page_title="FileWise Chat", page_icon="📂", layout="wide")

st.title("📂 FileWise AI Chatbot")
st.write("Type or speak to your FileWise agent to manage files interactively.")


# --- Session State ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "cwd" not in st.session_state:
    st.session_state.cwd = os.getcwd()


# --- Text-to-Speech Engine ---
def speak_text(text):
    engine = pyttsx3.init()
    engine.setProperty('rate', 150)
    engine.say(text)
    engine.runAndWait()


# --- Chat Function ---
def send_to_agent(user_input):
    """Send request to backend and update chat history"""
    try:
        response = requests.post(
            API_URL,
            json={"prompt": user_input, "current_dir": st.session_state.cwd},
            timeout=6000,
        )

        if response.status_code == 200:
            result = response.json()
            print(result)

            # Extract results
            agent_cmd = result.get("agent_command", {})
            exec_result = result.get("result", {})
            summary_result = result.get("summary", "")

            # Update cwd if needed
            if "directory" in exec_result:
                st.session_state.cwd = exec_result["directory"]

            # Build reply
            if "error" in exec_result:
                reply = f"❌ Failure: {exec_result['error']}"
            else:
                reply = f"✅ Success: {exec_result}"

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
                {"role": "agent", "text": f"❌ Error {response.status_code}: {response.text}"}
            )

    except Exception as e:
        st.session_state.chat_history.append(
            {"role": "agent", "text": f"⚠️ Request failed: {e}"}
        )


# --- Display Chat ---
for msg in st.session_state.chat_history:
    if msg["role"] == "user":
        st.chat_message("user").markdown(msg["text"])
    else:
        st.chat_message("assistant").markdown(msg["text"])
        if "command" in msg:
            with st.expander("📝 Agent JSON Command"):
                st.json(msg["command"])
            with st.expander("📌 Execution Result"):
                st.json(msg["raw_result"])
        if "summary" in msg and msg["summary"]:
            st.info(f"🔊 Summary: {msg['summary']}")


# --- Input Box ---
if prompt := st.chat_input("Type a request (e.g., 'create a folder named reports')"):
    send_to_agent(prompt)
    st.rerun()


# --- Voice Input ---
st.markdown("---")
st.subheader("🎤 Voice Command")

if st.button("Start Recording"):
    r = sr.Recognizer()
    try:
        with sr.Microphone() as source:
            st.write("🎙️ Listening... Speak now.")
            r.adjust_for_ambient_noise(source, duration=1)
            audio = r.listen(source, timeout=15, phrase_time_limit=20)
            st.write("⏳ Recognizing...")
            text = r.recognize_google(audio)
            st.success(f"✅ You said: {text}")

            # Auto-send to agent
            send_to_agent(text)
            st.rerun()

    except sr.WaitTimeoutError:
        st.error("⌛ No speech detected. Try again.")
    except sr.UnknownValueError:
        st.error("❌ Could not understand the audio.")
    except Exception as e:
        st.error(f"⚠️ Speech recognition error: {e}")

