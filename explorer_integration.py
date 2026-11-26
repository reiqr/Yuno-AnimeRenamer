"""Current-user Explorer integration for the Windows desktop app."""
import os
from pathlib import Path
import subprocess
import sys


MENU_KEY = r'Software\Classes\Directory\shell\YunoAnimeRenamerPreview'
SHORTCUT_NAME = 'AnimeRenamer - 打开预览.lnk'


def _launch_command():
    executable = Path(sys.executable)
    if getattr(sys, 'frozen', False):
        return executable, ['--explorer']
    windowed = executable.with_name('pythonw.exe')
    script = Path(__file__).with_name('AnimeRenamer.pyw').resolve()
    return (windowed if windowed.is_file() else executable), [str(script), '--explorer']


def _shortcut_path():
    return Path(os.environ['APPDATA']) / 'Microsoft' / 'Windows' / 'SendTo' / SHORTCUT_NAME


def install():
    import winreg

    executable, args = _launch_command()
    shortcut = _shortcut_path()
    shortcut.parent.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, ANIME_SHORTCUT=str(shortcut), ANIME_EXE=str(executable),
               ANIME_ARGS=subprocess.list2cmdline(args))
    # Pass values as environment data so EXE paths are never evaluated as script.
    script = (
        "$ErrorActionPreference = 'Stop'; "
        "$link = (New-Object -ComObject WScript.Shell).CreateShortcut($env:ANIME_SHORTCUT); "
        "$link.TargetPath = $env:ANIME_EXE; $link.Arguments = $env:ANIME_ARGS; $link.Save()"
    )
    shell = Path(os.environ['SystemRoot']) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
    result = subprocess.run([str(shell), '-NoProfile', '-NonInteractive', '-Command', script],
                            env=env, creationflags=subprocess.CREATE_NO_WINDOW,
                            capture_output=True, timeout=15)
    if result.returncode or not shortcut.is_file():
        raise OSError('无法创建“发送到”快捷方式。')

    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, MENU_KEY) as key:
        winreg.SetValueEx(key, '', 0, winreg.REG_SZ, '用 AnimeRenamer 打开预览')
        winreg.SetValueEx(key, 'MultiSelectModel', 0, winreg.REG_SZ, 'Single')
        if getattr(sys, 'frozen', False):
            winreg.SetValueEx(key, 'Icon', 0, winreg.REG_SZ, f'"{executable}",0')
        with winreg.CreateKey(key, 'command') as command:
            prefix = subprocess.list2cmdline([str(executable), *args])
            winreg.SetValueEx(command, '', 0, winreg.REG_SZ, prefix + ' "%1"')


def remove():
    import winreg

    _shortcut_path().unlink(missing_ok=True)
    for path in (MENU_KEY + r'\command', MENU_KEY):
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, path)
        except FileNotFoundError:
            pass
