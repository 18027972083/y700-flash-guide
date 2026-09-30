# y700-brandfix-lsposed

LSPosed 模块：**只在小布 / ColorOS / AIUnit 系进程内**把 `Build.BRAND`、`Build.MANUFACTURER` 伪装为 `OnePlus`——解决机型身份改动后**小布助手报「无法兼容当前设备」**的问题（详见排障手册 **Q8**）。

## 为什么需要它（Q8 的三方冲突）

| 需求方 | 依赖字段 | 要求 |
|---|---|---|
| 三角洲「144+高清」 | `ro.product.model` | 必须是 `TB322FC` |
| 微信「手机+平板双端」 | `brand` + `model` 组合自洽 | `TB322FC` 必须搭配 `Lenovo` |
| 小布助手 | `brand` | 必须是 OPPO 系（`OnePlus`） |

同一个 `ro.product.brand` 字段前两者要 `Lenovo`、小布要 `OnePlus`——无法共存。本模块把"给小布看的那份身份"**隔离到小布进程内部**，从而与主身份（`identity v2.0` 的 `Lenovo-TB322FC`）并存：

- 主身份 `modules/tb322fc_identity` v2.0 → 微信 ✓ 三角洲 ✓
- 本模块（作用域=小布系）→ 小布 ✓
- 两者互不干扰，检测环境实测无副作用（Momo / Ruru / MemoryDetector 全绿）

## 安装

1. 安装 `y700-brandfix.apk`（含预编译版，也可自行构建）
2. LSPosed 管理器 → 模块 → 启用 **Y700 BrandFix (XiaoBu)**
3. **作用域**：模块已声明推荐作用域（`com.heytap.speechassist`、`com.heytap.cloud`、`com.oplus.aiunit`、`com.coloros.assistantscreen`），采纳即可（状态若未到生效状态则重启设备）
4. 重启后验证：小布能正常打开；微信双端与三角洲 144+高清不受影响

## 构建

```bash
bash build.sh   # 可用 JDK_HOME / BUILD_TOOLS / ANDROID_JAR 环境变量覆盖工具路径
```

构建链：`javac`（编译期用 `stub/` 下的 Xposed API 存根，**不进 APK**）→ `d8` → `aapt2` → `zipalign` → `apksigner`（首次运行自动生成自签名 keystore）。

## 技术细节

- 入口类 `com.zcode.y700.brandfix.Hook`（`assets/xposed_init` 声明），实现传统 Xposed API（`xposedminversion=82`，LSPosed 1.9.x 兼容）
- 通过 `XposedHelpers.setStaticObjectField(Build.class, "BRAND"|"MANUFACTURER", "OnePlus")` 在目标进程内改写静态字段（`Build.BRAND` 由 zygote 预加载，改静态字段是进程内生效的正确途径）
- 代码层按进程名前缀过滤（`com.heytap.` / `com.coloros.` / `com.oplus.` / `com.aiunit.`）；**最终作用范围由 LSPosed 作用域控制**——保持只勾小布系 = 最小暴露面
- 作用域外进程感知不到 LSPosed，模块对检测软件无新增可见面（实测）

## 许可证

与仓库一致（仅限自有设备的个人研究与使用）。
