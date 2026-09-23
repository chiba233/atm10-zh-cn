# atm10-zh-cn — All the Mods 10 简体中文汉化补丁「绿油油版」
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
# ATM10 @@MCVER@@ 汉化补丁「绿油油版」安装器 (Windows)
# 版本号一律用 @@MCVER@@ 占位，由 scripts/build_dist.sh 按目标整合包版本填。
# 用法：把整个汉化文件夹放进 ATM10 实例根目录后，双击「双击安装-Windows.bat」，
# 或在 PowerShell 中运行：
#   .\install.ps1                    # 交互菜单
#   .\install.ps1 apply              # 应用汉化（自动先备份，不含可选mods）
#   .\install.ps1 apply-with-pinyin  # 应用汉化 + 安装可选 JEI 拼音搜索 mod
#   .\install.ps1 backup             # 仅备份
#   .\install.ps1 restore [备份名]   # 恢复备份
param(
    [string]$Action = '',
    [string]$BackupName = '',
    [string]$TargetPath = ''
)
$ErrorActionPreference = 'Stop'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $ScriptDir
# 中文输出：cmd 侧已 chcp 65001，这里让 PowerShell 也按 UTF-8 写控制台
try { [Console]::OutputEncoding = [Text.UTF8Encoding]::new($false) } catch {}
$script:Target = if ($TargetPath) { $TargetPath } else { Split-Path -Parent $ScriptDir }
$PackDirs = @('config', 'kubejs', 'mods', 'resourcepacks', 'vaultpatcher')
$PackEntry = 'file/ATM10汉化包-@@MCVER@@.zip'
$PinyinDir = '可选mods-拼音搜索'
$script:TS = ''
$script:BK = ''
# 就地解压：用户把压缩包内容直接解到了实例根目录，此时「源」和「目标」是同一个目录，
# 再复制一次就是 Copy-Item 自己覆盖自己 → IOException。这种情况文件本来就已到位。
$script:InPlace = $false
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)

# ── 长路径 ──────────────────────────────────────────────────────────────
# 备份层比游戏自己的路径多出 `\汉化文件夹\backups\<时间戳>\` 四十来个字符，于是实例
# 目录稍深一点就会出现「原文件读得到、它的备份写不进去」。超过 MAX_PATH 时 Win32 返回
# ERROR_PATH_NOT_FOUND，而 .NET 4.6.2 起不再在托管层判长度，抛出来的是
# DirectoryNotFoundException（「Could not find a part of the path」），看着像目录没建成。
# `\\?\` 前缀能绕开，但它不做任何规范化、只认绝对路径，PowerShell 5.1 的 FileSystem
# 提供程序也不收这种路径。所以这里只在**今天必然抛异常的长度上**才切到 .NET API：
# 短路径照旧走 Copy-Item，行为一个字不变；非 Windows 整套短路（那里没有 MAX_PATH）。
$script:OnWindows = ($PSVersionTable.PSVersion.Major -lt 6) -or $IsWindows
# 文件路径上限 259 个字符，目录还要给 8.3 短名留 12 个，所以是 247。
function Test-LongFilePath([string]$p) { return ($script:OnWindows -and $p -and $p.Length -gt 259) }
function Test-LongDirPath([string]$p)  { return ($script:OnWindows -and $p -and $p.Length -gt 247) }

function To-ExtendedPath([string]$p) {
    # 任何一步出意外都原样退回：宁可维持今天的行为，也不能让这个帮手把正常环境弄挂。
    if (-not $script:OnWindows -or -not $p) { return $p }
    if ($p.StartsWith('\\?\')) { return $p }
    try { $full = [System.IO.Path]::GetFullPath($p) } catch { return $p }
    if ($full.StartsWith('\\')) { return '\\?\UNC\' + $full.Substring(2) }
    if ($full -match '^[A-Za-z]:\\')  { return '\\?\' + $full }
    return $p
}

function New-DirForFile([string]$file) {
    $dir = Split-Path $file
    if (Test-LongDirPath $dir) { $dir = To-ExtendedPath $dir }
    [void][System.IO.Directory]::CreateDirectory($dir)
}

function Copy-OneFile([string]$from, [string]$to, [switch]$Force) {
    if ((Test-LongFilePath $from) -or (Test-LongFilePath $to)) {
        [System.IO.File]::Copy((To-ExtendedPath $from), (To-ExtendedPath $to), $true)
    } elseif ($Force) {
        Copy-Item -LiteralPath $from -Destination $to -Force
    } else {
        Copy-Item -LiteralPath $from -Destination $to
    }
}

function Get-FilesUnder([string]$root) {
    # 返回相对 $root 的路径。先照旧走 Get-ChildItem —— 正常情况下行为与过去完全一致，
    # 包括它默认跳过隐藏文件这一条；只有它整条炸掉（5.1 碰上超长路径就是如此）才退到
    # 扩展路径枚举。**先整体装进变量再返回**：半截失败不会把已枚举的那部分漏出去变成重复项。
    $rel = $null
    try {
        $rel = @(Get-ChildItem -LiteralPath $root -Recurse -File |
                 ForEach-Object { $_.FullName.Substring($root.Length + 1) })
    } catch { $rel = $null }
    if ($null -eq $rel) {
        $r = To-ExtendedPath $root
        $rel = @([System.IO.Directory]::EnumerateFiles($r, '*', [System.IO.SearchOption]::AllDirectories) |
                 ForEach-Object { $_.Substring($r.Length + 1) })
    }
    return $rel
}

# 判定一个目录是不是游戏实例根目录。
# 不能只看 options.txt —— **刚装好、一次都没启动过的整合包没有 options.txt**
# （它是 Minecraft 首次退出时才写的）。也不能只看 mods\ —— 汉化包自己的文件夹里
# 也有个 mods\（装着 vaultpatcher.jar）。用 jar 数量区分：ATM10 有 400+ 个，汉化包只有 1 个。
# ── 版本检查 ────────────────────────────────────────────────────────────
# 补丁自己的版本号，由 build_dist.sh 现填。
$script:PatchVer = '@@PATCHVER@@'
$script:PackMcVer = '@@MCVER@@'
$script:Repo     = 'chiba233/atm10-zh-cn'
$script:LatestRelease = $null

# 取仓库最新**正式版**的 tag。releases/latest 天然跳过预发布，正合用：
# 测试版不该被当成「最新版」去催人升级。
# 任何一步不成（没网、被限流、TLS 不通）都返回 $null，**绝不因此拦住安装**。
function Get-LatestRelease {
    if ($env:ATM_SKIP_UPDATE_CHECK -eq '1') { return $null }
    try {
        $old = $ProgressPreference; $ProgressPreference = 'SilentlyContinue'
        # 老一点的 Windows PowerShell 默认还在用 TLS 1.0，GitHub 早就不收了
        try { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 } catch {}
        $r = Invoke-RestMethod -Uri "https://api.github.com/repos/$($script:Repo)/releases/latest" `
                               -Headers @{ 'Accept' = 'application/vnd.github+json'
                                           'User-Agent' = 'atm10-zh-cn-installer' } `
                               -TimeoutSec 6
        $ProgressPreference = $old
        return $r
    } catch { return $null }
}

function Normalize-Ver([string]$v) { if ($v -and $v.StartsWith('v')) { $v.Substring(1) } else { $v } }

function Check-Update {
    if ($env:ATM_SKIP_UPDATE_CHECK -eq '1') { return }
    $isBeta = $script:PatchVer -match '(?i)beta|rc\d|^dev$'
    $script:LatestRelease = Get-LatestRelease
    $latest = if ($script:LatestRelease) { $script:LatestRelease.tag_name } else { $null }
    if ($isBeta) {
        Write-Host ''
        Write-Host "⚠️ 你装的是**测试版**：$($script:PatchVer)"
        Write-Host '   测试版可能有没发现的问题。遇到异常请提交 issue：'
        Write-Host "   https://github.com/$($script:Repo)/issues"
        if ($latest) {
            Write-Host "   在问题解决前，建议先切回正式版 ${latest}："
            Write-Host "   https://github.com/$($script:Repo)/releases/latest"
        }
        Write-Host ''
        return
    }
    if (-not $latest) { return }        # 查不到就当没这回事
    if ((Normalize-Ver $latest) -eq (Normalize-Ver $script:PatchVer)) {
        Write-Host "✓ 版本检查：$($script:PatchVer) 已是最新正式版"
    } else {
        Write-Host ''
        Write-Host '⚠️ 你装的不是最新版本'
        Write-Host "   当前包：$($script:PatchVer)      最新正式版：$latest"
        Write-Host '   建议先下最新版再装，老版本的已知问题不会再修：'
        Write-Host "   https://github.com/$($script:Repo)/releases/latest"
        Write-Host ''
    }
}

function Invoke-OneClickUpdate {
    $release = $script:LatestRelease
    if (-not $release) { $release = Get-LatestRelease }
    if (-not $release) {
        Write-Host '❌ 无法获取最新版信息，请检查网络后重试。'
        return
    }

    $latest = $release.tag_name
    if ((Normalize-Ver $latest) -eq (Normalize-Ver $script:PatchVer)) {
        Write-Host "✓ $($script:PatchVer) 已是最新正式版，无需更新。"
        return
    }

    # Release 同时带三个 ATM10 版本和客户端/服务端包；必须按当前包的 ATM 版本
    # 精确选择客户端 zip，不能只取 assets[0]，否则会把 7.0 用户升级到 7.2 包。
    $suffix = '-atm' + [regex]::Escape($script:PackMcVer) + '\.zip$'
    $asset = @($release.assets | Where-Object {
        $_.name -match '^atm10-zh_cn-client-.+' -and $_.name -match $suffix
    }) | Select-Object -First 1
    if (-not $asset) {
        Write-Host "❌ 最新版 $latest 没有 ATM10 $($script:PackMcVer) 的客户端安装包，未做任何改动。"
        return
    }
    $digest = [string]$asset.digest
    if ($digest -notmatch '^sha256:([0-9a-fA-F]{64})$') {
        Write-Host "❌ 最新版 $latest 的客户端安装包缺少有效的 SHA-256 摘要，拒绝安装。"
        return
    }
    $expectedSha256 = $Matches[1]

    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $stage = Join-Path $script:Target ".atm10-hanhua-update-$stamp"
    $zip = Join-Path $stage $asset.name
    $newInstallerStarted = $false
    $newInstallComplete = $false
    $newBackupsMerged = $false
    try {
        [void][System.IO.Directory]::CreateDirectory($stage)
        Write-Host "正在下载 $($asset.name)……"
        Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $zip -UseBasicParsing `
            -Headers @{ 'User-Agent' = 'atm10-zh-cn-installer' } -TimeoutSec 120
        $actualSha256 = (Get-FileHash -LiteralPath $zip -Algorithm SHA256).Hash
        if (-not [string]::Equals($actualSha256, $expectedSha256,
                                   [System.StringComparison]::OrdinalIgnoreCase)) {
            throw '下载文件的 SHA-256 与 GitHub Release 摘要不一致。'
        }
        Expand-Archive -LiteralPath $zip -DestinationPath $stage -Force
        $next = @(Get-ChildItem -LiteralPath $stage -Recurse -Filter 'install.ps1' -File |
                  Where-Object { $_.Directory.Name -eq 'atm10-zh_cn-client' }) | Select-Object -First 1
        if (-not $next) { throw '下载包中没有预期的客户端安装器。' }

        Write-Host '下载完成，正在由新版安装器备份并应用汉化……'
        $newInstallerStarted = $true
        & powershell -NoProfile -ExecutionPolicy Bypass -File $next.FullName apply -TargetPath $script:Target
        if ($LASTEXITCODE -ne 0) { throw "新版安装器退出码：$LASTEXITCODE" }
        $newInstallComplete = $true
        Merge-UpdateBackups $next.Directory.FullName
        $newBackupsMerged = $true
        Update-SourcePackage $next.Directory.FullName
        Write-Host "✅ 已更新到 $latest。新版安装器保留在：$stage"
        Write-Host "   本次备份已归入原安装包：$(Join-Path $ScriptDir 'backups')"
        Write-Host '   请退出并重新启动游戏后生效；确认无误前不要删除该目录。'
    } catch {
        Write-Host "❌ 一键更新失败：$($_.Exception.Message)"
        if ($newInstallComplete) {
            Write-Host '   新版汉化已经安装，但原安装包未能更新。'
            Write-Host "   之后请从这个新版目录运行安装器：$($next.Directory.FullName)"
            if ($newBackupsMerged) {
                Write-Host "   本次备份已归入原安装包：$(Join-Path $ScriptDir 'backups')"
            } else {
                Write-Host "   本次备份仍在新版目录：$(Join-Path $next.Directory.FullName 'backups')"
            }
        } elseif ($newInstallerStarted) {
            $newBackups = Join-Path $next.Directory.FullName 'backups'
            Write-Host '   新版安装器已经启动，实例可能只完成了部分更新。'
            Write-Host "   请先用新版安装器的 restore 功能恢复本次备份：$newBackups"
        } else {
            Write-Host "   新版安装器尚未启动；已下载的临时文件（如有）保留在：$stage"
        }
    }
}

function Merge-UpdateBackups([string]$newDir) {
    # 新版安装器把备份写在下载目录；原入口的 restore 只读取 ScriptDir/backups。
    # 成功更新后必须将备份归并到原入口，否则用户无法通过日常双击的安装器回滚。
    $from = Join-Path $newDir 'backups'
    if (-not (Test-Path -LiteralPath $from)) { return }
    $to = Join-Path $ScriptDir 'backups'
    [void][System.IO.Directory]::CreateDirectory($to)
    foreach ($backup in Get-ChildItem -LiteralPath $from -Directory) {
        $dest = Join-Path $to $backup.Name
        $n = 1
        while (Test-Path -LiteralPath $dest) {
            $dest = Join-Path $to "$($backup.Name)-update-$n"
            $n++
        }
        Move-Item -LiteralPath $backup.FullName -Destination $dest
    }
}

function Update-SourcePackage([string]$newDir) {
    # 用户今后仍会双击最初解压出来的 bat。只把游戏实例更新而不更新这个源目录，
    # 下次运行旧安装器会再次提示升级，甚至把旧 payload 覆盖回去。
    # 正常安装时源目录与实例分开，可以安全地以新版 payload 整体替换；就地解压时
    # 源目录就是实例，刚才的新版安装器已完成 payload 覆盖，绝不能删除实例目录。
    if (-not $script:InPlace) {
        foreach ($d in @($PackDirs + $PinyinDir)) {
            $old = Join-Path $ScriptDir $d
            $new = Join-Path $newDir $d
            if (Test-Path -LiteralPath $old) {
                Remove-Item -LiteralPath $old -Recurse -Force
            }
            if (Test-Path -LiteralPath $new) {
                Copy-Item -LiteralPath $new -Destination $old -Recurse -Force
            }
        }
    }

    # 当前 PowerShell 已把脚本读入内存，替换自身不会中断本次更新；bat 也只会在
    # 下次双击时读取。因此两个 Windows 入口都能安全换成新版。
    foreach ($f in @('install.ps1', '双击安装-Windows.bat', 'install-windows.bat')) {
        $new = Join-Path $newDir $f
        if (Test-Path -LiteralPath $new) {
            Copy-Item -LiteralPath $new -Destination (Join-Path $ScriptDir $f) -Force
        }
    }
    Write-Host '✅ 已将原安装包更新为新版；以后继续双击原来的安装 bat 即可。'
}

function Test-Instance([string]$d) {
    if (!(Test-Path -LiteralPath (Join-Path $d 'mods'))) { return $false }
    if (Test-Path -LiteralPath (Join-Path $d 'options.txt')) { return $true }
    $n = @(Get-ChildItem -LiteralPath (Join-Path $d 'mods') -Filter '*.jar' -File -ErrorAction SilentlyContinue).Count
    return ($n -ge 20)
}

function Set-InPlace {
    $a = (Resolve-Path -LiteralPath $ScriptDir).Path.TrimEnd('\')
    $b = (Resolve-Path -LiteralPath $script:Target).Path.TrimEnd('\')
    if ($a -eq $b) {
        $script:InPlace = $true
        Write-Host 'ℹ️ 检测到汉化文件已经在实例根目录里（压缩包内容被直接解压到了这一层）。'
        Write-Host '   文件本来就已到位，无需复制；本次只做 options.txt 的资源包启用。'
        Write-Host '   ⚠️ 这种装法没有备份可回退——原文件在你解压覆盖的那一刻就没了。'
        Write-Host '   想要可回退的安装，请解压到别处、把整个文件夹放进实例根目录再运行安装器。'
    }
}

function Check-Target {
    if (Test-Instance $script:Target) {
        Set-InPlace
        return
    }
    # 就地解压：脚本自己所在的这一层就是实例根目录
    if (Test-Instance $ScriptDir) {
        $script:Target = $ScriptDir
        Set-InPlace
        return
    }
    Write-Host '⚠️ 上一级目录不是游戏实例根目录（含 mods\ 的那一层）。'
    while ($true) {
        $inp = Read-Host '请输入 ATM10 实例根目录完整路径（q 退出）'
        $inp = $inp.Trim()
        if ($inp -eq 'q' -or [string]::IsNullOrWhiteSpace($inp)) { exit 1 }
        # 去掉整体包裹的成对引号（Windows 拖拽/粘贴带空格路径常加双引号）
        if (($inp.StartsWith('"') -and $inp.EndsWith('"')) -or ($inp.StartsWith("'") -and $inp.EndsWith("'"))) {
            $inp = $inp.Substring(1, $inp.Length - 2)
        }
        $inp = $inp.TrimEnd('\', '/')
        if (Test-Instance $inp) {
            $script:Target = $inp
            Write-Host "✅ 目标实例: $script:Target"
            Set-InPlace
            return
        }
        Write-Host '❌ 该路径下没找到 ATM10 的 mods\（应该有几百个 .jar），请重试。'
    }
}

function Get-PayloadFiles {
    foreach ($d in $PackDirs) {
        # ⚠️ 必须用**绝对**路径。Windows PowerShell 5.1 里，当前目录含 [ ] 时，
        # 相对路径即使配 -LiteralPath 也会在 provider 层被当通配符解析，
        # 结果是一个文件都枚举不到 → 安装器什么都不装。玩家路径里出现
        # 「[0.9.1正式版]」这种目录名并不罕见（整合包分享站的常见命名）。
        $abs = Join-Path $ScriptDir $d
        if (Test-Path -LiteralPath $abs) {
            Get-FilesUnder $abs | Where-Object { [System.IO.Path]::GetFileName($_) -ne '.DS_Store' } | ForEach-Object {
                Join-Path $d $_
            }
        }
    }
}

function Do-Backup {
    if ($script:InPlace) {
        Write-Host '⚠️ 就地解压模式下没有可备份的原文件（已被解压覆盖），跳过备份。'
        return
    }
    # 备份是**覆盖**式写入：同一秒里装第二次会撞上同一个目录，于是第二次备份的是
    # 已经汉化过的文件，把第一次那份原文盖掉，玩家的回退数据就没了。撞上就往后加序号。
    $script:TS = Get-Date -Format 'yyyyMMdd-HHmmss'
    # 序号补零：恢复界面按名字排序取最后一个当「最近一次」，不补零 -10 会排在 -2 前面。
    if (Test-Path -LiteralPath (Join-Path $ScriptDir "backups/$script:TS")) {
        $i = 2
        while (Test-Path -LiteralPath (Join-Path $ScriptDir ('backups/{0}-{1:d2}' -f $script:TS, $i))) { $i++ }
        $script:TS = '{0}-{1:d2}' -f $script:TS, $i
    }
    $script:BK = Join-Path $ScriptDir "backups/$script:TS"
    [System.IO.Directory]::CreateDirectory($script:BK) | Out-Null
    $newFiles = @()
    $n = 0
    foreach ($f in Get-PayloadFiles) {
        $dst = Join-Path $script:Target $f
        if (Test-Path -LiteralPath $dst) {
            $to = Join-Path $script:BK $f
            New-DirForFile $to
            Copy-OneFile $dst $to
            $n++
        } else {
            $newFiles += $f
        }
    }
    if ($newFiles.Count -gt 0) {
        [System.IO.File]::WriteAllLines((Join-Path $script:BK '新增文件清单.txt'), $newFiles, $Utf8NoBom)
    }
    if (Test-Path -LiteralPath (Join-Path $script:Target 'options.txt')) {
        Copy-Item -LiteralPath (Join-Path $script:Target 'options.txt') -Destination (Join-Path $script:BK 'options.txt')
    }
    Write-Host "✅ 已备份 $n 个将被覆盖的文件到 backups/$script:TS/"
}

# ATM10 @@MCVER@@ 默认启用的资源包，顺序照抄游戏自己写出来的 options.txt。
# 为什么要写死这一串：全新实例没有 options.txt，如果只写我们一个包，
# 游戏首次启动会把这 15 个内置包**全部插到我们后面**（实测汉化包落到第 3 位，
# 被 mod_resources 和五百多个模组包压在底下，汉化基本不生效）。
# 资源包是**后面的覆盖前面的**，我们必须排在最后一个。
# 这一串由 build_dist.sh 按目标版本现填（versions/<版本>/default_resource_packs.txt），
# 与 install.sh 用的是同一个占位符。以前这里写死的是 7.2 的列表，7.0/7.1 的 Windows 包
# 也拿它——而且用的是单引号字符串，里面的 "" 会**原样保留两个双引号**，写出来的
# resourcePacks 数组根本解析不了，游戏直接回落默认列表 = 汉化没启用。（issue #9 P1-2）
$DefaultPacks = '@@DEFAULT_PACKS@@'

function Patch-Options {
    $opt = Join-Path $script:Target 'options.txt'
    if (!(Test-Path -LiteralPath $opt)) {
        # ⚠️ 只有**从没启动过**的实例才允许新建 options.txt。玩过的实例必然有 logs/ 或
        # saves/；这时 options.txt 却不见了，多半是选错了目录（启动器没做版本隔离时，
        # 设置在 .minecraft\options.txt）。写一份只有两行的进去，游戏会把其余项按默认值
        # 补齐——玩家的键位 / 视频 / 音量当场全没。有玩家报过这个（R12 修复）。
        $played = (Test-Path -LiteralPath (Join-Path $script:Target 'logs')) -or
                  (Test-Path -LiteralPath (Join-Path $script:Target 'saves')) -or
                  (Test-Path -LiteralPath (Join-Path $script:Target 'usercache.json'))
        if ($played) {
            Write-Host '⚠️ 这个实例明显启动过（有 logs/ 或 saves/），却找不到 options.txt。'
            Write-Host '   为避免把你的键位 / 视频 / 音量设置冲掉，本次**不新建** options.txt。'
            Write-Host "   请确认目标目录是否正确：$($script:Target)"
            Write-Host '   （启动器没开「版本隔离」时，设置在 .minecraft\options.txt，那一层才是实例根目录）'
            Write-Host '   确认无误后进游戏 → 选项 → 资源包，手动把「汉化包」拖到已启用一侧的最后一位。'
            return
        }
        if ($DefaultPacks) {
            $line = 'resourcePacks:[' + $DefaultPacks + ',"' + $PackEntry + '"]'
            [System.IO.File]::WriteAllText($opt, "lang:zh_cn`n$line`n", $Utf8NoBom)
            Write-Host 'ℹ️ 这个实例还没启动过（没有 options.txt），已新建一份并写入中文语言与汉化资源包。'
            Write-Host '   首次启动游戏时 Minecraft 会自动补齐其余设置。'
            Write-Host '   💡 若首次进游戏后发现翻译没生效，退出游戏再跑一次本安装器即可——'
            Write-Host '      那说明你的整合包比预期多了几个内置资源包，重跑会把汉化包重新挪到最后一位。'
        } else {
            # 这一版的内置资源包顺序没实测过。**绝不伪造**——只写我们一个包的话，
            # 游戏首次启动会把内置包全插到它后面，汉化包等于没启用。
            [System.IO.File]::WriteAllText($opt, "lang:zh_cn`n", $Utf8NoBom)
            Write-Host 'ℹ️ 这个实例还没启动过（没有 options.txt），已写入中文语言。'
            Write-Host '   ⚠️ 资源包顺序需要两步：先启动一次游戏让 Minecraft 生成完整的资源包列表，'
            Write-Host '      退出游戏后再运行一次本安装器，它会把汉化包挪到列表最后一位（必须在最后才生效）。'
        }
        return
    }
    $lines = [System.IO.File]::ReadAllLines($opt)
    $idx = -1
    for ($i = 0; $i -lt $lines.Length; $i++) {
        if ($lines[$i].StartsWith('resourcePacks:[')) { $idx = $i; break }
    }
    if ($idx -lt 0) {
        Write-Host '⚠️ options.txt 中没有 resourcePacks 行，请进游戏手动启用资源包'
        return
    }
    $cur = $lines[$idx]
    # [System.IO.File]::ReadAllLines 会把 \r\n / \n / \r 三种行尾统一拆掉，
    # 这里 $cur 不会带残留 \r（不像 bash 版 grep 那样得自己剥）——PS 侧这块本来就安全。
    $body = $cur.Substring('resourcePacks:['.Length)
    $body = $body.Substring(0, $body.Length - 1)
    # 先把已有的汉化包条目摘掉，再追加到**末尾**。
    # 不能只判断「已存在就跳过」——旧版本装出来的实例里它可能排在很前面，
    # 那样等于没启用（后面的包会把它整个盖掉），必须重新挪到最后。
    # 摘除时同时兼容双引号/单引号、带/不带 file/ 前缀四种写法——重复安装、
    # 或旧工具用了不同写法留下的残留条目，都得认得出来，否则会越装越多份重复项。
    $packBasename = $PackEntry.Substring($PackEntry.IndexOf('/') + 1)
    $body = $body -replace [regex]::Escape('"' + $PackEntry + '"'), ''
    $body = $body -replace [regex]::Escape("'" + $PackEntry + "'"), ''
    $body = $body -replace [regex]::Escape('"' + $packBasename + '"'), ''
    $body = $body -replace [regex]::Escape("'" + $packBasename + "'"), ''
    $body = ($body -replace ',{2,}', ',').Trim(',')
    $new = if ($body) { 'resourcePacks:[' + $body + ',"' + $PackEntry + '"]' }
           else       { 'resourcePacks:["' + $PackEntry + '"]' }
    if ($new -eq $cur) {
        Write-Host 'options.txt 已正确启用汉化资源包（在列表最后），跳过'
        return
    }
    $lines[$idx] = $new
    [System.IO.File]::WriteAllLines($opt, $lines, $Utf8NoBom)
    Write-Host '✅ 已在 options.txt 启用汉化资源包并置于列表最后（不在最后会被其他包盖掉）'
}

##
# 清理本补丁旧版本（v7.2-release8 之前）遗留的文件。
#
# 那之前本包的任务书 delta 用的是 `<章节名>.snbt`，与整合包自带的同名文件**撞名**，
# 安装时直接覆盖 —— 整合包那一章上百条翻译当场没了，任务书变英文。
# （已经启动过的实例看不出来：整合包那批早合并完并改名成 .snbt_merged 了。）
#
# 现在统一加 zz_hanhua_ 前缀，不会再撞名。这里把旧名字的残留删掉，
# 且只在**内容与本包同名新文件逐字节相同**时才删 —— 这样能确定它是本包的旧产物，
# 绝不会误删整合包自己的文件。
# r14 之前的版本往实例里装过 CC: Tweaked 的中文 help 文档
# （kubejs\data\computercraft\lua\rom\help\，97 个 .txt）。CC 的终端用自带的
# term_font.png——256 个字形、没有汉字，中文进去整屏乱码。新版不再生成，
# 但安装器只覆盖不删除，旧文件会一直留着，于是「装了新版还是乱码」。这里主动清掉。
function Clear-LegacyCCHelp {
    # 只认这一个目录：旧版本就是往 lua\rom\help\ 里放译好的 .txt，别的地方一律不碰。
    # 旧代码递归删整个 computercraft 目录下的 *.txt，不看内容也不进备份——玩家自己
    # 放在那底下的 .txt 会**永久消失**，restore 也拿不回来（Do-Backup 只枚举当前
    # payload，而这些文件早就不在 payload 里）。（issue #9 P1-1）
    $ccd = Join-Path $script:Target 'kubejs\data\computercraft\lua\rom\help'
    if (-not (Test-Path -LiteralPath $ccd)) { return }
    $all = @(Get-ChildItem -LiteralPath $ccd -Recurse -Filter *.txt -File -ErrorAction SilentlyContinue)
    if ($all.Count -eq 0) { return }
    $txt = @()
    foreach ($f in $all) {
        # 判据：文件里有非 ASCII 字节。我们发的是中译本，CC 自带的 help 全是英文；
        # 纯 ASCII 的一律不动。万一还是判错，下面会先备份，restore 拿得回来。
        $bytes = $null
        try { $bytes = [System.IO.File]::ReadAllBytes($f.FullName) } catch { }
        if ($null -eq $bytes) { continue }
        foreach ($b in $bytes) { if ($b -gt 127) { $txt += $f; break } }
    }
    if ($txt.Count -eq 0) { return }
    foreach ($f in $txt) {
        if ($script:BK -and (Test-Path -LiteralPath $script:BK)) {
            $rel = $f.FullName.Substring($script:Target.Length).TrimStart('\', '/')
            $dst = Join-Path $script:BK $rel
            # 不用 New-Item：Windows PowerShell 5.1 的 New-Item 没有 -LiteralPath，
            # 而 -Path 会把 [ ] 当通配符（实例目录叫 [1.21.1]ATM10 很常见）。
            [void][System.IO.Directory]::CreateDirectory([System.IO.Path]::GetDirectoryName($dst))
            Copy-Item -LiteralPath $f.FullName -Destination $dst -ErrorAction SilentlyContinue
        }
        Remove-Item -LiteralPath $f.FullName -Force -ErrorAction SilentlyContinue
    }
    # 自底向上删空目录；非空的一律留着
    foreach ($d in @(Get-ChildItem -LiteralPath $ccd -Recurse -Directory -ErrorAction SilentlyContinue |
                     Sort-Object { $_.FullName.Length } -Descending)) {
        if (-not @(Get-ChildItem -LiteralPath $d.FullName -Force -ErrorAction SilentlyContinue)) {
            Remove-Item -LiteralPath $d.FullName -Force -ErrorAction SilentlyContinue
        }
    }
    if (-not @(Get-ChildItem -LiteralPath $ccd -Force -ErrorAction SilentlyContinue)) {
        Remove-Item -LiteralPath $ccd -Force -ErrorAction SilentlyContinue
    }
    Write-Host "🧹 清理了旧版本装进去的 CC: Tweaked 中文 help 文档（$($txt.Count) 个文件，已备份）。"
    Write-Host '   CC 的终端只有 256 个自带字形、没有汉字，中文在那里必然是乱码，'
    Write-Host '   所以这部分改回英文——这是终端本身的限制，不是漏翻。'
}

# r14 发过「模组配置界面汉化」那两个 VaultPatcher 模块（合计 2232 条），本版起不再发。
# 它们是 dynamic 模块，而 VaultPatcher 的 dynamic 表是**全局的、每次替换调用都要线性扫一遍**
# 的全局开销——留在盘上就等于全场景掉帧照旧，装了新版也修不掉。安装器只覆盖不删除，
# 所以必须在这里主动清掉。
function Clear-LegacyConfigUI {
    $vpm = Join-Path $script:Target 'vaultpatcher\modules'
    if (-not (Test-Path -LiteralPath $vpm)) { return }
    $hit = 0
    foreach ($f in @('config_ui_generated.json', 'catnip_config_ui.json')) {
        $old = Join-Path $vpm $f
        if (Test-Path -LiteralPath $old -PathType Leaf) {
            # 这两个文件不在 payload 里，Do-Backup 不会备份它们——删掉就永久没了。
            # 这里自己塞进本次备份目录（就地解压模式没有备份，那条路本来就无从回退）。
            if ($script:BK -and (Test-Path -LiteralPath $script:BK)) {
                $to = Join-Path $script:BK 'vaultpatcher\modules'
                # 不用 New-Item：Windows PowerShell 5.1 的 New-Item 没有 -LiteralPath
                # （实测 CI 红：NamedParameterNotFound），而 -Path 会把 [ ] 当通配符——
                # 实例目录叫 [1.21.1]ATM10 这种在 PCL/HMCL 下很常见。
                [void][System.IO.Directory]::CreateDirectory($to)
                Copy-Item -LiteralPath $old -Destination (Join-Path $to $f) -ErrorAction SilentlyContinue
            }
            Remove-Item -LiteralPath $old -Force -ErrorAction SilentlyContinue
            $hit++
        }
    }
    if ($hit -gt 0) {
        Write-Host "🧹 清理了 $hit 个 r14 装进去的配置界面汉化模块。"
        Write-Host '   那套替换表是全局开销（全局的，表越大越慢），留着会掉帧；'
        Write-Host '   代价是 Create 及其附属的配置界面回到英文（只有它们用这套界面）。'
    }
}

function Clear-LegacyQuestLang {
    $qd = Join-Path $script:Target 'config\ftbquests\quests\lang\zh_cn\chapters'
    $sd = Join-Path $ScriptDir 'config\ftbquests\quests\lang\zh_cn\chapters'
    if (!(Test-Path -LiteralPath $qd) -or !(Test-Path -LiteralPath $sd)) { return }
    $hit = 0
    foreach ($new in Get-ChildItem -LiteralPath $sd -Filter 'zz_hanhua_*.snbt' -File) {
        $base = $new.Name -replace '^zz_hanhua_', ''
        foreach ($n in @($base, "_$base")) {
            $old = Join-Path $qd $n
            # payload 会写同名文件 → 交给复制那一步，这里不删也不计数。
            # 不加这一句，payload 自己发的空壳 `_X.snbt` 与 `zz_hanhua_X.snbt` 字节相同，
            # 每次安装都会「删掉上次装的、再抄回来」，计数恒等于空壳个数。
            if (Test-Path -LiteralPath (Join-Path $sd $n)) { continue }
            if (!(Test-Path -LiteralPath $old)) { continue }
            $a = [System.IO.File]::ReadAllBytes($old)
            $b = [System.IO.File]::ReadAllBytes($new.FullName)
            if ($a.Length -eq $b.Length -and
                [System.Linq.Enumerable]::SequenceEqual($a, $b)) {
                Remove-Item -LiteralPath $old -Force
                $hit++
            }
        }
    }
    if ($hit -gt 0) {
        Write-Host "🧹 清理了 $hit 个旧版本残留的任务书语言文件。"
    }
}

function Do-Apply {
    if ($script:InPlace) {
        Clear-LegacyQuestLang
        Clear-LegacyCCHelp
        Clear-LegacyConfigUI
        Patch-Options
        Write-Host '✅ 汉化文件已在位，options.txt 已处理完毕。'
        return
    }
    # ⚠️ fail-closed：数不出足够的待装文件就**一个字节都不动**地退出。
    # 2026-08-01 玩家反馈过一次「备份 0 个 + 一路绿勾 + 实际什么都没装」——
    # 那种情况下安装器照样打印「✅ 汉化已应用」，玩家没有任何办法知道装失败了。
    # 正常包有数百个文件；少于 50 只可能是解压不完整、脚本不在汉化文件夹里，
    # 或路径把文件枚举搞没了。宁可当场报错，也不许假装成功。
    $payload = @(Get-PayloadFiles)
    if ($payload.Count -lt 50) {
        Write-Host "❌ 只找到 $($payload.Count) 个待安装文件，正常应有数百个。"
        Write-Host '   常见原因：压缩包没解压完整；或 install.ps1 不在解压出来的汉化文件夹里。'
        Write-Host '   已中止，**没有改动实例里的任何文件**。'
        exit 1
    }
    Do-Backup
    Clear-LegacyQuestLang
    Clear-LegacyCCHelp
    Clear-LegacyConfigUI
    $copied = 0
    foreach ($f in $payload) {
        $dst = Join-Path $script:Target $f
        if ((Join-Path $ScriptDir $f) -eq $dst) { continue }   # 双保险：源即目标就跳过
        New-DirForFile $dst
        Copy-OneFile (Join-Path $ScriptDir $f) $dst -Force
        $copied++
    }
    # 再核一遍是否真的落地：复制静默失败、目标只读、路径被通配符吃掉都在这里露馅。
    $missing = @($payload | Where-Object { -not (Test-Path -LiteralPath (Join-Path $script:Target $_)) })
    if ($missing.Count -gt 0) {
        Write-Host "❌ 有 $($missing.Count) 个文件没能写进实例（共 $($payload.Count) 个），例如 $($missing[0])。"
        Write-Host "   可用 .\install.ps1 restore $script:TS 回退。"
        exit 1
    }
    Patch-Options
    Write-Host "✅ 汉化已应用（$copied 个文件）。备份在 backups/$script:TS/，如需回退运行: .\install.ps1 restore $script:TS"
}

# 实例里是否已经有拼音搜索 mod。mod id 取自我们随包 jar 的文件名首段
# （jecharacters-1.21.1-neoforge-4.5.26.jar → jecharacters），不写死，
# 换 jar 时不用改这里。返回已装到的那个 jar 的相对路径，没有则返回 $null。
#
# 这不只是省一次按键：同一个 mod id 出现两个 jar，NeoForge 会以
# 「Mod ID is duplicated」拒绝启动。装过的人按下 y 就进不去游戏了。
function Get-InstalledPinyin {
    $pinAbs = Join-Path $ScriptDir $PinyinDir
    if (!(Test-Path -LiteralPath $pinAbs)) { return $null }
    $modsDir = Join-Path $script:Target 'mods'
    if (!(Test-Path -LiteralPath $modsDir)) { return $null }
    $installed = Get-ChildItem -LiteralPath $modsDir -Filter '*.jar' -File -ErrorAction SilentlyContinue
    if (!$installed) { return $null }
    foreach ($j in (Get-ChildItem -LiteralPath $pinAbs -Filter '*.jar' -File)) {
        $id = ($j.Name -split '-', 2)[0].ToLowerInvariant()
        if (!$id) { continue }
        foreach ($m in $installed) {
            $mb = $m.Name.ToLowerInvariant()
            if ($mb -eq "$id.jar" -or $mb.StartsWith("$id-")) { return "mods/$($m.Name)" }
        }
    }
    return $null
}

# 可选 mods（JEI 拼音搜索）：装进实例 mods/，并登记进当前备份以便恢复时删除
function Do-Pinyin {
    $pinAbs = Join-Path $ScriptDir $PinyinDir
    if (!(Test-Path -LiteralPath $pinAbs)) {
        Write-Host "（未找到 $PinyinDir 目录，跳过可选mods）"
        return
    }
    $already = Get-InstalledPinyin
    if ($already) {
        Write-Host "（已装有拼音搜索 mod：${already}，跳过——同一个 mod 装两个 jar 会让游戏起不来）"
        return
    }
    $jars = Get-ChildItem -LiteralPath $pinAbs -Filter '*.jar' -File
    if (!$jars) {
        Write-Host "（$PinyinDir 内没有 jar，跳过）"
        return
    }
    # 就地解压模式没有本次备份（BK 为空），只装不登记
    $manifest = if ($script:BK) { Join-Path $script:BK '新增文件清单.txt' } else { $null }
    foreach ($j in $jars) {
        $dst = Join-Path $script:Target "mods/$($j.Name)"
        if ($script:BK) {
            if (Test-Path -LiteralPath $dst) {
                [System.IO.Directory]::CreateDirectory((Join-Path $script:BK 'mods')) | Out-Null
                Copy-Item -LiteralPath $dst -Destination (Join-Path $script:BK "mods/$($j.Name)")
            } else {
                [System.IO.File]::AppendAllText($manifest, "mods/$($j.Name)`n", $Utf8NoBom)
            }
        }
        if ($j.FullName -eq $dst) { continue }
        Copy-Item -LiteralPath $j.FullName -Destination $dst -Force
        Write-Host "  已安装: mods/$($j.Name)"
    }
    Write-Host '✅ 可选 mod（JEI 拼音搜索）已安装'
}

function Do-Restore([string]$name) {
    $broot = Join-Path $ScriptDir 'backups'
    if (!(Test-Path -LiteralPath $broot) -or !(Get-ChildItem -LiteralPath $broot -Directory)) {
        Write-Host '❌ 没有任何备份'
        exit 1
    }
    $all = Get-ChildItem -LiteralPath $broot -Directory | Sort-Object Name
    if (-not $name) {
        Write-Host '可用备份：'
        $all | ForEach-Object { Write-Host "  $($_.Name)" }
        $latest = $all[-1].Name
        $name = Read-Host "要恢复的备份名 [回车 = $latest]"
        if (-not $name) { $name = $latest }
    }
    $bk = Join-Path $broot $name
    if (!(Test-Path -LiteralPath $bk)) {
        Write-Host "❌ 备份不存在: $name"
        exit 1
    }
    $manifest = Join-Path $bk '新增文件清单.txt'
    if (Test-Path -LiteralPath $manifest) {
        foreach ($f in [System.IO.File]::ReadAllLines($manifest)) {
            if ($f) { Remove-Item -LiteralPath (Join-Path $script:Target $f) -Force -ErrorAction SilentlyContinue }
        }
    }
    foreach ($rel in (Get-FilesUnder $bk)) {
        if ([System.IO.Path]::GetFileName($rel) -eq '新增文件清单.txt') { continue }
        $dst = Join-Path $script:Target $rel
        New-DirForFile $dst
        Copy-OneFile (Join-Path $bk $rel) $dst -Force
    }
    Write-Host "✅ 已恢复备份 $name（含 options.txt，安装时新增的文件已删除）"
}

Check-Target
Check-Update
switch ($Action) {
    'apply'             { Do-Apply }
    'apply-with-pinyin' { Do-Apply; Do-Pinyin }
    'backup'            { Do-Backup }
    'restore'           { Do-Restore $BackupName }
    default {
        Write-Host '══════════════════════════════════════════'
        Write-Host ' ATM10 @@MCVER@@ 汉化补丁 · 绿油油版 — 安装器'
        Write-Host " 目标实例: $script:Target"
        Write-Host '══════════════════════════════════════════'
        Write-Host ' [1] 应用汉化（自动先备份被覆盖文件）'
        if ($script:LatestRelease -and
            (Normalize-Ver $script:LatestRelease.tag_name) -ne (Normalize-Ver $script:PatchVer)) {
            Write-Host " [u] 一键下载并更新到 $($script:LatestRelease.tag_name)"
        }
        Write-Host ' [2] 仅备份'
        Write-Host ' [3] 恢复备份'
        Write-Host ' [q] 退出'
        $c = Read-Host '请选择'
        switch ($c) {
            '1' {
                Do-Apply
                # 已经装过就别问了：每次更新汉化都要按一次 N 属实多余。
                $already = Get-InstalledPinyin
                if ($already) {
                    Write-Host "（已装有拼音搜索 mod：${already}，无需重复安装）"
                } else {
                    $ans = Read-Host '是否同时安装可选的 JEI 拼音搜索 mod？[y/N]'
                    if ($ans -eq 'y' -or $ans -eq 'Y') { Do-Pinyin }
                    else { Write-Host '（跳过可选mods，之后可运行: .\install.ps1 apply-with-pinyin）' }
                }
            }
            'u' { Invoke-OneClickUpdate }
            '2' { Do-Backup }
            '3' { Do-Restore '' }
            default { Write-Host '已退出' }
        }
    }
}
