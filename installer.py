import os
import sys
import shutil
import winshell
import ctypes
from win32com.client import Dispatch
import customtkinter as ctk
from tkinter import messagebox

# --- DPI FIX FOR CRISP TEXT ---
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except:
        pass

class SetupApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("PortableMC Setup")
        self.geometry("400x220")
        self.install_path = os.path.join(os.environ["LOCALAPPDATA"], "PortableMC")
        
        # Appearance
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("green")

        # --- ICON LOGIC ---
        # Looks for the icon in the same folder as the setup exe
        if getattr(sys, 'frozen', False):
            base_path = os.path.dirname(sys.executable)
        else:
            base_path = os.getcwd()
            
        icon_path = os.path.join(base_path, "logo.ico")
        if os.path.exists(icon_path):
            try:
                self.after(200, lambda: self.iconbitmap(icon_path))
            except:
                pass
        
        ctk.CTkLabel(self, text="PortableMC Installer", font=("Arial", 20, "bold")).pack(pady=20)
        self.status = ctk.CTkLabel(self, text="Ready to install...", font=("Arial", 10))
        self.status.pack()
        
        ctk.CTkButton(self, text="Install Now", command=self.install, fg_color="#238636", hover_color="#2ea043").pack(pady=20)

    def install(self):
        try:
            if not os.path.exists(self.install_path):
                os.makedirs(self.install_path)

            source = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.getcwd()
            
            # Junk filter
            ignore_list = [".git", ".gitignore", "setup", "installer.py", "launcher.py", "build", "__pycache__", "portablemc.spec"]

            for item in os.listdir(source):
                if any(x in item.lower() for x in ignore_list):
                    continue

                s = os.path.join(source, item)
                d = os.path.join(self.install_path, item)

                if os.path.isdir(s):
                    if os.path.exists(d): shutil.rmtree(d, ignore_errors=True)
                    shutil.copytree(s, d)
                else:
                    shutil.copy2(s, d)

            # Shortcut Logic
            desktop = winshell.desktop()
            path = os.path.join(desktop, "PortableMC.lnk")
            target = os.path.join(self.install_path, "PortableMC.exe")
            
            shell = Dispatch('WScript.Shell')
            shortcut = shell.CreateShortCut(path)
            shortcut.Targetpath = target
            shortcut.WorkingDirectory = self.install_path
            shortcut.IconLocation = target # Uses the launcher's icon
            shortcut.save()

            messagebox.showinfo("Success", "Installation Complete!\nYou can now use the Desktop shortcut.")
            self.destroy()
        except Exception as e: 
            messagebox.showerror("Installation Error", f"Error: {str(e)}")

if __name__ == "__main__":
    SetupApp().mainloop()