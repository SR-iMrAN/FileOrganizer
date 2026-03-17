import os
import time
import shutil
import threading
import webbrowser
import customtkinter as ctk
from tkinter import messagebox, filedialog
import tkinter as tk
import pystray
from PIL import Image, ImageDraw
import sys
import requests

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ---------- VERSION ----------
CURRENT_VERSION = "1.1"
VERSION_URL = "https://raw.githubusercontent.com/SR-iMrAN/FileOrganizer/main/version.txt"
UPDATE_URL = "https://github.com/SR-iMrAN/FileOrganizer/releases/download/v1.2/SmartSort.exe"

# ---------- CONFIG ----------
CONFIG_FILE = "config.txt"
selected_path = os.path.join(os.path.expanduser("~"), "Downloads")

if os.path.exists(CONFIG_FILE):
    try:
        with open(CONFIG_FILE, "r") as f:
            selected_path = f.read()
    except:
        pass

running = False
tray_icon = None

# ---------- SPLASH ----------
def show_splash():
    splash = tk.Tk()
    splash.overrideredirect(True)
    splash.geometry("400x200+500+300")
    splash.configure(bg="#111")

    tk.Label(splash, text="SmartSort", fg="white", bg="#111",
             font=("Segoe UI", 26, "bold")).pack(expand=True)

    for i in range(0, 11):
        splash.attributes("-alpha", i * 0.1)
        splash.update()
        time.sleep(0.04)

    time.sleep(0.8)

    for i in range(10, -1, -1):
        splash.attributes("-alpha", i * 0.1)
        splash.update()
        time.sleep(0.04)

    splash.destroy()

# ---------- VERSION FIX ----------
def version_tuple(v):
    return tuple(map(int, v.split(".")))

# ---------- UPDATE ----------
def check_update(auto=False):
    try:
        res = requests.get(VERSION_URL, headers={"User-Agent": "Mozilla/5.0"})
        text = res.text.strip()

        if "<" in text:
            return

        if version_tuple(text) > version_tuple(CURRENT_VERSION):
            if messagebox.askyesno("Update", f"New version {text} available. Update now?"):
                download_update()
        else:
            if not auto:
                messagebox.showinfo("Update", "You are using latest version.")
    except:
        if not auto:
            messagebox.showerror("Error", "Update check failed")

def download_update():
    try:
        exe_dir = os.path.dirname(sys.executable)
        current_exe = sys.executable

        new_exe = os.path.join(exe_dir, "SmartSort_new.exe")
        final_exe = os.path.join(exe_dir, "SmartSort.exe")

        data = requests.get(UPDATE_URL).content
        with open(new_exe, "wb") as f:
            f.write(data)

        updater = os.path.join(exe_dir, "update.bat")

        with open(updater, "w") as f:
            f.write(f"""
@echo off
timeout /t 2 >nul
del "{current_exe}"
rename "{new_exe}" "SmartSort.exe"
start "" "{final_exe}"
del "%~f0"
""")

        messagebox.showinfo("Update", "Updating... restarting app")

        os.startfile(updater)
        app.destroy()

    except Exception as e:
        messagebox.showerror("Error", str(e))

def auto_check():
    time.sleep(3)
    check_update(auto=True)

# ---------- FILE LOGIC ----------
def get_folder(ext):
    ext = ext.lower().replace(".", "")
    if ext in ["jpg", "jpeg", "png", "gif"]:
        return os.path.join("Images", ext.upper())
    return ext.upper() if ext else "Others"

def move_file(file_path, file_name):
    ext = os.path.splitext(file_name)[1]
    folder = get_folder(ext)

    target = os.path.join(selected_path, folder)
    os.makedirs(target, exist_ok=True)

    try:
        shutil.move(file_path, os.path.join(target, file_name))
    except:
        pass

def loop():
    global running
    while running:
        for f in os.listdir(selected_path):
            path = os.path.join(selected_path, f)

            if os.path.isfile(path):
                try:
                    size1 = os.path.getsize(path)
                    time.sleep(0.2)
                    size2 = os.path.getsize(path)

                    if size1 == size2:
                        move_file(path, f)
                except:
                    pass

        time.sleep(5)

# ---------- CONTROLS ----------
def start():
    global running
    if running:
        messagebox.showinfo("Info", "Already Running")
        return

    running = True
    threading.Thread(target=loop, daemon=True).start()
    status_label.configure(text="Running", text_color="#00ff99")

def stop():
    global running
    running = False
    status_label.configure(text="Stopped", text_color="red")

# ---------- STARTUP ----------
def add_startup():
    import winshell
    from win32com.client import Dispatch

    startup = winshell.startup()
    exe_path = sys.executable
    shortcut = os.path.join(startup, "SmartSort.lnk")

    if os.path.exists(shortcut):
        messagebox.showinfo("Startup", "Already Added!")
        return

    shell = Dispatch('WScript.Shell')
    sc = shell.CreateShortCut(shortcut)
    sc.Targetpath = exe_path
    sc.Arguments = "--startup"
    sc.WorkingDirectory = os.path.dirname(exe_path)
    sc.save()

    messagebox.showinfo("Startup", "Added Successfully")

def auto_start_if_needed():
    global running
    if "--startup" in sys.argv:
        running = True
        threading.Thread(target=loop, daemon=True).start()
        hide_window()

# ---------- FOLDER ----------
def choose_folder():
    global selected_path
    path = filedialog.askdirectory()

    if path:
        selected_path = path
        path_label.configure(text=selected_path)

        with open(CONFIG_FILE, "w") as f:
            f.write(selected_path)

# ---------- WEBSITE ----------
def open_site():
    webbrowser.open("https://sr-imran.github.io/sri/")

# ---------- TRAY ----------
def create_image():
    image = Image.new('RGB', (64, 64), color=(0, 0, 0))
    d = ImageDraw.Draw(image)
    d.rectangle((10, 10, 54, 54), fill=(0, 200, 100))
    return image

def show_window(icon=None, item=None):
    app.after(0, app.deiconify)

def quit_app(icon, item):
    global running
    running = False
    icon.stop()
    app.destroy()

def hide_window():
    global tray_icon

    app.withdraw()

    if tray_icon:
        return

    tray_icon = pystray.Icon(
        "SmartSort",
        create_image(),
        "SmartSort",
        menu=pystray.Menu(
            pystray.MenuItem("Open", show_window),
            pystray.MenuItem("Exit", quit_app)
        )
    )

    threading.Thread(target=tray_icon.run, daemon=True).start()

# ---------- START ----------
if "--startup" not in sys.argv:
    show_splash()

# ---------- UI ----------
app = ctk.CTk()
app.title("SmartSort Organizer")
app.geometry("450x550")
app.protocol("WM_DELETE_WINDOW", hide_window)

ctk.CTkLabel(app, text="SmartSort", font=("Arial", 24, "bold")).pack(pady=10)

status_label = ctk.CTkLabel(app, text="Stopped", text_color="red")
status_label.pack(pady=5)

ctk.CTkButton(app, text="Start", command=start).pack(pady=10)
ctk.CTkButton(app, text="Stop", command=stop, fg_color="#cc3333").pack(pady=5)

path_label = ctk.CTkLabel(app, text=selected_path, wraplength=400)
path_label.pack(pady=10)

ctk.CTkButton(app, text="Select Folder", command=choose_folder).pack(pady=5)
ctk.CTkButton(app, text="Add to Startup", command=add_startup).pack(pady=10)
ctk.CTkButton(app, text="Check for Updates", command=check_update).pack(pady=5)

footer = ctk.CTkLabel(app, text="© SR Imran", text_color="cyan", cursor="hand2")
footer.pack(side="bottom", pady=10)
footer.bind("<Button-1>", lambda e: open_site())

threading.Thread(target=auto_check, daemon=True).start()

auto_start_if_needed()

app.mainloop()