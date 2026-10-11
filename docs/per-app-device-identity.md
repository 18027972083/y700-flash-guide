# 按应用机型伪装：微信双登 + 三角洲 165 + 小米生态三全其美

> 接续 [165hz-unlock.md](165hz-unlock.md) 与 [dual-flash-log](dual-flash-log-20261011.md)。
> 场景：TB322FC 澎湃 OS 4（piano 底包）+ KernelSU + Zygisk Next，**不引入 LSPosed**（隐藏检测风险）。
> 目标：微信手机+平板双登、三角洲 165+高画质、小米生态原生身份，三者互不干扰。

## 冲突的由来：一个全局身份喂不饱三个消费者

| 消费者 | 判定依据 | 需要的身份 |
|---|---|---|
| 微信（`inTabletEnv`） | 客户端硬编码机型白名单（见下） | 白名单内机型 |
| 三角洲（画质帧率白名单） | 服务端按 Build 机型下发 | iQOO Pad Ultra（165+高画质档） |
| 小米生态（账号/系统服务） | 原生属性 | piano（小米平板 8 Pro） |

微信判定机制的实锤：微信有一个 `inTabletEnv` 布尔判定，方法内拿 `Build.MODEL` 比对一张
硬编码的平板机型表，全部未命中即按"手机"登录（顶掉真手机）。开源项目
[WeKit](https://github.com/Ujhhgtg/WeKit)（定位该方法的特征串是 `"Lenovo TB-9707F"`、`"eebbk"`）
与 [TabletHook](https://github.com/roro2239/TabletHook)（还 hook 服务端
`/cgi-bin/micromsg-bin/checkloginaspad`）的源码证实了这一机制。iPA2691 太新不在表内 →
全局伪装 iQOO 的代价就是微信双登失效；QQ 用另一套判定，不受影响。

关键转机：**底包原生身份 piano（小米平板 8 Pro，25091RP04C）本身就在微信白名单里**，
小米生态又天然匹配——所以正确架构不是"换一个全局身份"，而是：

```
全局 = 原生 piano（微信✓ 小米生态✓ QQ✓）
三角洲 = device_faker 单独喂 iPA2691（165✓）
```

## device_faker：Zygisk 按应用机型伪装

[Seyud/Device_Faker](https://github.com/Seyud/Device_Faker)（Rust 实现）：按包名做
Build 字段覆写 + COW 属性伪造（mmap 写时复制，per-process 隔离，进程退出零残留），
**只对配置过的应用生效**；改配置仅需重启对应应用；自带 KSU WebUI。

安装要点（两个坑）：

1. 模块安装器把 `/data/adb/device_faker/config/` chcon 成 `system_file`，
   交互式 su 域对它**只读**（cat 可以，`>` 写入被拒）。config 是安装时由 ksud
   安装域部署的——把定制 `config.toml` 直接打进 zip 重装即可（顺带把 customize.sh
   里"音量键选择配置"的交互段删掉，否则重装时会保留旧配置）。
2. 想伪装的包名写进 `[[apps]]` 即可，其余应用零影响：

```toml
[[apps]]
package = "com.tencent.tmgp.dfm"
model = "iPA2691"
device = "DPD2605"
product = "DPD2605"
brand = "iQOO"
manufacturer = "iQOO"
marketname = "iQOO Pad Ultra"
# 备选：PLK110（一加15，也是 165Hz 白名单机型）
```

本仓库 `modules/device_faker_y700/config.toml` 就是这份定制配置。

## 第二只拦路虎：系统层 60fps 锁（PowerKeeper）

游戏内 165 解锁后，实测屏幕被锁 60。逐层定位：

1. `dumpsys display`：活动档掉到 modeId 5（60Hz），投票
   `PRIORITY_MIUI_REFRESH_RATE max=60`——不是应用请求、不是温控（currentTemp=0）、
   不是低电量（充电中 34%）、不是省电模式（均关闭）。
2. PowerKeeper 自己的日志：`[DisplayFrameSetting] setScreenEffect
   pkg=com.tencent.tmgp.dfm fps=60 cookie=254`，运行时配置
   `fpsconfig mPrivGames={com.tencent.tmgp.dfm=60}`（云端 `_c.0.0` 版本下发）。
3. 结论：PowerKeeper 的每游戏帧率协商表**按底包机型（piano，144Hz 档）谈的价**，
   它读真实设备属性，不看应用视角的伪装——device_faker 对它无效。

试过无效的两条路（记录供避坑）：

- 改 `user_configure.db` 的 `key_priv_names`（`com.tencent.tmgp.dfm:120`）→
  短暂生效一次 `fps=120`，随即被云端 `mPrivGames=60` 压回（云端优先级更高）；
  且 PowerKeeper 自动重启会带着旧内存状态随时写回 DB。
- 改 `highest_fps_group`（defineList/customList 加 dfm）→ 运行时的
  `mDefineHighestFpsApps/mCustomHighestFpsApps` 来自 `CLOUD_HIGHEST_FPS_GROUP`
  云端配置，根本不读这行 DB。

## 解法

```bash
adb shell su -c "pm disable-user --user 0 com.miui.powerkeeper"
```

禁用后 PowerKeeper 的 SceneFps 通道消失，全局 165 投票直接生效，游戏前台实测
`mActiveRenderFrameRate=165.0`。内核/高通层温控仍然在，只是失去 MIUI 的智能省电
与温控策略——游戏场景这正是想要的效果，代价是日常续航管理变松。恢复：

```bash
adb shell su -c "pm enable com.miui.powerkeeper"
```

（恢复后 60 锁会回来；可以只在游戏时禁用。）

## 最终验证

- 微信：平板上报小米平板 8 Pro → 扫码后手机提示"手机和平板同时在线"，双端在线 ✓
- 三角洲：游戏进程读 iPA2691 → 游戏内 165 选项放出；系统层 165Hz（投票 165，
  无 60 压制）✓
- 隐藏检测：全链不涉及 LSPosed，栈内仍只有 Zygisk Next + Assistant + HMA + TS ✓

## 回退

| 想还原什么 | 操作 |
|---|---|
| 三角洲伪装 | device_faker 删除 `[[apps]]` 条目或卸载模块 |
| 全局 iQOO 身份 | `ksud module enable tb322fc_identity_os4` + 重启 |
| PowerKeeper | `pm enable com.miui.powerkeeper` |
