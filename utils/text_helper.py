import re

def clean_filename(name):
    """
    Loại bỏ các ký tự bị cấm trong tên file/folder của Windows
    """
    if not name:
        return "Unknown_Name"
        
    # Thêm chữ r ở trước chuỗi để sửa lỗi SyntaxWarning
    # Regex này lọc bỏ: \ / : * ? " < > |
    cleaned = re.sub(r'[\\/*?:"<>|]', "", name)
    
    # Xóa khoảng trắng thừa và trả về
    return cleaned.strip()