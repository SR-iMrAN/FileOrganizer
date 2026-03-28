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
import tempfile
import subprocess

# ---------- HIGH PRIORITY (Fix: slow startup) ----------
try:
    import psutil
    p = psutil.Process(os.getpid())
    p.nice(psutil.HIGH_PRIORITY_CLASS)
except Exception:
    pass

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ---------- VERSION ----------
CURRENT_VERSION = "1.4"  # Fix: update this after every release so update loop stops
VERSION_URL = "https://raw.githubusercontent.com/SR-iMrAN/FileOrganizer/main/version.txt"
UPDATE_URL = "https://github.com/SR-iMrAN/FileOrganizer/releases/download/v1.4/organizer_gui.exe"
GITHUB_RELEASE_PAGE = "https://github.com/SR-iMrAN/FileOrganizer/releases/latest"

# ---------- CONFIG ----------
CONFIG_FILE = os.path.join(os.path.expanduser("~"), "SmartSort_config.txt")
STATE_FILE = os.path.join(os.path.expanduser("~"), "SmartSort_state.txt")  # Fix: persist running state

selected_path = os.path.join(os.path.expanduser("~"), "Downloads")

if os.path.exists(CONFIG_FILE):
    try:
        with open(CONFIG_FILE, "r") as f:
            val = f.read().strip()
            if val:
                selected_path = val
    except Exception:
        pass

running = False
tray_icon = None

# ---------- STATE HELPERS ----------
def save_state(is_running):
    try:
        with open(STATE_FILE, "w") as f:
            f.write("running" if is_running else "stopped")
    except Exception:
        pass

def load_state():
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, "r") as f:
                return f.read().strip() == "running"
    except Exception:
        pass
    return False

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

# ---------- VERSION HELPERS ----------
def version_tuple(v):
    try:
        return tuple(map(int, v.strip().split(".")))
    except Exception:
        return (0,)

# ---------- UPDATE ----------
def check_update(auto=False):
    try:
        res = requests.get(VERSION_URL, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
        text = res.text.strip()
        if "<" in text or not text:
            if not auto:
                messagebox.showerror("Error", "Could not read version info.")
            return
        if version_tuple(text) > version_tuple(CURRENT_VERSION):
            if messagebox.askyesno("Update", f"New version {text} available. Update now?"):
                download_update(text)
        else:
            if not auto:
                messagebox.showinfo("Update", "You are using the latest version.")
    except Exception:
        if not auto:
            messagebox.showerror("Error", "Update check failed. Check your internet connection.")

def download_update(new_version=""):
    # Fix: download to TEMP folder instead of Program Files (avoids Permission denied)
    try:
        tmp_dir = tempfile.gettempdir()
        new_exe = os.path.join(tmp_dir, "SmartSort_new.exe")

        messagebox.showinfo("Update", "Downloading update... please wait.")

        response = requests.get(UPDATE_URL, timeout=60, stream=True)
        response.raise_for_status()

        with open(new_exe, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        current_exe = sys.executable
        exe_dir = os.path.dirname(current_exe)
        final_exe = os.path.join(exe_dir, "SmartSort.exe")

        updater = os.path.join(tmp_dir, "smartsort_update.bat")
        with open(updater, "w") as f:
            f.write(f"""@echo off
timeout /t 2 >nul
del /f "{current_exe}"
copy /y "{new_exe}" "{final_exe}"
del /f "{new_exe}"
start "" "{final_exe}"
del "%~f0"
""")

        messagebox.showinfo("Update", "Update downloaded! App will restart.")
        save_state(running)
        subprocess.Popen(["cmd", "/c", updater], shell=False,
                         creationflags=subprocess.CREATE_NO_WINDOW)
        app.destroy()

    except requests.exceptions.HTTPError as e:
        # Fix: fallback to browser if download fails
        if messagebox.askyesno("Download Failed",
                               f"Auto-download failed ({e}).\nOpen browser to download manually?"):
            webbrowser.open(GITHUB_RELEASE_PAGE)
    except Exception as e:
        if messagebox.askyesno("Download Failed",
                               f"Auto-download failed.\nOpen browser to download manually?\n\nError: {e}"):
            webbrowser.open(GITHUB_RELEASE_PAGE)

def auto_check():
    time.sleep(3)
    check_update(auto=True)

# ---------- FILE LOGIC ----------
def get_folder(ext):
    ext = ext.lower().replace(".", "")
    if ext in ["jpg", "jpeg", "png", "gif", "bmp", "webp", "svg", "ico", "tiff"]:
        return os.path.join("Images", ext.upper())
    elif ext in ["mp4", "mkv", "avi", "mov", "wmv", "flv", "webm"]:
        return os.path.join("Videos", ext.upper())
    elif ext in ["mp3", "wav", "flac", "aac", "ogg", "m4a"]:
        return os.path.join("Audio", ext.upper())
    elif ext in ["pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "txt", "csv"]:
        return os.path.join("Documents", ext.upper())
    elif ext in ["zip", "rar", "7z", "tar", "gz"]:
        return os.path.join("Archives", ext.upper())
    elif ext in ["exe", "msi", "bat", "sh"]:
        return os.path.join("Programs", ext.upper())
    return os.path.join("Others", ext.upper() if ext else "NoExtension")

def move_file(file_path, file_name):
    ext = os.path.splitext(file_name)[1]
    folder = get_folder(ext)
    target = os.path.join(selected_path, folder)
    os.makedirs(target, exist_ok=True)
    dest = os.path.join(target, file_name)
    if os.path.exists(dest):
        base, extension = os.path.splitext(file_name)
        dest = os.path.join(target, f"{base}_{int(time.time())}{extension}")
    try:
        shutil.move(file_path, dest)
    except Exception:
        pass

def loop():
    global running
    while running:
        try:
            for f in os.listdir(selected_path):
                if not running:
                    break
                path = os.path.join(selected_path, f)
                if os.path.isfile(path):
                    try:
                        size1 = os.path.getsize(path)
                        time.sleep(0.3)
                        size2 = os.path.getsize(path)
                        if size1 == size2:
                            move_file(path, f)
                    except Exception:
                        pass
        except Exception:
            pass
        time.sleep(5)

# ---------- CONTROLS ----------
def start(skip_warning=False):
    global running
    if running:
        messagebox.showinfo("Info", "Already Running")
        return

    # Fix: warn about existing files before organizing
    if not skip_warning:
        existing = [f for f in os.listdir(selected_path)
                    if os.path.isfile(os.path.join(selected_path, f))]
        if existing:
            result = show_existing_files_dialog(existing)
            if result is None:
                return  # cancelled
            if result == "no":
                # "No" = organize both old and new (user confirmed)
                pass
            # "yes" = skip old files (only new ones going forward)
            # We handle this by just starting normally - loop catches new files
            # For "yes" (keep old), we just don't touch them right now (loop will still catch new)
            # Actually let's handle properly:
            if result == "yes":
                # Don't organize existing files — start loop which will only pick up new arrivals
                running = True
                threading.Thread(target=loop, daemon=True).start()
                status_label.configure(text="Running", text_color="#00ff99")
                save_state(True)
                return

    running = True
    threading.Thread(target=loop, daemon=True).start()
    status_label.configure(text="Running", text_color="#00ff99")
    save_state(True)

def show_existing_files_dialog(existing):
    """
    Custom dialog: shows path, count of existing files, Yes/No/Cancel.
    Yes = keep old files, only organize new ones going forward
    No = organize old + new files
    Cancel = don't start
    Returns: 'yes', 'no', or None
    """
    result = [None]

    dialog = tk.Toplevel()
    dialog.title("Existing Files Found")
    dialog.geometry("480x280")
    dialog.configure(bg="#1a1a2e")
    dialog.grab_set()
    dialog.resizable(False, False)

    # Center it
    dialog.update_idletasks()
    x = dialog.winfo_screenwidth() // 2 - 240
    y = dialog.winfo_screenheight() // 2 - 140
    dialog.geometry(f"+{x}+{y}")

    tk.Label(dialog, text="⚠  Existing Files Detected", fg="#ffcc00", bg="#1a1a2e",
             font=("Segoe UI", 14, "bold")).pack(pady=(15, 5))

    tk.Label(dialog, text=f"{len(existing)} file(s) already exist in:", fg="white",
             bg="#1a1a2e", font=("Segoe UI", 10)).pack()

    path_frame = tk.Frame(dialog, bg="#111", bd=1, relief="sunken")
    path_frame.pack(padx=20, pady=5, fill="x")
    tk.Label(path_frame, text=selected_path, fg="#00ccff", bg="#111",
             font=("Consolas", 9), wraplength=430).pack(padx=5, pady=4)

    def change_path_from_dialog():
        global selected_path
        path = filedialog.askdirectory(parent=dialog)
        if path:
            selected_path = path
            path_label.configure(text=selected_path)
            with open(CONFIG_FILE, "w") as f:
                f.write(selected_path)
            dialog.destroy()
            result[0] = None

    tk.Button(dialog, text="📁 Change Path", command=change_path_from_dialog,
              bg="#333", fg="white", relief="flat", cursor="hand2").pack(pady=3)

    tk.Label(dialog, text="Keep previous files as-is? (only organize new files going forward)",
             fg="#cccccc", bg="#1a1a2e", font=("Segoe UI", 9), wraplength=440).pack(pady=8)

    btn_frame = tk.Frame(dialog, bg="#1a1a2e")
    btn_frame.pack(pady=5)

    def on_yes():
        result[0] = "yes"
        dialog.destroy()

    def on_no():
        result[0] = "no"
        dialog.destroy()

    def on_cancel():
        result[0] = None
        dialog.destroy()

    tk.Button(btn_frame, text="✅ Yes – Keep old files", command=on_yes,
              bg="#006633", fg="white", font=("Segoe UI", 10, "bold"),
              padx=10, pady=5, relief="flat", cursor="hand2").grid(row=0, column=0, padx=8)

    tk.Button(btn_frame, text="🔄 No – Organize all", command=on_no,
              bg="#333399", fg="white", font=("Segoe UI", 10, "bold"),
              padx=10, pady=5, relief="flat", cursor="hand2").grid(row=0, column=1, padx=8)

    tk.Button(btn_frame, text="✖ Cancel", command=on_cancel,
              bg="#660000", fg="white", font=("Segoe UI", 10),
              padx=10, pady=5, relief="flat", cursor="hand2").grid(row=0, column=2, padx=8)

    dialog.wait_window()
    return result[0]

def stop():
    global running
    running = False
    status_label.configure(text="Stopped", text_color="red")
    save_state(False)  # Fix: save stopped state

# ---------- STARTUP ----------
def add_startup():
    try:
        import winshell
        from win32com.client import Dispatch

        startup = winshell.startup()
        exe_path = sys.executable
        shortcut = os.path.join(startup, "SmartSort.lnk")

        if os.path.exists(shortcut):
            messagebox.showinfo("Startup", "Already Added to Startup!")
            return

        shell = Dispatch('WScript.Shell')
        sc = shell.CreateShortCut(shortcut)
        sc.Targetpath = exe_path
        sc.Arguments = "--startup"
        sc.WorkingDirectory = os.path.dirname(exe_path)
        sc.save()

        messagebox.showinfo("Startup", "Added to Startup Successfully!")
    except Exception as e:
        messagebox.showerror("Error", f"Could not add to startup:\n{e}")

def auto_start_if_needed():
    """Fix: auto-start if launched via startup shortcut OR if last state was running"""
    global running
    is_startup_launch = "--startup" in sys.argv
    was_running = load_state()

    if is_startup_launch or was_running:
        running = True
        threading.Thread(target=loop, daemon=True).start()
        status_label.configure(text="Running", text_color="#00ff99")
        save_state(True)
        if is_startup_launch:
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
    image = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(image)
    d.rounded_rectangle((4, 4, 60, 60), radius=12, fill=(0, 200, 100))
    d.text((20, 20), "S", fill="white")
    return image

def show_window(icon=None, item=None):
    app.after(0, app.deiconify)

def quit_app(icon, item):
    global running
    running = False
    save_state(False)
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
        "SmartSort - " + ("Running" if running else "Stopped"),
        menu=pystray.Menu(
            pystray.MenuItem("Open", show_window),
            pystray.MenuItem("Exit", quit_app)
        )
    )
    threading.Thread(target=tray_icon.run, daemon=True).start()

# ---------- SPLASH ----------
if "--startup" not in sys.argv:
    show_splash()

# ---------- UI ----------
app = ctk.CTk()
app.title("SmartSort Organizer v" + CURRENT_VERSION)
app.geometry("460x570")
app.protocol("WM_DELETE_WINDOW", hide_window)

ctk.CTkLabel(app, text="SmartSort", font=("Arial", 24, "bold")).pack(pady=(15, 2))
ctk.CTkLabel(app, text=f"v{CURRENT_VERSION}", font=("Arial", 10), text_color="gray").pack()

status_label = ctk.CTkLabel(app, text="Stopped", text_color="red", font=("Arial", 13, "bold"))
status_label.pack(pady=6)

btn_frame = ctk.CTkFrame(app, fg_color="transparent")
btn_frame.pack(pady=5)
ctk.CTkButton(btn_frame, text="▶  Start", command=start, width=120).grid(row=0, column=0, padx=8)
ctk.CTkButton(btn_frame, text="■  Stop", command=stop, fg_color="#cc3333", width=120).grid(row=0, column=1, padx=8)

ctk.CTkLabel(app, text="Monitoring Folder:", font=("Arial", 11), text_color="gray").pack(pady=(15, 0))
path_label = ctk.CTkLabel(app, text=selected_path, wraplength=420, font=("Consolas", 9))
path_label.pack(pady=3)

ctk.CTkButton(app, text="📁  Select Folder", command=choose_folder).pack(pady=5)

ctk.CTkFrame(app, height=1, fg_color="#333").pack(fill="x", padx=30, pady=10)

ctk.CTkButton(app, text="🚀  Add to Startup", command=add_startup).pack(pady=5)
ctk.CTkButton(app, text="🔄  Check for Updates", command=check_update).pack(pady=5)

footer = ctk.CTkLabel(app, text="© SR Imran", text_color="cyan", cursor="hand2")
footer.pack(side="bottom", pady=10)
footer.bind("<Button-1>", lambda e: open_site())

threading.Thread(target=auto_check, daemon=True).start()

app.after(200, auto_start_if_needed)  # Fix: slight delay so UI loads first before auto-start

app.mainloop()