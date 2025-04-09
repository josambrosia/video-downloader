import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk, ImageSequence
import requests
import yt_dlp
import threading
import os
import re
from io import BytesIO

def strip_ansi(text):
    ansi_escape = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')
    return ansi_escape.sub('', text)

# Fallback for PIL resampling filter (for compatibility)
try:
    RESAMPLING = Image.Resampling.LANCZOS
except AttributeError:
    RESAMPLING = Image.ANTIALIAS


class YTDL_GUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Video Downloader")
        self.geometry("600x600")
        self.configure(bg="#1e1e1e")
        self.resizable(False, False)

        self.DEFAULT_SAVE_PATH = os.path.expanduser("~\\Downloads")
        self.ffmpeg_path = os.path.join(os.getcwd(), "ffmpeg.exe")

        self.url = tk.StringVar()
        self.save_path = tk.StringVar(value=self.DEFAULT_SAVE_PATH)
        self.format_map = {}
        self.selected_format = tk.StringVar()
        self.progress = tk.DoubleVar()
        self.status_text = tk.StringVar(value="Idle")
        self.thumbnail_image = None
        self.video_title = tk.StringVar(value="")

        self.download_cancelled = threading.Event()

        self.spinner_label = None
        self.spinner_frames = []
        self.spinner_running = False

        self.set_dark_theme()
        self.create_frames()
        self.create_footer()
        self.show_frame("stage1")

        self.bind('<Return>', self.enter_key_pressed)

    def set_dark_theme(self):
        style = ttk.Style(self)
        self.tk_setPalette(background="#1e1e1e", foreground="#ffffff")
        style.theme_use("default")
        style.configure("TLabel", background="#1e1e1e", foreground="#ffffff")
        style.configure("TButton", background="#3b82f6", foreground="#ffffff")
        style.configure("TEntry", fieldbackground="#2d2d2d", foreground="#ffffff")
        style.configure("TCombobox", fieldbackground="#2d2d2d", foreground="#ffffff", background="#2d2d2d")

        style.layout("custom.Horizontal.TProgressbar",
                     [('Horizontal.Progressbar.trough',
                       {'children': [('Horizontal.Progressbar.pbar',
                                      {'side': 'left', 'sticky': 'ns'})],
                        'sticky': 'nswe'})])
        style.configure("custom.Horizontal.TProgressbar",
                        troughcolor="#2d2d2d",
                        background="#10b981",
                        thickness=20,
                        bordercolor="#1e1e1e",
                        lightcolor="#10b981",
                        darkcolor="#10b981")

    def create_frames(self):
        self.frames = {}

        # Stage 1: Input
        frame1 = tk.Frame(self, bg="#1e1e1e")
        frame1.place(relx=0.5, rely=0.5, anchor="center")
        self.frames["stage1"] = frame1

        tk.Label(frame1, text="Enter Video URL:", font=("Segoe UI", 12)).pack(pady=12)
        self.url_entry = tk.Entry(frame1, textvariable=self.url, width=45, font=("Segoe UI", 12),
                                  bg="#2d2d2d", fg="white")
        self.url_entry.pack(pady=12)
        self.url_entry.focus_set()

        self.fetch_btn = tk.Button(frame1, text="Fetch Video", command=self.fetch_formats_threaded)
        self.fetch_btn.pack(pady=12)

        self.spinner_label = tk.Label(frame1, bg="#1e1e1e")
        self.spinner_label.pack()

        self.fetch_status_label = tk.Label(frame1, text="", font=("Segoe UI", 10), bg="#1e1e1e", fg="#aaaaaa")
        self.fetch_status_label.pack(pady=(0, 5))

        self.load_spinner()

        # Stage 2: Info + Format
        frame2 = tk.Frame(self, bg="#1e1e1e")
        self.frames["stage2"] = frame2

        self.thumbnail_label = tk.Label(frame2, bg="#1e1e1e")
        self.thumbnail_label.pack(pady=(20, 10))

        self.title_label = tk.Label(frame2, textvariable=self.video_title, font=("Segoe UI", 9, "italic"),
                                    wraplength=500, justify="center", bg="#1e1e1e", fg="#bbbbbb")
        self.title_label.pack(pady=(0, 10))

        tk.Label(frame2, text="Select Format:", font=("Segoe UI", 10)).pack(pady=5)
        self.format_combo = ttk.Combobox(frame2, textvariable=self.selected_format, state="readonly", width=55)
        self.format_combo.pack(pady=5)

        path_frame = tk.Frame(frame2, bg="#1e1e1e")
        path_frame.pack(pady=5)
        self.path_entry = tk.Entry(path_frame, textvariable=self.save_path, width=40, bg="#2d2d2d", fg="white")
        self.path_entry.pack(side=tk.LEFT, padx=5)
        browse_btn = tk.Button(path_frame, text="Browse", command=self.choose_directory)
        browse_btn.pack(side=tk.LEFT)

        self.download_btn = tk.Button(frame2, text="Download", command=self.download_threaded,
                                      font=("Segoe UI", 10, "bold"), bg="#10b981", fg="white")
        self.download_btn.pack(pady=15)

        # Stage 3: Download Progress
        frame3 = tk.Frame(self, bg="#1e1e1e")
        self.frames["stage3"] = frame3

        tk.Label(frame3, text="Download Progress", font=("Segoe UI", 12)).pack(pady=15)
        ttk.Progressbar(frame3, variable=self.progress, maximum=100, length=400,
                        style="custom.Horizontal.TProgressbar").pack(pady=10)
        self.status_label = tk.Label(frame3, textvariable=self.status_text, font=("Courier", 9), bg="#1e1e1e")
        self.status_label.pack(pady=10)

        self.cancel_btn = tk.Button(frame3, text="Cancel", command=self.cancel_download,
                                    font=("Segoe UI", 9, "bold"), bg="#2d2d2d", fg="white")
        self.cancel_btn.pack(pady=5)

    def create_footer(self):
        self.footer_label = tk.Label(self, text="Developed by Josambrosia · Powered by ChatGPT",
                                     font=("Segoe UI", 10), fg="#000000", bg="#1e1e1e")
        self.footer_label.pack(side="bottom", pady=5)
        self.fade_in_footer()

    def fade_in_footer(self, step=0):
        max_step = 20
        start_rgb = (0, 0, 0)
        end_rgb = (136, 136, 136)

        def blend(start, end, t):
            return int(start + (end - start) * t)

        if step <= max_step:
            t = step / max_step
            r = blend(start_rgb[0], end_rgb[0], t)
            g = blend(start_rgb[1], end_rgb[1], t)
            b = blend(start_rgb[2], end_rgb[2], t)
            color = f'#{r:02x}{g:02x}{b:02x}'
            self.footer_label.config(fg=color)
            self.after(50, lambda: self.fade_in_footer(step + 1))

    def show_frame(self, stage):
        for f in self.frames.values():
            f.pack_forget()
        self.frames[stage].pack(expand=True)

    def reset_ui(self):
        self.url.set("")
        self.save_path.set(self.DEFAULT_SAVE_PATH)
        self.format_map.clear()
        self.selected_format.set("")
        self.progress.set(0)
        self.status_text.set("Idle")
        self.thumbnail_image = None
        self.video_title.set("")
        self.thumbnail_label.config(image="", text="")
        self.format_combo['values'] = []
        self.download_cancelled.clear()
        self.title("Video Downloader")
        self.fetch_status_label.config(text="")
        self.show_frame("stage1")

    def choose_directory(self):
        folder = filedialog.askdirectory()
        if folder:
            self.save_path.set(folder)

    def fetch_formats_threaded(self):
        self.fetch_status_label.config(text="Fetching video info...")
        self.start_spinner()
        threading.Thread(target=self.fetch_formats, daemon=True).start()

    def download_threaded(self):
        threading.Thread(target=self.download, daemon=True).start()

    def cancel_download(self):
        self.download_cancelled.set()
        self.status_text.set("Cancelling...")
        self.progress.set(0)
        self.show_frame("stage1")

    def fetch_formats(self):
        url = self.url.get().strip()
        if not url:
            self.stop_spinner()
            messagebox.showwarning("Input Error", "Please enter a video URL.")
            self.fetch_status_label.config(text="")
            return

        ydl_opts = {'quiet': True, 'skip_download': True}
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                self.show_thumbnail(info.get("thumbnail"))
                self.video_title.set(info.get("title", ""))

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
                        size_mb = f"{round(filesize / 1024 / 1024, 1)}MB" if filesize else "?"

                        label = f"{f_id} | {res} | {ext} | {fps}fps | {abr}kbps | {size_mb}"
                        self.format_map[label] = f_id
                        format_display_list.append(label)

                if format_display_list:
                    self.format_combo['values'] = format_display_list
                    self.format_combo.current(0)
                    self.show_frame("stage2")
                    self.format_combo.focus_set()
                else:
                    messagebox.showwarning("No Formats", "No downloadable formats found.")
                self.fetch_status_label.config(text="")
        except Exception as e:
            self.fetch_status_label.config(text="")
            messagebox.showerror("Error", f"Failed to fetch formats:\n{e}")
        finally:
            self.stop_spinner()

    def show_thumbnail(self, url):
        try:
            response = requests.get(url)
            img_data = BytesIO(response.content)
            image = Image.open(img_data)
            image.thumbnail((300, 180))
            self.thumbnail_image = ImageTk.PhotoImage(image)
            self.thumbnail_label.config(image=self.thumbnail_image, text="")
        except Exception:
            self.thumbnail_label.config(image="", text="No thumbnail available")

    def download(self):
        url = self.url.get().strip()
        format_label = self.selected_format.get()
        format_id = self.format_map.get(format_label)
        path = self.save_path.get().strip() or "."

        if not os.path.exists(self.ffmpeg_path):
            messagebox.showerror("FFmpeg Error", f"ffmpeg not found at:\n{self.ffmpeg_path}")
            return

        if not url or not format_id:
            messagebox.showwarning("Input Error", "Please select a format.")
            return

        ydl_opts = {
            'format': f'{format_id}+bestaudio/best',
            'outtmpl': os.path.join(path, '%(title)s.%(ext)s'),
            'quiet': True,
            'progress_hooks': [self.hook],
            'ffmpeg_location': self.ffmpeg_path,
            'merge_output_format': 'mp4',
            'windowsfilenames': True
        }

        self.progress.set(0)
        self.download_cancelled.clear()
        self.show_frame("stage3")
        try:
            self.set_status("Starting download...")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            if not self.download_cancelled.is_set():
                self.set_status("Download complete.")
                messagebox.showinfo("Done", "Download complete!")
            self.reset_ui()
        except Exception as e:
            if not self.download_cancelled.is_set():
                self.set_status("Failed")
                messagebox.showerror("Error", str(e))
            self.reset_ui()

    def hook(self, d):
        if self.download_cancelled.is_set():
            raise Exception("Download cancelled by user.")

        if d['status'] == 'downloading':
            percent = strip_ansi(d.get('_percent_str', '0.0%')).strip().replace('%', '')
            speed = strip_ansi(d.get('_speed_str', '0.0 KiB/s'))
            eta = d.get('_eta_str', '??')

            try:
                self.progress.set(float(percent))
            except ValueError:
                self.progress.set(0)

            self.set_status(f"{percent}% at {speed} | ETA: {eta}")
        elif d['status'] == 'finished':
            self.progress.set(100)
            self.set_status("Finalizing...")

    def set_status(self, msg):
        self.status_text.set(msg)
        self.title(f"Video Downloader - {msg}")

    def enter_key_pressed(self, event):
        widget = self.focus_get()
        if widget == self.url_entry:
            self.fetch_formats_threaded()
        elif widget == self.path_entry:
            self.download_threaded()
        elif widget == self.format_combo:
            self.download_btn.focus_set()
        elif widget == self.download_btn:
            self.download_threaded()

    def load_spinner(self):
        try:
            spinner_path = os.path.join(os.getcwd(), "spinner.gif")
            image = Image.open(spinner_path)
            self.spinner_frames = [ImageTk.PhotoImage(img.copy().resize((24, 24), RESAMPLING))
                                   for img in ImageSequence.Iterator(image)]
        except Exception as e:
            print(f"Failed to load spinner.gif: {e}")

    def start_spinner(self):
        self.spinner_running = True
        self.animate_spinner(0)

    def animate_spinner(self, index):
        if self.spinner_running and self.spinner_frames:
            frame = self.spinner_frames[index]
            self.spinner_label.config(image=frame)
            next_index = (index + 1) % len(self.spinner_frames)
            self.after(80, lambda: self.animate_spinner(next_index))
        else:
            self.spinner_label.config(image="")

    def stop_spinner(self):
        self.spinner_running = False


if __name__ == "__main__":
    app = YTDL_GUI()
    app.mainloop()
