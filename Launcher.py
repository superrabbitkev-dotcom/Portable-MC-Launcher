import os
import sys
import threading
import shutil
import requests
import zipfile
import io
import platform
import subprocess
import base64
import psutil # New: for RAM detection
import customtkinter as ctk
import minecraft_launcher_lib
from tkinter import messagebox, filedialog

# --- SECURITY & ANTI-TAMPER ---
def check_integrity():
    if getattr(sys, 'frozen', False):
        exe_name = os.path.basename(sys.executable).lower()
        if "portablemc" not in exe_name and "python" not in exe_name:
            sys.exit()

def get_api_url():
    return base64.b64decode("aHR0cHM6Ly9hcGkubW9kcmludGguY29tL3Yy").decode('utf-8')

check_integrity()

# --- THEME ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("green")

# --- DIRECTORIES ---
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
        
        self.title("Minecraft Portable Pro")
        self.geometry("1000x750")
        self.configure(fg_color="#0d1117")
        self.skin_path = None

        # Sidebar
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0, fg_color="#161b22")
        self.sidebar.pack(side="left", fill="y")
        ctk.CTkLabel(self.sidebar, text="PortableMC", font=("Arial", 24, "bold"), text_color="#2da44e").pack(pady=30)

        # Tabs
        self.tabview = ctk.CTkTabview(self, fg_color="#0d1117", segmented_button_selected_color="#2da44e")
        self.tabview.pack(padx=20, pady=10, fill="both", expand=True)
        self.tab_launch = self.tabview.add("Play")
        self.tab_mods = self.tabview.add("Mod Store")
        self.tab_settings = self.tabview.add("Customization")

        self.setup_launch_tab()
        self.setup_mod_store_tab()
        self.setup_settings_tab()

        # Console
        self.console = ctk.CTkTextbox(self, height=120, fg_color="#000000", text_color="#58a6ff", font=("Consolas", 11))
        self.console.pack(padx=20, pady=20, fill="x")
        self.log("System Initialized.")

    def log(self, message):
        self.console.insert("end", f"> {message}\n")
        self.console.see("end")

    def update_status(self, text):
        self.launch_btn.configure(text=text.upper())

    def setup_launch_tab(self):
        frame = ctk.CTkFrame(self.tab_launch, fg_color="transparent")
        frame.pack(expand=True)
        
        ctk.CTkLabel(frame, text="Select Version", font=("Arial", 14)).pack(pady=5)
        self.version_menu = ctk.CTkOptionMenu(frame, values=["1.21.1", "1.20.1", "1.19.2", "1.12.2"], width=250)
        self.version_menu.pack(pady=10)
        
        ctk.CTkLabel(frame, text="Select Engine", font=("Arial", 14)).pack(pady=5)
        self.loader_menu = ctk.CTkOptionMenu(frame, values=["Vanilla", "Fabric", "Forge"], width=250)
        self.loader_menu.pack(pady=10)
        
        self.launch_btn = ctk.CTkButton(frame, text="LAUNCH GAME", command=self.start_launch, height=60, width=300, font=("Arial", 20, "bold"), fg_color="#238636")
        self.launch_btn.pack(pady=50)

    def setup_mod_store_tab(self):
        search_frame = ctk.CTkFrame(self.tab_mods, fg_color="transparent")
        search_frame.pack(fill="x", padx=20, pady=10)
        self.mod_search_entry = ctk.CTkEntry(search_frame, placeholder_text="Search mods (e.g. Sodium, Iris, Create)...", width=500)
        self.mod_search_entry.pack(side="left", padx=5)
        self.mod_search_entry.bind("<Return>", lambda e: self.search_mods())
        ctk.CTkButton(search_frame, text="Search", width=120, command=self.search_mods).pack(side="left")
        
        self.mod_results_frame = ctk.CTkScrollableFrame(self.tab_mods, fg_color="#161b22", height=450)
        self.mod_results_frame.pack(padx=20, pady=10, fill="both", expand=True)

    def search_mods(self):
        for widget in self.mod_results_frame.winfo_children(): widget.destroy()
        query = self.mod_search_entry.get()
        ver = self.version_menu.get()
        self.log(f"Searching for '{query}'...")
        url = f"{get_api_url()}/search?query={query}&facets=[[\"categories:fabric\"],[\"versions:{ver}\"]]"
        try:
            res = requests.get(url).json()
            for mod in res['hits']:
                card = ctk.CTkFrame(self.mod_results_frame, fg_color="#21262d")
                card.pack(fill="x", padx=10, pady=5)
                header = ctk.CTkFrame(card, fg_color="transparent")
                header.pack(fill="x", padx=10, pady=(5,0))
                ctk.CTkLabel(header, text=mod['title'], font=("Arial", 14, "bold"), text_color="#58a6ff").pack(side="left")
                ctk.CTkLabel(header, text=f"by {mod['author']}", font=("Arial", 10), text_color="gray").pack(side="left", padx=10)
                desc = mod.get('description', "No description.")
                ctk.CTkLabel(card, text=(desc[:120] + '..'), font=("Arial", 11), wraplength=650, justify="left").pack(padx=10, pady=5, anchor="w")
                ctk.CTkButton(card, text="Install", width=90, height=28, fg_color="#238636", command=lambda m=mod: threading.Thread(target=self.download_mod, args=(m,)).start()).pack(side="right", padx=10, pady=5)
        except Exception as e: self.log(f"Search error: {e}")

    def download_mod(self, mod_data, is_dep=False):
        p_id = mod_data.get('project_id') or mod_data.get('id')
        ver = self.version_menu.get()
        try:
            v_url = f"{get_api_url()}/project/{p_id}/version"
            v_res = requests.get(v_url, params={"loaders": '["fabric"]', "game_versions": f'["{ver}"]'}).json()
            if not v_res: return
            latest = v_res[0]
            if 'dependencies' in latest:
                for dep in latest['dependencies']:
                    if dep['dependency_type'] == "required":
                        self.download_mod({"id": dep['project_id']}, is_dep=True)
            f_info = latest['files'][0]
            path = os.path.join(MODS_DIR, f_info['filename'])
            if not os.path.exists(path):
                self.log(f"Installing {f_info['filename']}...")
                r = requests.get(f_info['url'])
                with open(path, "wb") as f: f.write(r.content)
            if not is_dep: self.log(f"Finished installing {mod_data.get('title', 'mod')}")
        except Exception as e: self.log(f"Download error: {e}")

    def setup_settings_tab(self):
        ctk.CTkButton(self.tab_settings, text="📂 Open Mods Folder", command=lambda: os.startfile(MODS_DIR), width=250).pack(pady=20)
        self.skin_label = ctk.CTkLabel(self.tab_settings, text="Current Skin: Default")
        self.skin_label.pack()
        ctk.CTkButton(self.tab_settings, text="👤 Set Custom Skin (.png)", command=self.select_skin, width=250, fg_color="#30363d").pack(pady=10)

    def select_skin(self):
        p = filedialog.askopenfilename(filetypes=[("Image", "*.png")])
        if p:
            self.skin_path = p
            self.skin_label.configure(text=f"Selected: {os.path.basename(p)}", text_color="#2da44e")

    def start_launch(self):
        self.launch_btn.configure(state="disabled")
        threading.Thread(target=self.run_launcher, daemon=True).start()

    def run_launcher(self):
        try:
            ver = self.version_menu.get()
            loader = self.loader_menu.get()
            
            # 1. RAM Calculation
            total_ram = psutil.virtual_memory().total / (1024**3)
            alloc_ram = min(int(total_ram / 2), 8) # Give half system RAM, max 8GB
            self.log(f"Allocating {alloc_ram}GB RAM...")

            # 2. Java setup
            jv = "25" if int(ver.split('.')[1]) >= 21 else "17" if int(ver.split('.')[1]) >= 18 else "8"
            self.update_status(f"Java {jv} Check")
            jf = os.path.join(RUNTIME_DIR, f"java-{jv}")
            if not os.path.exists(jf):
                self.log(f"Downloading Java Runtime {jv}...")
                u = f"https://api.adoptium.net/v3/binary/latest/{jv}/ga/windows/x64/jre/hotspot/normal/eclipse"
                r = requests.get(u)
                with zipfile.ZipFile(io.BytesIO(r.content)) as z: z.extractall(jf)
            
            java_exe = None
            for root, _, files in os.walk(jf):
                for f in files:
                    if f == "java.exe": java_exe = os.path.join(root, f)
            
            # 3. Base Game sync
            self.update_status("Syncing Assets")
            minecraft_launcher_lib.install.install_minecraft_version(ver, GAME_DIR)
            
            # 4. Mod Loader sync
            cid = ver
            if loader == "Fabric":
                self.update_status("Loading Fabric")
                minecraft_launcher_lib.fabric.install_fabric(ver, GAME_DIR)
                for v in minecraft_launcher_lib.utils.get_installed_versions(GAME_DIR):
                    if "fabric-loader" in v['id'] and ver in v['id']: cid = v['id']; break
            
            # 5. Skin Pack sync
            if self.skin_path:
                self.update_status("Updating Skin")
                sr = os.path.join(GAME_DIR, "resourcepacks", "SkinPack")
                sd = os.path.join(sr, "assets", "minecraft", "textures", "entity", "player")
                os.makedirs(sd, exist_ok=True)
                with open(os.path.join(sr, "pack.mcmeta"), "w") as f: f.write('{"pack":{"pack_format":34,"description":""}}')
                for n in ["steve.png","alex.png","slim.png","wide.png"]: shutil.copy(self.skin_path, os.path.join(sd, n))

            # 6. Final Launch
            self.update_status("Launching")
            self.log("Handoff to Minecraft. Closing in 5s...")
            opt = {
                "username": "PortablePlayer",
                "uuid": "8667ba71-b85a-4004-af54-457a9734eed7",
                "token": "",
                "executablePath": java_exe,
                "jvmArguments": [f"-Duser.home={GAME_DIR}", f"-Xmx{alloc_ram}G"]
            }
            subprocess.Popen(minecraft_launcher_lib.command.get_minecraft_command(cid, GAME_DIR, opt))
            self.after(5000, self.destroy)
        except Exception as e: 
            self.log(f"CRITICAL ERROR: {e}")
            messagebox.showerror("Error", str(e))
        finally: 
            self.launch_btn.configure(state="normal", text="LAUNCH GAME")

if __name__ == "__main__":
    LauncherApp().mainloop()