import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pytube import YouTube
import threading

class YouTubeDownloader(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("YouTube Video Downloader")
        self.geometry("500x300")
        self.resizable(False, False)

        self.video = None
        self.streams = []

        self.create_widgets()

    def create_widgets(self):
        # URL input
        tk.Label(self, text="YouTube Video URL:").pack(pady=5)
        self.url_entry = tk.Entry(self, width=60)
        self.url_entry.pack(pady=5)

        # Fetch button
        self.fetch_button = tk.Button(self, text="Fetch Video Info", command=self.fetch_video_info)
        self.fetch_button.pack(pady=5)

        # Resolution dropdown
        tk.Label(self, text="Select Resolution:").pack(pady=5)
        self.resolution_combo = ttk.Combobox(self, state="readonly", width=50)
        self.resolution_combo.pack(pady=5)

        # Save path
        self.path_label = tk.Label(self, text="Save to: (default is current folder)")
        self.path_label.pack(pady=5)
        self.save_path_entry = tk.Entry(self, width=50)
        self.save_path_entry.pack(side="left", padx=10, pady=5)
        self.browse_button = tk.Button(self, text="Browse", command=self.browse_folder)
        self.browse_button.pack(side="left")

        # Download button
        self.download_button = tk.Button(self, text="Download Video", command=self.download_video_threaded)
        self.download_button.pack(pady=15)

    def fetch_video_info(self):
        url = self.url_entry.get()
        if not url:
            messagebox.showwarning("Input Error", "Please enter a YouTube URL.")
            return

        try:
            self.video = YouTube(url)
            self.streams = self.video.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc()
            resolutions = [stream.resolution for stream in self.streams]
            self.resolution_combo['values'] = resolutions
            if resolutions:
                self.resolution_combo.current(0)
                messagebox.showinfo("Video Found", f"Video: {self.video.title}")
            else:
                messagebox.showwarning("No Video Streams", "No downloadable video streams found.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to fetch video info: {e}")

    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.save_path_entry.delete(0, tk.END)
            self.save_path_entry.insert(0, folder)

    def download_video(self):
        if not self.video or not self.streams:
            messagebox.showwarning("No Video", "Fetch a video first.")
            return

        resolution = self.resolution_combo.get()
        stream = next((s for s in self.streams if s.resolution == resolution), None)
        save_path = self.save_path_entry.get().strip() or "."

        if stream:
            try:
                self.download_button.config(state="disabled", text="Downloading...")
                stream.download(output_path=save_path)
                messagebox.showinfo("Success", "Download complete!")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to download video: {e}")
            finally:
                self.download_button.config(state="normal", text="Download Video")

    def download_video_threaded(self):
        threading.Thread(target=self.download_video).start()


if __name__ == "__main__":
    app = YouTubeDownloader()
    app.mainloop()
