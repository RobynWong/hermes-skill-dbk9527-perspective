# Windows GPU转录环境诊断与修复

**重要**: Windows用户名为 `Robyn`，所有路径中使用 `C:\\Users\\Robyn\\`

## 诊断顺序

当Windows GPU转录失败时，按以下顺序排查：

### 1. 检查Python是否存在
```bash
cmd.exe /c "python --version"
```
应返回 `Python 3.12.10`。如不存在，需安装Python。

### 2. 快速环境检测脚本
```bash
cat > /tmp/check_gpu.py << 'EOF'
import sys
sys.stdout.reconfigure(encoding='utf-8')
print(f"Python: {sys.version}")

try:
    import torch
    print(f"PyTorch: {torch.__version__}")
    print(f"CUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"CUDA version: {torch.version.cuda}")
        print(f"GPU: {torch.cuda.get_device_name(0)}")
except ImportError:
    print("PyTorch: NOT INSTALLED")

try:
    import faster_whisper
    print(f"faster-whisper: {faster_whisper.__version__}")
except ImportError:
    print("faster-whisper: NOT INSTALLED")

try:
    import ctranslate2
    print(f"ctranslate2: {ctranslate2.__version__}")
    print(f"CUDA devices: {ctranslate2.get_cuda_device_count()}")
except ImportError:
    print("ctranslate2: NOT INSTALLED")
EOF

cp /tmp/check_gpu.py /mnt/c/Users/Robyn/AppData/Local/Temp/check_gpu.py
cmd.exe /c "python C:\\Users\\Robyn\\AppData\\Local\\Temp\\check_gpu.py"
```

### 3. 检查torch是否为GPU版
```bash
cmd.exe /c "python -m pip show torch"
```
**关键看Version行**：
- `2.12.0+cpu` → CPU版，必须重装
- `2.7.1+cu118` → GPU版（CUDA 11.8）

### 4. 检查NVIDIA驱动版本
```bash
nvidia-smi 2>&1 | head -5
```

**CUDA版本与最低驱动要求**：
| CUDA | 最低驱动 |
|------|---------|
| 11.8 | 520+ |
| 12.1 | 530+ |
| 12.4 | 550+ |

### 5. 检查cuDNN（ctranslate2 GPU必需）
```python
import ctranslate2
print(ctranslate2.get_cuda_device_count())  # 返回0 = 缺cuDNN
```

## 系统重装后完整安装清单

### 1. Python 3.12
下载: https://www.python.org/downloads/

### 2. PyTorch + CUDA 11.8
```cmd
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

### 3. faster-whisper及相关依赖
```cmd
pip install faster-whisper youtube-transcript-api
```
**注意**: yt-dlp只需在WSL安装，Windows端不需要

### 4. cuDNN（ctranslate2 GPU必需）
```cmd
pip install nvidia-cudnn-cu11
```
约800MB，安装后重启或设置环境变量：
```cmd
set CUDA_PATH=C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.8
```

### 5. deno（WSL端yt-dlp需要）
```cmd
powershell -c "irm https://deno.land/install.ps1 | iex"
```

### 6. ffmpeg
```cmd
winget install ffmpeg
```

### 7. 验证安装
```cmd
python -c "import torch; print(torch.cuda.is_available())"
python -c "import ctranslate2; print(ctranslate2.get_cuda_device_count())"
python -c "import faster_whisper; print('OK')"
```

## 修复步骤

### 修复1: 重装torch GPU版
```cmd
pip uninstall torch -y
pip install torch --index-url https://download.pytorch.org/whl/cu118
```

### 修复2: 安装cuDNN
```cmd
pip install nvidia-cudnn-cu11
```

## 已知陷阱

1. **Windows用户名是Robyn** - 所有路径用`C:\Users\Robyn\`
2. **torch CPU版静默安装** — 不报错，只在CUDA模块时报循环导入错误
3. **PyTorch设备属性是`total_memory`不是`total_mem`**
4. **deno必须在PATH中** — yt-dlp的n challenge需要
5. **系统重装后Python包全部丢失**
6. **Windows Store Python stub** — 首次调用需要初始化时间
7. **ctranslate2需要cuDNN** — CUDA Toolkit不够，必须单独装cuDNN
8. **Windows cmd用gbk编码** — 脚本必须加`sys.stdout.reconfigure(encoding='utf-8')`，不能用emoji
9. **Windows端没有yt-dlp** — 正确流程：WSL下载音频→传Windows路径
10. **WSL路径转Windows路径** — `/mnt/h/xxx` → `H:\xxx`
11. **dbk_transcribe.py参数** — 接受`(audio_path, output_path)`，不是`(video_id)`
