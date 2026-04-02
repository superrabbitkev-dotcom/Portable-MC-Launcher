import os
import sys
import threading
import shutil
import requests
import zipfile
import io
import platform
import subprocess
import customtkinter as ctk
import minecraft_launcher_lib
from tkinter import messagebox, filedialog

# --- PORTABLE DIRECTORY SETUP ---
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

BIN_DIR = os.path.join(BASE_DIR, "bin")
RUNTIME_DIR = os.path.join(BIN_DIR, "runtime")
GAME_DIR = os.path.join(BIN_DIR, "game")

for folder in [RUNTIME_DIR, GAME_DIR]:
    os.makedirs(folder, exist_ok=True)

# --- LOGIC FUNCTIONS ---
def get_java_version(mc_version):
    try:
        minor = int(mc_version.split('.')[1]) if len(mc_version.split('.')) > 1 else 0
        if minor >= 21: return "25"
        if minor >= 18: return "17"
        return "8"
    except: return "17"

def download_java(java_v, status_callback):
    target = os.path.join(RUNTIME_DIR, f"java-{java_v}")
    if os.path.exists(target) and os.listdir(target):
        return target
    
    os.makedirs(target, exist_ok=True)
    status_callback(f"Downloading Java {java_v}...")
    sys_os = "windows" if platform.system() == "Windows" else "linux"
    url = f"https://api.adoptium.net/v3/binary/latest/{java_v}/ga/{sys_os}/x64/jre/hotspot/normal/eclipse"
    
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
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

def apply_skin_as_pack(skin_source_path, game_dir):
    """Creates a local resource pack to inject the skin into offline mode."""
    pack_root = os.path.join(game_dir, "resourcepacks", "SkinPack")
    skin_dest = os.path.join(pack_root, "assets", "minecraft", "textures", "entity", "player")
    
    if os.path.exists(pack_root): shutil.rmtree(pack_root)
    os.makedirs(skin_dest, exist_ok=True)

    # Create pack.mcmeta (Format 34 is for 1.21)
    with open(os.path.join(pack_root, "pack.mcmeta"), "w") as f:
        f.write('{"pack": {"pack_format": 34, "description": "Launcher Skin Pack"}}')

    # Copy skin to all possible default slots
    for name in ["steve.png", "alex.png", "wide.png", "slim.png"]:
        shutil.copy(skin_source_path, os.path.join(skin_dest, name))
    return "SkinPack"

# --- UI CLASS ---
class LauncherApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Portable MC Launcher 2026")
        self.geometry("500x450")
        ctk.set_appearance_mode("dark")
        self.skin_path = None

        # Tabs
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(padx=20, pady=20, fill="both", expand=True)
        self.tab_launch = self.tabview.add("Launch")
        self.tab_skin = self.tabview.add("Skin Settings")

        # Launch Tab
        self.label = ctk.CTkLabel(self.tab_launch, text="Minecraft Portable", font=("Arial Bold", 24))
        self.label.pack(pady=20)
        self.version_menu = ctk.CTkOptionMenu(self.tab_launch, values=["1.21.1", "1.20.1", "1.19.2", "1.12.2"])
        self.version_menu.pack(pady=10)
        self.status_label = ctk.CTkLabel(self.tab_launch, text="Status: Ready", text_color="gray")
        self.status_label.pack(pady=10)
        self.launch_btn = ctk.CTkButton(self.tab_launch, text="Launch Game", command=self.start_launch_thread, fg_color="#2da44e")
        self.launch_btn.pack(pady=20)

        # Skin Tab
        self.skin_title = ctk.CTkLabel(self.tab_skin, text="Character Customization", font=("Arial Bold", 18))
        self.skin_title.pack(pady=20)
        self.skin_display = ctk.CTkLabel(self.tab_skin, text="No Skin Selected", text_color="gray")
        self.skin_display.pack(pady=10)
        self.upload_btn = ctk.CTkButton(self.tab_skin, text="Select Skin PNG", command=self.select_skin)
        self.upload_btn.pack(pady=10)

    def select_skin(self):
        file = filedialog.askopenfilename(filetypes=[("Image files", "*.png")])
        if file:
            self.skin_path = file
            self.skin_display.configure(text=os.path.basename(file), text_color="white")

    def update_status(self, text):
        self.status_label.configure(text=f"Status: {text}")

    def start_launch_thread(self):
        self.launch_btn.configure(state="disabled")
        threading.Thread(target=self.run_launcher, daemon=True).start()

    def run_launcher(self):
        try:
            version = self.version_menu.get()
            
            # 1. Java
            java_v = get_java_version(version)
            java_folder = download_java(java_v, self.update_status)
            java_exe = find_java_bin(java_folder)

            # 2. Game Files
            self.update_status(f"Downloading MC {version}...")
            minecraft_launcher_lib.install.install_minecraft_version(version, GAME_DIR)

            # 3. Skin Pack
            if self.skin_path:
                self.update_status("Applying Skin Pack...")
                apply_skin_as_pack(self.skin_path, GAME_DIR)

            # 4. Final Launch
            self.update_status("Launching...")
            options = {
                "username": "PortablePlayer",
                "uuid": "00000000-0000-0000-0000-000000000000",
                "token": "",
                "executablePath": java_exe,
                "jvmArguments": [f"-Duser.home={GAME_DIR}", "-Xmx2G"]
            }
            command = minecraft_launcher_lib.command.get_minecraft_command(version, GAME_DIR, options)
            
            subprocess.Popen(command, creationflags=subprocess.CREATE_NEW_CONSOLE if platform.system() == "Windows" else 0)
            self.after(5000, self.withdraw)
            
        except Exception as e:
            messagebox.showerror("Error", str(e))
            self.update_status("Error Occurred")
        finally:
            self.launch_btn.configure(state="normal")

if __name__ == "__main__":
    app = LauncherApp()
    app.mainloop()