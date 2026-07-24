# atm10-zh-cn — All the Mods 10 简体中文汉化补丁「绿油油版」
# Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
# SPDX-License-Identifier: GPL-3.0-or-later
# ATM10 7.2 汉化补丁「绿油油版」安装器 (Windows)
# 用法：把整个汉化文件夹放进 ATM10 实例根目录后，双击「双击安装-Windows.bat」，
# 或在 PowerShell 中运行：
#   .\install.ps1                    # 交互菜单
#   .\install.ps1 apply              # 应用汉化（自动先备份，不含可选mods）
#   .\install.ps1 apply-with-pinyin  # 应用汉化 + 安装可选 JEI 拼音搜索 mod
#   .\install.ps1 backup             # 仅备份
#   .\install.ps1 restore [备份名]   # 恢复备份
param(
    [string]$Action = '',
    [string]$BackupName = ''
)
$ErrorActionPreference = 'Stop'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir
$script:Target = Split-Path -Parent $ScriptDir
$PackDirs = @('config', 'kubejs', 'mods', 'resourcepacks', 'vaultpatcher')
$PackEntry = 'file/ATM10汉化包-7.2.zip'
$PinyinDir = '可选mods-拼音搜索'
$script:TS = ''
$script:BK = ''
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)

function Check-Target {
    if ((Test-Path (Join-Path $script:Target 'mods')) -and (Test-Path (Join-Path $script:Target 'options.txt'))) {
        return
    }
    Write-Host '⚠️ 上一级目录不是游戏实例根目录（含 mods\ 与 options.txt 的那一层）。'
    while ($true) {
        $inp = Read-Host '请输入 ATM10 实例根目录完整路径（q 退出）'
        $inp = $inp.Trim()
        if ($inp -eq 'q' -or [string]::IsNullOrWhiteSpace($inp)) { exit 1 }
        # 去掉整体包裹的成对引号（Windows 拖拽/粘贴带空格路径常加双引号）
        if (($inp.StartsWith('"') -and $inp.EndsWith('"')) -or ($inp.StartsWith("'") -and $inp.EndsWith("'"))) {
            $inp = $inp.Substring(1, $inp.Length - 2)
        }
        $inp = $inp.TrimEnd('\', '/')
        if ((Test-Path (Join-Path $inp 'mods')) -and (Test-Path (Join-Path $inp 'options.txt'))) {
            $script:Target = $inp
            Write-Host "✅ 目标实例: $script:Target"
            return
        }
        Write-Host '❌ 该路径下未找到 mods\ 与 options.txt，请重试。'
    }
}

function Get-PayloadFiles {
    foreach ($d in $PackDirs) {
        if (Test-Path $d) {
            Get-ChildItem $d -Recurse -File | Where-Object { $_.Name -ne '.DS_Store' } | ForEach-Object {
                $_.FullName.Substring($ScriptDir.Length + 1)
            }
        }
    }
}

function Do-Backup {
    $script:TS = Get-Date -Format 'yyyyMMdd-HHmmss'
    $script:BK = Join-Path $ScriptDir "backups/$script:TS"
    New-Item -ItemType Directory -Force -Path $script:BK | Out-Null
    $newFiles = @()
    $n = 0
    foreach ($f in Get-PayloadFiles) {
        $dst = Join-Path $script:Target $f
        if (Test-Path $dst) {
            $to = Join-Path $script:BK $f
            New-Item -ItemType Directory -Force -Path (Split-Path $to) | Out-Null
            Copy-Item $dst $to
            $n++
        } else {
            $newFiles += $f
        }
    }
    if ($newFiles.Count -gt 0) {
        [System.IO.File]::WriteAllLines((Join-Path $script:BK '新增文件清单.txt'), $newFiles, $Utf8NoBom)
    }
    Copy-Item (Join-Path $script:Target 'options.txt') (Join-Path $script:BK 'options.txt')
    Write-Host "✅ 已备份 $n 个将被覆盖的文件到 backups/$script:TS/"
}

function Patch-Options {
    $opt = Join-Path $script:Target 'options.txt'
    $content = [System.IO.File]::ReadAllText($opt)
    if ($content -match [regex]::Escape($PackEntry)) {
        Write-Host 'options.txt 已启用汉化资源包，跳过'
        return
    }
    if ($content -match '(?m)^resourcePacks:\[\]\s*$') {
        $content = $content -replace '(?m)^resourcePacks:\[\]', ('resourcePacks:["' + $PackEntry + '"]')
    } elseif ($content -match '(?m)^resourcePacks:\[.+\]\s*$') {
        $content = $content -replace '(?m)^resourcePacks:\[(.+)\]', ('resourcePacks:[$1,"' + $PackEntry + '"]')
    } else {
        Write-Host '⚠️ options.txt 中没有 resourcePacks 行，请进游戏手动启用资源包'
        return
    }
    [System.IO.File]::WriteAllText($opt, $content, $Utf8NoBom)
    Write-Host '✅ 已在 options.txt 启用汉化资源包（不启用会全英文）'
}

function Do-Apply {
    Do-Backup
    foreach ($f in Get-PayloadFiles) {
        $dst = Join-Path $script:Target $f
        New-Item -ItemType Directory -Force -Path (Split-Path $dst) | Out-Null
        Copy-Item $f $dst -Force
    }
    Patch-Options
    Write-Host "✅ 汉化已应用。备份在 backups/$script:TS/，如需回退运行: .\install.ps1 restore $script:TS"
}

# 可选 mods（JEI 拼音搜索）：装进实例 mods/，并登记进当前备份以便恢复时删除
function Do-Pinyin {
    if (!(Test-Path $PinyinDir)) {
        Write-Host "（未找到 $PinyinDir 目录，跳过可选mods）"
        return
    }
    $jars = Get-ChildItem $PinyinDir -Filter '*.jar' -File
    if (!$jars) {
        Write-Host "（$PinyinDir 内没有 jar，跳过）"
        return
    }
    $manifest = Join-Path $script:BK '新增文件清单.txt'
    foreach ($j in $jars) {
        $dst = Join-Path $script:Target "mods/$($j.Name)"
        if (Test-Path $dst) {
            New-Item -ItemType Directory -Force -Path (Join-Path $script:BK 'mods') | Out-Null
            Copy-Item $dst (Join-Path $script:BK "mods/$($j.Name)")
        } else {
            [System.IO.File]::AppendAllText($manifest, "mods/$($j.Name)`n", $Utf8NoBom)
        }
        Copy-Item $j.FullName $dst -Force
        Write-Host "  已安装: mods/$($j.Name)"
    }
    Write-Host '✅ 可选 mod（JEI 拼音搜索）已安装'
}

function Do-Restore([string]$name) {
    $broot = Join-Path $ScriptDir 'backups'
    if (!(Test-Path $broot) -or !(Get-ChildItem $broot -Directory)) {
        Write-Host '❌ 没有任何备份'
        exit 1
    }
    $all = Get-ChildItem $broot -Directory | Sort-Object Name
    if (-not $name) {
        Write-Host '可用备份：'
        $all | ForEach-Object { Write-Host "  $($_.Name)" }
        $latest = $all[-1].Name
        $name = Read-Host "要恢复的备份名 [回车 = $latest]"
        if (-not $name) { $name = $latest }
    }
    $bk = Join-Path $broot $name
    if (!(Test-Path $bk)) {
        Write-Host "❌ 备份不存在: $name"
        exit 1
    }
    $manifest = Join-Path $bk '新增文件清单.txt'
    if (Test-Path $manifest) {
        foreach ($f in [System.IO.File]::ReadAllLines($manifest)) {
            if ($f) { Remove-Item (Join-Path $script:Target $f) -Force -ErrorAction SilentlyContinue }
        }
    }
    Get-ChildItem $bk -Recurse -File | Where-Object { $_.Name -ne '新增文件清单.txt' } | ForEach-Object {
        $rel = $_.FullName.Substring($bk.Length + 1)
        $dst = Join-Path $script:Target $rel
        New-Item -ItemType Directory -Force -Path (Split-Path $dst) | Out-Null
        Copy-Item $_.FullName $dst -Force
    }
    Write-Host "✅ 已恢复备份 $name（含 options.txt，安装时新增的文件已删除）"
}

Check-Target
switch ($Action) {
    'apply'             { Do-Apply }
    'apply-with-pinyin' { Do-Apply; Do-Pinyin }
    'backup'            { Do-Backup }
    'restore'           { Do-Restore $BackupName }
    default {
        Write-Host '══════════════════════════════════════════'
        Write-Host ' ATM10 7.2 汉化补丁 · 绿油油版 — 安装器'
        Write-Host " 目标实例: $script:Target"
        Write-Host '══════════════════════════════════════════'
        Write-Host ' [1] 应用汉化（自动先备份被覆盖文件）'
        Write-Host ' [2] 仅备份'
        Write-Host ' [3] 恢复备份'
        Write-Host ' [q] 退出'
        $c = Read-Host '请选择'
        switch ($c) {
            '1' {
                Do-Apply
                $ans = Read-Host '是否同时安装可选的 JEI 拼音搜索 mod？[y/N]'
                if ($ans -eq 'y' -or $ans -eq 'Y') { Do-Pinyin }
                else { Write-Host '（跳过可选mods，之后可运行: .\install.ps1 apply-with-pinyin）' }
            }
            '2' { Do-Backup }
            '3' { Do-Restore '' }
            default { Write-Host '已退出' }
        }
    }
}
