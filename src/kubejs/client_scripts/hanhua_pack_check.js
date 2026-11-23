// ATM10 汉化补丁「绿油油版」客户端资源包自检。只读语言表与资源包列表，不下载、不写文件、不联网。
//
// 玩家没启用资源包，或把它放在别的包下面时，看到的是满屏英文。这里在进入世界后提示。两层判断：
//
//   一、是否生效。资源包里有一个本包独有的键 atm10zhcn.pack.version
//       （assets/atm10zhcn/lang/zh_cn.json，值由构建脚本按发布版本填入）。语言表是所有启用的包
//       合并后的结果，查得到就说明包生效了。读 options.txt 只能查配置，文件损坏时会误判为正常。
//       查到的值与本脚本的版本不一致，说明启用的是旧版本的包（安装器只覆盖不删除，改过名的
//       旧包会留着）。
//
//   二、顺序。探针键排第几都查得到，第一层测不出顺序。确认包已加载后再查 PackRepository：
//       排在本包之后（优先级更高）的包里，有没有也提供 zh_cn 语言文件的。只有这种包会覆盖本包，
//       玩家放在最上面的材质包不算。正常安装时本包就是最后一个，不用打开任何包。
//
// 判断不了就不提示：配置正常的玩家每次进游戏都看到红字，比不做这个功能还糟。
//
// 与 hanhua_update_check.js 相同的两条约束：
//    - 块里只赋值，不声明。KubeJS 的 Rhino 把 try/if/for 块内的 const 提升成函数作用域的 var，
//      执行时抛 TypeError: redeclaration of var，又被 catch 吞掉。声明都写在函数体顶层，用 let。
//      由 check.py 的 js-no-const-inside-block 检查。
//    - Java.loadClass 只用字符串字面量，且类要通过 kubejs.classfilter.txt。这里用到的四个类都在
//      `+ net.minecraft` 放行范围内（只有 net.minecraft.Util 被禁）。由 check_kubejs_classfilter.py
//      检查。
//
// 整份放在 IIFE 里：client_scripts 共用一个全局作用域，顶层 const 重名会让整批脚本加载失败。
(function () {
  const PROBE_KEY = 'atm10zhcn.pack.version'
  const PROBE_NAMESPACE = 'atm10zhcn'
  const PACK_VERSION = '@@PATCHVER@@'
  const LANG_PATH = 'lang/zh_cn.json'
  // 进世界 3 秒后再提示：loggedIn 在连接阶段触发，立刻提示会被进服消息冲掉，
  // 3 秒后正好在模组的进服提示之后。
  const DELAY_TICKS = 20 * 3

  let pending = 0
  let verdict = null
  let offenders = ''

  function say(line) {
    console.info('[ATM10 汉化] ' + line)
  }

  // ---------- 第一层：包生效了没有 ----------
  // 'ok' / 'missing' / 'mismatch:<包里写的版本>'。判不准返回 null
  function inspectLang() {
    let I18nClass = null
    let value = ''
    try {
      I18nClass = Java.loadClass('net.minecraft.client.resources.language.I18n')
    } catch (err) {
      say('自检取不到 I18n，跳过：' + err)
      return null
    }
    try {
      if (!I18nClass.exists(PROBE_KEY)) return 'missing'
      value = String(I18nClass.get(PROBE_KEY))
    } catch (err) {
      say('自检查表失败，跳过：' + err)
      return null
    }
    if (value === PACK_VERSION) return 'ok'
    return 'mismatch:' + value
  }

  // ---------- 第二层：有没有人压在我们上面 ----------
  // 'top' / 'blocked' / 'blocked:<玩家自己装的包名>'。判不准返回 null
  function inspectOrder() {
    let McClass = null
    let PackTypeClass = null
    let LocClass = null
    let repo = null
    let list = null
    let i = 0
    let j = 0
    let ourIndex = -1
    let pack = null
    let res = null
    let namespaces = null
    let ns = null
    let id = ''
    let names = []
    let blockers = 0
    let hit = false

    try {
      McClass = Java.loadClass('net.minecraft.client.Minecraft')
      PackTypeClass = Java.loadClass('net.minecraft.server.packs.PackType')
      LocClass = Java.loadClass('net.minecraft.resources.ResourceLocation')
      repo = McClass.getInstance().getResourcePackRepository()
      // 越靠后优先级越高。这个列表与资源包界面不同：NeoForge 把每个模组自带的资源拆成独立的包，
      // ATM10 7.3 有 534 项，界面里只有十几项。
      list = repo.getSelectedPacks().toArray()
    } catch (err) {
      say('顺序自检取不到包列表，跳过：' + err)
      return null
    }

    // 按命名空间定位本包，不按文件名，玩家改了 zip 名也找得到
    for (i = 0; i < list.length; i++) {
      hit = false
      try {
        res = list[i].open()
        // close() 放在 finally：open() 成功后任何一步抛异常都要关闭句柄，
        // 否则五百多个包会留下一串未关闭的 zip
        try {
          namespaces = res.getNamespaces(PackTypeClass.CLIENT_RESOURCES)
          hit = namespaces.contains(PROBE_NAMESPACE)
        } finally {
          res.close()
        }
      } catch (err) {
        hit = false
      }
      if (hit) {
        ourIndex = i
        break
      }
    }
    if (ourIndex < 0) {
      say('顺序自检：没在选中列表里认出自己，跳过')
      return null
    }
    say('顺序自检：我们排在 ' + (ourIndex + 1) + '/' + list.length)

    // 再看排在本包之后的包里谁也提供 zh_cn。正常安装时这个循环一次都不进。
    for (i = ourIndex + 1; i < list.length; i++) {
      pack = list[i]
      hit = false
      try {
        res = pack.open()
        try {
          namespaces = res.getNamespaces(PackTypeClass.CLIENT_RESOURCES).toArray()
          for (j = 0; j < namespaces.length && !hit; j++) {
            ns = String(namespaces[j])
            if (res.getResource(PackTypeClass.CLIENT_RESOURCES,
                                LocClass.fromNamespaceAndPath(ns, LANG_PATH)) !== null) {
              hit = true
            }
          }
        } finally {
          res.close()
        }
      } catch (err) {
        say('顺序自检：读不动 ' + pack.getId() + '，跳过它（' + err + '）')
        hit = false
      }
      if (hit) {
        blockers++
        // 只列出玩家自己装的包（file/ 开头）：原版与模组自带资源有五百多项，界面里只有十几项，
        // 列出来玩家看不懂，而要做的都一样，把汉化包拖到最顶部。用 id 不用 getTitle()：
        // 「模组自带资源」的标题是全部模组 jar 的文件名清单，有几百行。
        id = String(pack.getId())
        if (id.indexOf('file/') === 0 && names.length < 3) {
          names.push(id.substring('file/'.length))
        }
      }
    }
    if (blockers === 0) return 'top'
    if (names.length === 0) return 'blocked'
    return 'blocked:' + names.join('、')
  }

  function tell(result, blocked) {
    let player = Client.player
    let packed = ''
    if (!player) return

    if (result === 'missing') {
      player.tell(Text.red('[ATM10 汉化] ')
        .append(Text.yellow('汉化资源包没有生效，游戏里绝大部分文本仍然是英文。')))
      player.tell(Text.gray('  打开 ')
        .append(Text.white('选项 → 资源包'))
        .append(Text.gray('，把 '))
        .append(Text.white('ATM10汉化包'))
        .append(Text.gray(' 拖到右侧「已选」一列的'))
        .append(Text.white('最顶部'))
        .append(Text.gray('。')))
      return
    }

    if (result === 'order') {
      player.tell(Text.gold('[ATM10 汉化] ')
        .append(Text.yellow('汉化资源包被压在下面了，部分名字会显示成别的译法。')))
      if (blocked !== '') {
        player.tell(Text.gray('  你自己装的 ')
          .append(Text.white(blocked))
          .append(Text.gray(' 排在它上面。')))
      }
      player.tell(Text.gray('  打开 ')
        .append(Text.white('选项 → 资源包'))
        .append(Text.gray('，把 '))
        .append(Text.white('ATM10汉化包'))
        .append(Text.gray(' 拖到「已选」一列的'))
        .append(Text.white('最顶部'))
        .append(Text.gray('。')))
      return
    }

    packed = result.substring('mismatch:'.length)
    player.tell(Text.red('[ATM10 汉化] ')
      .append(Text.yellow('资源包版本与汉化本体对不上：包是 ' + packed
        + '，本体是 ' + PACK_VERSION + '。')))
    player.tell(Text.gray('  多半是旧版本的包还留在 resourcepacks 里且被启用着，'
      + '重新跑一遍安装器即可。'))
  }

  ClientEvents.loggedIn(event => {
    let lang = null
    let order = null
    pending = 0
    verdict = null
    offenders = ''

    lang = inspectLang()
    say('资源包自检：' + lang)
    if (lang === null) return
    if (lang !== 'ok') {
      verdict = lang
      pending = DELAY_TICKS
      return
    }

    // 包确实生效了，这时候问顺序才有意义
    order = inspectOrder()
    say('顺序自检结论：' + (order === null ? '判不准' : order))
    if (order === null || order === 'top') return
    verdict = 'order'
    offenders = ''
    if (order.indexOf('blocked:') === 0) offenders = order.substring('blocked:'.length)
    pending = DELAY_TICKS
  })

  ClientEvents.tick(event => {
    if (pending <= 0) return
    pending--
    if (pending === 0) tell(verdict, offenders)
  })
})()
