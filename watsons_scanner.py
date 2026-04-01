import asyncio
import json
import random
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        print("🌐 啟動屈臣氏自動化爬蟲 (含 18 歲分級處理)...")
        
        browser = await p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        )
        
        page = await context.new_page()
        await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        url = "https://www.watsons.com.tw/search?text=%E8%B2%B7%E4%B8%80%E9%80%81%E4%B8%80&pageSize=64"
        all_products = []
        page_num = 1

        try:
            print("🚀 前往搜尋頁面...")
            await page.goto(url, wait_until="commit", timeout=60000)

            while True:
                print(f"--- 📄 正在處理第 {page_num} 頁 ---")

                # 1. 【核心：處理 18 歲警告彈窗】
                try:
                    # 定位彈窗內的「我已滿十八歲」按鈕
                    # 優先使用你提供的 class 與文字組合定位
                    age_btn = page.locator("e2-product-warning-modal a.btn-outline-primary:has-text('我已滿十八歲')")
                    
                    # 檢查是否看得到彈窗，最多等 5 秒
                    if await age_btn.is_visible(timeout=5000):
                        print("🔞 偵測到 18 歲警告，自動點擊「我已滿十八歲」...")
                        await age_btn.click()
                        await asyncio.sleep(2) # 等待彈窗消失
                except:
                    # 沒出現彈窗就直接跳過
                    pass

                # 2. 等待商品載入
                await page.wait_for_selector(".productName", timeout=20000)

                # 3. 模擬捲動觸發 Lazy Load
                for _ in range(5):
                    await page.mouse.wheel(0, 800)
                    await asyncio.sleep(1.2)

                # 4. 抓取資料
                new_items = await page.evaluate("""() => {
                    const results = [];
                    const nodes = document.querySelectorAll('.productName');
                    nodes.forEach(node => {
                        const parent = node.closest('e2-product-list-item') || node.parentElement.parentElement;
                        const nameEl = node.querySelector('a') || node;
                        const priceEl = parent.querySelector('.productPrice .formatted-value') || 
                                        parent.querySelector('.productPrice');
                        const name = nameEl.innerText.trim();
                        const price = priceEl ? priceEl.innerText.trim() : "買一送一";
                        if (name.length > 2) {
                            results.push({
                                name: name,
                                price: price.replace(/\\s+/g, ' ').trim(),
                                source: "屈臣氏"
                            });
                        }
                    });
                    return results;
                }""")

                # 合併資料
                initial_count = len(all_products)
                for item in new_items:
                    if not any(x['name'] == item['name'] for x in all_products):
                        all_products.append(item)
                
                print(f"✅ 本頁新增 {len(all_products) - initial_count} 筆，總累計 {len(all_products)} 筆。")

                # 5. 自動翻頁判斷
                next_btn_container = page.locator('li.page-item:has(i.icon-arrow-right)').last
                next_btn_link = next_btn_container.locator('a')

                if await next_btn_container.is_visible():
                    is_disabled = await next_btn_container.evaluate("el => el.classList.contains('disabled')")
                    if is_disabled:
                        print("🛑 已到達最後一頁。")
                        break
                    
                    print("➡️ 前往下一頁...")
                    await next_btn_link.scroll_into_view_if_needed()
                    await asyncio.sleep(1)
                    await next_btn_link.click(force=True)
                    
                    page_num += 1
                    await asyncio.sleep(random.randint(7, 10)) 
                else:
                    print("🛑 找不到翻頁按鈕。")
                    break

            # 存檔
            with open('watsons.json', 'w', encoding='utf-8') as f:
                json.dump(all_products, f, ensure_ascii=False, indent=4)
            print(f"✨ 抓取完成！共計 {len(all_products)} 筆。")

        except Exception as e:
            print(f"💥 錯誤: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(run())