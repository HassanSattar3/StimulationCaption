import os
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from tkinterdnd2 import TkinterDnD, DND_FILES
import moviepy.editor
import whisper
from PIL import Image, ImageDraw, ImageFont, ImageTk
import ffmpeg
import threading
import cv2
import numpy as np
from pathlib import Path
import shutil
import time
import subprocess
import sys

class VideoToGreenScreenApp:
    def __init__(self, master):
        self.master = master
        master.title("MrBeast-Style Green Screen Generator")
        master.geometry("600x400")
        
        self.font_path = None
        self.video_path = None
        self.transcribed_text = None
        
        self.temp_dir = os.path.join(os.path.expanduser("~"), "BeastFont_temp")
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)
        
        self.check_ffmpeg()
        self.create_widgets()
        self.setup_drag_and_drop()
        self.update_status("Please select a font file to begin")

    def check_ffmpeg(self):
        try:
            if sys.platform == 'win32':
                result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True, shell=True)
            else:
                result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
            
            if result.returncode != 0:
                raise subprocess.CalledProcessError(result.returncode, ['ffmpeg', '-version'])
        except subprocess.CalledProcessError:
            if sys.platform == 'win32':
                try:
                    where_result = subprocess.run(['where', 'ffmpeg'], capture_output=True, text=True, shell=True)
                    if where_result.returncode == 0 and where_result.stdout.strip():
                        messagebox.showwarning("FFmpeg Warning", "FFmpeg was found but had issues running.\nPlease try running the application again.")
                        return
                except:
                    pass
            
            messagebox.showerror("FFmpeg Error", "FFmpeg is not properly installed or not in PATH.\nPlease install FFmpeg using:\nwinget install \"FFmpeg (Essentials Build)\"\nThen restart your computer to ensure PATH is updated.")
            self.master.quit()
        except FileNotFoundError:
            messagebox.showerror("FFmpeg Error", "FFmpeg is not found in PATH.\nPlease install FFmpeg using:\nwinget install \"FFmpeg (Essentials Build)\"\nThen restart your computer to ensure PATH is updated.")
            self.master.quit()
        except Exception as e:
            print(f"Unexpected error checking FFmpeg: {str(e)}")
            messagebox.showerror("FFmpeg Error", "An unexpected error occurred while checking FFmpeg.\nPlease ensure FFmpeg is installed and try again.")
            self.master.quit()

    def create_widgets(self):
        self.main_frame = ttk.Frame(self.master)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        title_label = ttk.Label(self.main_frame, text="MrBeast-Style Green Screen Generator", font=("Arial", 16, "bold"))
        title_label.pack(pady=10)

        font_frame = ttk.LabelFrame(self.main_frame, text="Step 1: Select Font")
        font_frame.pack(fill=tk.X, pady=10)

        self.font_button = ttk.Button(font_frame, text="Select Font File", command=self.select_font)
        self.font_button.pack(pady=10)

        video_frame = ttk.LabelFrame(self.main_frame, text="Step 2: Select Video")
        video_frame.pack(fill=tk.X, pady=10)

        self.video_button = ttk.Button(video_frame, text="Select Video File", command=self.select_video)
        self.video_button.pack(pady=10)

        self.generate_button = ttk.Button(self.main_frame, text="Generate Green Screen Video", command=self.generate_final_video)
        self.generate_button.pack(pady=20)

        self.status_frame = ttk.Frame(self.main_frame)
        self.status_frame.pack(fill=tk.X, pady=10)

        self.status_label = ttk.Label(self.status_frame, text="", foreground="gray")
        self.status_label.pack()

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self.status_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, pady=5)

    def setup_drag_and_drop(self):
        self.master.drop_target_register(DND_FILES)
        self.master.dnd_bind('<<Drop>>', self.handle_file_drop)

    def select_font(self):
        self.font_path = filedialog.askopenfilename(title="Select Font File", filetypes=[("Font files", "*.ttf *.otf"), ("All files", "*.*")])
        if self.font_path:
            self.font_button.config(text=f"Font: {os.path.basename(self.font_path)}")
            self.update_status("Font selected. Please select a video file.")

    def select_video(self):
        self.video_path = filedialog.askopenfilename(title="Select Video File", filetypes=[("Video files", "*.mp4 *.avi *.mov *.mkv"), ("All files", "*.*")])
        if self.video_path:
            self.video_button.config(text=f"Video: {os.path.basename(self.video_path)}")
            self.update_status("Video selected. Click 'Generate Green Screen Video' to start processing.")

    def handle_file_drop(self, event):
        file_path = event.data.strip()
        if file_path:
            if file_path.lower().endswith(('.ttf', '.otf')):
                self.font_path = file_path
                self.font_button.config(text=f"Font: {os.path.basename(self.font_path)}")
                self.update_status("Font selected. Please select a video file.")
            elif file_path.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
                self.video_path = file_path
                self.video_button.config(text=f"Video: {os.path.basename(self.video_path)}")
                self.update_status("Video selected. Click 'Generate Green Screen Video' to start processing.")

    def update_status(self, message):
        self.status_label.config(text=message)
        self.master.update_idletasks()

    def generate_final_video(self):
        if not all([self.font_path, self.video_path]):
            self.update_status("Please select both a font and video file first")
            return

        self.generate_button.config(state=tk.DISABLED)
        self.update_status("Starting video processing...")
        
        def processing_thread():
            try:
                if not os.path.exists(self.temp_dir):
                    os.makedirs(self.temp_dir)
                
                temp_audio = os.path.join(self.temp_dir, "temp_audio.wav")
                temp_image = os.path.join(self.temp_dir, "temp_greenscreen.jpg")
                temp_whisper = os.path.join(self.temp_dir, "temp_whisper.wav")
                
                for temp_file in [temp_audio, temp_image, temp_whisper]:
                    if os.path.exists(temp_file):
                        try:
                            os.remove(temp_file)
                        except Exception as e:
                            print(f"Warning: Could not remove temporary file {temp_file}: {str(e)}")

                self.update_status("Extracting audio from video...")
                self.extract_audio(self.video_path, temp_audio)

                if not os.path.exists(temp_audio):
                    raise FileNotFoundError(f"Audio file not created: {temp_audio}")
                
                time.sleep(2)
                    
                self.update_status("Transcribing audio...")
                self.transcribed_text = self.transcribe_audio(temp_audio)

                self.update_status("Generating green screen with text...")
                self.generate_green_screen(self.transcribed_text, temp_image)

                if not os.path.exists(temp_image):
                    raise FileNotFoundError(f"Green screen image not created: {temp_image}")

                self.update_status("Creating final video...")
                output_path = os.path.normpath(os.path.splitext(self.video_path)[0] + "_greenscreen.mp4")
                self.create_final_video(temp_image, output_path)

                for temp_file in [temp_audio, temp_image, temp_whisper]:
                    if os.path.exists(temp_file):
                        try:
                            os.remove(temp_file)
                        except:
                            pass

                self.update_status(f"Done! Video saved as: {output_path}")
            except Exception as e:
                print(f"Error in processing: {str(e)}")
                self.update_status(f"Error: {str(e)}")
            finally:
                self.generate_button.config(state=tk.NORMAL)

        threading.Thread(target=processing_thread).start()

if __name__ == "__main__":
    root = TkinterDnD.Tk()
    app = VideoToGreenScreenApp(root)
    root.mainloop()
