import os
from PIL import Image
from io import BytesIO

def save_image(image_data, save_folder, file_name, target_format="PNG"):
    """
    Lưu ảnh với tính năng Smart Convert.
    - target_format: "PNG", "JPEG", "WEBP"
    """
    try:
        # 1. Tạo thư mục
        if not os.path.exists(save_folder):
            os.makedirs(save_folder)

        # 2. Đọc ảnh từ RAM để kiểm tra định dạng gốc
        image = Image.open(BytesIO(image_data))
        source_format = image.format.upper() if image.format else "UNKNOWN"

        # Chuẩn hóa target_format (để so sánh chính xác)
        target_format = target_format.upper()
        if target_format == "JPG": target_format = "JPEG"

        # --- LOGIC SMART CHECK ---
        # Nếu định dạng tải về TRÙNG KHỚP với định dạng muốn lưu
        # => Lưu thẳng dữ liệu thô (Raw bytes) -> Nhanh nhất, chất lượng gốc 100%
        if source_format == target_format:
            # Xác định đuôi file
            ext = target_format.lower().replace("jpeg", "jpg")
            save_path = os.path.join(save_folder, f"{file_name}.{ext}")
            
            with open(save_path, 'wb') as f:
                f.write(image_data)
            return True, save_path

        # --- LOGIC CONVERT (Nếu khác định dạng) ---
        # Xác định đuôi file và mode
        save_ext = target_format.lower().replace("jpeg", "jpg")
        save_path = os.path.join(save_folder, f"{file_name}.{save_ext}")

        # Xử lý transparency (trong suốt)
        # Nếu lưu JPEG (không hỗ trợ trong suốt) thì phải xóa nền alpha
        if target_format == "JPEG" and image.mode in ("RGBA", "P"):
            image = image.convert("RGB")
        
        # Cấu hình tham số lưu
        save_params = {}
        if target_format == "JPEG":
            save_params["quality"] = 90
        elif target_format == "PNG":
            save_params["compress_level"] = 6
        elif target_format == "WEBP":
            save_params["quality"] = 90
            save_params["method"] = 6

        image.save(save_path, target_format, **save_params)
        return True, save_path
        
    except Exception as e:
        print(f"❌ Lỗi lưu ảnh {file_name}: {e}")
        return False, str(e)