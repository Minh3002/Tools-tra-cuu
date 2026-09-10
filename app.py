import streamlit as st
import pandas as pd
import time
from io import BytesIO
from datetime import datetime
from scraper import BHYTScraper

# Page Configuration
st.set_page_config(
    page_title="Tra Cứu BHYT Tự Động (Local App)",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for rich aesthetics
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(135deg, #1E88E5 0%, #1565C0 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 1rem;
        color: #546E7A;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 1rem;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
        margin-top: 0.2rem;
    }
    .result-box {
        background: #F8FAFC;
        border-left: 4px solid #1E88E5;
        padding: 1.2rem;
        border-radius: 8px;
        margin-top: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# App Header
st.markdown("<div class='main-title'>🛡️ Tra Cứu Thông Tin BHYT Tự Động</div>", unsafe_allow_html=True)
st.markdown("<div class='sub-title'>Hệ thống tự động tra cứu BHYT từ Cổng thông tin BHXH Việt Nam | Tích hợp AI OCR giải Captcha tự động</div>", unsafe_allow_html=True)

# Sidebar Configuration
with st.sidebar:
    st.image("https://img.icons8.com/color/96/shield.png", width=64)
    st.header("⚙️ Cấu Hình Hệ Thống")
    max_retries = st.slider("Số lần thử giải Captcha tối đa", min_value=1, max_value=10, value=3)
    headless_mode = st.checkbox("Chạy ẩn trình duyệt (Headless)", value=True)
    
    st.divider()
    st.info("💡 **Mẹo sử dụng:**\n- Định dạng cột Excel: `Mã thẻ`, `Họ Tên`, `Ngày Sinh`.\n- Ngày sinh chấp nhận `DD/MM/YYYY` hoặc năm sinh `YYYY`.")

# Main Navigation Tabs
tab1, tab2, tab3 = st.tabs(["📁 Tra Cứu Hàng Loạt (Excel)", "🔍 Tra Cứu Nhanh (1 Thẻ)", "ℹ️ Hướng Dẫn & Mẫu Excel"])

# TAB 1: BATCH LOOKUP FROM EXCEL
with tab1:
    uploaded_file = st.file_uploader("Tải lên file Excel (.xlsx, .xls) hoặc CSV", type=["xlsx", "xls", "csv"])
    
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file, dtype=str)
            else:
                df = pd.read_excel(uploaded_file, dtype=str)
                
            st.success(f"📂 Đã nạp thành công file: **{uploaded_file.name}** ({len(df)} dòng dữ liệu)")
            
            # Flexible column mapping check
            cols = df.columns.tolist()
            col_ma_the = next((c for c in cols if 'mã' in c.lower() or 'mathe' in c.lower() or 'card' in c.lower()), None)
            col_ho_ten = next((c for c in cols if 'tên' in c.lower() or 'hoten' in c.lower() or 'name' in c.lower()), None)
            col_ngay_sinh = next((c for c in cols if 'sinh' in c.lower() or 'ngaysinh' in c.lower() or 'dob' in c.lower()), None)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                sel_ma_the = st.selectbox("Cột Mã thẻ BHYT", cols, index=cols.index(col_ma_the) if col_ma_the else 0)
            with col2:
                sel_ho_ten = st.selectbox("Cột Họ và Tên", cols, index=cols.index(col_ho_ten) if col_ho_ten else (1 if len(cols)>1 else 0))
            with col3:
                sel_ngay_sinh = st.selectbox("Cột Ngày/Năm Sinh", cols, index=cols.index(col_ngay_sinh) if col_ngay_sinh else (2 if len(cols)>2 else 0))

            # Ensure Mã thẻ preserves leading zeros as entered in Excel
            if sel_ma_the in df.columns:
                df[sel_ma_the] = df[sel_ma_the].fillna("").astype(str).str.strip().str.replace(r'\.0$', '', regex=True)

            with st.expander("👀 Xem trước 5 dòng đầu tiên", expanded=False):
                st.dataframe(df.head(), use_container_width=True)

            if st.button("🚀 Bắt Đầu Tra Cứu Hàng Loạt", type="primary", use_container_width=True):
                records = []
                for _, row in df.iterrows():
                    records.append({
                        "Mã thẻ": row[sel_ma_the],
                        "Họ Tên": row[sel_ho_ten],
                        "Ngày Sinh": row[sel_ngay_sinh]
                    })

                progress_bar = st.progress(0)
                status_text = st.empty()
                log_box = st.empty()
                
                scraper = BHYTScraper(headless=headless_mode, max_retries=max_retries)
                results = []
                
                logs = []
                def on_progress(current, total, item_res):
                    pct = current / total
                    progress_bar.progress(pct)
                    status_text.markdown(f"⏳ **Đang xử lý ({current}/{total}):** `{item_res['Họ Tên']}` - {item_res['Mã thẻ']}")
                    
                    status_icon = "✅" if item_res['Trạng Thái'] == 'Thành công' else ("🟡" if item_res['Trạng Thái'] == 'Không tìm thấy' else "❌")
                    logs.append(f"{status_icon} [{current}/{total}] {item_res['Họ Tên']} ({item_res['Mã thẻ']}) -> {item_res['Trạng Thái']}")
                    log_box.text_area("Nhật ký thực thi", "\n".join(logs[-8:]), height=150)

                start_time = time.time()
                with st.spinner("Hệ thống đang mở trình duyệt và tra cứu tự động..."):
                    results = scraper.scrape_batch(records, callback=on_progress)
                elapsed = round(time.time() - start_time, 1)

                status_text.success(f"🎉 Hoàn thành tra cứu {len(results)} bản ghi trong {elapsed} giây!")
                
                df_results = pd.DataFrame(results)
                
                # Metrics Summary
                total_cnt = len(df_results)
                success_cnt = len(df_results[df_results['Trạng Thái'] == 'Thành công'])
                notfound_cnt = len(df_results[df_results['Trạng Thái'] == 'Không tìm thấy'])
                error_cnt = total_cnt - success_cnt - notfound_cnt

                m1, m2, m3, m4 = st.columns(4)
                with m1:
                    st.markdown(f"<div class='metric-card'><div>Tổng bản ghi</div><div class='metric-value'>{total_cnt}</div></div>", unsafe_allow_html=True)
                with m2:
                    st.markdown(f"<div class='metric-card' style='border-top: 4px solid #10B981;'><div>🟢 Thành công</div><div class='metric-value' style='color:#10B981;'>{success_cnt}</div></div>", unsafe_allow_html=True)
                with m3:
                    st.markdown(f"<div class='metric-card' style='border-top: 4px solid #F59E0B;'><div>🟡 Không tìm thấy</div><div class='metric-value' style='color:#F59E0B;'>{notfound_cnt}</div></div>", unsafe_allow_html=True)
                with m4:
                    st.markdown(f"<div class='metric-card' style='border-top: 4px solid #EF4444;'><div>🔴 Lỗi / Thất bại</div><div class='metric-value' style='color:#EF4444;'>{error_cnt}</div></div>", unsafe_allow_html=True)

                st.subheader("📊 Bảng Kết Quả Chi Tiết")
                st.dataframe(df_results, use_container_width=True)

                # Export to Excel
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df_results.to_excel(writer, index=False, sheet_name='KetQuaTraCuu')
                
                st.download_button(
                    label="📥 Tải về Kết Quả (File Excel)",
                    data=output.getvalue(),
                    file_name=f"output_bhyt_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary"
                )
        except Exception as e:
            st.error(f"Lỗi đọc file Excel: {e}")

# TAB 2: SINGLE RECORD LOOKUP
with tab2:
    st.subheader("🔍 Tra Cứu Nhanh 1 Cá Nhân")
    with st.form("single_form"):
        c1, c2, c3 = st.columns(3)
        with c1:
            input_ma_the = st.text_input("Mã thẻ BHYT / Mã số BHXH *", placeholder="Ví dụ: 1078014401 hoặc DN401...")
        with c2:
            input_ho_ten = st.text_input("Họ và Tên *", placeholder="Ví dụ: NGUYỄN HỮU TIẾN")
        with c3:
            input_ngay_sinh = st.text_input("Ngày hoặc Năm Sinh *", placeholder="Ví dụ: 30/06/1978 hoặc 1978")
            
        btn_submit = st.form_submit_button("🔍 Tra Cứu Ngay", type="primary", use_container_width=True)

    if btn_submit:
        if not input_ma_the or not input_ho_ten or not input_ngay_sinh:
            st.warning("⚠️ Vui lòng điền đầy đủ Mã thẻ, Họ tên và Ngày sinh!")
        else:
            with st.spinner("Đang kết nối Cổng BHXH Việt Nam và giải Captcha..."):
                scraper = BHYTScraper(headless=headless_mode, max_retries=max_retries)
                res = scraper.scrape_single_record({
                    "Mã thẻ": input_ma_the,
                    "Họ Tên": input_ho_ten,
                    "Ngày Sinh": input_ngay_sinh
                })
                
            st.write("---")
            if res['Trạng Thái'] == 'Thành công':
                st.success("🟢 **Tra cứu thành công!**")
            elif res['Trạng Thái'] == 'Không tìm thấy':
                st.warning("🟡 **Không tìm thấy thông tin!**")
            else:
                st.error(f"🔴 **{res['Trạng Thái']}**")
                
            st.markdown(f"""
            <div class='result-box'>
                <h4>📋 Thông Tin Trả Về từ BHXH:</h4>
                <p><b>Mã thẻ:</b> {res['Mã thẻ']} | <b>Họ tên:</b> {res['Họ Tên']} | <b>Ngày sinh:</b> {res['Ngày Sinh']}</p>
                <hr/>
                <pre style="white-space: pre-wrap; font-family: inherit;">{res['Nội Dung Kết Quả']}</pre>
            </div>
            """, unsafe_allow_html=True)

# TAB 3: INSTRUCTIONS & TEMPLATE
with tab3:
    st.subheader("ℹ️ Hướng Dẫn Sử Dụng & File Mẫu")
    st.markdown("""
    ### 1. Cấu trúc file Excel mẫu
    File Excel tải lên cần chứa 3 cột thông tin cơ bản:
    - **Mã thẻ**: Mã số BHXH 10 số hoặc Mã thẻ BHYT 15 ký tự (ví dụ: `1078014401` hoặc `DN4010120860538`).
    - **Họ Tên**: Họ và tên tiếng Việt có dấu (ví dụ: `NGUYỄN HỮU TIẾN`).
    - **Ngày Sinh**: Định dạng `DD/MM/YYYY` (ví dụ: `30/06/1978`) hoặc chỉ ghi Năm sinh `1978`.

    ### 2. Nguyên lý hoạt động
    - Ứng dụng tự động điều khiển trình duyệt Chromium chạy ngầm (Playwright).
    - Sử dụng mô hình AI OCR (`ddddocr`) để tự động giải Captcha hình ảnh của Cổng thông tin BHXH Việt Nam.
    - Cơ chế tự động thử lại khi Captcha bị nhiễu.
    """)
    
    sample_df = pd.DataFrame([
        {"Mã thẻ": "1078014401", "Họ Tên": "NGUYỄN HỮU TIẾN", "Ngày Sinh": "30/06/1978"},
        {"Mã thẻ": "93099005270", "Họ Tên": "NGUYỄN TRÍ QUỐC", "Ngày Sinh": "12/09/1999"},
        {"Mã thẻ": "75199019731", "Họ Tên": "TRÀ THỊ THÚY", "Ngày Sinh": "14/05/1999"}
    ])
    
    sample_output = BytesIO()
    with pd.ExcelWriter(sample_output, engine='openpyxl') as writer:
        sample_df.to_excel(writer, index=False, sheet_name='DanhSachMau')
        
    st.download_button(
        label="📥 Tải về File Excel Mẫu Demo (.xlsx)",
        data=sample_output.getvalue(),
        file_name="input.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
