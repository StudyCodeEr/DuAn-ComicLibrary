import logging
import os
import traceback
from datetime import datetime

# 1. Tạo thư mục logs
if not os.path.exists("logs"):
    os.makedirs("logs")

# 2. Cấu hình file log
log_filename = f"logs/log_{datetime.now().strftime('%Y-%m-%d')}.txt"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8'),
        logging.StreamHandler() # Vẫn in ra màn hình console
    ]
)

def log_info(msg):
    logging.info(msg)

def log_error(msg):
    logging.error(msg)

def log_crash(e):
    """Hàm chuyên dụng để ghi lại lỗi sập app"""
    error_msg = f"CRASH REPORT:\n{traceback.format_exc()}"
    logging.critical(error_msg)
    # Có thể ghi thêm ra một file riêng cho dễ tìm
    with open("crash_log.txt", "w", encoding="utf-8") as f:
        f.write(error_msg)