// ATM10 汉化补丁「绿油油版」客户端更新提示。每次客户端会话首次进入世界或服务器时，读取一次
// GitHub 最新正式 Release。不下载、不写文件，失败只写一行日志。
//
// 不能用 java.net.http / java.lang.System：kubejs.classfilter.txt 里有 `- java.net` 与 `- java.lang`
//    （白名单里没有 System），Java.loadClass 会抛异常，被 catch 吞掉后看起来和「已是最新版」一样。
//    所以用整合包类路径上的 Apache HttpClient 4.5.13，HttpGet 接收字符串 URL，脚本里不出现受限类。
//    由 check_kubejs_classfilter.py 在构建时检查。
//
// 块里只赋值，不声明。KubeJS 的 Rhino 里，`try {}` / `if {}` 等嵌套块内部的 `const` 会在运行时抛
//    `TypeError: redeclaration of var <名字>`，加载阶段不报错，写在事件回调里就是没有效果。上游的
//    `const` 都在函数或回调体顶层。所以变量都在函数体顶层用 `let` 声明，`try` 内部只赋值。
//    由 check.py 的 js-no-const-inside-block 检查。
//
// JS 只在主线程运行。HTTP 交给 ForkJoinPool.commonPool()（守护线程，不影响游戏退出）在 Java 侧
//    完成，脚本在客户端 tick 里轮询 isDone()，不依赖 Rhino 能否在非主线程执行回调。
//
// 整份放在 IIFE 里：client_scripts 共用一个全局作用域，顶层 const 重名会让整批脚本加载失败。
(function () {
  const HANHUA_VERSION = '@@PATCHVER@@'
  const RELEASES_URL = 'https://github.com/chiba233/atm10-zh-cn/releases/latest'
  const API_URL = 'https://api.github.com/repos/chiba233/atm10-zh-cn/releases/latest'
  const TIMEOUT_MS = 6000
  const GIVE_UP_TICKS = 20 * 30          // 30 秒还没回来就收摊，别一直占着连接

  let task = null
  let http = null
  let ticks = 0
  let settled = false

  function releaseVersion(tag) {
    // 发布工作流允许 12、v12、r12、vr12 及 12.1 这种多段版本号，也允许 -release11、-beta2、-rc3
    // 这类后缀。release 的序号也是版本的一部分。
    let match = String(tag).match(/^v?r?(\d+(?:\.\d+)*)(?:-(release|beta|rc)(\d+))?$/i)
    if (!match) return null
    return {
      parts: match[1].split('.').map(part => Number(part)),
      // 同一数字版本下，beta < rc < 正式版。没有后缀也按正式版处理。
      stage: match[2] ? { beta: 1, rc: 2, release: 3 }[match[2].toLowerCase()] : 3,
      serial: match[3] ? Number(match[3]) : 0
    }
  }

  function isNewerVersion(latest, current) {
    let length = Math.max(latest.parts.length, current.parts.length)
    let diff = 0
    for (let i = 0; i < length; i++) {
      diff = (latest.parts[i] || 0) - (current.parts[i] || 0)
      if (diff !== 0) return diff > 0
    }
    if (latest.stage !== current.stage) return latest.stage > current.stage
    return latest.serial > current.serial
  }

  // 读环境变量也不能用 java.lang.System（被过滤表拒绝）。commons-lang3 在整合包类路径上且未被禁止。
  // 读不到就当没设。
  function skipByEnv() {
    let SystemUtilsClass = null
    let value = ''
    try {
      SystemUtilsClass = Java.loadClass('org.apache.commons.lang3.SystemUtils')
      value = String(SystemUtilsClass.getEnvironmentVariable('ATM_SKIP_UPDATE_CHECK', ''))
    } catch (err) {
      return false
    }
    return value === '1'
  }

  function done(message) {
    settled = true
    task = null
    if (http !== null) {
      try { http.close() } catch (err) { /* 关不掉就算了，进程退出时一起收 */ }
      http = null
    }
    if (message) console.warn('[ATM10 汉化] ' + message)
  }

  function startRequest() {
    let HttpClientsClass = null
    let HttpGetClass = null
    let BasicResponseHandlerClass = null
    let RequestConfigClass = null
    let FutureExecServiceClass = null
    let ForkJoinPoolClass = null
    let config = null
    let request = null
    let service = null
    try {
      HttpClientsClass = Java.loadClass('org.apache.http.impl.client.HttpClients')
      HttpGetClass = Java.loadClass('org.apache.http.client.methods.HttpGet')
      BasicResponseHandlerClass = Java.loadClass('org.apache.http.impl.client.BasicResponseHandler')
      RequestConfigClass = Java.loadClass('org.apache.http.client.config.RequestConfig')
      FutureExecServiceClass = Java.loadClass('org.apache.http.impl.client.FutureRequestExecutionService')
      ForkJoinPoolClass = Java.loadClass('java.util.concurrent.ForkJoinPool')

      config = RequestConfigClass.custom()
        .setConnectTimeout(TIMEOUT_MS)
        .setConnectionRequestTimeout(TIMEOUT_MS)
        .setSocketTimeout(TIMEOUT_MS)
        .build()
      http = HttpClientsClass.custom().setDefaultRequestConfig(config).build()

      request = new HttpGetClass(API_URL)
      request.setHeader('Accept', 'application/vnd.github+json')
      request.setHeader('User-Agent', 'atm10-zh-cn-update-checker')

      service = new FutureExecServiceClass(http, ForkJoinPoolClass.commonPool())
      task = service.execute(request, null, new BasicResponseHandlerClass())
    } catch (err) {
      done('更新检查没能发出请求：' + err)
    }
  }

  function tell(latest) {
    let player = Client.player
    if (!player) return
    player.tell(Text.gold('[ATM10 汉化] ')
      .append(Text.yellow('发现新版本 ' + latest + '（当前 ' + HANHUA_VERSION + '）。'))
      .append(Text.green(' [点击下载]').clickOpenUrl(RELEASES_URL)
        .hover('打开 GitHub Releases 最新正式版页面')))
  }

  ClientEvents.loggedIn(event => {
    if (settled || task !== null) return
    // dev 构建解析不出版本号，不发请求也不写日志。
    if (releaseVersion(HANHUA_VERSION) === null) return
    if (skipByEnv()) return
    startRequest()
  })

  ClientEvents.tick(event => {
    if (settled || task === null) return
    ticks++
    if (!task.isDone()) {
      if (ticks > GIVE_UP_TICKS) {
        try { task.cancel(true) } catch (err) { /* 已经结束了就无所谓 */ }
        done('更新检查超时，本次不提示')
      }
      return
    }

    let matched = null
    let latest = null
    let latestVersion = null
    try {
      // BasicResponseHandler 遇到非 2xx 会抛异常，走到这里说明拿到了正文。
      matched = String(task.get()).match(/"tag_name"\s*:\s*"([^"]+)"/)
    } catch (err) {
      return done('更新检查失败（网络或 GitHub 限流）：' + err)
    }
    done(null)
    if (!matched) {
      console.warn('[ATM10 汉化] 更新检查：响应里没有 tag_name')
      return
    }

    latest = matched[1]
    latestVersion = releaseVersion(latest)
    if (latestVersion === null) {
      console.warn('[ATM10 汉化] 更新检查：看不懂的版本号 ' + latest)
      return
    }
    if (isNewerVersion(latestVersion, releaseVersion(HANHUA_VERSION))) tell(latest)
  })
})()
