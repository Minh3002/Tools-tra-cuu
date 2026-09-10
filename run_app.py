import sys
import os
import subprocess
import time
from pyngrok import ngrok

def main():
    print("=" * 65)
    print("  🛡️ KHỞI CHẠY LỘC CỤ TRA CỨU BHYT TỰ ĐỘNG (LOCAL WEB APP)")
    print("=" * 65)

    # 1. Cài đặt/Kiểm tra Playwright Chromium
    print("\n[1/3] Kiểm tra môi trường Playwright Chromium...")
    try:
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
        print("  -> Trình duyệt Chromium đã sẵn sàng.")
    except Exception as e:
        print(f"  -> Cảnh báo cài đặt Chromium: {e}")

    # 2. Khởi chạy Streamlit Server ở Local Port 8501
    port = 8501
    print(f"\n[2/3] Khởi chạy Streamlit Web Server trên port {port}...")
    
    cmd = [sys.executable, "-m", "streamlit", "run", "app.py", "--server.port", str(port)]
    process = subprocess.Popen(cmd)

    # Đợi Streamlit khởi động trong 3 giây
    time.sleep(3)

    # 3. Tạo đường link Public bằng Ngrok
    print("\n[3/3] Tạo đường dẫn Public (Ngrok Tunnel)...")
    
    # Kiểm tra NGROK_AUTHTOKEN từ biến môi trường nếu có
    authtoken = os.environ.get("NGROK_AUTHTOKEN", "").strip()
    if authtoken:
        ngrok.set_auth_token(authtoken)

    public_url = ""
    try:
        tunnel = ngrok.connect(port, "http")
        public_url = tunnel.public_url
    except Exception as e:
        print(f"  -> Chưa thể tạo tự động tunnel Ngrok (Lỗi: {e})")
        print("  -> Gợi ý: Đăng ký tài khoản ngrok.com lấy Authtoken và chạy lệnh:")
        print("     .\\venv\\Scripts\\ngrok.exe config add-authtoken <YOUR_AUTHTOKEN>")

    print("\n" + "=" * 65)
    print("  🎉 HỆ THỐNG ĐÃ KHỞI CHẠY THÀNH CÔNG!")
    print("=" * 65)
    print(f"  🏠 Link Truy Cập Local   : http://localhost:{port}")
    if public_url:
        print(f"  🌐 Link Chia Sẻ Public  : {public_url}")
        print("     (Gửi đường link trên cho người khác cùng sử dụng)")
    print("=" * 65)
    print("\n⚠️  Lưu ý: Giữ cửa sổ terminal này luôn chạy khi muốn sử dụng.")
    print("    Nhấn Ctrl + C để dừng ứng dụng.\n")

    try:
        process.wait()
    except KeyboardInterrupt:
        print("\nStopping server...")
        ngrok.kill()
        process.terminate()

if __name__ == '__main__':
    main()
