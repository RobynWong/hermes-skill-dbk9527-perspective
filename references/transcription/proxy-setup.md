# yt-dlp + 代理 + deno PATH 排障记录

## 问题现象

WSL 通过 mihomo 代理拉 YouTube 频道列表时：
- `yt-dlp --flat-playlist ... @dbk9527/videos` 超时（>20秒）
- 单视频下载正常（`yt-dlp ... watch?v=xxx`）
- `curl --proxy http://127.0.0.1:9981 https://www.youtube.com` 正常返回

## 根因

yt-dlp 提取 YouTube 频道页依赖 **JavaScript 运行时**做页面渲染。
WSL 环境下默认无可用 JS runtime，导致 yt-dlp 反复尝试检测后超时。

## 解决方案

**必须设置 deno PATH**（deno 内置在 yt-dlp 的 JS runtime 支持）：

```bash
export PATH="/mnt/c/Users/Administrator/.deno/bin:$PATH"
```

此后频道列表拉取从 >20秒 超时降至 **~2秒**。

## 注意事项

- deno 在 **Windows 路径**：`/mnt/c/Users/Administrator/.deno/bin/deno.exe`
- 不在 WSL PATH 中，每次调用前必须显式设置
- 设置后 yt-dlp 输出中 `upload_date` 通过代理时返回 `NA`（元数据不完整），但 `video_id` + `title` 正常
- `--dateafter` 参数依赖 `upload_date`，所以不能用此参数做日期过滤，只能用增量对比法（逐条对比标题）

## 验证命令

```bash
export PATH="/mnt/c/Users/Administrator/.deno/bin:$PATH"
time yt-dlp --flat-playlist --print '%(upload_date)s|%(id)s|%(title)s' \
  --playlist-end 15 "https://www.youtube.com/@dbk9527/videos"
# 成功: <3秒，返回 video_id + title
# 失败: 超时
```
