#!/usr/bin/env python3
"""获取大镖客频道最新视频并转录 - 适配youtube-transcript-api v1.2+"""
import os
import sys
import re
import json
import csv
import subprocess
from datetime import datetime

os.environ['https_proxy'] = 'http://127.0.0.1:9981'
os.environ['http_proxy'] = 'http://127.0.0.1:9981'

VIDEO_DIR = '/mnt/h/大镖客蒸馏'
CSV_PATH = os.path.join(VIDEO_DIR, 'video_list.csv')

WINDOWS_USER = 'Robyn'

def check_mihomo():
    """检查mihomo代理是否运行"""
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    try:
        sock.connect(('127.0.0.1', 9981))
        sock.close()
        return True
    except:
        return False

def get_latest_videos(count=10):
    """用yt-dlp获取频道最新视频"""
    cmd = [
        'yt-dlp', '--flat-playlist',
        '--print', '%(id)s|%(title)s|%(duration)s|%(upload_date)s',
        '--playlist-end', str(count),
        'https://www.youtube.com/@dbk9527/videos'
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if result.returncode != 0:
        print(f"yt-dlp error: {result.stderr}")
        return []
    
    videos = []
    for line in result.stdout.strip().split('\n'):
        if not line.strip():
            continue
        parts = line.split('|')
        if len(parts) >= 4:
            vid_id = parts[0].strip()
            title = parts[1].strip()
            duration = parts[2].strip().replace('.0', '')
            upload_date = parts[3].strip() if len(parts) > 3 and parts[3].strip() else None
            videos.append({'id': vid_id, 'title': title, 'duration': duration, 'upload_date': upload_date})
        elif len(parts) >= 3:
            vid_id = parts[0].strip()
            title = parts[1].strip()
            duration = parts[2].strip().replace('.0', '')
            videos.append({'id': vid_id, 'title': title, 'duration': duration, 'upload_date': None})
    return videos

def get_upload_date(video_id):
    """获取视频上传日期"""
    # 方法1: yt-dlp -j + deno (必需，否则403)
    cmd = ['yt-dlp', '--js-runtimes', 'deno', '-j', '--no-playlist', f'https://www.youtube.com/watch?v={video_id}']
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode == 0 and result.stdout.strip():
        try:
            data = json.loads(result.stdout)
            upload_date = data.get('upload_date', '')
            if upload_date:
                return upload_date
        except:
            pass

    # 方法2: 直接从页面正则匹配
    cmd = ['curl', '-s', '--max-time', '15',
           '-H', 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
           f'https://www.youtube.com/watch?v={video_id}']
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
    match = re.search(r'"uploadDate":"([^"]+)"', result.stdout)
    if match:
        try:
            dt = datetime.fromisoformat(match.group(1).replace('Z', '+00:00'))
            return dt.strftime('%Y%m%d')
        except:
            pass

    return None

def get_wsl_ip():
    """获取当前WSL IP"""
    result = subprocess.run(['hostname', '-I'], capture_output=True, text=True)
    return result.stdout.strip().split()[0]

def transcribe_windows(video_id, title, date_dir):
    """Windows faster-whisper GPU转录（主力方案）"""
    import subprocess

    # 尝试多个可能的Python路径
    python_paths = [
        f'/mnt/c/Users/{WINDOWS_USER}/AppData/Local/Microsoft/WindowsApps/python.exe',
        f'/mnt/c/Users/{WINDOWS_USER}/AppData/Local/Programs/Python/Python312/python.exe',
        'python',  # 尝试PATH中的python
    ]
    python = None
    for p in python_paths:
        try:
            test = subprocess.run([p, '--version'], capture_output=True, timeout=15)
            if test.returncode == 0:
                python = p
                print(f"  [Windows] 使用Python: {python} ({test.stdout.strip()})")
                break
        except:
            continue

    if not python:
        print(f"  ❌ Windows Python未找到（WindowsApps路径不可用）")
        return False

    script_win = f'C:\\Users\\{WINDOWS_USER}\\Downloads\\dbk_transcribe.py'
    
    # 先在WSL下载音频
    audio_path = os.path.join(date_dir, f'{video_id}.m4a')
    if not os.path.exists(audio_path):
        print(f"  [WSL] 下载音频...")
        cmd = [
            'yt-dlp',
            '-f', 'bestaudio[ext=m4a]',
            '-o', audio_path,
            f'https://www.youtube.com/watch?v={video_id}'
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            print(f"  ❌ 音频下载失败: {result.stderr[-200:]}")
            return False
        print(f"  ✅ 音频下载完成")
    else:
        print(f"  音频已存在，跳过下载")

    # 转换WSL路径为Windows路径
    # /mnt/h/大镖客蒸馏/... -> H:\大镖客蒸馏\...
    audio_win = audio_path.replace('/mnt/', '').replace('/', '\\')
    audio_win = audio_win[0:1] + ':' + audio_win[1:]  # h\... -> H:\...
    
    fw_path = os.path.join(date_dir, f'{video_id}_fw.txt')
    fw_win = fw_path.replace('/mnt/', '').replace('/', '\\')
    fw_win = fw_win[0:1] + ':' + fw_win[1:]

    print(f"  [Windows] 开始转录: {title[:40]}...")
    print(f"  音频: {audio_win}")
    try:
        result = subprocess.run(
            [python, script_win, audio_win, fw_win],
            capture_output=True, text=True, timeout=600
        )
    except subprocess.TimeoutExpired:
        print(f"  ❌ Windows转录超时（600秒）")
        return False
    except FileNotFoundError as e:
        print(f"  ❌ Windows Python执行失败: {e}")
        return False

    if result.returncode == 0:
        lines = [l for l in result.stdout.split('\n') if l.strip()]
        # 从输出中解析实际使用的设备
        actual_device = 'GPU'  # 默认
        for l in lines:
            if 'DEVICE=cpu' in l:
                actual_device = 'CPU'
                break
            elif 'DEVICE=cuda' in l:
                actual_device = 'GPU'
                break
        print(f"  [Windows {actual_device}] 转录完成")
        for l in lines[-5:]:
            print(f"    {l}")
        return True
    else:
        print(f"  ❌ Windows转录失败")
        if result.stderr:
            print(f"    {result.stderr[-300:]}")
        return False

def get_transcript_subtitle(video_id):
    """WSL YouTube字幕API转录（备用方案）"""
    from youtube_transcript_api import YouTubeTranscriptApi

    try:
        ytt_api = YouTubeTranscriptApi()
        transcript = ytt_api.fetch(video_id, languages=['zh-Hant', 'zh-TW', 'zh'])
        lines = []
        for snippet in transcript:
            text = getattr(snippet, 'text', '') or ''
            lines.append(text)
        return '\n'.join(lines)
    except Exception as e:
        print(f"  字幕API失败: {e}")

    # fallback: list + fetch
    try:
        ytt_api = YouTubeTranscriptApi()
        transcript_list = ytt_api.list(video_id)
        for t in transcript_list:
            if 'zh' in str(t.language_code).lower():
                fetched = t.fetch()
                lines = []
                for snippet in fetched:
                    if hasattr(snippet, 'text'):
                        lines.append(snippet.text)
                    elif isinstance(snippet, dict):
                        lines.append(snippet.get('text', ''))
                return '\n'.join(lines)
    except Exception as e2:
        print(f"  字幕API(list)也失败: {e2}")

    return None

def transcribe_wsl_fw(video_id, date_dir):
    """WSL faster-whisper CPU转录（最后备用方案）"""
    import shutil
    from faster_whisper import WhisperModel

    audio_path = os.path.join(date_dir, f'{video_id}.m4a')
    fw_path = os.path.join(date_dir, f'{video_id}_fw.txt')

    # 如果音频不存在，先下载
    if not os.path.exists(audio_path):
        print(f"  [WSL] 下载音频...")
        cmd = [
            'yt-dlp',
            '-f', 'bestaudio[ext=m4a]',
            '-o', audio_path,
            f'https://www.youtube.com/watch?v={video_id}'
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            print(f"  ❌ 音频下载失败")
            return False

    print(f"  [WSL faster-whisper] 开始转录（CPU模式，5-15分钟）...")
    try:
        # 先尝试GPU，失败后回退到CPU
        try:
            model = WhisperModel('small', device='cuda', compute_type='float16', local_files_only=True)
            compute_type = 'float16'
        except Exception:
            print(f"  [WSL] GPU不可用，使用CPU int8...")
            model = WhisperModel('small', device='cpu', compute_type='int8')
            compute_type = 'int8'

        segments, info = model.transcribe(audio_path, language='zh', beam_size=5, vad_filter=True)
        print(f"  [WSL] 语言: {info.language}, 持续: {info.duration:.0f}秒")

        count = 0
        with open(fw_path, 'w', encoding='utf-8') as f:
            for seg in segments:
                count += 1
                f.write(f'{seg.start:.2f},{seg.end:.2f},{seg.text.strip()}\n')
        print(f"  [WSL] 转录完成: {count}段")
        return True

    except Exception as e:
        print(f"  ❌ WSL faster-whisper失败: {e}")
        if os.path.exists(audio_path):
            try:
                os.remove(audio_path)
            except:
                pass
        return False

def load_csv():
    """加载现有CSV"""
    existing_ids = set()
    rows = []
    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)
        for row in reader:
            if row:
                rows.append(row)
                if len(row) >= 2:
                    existing_ids.add(row[0].strip().strip('"'))
    return header, rows, existing_ids

def main():
    print("=" * 60)
    print("大镖客YouTube频道 - 新视频检查与转录")
    print("=" * 60)

    # 检查mihomo代理
    if not check_mihomo():
        print("❌ mihomo代理未运行！请先执行: ~/clash/clashctl start")
        sys.exit(1)
    
    header, rows, existing_ids = load_csv()
    print(f"现有CSV: {len(rows)} 条记录")
    print(f"Header: {header}")
    
    print("\n正在获取频道最新视频...")
    videos = get_latest_videos(10)
    print(f"获取到 {len(videos)} 个视频")
    
    new_videos = []
    for v in videos:
        if v['id'] not in existing_ids:
            new_videos.append(v)
            print(f"  🆕 [{v['id']}] {v['title']} ({v['duration']}s)")
        else:
            print(f"  ✅ [{v['id']}] 已存在")
    
    if not new_videos:
        print("\n没有新视频需要处理。")
        return
    
    print(f"\n发现 {len(new_videos)} 个新视频，开始处理...")
    
    for v in new_videos:
        vid_id = v['id']
        title = v['title']
        duration = v['duration']
        
        print(f"\n处理: {title}")
        
        upload_date = v.get('upload_date')
        if not upload_date or upload_date == 'NA':
            upload_date = get_upload_date(vid_id)
        if not upload_date:
            print("  ⚠️ 无法获取上传日期，使用今天日期")
            upload_date = datetime.now().strftime('%Y%m%d')
        print(f"  上传日期: {upload_date}")
        
        date_dir = os.path.join(VIDEO_DIR, upload_date)
        os.makedirs(date_dir, exist_ok=True)

        # 方案1: Windows GPU转录（主力，约2-3分钟/视频）
        # 用try/except包装，确保Windows崩溃时自动触发备用方案
        win_ok = False
        try:
            win_ok = transcribe_windows(vid_id, title, date_dir)
        except Exception as e:
            print(f"  ⚠️ Windows方案异常: {e}，切换备用方案")

        if win_ok:
            # Windows成功，在同目录生成transcript备用
            fw_path = os.path.join(date_dir, f'{vid_id}_fw.txt')
            if os.path.exists(fw_path):
                # 复制为transcript版（供分析脚本使用）
                transcript_path = os.path.join(date_dir, f'{vid_id}_transcript.txt')
                import shutil
                shutil.copy2(fw_path, transcript_path)
                print(f"  ✅ GPU转录完成 + 字幕API备用均已就绪")
        else:
            # 方案2: WSL字幕API（备用，秒级）
            transcript = get_transcript_subtitle(vid_id)
            if transcript:
                transcript_path = os.path.join(date_dir, f'{vid_id}_transcript.txt')
                with open(transcript_path, 'w', encoding='utf-8') as f:
                    f.write(transcript)
                byte_size = os.path.getsize(transcript_path)
                print(f"  ✅ 字幕API转录已保存: {transcript_path} ({byte_size} bytes)")
            else:
                # 方案3: WSL faster-whisper CPU（最后备用，分钟级）
                print(f"  ⚠️ 字幕API失败，尝试WSL faster-whisper CPU...")
                fw_path = os.path.join(date_dir, f'{vid_id}_fw.txt')
                ok = transcribe_wsl_fw(vid_id, date_dir)
                if ok:
                    # 复制为transcript版
                    transcript_path = os.path.join(date_dir, f'{vid_id}_transcript.txt')
                    import shutil
                    shutil.copy2(fw_path, transcript_path)
                    print(f"  ✅ WSL faster-whisper CPU转录完成")
                else:
                    print(f"  ❌ 所有方案均失败，请手动处理")
                    continue

        new_row = [vid_id, upload_date, title, 'yes']
        rows.append(new_row)
        print(f"  ✅ CSV已更新: {vid_id}")
    
    with open(CSV_PATH, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)
    
    print(f"\n{'=' * 60}")
    print(f"处理完成！CSV总记录数: {len(rows)}")
    print(f"{'=' * 60}")

if __name__ == '__main__':
    main()
