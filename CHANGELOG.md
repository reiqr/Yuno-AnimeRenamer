# 更新记录

## 0.3.0

- 增加按目录和季号的分组预览，可单独设置组名称、季度、起始集。
- 增加逐行纠正、特别篇编号纠正、批量跳过与恢复；视频纠正自动传递给明确关联的字幕。
- 增加复制整理模式，保留原文件和相对子目录结构。
- 修复字幕跨目录误配、小数集数截断、NCOP/NCED 编号丢失和音频参数误识别。
- 改名、复制、撤销使用预先持久化的操作记录，增加中断恢复与多窗口互斥。
- 检查 Windows 非法文件名、模板错误、预览后文件变化和外部同名文件。
- 扫描与执行改为后台线程，设置变化后要求重新预览。
- 修正中文 BAT 文件名，提供使用 UTF-8 文件名标记的发布包生成脚本。
- 增加文件操作故障注入、崩溃恢复、识别和 Tk 界面流程测试。

## 0.2.1

导入用户提供的版本，作为此次开发的 Git 基线。此前版本目录及压缩包保持原样。

## Future Diary UI latest bundle (2026-09-19)
- Includes Preview 16 UI, Preview 13 banner composition, Preview 15 Windows icon/build settings.
- Includes all runtime theme assets required by AnimeRenamer.pyw.
- Uses ASCII helper script names (`run_app.bat`, `build_exe.bat`) to reduce ZIP/Windows filename encoding issues.


### Future Diary UI Preview 17
- Enable Windows per-monitor DPI awareness before Tk initialization to prevent blurry bitmap-scaled UI.
- Reduce the initial physical window size without reducing asset/UI rendering resolution.
- Rebuild the sidebar portrait with a full-head safe crop and retain a 3x high-resolution derivative.
- Distinguish Latin/Chinese/Japanese/terminal typography using installed Windows font families.
- Clean EXE builds and output `AnimeRenamer_FutureDiary.exe` with the multi-size ICO embedded.
- Add `refresh_icon_cache.bat` for stale Explorer icon caches.
