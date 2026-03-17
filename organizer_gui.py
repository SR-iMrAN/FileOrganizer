import os
import time
import shutil
import threading
import webbrowser
import customtkinter as ctk
from tkinter import messagebox, filedialog
import pystray
from PIL import Image, ImageDraw
import sys
import requests

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ---------- VERSION ----------
CURRENT_VERSION = "1.0"
VERSION_URL = "https://raw.githubusercontent.com/SR-iMrAN/FileOrganizer/blob/main/version.txt"

UPDATE_URL = "https://github.com/SR-iMrAN/FileOrganizer/releases/download/v1.0/SmartSort.exe"

# ---------- CONFIG ----------
CONFIG_FILE = "config.txt"

if os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, "r") as f:
        selected_path = f.read()
else:
    selected_path = os.path.join(os.path.expanduser("~"), "Downloads")

running = False

# ---------- UPDATE SYSTEM ----------
def check_update(auto=False):
    try:
        latest = requests.get(VERSION_URL).text.strip()

        if latest > CURRENT_VERSION:
            if auto:
                res = messagebox.askyesno("Update", f"New version {latest} available. Update now?")
            else:
                res = messagebox.askyesno("Update", f"New version {latest} available. Update now?")

            if res:
                download_update()
        else:
            if not auto:
                messagebox.showinfo("Update", "You are using latest version.")
    except:
        if not auto:
            messagebox.showerror("Error", "Could not check updates")

def download_update():
    try:
        data = requests.get(UPDATE_URL).content

        new_file = os.path.join(os.getcwd(), "SmartSort_new.exe")

        with open(new_file, "wb") as f:
            f.write(data)

        messagebox.showinfo("Update", "Update downloaded! Replace old file and restart.")
    except:
        messagebox.showerror("Error", "Download failed")

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
                move_file(path, f)
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

# ---------- FOLDER SELECT ----------
def choose_folder():
    global selected_path
    path = filedialog.askdirectory()
    if path:
        selected_path = path
        path_label.configure(text=selected_path)

        with open(CONFIG_FILE, "w") as f:
            f.write(selected_path)

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
    sc.WorkingDirectory = os.path.dirname(exe_path)
    sc.save()

    messagebox.showinfo("Startup", "Added Successfully")

# ---------- WEBSITE ----------
def open_site():
    webbrowser.open("https://sr-imran.github.io/sri/")

# ---------- SYSTEM TRAY ----------
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
    app.withdraw()

    icon = pystray.Icon(
        "SmartSort",
        create_image(),
        "SmartSort",
        menu=pystray.Menu(
            pystray.MenuItem("Open", show_window),
            pystray.MenuItem("Exit", quit_app)
        )
    )

    threading.Thread(target=icon.run, daemon=True).start()

# ---------- UI ----------
app = ctk.CTk()
app.title("SmartSort Organizer")
app.geometry("450x550")

app.protocol("WM_DELETE_WINDOW", hide_window)

title = ctk.CTkLabel(app, text="SmartSort", font=("Arial", 24, "bold"))
title.pack(pady=10)

status_label = ctk.CTkLabel(app, text="Stopped", text_color="red", font=("Arial", 14))
status_label.pack(pady=5)

ctk.CTkButton(app, text="Start", command=start).pack(pady=10)
ctk.CTkButton(app, text="Stop", command=stop, fg_color="#cc3333").pack(pady=5)

path_label = ctk.CTkLabel(app, text=selected_path, wraplength=400)
path_label.pack(pady=10)

ctk.CTkButton(app, text="Select Folder", command=choose_folder).pack(pady=5)
ctk.CTkButton(app, text="Add to Startup", command=add_startup).pack(pady=10)

# 🔥 NEW UPDATE BUTTON
ctk.CTkButton(app, text="Check for Updates", command=check_update).pack(pady=5)

footer = ctk.CTkLabel(app, text="© SR Imran", text_color="cyan", cursor="hand2")
footer.pack(side="bottom", pady=10)
footer.bind("<Button-1>", lambda e: open_site())

# 🔥 AUTO UPDATE CHECK (BACKGROUND)
threading.Thread(target=auto_check, daemon=True).start()

app.mainloop()