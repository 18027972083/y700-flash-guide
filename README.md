# y700-flash-guide

联想拯救者 Y700 四代（TB322FC）刷 ColorOS 16 移植版的**完整流程记录**与**自研验证脚本**。

> 本仓库不包含任何固件、工具或镜像二进制；所有素材的获取渠道见 [docs/flash-guide.md](docs/flash-guide.md) 第 8 节。

## 背景

TB322FC 在 ZUXOS 1.5.10.259 之后常规解锁路径全部失效（unlock 分区被删、ABL 换生产密钥），唯一可行路线是 9008（EDL）线刷移植包 + 专用工具箱解锁。流程文档按"**推荐流程**（干净的操作序列，含从实测教训中前置的刷前验证）＋**排障节**（实测踩过的坑）"组织，其中最具通用价值的是：

- **刷前验证 + 预修 vbmeta**：移植包的 `vendor_boot.img` 与 `vbmeta.img` 不同步是已知构建缺陷，刷前用脚本查出并重签，可避免首启失败烧掉 RPMB 里的槽位计数。
- **"刷写成功但设备不启动"的定位方法论**（排障节 Q1）：分区读回比对 → ABL 日志（logfs）→ vbmeta 描述符逐条验证；以及用 AOSP 测试密钥重签 vbmeta 的完整修复命令。

## 仓库结构

```
y700-flash-guide/
├── docs/
│   └── flash-guide.md        # 推荐流程 + 排障手册（脱敏版）：
│                             #   阶段 0-5 干净流程，实测踩坑集中在第 6 节 Q1-Q5
├── scripts/                  # 自研脚本，纯标准库，无第三方依赖
│   ├── check_sha256.py       # 对照 SHA256SUMS.txt 全包校验（支持 zip 免解压、断点续算）
│   ├── verify_vbmeta.py      # 解析 AVB 描述符并逐条对实际镜像验哈希（排障核心）
│   └── dl_official.py        # 大文件分段并行下载（Range + 断点续传 + 尺寸校验）
└── modules/
    └── tb322fc_identity/     # 恢复真实机型身份的最小 KSU 模块（改 ro.product.*，可逆）
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

## 免责声明

本文档与脚本仅供**自有设备**的个人学习与技术研究。所有固件、工具、模块的版权归各自作者/厂商所有，请通过官方渠道获取并遵守其许可条款（多个工具明确标注"禁止倒卖"）。刷机有风险（变砖、数据丢失、保修失效），操作前务必备份数据并理解每一步的作用。因使用本仓库内容造成的任何后果由操作者自行承担。
