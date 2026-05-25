#!/usr/bin/env python3
"""监控Whisper转录进度 - 后台运行whisper后用此脚本监控"""
import subprocess
import time
import sys

transcript_file = '/mnt/h/dbk/subtitles/NBv2puiGLlc_transcript.txt'

if len(sys.argv) > 1:
    transcript_file = sys.argv[1]

print("Whisper进度监控 (Ctrl+C中断)")
print(f"输出文件: {transcript_file}")
print()

last_lines = 0
last_time = time.time()

while True:
    try:
        r = subprocess.run(['wc', '-l', transcript_file], capture_output=True, text=True)
        if r.returncode == 0:
            parts = r.stdout.strip().split()
            if parts:
                lines = int(parts[0])
                now = time.time()
                speed = (lines - last_lines) / (now - last_time) if now > last_time else 0
                print(f"\r行数: {lines:4d} | 速度: {speed:.1f} 行/秒", end='', flush=True)
                last_lines = lines
                last_time = now
    except:
        pass
    time.sleep(30)
print("\n监控结束")
