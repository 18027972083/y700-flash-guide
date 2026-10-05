# 联想拯救者 Y700 四代（TB322FC）刷 ColorOS 16 移植版 · 推荐流程与排障手册

> 生成日期：2026-09-30
> 用途：技术交接 / 整理发布。本文档为**脱敏版**：不含设备序列号、用户路径、任何固件/工具二进制。
> 结构说明：第 4 节为**推荐流程**（按理想顺序整理，照做即可）；第 6 节为**可能出现的问题**（实测踩过的坑及处理）。
> 所有固件与第三方工具请从各作者官方渠道获取（见第 9 节链接清单）。

---

## 1. 任务概述

把联想拯救者 Y700 四代（TB322FC，Android 16 / ZUXOS 1.5.10.259）通过 9008（EDL）线刷，刷成从一加平板 2 Pro（OPD2413）移植的 **ColorOS 16.0.8.300**（OPPO Pad Mini UI 适配版），并完成：

1. Bootloader 完整解锁
2. Root（SUkiSU，LKM 内核模块模式）
3. 游戏画质/帧率档位恢复（144 帧 + 高清共存）

系统 OTA 屏蔽为移植包自带特性（见第 10 节已知降级）。

最终设备状态：ColorOS 16.0.8.300 正常使用，开机约 25 秒，SUkiSU 管理器显示「工作中」，三角洲 144+高清可用。

---

## 2. 设备与约束（关键前提）

| 项 | 值 |
|---|---|
| 机型 | TB322FC（Y700 四代），SM8750（骁龙 8 Elite），16GB+512GB |
| 屏幕 | 1904x3040（3K），刷新率档位 30/60/90/120/144/**165**Hz（全档全分辨率） |
| 初始系统 | ZUXOS 1.5.10.259（Android 16） |
| 初始 BL 状态 | 锁定；**官方 sn.img 解锁与"直刷免解锁镜像"在 .259 上均不可行**（unlock 分区被删、ABL 信任密钥已换为生产密钥） |
| 唯一可行路径 | 9008（EDL）线刷移植包（覆盖全引导链）+ 专用工具箱解锁 |

**重要结论**：此机型在 .259 版本后，常规玩法（fastboot flashing unlock / 官方解锁申请）全部失效，必须走本文档的 9008 + 工具箱路线。

---

## 3. 硬件与模式操作速查

| 操作 | 按键方法 |
|---|---|
| 强制重启 | 长按「电源 + 音量减」 |
| 关机进 fastboot | 长按「音量加 + 电源」直到出现 fastboot 画面 |
| 关机直进 9008（EDL） | 完全关机后，**按住音量加，再插入 USB**（不要按电源键） |
| 系统内进 9008 | `adb reboot bootloader` → `fastboot oem edl`（锁定状态也有效） |
| 系统内进 fastboot | `adb reboot bootloader` |
| 工具流程中进 9008 | 按住音量加不松手，工具触发重启，黑屏瞬间松其他键只留音量加 |

**USB 口**：务必使用平板**长边**的 USB 口；数据线用原装。

**9008 确认**：设备管理器出现 `Qualcomm HS-USB QDLoader 9008 (COMx)`；`qdl.exe list` 显示 `05c6:9008`。

---

## 4. 推荐流程

### 阶段 0 · 素材准备与刷前验证

| 素材 | 用途 | 获取方式（见第 9 节） |
|---|---|---|
| ColorOS 16.0.8.300 移植包（单 zip，约 8.3GB） | 主体刷机包（QDL/EDL 格式，含 images/、tools/qdl/、root/、modules/） | 移植作者 123 网盘 |
| 刷机匣、xbl_s_devprg_ns.melf、免解锁 root 镜像包 | 辅助工具与 root 载荷 | UP 主迅雷网盘 |
| 解锁工具箱（"联想拯救者Y700四代工具箱"） | 解锁 BL 专用（含 abl_unlock.img、devprg、frp 修补、sn 生成） | 玩机资源百度网盘 |
| QDL v2.7（Windows x64） | 9008 刷写工具 | 移植包内 `tools/qdl/` 自带 |
| adb / fastboot | 设备通信 | Google platform-tools |
| avbtool.py + AOSP testkey_rsa4096.pem | 修复/重签 vbmeta 用 | AOSP / LineageOS 镜像仓库（公钥私钥均为公开测试密钥） |
| 官方救砖包（ZUXOS，任选版本） | 回滚保底 | lolinet 镜像站 / 玩机资源网盘 |

**电脑环境**：安装高通 QUD 驱动（或系统已带 Qualcomm HS-USB 驱动）；关闭休眠；只用一条数据线连接设备。

**刷前验证（不要跳过）**——本移植包存在已知构建缺陷（vendor_boot 与 vbmeta 描述符不同步，见第 5 节第 1 条），验证可以发现并在刷写前修掉：

```bash
# 1) 全包完整性校验（Python 脚本，见本仓库 scripts/check_sha256.py）
python check_sha256.py --zip 移植包.zip --sums SHA256SUMS.txt   # 111/111 文件全部一致才算通过

# 2) vbmeta 描述符 vs 实际镜像哈希验证（scripts/verify_vbmeta.py）
python verify_vbmeta.py --pkg 解压后的包目录
#    → vendor_boot 显示 MISMATCH 则必须先重签 vbmeta（见下），否则首启必失败
```

**预修 vbmeta（验证发现不同步时执行）**：

> 该包的 vbmeta 本来就用 AOSP 测试密钥签名（公钥 SHA1 `2597c218aae470a130f61162feaae70afd97f011`），私钥为公开测试密钥，可直接复用重签。

```bash
# 1) 从 LineageOS 镜像仓库获取测试密钥（android_external_avb 的 test/data/testkey_rsa4096.pem）
# 2) 导出公钥（用于 chain partition）
python avbtool.py extract_public_key --key testkey_rsa4096.pem --output testkey.avbpubkey
# 3) 重建 vbmeta：保留全部 chain（boot/recovery/vbmeta_system）+ hash 描述符（dtbo/init_boot/vendor_boot）
python avbtool.py make_vbmeta_image \
  --output vbmeta_fixed.img --key testkey_rsa4096.pem --algorithm SHA256_RSA4096 \
  --rollback_index 0 --rollback_index_location 0 --flags 0 --padding_size 65536 \
  --chain_partition boot:3:testkey.avbpubkey \
  --chain_partition recovery:1:testkey.avbpubkey \
  --chain_partition vbmeta_system:2:testkey.avbpubkey \
  --include_descriptors_from_image images/dtbo.img \
  --include_descriptors_from_image images/init_boot.img \
  --include_descriptors_from_image images/vendor_boot.img
# 4) 覆盖包内文件，随整体刷写一起写入
cp vbmeta_fixed.img images/vbmeta.img
#    注意：覆盖后 vbmeta.img 不再匹配包内 SHA256SUMS.txt，属预期
```

**QDL dry-run 预验证**（不读设备，仅解析 XML 与文件引用）：

```bash
qdl.exe --dry-run images/prog_firehose_ddr.elf \
  images/rawprogram0.xml images/rawprogram1.xml images/rawprogram2.xml \
  images/rawprogram3.xml images/rawprogram4.xml images/rawprogram5.xml \
  images/patch0.xml images/patch1.xml images/patch2.xml \
  images/patch3.xml images/patch4.xml images/patch5.xml
# 必须以状态码 0 退出且无缺文件
```

### 阶段 1 · 9008 线刷移植包

> 原包内含作者操作手册 `AGENTS.md`，可作参考；以下为实测流程。

1. **进 9008**：`adb reboot bootloader` → `fastboot devices` 确认 → `fastboot oem edl`
2. **清数据**（从官方系统跨厂商必须清；`-R` 保持 Firehose 会话不复位）：
   ```bash
   qdl.exe -R images/prog_firehose_ddr.elf erase 0/metadata erase 0/userdata
   ```
3. **立即完整刷写**（不带 `-R`，完成后自动复位；约 12 分钟 / 25GB）：
   ```bash
   qdl.exe images/prog_firehose_ddr.elf \
     images/rawprogram0.xml images/rawprogram1.xml images/rawprogram2.xml \
     images/rawprogram3.xml images/rawprogram4.xml images/rawprogram5.xml \
     images/patch0.xml images/patch1.xml images/patch2.xml \
     images/patch3.xml images/patch4.xml images/patch5.xml
   # 成功标志：flashed 逐条成功、78 patches applied、partition 1 is now bootable、EXIT=0
   ```
4. **等待重启**：首启较慢（首次开机初始化），耐心等待；异常情况见第 6 节。

### 阶段 2 · 首启验证

按推荐流程（阶段 0 预修过 vbmeta）刷写完成后，设备应正常进入 ColorOS 系统。

- 若**反复回到 fastboot / 无法启动** → 见第 6 节 Q1（含完整诊断与两种修复路径）。
- 若**卡在开机动画 / 黑屏**：先等待 5 分钟（首启初始化）；仍无反应时强制重启一次。

### 阶段 3 · 完整解锁 BL（专用的第三方工具箱）

> 解锁是后续 fastboot 写入（Root）与槽状态重置的前提。本案例在首启异常后执行解锁并成功启动；按推荐流程预修后再刷的设备也应完成本阶段以保障后续操作。

**联想解锁的真实机制**（与 AOSP 标准不同，`fastboot flashing unlock` 命令已被联想从 bootloader 中移除，`get_unlock_ability=1` 也不代表可以直接解锁）：

```
1) 9008 下：备份 abl/frp → 刷入"解锁版 abl"（abl_unlock.img）→ 修补 frp 分区强开 OEM 解锁
2) 重启到 fastboot：工具箱读取设备 Bootloader_SN 生成定制 sn.img →
   fastboot flash unlock sn.img → fastboot oem unlock-go
3) 设备出现解锁确认界面 → 音量键选 UNLOCK → 电源键确认（会清数据）
4) 再次进 9008：恢复原版 abl（工具箱自动完成）→ 重启
```

**操作步骤**（使用"联想拯救者Y700四代工具箱"bat 交互流程）：

1. 平板连接电脑，确保在 **fastboot** 或系统模式
2. 运行工具箱 → 选「1. 解锁BL」→ 按提示：
   - **按住平板音量加不松手** → 电脑按任意键 → 设备进入 9008
   - 工具自动：备份 abl/frp → 刷解锁版 abl → 修补 frp
   - 重启到 fastboot → 工具自动读 SN、生成解锁文件、执行解锁命令
   - **平板出现解锁确认界面 → 选 UNLOCK THE BOOTLOADER → 电源键确认**
   - 设备重启后，按提示**再进一次 9008**（按住音量加），工具恢复原版 abl
3. **验证**：`fastboot getvar unlocked` → `yes`
4. **重置槽位状态**（让设备可启动的关键一步）：
   ```bash
   fastboot --set-active=a      # 解锁前此命令被拒（Lock State），解锁后可用
   fastboot reboot
   ```
   → 设备进入系统，ColorOS 首次启动成功。

**工具卡住时**：见第 6 节 Q2（不要慌，手动完成等价操作）。

### 阶段 4 · Root（SUkiSU，LKM 模式）

**素材**：SUkiSU LKM 包（`init_boot.img` + `vbmeta.img` + `SukiSU APK`），来自 UP 主"免解锁镜像"合集。

**重签 vbmeta（标准步骤，不要跳过）**：SUkiSU 自带的 `vbmeta.img` 是 7 月构建，其 `vendor_boot` 描述符对应旧版镜像——直接刷会导致 AVB 失败。必须自行重签（方法同阶段 0，仅描述符来源不同）：

```bash
python avbtool.py make_vbmeta_image \
  --output vbmeta_suki.img --key testkey_rsa4096.pem --algorithm SHA256_RSA4096 \
  --rollback_index 0 --rollback_index_location 0 --flags 0 --padding_size 65536 \
  --chain_partition boot:3:testkey.avbpubkey \
  --chain_partition recovery:1:testkey.avbpubkey \
  --chain_partition vbmeta_system:2:testkey.avbpubkey \
  --include_descriptors_from_image images/dtbo.img \
  --include_descriptors_from_image suki_init_boot.img \
  --include_descriptors_from_image images/vendor_boot.img
```

**刷入**（已解锁，直接 fastboot）：

```bash
fastboot flash init_boot_a init_boot.img   # SUkiSU 版
fastboot flash init_boot_b init_boot.img
fastboot flash vbmeta_a vbmeta_suki.img    # 自签版
fastboot flash vbmeta_b vbmeta_suki.img
fastboot reboot
# 装管理器
adb install SukiSU_v4.1.3_40796-release.apk
```

**验证**：打开 SukiSU 管理器 → 主页显示「**工作中 \<LKM\>**」即成功（内核模块已加载）。模块页面为空是正常的。

> 备注：SUkiSU 的 su 命令行（adb shell su）在 LKM 模式下不落盘（无 /system/bin/su），不影响使用——所有 root 功能通过管理器授权体系工作（MT 管理器等 App 首次执行 root 操作时会在管理器弹授权）。

### 阶段 5 · 三角洲 144 帧 + 高清画质恢复（机型适配表问题）

**现象**：刷机前（ZUXOS）三角洲可选「144 帧 + 高清画质」；刷 ColorOS 后，**选 144 帧画质被强制降到"流畅"，想用"高清"则被强制回 120 帧**——两者互斥。

**根因**：腾讯系游戏（含三角洲）按**机型**下发画质-帧率组合适配表：

- 刷机前机型 = `TB322FC`（Y700 四代）→ 适配表：**144 + 高清**（该机型官方适配 144 帧）
- 刷机后机型 = `OPD2413`（一加平板 2 Pro，移植系统身份）→ 适配表：144 只配"流畅"

（排除法确认过显示模式表正常：`adb shell dumpsys display | grep -E "supportedRefreshRates|DisplayModeRecord"` 显示 1904x3040 全分辨率、144/165Hz 档齐全。）

**修复：混合机型身份（最小 KSU 模块）**

> ⚠️ 先划重点：**不能把品牌字段也改成联想**——会导致 ColorOS 品牌校验类服务拒绝服务（小布助手报「无法兼容当前设备」，见下方“品牌校验服务兼容”）。

自制 `tb322fc_identity` 模块（v1.1 混合身份，见本仓库 `modules/`）：

```ini
# system.prop —— 型号字段交给游戏适配表匹配，品牌字段保留一加给品牌校验服务
ro.product.model=TB322FC
ro.product.device=TB322FC
ro.vendor.product.model=TB322FC
ro.vendor.product.device=TB322FC
ro.product.brand=OnePlus
ro.product.manufacturer=OnePlus
ro.vendor.product.brand=OnePlus
ro.product.name=OP615EL1
ro.vendor.product.name=OP615EL1
```

```ini
# module.prop
id=tb322fc_identity
name=Y700 Identity Restore (Hybrid)
version=v1.1-hybrid
versionCode=2
description=Hybrid device identity: Lenovo model strings for per-model game graphics profiles + OnePlus brand strings for ColorOS brand-checked services (XiaoBu). Toggle off to revert.
```

**安装与生效**：SukiSU 刷入模块 → 重启 → `getprop ro.product.model` 确认 = `TB322FC`（brand 显示 OnePlus）→ **清三角洲缓存**（清数据更彻底）促使其重拉适配表 → 进游戏：**144 + 高清恢复** ✅

**★ 品牌校验服务的兼容（最终定稿 = v3.1）**：

品牌字段**必须**保留一加系（`OnePlus`）。heytap `BrandEnvSdk` 的白名单经反编译实测：`MD5(Build.BRAND.toUpperCase())` 必须命中 `OPPO` / `REALME` / `ONEPLUS` 三者之一，否则小布、主题商店、音乐、视频、阅读、浏览器、OPPO 商城、我的一加等整套 ColorOS 应用都会报「为定制应用，无法兼容当前设备」（机制与排查见排障手册 **Q8**）。
最终组合 = `brand/manufacturer=OnePlus` + `model/device=TB322FC`（即下面 v1.1 组合，模块定稿 **v3.1**）：2026-10-05 实测八应用全部恢复、微信双端 / 小布 / 三角洲 144+高清均正常。
**通用经验**：ColorOS 系设备改机型，品牌字段保持白名单内（OPPO 系）是硬约束；只调 model/device 满足游戏适配表即可。

**为什么安全**：

- 只改标准 `ro.product.*` 属性；ColorOS 的私有身份体系（移植作者建的"项目号 25928"路径，供 OPPO 私有 HAL/UI 读取）**不受影响**（两套并存）
- `ro.build.fingerprint` 保持 OPD2413 不动（避免 model 与指纹不一致的交叉特征）
- 模块开关即还原，完全可逆

---

## 5. 关键技术发现（流程为什么这样设计）

1. **移植包构建缺陷**：发布版 `vendor_boot.img`（9-24 更新）与 `vbmeta.img`（记录旧哈希）不同步 → AVB 校验必败。**任何刷该包者都会遇到**，所以阶段 0 的刷前验证 + 预修是必做步骤。建议向包作者反馈。
2. **RPMB 启动状态**：A/B 槽的"启动失败计数/不可启动"标记存于 RPMB 安全存储（`VB: RWDeviceState ... rpmb`），misc/UEFI 变量/全清零均**无效**；唯一重置途径 = 完整解锁流程。这也是"刷前预修"重要的原因：避免失败计数被烧掉。
3. **联想解锁机制**：标准 `fastboot flashing unlock` 已被移除；实际路径 = 刷解锁版 abl + frp 强开 + SN 定制 sn.img + `fastboot flash unlock` + `oem unlock-go` + 确认界面 + 恢复 abl。只解锁 critical（`unlock_critical`）**不会**获得刷写权限。
4. **vbmeta "chain partition" 结构**：boot/recovery/vbmeta_system 为链式分区（各自有带签名的 footer）；dtbo/init_boot/vendor_boot 为 vbmeta 内的 hash 描述符。修复时**两者都要与当前实际镜像匹配**。
5. **机型适配表**：国产游戏画质/帧率档随"机型字符串"变化。移植系统改机型（system.prop）是恢复游戏适配的通用手法。
6. **adb push 异常**（本机环境）：push 报成功但文件不落地；**base64 管道**是可靠替代（见第 6 节 Q3）。

---

## 6. 可能出现的问题（实测踩坑 → 处理）

### Q1 · 刷写全部成功但设备反复回到 fastboot（★ 最容易踩）

**症状**：101 个分区 + 78 patch 全部刷写成功，但设备反复回 fastboot，`fastboot getvar all` 显示 `slot-unbootable:a: yes`、`slot-retry-count:a: 6`（6 次启动失败耗尽）。

**诊断路径（三步，可复用于任何 QDL 刷机排障）**：

1. **读回设备分区与包内文件对比**（证明写入完整性）：
   ```bash
   qdl.exe images/prog_firehose_ddr.elf read 4/113318+24576 rb_boot_a.img   # 分区按 GPT 查 LBA
   # 对 boot/dtbo/vendor_boot/recovery/init_boot/pvmfw/super(23.6GB)/vbmeta 逐一 SHA256 对比
   ```
2. **读 ABL 日志**（`logfs` 分区，8MB，LUN4）：
   ```bash
   qdl.exe images/prog_firehose_ddr.elf read 4/logfs rb_logfs.img
   ```
   → 日志显示每次启动都走到 `VB2: boot state: orange(1)` + `BootLinux` + `Start EBS`——**引导链正常，失败发生在内核跳转之后**，且 `pstoredump` 分区全零（内核无 panic）。
3. **用 avbtool 解析 vbmeta 描述符并与实际镜像哈希比对**（关键步骤，或直接用本仓库 `scripts/verify_vbmeta.py`）：
   ```bash
   python avbtool.py info_image --image images/vbmeta.img
   ```
   → 若发现 `vendor_boot.img` 长度与描述符记录不一致 → 即移植包构建缺陷，**修复方法**：按阶段 0「预修 vbmeta」重签并写回（9008 写回双槽：自建 XML，`vbmeta_a@LUN4 sector 137946`、`vbmeta_b@LUN4 sector 346452`，各 16 扇区；或修好后整体重刷）。

**注意**：如果失败计数已经烧进 RPMB（`slot-retry-count` 耗尽），修好 vbmeta 后设备**仍然**卡 fastboot——此时唯一出路是**完成阶段 3 的解锁** + `fastboot --set-active=a` 重置槽状态。**预防方法就是阶段 0 的刷前预修**。

### Q2 · 解锁工具箱"等待 9008"卡住

工具箱在"等待 9008"步骤偶发检测卡住（USB 枚举残留）。**不要慌**，手动完成等价操作：

- 解锁确认后设备处于 fastboot，先验证 `fastboot getvar unlocked`（可能已生效，无确认界面直接生效）
- 若工具卡住：用 `qdl write` 手动恢复备份的 abl（工具箱 `bin/bak/` 下有自动备份）
- 工具箱的 frp 备份是"修补前"的，**不要恢复 frp**（会撤销解锁强开），只恢复 abl

### Q3 · adb push 报成功但文件不落地

本机环境实测的传输异常，用 **base64 管道**替代：

```bash
base64 -w0 file | adb shell "base64 -d > /sdcard/file"   # 传完 md5sum 双方校验
```

### Q4 · Root 刷完仍无 root（SukiSU 未工作）

先检查是否按阶段 4 重签过 vbmeta——直接刷 SUkiSU 自带的旧 vbmeta 会导致 AVB 失败（症状同 Q1）。重签后重刷 `init_boot` 双槽 + `vbmeta` 双槽，重启后确认管理器显示「工作中 \<LKM\>」。

### Q5 · 画质恢复后游戏内仍无「144 + 高清」

- 确认 `getprop ro.product.model` = `TB322FC`（模块是否生效）
- **清三角洲缓存/数据**促使游戏重拉适配表（这一步不能省）
- 冷启动游戏再看选项

### Q6 · heytap 系应用报「"XX"为定制应用，无法兼容当前设备」（小布 / 主题商店 / 音乐 / 视频 / 阅读 / 浏览器 / OPPO 商城 / 我的一加）

`brand` 不在 heytap `BrandEnvSdk` 白名单（OPPO / REALME / ONEPLUS，MD5 校验；反向确认过 MD5 常量）时，整套 ColorOS 应用拒绝服务。
解决：身份模块的 `brand/manufacturer` 保持 `OnePlus`（本仓库 v3.1 模块即定稿组合 `brand=OnePlus + model/device=TB322FC`），覆盖安装后**重启**（`Build.BRAND` 走 zygote 启动缓存，必须整机重启）。机制与排查详见 **Q8**。
通用原则：**改机型只动 model/device，品牌字段保持 OPPO 系（白名单内）不动**。

### Q7 · 插充电器 1~3 秒即停充（电量只降不升，重启/换充电器均无效）

**症状**：任意充电器（含高功率 PD 头）插上后系统短暂显示充电，1~3 秒后中止；`dumpsys battery` 的 `status` 长期为 4（未充电），电量持续下降。重启、换充电器/线、关闭全部 KSU 模块均无效。设置里的旁路充电、智能充电、充电保护都是关闭/未触发状态——**设置层看起来一切正常正是它难查的原因**。

**根因**：移植包对 OPLUS 充电通信节点的 bridge 覆盖不全，充电子系统持续报错并触发"暂停充电"保护，周期性把 `persist.sys.pause_charge` 置 1（实测约每 3.45 秒一次，跨重启持续）。日志中可直接看到这些缺失：

| 缺失节点 | 报错者 | 频率 |
|---|---|---|
| `/sys/class/oplus_mutual/cmd` | charger HAL（logcat tag `chg_exchange_mesg`） | 每秒级 |
| `/proc/charger/*` | power stats HAL | 每 ~20-30 秒 |
| `/proc/wireless/enable_tx` | 充电信息更新线程 | 每次刷新 |
| SOH 相关文件（`chg_exchange_soh_mesg`） | charger HAL | 每 ~45-90 秒 |

**诊断一行**：`adb shell getprop persist.sys.pause_charge` 返回 **1** 即命中（注意：设置层的 `settings get system bypass_charge_state` 会是 0——两者是不同机制，不冲突；这就是它骗过所有常规排查的原因）。

**修复**：刷入本仓库 [`modules/unpause_charge`](../modules/unpause_charge/)（watchdog 每秒把该属性清 0；可用模块的 **action 按钮立即启动，无需重启**）。运行日志：`/data/local/tmp/unpause_charge.log`。

**修复效果（实测）**：装入后 `persist.sys.pause_charge` 被稳定压在 0，充电恢复——实测电量 19% → 36% 约 1.5 小时（5V/3A 档约 10W，与协商上限一致），`status` 持续为 charging。注意：**系统仍会周期性重设该标志**（约每 3.45 秒一次，采样实测），由 watchdog 逐次清除，因此**模块需保持启用**；卸载模块 = 症状回归。等上游修复 bridge 后方可卸载。

**待上游修复**：bridge 扩展对 `oplus_mutual`、`/proc/charger` 等节点的转接后，此模块即可卸载。触发时刻的外因未完全明确（实测在刷机数小时后开始出现，之后跨重启持续），**任何使用该移植包的设备都可能遇到**。

### Q8 · 机型身份的多方冲突：定制应用白名单 / 品牌校验 / 游戏适配表

**背景**：本移植包原始身份是 `OPD2413`（一加平板 2 Pro）。为恢复三角洲「144 帧 + 高清」需要把 model 改成 `TB322FC`（见阶段 5）。围绕 `brand` / `model` 两个字段，存在多方消费者，约束互斥：

| 需求方 | 依赖字段 | 要求 | 冲突表现 |
|---|---|---|---|
| 三角洲 144+高清 | `ro.product.model`（实测**只认主域**） | `= TB322FC` | model 改回 OPD2413 即丢 144 |
| heytap `BrandEnvSdk` 系应用（小布 / 主题商店 / 音乐 / 视频 / 阅读 / 浏览器 / OPPO 商城 / 我的一加） | `Build.BRAND`（zygote 缓存）或实时 `ro.product.brand` | 见下方 MD5 白名单 | brand=Lenovo 时集体报「为定制应用，无法兼容当前设备」 |
| 微信 手机+平板双端（历史问题） | `brand` + `model` 组合（服务端校验） | 曾记录 `TB322FC` 须配 `Lenovo` | v1.1 时期出现过 `OnePlus-TB322FC` 不能双端；**2026-10-05 复测未复现**（见下） |

**BrandEnvSdk 校验机制（反编译实测，`com.heytap.msp.sdk.brand`）**：

```
// 判定核心（a.a.f()）:
String md5 = MD5(Build.BRAND.toUpperCase());
return md5.equalsIgnoreCase("67843bc0e7e7b09cc369beabf05e9d30")   // OPPO
    || md5.equalsIgnoreCase("60c89617499cd5202c71062b5f22087d")   // REALME
    || md5.equalsIgnoreCase("5836b6c1f251363d1ebc8e1c2e1fb9b9");  // ONEPLUS
```

- 品牌白名单只有三个：**OPPO / REALME / ONEPLUS**，其余一律弹「无法兼容当前设备」并 `return false`
- **两条读取路径**（决定修复方式，排障时别被误导）：
  - `Build.BRAND`——**zygote 启动时缓存**，应用进程 fork 后继承该固定值 → 必须**开机阶段**（post-fs-data）品牌就是白名单值；**运行时 resetprop 对读这条路径的应用无效**（音乐/视频/阅读/浏览器等实测）
  - 实时 `ro.product.brand`（UserCenter SDK 的 `PhoneProperty` / `SystemPropertyUtils.get`）→ **运行时 resetprop 即生效**（主题商店实测）
- 任何"改属性后重启应用进程"的运行时验证只能覆盖后者；前者必须整机重启才生效

**演进史（供参考，别重复踩）**：

| 方案 | brand+model | 微信双端 | ColorOS 系应用 | 三角洲 |
|---|---|---|---|---|
| 混合版 v1.1 | OnePlus + TB322FC | ✗（当时实测） | ✓ | ✓ |
| 品牌回退 v2.0/v2.1 | Lenovo + TB322FC | ✓ | ✗（当时只发现小布、用 LSPosed 单独修；其余七个后被发现集体被拒） | ✓ |
| 域分离 v3.0（TB322FC 藏 vendor/device 域） | OnePlus + OPD2413 | ✓ | ✓ | ✗ |
| **v3.1 定稿** | **OnePlus + TB322FC** | **✓（2026-10-05 复测）** | **✓（八应用实测全开）** | **✓** |

**v3.1 定稿方案（全绿，2026-10-05 实测）**：

1. 身份模块 [`modules/tb322fc_identity`](../modules/tb322fc_identity/) **v3.1**：`brand/manufacturer=OnePlus` + `model/device=TB322FC` + `ro.config.zui.devicetype=PAD` → ColorOS 八应用、微信双端、小布、三角洲 144+高清全部正常
2. 复测说明：v2.x 期间为解决微信双端把 brand 整体回退成 Lenovo，代价是全部 heytap 系应用被 BrandEnv 白名单拒绝（当时只发现了小布一个；主题商店、音乐、视频、阅读、浏览器、OPPO 商城、我的一加共七个是后来才被发现的）。改回 OnePlus 后 **微信双端未复现问题**——v1.1 时期「OnePlus-TB322FC 被拒」的归因在当前环境/微信版本下不再成立（无法确证当时成因，如实记录）
3. [`modules/y700-brandfix-lsposed`](../modules/y700-brandfix-lsposed/)（LSPosed 小布伪装）在 v3.1 下**冗余**（全局 brand 已是 OnePlus），保留仅供回退 v2.x 身份时使用

**本次定位的手法速查**：

- `adb shell getprop` 全量对照 + `dumpsys activity activities | grep topResumedActivity`（看前台是不是弹窗类 Activity，本次即 `BrandEnvActivity`）
- `uiautomator dump` + grep 文案（微信等加固应用会 dump 失败，需截图）
- 运行时 `resetprop` + `am force-stop` 快速二分定位（只对"实时读取"路径有效，见上文机制）
- APK 反编译（androguard，纯 Python 无需 JDK）：搜文案字符串 / 属性名字符串的引用，直接定位判定代码

**通用经验**：机型身份是**多消费者字段**——改机型前先确认每个消费者（游戏适配表、通信 App 的设备验证、厂商服务品牌校验）各自读哪几个字段、走哪条读取路径（缓存 or 实时），再设计"统一主身份 +（必要时）进程级隔离"的组合，比单点改字段更稳。

---

## 7. 验证方法论（通用，建议保留成脚本）

| 方法 | 用途 |
|---|---|
| `SHA256SUMS.txt` + 逐文件校验脚本 | 刷机包完整性（本案例 111/111 通过） |
| `qdl --dry-run` | XML 与镜像引用预验证（不碰设备） |
| `qdl read` + 分区读回 SHA256 对比 | 证明写入正确（排障第一课） |
| `avbtool info_image` + 手工哈希验证 | 定位 AVB 描述符与实际镜像不匹配 |
| `fastboot getvar all` | 槽位/锁/分区表全面状态快照 |
| `dumpsys display` | 显示模式表（分辨率/刷新率）诊断 |
| logfs / pstoredump 读取 | ABL 日志 / 内核崩溃日志（均可用 QDL read） |

---

## 8. 回滚到官方系统（保底方案）

1. 获取官方固件（ZUXOS 1.5.10.259 或 1.1.11.263 等完整包，约 9.5GB，含 QDL 线刷文件）
2. 9008 模式 → QDL 同流程刷写（rawprogram/patch XML 为官方包自带）
3. 官方包刷回后，官方签名链自洽，可直接启动；如需重新锁定 BL 用 `fastboot flashing lock`（会清数据）

**刷回官方后注意**：A/B 槽状态、vbmeta 均为官方版本；root 与模块全部消失。

---

## 9. 素材与工具官方渠道（不打包二进制）

| 内容 | 渠道 |
|---|---|
| ColorOS 16 移植包（含作者手册、QDL 工具、root 载荷） | 移植作者 Aptx5497 B 站视频简介的 123 网盘链接（BV1b5N36cEZa） |
| 刷机教程 / 工具（刷机匣、melf、免解锁 root 镜像） | UP 主"悲伤的压缩包"B 站视频（BV1NcTp64E6M）迅雷网盘 |
| 解锁工具箱 / 玩机资源 | 同 UP 主：腾讯文档《玩机更新资源教程》（公众号"悲伤压缩包"→玩机教程菜单获取）中的百度网盘合集 |
| MT 管理器 | 官网 mt.cc |
| adb/fastboot | Google platform-tools（developer.android.com） |
| avbtool + AOSP 测试密钥 | AOSP external/avb（或镜像仓库 android_external_avb）的 `avbtool.py` 与 `test/data/testkey_rsa4096.pem` |
| LTBox（EDL 工具，备用） | 作者发布页（GitHub：某贼/LTBox 相关仓库） |
| 官方固件 | mirrors.lolinet.com（lenowow/2025/Y700_4th_Gen/TB322FC_CN/）或联想 OTA 接口 |

---

## 10. 移植系统已知降级（作者文档明示）

- 系统 OTA 被屏蔽（组件级禁用，更新需重刷本项目包）
- 热点仅 2.4G
- 蓝牙编解码仅 AAC
- 色彩调节无效
- "查找"定位功能不可用

---

## 11. 免责声明

本文档仅供个人学习与技术研究。所有固件、工具、模块的版权归各自作者/厂商所有，请通过官方渠道获取并遵守其许可条款（多个工具明确标注"禁止倒卖"）。刷机有风险（变砖、数据丢失、保修失效），操作前务必备份数据并理解每一步作用。因使用本文档造成的任何后果由操作者自行承担。
