import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import requests
import yt_dlp
import threading
import os
import re
from io import BytesIO

def strip_ansi(text):
    ansi_escape = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')
    return ansi_escape.sub('', text)

class YTDL_GUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Video Downloader")
        self.geometry("900x700")
        self.configure(bg="#1e1e1e")

        self.url = tk.StringVar()
        self.save_path = tk.StringVar(value=os.getcwd())
        self.format_map = {}
        self.selected_format = tk.StringVar()
        self.progress = tk.DoubleVar()
        self.status_text = tk.StringVar(value="Idle")
        self.thumbnail_image = None

        self.create_widgets()
        self.set_dark_theme()

    def set_dark_theme(self):
        style = ttk.Style(self)
        self.tk_setPalette(background="#1e1e1e", foreground="#ffffff")
        style.theme_use("default")
        style.configure("TLabel", background="#1e1e1e", foreground="#ffffff")
        style.configure("TButton", background="#333333", foreground="#ffffff")
        style.configure("TEntry", fieldbackground="#2d2d2d", foreground="#ffffff")
        style.configure("TCombobox", fieldbackground="#2d2d2d", foreground="#ffffff", background="#2d2d2d")
        style.configure("TProgressbar", background="#3b82f6")

    def create_widgets(self):
        pad = {'padx': 10, 'pady': 6}

        tk.Label(self, text="Video URL:", font=("Segoe UI", 10), bg="#1e1e1e", fg="white").pack(**pad)
        tk.Entry(self, textvariable=self.url, width=90, font=("Segoe UI", 10), bg="#2d2d2d", fg="white", insertbackground="white").pack(**pad)

        tk.Button(self, text="Fetch Available Formats", command=self.fetch_formats_threaded, font=("Segoe UI", 10),
                  bg="#3b82f6", fg="white", activebackground="#2563eb").pack(**pad)

        self.thumbnail_label = tk.Label(self, bg="#1e1e1e")
        self.thumbnail_label.pack(pady=(10, 5))

        # Download button placed right under the thumbnail
        self.download_btn = tk.Button(self, text="Download Selected Format", command=self.download_threaded,
                                      font=("Segoe UI", 10), bg="#10b981", fg="white", activebackground="#059669")
        self.download_btn.pack(pady=10)

        tk.Label(self, text="Select Format:", bg="#1e1e1e", fg="white", font=("Segoe UI", 10)).pack(**pad)
        self.format_combo = ttk.Combobox(self, textvariable=self.selected_format, state="readonly", width=90)
        self.format_combo.pack(**pad)

        tk.Label(self, text="Save to Folder:", bg="#1e1e1e", fg="white", font=("Segoe UI", 10)).pack(**pad)
        path_frame = tk.Frame(self, bg="#1e1e1e")
        path_frame.pack()
        tk.Entry(path_frame, textvariable=self.save_path, width=65, bg="#2d2d2d", fg="white", insertbackground="white").pack(side=tk.LEFT, padx=5)
        tk.Button(path_frame, text="Browse", command=self.choose_directory, bg="#3b82f6", fg="white", activebackground="#2563eb").pack(side=tk.LEFT)

        tk.Label(self, text="Download Progress:", bg="#1e1e1e", fg="white", font=("Segoe UI", 10)).pack(pady=(20, 0))
        ttk.Progressbar(self, variable=self.progress, maximum=100, length=750).pack(pady=5)

        self.status_label = tk.Label(self, textvariable=self.status_text, font=("Courier", 10), bg="#1e1e1e", fg="white")
        self.status_label.pack()

    def choose_directory(self):
        folder = filedialog.askdirectory()
        if folder:
            self.save_path.set(folder)

    def fetch_formats(self):
        url = self.url.get().strip()
        if not url:
            messagebox.showwarning("Input Error", "Please enter a video URL.")
            return

        ydl_opts = {'quiet': True, 'skip_download': True}
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                self.show_thumbnail(info.get("thumbnail"))

                formats = info.get("formats", [])
                self.format_map.clear()
                format_display_list = []

                for f in formats:
                    if f.get("vcodec") != "none" or f.get("acodec") != "none":
                        f_id = f["format_id"]
                        ext = f["ext"]
                        res = f.get("resolution") or f.get("height") or "audio"
                        fps = f.get("fps", "")
                        abr = f.get("abr", "")
                        filesize = f.get("filesize") or f.get("filesize_approx")
                        size_mb = f"{round(filesize/1024/1024, 1)}MB" if filesize else "?"

                        label = f"{f_id} | {res} | {ext} | {fps}fps | {abr}kbps | {size_mb}"
                        self.format_map[label] = f_id
                        format_display_list.append(label)

                if format_display_list:
                    self.format_combo['values'] = format_display_list
                    self.format_combo.current(0)
                    messagebox.showinfo("Formats Found", "Available formats loaded.")
                else:
                    messagebox.showwarning("No Formats", "No downloadable formats found.")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to fetch formats:\n{e}")

    def show_thumbnail(self, url):
        try:
            response = requests.get(url)
            img_data = BytesIO(response.content)
            image = Image.open(img_data)
            image.thumbnail((360, 202))  # Smaller thumbnail
            self.thumbnail_image = ImageTk.PhotoImage(image)
            self.thumbnail_label.config(image=self.thumbnail_image)
            self.update_idletasks()
        except Exception:
            self.thumbnail_label.config(image="", text="No thumbnail available")

    def download(self):
        url = self.url.get().strip()
        format_label = self.selected_format.get()
        format_id = self.format_map.get(format_label)
        path = self.save_path.get().strip() or "."

        ffmpeg_path = r"D:\Software Dependency (Installer)\ffmpeg-2025-03-31-git-35c091f4b7-essentials_build\bin"  # Replace this path with your actual ffmpeg location

        if not os.path.exists(ffmpeg_path):
            messagebox.showerror("FFmpeg Error", f"ffmpeg not found at:\n{ffmpeg_path}")
            return

        if not url or not format_id:
            messagebox.showwarning("Input Error", "Please select a format.")
            return

        ydl_opts = {
            'format': f'{format_id}+bestaudio/best',
            'outtmpl': os.path.join(path, '%(title)s.%(ext)s'),
            'quiet': True,
            'progress_hooks': [self.hook],
            'ffmpeg_location': ffmpeg_path,
            'merge_output_format': 'mp4',
        }

        try:
            self.set_status("Starting download...")
            self.progress.set(0)
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            self.set_status("Download complete.")
            messagebox.showinfo("Done", "Download complete!")
        except Exception as e:
            messagebox.showerror("Error", str(e))
            self.set_status("Failed")

    def hook(self, d):
        if d['status'] == 'downloading':
            percent_raw = d.get('_percent_str', '0.0%')
            speed_raw = d.get('_speed_str', '0.0 KiB/s')
            eta = d.get('_eta_str', '??')

            percent_clean = strip_ansi(percent_raw).strip().replace('%', '')
            speed_clean = strip_ansi(speed_raw)

            try:
                self.progress.set(float(percent_clean))
            except ValueError:
                self.progress.set(0)

            self.set_status(f"{percent_clean}% at {speed_clean} | ETA: {eta}")

        elif d['status'] == 'finished':
            self.progress.set(100)
            self.set_status("Finalizing...")

    def set_status(self, msg):
        self.status_text.set(msg)
        self.title(f"Video Downloader - {msg}")

    def fetch_formats_threaded(self):
        threading.Thread(target=self.fetch_formats).start()

    def download_threaded(self):
        threading.Thread(target=self.download).start()

if __name__ == "__main__":
    app = YTDL_GUI()
    app.mainloop()
