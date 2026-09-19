# AnimeRenamer 0.3.0

Windows 离线番剧、字幕与轻小说文件整理工具。先扫描并检查预览，再执行原地重命名或复制整理。无需账号、API 密钥或网络服务。

## 启动

- 已打包版本：双击 `AnimeRenamer_FutureDiary_v<产品版本>.<构建号>.exe`，例如 `AnimeRenamer_FutureDiary_v0.3.0.57.exe`，无需安装 Python。
- 源码版本：安装 Python 3.10+，双击 `run_app.bat`，或运行 `python AnimeRenamer.pyw`。程序运行只使用 Python 标准库。
- 兼容入口：旧中文名脚本 `运行 AnimeRenamer.bat` 与 `生成EXE.bat` 仍然保留可用；新用户建议使用英文名脚本。若旧构建脚本与当前说明不一致，以 `build_exe.bat` 为准。
- 源码与后续 Git 历史固定保存在 `AnimeRenamer` 目录；旁边的旧版本目录和 ZIP 可作为原始交付备份保留。

## 仓库目录

- `AnimeRenamer.pyw`：程序入口。
- `renamer_core.py` / `file_operations.py`：番剧识别与文件操作核心。
- `ui/`：主界面、主题、弹窗、轻小说模式等 UI 模块。
- `assets/`：程序实际使用的图片和图标素材。
- `tools/`：发布打包、Windows 版本信息生成、图标缓存维护工具。
- `tests/`：回归测试。
- `benchmarks/`：性能基准。
- `history/`：历史 Preview 资料。

根目录只保留用户入口、核心模块和项目级文档，避免后续功能继续堆散文件。

## 基本使用流程

1. 选择输入文件夹，可选“子目录”。
2. 在右上角选择内容类型：`番剧` 或 `轻小说`。
3. 设置作品名、命名规则及需要的选项，点击“扫描文件”。
4. 在“未来记录 / RENAME PREVIEW”中检查原名、目标名、识别结果和状态。
5. 必要时使用“分组”“纠正”“跳过”“清除”进行人工调整。
6. 改动输入路径、命名设置或内容类型后，需要重新扫描，`改写未来` 才会重新启用。
7. 确认预览无冲突后，点击“改写未来”执行。

单击一行会显示完整源路径、目标路径及识别依据。规则评分只用于提示匹配强弱，不是统计准确率。

## 番剧模式

### 分组和排序

- 文件按原目录及明确的 `SxxEyy` 季号进行分组。
- 选择一个组后点击“分组”，可覆盖该组的作品名、季度或排序起始集；留空时使用默认值。
- “排序编号”会对组内正片按排序重新编号，不是只处理无法识别的文件。
- 特别篇、小数集数、手动纠正和跳过的文件不消耗自动编号。
- 手动编号与自动编号重叠时会显示冲突，不会覆盖已有目标。
- 字幕只在同目录内关联视频；优先使用精确文件名前缀，再使用唯一原集数。存在多个候选时等待人工确认，不跨目录猜测。
- 季度只有在模板包含 `{season}` 时才出现在文件名中；同目录多季建议使用“番剧名 S01E01”一类模板。

### 支持的命名示例

- `01.mkv`、`002.ass`、`04.chs.ass`
- `作品 S02E08.mkv`、`作品 EP12.mkv`、`作品 第24话.mkv`
- `作品 [03] x265.mkv`、`作品 - 03 h264.mkv`
- `未来日记01.mkv`、`作品 - 12.5.mkv`
- `NCOP01`、`NCED02`、`SP01`、`OVA`、`OAD`、`PV`

编码、分辨率、帧率、音频声道等常见技术参数会在通用集数识别前过滤。纯数字文件优先视为集数；含糊的 `5.1` 等可能是音轨参数，可在预览中人工纠正。多集文件（例如 `01-02`）需要人工确认。

番剧模板字段：`{title}`、`{season:02d}`、`{episode:02d}`。小数集数保留小数部分，例如 `3.5` 在两位格式中输出 `03.5`。特别篇使用独立格式，不套用正片季集模板。

视频：MKV、MP4、AVI、MOV、WMV、FLV、M4V、TS、M2TS、WEBM。  
字幕：ASS、SSA、SRT、VTT、SUP、SUB、IDX；保留常见中英日语言标记。

不会扫描符号链接文件，也不会跟随目录链接。

## 轻小说模式

轻小说模式与番剧集数解析分离，只按文件名识别卷号和系列信息，不读取 EPUB / PDF 等文件正文。

支持文件类型：

- EPUB
- MOBI
- AZW3
- PDF
- TXT
- CBZ

可识别的卷号形式包括：

- `第3卷`
- `Vol.03`
- `V03`
- `EP03`
- `[03]`
- 独立数字卷号

支持保留卷标题，以及 `上 / 中 / 下`、`上册 / 下册` 等分册信息。对混合书库可根据已经识别出的系列名前缀进行分组；无法可靠判断的条目会保留为待确认状态。

轻小说可用模板包括：

- `书名 - 第01卷`
- `书名 01`
- `书名 Vol.01`
- `书名 - 01 - 卷标题`
- `书名 - 第01卷 上 卷标题`
- 自定义模板

轻小说模板字段：`{title}`、`{volume}`、`{volume_title}`、`{part}`。

双击轻小说条目可人工纠正卷号；“排序编号”也可用于按组重新分配卷号。

## 两种操作方式

### 原地重命名

只修改文件名，不修改文件内容、扩展名类型或目录位置。

### 复制整理（保留原文件）

复制到输入目录以外的目标目录，并保留相对子目录结构。支持跨盘，目标同名文件不会被覆盖。

复制任务在后台线程运行，并显示：

- 总体复制百分比；
- 当前文件与文件序号；
- 已复制 / 总字节数；
- 实时复制速度；
- “取消复制”按钮。

取消时会安全停止复制并清理本次创建的临时文件和副本，原文件保持不变。若清理未能完整完成，会保留恢复记录，并提示使用“恢复中断操作”。

不提供硬链接、自动下载后整理或在线元数据查询。

## 撤销和恢复

- 执行前先持久化整个操作计划；恢复记录写入失败时不改动媒体文件。
- 使用两阶段临时名处理链式改名和交换名称，目标出现外部同名文件时停止。
- 普通异常时尝试恢复原名；进程中断或恢复被文件占用阻止时，可使用“恢复中断操作”继续恢复。存在未完成操作时不允许开启新批次。
- 多个窗口共享操作锁，避免同时改名、复制、撤销或恢复。
- “撤销上次操作”只针对最近一次成功批次。改名会恢复原名；复制会删除本工具生成的副本，原文件保留。
- 操作前后检查文件标识、大小和修改时间；文件被替换或普通编辑后停止自动恢复 / 撤销。该检查不是内容哈希校验。
- 恢复记录在 `%LOCALAPPDATA%\AnimeRenamer\pending_v2.json`，上次成功记录为 `rename_history_v2.json`。0.2.x 的旧记录不自动导入。
- 当提示“无法确认归属”时，应保留现场和 JSON 恢复记录，先处理文件占用或外部变更。

## 打包与测试

打包依赖 **PyInstaller**，来源为 Python Package Index（PyPI）。安装它会修改所选 Python 环境，并可能同时安装传递依赖。`build_exe.bat` **不会自动安装或升级任何 Python 包**。

确认接受该依赖后，可手动安装：

```powershell
python -m pip install pyinstaller
```

随后双击 `build_exe.bat`。EXE 文件名会直接包含完整构建版本，例如：

```text
dist\AnimeRenamer_FutureDiary_v0.3.0.57.exe
```

构建前会由 `tools/generate_version_info.py` 自动生成 Windows 版本信息：

- `ProductVersion` 直接读取 `renamer_core.VERSION`，仍是项目发布版本，例如 `0.3.0`；
- `FileVersion` 追加自动构建号，例如 `0.3.0.57`；
- EXE 文件名使用与 `FileVersion` 相同的完整版本号；
- GitHub Actions 使用 `github.run_number` 作为构建号；
- 本地 `build_exe.bat` 使用当前 Git 提交数量作为构建号；若源码不在 Git 仓库中则使用 `0`。

因此每次 CI 新构建都能直接从文件名和 EXE 属性中区分，同时产品版本仍只维护一个来源。仓库中的旧 `tools/windows_version_info.txt` 仅保留为历史兼容参考，正式构建和发布包不再依赖它。

构建脚本会使用 `assets\app_icon.ico` 作为 Windows EXE 图标，并把 `assets/` 一并打包。脚本只清理 `build/`、生成的 `.spec` 和**当前同版本目标 EXE**，不会清空整个 `dist/` 目录，也不会删除其他旧版本 EXE 或发布 ZIP。

运行测试：

```powershell
python -m unittest discover -s tests -v
```

使用 UTF-8 文件名标记的 ZIP 发布源码：

```powershell
python tools/package_release.py
```

发布包输出到 `dist`。如果当前版本对应的 EXE 已构建，发布 ZIP 只收录这一份版本匹配的 EXE；旧的无版本号 EXE 和其他历史 EXE 不会混入。ZIP 不包含 Git、缓存、真实媒体文件或字体文件。

## Future Diary UI

当前 UI 已进入 Preview 19 系列，并在 Preview 19.2 完成一轮显示收尾。主要资源包括：

- `assets/yuno_sidebar.png`：左侧角色图；
- `assets/yuno_sidebar_hd.png`：高分辨率派生源；
- `assets/yuno_banner_dark.png` / `assets/yuno_banner_dark_wide.png`：等待、待刷新、检查和冲突等暗态横幅；
- `assets/yuno_banner_bright.png` / `assets/yuno_banner_bright_wide.png`：安全预览和完成状态亮态横幅；
- `assets/yuno_banner.png` / `assets/yuno_banner_wide.png`：兼容横幅素材；
- `assets/empty_phone.png`：空预览状态手机图；
- `assets/app_icon.png`：运行时窗口图标；
- `assets/app_icon.ico`：Windows EXE / 资源管理器图标。

界面状态与横幅联动：

- `WAITING`、`NEEDS REFRESH`、检查 / 冲突类状态：暗态；
- `PREVIEW SAFE`、完成状态：亮态；
- `PROCESSING`：处理中进行明暗状态提示。

当前布局还包含内容类型选择器、复制实时进度与安全取消、紧凑右侧工作区，以及避免空预览说明文字被裁切的修正。

## Future Diary UI 当前构建说明

- 在导入 Tkinter、创建首个窗口之前启用 Windows Per-Monitor DPI 感知，避免系统对整个 Tk 窗口做位图拉伸造成模糊。
- UI 字体只从系统已安装字体中选择；中文优先 `Microsoft YaHei UI`，拉丁标题优先 `Bahnschrift / Segoe UI`，日文优先 `Yu Gothic UI`，等宽标签优先 `Cascadia Mono / Consolas`。显式字号保持在紧凑可读区间，不捆绑字体文件。
- 发布脚本会拒绝将 `.ttf/.otf/.ttc/.woff/.woff2` 等字体文件打入发布包，避免字体授权与体积问题。
- 侧边栏角色图以安全的头部与发丝留白显示，高分辨率派生源保留在 `assets/yuno_sidebar_hd.png`；运行时使用原生 Tk 图像资源，不对整个窗口做低分辨率截图式缩放。
- 打包 EXE 使用 `AnimeRenamer_FutureDiary_v<产品版本>.<构建号>.exe`，文件名、Windows `FileVersion` 和发布包选取保持一致。
- `build_exe.bat` 每次构建前只清理 `build/`、生成的 `.spec` 和当前同版本目标 EXE，不删除 `dist/` 中其他文件，也不会自动安装或升级依赖。
- 若资源管理器仍显示旧图标或旧版本信息，可运行一次 `tools/refresh_icon_cache.bat` 后重新打开文件夹。
