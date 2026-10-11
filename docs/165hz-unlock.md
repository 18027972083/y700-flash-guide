# 澎湃 OS 4 解锁 165Hz 全局刷新率（Y700 四代实录）

> 适用场景：任意"面板支持高刷、但 HyperOS 策略把大部分应用压在 120Hz"的设备。
> 实测环境：Y700 四代 TB322FC，澎湃 OS 4.0.0.37 移植包（piano 底包），KernelSU（LKM）root。
> 全过程用 adb + root 即可复现，可完整回退。

## 现象

- 显示设置里刷新率上限 120Hz；即使用 adb 把 MIUI 的 `user_refresh_rate` 写成 165，大部分应用仍然只跑 120。
- 但 `dumpsys display` 显示**硬件层没有锁**：

```
DisplayDeviceInfo{"内置屏幕": 1904 x 3040, ...
  supportedRefreshRates [165.0, 144.00002, 120.00001, 90.0, 60.000004, 30.000002],
  supportedModes [{id=1, fps=120.00001}, {id=2, fps=165.0}, {id=3, fps=144.00002},
                  {id=4, fps=90.0}, {id=5, fps=60.0}, {id=6, fps=30.0}]
  defaultModeId 2        ← 165Hz 是内核默认档
```

## 排查：锁到底在哪一层

### 第 1 层：Settings 键（120 的直接来源）

```
adb shell settings list system | grep -i refresh
    peak_refresh_rate=120
adb shell settings list secure | grep -i refresh
    miui_refresh_rate=120
    user_refresh_rate=120        ← MIUI"刷新率"开关真正写的键
    support_highfps=1
```

把这几个键改成 165（`settings put ...`）后，桌面确实短暂跑上 165——
**但这是陷阱**：几秒后投票日志出现 `[RefreshRate] DOWN policyEnd`，回落 120。
写入设置的动作触发了 MIUI 的"交互加速（UP）"，加速结束又回到基础策略 120。
**验证刷新率必须看稳定态，不能在改完设置的几秒内看。**

### 第 2 层：PowerKeeper 策略上限（persist 属性）

`dumpsys display` 的 MIUI 扩展段给出了决定性证据：

```
RefreshRatePolicyController
  refresh rate support: [144, 165, 120, 90, 60, 30]
  user refresh rate: 165          ← 我们的设置它读到了
  max refresh rate in policy: 120 ← 但策略上限仍是 120
Local Log:
  [Config] defaultEnable=false maxRate=120 userRate=165
```

把 `user_refresh_rate` 改成 60 再改回 165，日志同步变成
`maxRate=60 userRate=60` → `maxRate=120 userRate=165`——
**maxRate = min(userRate, 一个 120 的上限)**。这个上限来自：

```
adb shell getprop | grep smartpower
  [persist.sys.smartpower.limit.max.refresh.rate]: [120]
  [persist.sys.smartpower.limit.normal.max.refresh.rate.enable]: [true]
  [persist.sys.smartpower.limit.normal.max.refresh.rate.support]: [120]
```

（来源定位：`grep -rl 'smartpower.limit' /system*/framework` 只命中
`/system_ext/framework/miui-services.jar`，即 system_server 内的 MIUI 智能省电显示策略。）

### 第 3 层：开机默认 `mLockedMaxRefreshRate=120`

把两个 persist 属性改成 165 后重启，属性值保留了，但策略上限**仍是 120**——
`DisplayModeDirector` 段里 `mLockedMaxRefreshRate: 120.0` 没变。
说明该策略在运行时不重读属性，开机时把锁初始化为 120。

## 关键发现：属性要"变化"才会触发重评

**切换属性值制造变化事件**（而非只把值改对）：

```bash
adb shell su -c "setprop persist.sys.smartpower.limit.max.refresh.rate 166"
sleep 2
adb shell su -c "setprop persist.sys.smartpower.limit.max.refresh.rate 165"
```

变化事件一到，策略立刻重新评估：

```
mLockedMaxRefreshRate: 0.0          ← 锁清零
PRIORITY_MIUI_REFRESH_RATE -> RenderVote{ mMaxRefreshRate=165.0 }
mActiveRenderFrameRate=165.0        ← 实际渲染 165
```

注意两个坑：

1. `setprop` 对这些属性**偶发被 init 拒绝**（"Failed to set property"），原因未明
   （疑似与策略服务并发写回有关）。对策：失败重试，或用 166/165 来回切制造事件。
2. 值写成 166 也无妨——显示服务只会选最接近且不超过投票值的实际档位（165）。

## 解法：`modules/y700_os4_max_fps` KSU 模块

开机后 20 秒自动执行（等 `sys.boot_completed=1`，给 MIUI 留出上锁时间）：

1. 对两个 smartpower persist 属性做"166↔165 切换"（带 8 次重试）制造变化事件 →
   触发 MIUI 重评、`mLockedMaxRefreshRate` 清零；
2. 重写 `peak_refresh_rate=165.0`、`min_refresh_rate=165.0`、
   `user_refresh_rate=165`、`miui_refresh_rate=165`（防 MIUI 界面操作重置）；
3. `cmd display set-user-preferred-display-mode 1904 3040 165` 钉死首选档
   （此命令 shell 身份会报 `SecurityException`，必须 root；持久化在
   `Settings.Global.user_preferred_refresh_rate`）。

安装：

```bash
adb push y700_os4_max_fps.zip /data/local/tmp/
adb shell su -c "ksud module install /data/local/tmp/y700_os4_max_fps.zip"
adb reboot
```

## 验证（稳定态）

```bash
# 等 30 秒以上再验证
adb shell dumpsys display | grep -E "mActiveModeId|mActiveRenderFrameRate"
    mActiveModeId=2            ← modeId 2 = 165Hz
    mActiveRenderFrameRate=165.0

# 看锁与投票
adb shell dumpsys display | grep -E "mLockedMaxRefreshRate|PRIORITY_MIUI_REFRESH_RATE"
    mLockedMaxRefreshRate: 0.0
    PRIORITY_MIUI_REFRESH_RATE -> RenderVote{ mMaxRefreshRate=165.0 }

# 第三方应用前台也应保持 165（PowerKeeper 不再单独压包）
```

实测：重启后桌面、第三方文件管理器稳定 165Hz；开机日志可见投票从
120（MIUI 默认锁）被模块翻转成 165 的完整过程。

## 回退

- 折中省电（保留 165 上限，允许动态降频）：
  `adb shell settings put system min_refresh_rate 0.0`
- 完全还原：KSU 管理器禁用 `y700_os4_max_fps` 模块 → 重启 →
  显示设置里把刷新率调回 120（会重写 `user_refresh_rate`）。

## 附：这条链路上查过但**不是**元凶的东西

- `ro.vendor.display.*`（idle fps、dynamic_refresh_rate 等）：SF 空闲降频参数，与上限无关
- `/product/etc/device_features/piano.xml`：无刷新率相关键
- PowerKeeper `highrefreshrate.db`：强制高刷白名单（incallui 等 5 个包）
- PowerKeeper `user_configure.db` 的 fps 分组（list60/list90/highest_fps_group）：
  按包名压帧率，但不解释全局 120
- PowerKeeper `cloud_configure.db`：云端下发的 GlobalFeatureTable 无刷新率项
- Android 16 的 `FrameRateCategoryRate {normal=60, high=90}`：只影响走
  FrameRateCategory API 的应用，非本例主因

## 代价与取舍

LCD 无 LTPO，全局钉 165 比动态 120 明显费电。折中方案见"回退"节。
游戏内帧率仍由游戏自己决定——系统上报峰值 165 后，游戏端才有机会放出更高档位
（能否放出还取决于游戏自身的机型白名单，见 [dual-flash-log](dual-flash-log-20261011.md)）。
