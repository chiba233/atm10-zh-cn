// atm10-zh-cn — All the Mods 10 简体中文汉化补丁「绿油油版」
// Copyright (C) 2026 星野夢華 (Hoshino Yumeka)
// SPDX-License-Identifier: GPL-3.0-or-later
//
// 任务书横幅：KubeJS 2101.7.2 build 377 起 kubejs/assets 排在玩家资源包之上
// （KubeJS 提交 7973e69e），汉化包里的中文横幅会被 ATM 自带的英文原图盖住。
// 进入世界时逐张检查：最上层不是汉化包的，就把汉化包里那张读出来注册到纹理管理器，
// 盖回原路径。汉化包本来就在最上层时什么都不做。不改动 ATM 的任何文件。
// 汉化包没启用、或游戏语言不是简体中文时不工作，并释放之前注册过的图，让横幅回到原图。

const $NativeImage = Java.loadClass('com.mojang.blaze3d.platform.NativeImage')
const $DynamicTexture = Java.loadClass('net.minecraft.client.renderer.texture.DynamicTexture')

// 汉化包独有的命名空间（hanhua_pack_check.js 的隐藏键 atm10zhcn.pack.version 就在这里）。
// 按它找出汉化包真实的包 ID，不依赖文件名，改名也认得出。
const HANHUA_PROBE = 'atm10zhcn:lang/zh_cn.json'

// 本脚本注册过的横幅，条件不满足时要释放掉
const hanhuaRegistered = {}

// 语言是简体中文且汉化包已启用时，返回汉化包的包 ID，否则返回 null。
// 只有已启用的资源包才会出现在资源管理器里，找不到隐藏键就是没启用。
function hanhuaPackId() {
  if (String(Client.getLanguageManager().getSelected()) != 'zh_cn') return null
  const probe = Client.getResourceManager().getResourceStack(HANHUA_PROBE)
  if (probe.isEmpty()) return null
  return String(probe.get(probe.size() - 1).sourcePackId())
}

ClientEvents.loggedIn(event => {
  const textures = Client.getTextureManager()
  const packId = hanhuaPackId()
  if (packId == null) {
    Object.keys(hanhuaRegistered).forEach(key => {
      textures.release(hanhuaRegistered[key])
      delete hanhuaRegistered[key]
    })
    return
  }
  const stacks = Client.getResourceManager().listResourceStacks('textures/questpics',
    id => id.getNamespace() == 'atm' && id.getPath().endsWith('.png'))
  stacks.forEach((id, stack) => {
    if (stack.isEmpty()) return
    if (String(stack.get(stack.size() - 1).sourcePackId()) == packId) return
    let ours = null
    stack.forEach(res => {
      if (String(res.sourcePackId()) == packId) ours = res
    })
    if (ours == null) return
    try {
      // read 与 register 都有重载，Rhino 判不出该用哪个（java.io 又被类过滤挡住），
      // 不指明签名会报「ambiguous」。这里不用 const 中转：KubeJS 的 Rhino 在回调里第二次执行到
      // try 块中的 const 时会报「redeclaration of var」。
      textures['register(net.minecraft.resources.ResourceLocation,net.minecraft.client.renderer.texture.AbstractTexture)'](
        id, new $DynamicTexture($NativeImage['read(java.io.InputStream)'](ours.open())))
      hanhuaRegistered[String(id)] = id
    } catch (e) {
      console.error('汉化包横幅 ' + id + ' 加载失败：' + e)
    }
  })
})
