# CUDA Toolkit 安装指南（ctranslate2 GPU支持）

## 问题背景

PyTorch自带CUDA运行时，但ctranslate2（faster-whisper的底层引擎）需要**系统级CUDA Toolkit**。
症状：`ctranslate2.get_cuda_device_count()` 返回0，faster-whisper GPU模式报错：
```
RuntimeError: CUDA failed with error CUDA driver version is insufficient for CUDA runtime version
```

## 安装步骤

### 1. CUDA Toolkit 11.8

下载地址：https://developer.nvidia.com/cuda-11-8-0-download-archive

选择：
- Operating System: Windows
- Architecture: x86_64
- Version: 10 (或11)
- Installer Type: exe (local)

安装后验证：
```cmd
nvcc --version
```
应显示 `Cuda compilation tools, release 11.8`

### 2. cuDNN 8.x (for CUDA 11.x)

下载地址：https://developer.nvidia.com/rdp/cudnn-archive
（需要注册NVIDIA开发者账号）

选择：cuDNN v8.9.x for CUDA 11.x

安装方法：
1. 解压下载的zip
2. 将`bin\cudnn*.dll`复制到`C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.8\bin\`
3. 将`include\cudnn*.h`复制到`C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.8\include\`
4. 将`lib\x64\cudnn*.lib`复制到`C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.8\lib\x64\`

### 3. 验证安装

```cmd
:: 检查CUDA Toolkit
nvcc --version

:: 检查ctranslate2 CUDA支持
python -c "import ctranslate2; print(f'CUDA devices: {ctranslate2.get_cuda_device_count()}')"

:: 检查faster-whisper GPU模式
python -c "from faster_whisper import WhisperModel; m = WhisperModel('small', device='cuda'); print('OK')"
```

## 常见问题

### Q: PyTorch显示CUDA可用，为什么ctranslate2不行？
A: PyTorch自带CUDA运行时（打包在wheel中），不依赖系统CUDA Toolkit。ctranslate2使用不同的CUDA绑定方式，需要系统级安装。

### Q: 安装CUDA Toolkit后需要重启吗？
A: 是的，必须重启终端（最好重启电脑），否则环境变量不会生效。

### Q: CUDA版本选11.8还是12.x？
A: 选11.8。PyTorch cu118和ctranslate2都兼容CUDA 11.8。CUDA 12.x可能需要更新的NVIDIA驱动。
