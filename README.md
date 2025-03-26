# StimulationCaption

A Python application that generates MrBeast-style animated captions with green screen backgrounds. This tool automatically transcribes video audio and creates dynamic text animations that can be overlaid on your videos.

## Features

- Drag & drop interface for easy file selection
- Automatic audio transcription using Whisper AI
- Dynamic text animation with custom fonts
- Green screen background for easy video compositing
- Support for multiple video formats (mp4, avi, mov, mkv)

## Requirements

- Python 3.x
- FFmpeg installed on your system (Use `winget install "FFmpeg (Essentials Build)"` on Windows)
- Required Python packages (install via pip):
```bash
pip install -r requirements.txt
```

## Installation

1. Clone the repository
2. Install FFmpeg if not already installed:
   ```powershell
   winget install "FFmpeg (Essentials Build)"
   ```
3. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. Run the application:
   ```bash
   python main.py
   ```
2. Select or drag-and-drop your font file (TTF/OTF)
3. Select or drag-and-drop your video file
4. Click "Generate Green Screen Video" to process
5. Find the output video with "_greenscreen" suffix in the same directory as your input video

## Note
