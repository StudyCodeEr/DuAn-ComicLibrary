import re

def clean_filename(name):
    """
    Làm sạch chuỗi để dùng làm tên file/thư mục an toàn trên Windows/Linux.
    Loại bỏ các ký tự cấm: < > : " / \ | ? *
    """
    if not name: return "Unknown"
    
    # 1. Thay thế các ký tự cấm bằng dấu gạch ngang
    cleaned = re.sub(r'[<>:"/\\|?*]', '-', str(name))
    
    # 2. Loại bỏ các ký tự điều khiển (xuống dòng, tab...) gây lỗi WinError 123
    cleaned = re.sub(r'[\x00-\x1f]', '', cleaned)
    
    # 3. Xóa khoảng trắng thừa và dấu chấm ở cuối (Windows ghét dấu chấm cuối folder)
    cleaned = cleaned.strip().rstrip('.')
    
    # 4. Giới hạn độ dài tên file (Windows giới hạn đường dẫn 255 ký tự)
    # [UPDATED] User requested to remove the 100 char limit.
    # Note: Long paths might still cause issues on Windows if > 260 chars total.
    # if len(cleaned) > 100:
    #     cleaned = cleaned[:100]
        
    return cleaned