# 校验规则

`scripts/check.py` 是这些规则文件的解释器。
每条规则是一个对象，`kind` 决定用哪个检查器，其余字段是这条规则的参数。

加一条同类规则，只改这里的 JSON。加一种新检查器，才需要动 `check.py`。

这么分是因为有两类东西会持续累积：废弃译名、豁免白名单。它们写进脚本的话，
脚本会越积越乱，所以都放在 JSON 里，例如废弃译名在 `terms.json`。

## 字段

所有规则都有：

| 字段 | 说明 |
|---|---|
| `id` | 唯一标识，报错时打印，方便定位是哪条规则 |
| `kind` | 检查器名字。未知的 `kind` 直接让校验失败，防止改错字段名后规则静默失效 |
| `why` | 必填。为什么有这条规则。多数规则来自真实问题，写清原因，以后才能判断能不能删、能不能改 |

`scope` 缺省是 `tree`（查出货树）。`repo` 表示查整个仓库。

## 检查器一览

| kind | 干什么 |
|---|---|
| `json_parses` | glob 命中的文件必须是合法 JSON |
| `json_assert` | 某个 JSON 文件里某个路径的值必须等于给定值 |
| `file_absent` | 这个文件不许存在（防止废弃的产物再次出现） |
| `filename_prefix` | glob 命中的文件名必须带前缀 |
| `forbidden_text` | 一批词不许出现在文件里，可按路径尾巴豁免 |
| `vp_shape` | VaultPatcher 模块的 JSON 结构 |
| `vp_pair_key_in` | 某批原文串不许被替换（可限定只查「有风险」的块） |
| `vp_pair_regex` | 原文匹配某正则且译文含中文时报错 |
| `vp_server_global` | 服务端模块清单里不许有全局替换块 |
| `vp_keybind_names` | 替换的原文不许与按键注册名及其字符串片段相同 |
| `gui_choice_ascii` | `.gui` 里 `choice(...)` 的参数必须保持英文 |
| `format_safety` | 译文的占位符 / 颜色码不得比英文原文更危险 |
| `snbt_no_dup_keys` | 任务书 delta 之间不许有重复键 |
| `pb_single_source` | 蜂名脚本表必须与资源包 zh_cn 一致 |
| `vp_value_conflict` | 同类同原文同匹配模式下不许有两句译文 |
| `term_binding` | 英文词与中文词双向绑定，出现其一必须出现其二 |
| `tiered_family` | 同一族 N 档的词干必须相同、档位后缀写法必须统一 |
