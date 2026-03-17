import os
import time
import shutil
import threading
import webbrowser
import customtkinter as ctk
from tkinter import messagebox

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

DOWNLOADS_PATH = os.path.join(os.path.expanduser("~"), "Downloads")
running = False

def get_folder(ext):
    ext = ext.lower().replace(".", "")
    if ext in ["jpg", "jpeg", "png", "gif"]:
        return os.path.join("Images", ext.upper())
    return ext.upper() if ext else "Others"

def move_file(file_path, file_name):
    ext = os.path.splitext(file_name)[1]
    folder = get_folder(ext)

    target = os.path.join(DOWNLOADS_PATH, folder)

    if date_var.get():
        from datetime import datetime
        now = datetime.now()
        target = os.path.join(target, str(now.year), str(now.month))

    os.makedirs(target, exist_ok=True)

    try:
        shutil.move(file_path, os.path.join(target, file_name))
    except:
        pass

def loop():
    global running
    while running:
        for f in os.listdir(DOWNLOADS_PATH):
            path = os.path.join(DOWNLOADS_PATH, f)
            if os.path.isfile(path):
                move_file(path, f)
        time.sleep(5)

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

def open_site():
    webbrowser.open("https://sr-imran.github.io/sri/")

# ---------- UI ----------
app = ctk.CTk()
app.title("SmartSort Organizer")
app.geometry("420x420")

title = ctk.CTkLabel(app, text="SmartSort", font=("Arial", 24, "bold"))
title.pack(pady=10)

status_label = ctk.CTkLabel(app, text="Stopped", text_color="red", font=("Arial", 14))
status_label.pack(pady=5)

start_btn = ctk.CTkButton(app, text="Start", command=start)
start_btn.pack(pady=10)

stop_btn = ctk.CTkButton(app, text="Stop", command=stop, fg_color="#cc3333")
stop_btn.pack(pady=5)

date_var = ctk.BooleanVar()
date_check = ctk.CTkCheckBox(app, text="Sort by Date", variable=date_var)
date_check.pack(pady=10)

startup_btn = ctk.CTkButton(app, text="Add to Startup")
startup_btn.pack(pady=10)

footer = ctk.CTkLabel(app, text="© SR Imran", text_color="cyan", cursor="hand2")
footer.pack(side="bottom", pady=10)
footer.bind("<Button-1>", lambda e: open_site())

app.mainloop()