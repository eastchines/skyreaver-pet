# ============================================================
#  SkyReaver 桌面宠物助手（PowerShell 零安装版）
#  由 启动桌宠.bat 调用运行。Windows 系统自带 PowerShell，无需安装任何软件。
#  功能：
#    - 手跟随按键 / 空格
#    - 闲置 10 秒变兽态绕圈
#    - 吃饱 60 分钟后饥饿，弹出“我要吃饭！”
#    - 右键宠物 -> 投喂文件夹 / 立即吃饱 / 退出
# ============================================================

$ErrorActionPreference = "Stop"

# ---------- 加载 WinForms / Drawing ----------
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

# ---------- C#：全局键盘钩子 + 输入法 ----------
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;

public static class WinHook
{
    private delegate IntPtr HookProc(int nCode, IntPtr wParam, IntPtr lParam);
    private static HookProc _proc;
    private static IntPtr _hook = IntPtr.Zero;
    public static event Action<int> KeyDown;

    [DllImport("user32.dll", SetLastError=true)]
    private static extern IntPtr SetWindowsHookEx(int idHook, HookProc lpfn, IntPtr hMod, uint dwThreadId);
    [DllImport("user32.dll", SetLastError=true)]
    private static extern bool UnhookWindowsHookEx(IntPtr hhk);
    [DllImport("user32.dll")]
    private static extern IntPtr CallNextHookEx(IntPtr hhk, int nCode, IntPtr wParam, IntPtr lParam);
    [DllImport("kernel32.dll", CharSet=CharSet.Auto)]
    private static extern IntPtr GetModuleHandle(string lpModuleName);
    [DllImport("user32.dll")]
    private static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")]
    private static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint pid);
    [DllImport("user32.dll")]
    private static extern IntPtr GetKeyboardLayout(uint idThread);

    public static void Start()
    {
        if (_hook != IntPtr.Zero) return;
        _proc = HookCallback;
        IntPtr hMod;
        using (System.Diagnostics.Process p = System.Diagnostics.Process.GetCurrentProcess())
        {
            hMod = GetModuleHandle(p.MainModule.ModuleName);
        }
        _hook = SetWindowsHookEx(13, _proc, hMod, 0);
    }

    public static void Stop()
    {
        if (_hook != IntPtr.Zero)
        {
            UnhookWindowsHookEx(_hook);
            _hook = IntPtr.Zero;
        }
    }

    public static int GetFgLayout()
    {
        try
        {
            IntPtr h = GetForegroundWindow();
            uint pid;
            uint tid = GetWindowThreadProcessId(h, out pid);
            return (int)(GetKeyboardLayout(tid).ToInt64() & 0xFFFF);
        }
        catch { return 0; }
    }

    private static IntPtr HookCallback(int nCode, IntPtr wParam, IntPtr lParam)
    {
        if (nCode >= 0 && wParam == (IntPtr)0x100) // WM_KEYDOWN
        {
            int vk = Marshal.ReadInt32(lParam);
            if (KeyDown != null) KeyDown(vk);
        }
        return CallNextHookEx(_hook, nCode, wParam, lParam);
    }
}
'@

# ---------- 全局状态 ----------
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

$script:mode     = "beast"     # beast / girl
$script:state    = "active"    # active / idle
$script:hungry   = $false
$script:walkPhase = 0.0

$script:lastInputTick = [Environment]::TickCount   # 键盘钩子线程写入（原子安全）
$script:fedTick       = [Environment]::TickCount

$script:handX = 300.0
$script:handY = 90.0
$script:handTX = 300.0
$script:handTY = 90.0

# ---------- 配置 ----------
$IDLE_SECONDS   = 10
$HUNGRY_SECONDS = 60 * 60
$SMOOTH         = 0.35
$FRAME_MS       = 20
$WALK_SPEED     = 2.0

$CANVAS_W = 780
$CANVAS_H = 520

$BODY_ACTIVE_X = 180
$BODY_ACTIVE_Y = 60

$WALK_MIN_X = 20;  $WALK_MIN_Y = 30
$WALK_MAX_X = $CANVAS_W - 360
$WALK_MAX_Y = $CANVAS_H - 360

$CN_LAYOUT = 0x0804

# 键位（窗口坐标，键帽中心）
$script:keyPos = @{
  "q"=@(140,250); "w"=@(168,252); "e"=@(196,256); "r"=@(220,259);
  "t"=@(244,261); "y"=@(266,261); "u"=@(288,262);
  "a"=@(142,282); "s"=@(165,284); "d"=@(188,286); "f"=@(212,289);
  "g"=@(236,290); "h"=@(258,291); "j"=@(280,291);
  "z"=@(146,300); "x"=@(167,302); "c"=@(191,304); "v"=@(214,305);
  "b"=@(236,306); "n"=@(258,307); "m"=@(280,307);
  "space"=@(170,322)
}

# ---------- 图片路径 ----------
$imgBeastBody = Join-Path $scriptDir "beast_body.png"
$imgBeastHand = Join-Path $scriptDir "beast_hand.png"
$imgGirlBody  = Join-Path $scriptDir "girl_body.png"
$imgGirlHand  = Join-Path $scriptDir "girl_hand.png"

# ---------- 窗体 ----------
$form = New-Object System.Windows.Forms.Form
$form.FormBorderStyle = [System.Windows.Forms.FormBorderStyle]::None
$form.StartPosition = [System.Windows.Forms.FormStartPosition]::Manual
$form.Location = New-Object System.Drawing.Point(120,150)
$form.Size = New-Object System.Drawing.Size($CANVAS_W,$CANVAS_H)
$form.TopMost = $true
$form.BackColor = [System.Drawing.Color]::Magenta
$form.TransparencyKey = [System.Drawing.Color]::Magenta
$form.ShowInTaskbar = $false

# ---------- 身体层 / 手层 ----------
$body = New-Object System.Windows.Forms.PictureBox
$body.Location = New-Object System.Drawing.Point($BODY_ACTIVE_X,$BODY_ACTIVE_Y)
$body.SizeMode = [System.Windows.Forms.PictureBoxSizeMode]::AutoSize
$body.BackColor = [System.Drawing.Color]::Magenta
$body.Image = [System.Drawing.Image]::FromFile($imgBeastBody)
$form.Controls.Add($body)

$hand = New-Object System.Windows.Forms.PictureBox
$hand.Location = New-Object System.Drawing.Point(300,90)
$hand.SizeMode = [System.Windows.Forms.PictureBoxSizeMode]::AutoSize
$hand.BackColor = [System.Drawing.Color]::Magenta
$hand.Image = [System.Drawing.Image]::FromFile($imgBeastHand)
$form.Controls.Add($hand)
$hand.BringToFront()

# ---------- 饥饿提示文字 ----------
$banner = New-Object System.Windows.Forms.Label
$banner.Location = New-Object System.Drawing.Point(0,10)
$banner.Size = New-Object System.Drawing.Size($CANVAS_W,50)
$banner.TextAlign = [System.Drawing.ContentAlignment]::MiddleCenter
$banner.Font = New-Object System.Drawing.Font("Microsoft YaHei",20,[System.Drawing.FontStyle]::Bold)
$banner.ForeColor = [System.Drawing.Color]::Red
$banner.BackColor = [System.Drawing.Color]::Magenta
$banner.Text = ""
$form.Controls.Add($banner)
$banner.BringToFront()

# ---------- 切换形象 ----------
function Set-Mode([string]$m) {
    if ($m -eq $script:mode) { return }
    $script:mode = $m
    if ($m -eq "beast") {
        $body.Image = [System.Drawing.Image]::FromFile($imgBeastBody)
        $hand.Image = [System.Drawing.Image]::FromFile($imgBeastHand)
    } else {
        $body.Image = [System.Drawing.Image]::FromFile($imgGirlBody)
        $hand.Image = [System.Drawing.Image]::FromFile($imgGirlHand)
    }
}

# ---------- 键盘虚拟键 -> 键名 ----------
function Get-KeyName([int]$vk) {
    if ($vk -eq 0x20) { return "space" }
    if ($vk -ge 0x41 -and $vk -le 0x5A) { return ([char]($vk + 0x20)).ToString() }
    return $null
}

# ---------- 键盘钩子回调 ----------
[WinHook]::KeyDown = {
    param([int]$vk)
    $script:lastInputTick = [Environment]::TickCount
    $k = Get-KeyName $vk
    if ($k -ne $null -and $script:state -eq "active" -and $script:keyPos.ContainsKey($k)) {
        $pt = $script:keyPos[$k]
        $script:handTX = [double]$pt[0]
        $script:handTY = [double]$pt[1]
    }
}

# ---------- 绕圈位置 ----------
function Get-WalkPos([double]$phase) {
    $w = $WALK_MAX_X - $WALK_MIN_X
    $h = $WALK_MAX_Y - $WALK_MIN_Y
    $seg = $phase % 4.0
    if ($seg -lt 1) { $t=$seg; return @($WALK_MIN_X + $w*$t, $WALK_MIN_Y) }
    elseif ($seg -lt 2) { $t=$seg-1; return @($WALK_MAX_X, $WALK_MIN_Y + $h*$t) }
    elseif ($seg -lt 3) { $t=$seg-2; return @($WALK_MAX_X - $w*$t, $WALK_MAX_Y) }
    else { $t=$seg-3; return @($WALK_MIN_X, $WALK_MAX_Y - $h*$t) }
}

# ---------- 投喂 ----------
function Feed-Folder {
    $dlg = New-Object System.Windows.Forms.FolderBrowserDialog
    $dlg.Description = "选择一个文件夹，让宠物吃掉"
    if ($dlg.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK -and $dlg.SelectedPath) {
        $name = Split-Path -Leaf $dlg.SelectedPath
        $script:fedTick = [Environment]::TickCount
        $script:hungry = $false
        $banner.Text = "已吃掉：$name"
        $script:tb.Stop(); $script:tb.Start()
        [System.Windows.Forms.MessageBox]::Show("宠物吃掉了文件夹“$name”，现在吃饱啦！","投喂成功")
    }
}
function Feed-Now {
    $script:fedTick = [Environment]::TickCount
    $script:hungry = $false
    $banner.Text = "吃饱啦！"
    $script:tb.Stop(); $script:tb.Start()
}

# ---------- 右键菜单 ----------
$menu = New-Object System.Windows.Forms.ContextMenu
$miFeed  = New-Object System.Windows.Forms.MenuItem("投喂文件夹…", { Feed-Folder })
$miNow   = New-Object System.Windows.Forms.MenuItem("立即吃饱（测试）", { Feed-Now })
$miSep   = New-Object System.Windows.Forms.MenuItem("-")
$miExit  = New-Object System.Windows.Forms.MenuItem("退出", { $form.Close() })
$menu.MenuItems.Add($miFeed) | Out-Null
$menu.MenuItems.Add($miNow)  | Out-Null
$menu.MenuItems.Add($miSep)  | Out-Null
$menu.MenuItems.Add($miExit) | Out-Null
$body.ContextMenu = $menu
$form.ContextMenu = $menu

# 投喂/吃饱提示的自动消失定时器（显示 2 秒后清空，除非饥饿常驻）
$form.Add_Shown({ })
$timerBanner = New-Object System.Windows.Forms.Timer
$timerBanner.Interval = 2000
$timerBanner.Add_Tick({
    if (-not $script:hungry) { $banner.Text = "" }
    $timerBanner.Stop()
})
$script:tb = $timerBanner

# ---------- 主动画定时器 ----------
$anim = New-Object System.Windows.Forms.Timer
$anim.Interval = $FRAME_MS
$anim.Add_Tick({
    $now = [Environment]::TickCount
    $idleMs = $now - $script:lastInputTick

    # 1) 闲置 -> 绕圈
    $idleNow = ($idleMs / 1000.0) -gt $IDLE_SECONDS
    if ($idleNow -and $script:state -eq "active") {
        $script:state = "idle"
        Set-Mode "beast"
    }
    elseif (-not $idleNow -and $script:state -eq "idle") {
        $script:state = "active"
        $body.Location = New-Object System.Drawing.Point($BODY_ACTIVE_X,$BODY_ACTIVE_Y)
        $script:handTX = 300.0; $script:handTY = 90.0
    }

    # 2) 绕圈运动
    if ($script:state -eq "idle") {
        $script:walkPhase += $WALK_SPEED * $FRAME_MS / 1000.0
        $wp = Get-WalkPos $script:walkPhase
        $body.Location = New-Object System.Drawing.Point([int]$wp[0],[int]$wp[1])
        $hand.Location = New-Object System.Drawing.Point([int]($wp[0]+300),[int]($wp[1]+90))
    }
    else {
        # 手平滑跟随
        $script:handX += ($script:handTX - $script:handX) * $SMOOTH
        $script:handY += ($script:handTY - $script:handY) * $SMOOTH
        $hand.Location = New-Object System.Drawing.Point([int]$script:handX,[int]$script:handY)
    }

    # 3) 饥饿判定
    if (-not $script:hungry -and (($now - $script:fedTick) / 1000.0) -gt $HUNGRY_SECONDS) {
        $script:hungry = $true
        $banner.Text = "我要吃饭！"
    }

    # 4) 输入法切换形象（中文=少女）
    try {
        $lid = [WinHook]::GetFgLayout()
        if ($lid -eq $CN_LAYOUT) { Set-Mode "girl" } else { Set-Mode "beast" }
    } catch { }
})
$anim.Start()

# ---------- 启动与清理 ----------
$form.Add_Shown({
    [WinHook]::Start()
})
$form.Add_FormClosed({
    [WinHook]::Stop()
    try { $anim.Stop() } catch { }
})

[System.Windows.Forms.Application]::Run($form)
