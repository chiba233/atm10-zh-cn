// atm10-zh-cn — All the Mods 10 简体中文汉化补丁「绿油油版」
// Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
// SPDX-License-Identifier: GPL-3.0-or-later
//
// 任务书横幅：KubeJS 2101.7.2 build 377 起 kubejs/assets 排在玩家资源包之上
// （KubeJS 提交 7973e69e），汉化包里的中文横幅会被 ATM 自带的英文原图盖住。
// 进入世界时逐张检查：最上层不是汉化包的，就把汉化包里那张读出来注册到纹理管理器，
// 盖回原路径。汉化包本来就在最上层时什么都不做。不改动 ATM 的任何文件。

const $NativeImage = Java.loadClass('com.mojang.blaze3d.platform.NativeImage')
const $DynamicTexture = Java.loadClass('net.minecraft.client.renderer.texture.DynamicTexture')

const HANHUA_PACK_MARK = 'ATM10汉化包'

ClientEvents.loggedIn(event => {
  const textures = Client.getTextureManager()
  const stacks = Client.getResourceManager().listResourceStacks('textures/questpics',
    id => id.getNamespace() == 'atm' && id.getPath().endsWith('.png'))
  stacks.forEach((id, stack) => {
    if (stack.isEmpty()) return
    if (String(stack.get(stack.size() - 1).sourcePackId()).indexOf(HANHUA_PACK_MARK) >= 0) return
    let ours = null
    stack.forEach(res => {
      if (String(res.sourcePackId()).indexOf(HANHUA_PACK_MARK) >= 0) ours = res
    })
    if (ours == null) return
    try {
      textures.register(id, new $DynamicTexture($NativeImage.read(ours.open())))
    } catch (e) {
      console.error('汉化包横幅 ' + id + ' 加载失败：' + e)
    }
  })
})
