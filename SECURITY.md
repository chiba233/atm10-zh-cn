# 安全政策 / Security Policy

## 报告安全问题 / Reporting

如果你在本汉化补丁中发现安全问题——例如：

- 安装脚本（`install.sh` / `install.ps1`）存在可被利用的行为
  （任意路径写入、命令注入等）；
- 分发包内出现了不该有的可执行内容；
- KubeJS 脚本 / VaultPatcher 模块可被恶意输入利用；

请**不要**公开发 Issue，直接发邮件到 **qwq@qwwq.org**，
标题注明 `[SECURITY] atm10-zh-cn`。会在 72 小时内回复。

If you find a security issue in this localization patch (installer script
abuse, unexpected executable content in release packages, exploitable
KubeJS/VaultPatcher behavior), please do **not** open a public issue.
Email **qwq@qwwq.org** with subject `[SECURITY] atm10-zh-cn`.
You will get a response within 72 hours.

## 范围说明 / Scope

- 本项目分发的 jar（`vaultpatcher.jar`、可选拼音搜索 mod）均为上游原版
  再分发，不做任何修改；其自身漏洞请报给对应上游。
- 汉化文本内容的错误（错译 / 漏翻）不属于安全问题，请走普通 Issue。
