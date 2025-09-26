import tkinter as tk
from tkinter import ttk, scrolledtext
import requests
import threading
import json
from datetime import datetime
import speech_recognition as sr
import pyaudio
import time

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
        
        self.setup_ui()
        self.setup_microphone()
        self.test_connection()
        
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
        
        # Log Frame
        log_frame = tk.Frame(self.root, bg='#2c3e50')
        log_frame.pack(pady=10, fill='both', expand=True, padx=20)
        
        tk.Label(
            log_frame,
            text="Voice Activity Log:",
            font=('Arial', 12, 'bold'),
            fg='#bdc3c7',
            bg='#2c3e50'
        ).pack(anchor='w')
        
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
            
            # Send command to backend
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
    
    def send_command_to_backend(self, command):
        """Send command to backend /file-agent endpoint"""
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
                    
                    # Log the result in a readable format
                    if "result" in result:
                        self.log_message(f"   Result: {json.dumps(result['result'], indent=2)}")
                    else:
                        self.log_message(f"   Response: {json.dumps(result, indent=2)}")
                        
                else:
                    self.log_message(f"❌ Backend error: HTTP {response.status_code}")
                    self.update_debug_info(f"❌ Backend error: {response.status_code}")
                    self.status_text.config(text="❌ Backend error")
                    
            except Exception as e:
                self.log_message(f"❌ Error sending command: {e}")
                self.update_debug_info(f"❌ Send error: {e}")
                self.status_text.config(text="❌ Error sending command")
        
        threading.Thread(target=send_thread, daemon=True).start()

def main():
    root = tk.Tk()
    app = VoiceAssistantUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()