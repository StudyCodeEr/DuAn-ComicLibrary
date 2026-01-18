# 📚 Manga Local Library (PC Server)

Ứng dụng quản lý, tải xuống và đọc truyện tranh Offline trên PC. Tích hợp Server để đồng bộ và đọc trực tiếp trên điện thoại Android qua mạng LAN.

## 🚀 Tính năng chính

* **Tải truyện tự động:** Sử dụng Selenium để tải truyện từ các trang web (vượt qua Cloudflare/Anti-bot).
* **Quản lý thư viện:** Giao diện lưới (Grid), tìm kiếm, lọc theo Tag.
* **Đọc truyện:** Tích hợp trình đọc truyện mượt mà, hỗ trợ Zoom, Dark Mode.
* **PC Server:**
    * Tự động phát hiện IP qua UDP (không cần nhập IP thủ công trên điện thoại).
    * Đồng bộ danh sách truyện sang App Android.
    * Nhận lệnh tải truyện từ điện thoại gửi về PC.
    * Cho phép điện thoại đọc truyện (xem ảnh) trực tiếp từ ổ cứng PC.

## 🛠 Yêu cầu hệ thống

* **OS:** Windows 10/11.
* **Python:** 3.8 trở lên.
* **Trình duyệt:** Google Chrome (để Selenium hoạt động).

## 📦 Hướng dẫn cài đặt (Dành cho Developer)

### Bước 1: Cài đặt môi trường ảo
Mở **PowerShell** tại thư mục dự án và chạy lệnh:

```powershell
# Xóa môi trường cũ (nếu có)
Remove-Item -Path ".venv" -Recurse -Force -ErrorAction SilentlyContinue

# Tạo môi trường mới
python -m venv .venv

# Kích hoạt môi trường
.\.venv\Scripts\Activate
```
### Bước 2: Cài đặt thư viện
Sau khi kích hoạt .venv, chạy lệnh sau để tải các gói cần thiết:
```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```
### Bước 3: Chạy ứng dụng
Dùng lệnh:
```powershell
python main.py
```
Hoặc ấn vào nút **Run** trong vscode
