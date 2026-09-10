import os
import sys
import time
import pandas as pd
from datetime import datetime
from playwright.sync_api import sync_playwright
import ddddocr

class BHYTScraper:
    def __init__(self, headless=True, max_retries=3):
        self.headless = headless
        self.max_retries = max_retries
        # Dùng ddddocr mặc định (beta=False)
        self.ocr = ddddocr.DdddOcr(show_ad=False)
        self.url = "https://baohiemxahoi.gov.vn/tracuu/Pages/tra-cuu-thoi-han-su-dung-the-bhyt.aspx"

    def _launch_browser(self, p):
        """Khởi tạo trình duyệt Playwright chạy local ổn định."""
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        browser = p.chromium.launch(headless=self.headless)
        context = browser.new_context(
            user_agent=user_agent,
            viewport={"width": 1280, "height": 800},
            locale="vi-VN",
            timezone_id="Asia/Ho_Chi_Minh"
        )
        page = context.new_page()
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

        # Chuẩn hóa mã thẻ số (giữ nguyên độ dài 10 chữ số)
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
        """Cắt ảnh Captcha trực tiếp từ element #imgCaptcha trên trang và dùng ddddocr giải."""
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
            page.wait_for_selector("#txtMaThe", state="visible", timeout=15000)

            captcha_success = False

            for attempt in range(1, self.max_retries + 1):
                # Điền form + trigger sự kiện change + Tab để trang nhận đủ input
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
