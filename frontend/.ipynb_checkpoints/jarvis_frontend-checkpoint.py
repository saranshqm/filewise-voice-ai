import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import requests
import threading
import json
from datetime import datetime
import speech_recognition as sr
import pyaudio
import time
import pyttsx3  # Added for text-to-speech

class VoiceAssistantUI:
    def __init__(self, root):
        self.root = root
        self.root.title("JARVIS Voice Assistant - LOCAL VOICE")
        self.root.geometry("700x600")
        self.root.configure(bg='#2c3e50')
        
        self.base_url = "http://127.0.0.1:8002"
        self.is_listening = False
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.wake_words = ["jarvis", "javis", "jar"]
        self.voice_thread = None
        
        # Initialize text-to-speech engine
        self.tts_engine = pyttsx3.init()
        self.tts_engine.setProperty('rate', 150)  # Speech rate
        self.tts_engine.setProperty('volume', 0.8)  # Volume level
        
        self.setup_ui()
        self.setup_microphone()
        self.test_connection()

    def clear_logs(self):
        """Clear the voice activity logs"""
        self.log_text.config(state='normal')
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state='disabled')
        self.log_message("📋 Logs cleared")
        
    def setup_ui(self):
        # Title
        title_label = tk.Label(
            self.root, 
            text="🎯 JARVIS Voice Assistant - LOCAL VOICE RECOGNITION", 
            font=('Arial', 14, 'bold'),
            fg='#ecf0f1',
            bg='#2c3e50'
        )
        title_label.pack(pady=10)
        
        # TTS Control Frame
        tts_frame = tk.Frame(self.root, bg='#34495e')
        tts_frame.pack(pady=5, fill='x', padx=20)
        
        tk.Label(
            tts_frame,
            text="Speech Response:",
            font=('Arial', 10, 'bold'),
            fg='#f39c12',
            bg='#34495e'
        ).pack(anchor='w')
        
        tts_control_frame = tk.Frame(tts_frame, bg='#34495e')
        tts_control_frame.pack(fill='x', pady=5)
        
        self.tts_enabled = tk.BooleanVar(value=True)
        tts_toggle = tk.Checkbutton(
            tts_control_frame,
            text="Enable Voice Responses",
            variable=self.tts_enabled,
            font=('Arial', 9),
            fg='#ecf0f1',
            bg='#34495e',
            selectcolor='#2c3e50'
        )
        tts_toggle.pack(side='left', padx=5)
        
        test_tts_btn = tk.Button(
            tts_control_frame,
            text="Test Speech",
            command=self.test_tts,
            bg='#16a085',
            fg='white',
            font=('Arial', 9),
            width=12
        )
        test_tts_btn.pack(side='left', padx=5)
        
        # Debug Info Frame
        debug_frame = tk.Frame(self.root, bg='#34495e')
        debug_frame.pack(pady=5, fill='x', padx=20)
        
        tk.Label(
            debug_frame,
            text="Voice Recognition Status:",
            font=('Arial', 10, 'bold'),
            fg='#f39c12',
            bg='#34495e'
        ).pack(anchor='w')
        
        self.debug_text = tk.Label(
            debug_frame,
            text="Microphone ready - Click 'Start Listening'",
            font=('Arial', 9),
            fg='#ecf0f1',
            bg='#2c3e50',
            wraplength=660,
            justify='left'
        )
        self.debug_text.pack(fill='x', pady=2, ipady=2)
        
        # Control Frame
        control_frame = tk.Frame(self.root, bg='#2c3e50')
        control_frame.pack(pady=10, fill='x', padx=20)
        
        self.start_btn = tk.Button(
            control_frame,
            text="Start Listening",
            command=self.start_listening,
            bg='#27ae60',
            fg='white',
            font=('Arial', 12),
            width=15
        )
        self.start_btn.pack(side='left', padx=5)
        
        self.stop_btn = tk.Button(
            control_frame,
            text="Stop Listening",
            command=self.stop_listening,
            bg='#e74c3c',
            fg='white',
            font=('Arial', 12),
            width=15,
            state='disabled'
        )
        self.stop_btn.pack(side='left', padx=5)
        
        self.test_btn = tk.Button(
            control_frame,
            text="Test Microphone",
            command=self.test_microphone,
            bg='#3498db',
            fg='white',
            font=('Arial', 12),
            width=15
        )
        self.test_btn.pack(side='left', padx=5)
        
        # Manual Command Frame
        command_frame = tk.Frame(self.root, bg='#2c3e50')
        command_frame.pack(pady=5, fill='x', padx=20)
        
        tk.Label(
            command_frame,
            text="Quick Test Commands:",
            font=('Arial', 10, 'bold'),
            fg='#bdc3c7',
            bg='#2c3e50'
        ).pack(anchor='w')
        
        button_frame = tk.Frame(command_frame, bg='#2c3e50')
        button_frame.pack(fill='x', pady=5)
        
        # Quick test buttons
        test_commands = [
            ("Open Notepad", "open notepad"),
            ("List Files", "list files in current directory"),
            ("Open Calculator", "open calculator"),
            ("What's the time?", "what time is it")
        ]
        
        for text, command in test_commands:
            btn = tk.Button(
                button_frame,
                text=text,
                command=lambda cmd=command: self.send_command_to_backend(cmd),
                bg='#8e44ad',
                fg='white',
                font=('Arial', 9),
                width=15
            )
            btn.pack(side='left', padx=2)
        
        # Status Frame
        status_frame = tk.Frame(self.root, bg='#2c3e50')
        status_frame.pack(pady=10, fill='x', padx=20)
        
        tk.Label(
            status_frame,
            text="Current Status:",
            font=('Arial', 12, 'bold'),
            fg='#bdc3c7',
            bg='#2c3e50'
        ).pack(anchor='w')
        
        self.status_text = tk.Label(
            status_frame,
            text="🔴 Stopped - Click 'Start Listening' to begin",
            font=('Arial', 11),
            fg='#ecf0f1',
            bg='#34495e',
            wraplength=660,
            justify='left'
        )
        self.status_text.pack(fill='x', pady=5, ipady=5)
        
        # Wake Words Frame
        wake_frame = tk.Frame(self.root, bg='#2c3e50')
        wake_frame.pack(pady=5, fill='x', padx=20)
        
        tk.Label(
            wake_frame,
            text="Wake Words (say clearly):",
            font=('Arial', 12, 'bold'),
            fg='#bdc3c7',
            bg='#2c3e50'
        ).pack(anchor='w')
        
        wake_words_text = tk.Label(
            wake_frame,
            text="🚨 'JARVIS', 'JAVIS', or 'JAR' - then speak your command",
            font=('Arial', 11, 'bold'),
            fg='#e74c3c',
            bg='#2c3e50'
        )
        wake_words_text.pack(anchor='w', pady=2)
        
        # Clarification Frame
        # clarification_frame = tk.Frame(self.root, bg='#2c3e50')
        # clarification_frame.pack(pady=5, fill='x', padx=20)
        
        # tk.Label(
        #     clarification_frame,
        #     text="Clarification Mode:",
        #     font=('Arial', 10, 'bold'),
        #     fg='#f39c12',
        #     bg='#2c3e50'
        # ).pack(anchor='w')
        
        # clarification_text = tk.Label(
        #     clarification_frame,
        #     text="🔍 If command is unclear, I will ask for clarification",
        #     font=('Arial', 9),
        #     fg='#ecf0f1',
        #     bg='#2c3e50'
        # )
        # clarification_text.pack(anchor='w', pady=2)
        
        # Log Frame
        log_frame = tk.Frame(self.root, bg='#2c3e50')
        log_frame.pack(pady=10, fill='both', expand=True, padx=20)
        
        log_header_frame = tk.Frame(log_frame, bg='#2c3e50')
        log_header_frame.pack(fill='x')
        
        tk.Label(
            log_header_frame,
            text="Voice Activity Log:",
            font=('Arial', 12, 'bold'),
            fg='#bdc3c7',
            bg='#2c3e50'
        ).pack(side='left', anchor='w')
        
        # ADDED: Clear Logs button
        clear_logs_btn = tk.Button(
            log_header_frame,
            text="Clear Logs",
            command=self.clear_logs,
            bg='#e67e22',
            fg='white',
            font=('Arial', 9),
            width=10
        )
        clear_logs_btn.pack(side='right', padx=5)
        
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            height=15,
            bg='#1a252f',
            fg='#ecf0f1',
            font=('Consolas', 9),
            wrap=tk.WORD
        )
        self.log_text.pack(fill='both', expand=True)
        self.log_text.config(state='disabled')
    
    def speak_response(self, text):
        """Speak the response using text-to-speech"""
        if self.tts_enabled.get():
            def speak_thread():
                try:
                    self.tts_engine.say(text)
                    self.tts_engine.runAndWait()
                except Exception as e:
                    self.log_message(f"❌ TTS Error: {e}")
            
            threading.Thread(target=speak_thread, daemon=True).start()
    
    def test_tts(self):
        """Test the text-to-speech functionality"""
        test_text = "Hello, I am JARVIS. Voice responses are working correctly."
        self.speak_response(test_text)
        self.log_message("🔊 Testing text-to-speech: 'Hello, I am JARVIS'")
    
    def ask_clarification(self, command):
        """Ask for clarification when command is unclear"""
        clarification_text = f"I'm not sure about your command: '{command}'. Could you please clarify what you want me to do?"
        
        # Speak the clarification
        self.speak_response(clarification_text)
        
        # Show in UI
        self.log_message(f"❓ Clarification requested: {command}")
        self.status_text.config(text="❓ Please clarify your command")
        
        # Optionally show a dialog box for manual clarification
        self.root.after(0, lambda: self.show_clarification_dialog(command))
    
    def show_clarification_dialog(self, original_command):
        """Show a dialog box for manual clarification"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Clarification Needed")
        dialog.geometry("400x200")
        dialog.configure(bg='#2c3e50')
        dialog.transient(self.root)
        dialog.grab_set()
        
        tk.Label(
            dialog,
            text="Clarification Needed",
            font=('Arial', 12, 'bold'),
            fg='#f39c12',
            bg='#2c3e50'
        ).pack(pady=10)
        
        tk.Label(
            dialog,
            text=f"Original command: '{original_command}'",
            font=('Arial', 9),
            fg='#ecf0f1',
            bg='#2c3e50',
            wraplength=380
        ).pack(pady=5)
        
        tk.Label(
            dialog,
            text="Please clarify your command:",
            font=('Arial', 10),
            fg='#ecf0f1',
            bg='#2c3e50'
        ).pack(pady=5)
        
        clarification_entry = tk.Entry(dialog, width=40, font=('Arial', 10))
        clarification_entry.pack(pady=10)
        clarification_entry.focus()
        
        def submit_clarification():
            clarified_command = clarification_entry.get().strip()
            if clarified_command:
                dialog.destroy()
                self.send_command_to_backend(clarified_command)
                self.speak_response("Thank you for the clarification. Processing your command now.")
        
        def cancel_clarification():
            dialog.destroy()
            self.speak_response("Clarification cancelled. Please try your command again.")
        
        button_frame = tk.Frame(dialog, bg='#2c3e50')
        button_frame.pack(pady=10)
        
        tk.Button(
            button_frame,
            text="Submit",
            command=submit_clarification,
            bg='#27ae60',
            fg='white',
            width=10
        ).pack(side='left', padx=5)
        
        tk.Button(
            button_frame,
            text="Cancel",
            command=cancel_clarification,
            bg='#e74c3c',
            fg='white',
            width=10
        ).pack(side='left', padx=5)
        
        # Bind Enter key to submit
        dialog.bind('<Return>', lambda e: submit_clarification())
    
    def setup_microphone(self):
        """Initialize microphone"""
        try:
            # Test the microphone
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
            self.log_message("✅ Microphone initialized successfully")
            self.update_debug_info("Microphone ready for voice recognition")
            return True
        except Exception as e:
            self.log_message(f"❌ Microphone setup failed: {e}")
            self.update_debug_info(f"Microphone error: {e}")
            return False
    
    def update_debug_info(self, message):
        """Update the debug information display"""
        self.debug_text.config(text=message)
        
    def log_message(self, message):
        """Log message with timestamp"""
        self.log_text.config(state='normal')
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')
        
    def test_connection(self):
        """Test connection to backend"""
        self.update_debug_info("Testing connection to backend...")
        try:
            response = requests.get(f"{self.base_url}/", timeout=5)
            if response.status_code == 200:
                self.log_message("✅ Connected to backend API")
                self.update_debug_info("✅ Backend connection successful")
                return True
            else:
                self.log_message(f"❌ Backend returned status: {response.status_code}")
                return False
        except Exception as e:
            self.log_message(f"❌ Cannot connect to backend: {str(e)}")
            self.update_debug_info("❌ Backend connection failed")
            return False
            
    def start_listening(self):
        """Start voice listening"""
        if self.is_listening:
            return
            
        self.is_listening = True
        self.start_btn.config(state='disabled')
        self.stop_btn.config(state='normal')
        self.status_text.config(text="🎯 Listening for wake words... Say 'JARVIS'")
        self.update_debug_info("🎤 Listening for wake words...")
        self.log_message("🚀 Voice recognition started - waiting for wake word")
        
        # Start voice recognition in a separate thread
        self.voice_thread = threading.Thread(target=self.voice_recognition_loop, daemon=True)
        self.voice_thread.start()
        
    def stop_listening(self):
        """Stop voice listening"""
        self.is_listening = False
        self.start_btn.config(state='normal')
        self.stop_btn.config(state='disabled')
        self.status_text.config(text="🔴 Voice recognition stopped")
        self.update_debug_info("Voice recognition stopped")
        self.log_message("⏹️ Voice recognition stopped")
        
    def test_microphone(self):
        """Test microphone functionality"""
        def test_thread():
            self.update_debug_info("Testing microphone... Speak now!")
            try:
                # Create a new microphone instance for testing to avoid context issues
                test_mic = sr.Microphone()
                with test_mic as source:
                    self.recognizer.adjust_for_ambient_noise(source, duration=1)
                    self.log_message("🔊 Listening for test speech...")
                    audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=3)
                    text = self.recognizer.recognize_google(audio)
                    self.log_message(f"✅ Microphone test successful: '{text}'")
                    self.update_debug_info(f"✅ Heard: '{text}'")
            except sr.WaitTimeoutError:
                self.log_message("❌ No speech detected during test")
                self.update_debug_info("❌ No speech detected")
            except sr.UnknownValueError:
                self.log_message("❌ Could not understand speech")
                self.update_debug_info("❌ Speech not understood")
            except Exception as e:
                self.log_message(f"❌ Microphone test error: {e}")
                self.update_debug_info(f"❌ Test failed: {e}")
                
        threading.Thread(target=test_thread, daemon=True).start()
    
    def voice_recognition_loop(self):
        """Main voice recognition loop - FIXED VERSION"""
        self.log_message("🎧 Voice recognition loop started")
        
        # Use a single microphone context for the entire loop
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
            
            while self.is_listening:
                try:
                    # Listen for wake word
                    self.update_debug_info("👂 Listening for wake word...")
                    self.status_text.config(text="👂 Listening... Say 'JARVIS'")
                    
                    # Listen with shorter timeout for responsiveness
                    audio = self.recognizer.listen(source, timeout=2, phrase_time_limit=3)
                    text = self.recognizer.recognize_google(audio).lower()
                    
                    self.log_message(f"🎙️ Heard: '{text}'")
                    self.update_debug_info(f"Heard: '{text}'")
                    
                    # Check for wake words
                    wake_word_detected = False
                    detected_word = ""
                    for wake_word in self.wake_words:
                        if wake_word in text:
                            wake_word_detected = True
                            detected_word = wake_word
                            break
                    
                    if wake_word_detected:
                        self.log_message(f"🔔 Wake word '{detected_word}' detected!")
                        self.update_debug_info(f"🚨 Wake word detected! Listening for command...")
                        
                        # Listen for command immediately
                        self.listen_for_command(source)
                        
                except sr.WaitTimeoutError:
                    continue  # No speech detected, continue listening
                except sr.UnknownValueError:
                    # Speech was unintelligible, continue listening
                    continue
                except sr.RequestError as e:
                    self.log_message(f"❌ Speech recognition API error: {e}")
                    time.sleep(2)  # Wait before retrying
                except Exception as e:
                    self.log_message(f"❌ Voice recognition error: {e}")
                    time.sleep(1)  # Wait before retrying
    
    def listen_for_command(self, source):
        """Listen for command after wake word - FIXED VERSION"""
        try:
            self.status_text.config(text="🎯 Listening for command... Speak now!")
            self.update_debug_info("🎤 Listening for command...")
            
            # Use the same source that's already in context
            audio = self.recognizer.listen(source, timeout=6, phrase_time_limit=6)
            command = self.recognizer.recognize_google(audio)
            
            self.log_message(f"🎯 Command received: '{command}'")
            self.update_debug_info(f"✅ Command: '{command}'")
            self.status_text.config(text=f"📡 Sending command to backend: {command}")
            
            # REMOVED: Clarification check
            # Send command directly to backend
            self.send_command_to_backend(command)
            
        except sr.WaitTimeoutError:
            self.log_message("❌ No command detected within timeout")
            self.update_debug_info("❌ Command timeout")
            self.status_text.config(text="❌ No command detected")
        except sr.UnknownValueError:
            self.log_message("❌ Could not understand command")
            self.update_debug_info("❌ Command not understood")
            self.status_text.config(text="❌ Command not understood")
        except Exception as e:
            self.log_message(f"❌ Command listening error: {e}")
            self.update_debug_info(f"❌ Command error: {e}")
            self.status_text.config(text="❌ Error listening for command")
    
    def needs_clarification(self, command):
        """Determine if a command needs clarification"""
        command_lower = command.lower()
        
        # Commands that are likely unclear
        unclear_indicators = [
            "this", "that", "it", "something", "thing",
            "do something", "help me", "what", "how"
        ]
        
        # Very short commands might need clarification
        if len(command.split()) <= 2:
            return True
            
        # Check for unclear indicators
        for indicator in unclear_indicators:
            if indicator in command_lower:
                return True
                
        return False
    
    def format_response_for_speech(self, result):
        """Format the backend response for clear speech - FIXED VERSION"""
        try:
            # First, try to extract the main content from the response
            speech_text = ""
            
            # Check if there's a direct message or result
            if "result" in result:
                response_data = result["result"]
            elif "response" in result:
                response_data = result["response"]
            elif "message" in result:
                response_data = result["message"]
            else:
                response_data = result
            
            # Handle different response formats
            if isinstance(response_data, str):
                # If it's a string, use it directly
                speech_text = response_data
            elif isinstance(response_data, dict):
                # Extract meaningful content from dictionary
                if "content" in response_data:
                    speech_text = response_data["content"]
                elif "output" in response_data:
                    speech_text = response_data["output"]
                elif "text" in response_data:
                    speech_text = response_data["text"]
                elif "message" in response_data:
                    speech_text = response_data["message"]
                elif "status" in response_data:
                    speech_text = f"Command completed with status: {response_data['status']}"
                else:
                    # Try to find any string value in the dict
                    for key, value in response_data.items():
                        if isinstance(value, str) and len(value) > 0:
                            speech_text = value
                            break
                    if not speech_text:
                        speech_text = "Command executed successfully."
            elif isinstance(response_data, list):
                # If it's a list, try to extract meaningful content
                if len(response_data) > 0:
                    first_item = response_data[0]
                    if isinstance(first_item, str):
                        speech_text = f"Found {len(response_data)} items. {first_item}"
                    elif isinstance(first_item, dict):
                        speech_text = f"Operation completed with {len(response_data)} results."
                else:
                    speech_text = "Operation completed successfully."
            else:
                speech_text = "Command executed successfully."
            
            # Clean up the speech text
            if speech_text:
                # Remove excessive whitespace and limit length for speech
                speech_text = ' '.join(str(speech_text).split())
                if len(speech_text) > 300:
                    speech_text = speech_text[:300] + "... Check the log for full details."
            
            return speech_text if speech_text else "Command completed successfully."
            
        except Exception as e:
            self.log_message(f"❌ Error formatting speech response: {e}")
            return "Command executed. Check the log for details."
    
    def send_command_to_backend(self, command):
        """Send command to backend /file-agent endpoint - IMPROVED VERSION"""
        def send_thread():
            try:
                self.log_message(f"📤 Sending to backend: '{command}'")
                self.update_debug_info(f"📡 Sending command to backend...")
                
                payload = {
                    "prompt": command,
                    "current_dir": "."
                }
                
                response = requests.post(
                    f"{self.base_url}/file-agent", 
                    json=payload, 
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    self.log_message(f"✅ Backend response received")
                    self.update_debug_info("✅ Command executed successfully")
                    self.status_text.config(text="✅ Command executed successfully")
                    
                    # Log the full result for debugging
                    self.log_message(f"   Full response: {json.dumps(result, indent=2)}")
                    
                    # Speak the response - with better extraction
                    response_text = self.format_response_for_speech(result)
                    self.log_message(f"🔊 Speech content: {response_text}")
                    self.speak_response(response_text)
                        
                else:
                    error_msg = f"Backend error: HTTP {response.status_code}"
                    self.log_message(f"❌ {error_msg}")
                    self.update_debug_info(f"❌ {error_msg}")
                    self.status_text.config(text="❌ Backend error")
                    self.speak_response(f"Error processing command. Status code {response.status_code}")
                    
            except Exception as e:
                error_msg = f"Error sending command: {e}"
                self.log_message(f"❌ {error_msg}")
                self.update_debug_info(f"❌ Send error: {e}")
                self.status_text.config(text="❌ Error sending command")
                self.speak_response(f"Error sending command to backend. Please check the connection.")
        
        threading.Thread(target=send_thread, daemon=True).start()

def main():
    root = tk.Tk()
    app = VoiceAssistantUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()