# 大镖客视频转录工作流 - 故障排除指南

## 核心原则

**手动yt-dlp + youtube-transcript-api比fetch_new_videos.py脚本更可靠**。脚本因yt-dlp --flat-playlist超时容易挂。

## youtube-transcript-api 行为模式

### 最新视频（<1天）可能首次失败

**现象**：刚发布的视频（<24小时），youtube-transcript-api可能返回"Could not retrieve a transcript"错误。

**原因**：YouTube字幕系统需要时间处理新视频，自动字幕可能还未生成。

**解决方案**：**重试即可成功**。实测6/1-6/3三个视频首次全部失败，等待后重试全部成功。

```python
# 推荐重试模式
for attempt in range(3):
    try:
        transcript = ytt.fetch(vid_id, languages=['zh-TW', 'zh', 'zh-Hans'])
        break
    except Exception as e:
        if attempt < 2:
            time.sleep(10 * (attempt + 1))  # 递增等待
        else:
            raise
```

### 语言优先级

大镖客视频字幕语言：`['zh-TW', 'zh', 'zh-Hans', 'en']`

繁体中文(zh-TW)最准确，简体中文(zh-Hans)次之，英文(en)最差但可作为fallback。

## yt-dlp 故障排除

### 429 Too Many Requests

**现象**：yt-dlp返回HTTP 429错误。

**原因**：YouTube限流，通常发生在短时间内多次请求。

**解决方案**：
1. 等待5-10分钟后重试
2. 使用不同的代理IP
3. 减少请求频率

### "Sign in to confirm you're not a bot"

**现象**：yt-dlp要求cookies认证。

**解决方案**：
1. 使用cookies文件：`yt-dlp --cookies cookies.txt`
2. 使用浏览器cookies：`yt-dlp --cookies-from-browser chrome`
3. 使用deno运行时：`yt-dlp --js-runtimes deno:/path/to/deno.exe`

### Cookies过期（2026-06-08验证）

**现象**：yt-dlp即使带cookies仍报"Sign in to confirm you're not a bot"，cookies文件只有基本的PREF和SOCS条目（没有认证cookies）。

**原因**：cookies文件过期，YouTube认证cookies有时效限制。

**解决方案（优先级）**：
1. **Windows端用浏览器cookies**（最可靠）：
   ```powershell
   yt-dlp --cookies-from-browser chrome --write-auto-sub --sub-lang zh-TW --skip-download --output "C:\Users\Robyn\Downloads\VIDEO_ID" "https://www.youtube.com/watch?v=VIDEO_ID"
   ```
2. **重新导出cookies**：在Chrome中登录YouTube → 用"Get cookies.txt LOCALLY"扩展导出 → 覆盖 `C:\Users\Robyn\Downloads\cookies.txt`
3. **youtube-transcript-api重试**：最新视频（<1天）首次可能失败，等待后重试即可（2026-06-03验证）

**⚠️ cookies过期的判断方法**：检查cookies文件头部，如果只有PREF和SOCS两行（没有SID、HSID、SSID等认证条目），说明已过期。

### deno路径（Windows）

```
C:\Users\Robyn\.deno\bin\deno.exe
```

WSL路径：`/mnt/c/Users/Robyn/.deno/bin/deno.exe`

完整命令：
```bash
yt-dlp --js-runtimes deno:/mnt/c/Users/Robyn/.deno/bin/deno.exe ...
```

## faster-whisper 故障排除

### WSL下CUDA库缺失

**现象**：`libcublasLt.so.*[0-9] not found in the system path`

**原因**：WSL环境下CUDA库路径不正确。

**解决方案**：
1. **使用Windows端faster-whisper**（推荐，有GTX1080 GPU）
2. 安装CUDA库：`pip install nvidia-cublas-cu11`
3. 设置环境变量：`export LD_LIBRARY_PATH=/usr/lib/wsl/lib:$LD_LIBRARY_PATH`

### Windows端转录脚本

路径：`C:\Users\Robyn\Downloads\dbk_transcribe.py`

使用方式：
```bash
cmd.exe /c "python C:\Users\Robyn\Downloads\dbk_transcribe.py AUDIO_PATH OUTPUT_PATH"
```

**注意**：WSL无法直接执行cmd.exe，需要通过Windows终端或PowerShell。

## CSV管理

### 追加后去重

每次追加新视频到CSV后，必须去重：

```bash
# 检查重复
awk -F',' '{print $1}' video_list.csv | sort | uniq -d

# 去重（保留header + 第一次出现的行）
head -1 video_list.csv > /tmp/clean.csv
tail -n +2 video_list.csv | awk -F',' '!seen[$1]++' >> /tmp/clean.csv
cp /tmp/clean.csv video_list.csv
```

### CSV格式

```csv
video_id,date,title,transcribed
XXlkgNbS0v0,20260603,比特幣，BTC弱勢反彈了又怎樣？,yes
```

## 批量转录流程

### 推荐流程

1. **获取最新视频列表**
   ```bash
   yt-dlp --flat-playlist --print '%(id)s|%(title)s|%(duration)s' --playlist-end 10 'https://www.youtube.com/@dbk9527/videos'
   ```

2. **获取上传日期**
   ```bash
   yt-dlp --js-runtimes deno:/mnt/c/Users/Robyn/.deno/bin/deno.exe -j --no-playlist 'https://www.youtube.com/watch?v=VIDEO_ID' | jq -r '.upload_date'
   ```

3. **检查CSV是否已存在**
   ```bash
   grep "VIDEO_ID" video_list.csv
   ```

4. **转录（优先级）**
   - 方案1：youtube-transcript-api（秒级，最可靠）
   - 方案2：yt-dlp下载字幕（如果有）
   - 方案3：faster-whisper转录音频（分钟级，最后手段）

5. **更新CSV并去重**

### 目录结构

```
/mnt/h/大镖客蒸馏/
├── video_list.csv
├── 20260603/
│   ├── XXlkgNbS0v0.m4a          # 音频（可选）
│   ├── XXlkgNbS0v0_transcript.txt  # 转录文本
│   └── XXlkgNbS0v0_fw.txt        # faster-whisper转录（备用）
├── 20260602/
│   └── ...
└── ...
```

## 常见坑

1. **fetch_new_videos.py超时是常态**：不要依赖它，手动yt-dlp更可靠
2. **youtube-transcript-api首次失败≠永远失败**：重试即可
3. **faster-whisper在WSL需要CUDA库**：没有就用Windows端
4. **CSV追加会重复**：必须去重
5. **yt-dlp需要deno**：没有deno会报警告，但可能仍能工作
