import asyncio
import os
import sys
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import yaml
from PIL import Image, ImageTk
import threading
import queue
import re
from media_downloader import begin_import, logger

class RedirectText:
    def __init__(self, text_widget):
        self.text_widget = text_widget
        self.queue = queue.Queue()
        self.update_timer = None
        self.ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        
    def write(self, string):
        # Remove ANSI escape sequences
        clean_string = self.ansi_escape.sub('', string)
        
        # Filter out unnecessary messages
        if any(msg in clean_string.lower() for msg in [
            'connecting', 'connected!', 'session', 'device:', 'system:',
            'network', 'ping', 'handler'
        ]):
            return
            
        self.queue.put(clean_string)
        if self.update_timer is None:
            self.update_timer = self.text_widget.after(100, self.update_text)
    
    def update_text(self):
        while not self.queue.empty():
            string = self.queue.get_nowait()
            self.text_widget.configure(state='normal')
            
            # Add tags for colored text
            if "✅" in string:
                self.text_widget.insert(tk.END, string, 'success')
            elif "❌" in string:
                self.text_widget.insert(tk.END, string, 'error')
            else:
                self.text_widget.insert(tk.END, string)
                
            self.text_widget.see(tk.END)
            self.text_widget.configure(state='disabled')
        self.update_timer = None
    
    def flush(self):
        pass

class TelegramDownloaderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Telegram Media Downloader")
        self.root.geometry("800x600")
        
        # Configure style
        style = ttk.Style()
        style.configure('TButton', padding=5)
        style.configure('TLabel', padding=5)
        style.configure('TEntry', padding=5)
        
        # Create main frame
        main_frame = ttk.Frame(root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # API Credentials frame
        cred_frame = ttk.LabelFrame(main_frame, text="API Credentials", padding="5")
        cred_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(cred_frame, text="API ID:").grid(row=0, column=0, sticky=tk.W)
        self.api_id_entry = ttk.Entry(cred_frame, width=50)
        self.api_id_entry.grid(row=0, column=1, padx=5)
        
        ttk.Label(cred_frame, text="API Hash:").grid(row=1, column=0, sticky=tk.W)
        self.api_hash_entry = ttk.Entry(cred_frame, width=50)
        self.api_hash_entry.grid(row=1, column=1, padx=5)
        
        ttk.Label(cred_frame, text="Phone Number:").grid(row=2, column=0, sticky=tk.W)
        self.phone_entry = ttk.Entry(cred_frame, width=50)
        self.phone_entry.grid(row=2, column=1, padx=5)
        
        # Channel input frame
        input_frame = ttk.LabelFrame(main_frame, text="Channel Details", padding="5")
        input_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(input_frame, text="Enter channel username/ID:").grid(row=0, column=0, sticky=tk.W)
        self.channel_entry = ttk.Entry(input_frame, width=50)
        self.channel_entry.grid(row=0, column=1, padx=5)
        
        # Load existing config if available
        try:
            with open("config.yaml", 'r') as f:
                config = yaml.safe_load(f)
                
            # Pre-fill credentials if they exist
            if config:
                self.api_id_entry.insert(0, str(config.get('api_id', '')))
                self.api_hash_entry.insert(0, config.get('api_hash', ''))
                self.phone_entry.insert(0, config.get('phone_number', ''))
                if 'chat_id' in config:
                    self.channel_entry.insert(0, str(config.get('chat_id', '')))
        except Exception as e:
            logger.warning(f"Could not load config: {str(e)}")
        
        # Download directory frame
        dir_frame = ttk.LabelFrame(main_frame, text="Download Location", padding="5")
        dir_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        self.dir_entry = ttk.Entry(dir_frame, width=50)
        self.dir_entry.grid(row=0, column=0, padx=5)
        self.dir_entry.insert(0, os.path.join(os.path.expanduser("~"), "Downloads"))
        
        ttk.Button(dir_frame, text="Browse", command=self.choose_directory).grid(row=0, column=1, padx=5)
        
        # Media types frame
        media_frame = ttk.LabelFrame(main_frame, text="Media Types", padding="5")
        media_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        self.media_vars = {
            "audio": tk.BooleanVar(value=True),
            "document": tk.BooleanVar(value=True),
            "photo": tk.BooleanVar(value=True),
            "video": tk.BooleanVar(value=True),
            "voice": tk.BooleanVar(value=True)
        }
        
        for i, (media_type, var) in enumerate(self.media_vars.items()):
            ttk.Checkbutton(media_frame, text=media_type.capitalize(), variable=var).grid(
                row=i//3, column=i%3, sticky=tk.W, padx=5
            )
        
        # Buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=2, pady=10)
        
        self.download_button = ttk.Button(button_frame, text="Start Download", command=self.start_download)
        self.download_button.grid(row=0, column=0, padx=5)
        
        ttk.Button(button_frame, text="Exit", command=root.quit).grid(row=0, column=1, padx=5)
        
        # Progress frame
        progress_frame = ttk.LabelFrame(main_frame, text="Download Progress", padding="5")
        progress_frame.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        # Create Text widget for logging with custom tags
        self.log_text = scrolledtext.ScrolledText(progress_frame, height=15, width=80)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.log_text.configure(state='disabled')
        
        # Configure text tags for colors
        self.log_text.tag_configure('success', foreground='green')
        self.log_text.tag_configure('error', foreground='red')
        
        # Redirect stdout to the Text widget
        sys.stdout = RedirectText(self.log_text)
        
        # Configure grid weights
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(5, weight=1)
        
        self.is_downloading = False
    
    def update_config(self):
        """Update config with GUI settings."""
        try:
            # Create default config if file doesn't exist
            if not os.path.exists("config.yaml"):
                config = {
                    "api_id": "",
                    "api_hash": "",
                    "phone_number": "",
                    "chat_id": "",
                    "media_types": ["audio", "document", "photo", "video", "voice"],
                    "file_formats": {
                        "audio": ["all"],
                        "document": ["all"],
                        "video": ["all"]
                    }
                }
            else:
                with open("config.yaml", 'r') as f:
                    config = yaml.safe_load(f)
            
            # Update API credentials
            api_id = self.api_id_entry.get().strip()
            api_hash = self.api_hash_entry.get().strip()
            phone = self.phone_entry.get().strip()
            
            if not api_id or not api_hash or not phone:
                messagebox.showerror("Error", "Please fill in all API credentials")
                return None
                
            try:
                config['api_id'] = int(api_id)
            except ValueError:
                messagebox.showerror("Error", "API ID must be a number")
                return None
                
            config['api_hash'] = api_hash
            config['phone_number'] = phone
            config['chat_id'] = self.channel_entry.get().strip()
            
            # Update media types based on checkboxes
            config['media_types'] = [
                media_type for media_type, var in self.media_vars.items()
                if var.get()
            ]
            
            if not config['media_types']:
                messagebox.showerror("Error", "Please select at least one media type")
                return None
            
            # Save the updated config
            with open("config.yaml", 'w') as f:
                yaml.safe_dump(config, f, default_flow_style=False)
            
            return config
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load/save config: {str(e)}")
            return None
    
    def choose_directory(self):
        dir_path = filedialog.askdirectory(
            initialdir=self.dir_entry.get(),
            title="Select Download Directory"
        )
        if dir_path:
            self.dir_entry.delete(0, tk.END)
            self.dir_entry.insert(0, dir_path)
            
    def start_download(self):
        """Start the download process in a separate thread."""
        if self.is_downloading:
            messagebox.showinfo("Info", "Download is already in progress!")
            return
        
        # Get the download directory
        download_dir = self.dir_entry.get()
        if not os.path.exists(download_dir):
            try:
                os.makedirs(download_dir)
            except Exception as e:
                messagebox.showerror("Error", f"Could not create download directory: {str(e)}")
                return
                
        # Get channel ID/username
        channel = self.channel_entry.get().strip()
        if not channel:
            messagebox.showerror("Error", "Please enter a channel username or ID")
            return
        
        config = self.update_config()
        if not config:
            return
        
        self.is_downloading = True
        self.download_button.configure(state='disabled')
        
        # Clear previous log
        self.log_text.configure(state='normal')
        self.log_text.delete(1.0, tk.END)
        self.log_text.configure(state='disabled')
        
        # Create and start download thread
        download_thread = threading.Thread(
            target=self.download_process,
            args=(config, download_dir, channel),
            daemon=True
        )
        download_thread.start()
    
    def download_process(self, config, download_dir, channel_input):
        """Run the download process."""
        try:
            # Clear any previous session files
            session_file = "media_downloader.session"
            if os.path.exists(session_file):
                try:
                    os.remove(session_file)
                except Exception as e:
                    logger.warning(f"Could not remove old session file: {str(e)}")
            
            asyncio.run(begin_import(config, pagination_limit=100, channel_input=channel_input, download_dir=download_dir))
        except Exception as e:
            messagebox.showerror("Error", f"Download failed: {str(e)}")
        finally:
            self.is_downloading = False
            self.root.after(0, self.download_button.configure, {'state': 'normal'})

def main():
    root = tk.Tk()
    app = TelegramDownloaderGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
