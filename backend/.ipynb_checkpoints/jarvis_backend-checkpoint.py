# models
# Model	RPM	TPM	RPD
# Gemini 2.5 Pro	     5	   250,000	 100
# Gemini 2.5 Flash	    10	   250,000	 250
# Gemini 2.5 Flash-Lite	15	   250,000	1000
# Gemini 2.0 Flash	    15	1,000,000	 200
# Gemini 2.0 Flash-Lite	30	1,000,000	 200

import google.generativeai as genai
import os
import shutil
import json
import pathlib
import sys
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
import subprocess
import threading
import time
from difflib import SequenceMatcher
import speech_recognition as sr
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import re
import pyttsx3

API_KEY = ''
with open('../../GPT_SECRET_KEY.json', 'r') as file_to_read:
    json_data = json.load(file_to_read)
    API_KEY = json_data["API_KEY"]
os.environ["API_KEY"] = API_KEY

model_name = "gemini-2.5-flash-lite"

try:
    genai.configure(api_key=str(os.environ["API_KEY"]))
except AttributeError:
    print("Error: Please set your 'GEMINI_API_KEY' as an environment variable.")
    sys.exit(1)

class ConversationMemory:
    def __init__(self, max_history=10):
        self.history = []
        self.max_history = max_history
        self.search_results_cache = {}  # Cache for search results
        self.file_semantic_cache = {}   # Cache for file semantic analysis
    
    def add_interaction(self, user_input, agent_response, command_result):
        """Add a conversation turn to memory"""
        interaction = {
            "user_input": user_input,
            "agent_response": agent_response,
            "command_result": command_result,
            "timestamp": time.time()
        }
        self.history.append(interaction)
        
        # Keep only recent history
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
    
    def get_context(self):
        """Get recent conversation context"""
        if not self.history:
            return "No previous conversation."
        
        context = "Previous conversation:\n"
        for i, interaction in enumerate(self.history[-3:]):  # Last 3 interactions
            context += f"User: {interaction['user_input']}\n"
            context += f"Agent: {interaction['agent_response']}\n"
            if 'error' in interaction['command_result']:
                context += f"Result: Error - {interaction['command_result']['error']}\n"
            context += "---\n"
        return context
    
    def cache_search_results(self, search_path, keyword, results):
        """Cache search results for semantic matching"""
        key = f"{search_path}:{keyword.lower()}"
        self.search_results_cache[key] = {
            'results': results,
            'timestamp': time.time(),
            'files': self._extract_file_info(results)
        }
    
    def _extract_file_info(self, results):
        """Extract file information for semantic matching"""
        files = []
        if 'results' in results:
            for file_path in results['results'].get('files', []):
                filename = os.path.basename(file_path)
                name_without_ext = os.path.splitext(filename)[0]
                files.append({
                    'path': file_path,
                    'name': filename,
                    'name_without_ext': name_without_ext,
                    'folder': os.path.dirname(file_path)
                })
        return files
    
    def find_semantic_match(self, search_path, user_query, threshold=0.3):
        """Find semantically similar files using cached results"""
        best_match = None
        best_score = 0
        
        # Extract key terms from user query
        query_terms = re.findall(r'\w+', user_query.lower())
        
        for cache_key, cache_data in self.search_results_cache.items():
            if search_path in cache_key:
                for file_info in cache_data.get('files', []):
                    # Compare with filename without extension
                    filename_terms = re.findall(r'\w+', file_info['name_without_ext'].lower())
                    
                    # Calculate similarity using multiple methods
                    similarity = self._calculate_similarity(query_terms, filename_terms)
                    
                    if similarity > best_score and similarity > threshold:
                        best_score = similarity
                        best_match = file_info
        
        return best_match, best_score
    
    def _calculate_similarity(self, query_terms, filename_terms):
        """Calculate similarity between query and filename terms"""
        if not query_terms or not filename_terms:
            return 0
        
        # Method 1: Exact term matching
        exact_matches = len(set(query_terms) & set(filename_terms))
        exact_score = exact_matches / len(query_terms)
        
        # Method 2: Partial term matching
        partial_score = 0
        for q_term in query_terms:
            for f_term in filename_terms:
                if q_term in f_term or f_term in q_term:
                    partial_score += 0.5
        partial_score = min(partial_score / len(query_terms), 1.0)
        
        # Method 3: Sequence matching for the whole string
        query_str = ' '.join(query_terms)
        filename_str = ' '.join(filename_terms)
        sequence_score = SequenceMatcher(None, query_str, filename_str).ratio()
        
        # Weighted combination
        final_score = (exact_score * 0.4) + (partial_score * 0.3) + (sequence_score * 0.3)
        return final_score

class EnhancedFileAgent:
    def __init__(self, system_prompt):
        self.system_prompt = system_prompt
        self.model = genai.GenerativeModel(model_name)
        self.conversation = self.model.start_chat(history=[
            {"role": "user", "parts": [self.system_prompt]},
            {"role": "model", "parts": ["Understood. I am FileWise. Ready to assist."]}
        ])
        self.memory = ConversationMemory()
        self.pending_command = None

        # Common Windows applications mapping
        self.windows_apps = {
            "notepad": "notepad.exe",
            "notepad++": "notepad++.exe",
            "word": "winword.exe",
            "excel": "excel.exe",
            "powerpoint": "powerpnt.exe",
            "outlook": "outlook.exe",
            "calculator": "calc.exe",
            "paint": "mspaint.exe",
            "cmd": "cmd.exe",
            "powershell": "powershell.exe",
            "chrome": "chrome.exe",
            "firefox": "firefox.exe",
            "edge": "msedge.exe",
            "explorer": "explorer.exe",
            "task manager": "taskmgr.exe",
            "control panel": "control.exe",
            "calendar": "outlook.exe /select outlook:calendar",
            "vlc": "vlc.exe",
            "media player": "wmplayer.exe",
            "photos": "ms-photos:",
            "camera": "microsoft.windows.camera:",
            "settings": "ms-settings:",
            "store": "ms-windows-store:"
        }

    def _summarize_action(self, command: dict, result: dict) -> str:
        cmd = command.get("command", "")
        params = command.get("parameters", {})
        if "error" in result:
            return f"❌ Failed to {cmd} with {params}. Reason: {result['error']}"
        return f"✅ {cmd} executed with {params}"

    # -------------------- Enhanced Search with Semantic Matching --------------------
    
    def _search_item(self, **kwargs):
        keyword = kwargs.get("keyword", "")
        search_path = os.path.abspath(kwargs.get("search_path", "."))
        search_type = kwargs.get("search_type", "both")
        use_semantic = kwargs.get("use_semantic", False)
        semantic_threshold = kwargs.get("semantic_threshold", 0.3)
        
        results = {"files": [], "folders": [], "semantic_matches": []}
        
        try:
            if not os.path.exists(search_path):
                return {"error": f"Search path does not exist: {search_path}"}
            
            # First, try exact search
            for root, dirs, files in os.walk(search_path):
                if search_type in ["both", "folder"]:
                    for d in dirs:
                        if keyword.lower() in d.lower():
                            results["folders"].append(os.path.join(root, d))
                
                if search_type in ["both", "file"]:
                    for f in files:
                        if keyword.lower() in f.lower():
                            results["files"].append(os.path.join(root, f))
            
            # If no exact matches found and semantic search is enabled
            if use_semantic and not results["files"] and not results["folders"]:
                semantic_match, similarity_score = self.memory.find_semantic_match(
                    search_path, keyword, semantic_threshold
                )
                
                if semantic_match:
                    results["semantic_matches"].append({
                        "path": semantic_match['path'],
                        "name": semantic_match['name'],
                        "similarity_score": round(similarity_score, 2),
                        "type": "semantic"
                    })
            
            # Cache the results for future semantic matching
            self.memory.cache_search_results(search_path, keyword, results)
            
            # Auto-open if single result found
            if len(results["files"]) == 1 and not results["folders"] and not results["semantic_matches"]:
                self._open_file(results["files"][0])
            elif len(results["folders"]) == 1 and not results["files"] and not results["semantic_matches"]:
                self._open_folder(results["folders"][0])
            elif len(results["semantic_matches"]) == 1 and not results["files"] and not results["folders"]:
                best_match = results["semantic_matches"][0]
                return {
                    "results": results,
                    "keyword": keyword,
                    "search_path": search_path,
                    "total_found": 1,
                    "semantic_suggestion": f"Found similar file: {best_match['name']} (similarity: {best_match['similarity_score']})",
                    "suggested_path": best_match["path"]
                }
            
            return {
                "results": results, 
                "keyword": keyword,
                "search_path": search_path,
                "total_found": len(results["files"]) + len(results["folders"]) + len(results["semantic_matches"])
            }
            
        except Exception as e:
            return {"error": f"Search failed: {str(e)}"}

    # Keep all your existing methods (_list_directory, _open_application, etc.)
    # ... [All your existing methods remain the same] ...
    
    def _list_directory(self, path="."):
        try:
            items = os.listdir(path)
            return {"directory": os.path.abspath(path), "contents": items}
        except FileNotFoundError:
            return {"error": f"Directory not found at '{path}'"}
        except Exception as e:
            return {"error": str(e)}

    def _open_application(self, application):
        try:
            app_name_lower = application.lower().strip()
            if app_name_lower in self.windows_apps:
                app_command = self.windows_apps[app_name_lower]
                if app_command.startswith(("ms-", "microsoft.")):
                    subprocess.Popen(f"start {app_command}", shell=True)
                else:
                    subprocess.Popen(app_command, shell=True)
                return {"message": f"Opened {application}"}
            subprocess.Popen(f"start {application}", shell=True)
            return {"message": f"Attempted to open {application}"}
        except Exception as e:
            return {"error": str(e)}

    def _read_file(self, path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            return {"path": os.path.abspath(path), "content": content}
        except FileNotFoundError:
            return {"error": f"File not found at '{path}'"}
        except Exception as e:
            return {"error": str(e)}

    def _open_file(self, path, application=None):
        try:
            abs_path = os.path.abspath(path)
            if not os.path.exists(abs_path):
                return {"error": f"File not found at '{abs_path}'"}
            if application:
                app_lower = application.lower()
                if app_lower in self.windows_apps:
                    application = self.windows_apps[app_lower]
                os.system(f'start "" "{application}" "{abs_path}"')
            else:
                os.startfile(abs_path)
            return {"message": f"Opened file '{abs_path}'"}
        except Exception as e:
            return {"error": str(e)}

    def _open_folder(self, path):
        try:
            abs_path = os.path.abspath(path)
            if not os.path.isdir(abs_path):
                return {"error": f"Folder not found: '{abs_path}'"}
            os.startfile(abs_path)
            return {"message": f"Opened folder '{abs_path}'"}
        except Exception as e:
            return {"error": str(e)}

    def _execute_code(self, path=None, language=None, **kwargs):
        if not path and "file_path" in kwargs:
            path = kwargs["file_path"]
        try:
            abs_path = os.path.abspath(path)
            if not os.path.exists(abs_path):
                return {"error": f"File not found at '{abs_path}'"}
            ext = os.path.splitext(abs_path)[1].lower()
    
            if ext == ".py":
                subprocess.Popen(f'start cmd /K python "{abs_path}"', shell=True)
            elif ext in [".bat", ".cmd"]:
                subprocess.Popen(f'start cmd /K "{abs_path}"', shell=True)
            elif ext == ".ps1":
                subprocess.Popen(f'start powershell -NoExit -File "{abs_path}"', shell=True)
            elif ext == ".js":
                subprocess.Popen(f'start cmd /K node "{abs_path}"', shell=True)
            elif ext == ".sh":
                subprocess.Popen(f'start cmd /K wsl bash "{abs_path}"', shell=True)
            elif ext == ".exe":
                subprocess.Popen(f'start "" "{abs_path}"', shell=True)
            elif ext == ".html":
                os.system(f'start "" "{abs_path}"')
            else:
                return {"error": f"Unsupported file type: {ext}"}
    
            return {"message": f"Executed '{abs_path}' in new terminal (terminal remains open)"}
        except Exception as e:
            return {"error": str(e)}

    def _create_file(self, path, content="", open_after=False):
        try:
            abs_path = os.path.abspath(path)
            with open(abs_path, "w", encoding="utf-8") as f:
                f.write(content)
            if open_after:
                os.startfile(abs_path)
            return {"message": f"Created file '{abs_path}'"}
        except Exception as e:
            return {"error": str(e)}

    def _write_file(self, path, content="", open_after=False):
        try:
            abs_path = os.path.abspath(path)
            with open(abs_path, "w", encoding="utf-8") as f:
                f.write(content)
            if open_after:
                os.startfile(abs_path)
            return {"message": f"Wrote to '{abs_path}'"}
        except Exception as e:
            return {"error": str(e)}

    def _move_item(self, source, destination):
        try:
            shutil.move(source, destination)
            return {"message": f"Successfully moved '{os.path.abspath(source)}' to '{os.path.abspath(destination)}'"}
        except FileNotFoundError:
            return {"error": f"Source '{source}' not found."}
        except Exception as e:
            return {"error": str(e)}

    def _copy_item(self, source, destination):
        try:
            abs_source = os.path.abspath(source)
            abs_destination = os.path.abspath(destination)
    
            if not os.path.exists(abs_source):
                return {"error": f"Source '{abs_source}' not found."}
    
            if os.path.isdir(abs_source):
                if os.path.exists(abs_destination):
                    return {"error": f"Destination '{abs_destination}' already exists."}
                shutil.copytree(abs_source, abs_destination)
            else:
                os.makedirs(os.path.dirname(abs_destination), exist_ok=True)
                shutil.copy2(abs_source, abs_destination)
    
            return {
                "message": f"Successfully copied '{abs_source}' to '{abs_destination}'"
            }
        except Exception as e:
            return {"error": str(e)}

    def _delete_file(self, path):
        try:
            os.remove(path)
            return {"message": f"Successfully deleted file: '{os.path.abspath(path)}'"}
        except FileNotFoundError:
            return {"error": f"File not found at '{path}'"}
        except Exception as e:
            return {"error": str(e)}

    def _create_directory(self, path, exist_ok=True):
        try:
            abs_path = os.path.abspath(path)
            os.makedirs(abs_path, exist_ok=exist_ok)
            return {"message": f"Directory created at '{abs_path}'"}
        except Exception as e:
            return {"error": str(e)}

    def _delete_directory(self, path):
        try:
            shutil.rmtree(path)
            return {"message": f"Successfully deleted directory and its contents: '{os.path.abspath(path)}'"}
        except FileNotFoundError:
            return {"error": f"Directory not found at '{path}'"}
        except Exception as e:
            return {"error": str(e)}
    
    def _clarify(self, question):
        return {"clarify": question}

    def _respond(self, message):
        return {"response": message}

    def _execute_command(self, response_json):
        try:
            if "workflow" in response_json:
                workflow_results = []
                for step in response_json["workflow"]:
                    result = self._execute_single_command(step)
                    workflow_results.append({
                        "command": step,
                        "result": result,
                        "summary": self._summarize_action(step, result)
                    })
                return {"workflow": workflow_results}
            else:
                return self._execute_single_command(response_json)
        except Exception as e:
            return {"error": f"Execution error: {str(e)}"}

    def _execute_single_command(self, command_json):
        command = command_json.get("command")
        params = command_json.get("parameters", {})
    
        if "file_path" in params and "path" not in params:
            params["path"] = params.pop("file_path")
        if "folder_path" in params and "path" not in params:
            params["path"] = params.pop("folder_path")
    
        if command == "execute_file":
            command = "execute_code"
        
        command_map = {
            "create_file": self._create_file,
            "write_file": self._write_file,
            "open_file": self._open_file,
            "open_folder": self._open_folder,
            "execute_code": self._execute_code,
            "execute_file": self._execute_code,
            "search_item": self._search_item,
            "open_application": self._open_application,
            "list_directory": self._list_directory,
            "read_file": self._read_file,
            "move_item": self._move_item,
            "delete_file": self._delete_file,
            "delete_directory": self._delete_directory,
            "clarify": self._clarify,
            "respond": self._respond,
            "copy_item": self._copy_item,
            "create_directory": self._create_directory
        }
        if command in command_map:
            return command_map[command](**params)
        return {"error": f"Unknown command '{command}'"}

    def process_request(self, user_prompt, current_dir="."):
        # Add conversation context to the prompt
        conversation_context = self.memory.get_context()
        full_prompt = f"{conversation_context}\n\nCurrent Directory: '{current_dir}'\nUser: '{user_prompt}'"
        
        try:
            response = self.conversation.send_message(full_prompt)
            clean = response.text.strip().replace("```json", "").replace("```", "").strip()
            response_json = json.loads(clean)
            result = self._execute_command(response_json)
            
            # Store in memory
            self.memory.add_interaction(user_prompt, response_json, result)
            
            return {"agent_command": response_json, "result": result}
        except json.JSONDecodeError:
            return {"error": "Invalid JSON from model", "raw": response.text}
        except Exception as e:
            return {"error": str(e)}

# Enhanced Voice Recognition System
class AdvancedVoiceRecognition:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.is_listening = False
        self.current_status = "Ready"
        self.last_command = ""
        self.last_error = ""
        self.wake_words = ["jarvis", "javis", "jar", "hey jarvis", "okay jarvis"]
        self.conversation_mode = False
        self.continuous_listening = False
        
    def setup_microphone(self):
        """Enhanced microphone setup with better error handling"""
        try:
            with self.microphone as source:
                print("🔊 Calibrating microphone for ambient noise...")
                self.recognizer.adjust_for_ambient_noise(source, duration=2)
                print("✅ Microphone calibration complete")
            return True
        except Exception as e:
            error_msg = f"❌ Microphone setup failed: {e}"
            print(error_msg)
            self.last_error = error_msg
            return False
    
    def listen_for_wake_word_continuous(self):
        """Continuous wake word detection with improved accuracy"""
        self.current_status = "🎯 Listening for wake words..."
        print(self.current_status)
        
        with self.microphone as source:
            while self.is_listening:
                try:
                    # Listen with better parameters
                    audio = self.recognizer.listen(source, timeout=3, phrase_time_limit=4)
                    text = self.recognizer.recognize_google(audio).lower()
                    print(f"🎙️ Heard: '{text}'")
                    
                    # Flexible wake word detection
                    detected = False
                    for wake_word in self.wake_words:
                        if wake_word in text:
                            self.current_status = f"🔔 Wake word '{wake_word}' detected!"
                            print(self.current_status)
                            self.handle_command_mode()
                            detected = True
                            break
                    
                    if not detected:
                        print("❌ No wake word detected")
                        
                except sr.WaitTimeoutError:
                    continue
                except sr.UnknownValueError:
                    print("🔇 Could not understand audio")
                    continue
                except sr.RequestError as e:
                    error_msg = f"🌐 Speech recognition error: {e}"
                    print(error_msg)
                    self.last_error = error_msg
                    time.sleep(2)
                except Exception as e:
                    error_msg = f"💥 Unexpected error: {e}"
                    print(error_msg)
                    self.last_error = error_msg
                    time.sleep(1)
    
    def handle_command_mode(self):
        """Handle command listening with conversation support"""
        self.current_status = "💬 Listening for command..."
        print(self.current_status)
        
        with self.microphone as source:
            try:
                # Extended listening time for commands
                audio = self.recognizer.listen(source, timeout=8, phrase_time_limit=10)
                command = self.recognizer.recognize_google(audio)
                self.last_command = command
                
                print(f"✅ Command received: '{command}'")
                
                # Process command through FileAgent
                # This would integrate with your main agent
                self.process_voice_command(command)
                
            except sr.UnknownValueError:
                error_msg = "❌ Sorry, I couldn't understand your command"
                print(error_msg)
                self.last_error = error_msg
                self.speak_response("Sorry, I couldn't understand that. Please try again.")
            except sr.WaitTimeoutError:
                error_msg = "⏰ No command detected within time limit"
                print(error_msg)
                self.last_error = error_msg
            except Exception as e:
                error_msg = f"💥 Error processing command: {e}"
                print(error_msg)
                self.last_error = error_msg
    
    def process_voice_command(self, command):
        """Process voice command and provide audio feedback"""
        # Integrate with your FileAgent here
        try:
            # Simulate processing - replace with actual agent call
            result = f"Processed command: {command}"
            self.current_status = f"✅ Command processed: {command}"
            
            # Convert result to speech
            self.speak_response(f"I've executed your command: {command}")
            
        except Exception as e:
            error_msg = f"Error processing command: {e}"
            self.speak_response("Sorry, there was an error processing your command.")

    

    def setup_tts(self):
        self.tts_engine = pyttsx3.init()
        # Configure voice properties
        voices = self.tts_engine.getProperty('voices')
        self.tts_engine.setProperty('voice', voices[1].id)  # Female voice
        self.tts_engine.setProperty('rate', 150)  # Speech rate
    
    def speak_response(self, text):
        """Convert text to speech (placeholder - implement with actual TTS)"""
        print(f"🗣️ Speaking: {text}")
        # Implement with pyttsx3 or other TTS library
        import pyttsx3
        engine = pyttsx3.init()
        engine.say(text)
        engine.runAndWait()
    
    def start_continuous_listening(self):
        """Start continuous voice recognition"""
        if self.is_listening:
            return {"success": False, "message": "Already listening"}
        
        if not self.setup_microphone():
            return {"success": False, "message": "Microphone setup failed"}
        
        self.is_listening = True
        threading.Thread(target=self.listen_for_wake_word_continuous, daemon=True).start()
        
        return {"success": True, "message": "Continuous voice recognition started"}
    
    def stop_listening(self):
        """Stop voice recognition"""
        self.is_listening = False
        self.current_status = "🛑 Voice recognition stopped"
        return {"success": True, "message": "Voice recognition stopped"}

# FastAPI Setup
app = FastAPI(title="FileWise AI Agent with Voice Recognition")

# Add CORS middleware
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Enhanced system prompt with conversation awareness
ENHANCED_SYSTEM_PROMPT = r"""You are "FileWise", an advanced AI assistant with conversational memory and semantic search capabilities.

CONVERSATION AWARENESS:
- Remember previous interactions and build upon them
- If a search returns no results, suggest similar files based on semantic matching
- Maintain context across multiple requests

SEMANTIC SEARCH FEATURES:
- When exact matches aren't found, suggest similar files
- Understand user intent even with imperfect filename matches
- Learn from previous search patterns

VOICE INTERACTION:
- Responses should be concise for voice feedback
- Provide clear, actionable results

🚨 STRICT OUTPUT RULES 🚨  
Always use **consistent parameter names** across all commands. Do not invent synonyms.  
- For files and folders → always use "path"  
- For move/copy/cut → always use "source" and "destination"  
- For search → always use "keyword", "search_path", "search_type"  
- For applications → always use "application"  

Example (GOOD ✅):
{
  "command": "open_file",
  "parameters": {"path": "C:\\Users\\me\\report.pdf"}
}

Example (BAD ❌):
{
  "command": "open_file",
  "parameters": {"file_path": "C:\\Users\\me\\report.pdf"}
}


Core Directives
Persona: Be careful, reliable, and user-centric. Always ensure actions are safe and clarify when destructive changes may occur.

Environment: Operate on a Windows machine, always using Windows-style file paths (e.g., C:\Users\Username\Documents).

Default Context: A Current Working Directory (CWD) may be provided. Use this as the default location unless the user specifies a full path.

Chained Operations: If a user requests multiple actions in a single command (e.g., "search for report.pdf, copy it to Documents, then open it"), you must generate a workflow chain.

Enhanced Search: When searching for items, search for BOTH files and folders unless specifically requested otherwise. Use the 'search_item' command instead of 'search_file'.

Application Opening: You can now open Windows applications using the 'open_application' command. Common applications include: notepad, excel, word, powerpoint, calculator, paint, chrome, firefox, etc.

Response Format
Always translate user input into JSON only.

Single Action Examples:
{
  "command": "open_file",
  "parameters": {"path": "C:\\Users\\me\\report.pdf"}
}

{
  "command": "open_application",
  "parameters": {"application": "excel"}
}

Multiple Actions (Workflow) Example:
{
  "workflow": [
    {
      "command": "search_item",
      "parameters": {"keyword": "report.pdf", "search_path": "C:\\", "search_type": "both"}
    },
    {
      "command": "copy_item",
      "parameters": {
        "source": "C:\\Found\\report.pdf",
        "destination": "C:\\Users\\me\\Documents"
      }
    },
    {
      "command": "open_application",
      "parameters": {"application": "excel"}
    },
    {
      "command": "open_file",
      "parameters": {"path": "C:\\Users\\me\\Documents\\report.pdf", "application": "excel"}
    }
  ]
}

Supported Commands [FOLLOW THEM STRICTLY]:
- List directory → list_directory
- Create directory → create_directory
- Create file → create_file
- Read file → read_file
- Write file → write_file
- Open file → open_file
- Open folder → open_folder
- Move item → move_item
- Copy item → copy_item
- Cut item → cut_item
- Delete file → delete_file
- Delete directory → delete_directory
- Search files AND folders → search_item (use this instead of search_file)
- Execute code → execute_code
- Open Windows application → open_application

IMPORTANT SEARCH COMMAND UPDATE:
- Use "search_item" NOT "search_file"
- Parameters: "keyword" (not "filename"), "search_path", "search_type" ("file", "folder", or "both")
- Example: {"command": "search_item", "parameters": {"keyword": "project", "search_path": "C:\\", "search_type": "both"}}

CODE EXECUTION UPDATE:
- When executing code files (.py, .bat, .js), the terminal will remain open after execution
- This allows you to see the output and any error messages

APPLICATION OPENING:
- Use "open_application" command for opening Windows apps
- Supported apps: notepad, excel, word, powerpoint, calculator, paint, chrome, firefox, edge, cmd, powershell, etc.
- You can also specify custom applications by name

KEYWORD EXTRACTION RULES:

CRITICAL: Extract the ACTUAL SEARCH KEYWORD from user requests, not the entire phrase.

1. REMOVE ACTION WORDS:
   - Remove words like: "open", "find", "search", "look for", "locate", "get"
   - Remove file type words unless they are part of the actual filename: "photo", "image", "file", "document", "video", "folder"

2. EXTRACT THE CORE FILENAME/PATH:
   - "open ironman photo from f drive" → keyword: "ironman"
   - "find my resume document" → keyword: "resume"
   - "search for project report pdf" → keyword: "project report"
   - "locate vacation pictures folder" → keyword: "vacation pictures"

3. PRESERVE ACTUAL FILENAME COMPONENTS:
   - If the user specifies a clear filename, use it as-is: "annual report.pdf" → "annual report.pdf"
   - If it's a descriptive request, extract the main identifier: "my thesis document" → "thesis"

EXAMPLES:

"open ironman photo from f drive"
{
  "workflow": [
    {
      "command": "search_item",
      "parameters": {"keyword": "ironman", "search_path": "F:\\", "search_type": "both"}
    },
    {
      "command": "open_file",
      "parameters": {"path": "[SEARCH_RESULT_PATH]"}
    }
  ]
}

"find my resume document in downloads"
{
  "workflow": [
    {
      "command": "search_item",
      "parameters": {"keyword": "resume", "search_path": "C:\\Users\\[Username]\\Downloads", "search_type": "both"}
    },
    {
      "command": "open_file",
      "parameters": {"path": "[SEARCH_RESULT_PATH]"}
    }
  ]
}

"search for project report pdf file"
{
  "workflow": [
    {
      "command": "search_item",
      "parameters": {"keyword": "project report", "search_path": "C:\\", "search_type": "both"}
    },
    {
      "command": "open_file",
      "parameters": {"path": "[SEARCH_RESULT_PATH]"}
    }
  ]
}

"locate vacation pictures folder"
{
  "workflow": [
    {
      "command": "search_item",
      "parameters": {"keyword": "vacation pictures", "search_path": "C:\\", "search_type": "folder"}
    },
    {
      "command": "open_folder",
      "parameters": {"path": "[SEARCH_RESULT_PATH]"}
    }
  ]
}

SEARCH STRATEGY GUIDE:

1. KEYWORD EXTRACTION:
   - Extract the core filename/foldername from the request
   - Remove action words and generic file type descriptors

2. FILE TYPE SEARCHES (only when explicitly requested):
   - Only use file extension searches when user specifically asks for file types: "all image files", "PDF documents"
   - Examples: "image files", "video files", "PDF documents", "all MP3 files"

3. SEARCH AND OPEN COMBINATIONS:
   - Always use workflows for search-and-open requests
   - Search first, then open the result

Workflow Building:
- Preserve command order as implied in user's request
- Extract the actual search keyword by removing action words and generic descriptors
- Use "[SEARCH_RESULT_PATH]" as placeholder in open commands

CRITICAL: 
- EXTRACT THE ACTUAL KEYWORD, not the entire phrase
- Remove words like "open", "photo", "file", "document" unless they are part of the actual filename
- NEVER output natural language responses. ALWAYS output valid JSON only.
"""

# Initialize enhanced components
agent = EnhancedFileAgent(system_prompt=ENHANCED_SYSTEM_PROMPT)
voice_recognition = AdvancedVoiceRecognition()

class UserRequest(BaseModel):
    prompt: str
    current_dir: str = "."
    use_semantic: bool = True

@app.get("/")
def home():
    return {
        "message": "Enhanced FileWise API is running", 
        "features": ["conversational_memory", "semantic_search", "voice_recognition"],
        "status": "ok"
    }

@app.get("/status")
def get_status():
    return {
        "is_listening": voice_recognition.is_listening,
        "current_status": voice_recognition.current_status,
        "last_command": voice_recognition.last_command,
        "last_error": voice_recognition.last_error,
        "conversation_history_count": len(agent.memory.history),
        "wake_words": voice_recognition.wake_words
    }

@app.post("/start-voice")
def start_voice_recognition():
    return voice_recognition.start_continuous_listening()

@app.post("/stop-voice")
def stop_voice_recognition():
    return voice_recognition.stop_listening()

@app.post("/file-agent")
def handle_request(request: UserRequest):
    # Add semantic search parameter if requested
    if request.use_semantic:
        # This would modify the search parameters to enable semantic matching
        pass
        
    result = agent.process_request(request.prompt, request.current_dir)
    print(result)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result)
    return result

@app.get("/conversation-history")
def get_conversation_history():
    return {
        "history": agent.memory.history,
        "total_interactions": len(agent.memory.history)
    }

@app.post("/clear-conversation")
def clear_conversation():
    agent.memory.history = []
    return {"message": "Conversation history cleared"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8002)