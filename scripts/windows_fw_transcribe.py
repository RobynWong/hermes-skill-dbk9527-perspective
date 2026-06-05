#!/usr/bin/env python3
"""
Windows faster-whisper 转录脚本
通过WSL调用Windows Python执行GPU加速转录
"""
import os
import sys
import subprocess
import shutil

def get_wsl_ip():
    """获取当前WSL IP"""
    result = subprocess.run(['hostname', '-I'], capture_output=True, text=True)
    return result.stdout.strip().split()[0]

def check_gpu_available():
    """检查Windows端GPU是否可用"""
    python = r'C:\Users\Administrator\AppData\Local\Programs\Python\Python312\python.exe'
    cmd = [python, '-c', 'import torch; print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else "N/A")']
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    return result.returncode == 0 and 'True' in result.stdout

def transcribe(video_id, title, output_path):
    """执行Windows GPU转录"""
    python = r'C:\Users\Administrator\AppData\Local\Programs\Python\Python312\python.exe'
    script = r'C:\Users\Administrator\Downloads\dbk_transcribe.py'

    # 查WSL IP（用于代理）
    wsl_ip = get_wsl_ip()

    cmd = [
        python, script, video_id
    ]

    env = os.environ.copy()
    env['PATH'] = r'C:\Users\Administrator\.deno\bin;' + env.get('PATH', '')
    env['https_proxy'] = f'http://{wsl_ip}:7890'
    env['http_proxy'] = f'http://{wsl_ip}:7890'

    print(f"  Windows GPU转录: {video_id}")
    print(f"  WSL IP: {wsl_ip}")

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600, env=env)

    if result.returncode == 0:
        print(f"  ✅ Windows转录完成")
        if result.stdout:
            lines = [l for l in result.stdout.split('\n') if l.strip()]
            for l in lines[-5:]:
                print(f"     {l}")
        return True
    else:
        print(f"  ❌ Windows转录失败: {result.stderr[-300:] if result.stderr else result.stdout[-300:]}")
        return False

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: windows_fw_transcribe.py <video_id> <output_path>")
        sys.exit(1)

    video_id = sys.argv[1]
    output_path = sys.argv[2]
    title = sys.argv[3] if len(sys.argv) > 3 else video_id

    success = transcribe(video_id, title, output_path)
    sys.exit(0 if success else 1)
