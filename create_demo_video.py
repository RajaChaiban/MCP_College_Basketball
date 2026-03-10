#!/usr/bin/env python3
import subprocess
import os
from pathlib import Path

# Create frames directory
os.makedirs('demo_frames', exist_ok=True)

# Create a simple video using ffmpeg with text overlays
# Using the dashboard screenshot we already have

# Duration: 30 seconds, we'll use the existing dashboard image with text overlays
dashboard_img = 'demo_1_dashboard.png'

# Create 30 seconds worth of frames at 1 fps (30 frames total)
# Frame 1-8 (8 sec): Title + "AI Analyst Feature"
for i in range(8):
    cmd = [
        'ffmpeg', '-i', dashboard_img,
        '-vf', f"drawtext=text='CBB Predictive Dashboard':fontsize=60:fontcolor=white:x=(w-text_w)/2:y=h/2-200",
        f'demo_frames/frame_{i:03d}.png',
        '-y'
    ]
    subprocess.run(cmd, capture_output=True)

# Frame 9-16 (8 sec): Show AI Chat interaction
for i in range(8, 16):
    cmd = [
        'ffmpeg', '-i', dashboard_img,
        '-vf', f"drawtext=text='Ask AI Analyst Questions':fontsize=50:fontcolor=yellow:x=(w-text_w)/2:y=h/2-100,drawtext=text='Duke Stats | UNC Record':fontsize=40:fontcolor=white:x=(w-text_w)/2:y=h/2+50",
        f'demo_frames/frame_{i:03d}.png',
        '-y'
    ]
    subprocess.run(cmd, capture_output=True)

# Frame 17-24 (8 sec): Game details
for i in range(16, 24):
    cmd = [
        'ffmpeg', '-i', dashboard_img,
        '-vf', f"drawtext=text='View Live Games':fontsize=50:fontcolor=cyan:x=(w-text_w)/2:y=h/2-100,drawtext=text='Real-time Box Scores':fontsize=40:fontcolor=white:x=(w-text_w)/2:y=h/2+50",
        f'demo_frames/frame_{i:03d}.png',
        '-y'
    ]
    subprocess.run(cmd, capture_output=True)

# Frame 25-30 (6 sec): Win Probability
for i in range(24, 30):
    cmd = [
        'ffmpeg', '-i', dashboard_img,
        '-vf', f"drawtext=text='Win Probability Analysis':fontsize=50:fontcolor=lime:x=(w-text_w)/2:y=h/2-100,drawtext=text='ML-Powered Predictions':fontsize=40:fontcolor=white:x=(w-text_w)/2:y=h/2+50",
        f'demo_frames/frame_{i:03d}.png',
        '-y'
    ]
    subprocess.run(cmd, capture_output=True)

print("Frames created successfully")
print(f"Total frames: {len(os.listdir('demo_frames'))}")

# Now create the video from frames
cmd = [
    'ffmpeg',
    '-framerate', '1',  # 1 frame per second = 30 frames = 30 seconds
    '-i', 'demo_frames/frame_%03d.png',
    '-c:v', 'libx264',
    '-pix_fmt', 'yuv420p',
    '-y',
    'CBB_AI_Analyst_Demo.mp4'
]

result = subprocess.run(cmd, capture_output=True, text=True)
if result.returncode == 0:
    print("✓ Video created successfully: CBB_AI_Analyst_Demo.mp4")
else:
    print("Error creating video:")
    print(result.stderr)

# Verify the video was created
if os.path.exists('CBB_AI_Analyst_Demo.mp4'):
    file_size = os.path.getsize('CBB_AI_Analyst_Demo.mp4')
    print(f"Video file size: {file_size / 1024 / 1024:.2f} MB")
