import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import requests
import threading
import json
from datetime import datetime
import speech_recognition as sr
import pyaudio
import time
import pyttsx3
import webbrowser
import os
import platform
import psutil
import socket
import geocoder
from PIL import Image, ImageTk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class ResultWindow:
    def __init__(self, parent, title, data, data_type="json"):
        self.window = tk.Toplevel(parent)
        self.window.title(title)
        self.window.geometry("600x400")
        self.window.configure(bg='#2c3e50')
        self.window.transient(parent)
        self.window.grab_set()
        
        # Title
        title_label = tk.Label(
            self.window,
            text=title,
            font=('Arial', 14, 'bold'),
            fg='#ecf0f1',
            bg='#2c3e50'
        )
        title_label.pack(pady=10)
        
        if data_type == "json":
            self.show_json_data(data)
        elif data_type == "stats":
            self.show_device_stats(data)
        elif data_type == "location":
            self.show_location_data(data)
        elif data_type == "text":
            self.show_text_data(data)
        
    def show_json_data(self, data):
        """Display JSON data in a readable format"""
        text_widget = scrolledtext.ScrolledText(
            self.window,
            bg='#1a252f',
            fg='#ecf0f1',
            font=('Consolas', 10),
            wrap=tk.WORD
        )
        text_widget.pack(fill='both', expand=True, padx=10, pady=10)
        
        try:
            formatted_json = json.dumps(data, indent=2, ensure_ascii=False)
            text_widget.insert(tk.END, formatted_json)
        except:
            text_widget.insert(tk.END, str(data))
        
        text_widget.config(state='disabled')
        
        # Add copy button
        copy_btn = tk.Button(
            self.window,
            text="Copy to Clipboard",
            command=lambda: self.copy_to_clipboard(str(data)),
            bg='#3498db',
            fg='white'
        )
        copy_btn.pack(pady=5)
    
    def show_device_stats(self, data):
        """Display device statistics in a user-friendly way"""
        main_frame = tk.Frame(self.window, bg='#2c3e50')
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Create notebook for different stat categories
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill='both', expand=True)
        
        # System Info Tab
        system_frame = ttk.Frame(notebook)
        notebook.add(system_frame, text="System")
        
        system_text = scrolledtext.ScrolledText(
            system_frame,
            bg='#1a252f',
            fg='#ecf0f1',
            font=('Consolas', 9)
        )
        system_text.pack(fill='both', expand=True, padx=5, pady=5)
        
        system_info = f"""
System Information:
-------------------
OS: {platform.system()} {platform.release()}
Version: {platform.version()}
Architecture: {platform.architecture()[0]}
Processor: {platform.processor()}
Hostname: {socket.gethostname()}
        """
        system_text.insert(tk.END, system_info)
        system_text.config(state='disabled')
        
        # Memory Tab
        memory_frame = ttk.Frame(notebook)
        notebook.add(memory_frame, text="Memory")
        
        memory_text = scrolledtext.ScrolledText(
            memory_frame,
            bg='#1a252f',
            fg='#ecf0f1',
            font=('Consolas', 9)
        )
        memory_text.pack(fill='both', expand=True, padx=5, pady=5)
        
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        memory_info = f"""
Memory Usage:
-------------
Total: {memory.total // (1024**3)} GB
Available: {memory.available // (1024**3)} GB
Used: {memory.used // (1024**3)} GB ({memory.percent}%)
Swap: {swap.used // (1024**3)} GB / {swap.total // (1024**3)} GB ({swap.percent}%)
        """
        memory_text.insert(tk.END, memory_info)
        memory_text.config(state='disabled')
        
        # CPU Tab
        cpu_frame = ttk.Frame(notebook)
        notebook.add(cpu_frame, text="CPU")
        
        cpu_text = scrolledtext.ScrolledText(
            cpu_frame,
            bg='#1a252f',
            fg='#ecf0f1',
            font=('Consolas', 9)
        )
        cpu_text.pack(fill='both', expand=True, padx=5, pady=5)
        
        cpu_info = f"""
CPU Information:
----------------
Cores: {psutil.cpu_count()} (Physical: {psutil.cpu_count(logical=False)})
Usage: {psutil.cpu_percent(interval=1)}%
Frequency: {psutil.cpu_freq().current if psutil.cpu_freq() else 'N/A'} MHz
        """
        cpu_text.insert(tk.END, cpu_info)
        cpu_text.config(state='disabled')
        
        # Disk Tab
        disk_frame = ttk.Frame(notebook)
        notebook.add(disk_frame, text="Storage")
        
        disk_text = scrolledtext.ScrolledText(
            disk_frame,
            bg='#1a252f',
            fg='#ecf0f1',
            font=('Consolas', 9)
        )
        disk_text.pack(fill='both', expand=True, padx=5, pady=5)
        
        disk_info = "Disk Usage:\n-----------\n"
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disk_info += f"\n{partition.device} ({partition.fstype}):\n"
                disk_info += f"  Total: {usage.total // (1024**3)} GB\n"
                disk_info += f"  Used: {usage.used // (1024**3)} GB ({usage.percent}%)\n"
                disk_info += f"  Free: {usage.free // (1024**3)} GB\n"
            except:
                continue
        
        disk_text.insert(tk.END, disk_info)
        disk_text.config(state='disabled')
    
    def show_location_data(self, data):
        """Display location information"""
        main_frame = tk.Frame(self.window, bg='#2c3e50')
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        try:
            # Get location data
            g = geocoder.ip('me')
            location_info = f"""
Location Information:
---------------------
IP Address: {g.ip}
City: {g.city}
State: {g.state}
Country: {g.country}
Latitude: {g.lat}
Longitude: {g.lng}
Postal Code: {g.postal}
Timezone: {g.timezone}
            """
        except Exception as e:
            location_info = f"Could not retrieve location data: {e}"
        
        text_widget = scrolledtext.ScrolledText(
            main_frame,
            bg='#1a252f',
            fg='#ecf0f1',
            font=('Consolas', 10)
        )
        text_widget.pack(fill='both', expand=True)
        text_widget.insert(tk.END, location_info)
        text_widget.config(state='disabled')
        
        # Add map button if coordinates are available
        try:
            if g.lat and g.lng:
                map_btn = tk.Button(
                    main_frame,
                    text="Open in Maps",
                    command=lambda: webbrowser.open(f"https://maps.google.com/?q={g.lat},{g.lng}"),
                    bg='#e74c3c',
                    fg='white'
                )
                map_btn.pack(pady=5)
        except:
            pass
    
    def show_text_data(self, data):
        """Display simple text data"""
        text_widget = scrolledtext.ScrolledText(
            self.window,
            bg='#1a252f',
            fg='#ecf0f1',
            font=('Consolas', 10),
            wrap=tk.WORD
        )
        text_widget.pack(fill='both', expand=True, padx=10, pady=10)
        text_widget.insert(tk.END, str(data))
        text_widget.config(state='disabled')
    
    def copy_to_clipboard(self, text):
        """Copy text to clipboard"""
        self.window.clipboard_clear()
        self.window.clipboard_append(text)
        messagebox.showinfo("Copied", "Text copied to clipboard!")

class VoiceAssistantUI:
    def __init__(self, root):
        self.root = root
        self.root.title("JARVIS Voice Assistant - LOCAL VOICE")
        # Make the main window larger to accommodate bigger logs
        self.root.geometry("800x700")
        self.root.configure(bg='#2c3e50')
        
        self.base_url = "http://127.0.0.1:8002"
        self.is_listening = False
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.wake_words = ["jarvis", "javis", "jar"]
        self.voice_thread = None
        
        # Initialize text-to-speech engine
        self.tts_engine = pyttsx3.init()
        self.tts_engine.setProperty('rate', 150)
        self.tts_engine.setProperty('volume', 0.8)
        
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
            wraplength=760,  # Increased for larger window
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
        
        # Quick Actions Frame
        actions_frame = tk.Frame(self.root, bg='#2c3e50')
        actions_frame.pack(pady=5, fill='x', padx=20)
        
        tk.Label(
            actions_frame,
            text="Quick Actions:",
            font=('Arial', 10, 'bold'),
            fg='#bdc3c7',
            bg='#2c3e50'
        ).pack(anchor='w')
        
        actions_buttons_frame = tk.Frame(actions_frame, bg='#2c3e50')
        actions_buttons_frame.pack(fill='x', pady=5)
        
        # Quick action buttons for common queries
        quick_actions = [
            ("Device Stats", self.show_device_stats),
            ("Location Info", self.show_location_info),
            ("System Info", self.show_system_info),
            ("Network Info", self.show_network_info)
        ]
        
        for text, command in quick_actions:
            btn = tk.Button(
                actions_buttons_frame,
                text=text,
                command=command,
                bg='#8e44ad',
                fg='white',
                font=('Arial', 9),
                width=15
            )
            btn.pack(side='left', padx=2)
        
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
            wraplength=760,  # Increased for larger window
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
        
        # Log Frame - Made larger
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
        
        # Increased the height of the log text area
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            height=20,  # Increased from 15 to 20
            bg='#1a252f',
            fg='#ecf0f1',
            font=('Consolas', 9),
            wrap=tk.WORD
        )
        self.log_text.pack(fill='both', expand=True)
        self.log_text.config(state='disabled')
    
    def show_device_stats(self):
        """Show device statistics in a separate window"""
        try:
            stats_data = self.get_device_stats()
            ResultWindow(self.root, "Device Statistics", stats_data, "stats")
            self.speak_response("Showing device statistics")
        except Exception as e:
            self.log_message(f"❌ Error showing device stats: {e}")
    
    def show_location_info(self):
        """Show location information in a separate window"""
        try:
            location_data = self.get_location_info()
            ResultWindow(self.root, "Location Information", location_data, "location")
            self.speak_response("Showing location information")
        except Exception as e:
            self.log_message(f"❌ Error showing location info: {e}")
    
    def show_system_info(self):
        """Show system information"""
        try:
            system_data = self.get_system_info()
            ResultWindow(self.root, "System Information", system_data, "text")
            self.speak_response("Showing system information")
        except Exception as e:
            self.log_message(f"❌ Error showing system info: {e}")
    
    def show_network_info(self):
        """Show network information"""
        try:
            network_data = self.get_network_info()
            ResultWindow(self.root, "Network Information", network_data, "text")
            self.speak_response("Showing network information")
        except Exception as e:
            self.log_message(f"❌ Error showing network info: {e}")
    
    def get_device_stats(self):
        """Get comprehensive device statistics"""
        return {
            "system": platform.uname()._asdict(),
            "memory": dict(psutil.virtual_memory()._asdict()),
            "cpu": {
                "cores": psutil.cpu_count(),
                "usage": psutil.cpu_percent(interval=1),
                "frequency": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None
            },
            "disk": [dict(psutil.disk_usage(part.mountpoint)._asdict()) for part in psutil.disk_partitions()]
        }
    
    def get_location_info(self):
        """Get location information"""
        g = geocoder.ip('me')
        return g.json if g else {"error": "Could not retrieve location"}
    
    def get_system_info(self):
        """Get system information"""
        return f"""
System Information:
-------------------
OS: {platform.system()} {platform.release()}
Version: {platform.version()}
Architecture: {platform.architecture()[0]}
Processor: {platform.processor()}
Hostname: {socket.gethostname()}
Boot Time: {datetime.fromtimestamp(psutil.boot_time()).strftime('%Y-%m-%d %H:%M:%S')}
        """
    
    def get_network_info(self):
        """Get network information"""
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        
        network_info = f"""
Network Information:
--------------------
Hostname: {hostname}
Local IP: {local_ip}
        """
        
        # Add network interfaces
        try:
            interfaces = psutil.net_if_addrs()
            network_info += "\nNetwork Interfaces:\n"
            for interface, addrs in interfaces.items():
                network_info += f"\n{interface}:\n"
                for addr in addrs:
                    network_info += f"  {addr.family.name}: {addr.address}\n"
        except:
            pass
        
        return network_info
    
    def speak_response(self, text):
        """Speak the response using text-to-speech - FIXED VERSION"""
        if self.tts_enabled.get() and text:
            def speak_thread():
                try:
                    # Stop any ongoing speech first
                    self.tts_engine.stop()
                    # Then speak the new text
                    self.tts_engine.say(text)
                    self.tts_engine.runAndWait()
                except Exception as e:
                    self.log_message(f"❌ TTS Error: {e}")
            
            # Start speech in a new thread
            speech_thread = threading.Thread(target=speak_thread, daemon=True)
            speech_thread.start()
    
    def test_tts(self):
        """Test the text-to-speech functionality"""
        test_text = "Hello, I am JARVIS. Voice responses are working correctly."
        self.speak_response(test_text)
        self.log_message("🔊 Testing text-to-speech: 'Hello, I am JARVIS'")
    
    def setup_microphone(self):
        """Initialize microphone"""
        try:
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
        """Main voice recognition loop"""
        self.log_message("🎧 Voice recognition loop started")
        
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
            
            while self.is_listening:
                try:
                    self.update_debug_info("👂 Listening for wake word...")
                    self.status_text.config(text="👂 Listening... Say 'JARVIS'")
                    
                    audio = self.recognizer.listen(source, timeout=2, phrase_time_limit=3)
                    text = self.recognizer.recognize_google(audio).lower()
                    
                    self.log_message(f"🎙️ Heard: '{text}'")
                    self.update_debug_info(f"Heard: '{text}'")
                    
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
                        self.listen_for_command(source)
                        
                except sr.WaitTimeoutError:
                    continue
                except sr.UnknownValueError:
                    continue
                except sr.RequestError as e:
                    self.log_message(f"❌ Speech recognition API error: {e}")
                    time.sleep(2)
                except Exception as e:
                    self.log_message(f"❌ Voice recognition error: {e}")
                    time.sleep(1)
    
    def listen_for_command(self, source):
        """Listen for command after wake word"""
        try:
            self.status_text.config(text="🎯 Listening for command... Speak now!")
            self.update_debug_info("🎤 Listening for command...")
            
            audio = self.recognizer.listen(source, timeout=6, phrase_time_limit=6)
            command = self.recognizer.recognize_google(audio)
            
            self.log_message(f"🎯 Command received: '{command}'")
            self.update_debug_info(f"✅ Command: '{command}'")
            self.status_text.config(text=f"📡 Sending command to backend: {command}")
            
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
    
    def format_response_for_speech(self, result):
        """Format the backend response for clear speech"""
        try:
            speech_text = ""
            
            if "result" in result:
                response_data = result["result"]
            elif "response" in result:
                response_data = result["response"]
            elif "message" in result:
                response_data = result["message"]
            else:
                response_data = result
            
            if isinstance(response_data, str):
                speech_text = response_data
            elif isinstance(response_data, dict):
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
                    for key, value in response_data.items():
                        if isinstance(value, str) and len(value) > 0:
                            speech_text = value
                            break
                    if not speech_text:
                        speech_text = "Command executed successfully."
            elif isinstance(response_data, list):
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
            
            if speech_text:
                speech_text = ' '.join(str(speech_text).split())
                if len(speech_text) > 300:
                    speech_text = speech_text[:300] + "... Check the log for full details."
            
            return speech_text if speech_text else "Command completed successfully."
            
        except Exception as e:
            self.log_message(f"❌ Error formatting speech response: {e}")
            return "Command executed. Check the log for details."
    
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
                    
                    # Log the full result
                    self.log_message(f"   Full response: {json.dumps(result, indent=2)}")
                    
                    # Open result in separate window only for specific queries (not for app launches)
                    self.handle_backend_response(command, result)
                    
                    # Speak the response - ALWAYS speak the response
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
    
    def handle_backend_response(self, command, result):
        """Handle backend response and open appropriate windows - FIXED VERSION"""
        command_lower = command.lower()
        
        # List of commands that should NOT open dialog windows
        app_launch_commands = [
            'open', 'launch', 'start', 'run', 'execute',
            'notepad', 'calculator', 'browser', 'chrome', 'firefox', 'edge',
            'surf', 'browse', 'search', 'google', 'youtube', 'website'
        ]
        
        # Check if this is an application launch command
        is_app_launch = any(word in command_lower for word in app_launch_commands)
        
        # Only open dialog windows for information queries, not app launches
        if not is_app_launch:
            # Check if result contains complex data that should be shown in a window
            if isinstance(result, (dict, list)) and len(str(result)) > 200:
                # Open JSON data in separate window
                ResultWindow(self.root, f"Result: {command}", result, "json")
            
            # Specific command handlers for information queries only
            if any(word in command_lower for word in ['stat', 'info', 'detail', 'show', 'display', 'get']):
                if any(word in command_lower for word in ['device', 'system', 'computer', 'hardware']):
                    ResultWindow(self.root, "Device Statistics", self.get_device_stats(), "stats")
                elif any(word in command_lower for word in ['location', 'where', 'ip', 'address']):
                    ResultWindow(self.root, "Location Information", self.get_location_info(), "location")
                elif any(word in command_lower for word in ['network', 'connection', 'wifi', 'ethernet']):
                    ResultWindow(self.root, "Network Information", self.get_network_info(), "text")

def main():
    root = tk.Tk()
    app = VoiceAssistantUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()