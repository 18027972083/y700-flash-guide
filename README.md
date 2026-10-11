# y700-flash-guide

联想拯救者 Y700 四代（TB322FC）刷 ColorOS 16 移植版的**完整流程记录**与**自研验证脚本**。

> 本仓库不包含任何固件、工具或镜像二进制；所有素材的获取渠道见 [docs/flash-guide.md](docs/flash-guide.md) 第 8 节。
> 2026-10-11 新增：[docs/dual-flash-log-20261011.md](docs/dual-flash-log-20261011.md) —— 双机实录：二代 TB320FC 刷 ColorOS 16 + 四代 TB322FC 换澎湃 OS 4，含身份数据分区覆盖的发现与还原、人脸 hat_valid 排查实录、隐藏环境部署与 Hunter 过检调优。
> 2026-10-11 新增：[docs/165hz-unlock.md](docs/165hz-unlock.md) —— 澎湃 OS 4 把全局刷新率锁在 120Hz 的三层来源定位（Settings 键 → PowerKeeper persist 属性 → 开机默认锁），以及用"persist 属性变化事件"触发 MIUI 策略重评解锁 165Hz 的 KSU 模块、验证命令与回退方法。
> 2026-10-11 新增：[docs/per-app-device-identity.md](docs/per-app-device-identity.md) —— 微信双登失效根因（微信 `inTabletEnv` 是客户端硬编码机型白名单，不认 iPA2691）与"全局回原生 piano + Zygisk 按应用伪装（device_faker）"架构；附 PowerKeeper 每游戏帧率表（`mPrivGames`）造成的系统层 60fps 锁定位与解法。

## 背景

TB322FC 在 ZUXOS 1.5.10.259 之后常规解锁路径全部失效（unlock 分区被删、ABL 换生产密钥），唯一可行路线是 9008（EDL）线刷移植包 + 专用工具箱解锁。流程文档按"**推荐流程**（干净的操作序列，含从实测教训中前置的刷前验证）＋**排障节**（实测踩过的坑）"组织，其中最具通用价值的是：

- **刷前验证 + 预修 vbmeta**：移植包的 `vendor_boot.img` 与 `vbmeta.img` 不同步是已知构建缺陷，刷前用脚本查出并重签，可避免首启失败烧掉 RPMB 里的槽位计数。
- **"刷写成功但设备不启动"的定位方法论**（排障节 Q1）：分区读回比对 → ABL 日志（logfs）→ vbmeta 描述符逐条验证；以及用 AOSP 测试密钥重签 vbmeta 的完整修复命令。

## 仓库结构

```
y700-flash-guide/
├── docs/
│   ├── flash-guide.md        # 推荐流程 + 排障手册（脱敏版）：
│   │                         #   阶段 0-5 干净流程，实测踩坑集中在第 6 节 Q1-Q8
│   └── dual-flash-log-20261011.md
│                             # 双机实录：二代 ColorOS16（含 SN 覆盖还原）
│                             #   + 四代 澎湃OS4（root/隐藏环境/人脸排查）
├── scripts/                  # 自研脚本，纯标准库，无第三方依赖
│   ├── check_sha256.py       # 对照 SHA256SUMS.txt 全包校验（支持 zip 免解压、断点续算）
│   ├── verify_vbmeta.py      # 解析 AVB 描述符并逐条对实际镜像验哈希（排障核心）
│   └── dl_official.py        # 大文件分段并行下载（Range + 断点续传 + 尺寸校验）
└── modules/
    ├── tb322fc_identity/     # 混合机型身份 KSU 模块 v3.1（brand=OnePlus 过 heytap 品牌
    │                         #   白名单 + model/device=TB322FC 保三角洲 144；微信双端实测正常）
    ├── unpause_charge/       # 充电暂停修复 KSU 模块（已实测验证：watchdog 对抗移植包的
    │                         #   充电保护误触发，见排障手册 Q7；action 按钮可免重启启动）
    ├── y700-brandfix-lsposed/# LSPosed 小布品牌伪装模块（源码 + 构建脚本 + 预编译 APK；
    │                         #   v3.1 身份下已冗余，仅回退 v2.x 联想身份时使用，见 Q8）
    ├── y700_os4_max_fps/     # 165Hz 全局解锁 KSU 模块（开机自动触发 MIUI 智能省电策略
    │                         #   重评解除 120Hz 锁 + 钉死首选显示档；实测桌面/应用稳定 165，
    │                         #   详见 docs/165hz-unlock.md）
    └── device_faker_y700/    # Device_Faker 定制配置（仅三角洲→iQOO Pad Ultra；微信双登/
                              #   小米生态走原生 piano 身份），详见 docs/per-app-device-identity.md
```

## 脚本用法

```bash
# 1) 刷机包完整性校验（8.3GB zip 免解压，逐文件对内部 manifest）
python scripts/check_sha256.py --zip PACKAGE.zip --sums SHA256SUMS.txt

# 2) vbmeta 描述符 vs 实际镜像哈希验证（定位 AVB 不同步）
python scripts/verify_vbmeta.py --pkg /path/to/extracted_package

# 3) 官方救砖固件分段下载（断点续传）
python scripts/dl_official.py --url <firmware-url> --out TB322FC_official.7z
```

机型身份模块的原理与安装方式见文档阶段 5。
> 2026-10-11 双机实录补充：OS4 上身份策略已演进为"全局回原生 piano + device_faker 按应用伪装"（全局 iQOO 模块 `tb322fc_identity_os4` 已禁用）——微信平板双登、小米生态、三角洲 165 白名单三者兼得，见 [docs/per-app-device-identity.md](docs/per-app-device-identity.md)。系统刷新率的两层压制（全局 120 / 游戏内 60）的定位与解法见 [docs/165hz-unlock.md](docs/165hz-unlock.md) 与 per-app 文档的 PowerKeeper 节。

## 免责声明

本文档与脚本仅供**自有设备**的个人学习与技术研究。所有固件、工具、模块的版权归各自作者/厂商所有，请通过官方渠道获取并遵守其许可条款（多个工具明确标注"禁止倒卖"）。刷机有风险（变砖、数据丢失、保修失效），操作前务必备份数据并理解每一步的作用。因使用本仓库内容造成的任何后果由操作者自行承担。
