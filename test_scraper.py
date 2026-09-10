import sys
import pandas as pd
from scraper import BHYTScraper

sys.stdout.reconfigure(encoding='utf-8')

def test():
    try:
        df = pd.read_excel('danhsach.xlsx', dtype=str)
        print(f"Loaded {len(df)} rows from danhsach.xlsx", flush=True)
        print(f"Columns: {df.columns.tolist()}", flush=True)

        records = df.to_dict(orient='records')
        scraper = BHYTScraper(headless=True)
        
        def progress_cb(current, total, item_res):
            print(f"[{current}/{total}] {item_res['Họ Tên']} -> {item_res['Trạng Thái']}: {item_res['Nội Dung Kết Quả'][:80]}", flush=True)

        print("\n--- Testing scrape_batch ---", flush=True)
        results = scraper.scrape_batch(records, callback=progress_cb)
        print("\nFinished scrape_batch! Results summary:", flush=True)
        for r in results:
            print(r, flush=True)

    except Exception as e:
        print(f"Error during test: {e}", flush=True)

if __name__ == '__main__':
    test()
