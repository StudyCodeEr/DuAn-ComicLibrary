import sys
import os

def is_windows():
    return sys.platform.startswith('win')

def toggle_startup(enable: bool, app_name="MangaLocalLibrary"):
    if not is_windows():
        return False
        
    try:
        import winreg
        key = winreg.HKEY_CURRENT_USER
        sub_key = r"Software\Microsoft\Windows\CurrentVersion\Run"
        
        with winreg.OpenKey(key, sub_key, 0, winreg.KEY_ALL_ACCESS) as reg_key:
            if enable:
                # Đăng ký với đường dẫn file chạy hiện tại (bản thân file exe)
                exe_path = sys.executable
                command = f'"{exe_path}" --hidden'
                winreg.SetValueEx(reg_key, app_name, 0, winreg.REG_SZ, command)
            else:
                try:
                    winreg.DeleteValue(reg_key, app_name)
                except FileNotFoundError:
                    pass
        return True
    except Exception as e:
        print(f"Lỗi đăng ký Registry: {e}")
        return False

def is_startup_enabled(app_name="MangaLocalLibrary"):
    if not is_windows():
        return False
        
    try:
        import winreg
        key = winreg.HKEY_CURRENT_USER
        sub_key = r"Software\Microsoft\Windows\CurrentVersion\Run"
        
        with winreg.OpenKey(key, sub_key, 0, winreg.KEY_READ) as reg_key:
            try:
                value, _ = winreg.QueryValueEx(reg_key, app_name)
                return sys.executable in value
            except FileNotFoundError:
                return False
    except Exception:
        return False
