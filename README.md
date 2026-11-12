# OpenCV Image Editor

Ứng dụng desktop chỉnh sửa ảnh cơ bản bằng Python, Tkinter, OpenCV và NumPy. Giao diện dark-mode lấy cảm hứng từ Pixelroom: thanh thương hiệu/nav, breadcrumb dự án, công cụ bên trái, vùng so sánh ảnh ở giữa và bảng thiết lập ngữ cảnh bên phải.

## Cài đặt

Khuyến nghị tạo môi trường ảo rồi cài thư viện:

```powershell
py -m venv venv
.\venv\Scripts\Activate.ps1
pip install opencv-python numpy pillow
```

Hoặc:

```powershell
pip install -r requirements.txt
```

## Chạy

```powershell
python src/main.py
```

> Nếu Windows báo `Can't find a usable init.tcl`, bản cài Python đang thiếu thành phần **Tcl/Tk and IDLE**. Chạy lại Python Installer, chọn **Modify**, bật thành phần này, sau đó tạo lại môi trường `.venv` và cài lại `requirements.txt`.

## Chức năng

- Mở/lưu JPG, PNG; đọc và ghi được cả đường dẫn chứa tiếng Việt.
- Hiển thị song song ảnh gốc và ảnh đang chỉnh sửa, hoặc chỉ xem kết quả; BGR được chuyển sang RGB đúng khi đưa lên Tkinter.
- Ảnh xám, Canny (2 ngưỡng + preset), âm bản, Logarit (điều chỉnh hệ số c) và Gamma.
- Cắt ảnh bằng tọa độ trong bảng bên phải hoặc chọn vùng trực tiếp trên ảnh kết quả.
- Resize bằng cách nhập kích thước (có tùy chọn giữ tỷ lệ) hoặc kéo tay nắm xanh ở góc dưới-phải ảnh.
- Lịch sử thao tác, thông tin ảnh, trạng thái xử lý, nút mở/lưu/đặt lại luôn sẵn có.

Mọi thao tác xử lý nằm ở `src/core/processor.py` để dễ kiểm thử hoặc mở rộng, còn giao diện được tách vào `src/ui/`.
