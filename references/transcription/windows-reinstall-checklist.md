# Windows系统重装后GPU转录环境配置清单

## 前提条件
- Windows用户名: Robyn
- GPU: NVIDIA GeForce GTX 1080 8GB
- CUDA: 11.8（驱动版本522.25+）

## 必装组件（pip安装）

```cmd
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
pip install faster-whisper yt-dlp youtube-transcript-api
```

## 必装组件（手动安装）

### deno（yt-dlp绕过YouTube验证需要）
```cmd
powershell -c "irm https://deno.land/install.ps1 | iex"
```
安装路径: `C:\Users\Robyn\.deno\bin\deno.exe`

### ffmpeg（音频处理需要）
```cmd
winget install ffmpeg
```
或下载: https://github.com/BtbN/FFmpeg-Builds/releases

## 验证命令

```cmd
python -c "import torch; print(f'PyTorch: {torch.__version__}, CUDA: {torch.cuda.is_available()}')"
python -c "import faster_whisper; print(f'faster-whisper: {faster_whisper.__version__}')"
deno --version
ffmpeg -version
yt-dlp --version
```

## Python路径

Windows Store Python: `C:\Users\Robyn\AppData\Local\Microsoft\WindowsApps\python.exe`
- 这是2字节的Store stub，首次调用可能超时
- 实际Python包路径: `C:\Users\Robyn\AppData\Local\...\PythonSoftwareFoundation.Python.3.12_qbz5n2kfra8p0\`

## WSL环境（无需重装，不依赖Windows系统）

- yt-dlp: 2026.3.17
- youtube-transcript-api: 1.2.4
- ffmpeg: /usr/bin/ffmpeg
- torch: 有CUDA依赖问题，但WSL只用字幕API和CPU模式，不影响
