# Windows deno PATH 修复备忘

## 问题
Windows端yt-dlp运行时报 `Sign in to confirm you're not a bot`，原因是找不到deno解n challenge。

## 根因
1. `setx PATH "xxx" /M` 写入时会产生尾引号bug，导致路径变成 `C:\Users\Administrator\.deno\bin"`（多个引号）
2. cmd.exe 新开窗口需要重新登录才能刷新注册表级环境变量
3. WindowsApps Python 启动的子进程不继承系统PATH更新

## 修复步骤

### 1. PowerShell写入（无引号bug）
```powershell
$current = [Environment]::GetEnvironmentVariable('Path', 'Machine')
$parts = $current -split ';' | Where-Object { $_.Trim() -ne '' -and $_ -notmatch '"' }
$clean = ($parts | Select-Object -Unique) -join ';'
[Environment]::SetEnvironmentVariable('Path', $clean, 'Machine')
```

### 2. 广播环境变量变更
```powershell
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public class Env {
    [DllImport("user32.dll", SetLastError = true, CharSet = CharSet.Auto)]
    public static extern IntPtr SendMessageTimeout(IntPtr hWnd, uint Msg, UIntPtr wParam, string lParam, uint fuFlags, uint uTimeout, out UIntPtr lpdwResult);
    public const int HWND_BROADCAST = 0xffff;
    public const uint WM_SETTINGCHANGE = 0x001A;
    public const uint SMTO_ABORTIFHUNG = 0x0002;
}
'@
$result = [UIntPtr]::Zero
[Env]::SendMessageTimeout([IntPtr]::new([Env]::HWND_BROADCAST), [Env]::WM_SETTINGCHANGE, [UIntPtr]::Zero, 'Environment', [Env]::SMTO_ABORTIFHUNG, 5000, [ref]$result)
```

### 3. 脚本内注入（最可靠）
即使系统PATH写入成功，脚本内仍建议显式注入：
```python
env = os.environ.copy()
env["PATH"] = r"C:\Users\Administrator\.deno\bin;" + env.get("PATH", "")
subprocess.run([...], env=env)
```

## 验证方法
```powershell
powershell.exe -Command "[Environment]::GetEnvironmentVariable('Path','Machine')" | tr ';' '\n' | grep deno
```
期望输出：`C:\Users\Administrator\.deno\bin`（无引号）
