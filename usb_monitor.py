import os
import time
import threading
import tkinter as tk
from tkinter import Listbox, messagebox, scrolledtext
import datetime
import sys
import shutil

try:
    import win32file
except ImportError:
    print("Win32 modules not found. Please install them using:")
    print("pip install pywin32")
    sys.exit(1)

try:
    from colorama import init, Fore, Style
    init()
    COLOR_SUPPORT = True
except ImportError:
    COLOR_SUPPORT = False

connected_drives = set()

def list_drives():
    drives = []
    bitmask = win32file.GetLogicalDrives()
    for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        if bitmask & 1:
            drives.append(f"{letter}:/")
        bitmask >>= 1
    return drives

def get_file_content(file_path, binary=False):
    try:
        mode = "rb" if binary else "r"
        with open(file_path, mode) as f:
            if binary:
                content = f"Binary file, size: {os.path.getsize(file_path)} bytes"
            else:
                content = f.read()
        return content
    except Exception as e:
        return f"Error reading file: {str(e)}"

def is_binary_file(file_path):
    try:
        with open(file_path, 'rb') as f:
            chunk = f.read(1024)
            return b'\0' in chunk
    except Exception:
        return True

def log(message, msg_type="INFO"):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if COLOR_SUPPORT:
        color = {
            "INFO": Fore.GREEN,
            "WARNING": Fore.YELLOW,
            "ERROR": Fore.RED,
            "CONNECT": Fore.CYAN,
            "DISCONNECT": Fore.MAGENTA
        }.get(msg_type, Fore.WHITE)
        print(f"{color}[{timestamp}] [{msg_type}] {message}{Style.RESET_ALL}")
    else:
        print(f"[{timestamp}] [{msg_type}] {message}")

def show_files_gui(drive_path):
    try:
        files = os.listdir(drive_path)
        log(f"Found {len(files)} files/folders on {drive_path}", "INFO")
    except Exception as e:
        log(f"Error reading drive {drive_path}: {e}", "ERROR")
        return

    window = tk.Tk()
    window.title(f"USB Contents - {drive_path}")
    window.geometry("800x600")

    list_frame = tk.Frame(window)
    list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=5, pady=5)

    content_frame = tk.Frame(window)
    content_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)

    path_label = tk.Label(list_frame, text=f"Drive: {drive_path}", font=("Arial", 10, "bold"))
    path_label.pack(anchor="w", pady=(0, 5))

    listbox = Listbox(list_frame, width=30)
    listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    scrollbar = tk.Scrollbar(list_frame)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    listbox.config(yscrollcommand=scrollbar.set)
    scrollbar.config(command=listbox.yview)

    content_label = tk.Label(content_frame, text="File Content:")
    content_label.pack(anchor="w")

    text_area = scrolledtext.ScrolledText(content_frame, wrap=tk.WORD)
    text_area.pack(fill=tk.BOTH, expand=True)

    for file in files:
        listbox.insert(tk.END, file)

    def on_select(event):
        if listbox.curselection():
            selected = listbox.get(listbox.curselection()[0])
            full_path = os.path.join(drive_path, selected)
            content_label.config(text=f"File: {selected}")
            if os.path.isdir(full_path):
                text_area.delete(1.0, tk.END)
                text_area.insert(tk.END, f"[Directory] {selected}\n\nContents:\n")
                try:
                    for item in os.listdir(full_path):
                        text_area.insert(tk.END, f"- {item}\n")
                except Exception as e:
                    text_area.insert(tk.END, f"Error listing directory: {str(e)}")
            else:
                is_binary = is_binary_file(full_path)
                content = get_file_content(full_path, binary=is_binary)
                text_area.delete(1.0, tk.END)
                text_area.insert(tk.END, content)
            log(f"Accessed: {full_path}", "INFO")

    listbox.bind('<<ListboxSelect>>', on_select)
    window.mainloop()

def monitor_usb():
    global connected_drives
    connected_drives = set(list_drives())
    log("Starting USB detection system...", "INFO")
    log(f"Currently connected drives: {', '.join(connected_drives) if connected_drives else 'None'}", "INFO")
    while True:
        time.sleep(1)
        current = set(list_drives())

        if current - connected_drives:
            new_drives = current - connected_drives
            for new_drive in new_drives:
                log(f"USB drive connected: {new_drive}", "CONNECT")
                try:
                    total, free = shutil.disk_usage(new_drive)[0::2]
                    log(f"Drive {new_drive} - Size: {total//(1024*3)}GB, Free: {free//(1024*3)}GB", "INFO")
                except Exception:
                    log(f"Could not get disk information for {new_drive}", "WARNING")
                threading.Thread(target=show_files_gui, args=(new_drive,)).start()

        if connected_drives - current:
            removed_drives = connected_drives - current
            for removed_drive in removed_drives:
                log(f"USB drive removed: {removed_drive}", "DISCONNECT")
                messagebox.showinfo("USB Removed", f"Drive {removed_drive} disconnected.")

        connected_drives = current

if _name_ == "_main_":
    try:
        log("USB Detector v1.0 starting...", "INFO")
        monitor_usb()
    except KeyboardInterrupt:
        log("Program terminated by user.", "INFO")
    except Exception as e:
        log(f"Unexpected error: {str(e)}", "ERROR")