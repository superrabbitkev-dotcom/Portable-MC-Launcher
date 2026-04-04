import os
import sys
import threading
import shutil
import requests
import zipfile
import io
import subprocess
import base64
import psutil
import ctypes
import customtkinter as ctk
import minecraft_launcher_lib
from tkinter import messagebox, filedialog

# --- DPI FIX FOR CRISP TEXT AND ICONS ---
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except:
        pass

# Fix for Taskbar Icon
if sys.platform == "win32":
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("rabbit.portablemc.launcher.v1")
    except:
        pass

# --- THEME & PATHS ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("green")

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

BIN_DIR = os.path.join(BASE_DIR, "bin")
RUNTIME_DIR = os.path.join(BIN_DIR, "runtime")
GAME_DIR = os.path.join(BIN_DIR, "game")
MODS_DIR = os.path.join(GAME_DIR, "mods")

for folder in [RUNTIME_DIR, GAME_DIR, MODS_DIR]:
    os.makedirs(folder, exist_ok=True)

class LauncherApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("PortableMC Pro")
        self.geometry("1000x750")
        self.configure(fg_color="#0d1117")
        
        # --- ICON LOGIC ---
        icon_path = os.path.join(BASE_DIR, "logo.ico")
        if os.path.exists(icon_path):
            try:
                # We use a slight delay to ensure the window is ready for the icon
                self.after(250, lambda: self.iconbitmap(icon_path))
            except:
                pass

        # Sidebar
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0, fg_color="#161b22")
        self.sidebar.pack(side="left", fill="y")
        ctk.CTkLabel(self.sidebar, text="PortableMC", font=("Arial", 24, "bold"), text_color="#2da44e").pack(pady=30)

        # Tabs
        self.tabview = ctk.CTkTabview(self, fg_color="#0d1117", segmented_button_selected_color="#2da44e")
        self.tabview.pack(padx=20, pady=10, fill="both", expand=True)
        self.tab_launch = self.tabview.add("Play")
        self.tab_mods = self.tabview.add("Mod Store")
        self.tab_settings = self.tabview.add("Settings")

        self.setup_launch_tab()
        self.setup_mod_store_tab()
        self.setup_settings_tab()

        self.console = ctk.CTkTextbox(self, height=120, fg_color="#000000", text_color="#58a6ff", font=("Consolas", 11))
        self.console.pack(padx=20, pady=20, fill="x")

    def log(self, message):
        self.console.insert("end", f"> {message}\n")
        self.console.see("end")

    def setup_launch_tab(self):
        frame = ctk.CTkFrame(self.tab_launch, fg_color="transparent")
        frame.pack(expand=True)
        self.version_menu = ctk.CTkOptionMenu(frame, values=["1.21.1", "1.20.1", "1.19.2"], width=250)
        self.version_menu.pack(pady=10)
        self.loader_menu = ctk.CTkOptionMenu(frame, values=["Vanilla", "Fabric"], width=250)
        self.loader_menu.pack(pady=10)
        self.launch_btn = ctk.CTkButton(frame, text="LAUNCH", command=self.start_launch, height=50, width=280, font=("Arial", 16, "bold"), fg_color="#238636")
        self.launch_btn.pack(pady=40)

    def setup_mod_store_tab(self):
        search_frame = ctk.CTkFrame(self.tab_mods, fg_color="transparent")
        search_frame.pack(fill="x", padx=20, pady=10)
        self.mod_search_entry = ctk.CTkEntry(search_frame, placeholder_text="Search Modrinth...", width=400)
        self.mod_search_entry.pack(side="left", padx=5)
        ctk.CTkButton(search_frame, text="Search", command=self.search_mods).pack(side="left")
        self.mod_results_frame = ctk.CTkScrollableFrame(self.tab_mods, fg_color="#161b22", height=400)
        self.mod_results_frame.pack(padx=20, pady=10, fill="both", expand=True)

    def search_mods(self):
        for widget in self.mod_results_frame.winfo_children(): widget.destroy()
        query = self.mod_search_entry.get()
        ver = self.version_menu.get()
        # Modrinth API v2
        url = f"https://api.modrinth.com/v2/search?query={query}&facets=[[\"categories:fabric\"],[\"versions:{ver}\"]]"
        try:
            res = requests.get(url).json()
            for mod in res['hits']:
                card = ctk.CTkFrame(self.mod_results_frame, fg_color="#21262d")
                card.pack(fill="x", padx=10, pady=5)
                ctk.CTkLabel(card, text=mod['title'], font=("Arial", 14, "bold")).pack(side="left", padx=10)
                ctk.CTkButton(card, text="Install", width=80, command=lambda m=mod: threading.Thread(target=self.download_mod, args=(m,)).start()).pack(side="right", padx=10)
        except Exception as e: self.log(f"Search failed: {e}")

    def download_mod(self, mod_data):
        p_id = mod_data.get('id')
        ver = self.version_menu.get()
        try:
            v_url = f"https://api.modrinth.com/v2/project/{p_id}/version"
            v_res = requests.get(v_url, params={"loaders": '["fabric"]', "game_versions": f'["{ver}"]'}).json()
            if v_res:
                f_info = v_res[0]['files'][0]
                path = os.path.join(MODS_DIR, f_info['filename'])
                if not os.path.exists(path):
                    r = requests.get(f_info['url'])
                    with open(path, "wb") as f: f.write(r.content)
                    self.log(f"Installed: {f_info['filename']}")
        except: pass

    def setup_settings_tab(self):
        ctk.CTkButton(self.tab_settings, text="Open Mods Folder", command=lambda: os.startfile(MODS_DIR)).pack(pady=20)
        self.skin_label = ctk.CTkLabel(self.tab_settings, text="Default Skin Active")
        self.skin_label.pack()
        ctk.CTkButton(self.tab_settings, text="Set Skin (.png)", command=self.select_skin).pack(pady=10)

    def select_skin(self):
        p = filedialog.askopenfilename(filetypes=[("Image", "*.png")])
        if p:
            self.skin_path = p
            self.skin_label.configure(text=f"Selected: {os.path.basename(p)}")

    def start_launch(self):
        self.launch_btn.configure(state="disabled", text="STARTING...")
        threading.Thread(target=self.run_launcher, daemon=True).start()

    def run_launcher(self):
        try:
            ver = self.version_menu.get()
            loader = self.loader_menu.get()
            mem = min(int(psutil.virtual_memory().total / (1024**3) / 2), 8)
            
            jv = "25" if "1.21" in ver else "17" if "1.18" in ver else "8"
            jf = os.path.join(RUNTIME_DIR, f"java-{jv}")
            if not os.path.exists(jf):
                self.log(f"Downloading Java {jv}...")
                u = f"https://api.adoptium.net/v3/binary/latest/{jv}/ga/windows/x64/jre/hotspot/normal/eclipse"
                r = requests.get(u)
                with zipfile.ZipFile(io.BytesIO(r.content)) as z: z.extractall(jf)
            
            java_exe = None
            for root, _, files in os.walk(jf):
                for f in files:
                    if f == "java.exe": java_exe = os.path.join(root, f)

            minecraft_launcher_lib.install.install_minecraft_version(ver, GAME_DIR)
            cid = ver
            if loader == "Fabric":
                minecraft_launcher_lib.fabric.install_fabric(ver, GAME_DIR)
                for v in minecraft_launcher_lib.utils.get_installed_versions(GAME_DIR):
                    if "fabric-loader" in v['id'] and ver in v['id']: cid = v['id']; break

            opt = {
                "username": "Player",
                "uuid": "0",
                "token": "",
                "executablePath": java_exe,
                "jvmArguments": [f"-Duser.home={GAME_DIR}", f"-Xmx{mem}G"]
            }
            subprocess.Popen(minecraft_launcher_lib.command.get_minecraft_command(cid, GAME_DIR, opt))
            self.after(5000, self.destroy)
        except Exception as e: messagebox.showerror("Error", str(e))
        finally: self.launch_btn.configure(state="normal", text="LAUNCH")

if __name__ == "__main__":
    LauncherApp().mainloop()