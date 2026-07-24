@echo off
REM atm10-zh-cn — All the Mods 10 简体中文汉化补丁「绿油油版」
REM Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
REM SPDX-License-Identifier: GPL-3.0-or-later
chcp 65001 >nul
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1"
pause
