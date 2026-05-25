# YouTube字幕/音频转录工作流

## 2026-05-20 v3 更新

### 背景

YouTube从WSL IP访问结果不稳定：有时成功（10秒），有时RequestBlocked。没有绝对可靠的方案，需要组合拳。

**最优路径**：Windows faster-whisper GPU（主力，2-3分钟）→ WSL youtube-transcript-api（备用，秒级）→ 两者均失败才手动处理

---

### 路径A：Windows faster-whisper GPU（主力，2-3分钟/视频）

Windows完整脚本，下载音频+faster-whisper转录一体化。**必须用这个作为首选方案**：

```bash
python C:\\Users\\Administrator\\Downloads\\dbk_transcribe.py <VIDEO_ID>
```

**前置条件**：
- cookies.txt 同目录（从Chrome导出）
- ffmpeg.exe 同目录
- deno 在 `C:\Users\Administrator\.deno\bin\`（需先设置PATH）
- 代理：mihomo在WSL端口9981，Windows访问端口7890

**WSL IP查询**（mihomo在WSL，Windows Python需要走代理）：
```bash
hostname -I | awk '{print $1}'
```

**Windows端环境变量**（运行时设置）：
```
set PATH=C:\Users\Administrator\.deno\bin;%PATH%
set https_proxy=http://<WSL_IP>:7890
set http_proxy=http://<WSL_IP>:7890
```

**流程**：自动下载音频 → faster-whisper small GPU转录 → 按日期归档 → 输出`H:\大镖客蒸馏\YYYYMMDD\VIDEO_ID_fw.txt` + 复制为`transcript.txt`

**WSL GPU性能**（GTX 1080 8GB，small模型，26分钟音频）：约2-3分钟

---

### 路径B：youtube-transcript-api（备用，秒级）

> ⚠️ 仅在路径A失败时使用。WSL IP被YouTube封锁时直接报RequestBlocked。

```python
import os
os.environ['https_proxy'] = 'http://127.0.0.1:9981'
os.environ['http_proxy'] = 'http://127.0.0.1:9981'
from youtube_transcript_api import YouTubeTranscriptApi
ytt = YouTubeTranscriptApi()
transcript = ytt.fetch('VIDEO_ID', languages=['zh-TW', 'zh', 'en'])
lines = [snippet.text.replace('\n', ' ').strip() for snippet in transcript if snippet.text.strip()]
result = ' '.join(lines)
# 保存到 /mnt/h/大镖客蒸馏/YYYYMMDD/transcript.txt
```

**注意**：成功率约50%，WSL IP被封时直接失败（RequestBlocked）。

---

### 路径C：faster-whisper（独立高准确度转录）

**⚠️ 不要用原生whisper CLI，会被SIGTERM终止。用faster-whisper Python API。**

```python
from faster_whisper import WhisperModel
import torch
device = "cuda" if torch.cuda.is_available() else "cpu"
compute_type = "float16" if device == "cuda" else "int8"
model = WhisperModel('small', device=device, compute_type=compute_type, cpu_threads=16)
segments, info = model.transcribe('audio.m4a', language='zh', beam_size=5, vad_filter=True)
text = '\n'.join([seg.text for seg in segments])
```

> ⚠️ Hermes后台任务SIGTERM陷阱：所有Whisper/faster-whisper后台任务在Hermes中都会被SIGTERM强制终止。**必须用前台terminal()并设置timeout=900**。

**WSL GPU性能**（GTX 1080 8GB，small模型，26分钟音频）：约2-3分钟

---

### 关键陷阱

1. **WSL IP是动态的** — 每次启动可能不同（172.27.x.x）。Windows端运行前必须`hostname -I`确认当前IP。mihomo代理端口9981，Windows访问端口7890。

2. **youtube-transcript-api不稳定** — WSL IP被YouTube封锁时直接报RequestBlocked。需要路径B fallback。

3. **Chrome cookies文件锁** — Chrome运行时无法读取Cookies SQLite DB。路径B需要关Chrome或用cookies.txt。

4. **deno必须在PATH（路径B）** — YouTube的EJS challenge验证需要deno解码。无deno报"n challenge solving failed"。

5. **"There are no subtitles for the requested languages"** — 视频本身无字幕，不是错误，改用路径B/C。

6. **原生whisper CLI被SIGTERM** — 不要用。后台任务全部被终止。

7. **mihomo allow-lan=true** — config.yaml已配置。

8. **Windows Python路径** — `C:\Users\Administrator\AppData\Local\Microsoft\WindowsApps\python.exe` 是Launcher，实际Python在`PythonSoftwareFoundation.Python.3.12_qbz5n2kfra8p0`目录。

9. **fetch_new_videos.py超时** — timeout=180秒。YouTube频道列表在美国服务器，拉取慢时可能超限。

---

### 自动转录工作流（fetch_new_videos.py）

```bash
python3 ~/.hermes/skills/dbk9527-perspective/scripts/fetch_new_videos.py
```

**功能**：获取频道最新10个视频 → 识别新视频 → 自动转录 → 更新video_list.csv

**修复记录（v3）**：
- timeout 120秒→180秒
- yt-dlp直接返回upload_date（避免每个视频额外API请求）
- 转录失败时输出正确的Windows fallback命令

**已知限制**：
- WSL youtube-transcript-api失败时脚本会跳过该视频并输出Windows命令，需手动在Windows执行
- 不自动调用dbk_transcribe.py（Windows环境隔离）

---

### 目录结构

```
/mnt/h/大镖客蒸馏/        (H:\大镖客蒸馏\)
  video_list.csv           ← 总索引（git已初始化）
  YYYYMMDD/
    transcript_raw.txt     ← youtube-transcript-api版（原始）
    transcript.txt         ← faster-whisper版（精修）
    transcript_fw.txt      ← faster-whisper版（原始）
  subtitles/               ← 临时文件
```

**git已初始化**：cd `/mnt/h/大镖客蒸馏` → `git commit` 记录历史

---

### 已知失效方案

- **WSL yt-dlp + 127.0.0.1:9981** — ❌ yt-dlp不走系统代理，走WSL mihomo需要在Windows端用WSL IP
- **Chrome Cookies SQLite直接读取** — ❌ DPAPI加密，WSL无法解密
- **原生whisper CLI** — ❌ 被SIGTERM终止
- **fetch_new_videos.py timeout 60秒** — ❌ YouTube频道列表拉取慢，应设180秒
