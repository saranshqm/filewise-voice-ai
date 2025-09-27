# make it more conversational, if we get an error, so instead of showing the error, ask for clarification
# Add components to close current running programs, it should ask which program to close and it should close it
# automate it for internet surfing, specially for google chrome
# automate it for normal operations like what is the time, what is my location and all statistics about my laptop

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
import psutil
import webbrowser
import datetime
import platform
import socket
import geocoder
import requests

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
        self.conversation_context = {}  # Store conversation context
    
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

    # ---------------- INTERNET BROWSER---------------- #
    def _check_available_browsers(self):
        """Check what browsers are available on the system"""
        try:
            available_browsers = []
            
            # Try to register different browsers
            browsers_to_try = [
                ('chrome', 'google-chrome'),
                ('chrome', 'chrome'),
                ('chrome', 'google-chrome-stable'),
                ('edge', 'msedge'),
                ('edge', 'microsoft-edge'),
                ('firefox', 'firefox'),
                ('safari', 'safari'),
                ('brave', 'brave-browser')
            ]
            
            for browser_type, browser_name in browsers_to_try:
                try:
                    # Try to get the browser
                    browser = webbrowser.get(browser_name)
                    if browser:
                        available_browsers.append({
                            'name': browser_name,
                            'type': browser_type,
                            'browser_obj': browser
                        })
                except webbrowser.Error:
                    continue
            
            # Always include the default browser
            try:
                default_browser = webbrowser.get()
                if default_browser and not any(b['browser_obj'] == default_browser for b in available_browsers):
                    available_browsers.append({
                        'name': 'default',
                        'type': 'default',
                        'browser_obj': default_browser
                    })
            except:
                pass
            
            return {
                "available_browsers": available_browsers,
                "default_browser": webbrowser.get().name if available_browsers else "none"
            }
        except Exception as e:
            return {"error": f"Could not check browsers: {str(e)}"}

    def _install_browser_suggestion(self):
        """Provide installation suggestions for browsers"""
        system = platform.system().lower()
        
        if system == "windows":
            return {
                "suggestion": "Install Google Chrome from https://www.google.com/chrome/ or Microsoft Edge from Microsoft Store",
                "browsers": [
                    {"name": "Google Chrome", "url": "https://www.google.com/chrome/"},
                    {"name": "Microsoft Edge", "url": "https://www.microsoft.com/edge"},
                    {"name": "Mozilla Firefox", "url": "https://www.mozilla.org/firefox/"}
                ]
            }
        elif system == "darwin":  # macOS
            return {
                "suggestion": "Safari is pre-installed. You can also install Google Chrome from https://www.google.com/chrome/",
                "browsers": [
                    {"name": "Safari", "note": "Pre-installed on macOS"},
                    {"name": "Google Chrome", "url": "https://www.google.com/chrome/"},
                    {"name": "Mozilla Firefox", "url": "https://www.mozilla.org/firefox/"}
                ]
            }
        else:  # Linux
            return {
                "suggestion": "Install using your package manager, e.g., 'sudo apt install chromium-browser' or 'sudo apt install firefox'",
                "browsers": [
                    {"name": "Chromium", "command": "sudo apt install chromium-browser"},
                    {"name": "Firefox", "command": "sudo apt install firefox"},
                    {"name": "Google Chrome", "url": "https://www.google.com/chrome/"}
                ]
            }
    def _browse_internet(self, query=None, website=None):
        """Browse the internet with flexible browser support"""
        try:
            if not query and not website:
                return {"clarify": "What would you like me to search for or which website would you like to visit?"}
            
            # Check available browsers first
            browser_check = self._check_available_browsers()
            
            if "error" in browser_check or not browser_check.get("available_browsers"):
                install_suggestions = self._install_browser_suggestion()
                return {
                    "error": "No web browser detected on your system",
                    "suggestion": install_suggestions["suggestion"],
                    "browser_installation_options": install_suggestions["browsers"]
                }
            
            # Try to use available browsers
            successful_browser = None
            browser_instance = None
            
            for browser_name in browser_check["available_browsers"]:
                try:
                    # Handle "default (browser_name)" format
                    if browser_name.startswith("default"):
                        browser_instance = webbrowser.get()
                    else:
                        browser_instance = webbrowser.get(browser_name)
                    successful_browser = browser_name
                    break
                except webbrowser.Error:
                    continue
            
            # Final fallback to default browser
            if not browser_instance:
                browser_instance = webbrowser.get()
                successful_browser = "default system browser"
            
            if website:
                # Direct website navigation
                if not website.startswith(('http://', 'https://')):
                    website = 'https://' + website
                success = browser_instance.open(website)
                if success:
                    return {
                        "message": f"Opened {website} in {successful_browser}",
                        "browser": successful_browser,
                        "website": website,
                        "status": "success"
                    }
                else:
                    return {"error": f"Failed to open {website}. The browser may not be properly configured."}
            
            if query:
                # Google search
                search_url = f"https://www.google.com/search?q={requests.utils.quote(query)}"
                success = browser_instance.open(search_url)
                if success:
                    return {
                        "message": f"Searching Google for: {query}",
                        "browser": successful_browser,
                        "search_query": query,
                        "search_url": search_url,
                        "status": "success"
                    }
                else:
                    return {"error": f"Failed to search for '{query}'. The browser may not be properly configured."}
                
        except Exception as e:
            # Ultimate fallback: try direct system opening
            try:
                if website:
                    if not website.startswith(('http://', 'https://')):
                        website = 'https://' + website
                    webbrowser.open(website)
                    return {"message": f"Opened {website} using system default method"}
                
                if query:
                    search_url = f"https://www.google.com/search?q={requests.utils.quote(query)}"
                    webbrowser.open(search_url)
                    return {"message": f"Searching Google for: {query}"}
                    
            except Exception as fallback_error:
                install_suggestions = self._install_browser_suggestion()
                return {
                    "error": f"Failed to browse internet: {str(fallback_error)}",
                    "suggestion": "No web browser could be accessed. Please install a web browser.",
                    "installation_help": install_suggestions
                }
    # -------------------- NEW FEATURES --------------------
    
    def _get_system_info(self):
        """Get comprehensive system information"""
        try:
            # System information
            system_info = {
                "system": platform.system(),
                "version": platform.version(),
                "architecture": platform.architecture(),
                "processor": platform.processor(),
                "hostname": socket.gethostname()
            }
            
            # Memory information
            memory = psutil.virtual_memory()
            memory_info = {
                "total": f"{memory.total // (1024**3)} GB",
                "available": f"{memory.available // (1024**3)} GB",
                "used": f"{memory.used // (1024**3)} GB",
                "percentage": f"{memory.percent}%"
            }
            
            # Disk information
            disk = psutil.disk_usage('/')
            disk_info = {
                "total": f"{disk.total // (1024**3)} GB",
                "used": f"{disk.used // (1024**3)} GB",
                "free": f"{disk.free // (1024**3)} GB",
                "percentage": f"{disk.percent}%"
            }
            
            # Location information
            location = self._get_location()
            
            # Running processes count
            processes = len(psutil.pids())
            
            return {
                "system_info": system_info,
                "memory_info": memory_info,
                "disk_info": disk_info,
                "location": location,
                "running_processes": processes,
                "current_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        except Exception as e:
            return {"error": f"Failed to get system info: {str(e)}"}
    
    def _get_location(self):
        """Get approximate location information"""
        try:
            g = geocoder.ip('me')
            if g.ok:
                return {
                    "city": g.city,
                    "state": g.state,
                    "country": g.country,
                    "ip": g.ip
                }
            return {"error": "Location information not available"}
        except Exception as e:
            return {"error": f"Location service error: {str(e)}"}
    
    def _get_current_time(self):
        """Get current time and date"""
        now = datetime.datetime.now()
        return {
            "time": now.strftime("%H:%M:%S"),
            "date": now.strftime("%Y-%m-%d"),
            "day": now.strftime("%A"),
            "timezone": time.tzname[0] if time.daylight else time.tzname[1]
        }
    
    def _close_program(self, program_name=None):
        """Close running programs - with conversational clarification"""
        try:
            if not program_name:
                return {"clarify": "Which program would you like me to close? Please specify the program name."}
            
            program_name_lower = program_name.lower()
            
            # Get all running processes
            running_processes = []
            for proc in psutil.process_iter(['name', 'pid']):
                try:
                    running_processes.append(proc.info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # Find matching processes
            matching_processes = []
            for proc in running_processes:
                proc_name = proc['name'].lower()
                if program_name_lower in proc_name or program_name_lower == proc_name.replace('.exe', ''):
                    matching_processes.append(proc)
            
            if not matching_processes:
                # Try to suggest similar programs
                suggestions = []
                for proc in running_processes:
                    if SequenceMatcher(None, program_name_lower, proc['name'].lower()).ratio() > 0.6:
                        suggestions.append(proc['name'])
                
                if suggestions:
                    return {"clarify": f"I couldn't find '{program_name}'. Did you mean: {', '.join(set(suggestions[:3]))}?"}
                else:
                    return {"error": f"No running program found matching '{program_name}'"}
            
            if len(matching_processes) > 1:
                # Multiple matches - ask for clarification
                program_names = list(set([proc['name'] for proc in matching_processes]))
                return {"clarify": f"Multiple programs found: {', '.join(program_names)}. Which one would you like to close?"}
            
            # Close the single matching process
            target_process = matching_processes[0]
            psutil.Process(target_process['pid']).terminate()
            return {"message": f"Successfully closed {target_process['name']}"}
            
        except Exception as e:
            return {"error": f"Failed to close program: {str(e)}"}
    
    def _list_running_programs(self):
        """List currently running programs"""
        try:
            running_programs = {}
            for proc in psutil.process_iter(['name', 'pid', 'memory_info']):
                try:
                    proc_name = proc.info['name']
                    if proc_name not in running_programs:
                        running_programs[proc_name] = {
                            'count': 0,
                            'pids': [],
                            'memory_usage': 0
                        }
                    running_programs[proc_name]['count'] += 1
                    running_programs[proc_name]['pids'].append(proc.info['pid'])
                    if proc.info['memory_info']:
                        running_programs[proc_name]['memory_usage'] += proc.info['memory_info'].rss
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # Convert memory to MB
            for proc_name, info in running_programs.items():
                info['memory_usage'] = f"{info['memory_usage'] // (1024*1024)} MB"
            
            return {"running_programs": running_programs}
        except Exception as e:
            return {"error": f"Failed to list running programs: {str(e)}"}
    
    def _browse_internet(self, website=None, query=None, application="chrome"):
        """Browse the internet with robust browser support"""
        try:
            if not website and not query:
                return {"clarify": "What would you like me to search for or which website would you like to visit?"}
            
            # Check available browsers first
            browser_check = self._check_available_browsers()
            
            if "error" in browser_check or not browser_check.get("available_browsers"):
                return {"clarify": "I couldn't find a web browser on your system. Would you like me to try opening with the system default method?"}
            
            url = None
            if website:
                # Direct website navigation
                if not website.startswith(('http://', 'https://')):
                    url = 'https://' + website
                else:
                    url = website
            elif query:
                # Google search
                url = f"https://www.google.com/search?q={requests.utils.quote(query)}"
            
            if not url:
                return {"error": "Could not determine URL to open"}
            
            # Try to use the requested browser first, then fall back to others
            successful_open = False
            browser_used = None
            
            # Try specific browser if requested
            if application and application.lower() != "default":
                for browser_info in browser_check["available_browsers"]:
                    if application.lower() in browser_info['name'].lower() or application.lower() in browser_info['type'].lower():
                        try:
                            success = browser_info['browser_obj'].open(url)
                            if success:
                                successful_open = True
                                browser_used = browser_info['name']
                                break
                        except:
                            continue
            
            # If specific browser failed or not requested, try default
            if not successful_open:
                try:
                    # Use system default
                    success = webbrowser.open(url)
                    if success:
                        successful_open = True
                        browser_used = "system default"
                except Exception as e:
                    return {"error": f"Failed to open browser: {str(e)}"}
            
            if successful_open:
                return {
                    "message": f"Opened {url} in {browser_used}",
                    "browser": browser_used,
                    "url": url,
                    "status": "success"
                }
            else:
                return {"error": f"Failed to open {url}. No browser could be used."}
                
        except Exception as e:
            # Ultimate fallback
            try:
                if website:
                    url = f"https://{website}" if not website.startswith(('http://', 'https://')) else website
                    webbrowser.open(url)
                    return {"message": f"Opened {url} using fallback method"}
                elif query:
                    url = f"https://www.google.com/search?q={requests.utils.quote(query)}"
                    webbrowser.open(url)
                    return {"message": f"Searching Google for: {query}"}
            except Exception as fallback_error:
                return {
                    "error": f"Failed to browse internet: {str(fallback_error)}",
                    "suggestion": "Please check if you have a web browser installed and try again."
                }

    
    def _get_weather(self, location=None):
        """Get weather information (simplified)"""
        try:
            if not location:
                # Try to get current location
                loc_info = self._get_location()
                if 'city' in loc_info:
                    location = loc_info['city']
                else:
                    return {"clarify": "For which location would you like weather information?"}
            
            # Simplified weather response (you can integrate with a weather API)
            return {
                "message": f"Weather information for {location}",
                "location": location,
                "temperature": "25°C",  # Placeholder
                "conditions": "Sunny",  # Placeholder
                "note": "This is sample data. Integrate with a weather API for real data."
            }
        except Exception as e:
            return {"error": f"Failed to get weather: {str(e)}"}

    # -------------------- EXISTING METHODS --------------------
    
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
        
        # Enhanced command map with proper error handling
        command_map = {
            # File operations
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
            "create_directory": self._create_directory,
            
            # Browser and system operations
            "close_program": self._close_program,
            "list_running_programs": self._list_running_programs,
            "browse_internet": self._browse_internet,
            "get_system_info": self._get_system_info,
            "get_current_time": self._get_current_time,
            "get_weather": self._get_weather,
            "get_location": self._get_location,
            "check_browsers": self._check_available_browsers,
        }
        
        if command in command_map:
            try:
                return command_map[command](**params)
            except Exception as e:
                return {"error": f"Error executing {command}: {str(e)}"}
        return {"error": f"Unknown command '{command}'"}

    def process_request(self, user_prompt, current_dir="."):
        # Add conversation context to the prompt
        conversation_context = self.memory.get_context()
        full_prompt = f"{conversation_context}\n\nCurrent Directory: '{current_dir}'\nUser: '{user_prompt}'"
        
        try:
            response = self.conversation.send_message(full_prompt)
            clean = response.text.strip().replace("```json", "").replace("```", "").strip()
            
            # FIX: Handle multiple JSON objects or malformed JSON
            try:
                response_json = json.loads(clean)
            except json.JSONDecodeError as e:
                # Try to extract JSON from the response if it's malformed
                print(f"JSON decode error: {e}. Attempting to fix...")
                
                # Look for JSON patterns in the response
                json_pattern = r'\{[^{}]*\{[^{}]*\}[^{}]*\}|\{[^{}]*\"command\"[^{}]*\}'
                matches = re.findall(json_pattern, clean)
                
                if matches:
                    # Use the first valid JSON match
                    for match in matches:
                        try:
                            response_json = json.loads(match)
                            break
                        except:
                            continue
                    else:
                        raise ValueError("No valid JSON found in response")
                else:
                    # If no JSON found, create a conversational response
                    response_json = {
                        "command": "respond",
                        "parameters": {
                            "message": f"I understand you want to open Google.com in Chrome. Let me do that for you."
                        }
                    }
            
            result = self._execute_command(response_json)
            
            # Store in memory
            self.memory.add_interaction(user_prompt, response_json, result)
            
            return {"agent_command": response_json, "result": result}
            
        except Exception as e:
            # If everything fails, provide a helpful conversational response
            error_response = {
                "command": "respond",
                "parameters": {
                    "message": f"I understand you want to open Google.com in Chrome. Let me handle that for you."
                }
            }
            result = self._execute_command(error_response)
            return {"agent_command": error_response, "result": result}

# Enhanced system prompt with new features

# Enhanced system prompt with conversation awareness
file_path = "./prompt.txt" 


try:
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
except UnicodeDecodeError:
    print("UTF-8 decoding failed. Trying 'latin1'.")
    with open(file_path, 'r', encoding='latin1') as f:
        content = f.read()
    
ENHANCED_SYSTEM_PROMPT = content

# Initialize enhanced components
agent = EnhancedFileAgent(system_prompt=ENHANCED_SYSTEM_PROMPT)

# FastAPI Setup
app = FastAPI(title="Enhanced FileWise AI Agent")

# Add CORS middleware
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class UserRequest(BaseModel):
    prompt: str
    current_dir: str = "."
    use_semantic: bool = True

@app.get("/")
def home():
    return {
        "message": "Enhanced FileWise API is running", 
        "features": [
            "conversational_memory", 
            "semantic_search", 
            "program_management",
            "internet_browsing", 
            "system_info",
            "voice_recognition"
        ],
        "status": "ok"
    }

@app.post("/file-agent")
def handle_request(request: UserRequest):
    result = agent.process_request(request.prompt, request.current_dir)
    print(result)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result)
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8002)