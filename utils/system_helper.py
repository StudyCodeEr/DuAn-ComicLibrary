import os
import sys

def get_app_dir():
    """
    Trả về thư mục gốc của ứng dụng.
    - Nếu chạy qua script Python (.py), trả về thư mục chứa main.py
    - Nếu chạy qua file đóng gói (.exe) bằng PyInstaller, trả về thư mục chứa file .exe 
      (Tránh lỗi lưu data vào thư mục tạm _internal khi dùng --onedir)
    """
    if getattr(sys, 'frozen', False):
        # Chạy bằng PyInstaller (đã đóng gói thành exe)
        return os.path.dirname(sys.executable)
    else:
        # Chạy bằng source code python trực tiếp (.py)
        # Vì file này ở utils/system_helper.py nên phải lùi 1 thư mục về root
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
