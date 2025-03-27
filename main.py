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
                result = subprocess.run(['ffmpeg', '-version'],
                                     capture_output=True,
                                     text=True,
                                     shell=True)
            else:
                result = subprocess.run(['ffmpeg', '-version'],
                                     capture_output=True,
                                     text=True)
            
            if result.returncode != 0:
                raise subprocess.CalledProcessError(result.returncode, ['ffmpeg', '-version'])
                
        except subprocess.CalledProcessError:
            if sys.platform == 'win32':
                try:
                    where_result = subprocess.run(['where', 'ffmpeg'],
                                               capture_output=True,
                                               text=True,
                                               shell=True)
                    if where_result.returncode == 0 and where_result.stdout.strip():
                        messagebox.showwarning("FFmpeg Warning",
                            "FFmpeg was found but had issues running.\n"
                            "Please try running the application again.")
                        return
                except:
                    pass
            
            messagebox.showerror("FFmpeg Error",
                "FFmpeg is not properly installed or not in PATH.\n"
                "Please install FFmpeg using:\n"
                "winget install \"FFmpeg (Essentials Build)\"\n"
                "Then restart your computer to ensure PATH is updated.")
            self.master.quit()
        except FileNotFoundError:
            messagebox.showerror("FFmpeg Error",
                "FFmpeg is not found in PATH.\n"
                "Please install FFmpeg using:\n"
                "winget install \"FFmpeg (Essentials Build)\"\n"
                "Then restart your computer to ensure PATH is updated.")
            self.master.quit()
        except Exception as e:
            print(f"Unexpected error checking FFmpeg: {str(e)}")
            messagebox.showerror("FFmpeg Error",
                "An unexpected error occurred while checking FFmpeg.\n"
                "Please ensure FFmpeg is installed and try again.")
            self.master.quit()

    def create_widgets(self):
        self.main_frame = ttk.Frame(self.master)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        title_label = ttk.Label(self.main_frame, text="MrBeast-Style Green Screen Generator",
                              font=("Arial", 16, "bold"))
        title_label.pack(pady=10)

        font_frame = ttk.LabelFrame(self.main_frame, text="Step 1: Select Font")
        font_frame.pack(fill=tk.X, pady=10)

        self.font_button = ttk.Button(font_frame, text="Select Font File",
                                    command=self.select_font)
        self.font_button.pack(pady=10)

        video_frame = ttk.LabelFrame(self.main_frame, text="Step 2: Select Video")
        video_frame.pack(fill=tk.X, pady=10)

        self.video_button = ttk.Button(video_frame, text="Select Video File",
                                     command=self.select_video)
        self.video_button.pack(pady=10)

        self.generate_button = ttk.Button(self.main_frame, text="Generate Green Screen Video",
                                        command=self.generate_final_video)
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
        self.font_path = filedialog.askopenfilename(
            title="Select Font File",
            filetypes=[("Font files", "*.ttf *.otf"), ("All files", "*.*")]
        )
        if self.font_path:
            self.font_button.config(text=f"Font: {os.path.basename(self.font_path)}")
            self.update_status("Font selected. Please select a video file.")

    def select_video(self):
        self.video_path = filedialog.askopenfilename(
            title="Select Video File",
            filetypes=[
                ("Video files", "*.mp4 *.avi *.mov *.mkv"),
                ("All files", "*.*")
            ]
        )
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

    def extract_audio(self, video_path, output_path):
        clip = None
        try:
            # Ensure temp directory exists
            if not os.path.exists(self.temp_dir):
                os.makedirs(self.temp_dir)
            
            # Convert paths to absolute paths
            video_path = os.path.abspath(video_path)
            output_path = os.path.abspath(output_path)
            
            clip = moviepy.editor.VideoFileClip(video_path)
            
            if clip.audio is None:
                raise ValueError("No audio found in video file")
            
            # Write audio file
            clip.audio.write_audiofile(output_path)
            
            # Close the clip
            clip.close()
            clip = None
            
            # Wait to ensure file is written
            time.sleep(2)
            
            # Verify file exists
            if not os.path.exists(output_path):
                raise FileNotFoundError(f"Failed to create audio file: {output_path}")
                
        except Exception as e:
            print(f"Error extracting audio: {str(e)}")
            self.update_status(f"Error: {str(e)}")
            raise
        finally:
            if clip is not None:
                try:
                    clip.close()
                except:
                    pass

    def transcribe_audio(self, audio_path):
        try:
            import soundfile as sf
            import numpy as np
            
            # Ensure temp directory exists
            if not os.path.exists(self.temp_dir):
                os.makedirs(self.temp_dir)
            
            # Convert path to absolute path
            audio_path = os.path.abspath(audio_path)
            
            # Verify audio file exists
            if not os.path.exists(audio_path):
                raise FileNotFoundError(f"Audio file not found: {audio_path}")
            
            # Read audio file
            data, samplerate = sf.read(audio_path)
            
            if len(data.shape) > 1:
                data = np.mean(data, axis=1)
            
            # Create whisper temp file with absolute path
            temp_path = os.path.abspath(os.path.join(self.temp_dir, "temp_whisper.wav"))
            
            # Write audio file
            sf.write(temp_path, data, samplerate)
            
            # Wait to ensure file is written
            time.sleep(1)
            
            # Verify whisper temp file exists
            if not os.path.exists(temp_path):
                raise FileNotFoundError(f"Failed to create whisper temp file: {temp_path}")
            
            try:
                # Load model and transcribe
                model = whisper.load_model("base")
                result = model.transcribe(temp_path, word_timestamps=True)
                
                if not result or 'segments' not in result:
                    raise ValueError("Transcription failed - no segments generated")
                
                # Store transcription data with timestamps
                self.transcription_data = []
                for segment in result['segments']:
                    words = []
                    if 'words' in segment:
                        for word in segment['words']:
                            words.append({
                                'text': word['text'],
                                'start': word['start'],
                                'end': word['end']
                            })
                    else:
                        words.append({
                            'text': segment['text'],
                            'start': segment['start'],
                            'end': segment['end']
                        })
                    self.transcription_data.append({
                        'text': segment['text'],
                        'start': segment['start'],
                        'end': segment['end'],
                        'words': words
                    })
                
                # Return combined text for backward compatibility
                return ' '.join(segment['text'] for segment in self.transcription_data)
            finally:
                # Clean up whisper temp file
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except:
                        pass
            
        except Exception as e:
            print(f"Error in transcription: {str(e)}")
            self.update_status(f"Transcription error: {str(e)}")
            raise

    def generate_frame(self, frame_text, output_path, width=1920, height=1080):
        # Create a new green screen frame with the current text state
        img = Image.new('RGB', (width, height), color=(0, 255, 0))
        draw = ImageDraw.Draw(img)

        try:
            font = ImageFont.truetype(self.font_path, 120)
        except IOError:
            font = ImageFont.load_default()

        # Text wrapping
        max_width = width - 100
        words = frame_text.split()
        lines = []
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            text_width = draw.textlength(test_line, font=font)
            if text_width <= max_width:
                current_line.append(word)
            else:
                lines.append(' '.join(current_line))
                current_line = [word]
        lines.append(' '.join(current_line))

        # Calculate positions
        total_height = sum(font.getbbox(line)[3] - font.getbbox(line)[1] for line in lines)
        y = (height - total_height) // 2

        # Draw lines
        for line in lines:
            text_width = draw.textlength(line, font=font)
            x = (width - text_width) // 2
            draw.text((x, y), line, fill=(0, 0, 0), font=font)
            y += font.getbbox(line)[3] - font.getbbox(line)[1] + 10

        img.save(output_path)

    def generate_frames(self, fps=30):
        if not hasattr(self, 'transcription_data'):
            raise ValueError("No transcription data available. Run transcribe_audio first.")
            
        # Create frames directory
        frames_dir = os.path.join(self.temp_dir, "frames")
        os.makedirs(frames_dir, exist_ok=True)
        
        try:
            # Calculate total frames needed
            total_duration = max(segment['end'] for segment in self.transcription_data)
            total_frames = int(total_duration * fps)
            
            # Track current text state
            current_text = ""
            last_frame_path = None
            frame_paths = []
            
            # Prepare segments with simple text splitting
            segments = []
            words_per_segment = 6  # Number of words per segment
            
            for segment in self.transcription_data:
                # Get segment text safely
                segment_text = segment.get('text', '').strip()
                if not segment_text:
                    continue
                
                # Split text into words
                words = segment_text.split()
                if not words:
                    continue
                
                # Create segments of fixed size
                for i in range(0, len(words), words_per_segment):
                    word_chunk = words[i:i + words_per_segment]
                    chunk_text = ' '.join(word_chunk)
                    
                    # Calculate timing based on segment duration
                    segment_duration = segment['end'] - segment['start']
                    words_per_chunk = len(word_chunk)
                    total_words = len(words)
                    
                    # Calculate start and end times for this chunk
                    start_time = segment['start'] + (i * segment_duration / total_words)
                    end_time = start_time + (words_per_chunk * segment_duration / total_words)
                    
                    # Add some padding to keep text visible longer
                    end_time += 0.5  # Keep text visible for 0.5 seconds after it should disappear
                    
                    segments.append({
                        'text': chunk_text,
                        'start': start_time,
                        'end': end_time
                    })
            
            # Sort segments by start time
            segments.sort(key=lambda x: x['start'])
            
            # Generate frames
            for frame_num in range(total_frames):
                current_time = frame_num / fps
                
                # Update text based on timing
                text_changed = False
                visible_segments = []
                
                for segment in segments:
                    if segment['start'] <= current_time <= segment['end']:
                        visible_segments.append(segment['text'])
                
                new_text = ' '.join(visible_segments)
                if new_text != current_text:
                    current_text = new_text
                    text_changed = True
                
                # Only generate new frame if text changed
                if text_changed or not frame_paths:
                    frame_path = os.path.join(frames_dir, f"frame_{frame_num:06d}.jpg")
                    self.generate_frame(current_text.strip(), frame_path)
                    last_frame_path = frame_path
                else:
                    # Reuse last frame by creating a copy
                    frame_path = os.path.join(frames_dir, f"frame_{frame_num:06d}.jpg")
                    shutil.copy2(last_frame_path, frame_path)
                
                frame_paths.append(frame_path)
                
                # Update progress
                progress = (frame_num + 1) / total_frames * 100
                self.progress_var.set(progress)
                self.update_status(f"Generating frames: {progress:.1f}%")
                self.master.update_idletasks()
            
            return frames_dir
            
        except Exception as e:
            # Clean up frames directory on error
            shutil.rmtree(frames_dir, ignore_errors=True)
            raise e

    def generate_green_screen(self, text, output_path, width=1920, height=1080):
        # Generate frames directory
        frames_dir = self.generate_frames()
        
        # Use the last frame as the output image
        frame_files = sorted(os.listdir(frames_dir))
        if not frame_files:
            raise ValueError("No frames were generated")
            
        last_frame = os.path.join(frames_dir, frame_files[-1])
        shutil.copy2(last_frame, output_path)
        
        # Clean up frames directory
        try:
            shutil.rmtree(frames_dir)
        except:
            pass

    def create_final_video(self, image_path, output_path):
        # Generate frames with animated text
        self.update_status("Creating animated text frames...")
        frames_dir = self.generate_frames()
        
        try:
            # Create output directory
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Get video properties
            clip = moviepy.editor.VideoFileClip(self.video_path)
            duration = clip.duration
            fps = 30  # Fixed fps for smooth animation
            clip.close()

            # Create video from frame sequence using ffmpeg
            self.update_status("Creating final video from frames...")
            frame_pattern = os.path.join(frames_dir, 'frame_%06d.jpg')
            stream = ffmpeg.input(frame_pattern, pattern_type='sequence', framerate=fps)
            stream = ffmpeg.output(stream, output_path, vcodec='libx264', pix_fmt='yuv420p')
            ffmpeg.run(stream, overwrite_output=True, capture_stdout=True, capture_stderr=True)
            
            # Wait to ensure file is written
            time.sleep(2)
            
            # Verify output file exists
            if not os.path.exists(output_path):
                raise FileNotFoundError(f"Failed to create final video: {output_path}")
                
        except ffmpeg.Error as e:
            print(f"FFmpeg error: {e.stderr.decode() if e.stderr else str(e)}")
            raise Exception(f"FFmpeg error: {e.stderr.decode() if e.stderr else str(e)}")
        except Exception as e:
            print(f"Error creating final video: {str(e)}")
            raise
        finally:
            # Clean up frames directory
            try:
                if os.path.exists(frames_dir):
                    shutil.rmtree(frames_dir)
            except:
                pass

if __name__ == "__main__":
    root = TkinterDnD.Tk()
    app = VideoToGreenScreenApp(root)
    root.mainloop()
