import asyncio
import json
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        # headless=False 方便觀察爬取過程
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 1000},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        # 家樂福買一送一活動長網址
        url = "https://online.carrefour.com.tw/zh/%E8%B2%B7%E4%B8%80%E9%80%81%E4%B8%80%28%E5%95%86%E5%93%81%E5%83%B9%E6%A0%BC%E5%8F%8A%E6%B4%BB%E5%8B%95%E7%94%9F%E6%95%88%E6%99%82%E9%96%93%E7%82%BA%E4%BF%83%E9%8A%B7%E8%B5%B7%E5%A7%8B%E6%97%A5%E6%97%A9%E4%B8%8A9%3A00%E8%B5%B7%29"
        
        all_products = []
        page_num = 1
        last_url = ""

        try:
            print("🚀 正在開啟家樂福買一送一專區...")
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            
            # 等待價格元素出現，確保頁面至少加載出商品
            try:
                await page.wait_for_selector('.current-price', timeout=15000)
            except:
                print("⚠️ 警告：頁面加載較慢，若有彈窗請手動點掉...")

            print("💡 提示：若有彈窗請手動點掉，程式將持續掃描...")

            while True:
                current_url = page.url
                print(f"📄 正在處理第 {page_num} 頁... (網址末段: {current_url[-15:]})")
                
                # 1. 暴力捲動與等待載入
                for _ in range(3):
                    await page.evaluate("window.scrollBy(0, 1500)")
                    await asyncio.sleep(1.5)
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(2)

                # 2. 執行 JS 抓取資料：改用更具彈性的定位方式
                new_items = await page.evaluate("""() => {
                    const results = [];
                    // 1. 先抓取所有的價格區塊，因為它是商品存在的黃金特徵
                    const prices = document.querySelectorAll('.current-price');
                    
                    prices.forEach(priceEl => {
                        // 2. 找到這個價格所屬的商品大容器 (向上找包含名稱的 div)
                        const container = priceEl.closest('div[class*="item"], .product-item, .item-block');
                        if (!container) return;

                        // 3. 在容器內精確提取資訊
                        const nameEl = container.querySelector('.item-name, .name, a[title]');
                        const realPriceEl = priceEl.querySelector('em'); // 取出 <em>$999</em> 中的金額
                        const labels = container.querySelector('.little-label');
                        
                        const nameText = nameEl ? nameEl.innerText.trim() : "";
                        const priceText = realPriceEl ? realPriceEl.innerText.trim() : "未標價";
                        const labelText = labels ? labels.innerText : "";

                        // 4. 過濾：必須有名稱且標籤包含「買一送一」
                        if (nameText && (labelText.includes('買一送一') || labelText.includes('買1送1'))) {
                            results.push({ 
                                name: nameText, 
                                price: priceText, 
                                source: "家樂福",
                                date: "活動中"
                            });
                        }
                    });
                    return results;
                }""")

                # 3. 合併資料並去重
                count_before = len(all_products)
                for item in new_items:
                    if not any(x['name'] == item['name'] for x in all_products):
                        all_products.append(item)
                
                added_this_page = len(all_products) - count_before
                print(f"✅ 第 {page_num} 頁完成，新增 {added_this_page} 筆，總累計 {len(all_products)} 筆。")

                # 4. 定位「下一頁」按鈕 (next.svg)
                next_btn = page.locator('a:has(img[src*="next.svg"])').last
                
                # --- 判斷停止條件 ---
                if not await next_btn.is_visible():
                    print("🛑 找不到下一頁按鈕，或已到最後一頁。")
                    break
                
                if current_url == last_url:
                    print("🛑 網址未變更，判定抓取結束。")
                    break
                
                last_url = current_url

                # 5. 點擊下一頁
                print("➡️ 點擊『Next』進入下一頁...")
                try:
                    await next_btn.scroll_into_view_if_needed()
                    # 強制點擊 (繞過 UI 遮擋)
                    await page.evaluate('(el) => el.click()', await next_btn.element_handle())
                    page_num += 1
                    await asyncio.sleep(6) # 給予充足時間加載下一頁內容
                except Exception as click_err:
                    print(f"⚠️ 點擊失敗：{click_err}")
                    break

            # 6. 存檔
            unique_data = list({v['name']:v for v in all_products}.values())
            with open('carrefour.json', 'w', encoding='utf-8') as f:
                json.dump(unique_data, f, ensure_ascii=False, indent=4)
            
            print("---")
            print(f"✨ 任務完成！")
            print(f"📁 檔案: carrefour.json")
            print(f"📦 總商品數: {len(unique_data)} 筆")

        except Exception as e:
            print(f"💥 錯誤：{e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(run())