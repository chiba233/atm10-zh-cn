---
name: upload-github-attachment
description: 把本地图片或文件上传到 GitHub 的 user-attachments 存储，得到可以直接写进 issue、PR、评论的链接。用于要在 GitHub 文本里贴游戏截图、日志或其他证据，又不能把文件提交进仓库的时候。
---

# 上传 GitHub 附件

用随附的脚本上传。认证、仓库解析、MIME 识别与链接提取都由脚本处理。

## 前提

- 需要 `gh` 与 `curl`。
- 优先用已有的 `gh auth login` 会话。没有会话时，需要环境变量 `GH_TOKEN` 或 `GITHUB_TOKEN`。
- 如果 `gh auth token` 取不到令牌，停下来，请维护者配置认证。不要打印、保存或拼接令牌。

## 上传

在仓库目录里执行：

```bash
.agents/skills/upload-github-attachment/scripts/upload-github-attachment.sh /绝对路径/截图.png
```

如果当前目录解析不出仓库，用 `--repo` 指定：

```bash
.agents/skills/upload-github-attachment/scripts/upload-github-attachment.sh \
  --repo chiba233/atm10-zh-cn \
  /绝对路径/截图.png
```

脚本只输出最终的 `https://github.com/user-attachments/assets/...` 链接。图片写成 `![](链接)`，其他文件写成 `[说明](链接)`。

## 核对

1. 上传命令成功，并返回了 `https://github.com/user-attachments/assets/...` 链接。
2. 这个链接只用于它对应的那个本地文件。不要用 GET 或 HEAD 请求去验证它。
3. 匿名访问返回 404 不代表上传失败，不要因此中止。
4. 创建或编辑 GitHub 文本之后，重新打开它，核对附件用的是返回的链接。

GitHub 没有公开这个上传接口的文档。如果上传被拒绝，把它当成接口变化，停下来报告。不要改成把图片提交进仓库。

## 来源

脚本原样取自 [moeru-ai/airi](https://github.com/moeru-ai/airi) 的同名 skill，本说明按它的英文原文改写。两者按 MIT 许可再分发，许可全文见 `.agents/LICENSE-airi.txt`。
