# AnimeRenamer v0.1.0

一个 Windows 本地番剧批量重命名原型。

## 已实现

- 扫描常见视频：MKV / MP4 / AVI / MOV / WMV / FLV / M4V / TS / M2TS / WEBM
- 扫描常见字幕：ASS / SSA / SRT / VTT / SUP / SUB
- 自动识别常见集数写法：
  - `S01E03`
  - `E03` / `EP03` / `Episode 03`
  - `第03集` / `第3话`
  - `[03]`
  - 常见的 ` - 03 `、`.03.` 等
- 尽量避开 `1080p / 265 / 10bit / fps` 等技术参数
- 识别 `OVA / OAD / SP / NCOP / NCED / PV`
- 多种统一命名模板
- 自定义模板
- 字幕联动重命名
- 保留 `chs / cht / zh-Hans / zh-Hant / eng / jpn` 等语言标签
- 可选递归扫描子文件夹
- 可选按文件排序强制编号
- 重命名前预览
- 检查目标文件冲突
- 两阶段安全改名，避免 `01 -> 02`、`02 -> 03` 互相覆盖
- 撤销上一次重命名

## 直接运行

本版本使用 Python 标准库 Tkinter，不需要安装额外 Python 包。

如果电脑已安装 Python 3.10+：

1. 双击 `运行 AnimeRenamer.bat`
2. 或直接运行 `AnimeRenamer.pyw`

## 打包 Windows EXE

双击 `生成EXE.bat`。

脚本会：

1. 安装/升级 PyInstaller
2. 生成单文件 `dist\\AnimeRenamer.exe`

> 打包 EXE 必须在 Windows 上执行。当前交付包提供源码和自动打包脚本；Linux 环境不能可靠生成原生 Windows EXE。

## 自定义模板

可使用：

- `{title}`：番剧名
- `{season:02d}`：两位季度
- `{episode:02d}`：两位集数

例如：

```text
{title} - {episode:02d}
```

输出：

```text
未来日记 - 01.mkv
```

或者：

```text
{title} S{season:02d}E{episode:02d}
```

输出：

```text
未来日记 S01E01.mkv
```

## 建议

第一次使用时，建议先复制 2～3 集到测试文件夹里验证识别结果。
尤其是发布组命名非常特殊、BDMV 拆分、OVA/SP 混排、双语字幕复杂命名时，先看“预览”再执行。
