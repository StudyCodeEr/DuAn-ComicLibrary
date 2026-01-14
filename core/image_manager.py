import os
from PIL import Image
import io

def save_image(image_data, save_path, file_name, format_type):
    """
    Lưu ảnh từ dữ liệu bytes.
    :param image_data: Dữ liệu ảnh (bytes)
    :param save_path: Thư mục lưu
    :param file_name: Tên file (không đuôi)
    :param format_type: 'PNG', 'JPEG', 'WEBP', 'ORIGINAL'
    """
    if not os.path.exists(save_path):
        os.makedirs(save_path)

    try:
        # Nếu chọn giữ nguyên gốc
        if format_type == "ORIGINAL":
            # Mặc định lưu jpg nếu không đoán được, nhưng thực tế nên check header
            # Ở đây để đơn giản ta lưu .jpg, hoặc có thể check magic number
            final_path = os.path.join(save_path, f"{file_name}.jpg")
            with open(final_path, "wb") as f:
                f.write(image_data)
            return

        # Dùng Pillow để xử lý/convert
        image = Image.open(io.BytesIO(image_data))
        
        # Chuyển sang RGB nếu lưu JPEG (vì JPEG không hỗ trợ trong suốt)
        if format_type == "JPEG" and image.mode in ("RGBA", "P"):
            image = image.convert("RGB")

        # Xác định đuôi file
        ext = format_type.lower()
        if format_type == "JPEG": ext = "jpg"
        
        final_path = os.path.join(save_path, f"{file_name}.{ext}")
        
        # Lưu ảnh với chất lượng cao
        if format_type == "JPEG":
            image.save(final_path, format="JPEG", quality=90)
        elif format_type == "WEBP":
            image.save(final_path, format="WEBP", quality=90)
        else:
            image.save(final_path, format="PNG")
            
    except Exception as e:
        print(f"Lỗi save_image: {e}")
        # Fallback: Nếu lỗi convert thì cứ lưu thô (dump bytes)
        with open(os.path.join(save_path, f"{file_name}_error.bin"), "wb") as f:
            f.write(image_data)