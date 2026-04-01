import os
import sys
import threading
import customtkinter as ctk
import minecraft_launcher_lib
import requests
import zipfile
import io
import platform
import subprocess
from tkinter import messagebox

# --- PORTABLE DIRECTORY SETUP ---
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

BIN_DIR = os.path.join(BASE_DIR, "bin")
RUNTIME_DIR = os.path.join(BIN_DIR, "runtime")
GAME_DIR = os.path.join(BIN_DIR, "game")

os.makedirs(RUNTIME_DIR, exist_ok=True)
os.makedirs(GAME_DIR, exist_ok=True)

# --- UTILITY FUNCTIONS ---
def get_java_version(mc_version):
    try:
        minor = int(mc_version.split('.')[1]) if len(mc_version.split('.')) > 1 else 0
        if minor >= 21: return "25"
        if minor >= 18: return "17"
        return "8"
    except:
        return "17"

def download_java(java_v, status_callback):
    target = os.path.join(RUNTIME_DIR, f"java-{java_v}")
    
    # Check if folder exists and isn't empty
    if os.path.exists(target) and os.listdir(target):
        return target
    
    os.makedirs(target, exist_ok=True)
    status_callback(f"Downloading Java {java_v}...")

    sys_os = "windows" if platform.system() == "Windows" else "linux"
    url = f"https://api.adoptium.net/v3/binary/latest/{java_v}/ga/{sys_os}/x64/jre/hotspot/normal/eclipse"
    
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    
    status_callback(f"Extracting Java...")
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        z.extractall(target)
    return target

def find_java_bin(folder):
    for root, dirs, files in os.walk(folder):
        for f in files:
            if f in ["java.exe", "java"]:
                return os.path.join(root, f)
    return None

# --- UI CLASS ---
class LauncherApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Portable MC Launcher")
        self.geometry("450x350")
        ctk.set_appearance_mode("dark")

        self.label = ctk.CTkLabel(self, text="Minecraft Portable", font=("Arial Bold", 24))
        self.label.pack(pady=30)

        self.version_menu = ctk.CTkOptionMenu(self, values=["1.21.1", "1.20.1", "1.19.2", "1.12.2"])
        self.version_menu.pack(pady=10)

        self.status_label = ctk.CTkLabel(self, text="Status: Ready", text_color="gray")
        self.status_label.pack(pady=10)

        self.launch_btn = ctk.CTkButton(self, text="Launch Game", command=self.start_launch_thread, fg_color="#2da44e", hover_color="#2c974b")
        self.launch_btn.pack(pady=20)

    def update_status(self, text):
        self.status_label.configure(text=f"Status: {text}")

    def start_launch_thread(self):
        self.launch_btn.configure(state="disabled")
        threading.Thread(target=self.run_launcher, daemon=True).start()

    def run_launcher(self):
        try:
            version = self.version_menu.get()
            
            # 1. Handle Java
            java_v = get_java_version(version)
            java_folder = download_java(java_v, self.update_status)
            java_exe = find_java_bin(java_folder)
            
            if not java_exe:
                raise Exception("Could not locate java executable in downloaded folder.")

            # 2. Handle Game Files
            self.update_status(f"Downloading Minecraft {version}...")
            minecraft_launcher_lib.install.install_minecraft_version(version, GAME_DIR)

            # 3. Launching
            self.update_status("Launching...")
            options = {
                "username": "PortablePlayer",
                "uuid": "00000000-0000-0000-0000-000000000000",
                "token": "",
                "executablePath": java_exe,
                "jvmArguments": [f"-Duser.home={GAME_DIR}", "-Xmx2G"]
            }
            
            command = minecraft_launcher_lib.command.get_minecraft_command(version, GAME_DIR, options)
            
            # Fix for 1.21 Render Thread Error
            subprocess.Popen(command, creationflags=subprocess.CREATE_NEW_CONSOLE if platform.system() == "Windows" else 0)
            
            self.after(3000, self.withdraw) # Hide launcher after 3 seconds
            
        except Exception as e:
            messagebox.showerror("Launcher Error", str(e))
            self.update_status("Error Occurred")
        finally:
            self.launch_btn.configure(state="normal")

if __name__ == "__main__":
    app = LauncherApp()
    app.mainloop()