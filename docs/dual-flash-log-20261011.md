# 双机实录：二代上 ColorOS 16，四代上澎湃 OS 4

> 本文是本仓库 [flash-guide.md](flash-guide.md)（TB322FC 刷 ColorOS 16 完整流程）的续篇：同一天完成了二代 TB320FC 刷 ColorOS 16 与四代 TB322FC 换澎湃 OS 4 的双机操作。
> 仓库 modules/tb322fc_identity 身份模块（model/device=TB322FC 保三角洲 144 帧）在澎湃 OS 4 上预期同样有效——KSU 默认卸载模块只移除 App 视野内的文件挂载，system.prop 级属性伪装是全局的（此推断待实测，欢迎反馈）。

## 背景

设备A：拯救者 Y700 二代 TB320FC（骁龙 8+ Gen 1）→ ColorOS 16.0.5.700
设备B：拯救者 Y700 四代 TB322FC（骁龙 8 Elite）→ 澎湃 OS 4.0.0.37 + KernelSU root + 完整隐藏环境
一天完成，序列号已脱敏（以「序列号A/B」代称）。

## 〇、写给后来者的前置认知

1. **Y700 全系支持 9008（EDL）免解锁刷机**：不需要解 BL 锁，用工程引导（firehose/programmer）+ QFIL/fh_loader 可以整包刷写。这是整个生态的根基——**刷坏也能用 9008 救回来**。
2. **刷机前必做分区备份**（root 状态下 dd 全部关键分区到电脑）：`persist`、`modemst1/2`、`fsc/fsg`、`proinfo`（四代）、`lenovolock`、`lenovocust`、`lenovoraw`、`apdp/apdpb`、`devinfo`、`frp`、`keystore`、`secdata`、`ssd`、`splash`、`spunvm` 等，外加 boot/init_boot/vendor_boot/vbmeta/dtbo/recovery 的 A/B 双槽。**这些文件含序列号和校准数据，刷机包会覆盖它们（两台均实证，见下文），备份是唯一的后悔药。**
3. 移植包主要来源：酷安 **GUF26 / GUF296 / 兰微卡鱼**，B站 **悲伤的压缩包**（bszip.me，其网盘常年更新各代刷机包 + 9008 救砖包 + 教程视频）。
4. Y700 命名对照：2022 一代(870) / 2023 二代(8+Gen1, TB320FC) / 2024 三代(8Gen3, TB321FU) / 2025 四代(8Elite, TB322FC) / 2026 五代。**刷机包必须严格对应代际，跨代即砖。**

## 一、二代（TB320FC）：ColorOS 16

### 包与来源
- **ColorOS16.0.5.700_A16_TB320FC**（作者：酷安@兰微卡鱼），底包一加平板 2 Pro（OPD2413/OP615EL1）
- 9008 线刷包结构：`images/`（全套分区镜像 + rawprogram0-5.xml + patch0-5.xml）+ `bin/9008/`（QPST/QFIL + Y700_2023_prog_firehose_ddr.elf）+ 官方包内置 `点我一键刷入.cmd` 三模式脚本（Fastboot保数据 / Fastboot双清 / 9008深度线刷）
- 分发：bszip.me 收录，迅雷云盘

### 流程（9008 深刷）
```
1. adb reboot edl（或关机按住音量上插线）
2. QSaharaServer -p \\.\COMx -s 13:"...\Y700_2023_prog_firehose_ddr.elf"
3. fh_loader --sendxml=rawprogram0~5.xml,patch0~5.xml --setactivepartition=1
   --memoryname=ufs --reset
```
4. 卡开机 → **9008 擦 userdata+metadata**（按 rawprogram 里两个分区的 start_sector/num_partition_sectors 生成 erase XML）→ 正常开机

### ⚠️ 重大踩坑：移植包会覆盖身份数据（SN 变更）
ColorOS 包的 rawprogram **带文件名刷写了 lenovolock（SN/锁区）、lenovocust（300MB 定制数据）、lenovoraw、oemowninfo、apdp、modemst1/2**——刷完设备序列号变成了包作者的（USB 层直接可见）。
**还原方法**：用刷机前备份的原厂镜像，按包内 rawprogram 相同的扇区参数生成 restore XML，fh_loader 写回。8 个分区 1 分钟，序列号立即恢复。
> **给所有刷 Y700 移植包的人：刷完必查 `adb shell getprop ro.serialno`，不对就用备份还原 lenovolock 等分区。**

## 二、四代（TB322FC）：澎湃 OS 4

### 包与来源
- **澎湃OS4.0.0.37（0928）**（移植作者：酷安 GUF296，底包小米平板 8 Pro/spinel），2026-10-01 发布
- 包结构：`y700-hyper/images/`（super.img 22GB + 全套底层镜像 + rawprogram/patch XML + **xbl_s_devprg_ns.melf**）+ `tool/`（BFF 高通工具箱 GUI + 全套命令行 + 三种驱动）+ 免解锁 root 镜像 9 种（KernelSU/SukiSU/APatch/KowSU/7kk/FolkPatch 等 LKM 版 + ReSukiSU）
- 参考教程：imaegoo《Y700 四代（TB322FC）刷入澎湃 OS 3 教程》（OS3 同款流程）、B站@悲伤的压缩包

### 流程
1. 进 9008（adb reboot edl）
2. BFF 高通工具箱：发送引导（选 images 里的 melf，**不要选 tool/bin 下 legion-y700-5 系列那是五代引导**）→ 读取信息（验证 firehose 活着 + 96 项分区表）→ 「使用XML文件」全选 rawprogram0~5 + patch0~5 → 刷写（40MB/s 下约 17 分钟）
3. **首刷必做恢复出厂**（工具箱下拉菜单内置；不清数据必卡开机）
4. 如进 recovery → 手动双清后重启

### Root（免解锁 LKM 方案）
- 刷「澎湃OS4.0.0.37_KernelSU_LKM.zip」内的 init_boot.img 到 **init_boot_a + init_boot_b 双槽**（fh_loader 单独写或工具箱"从文件"刷写）
- 重启后装 KernelSU 管理器 → 工作中 / LKM / SELinux Enforcing
- LKM 走内核模块注入，内核本体不动，KMI 匹配 6.6.118-android15-8

### 隐藏环境（三角洲等 ACE 反作弊游戏实测过检）
- **悲伤一键隐藏环境 v1.9.1**（bszip.me 首页，「支持 Magisk/KernelSU/APatch 及分支」，WebUI 管理，自动更新 Ts 包名 + 云端更新密钥）
- 该模块安装时会**云端自动部署全家桶**：LSPosed、HMA-OSS、Play Integrity Fix [INJECT]、TEESimulator-RS、TS-SilentListen
- WebUI 三个必点：更新 TS 包名（同步包名到 target.txt）/ 配置隐藏应用列表（HMA 一键还原）/ 更新哈希值（vbmeta 摘要）
- **⚠️ Hunter 检测「高风险设备，可能存在攻击行为」的元凶 = LSPosed + PIF + Tricky Store(TEE模拟器) 三个注入类组件。全部禁用（ksud module disable）只保留 Zygisk Next + Zygisk Assistant + HMA + 悲伤环境本体后，Hunter 复测通过。**
- 底层属性（locked/green）在 OS4 包上保持免解锁伪装状态，属性层面无破绽
- 旁路充电：小米平板 8 Pro 底包本身无此功能，无解（Lenovo 特性未随包）
- 侧边充电口：实测可用（包的 USB 配置实际支持双口）

## 三、人脸识别无法录入的深度排查（四代/澎湃OS4，未解决，等作者）

**现象**：录入秒失败，errCode=2「无法验证人脸，请重试」，全程不到 10ms（未开摄像头）。

**排查过程与排除项**：
```
日志：Y700MiFace: FaceHAL enroll: rejecting invalid metadata
      features_supported=true challenge_valid=true hat_valid=false mac_len=32
```
1. ✅ miface 全栈在位且运行：mifaced 守护（Rust）/ miface_face 库目录（商汤 stfaceunlock + TFLite）/ face-v4 VINTF 声明 / biometric 服务注册 face 传感器（modality 8）
2. ✅ 排除 SELinux 属性拦截：补 allow system_app→vendor_miface_prop、system_server→vendor_default_prop 后无变化
3. ✅ 排除 enroll_version 属性缺失：该属性仅 Settings 读取，已手动设置 persist.vendor.miface.info.enroll_version=1，无变化
4. ✅ 排除 HAT 过期：输完锁屏密码 5 秒内点录入（新鲜令牌），无变化
5. ✅ 排除身份数据被覆盖：还原 lenovocust/lenovoraw/apdp 原厂备份后无变化（lenovoraw 原件在历史刷机中已不可考）

**结论**：HAT 由设备 qti keymint/gatekeeper 现场签发（mac_len=32 格式正常），但 GUF296 的 Y700MiFace v4 HAL 校验不通过——**HAL 内的 HAT 校验密钥/协议与 TB322FC 的 qti TEE 签发链不兼容，需作者在 HAL 源码层修复**。建议：如 OS3（3.0.307）人脸正常，可将 OS3 的 HAT 校验逻辑回移植到 OS4。

## 四、资源与工具速查

| 资源 | 位置 |
|---|---|
| 二代 ColorOS16 + 官方救砖包 | bszip.me/9008 「联想y700二代免解锁bl刷root」（迅雷，提取码 zvvf） |
| 四代澎湃OS4.0.0.37 | B站 BV1bPYc6NE2p 简介迅雷链接（提取码 zh5v） |
| 悲伤一键隐藏环境 v1.9.1 | bszip.me 首页（迅雷，提取码 3jun，附酷安图文+B站教程） |
| 二代官方9008救砖包 | bszip.me/9008（提取码 r8m2） |
| 四代官方 ZUI 线刷包 | onfix.cn / donghairom.com |
| OS3 四代图文教程 | imaegoo.com/2026/y700-tb322fc-flash-hyper |

## 五、教训总结

1. **备份先行**：root 状态下 dd 备份全部关键分区再动手，两个包都实证会覆盖身份数据分区
2. **刷完必验序列号**（getprop ro.serialno），不对就用备份还原
3. **跨系统刷机（ZUI/ColorOS/澎湃互刷）必擦 userdata+metadata**，否则卡开机——9008 下用 erase XML 擦最干净
4. **红线**：不碰 provision_ufs*.xml、不点"全部格式化"（SN/IMEI 不可逆丢失）、不用错误代际的引导文件
5. **隐藏的悖论**：LSPosed/PIF/TEE模拟器这类注入组件自己就是高级检测器（Hunter/Momo）的靶子——**用不上就禁用**，最小暴露面 = 最高过检率
6. 排查神装：`dumpsys biometric`、logcat 三轮对比、对 HAL 库做字符串分析——本文人脸问题从"不能录入"定位到"HAT 校验不兼容"全靠这套组合拳
