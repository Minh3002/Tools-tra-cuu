import os
import sys
import time
import pandas as pd
from datetime import datetime
from playwright.sync_api import sync_playwright
try:
    from playwright_stealth.stealth import Stealth
    HAS_STEALTH = True
except Exception:
    HAS_STEALTH = False

import ddddocr

class BHYTScraper:
    def __init__(self, headless=True, max_retries=3):
        self.headless = headless
        self.max_retries = max_retries
        self.ocr = ddddocr.DdddOcr(show_ad=False)
        self.url = "https://baohiemxahoi.gov.vn/tracuu/Pages/tra-cuu-thoi-han-su-dung-the-bhyt.aspx"

    def _launch_browser(self, p):
        """1. CẤU HÌNH BROWSER LAUNCH: Bypass Anti-bot trên Cloud Linux với Chrome User-Agent, Viewport 1920x1080 & xóa navigator.webdriver."""
        args = [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-infobars",
            "--window-size=1920,1080",
            "--ignore-certificate-errors"
        ]
        
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        
        try:
            browser = p.chromium.launch(headless=self.headless, channel="chrome", args=args)
        except Exception:
            browser = p.chromium.launch(headless=self.headless, args=args)
            
        context = browser.new_context(
            user_agent=user_agent,
            viewport={"width": 1920, "height": 1080},
            locale="vi-VN",
            timezone_id="Asia/Ho_Chi_Minh",
            extra_http_headers={
                "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
                "Sec-Ch-Ua": '"Chromium";v="128", "Not;A=Brand";v="24", "Google Chrome";v="128"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"Windows"'
            }
        )
        
        # Xóa thuộc tính navigator.webdriver chống phát hiện bot
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        page = context.new_page()
        
        if HAS_STEALTH:
            try:
                Stealth().apply_stealth_sync(page)
            except Exception:
                pass
                
        return browser, context, page

    def _format_input_data(self, record):
        # Format Mã thẻ
        ma_the_raw = record.get('Mã thẻ', record.get('MaThe', ''))
        if pd.isna(ma_the_raw):
            ma_the = ""
        elif isinstance(ma_the_raw, float) and ma_the_raw.is_integer():
            ma_the = str(int(ma_the_raw))
        else:
            ma_the = str(ma_the_raw).strip()

        # Chuẩn hóa mã thẻ số
        if ma_the.isdigit():
            ma_the = ma_the.lstrip('0').zfill(10)

        # Format Họ tên
        ho_ten_raw = record.get('Họ Tên', record.get('Họ và Tên', record.get('HoTen', '')))
        ho_ten = "" if pd.isna(ho_ten_raw) else str(ho_ten_raw).strip()

        # Format Ngày sinh
        ngay_sinh_raw = record.get('Ngày Sinh', record.get('Năm Sinh', record.get('NgaySinh', '')))
        if pd.isna(ngay_sinh_raw):
            ngay_sinh = ""
        elif isinstance(ngay_sinh_raw, pd.Timestamp):
            ngay_sinh = ngay_sinh_raw.strftime('%d/%m/%Y')
        elif isinstance(ngay_sinh_raw, (int, float)):
            ngay_sinh = str(int(ngay_sinh_raw))
        else:
            s_date = str(ngay_sinh_raw).strip()
            try:
                if "-" in s_date and len(s_date) == 10:
                    parsed = pd.to_datetime(s_date)
                    ngay_sinh = parsed.strftime('%d/%m/%Y')
                else:
                    ngay_sinh = s_date
            except:
                ngay_sinh = s_date

        return ma_the, ho_ten, ngay_sinh

    def _solve_captcha(self, page):
        """Cắt trực tiếp khung element #imgCaptcha và dùng ddddocr mặc định."""
        try:
            captcha_selector = "#imgCaptcha"
            page.wait_for_selector(captcha_selector, state="visible", timeout=10000)
            captcha_element = page.locator(captcha_selector).first
            img_bytes = captcha_element.screenshot()
            
            captcha_text = self.ocr.classification(img_bytes)
            return captcha_text.strip()
        except Exception:
            return ""

    def scrape_single_record(self, record, page=None, close_browser=True):
        ma_the, ho_ten, ngay_sinh = self._format_input_data(record)
        
        result_info = {
            "Mã thẻ": ma_the,
            "Họ Tên": ho_ten,
            "Ngày Sinh": ngay_sinh,
            "Trạng Thái": "Lỗi hệ thống",
            "Nội Dung Kết Quả": "",
            "Thời Gian Tra Cứu": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        if not ma_the or not ho_ten or not ngay_sinh:
            result_info["Trạng Thái"] = "Thiếu thông tin"
            result_info["Nội Dung Kết Quả"] = "Dữ liệu đầu vào thiếu Mã thẻ, Họ tên hoặc Ngày sinh."
            return result_info

        p_instance = None
        browser_instance = None
        should_close = False

        try:
            if page is None:
                p_instance = sync_playwright().start()
                browser_instance, context, page = self._launch_browser(p_instance)
                should_close = True

            page.goto(self.url, wait_until="domcontentloaded", timeout=60000)

            # 2. KIỂM TRA RESPONSE & DEBUG: Chờ form #txtMaThe, nếu không thấy chụp ảnh màn hình debug_cloud.png
            try:
                page.wait_for_selector("#txtMaThe", state="visible", timeout=15000)
            except Exception as e:
                print(f"[DEBUG CLOUD] Không thể tải form tra cứu #txtMaThe: {e}")
                try:
                    page.screenshot(path="debug_cloud.png")
                except Exception:
                    pass
                result_info["Trạng Thái"] = "Lỗi kết nối"
                result_info["Nội Dung Kết Quả"] = "Không thể nạp form tra cứu từ Cổng BHXH (Trang bị chặn hoặc quá tải)."
                return result_info

            captcha_success = False

            for attempt in range(1, self.max_retries + 1):
                # Điền form kèm trigger sự kiện (Press Tab sau khi fill)
                page.fill("#txtMaThe", ma_the)
                page.locator("#txtMaThe").dispatch_event("change")
                page.locator("#txtMaThe").focus()
                page.keyboard.press("Tab")

                page.fill("#txtHoTen", ho_ten)
                page.locator("#txtHoTen").dispatch_event("change")
                page.locator("#txtHoTen").focus()
                page.keyboard.press("Tab")

                page.fill("#txtNgaySinh", ngay_sinh)
                page.locator("#txtNgaySinh").dispatch_event("change")
                page.locator("#txtNgaySinh").focus()
                page.keyboard.press("Tab")

                captcha_text = self._solve_captcha(page)
                if not captcha_text:
                    if page.locator("#imgCaptcha").count() > 0:
                        page.locator("#imgCaptcha").first.click()
                    page.wait_for_timeout(1000)
                    continue

                page.fill("#tokenRecaptch", captcha_text)
                page.locator("#tokenRecaptch").dispatch_event("change")
                page.locator("#tokenRecaptch").focus()
                page.keyboard.press("Tab")

                page.click("#btnTraCuu")
                page.wait_for_timeout(2500)

                # Kiểm tra thông báo lỗi Captcha từ #messeger
                err_msg = ""
                if page.locator("#messeger").count() > 0:
                    err_msg = page.locator("#messeger").first.inner_text().strip()

                if err_msg and any(k in err_msg.lower() for k in ["không hợp lệ", "không đúng", "mã xác"]):
                    if page.locator("#imgCaptcha").count() > 0:
                        page.locator("#imgCaptcha").first.click()
                    page.wait_for_timeout(1000)
                    continue

                # Kiểm tra khung kết quả #tcContainer
                if page.locator("#tcContainer").count() > 0:
                    tc_text = page.locator("#tcContainer").first.inner_text().strip()
                    if tc_text:
                        captcha_success = True
                        if "Chưa có thông tin" in tc_text or "không tìm thấy" in tc_text.lower():
                            result_info["Trạng Thái"] = "Không tìm thấy"
                            result_info["Nội Dung Kết Quả"] = tc_text
                        else:
                            result_info["Trạng Thái"] = "Thành công"
                            result_info["Nội Dung Kết Quả"] = tc_text
                        break

            if not captcha_success and result_info["Trạng Thái"] == "Lỗi hệ thống":
                result_info["Trạng Thái"] = "Lỗi Captcha"
                result_info["Nội Dung Kết Quả"] = f"Không giải đúng Captcha sau {self.max_retries} lần thử."

        except Exception as e:
            result_info["Trạng Thái"] = "Lỗi kết nối"
            result_info["Nội Dung Kết Quả"] = f"Lỗi trong quá trình tra cứu: {str(e)}"

        finally:
            if should_close and close_browser:
                if browser_instance:
                    browser_instance.close()
                if p_instance:
                    p_instance.stop()

        return result_info

    def scrape_batch(self, records_list, callback=None):
        results = []
        with sync_playwright() as p:
            browser, context, page = self._launch_browser(p)
            total = len(records_list)
            for idx, record in enumerate(records_list):
                res = self.scrape_single_record(record, page=page, close_browser=False)
                results.append(res)
                if callback:
                    callback(idx + 1, total, res)

            browser.close()

        return results
