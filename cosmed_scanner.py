import asyncio
import json
import random
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        print("🌐 啟動康是美自動化爬蟲 (無限捲軸版)...")
        
        browser = await p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )
        
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 1000},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        )
        
        page = await context.new_page()
        # 抹除機器人痕跡
        await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        # 康是美買一送一/促銷專區
        url = "https://shop.cosmed.com.tw/v2/official/SalePageCategory/259104?sortMode=Sales"
        
        all_products = []

        try:
            print("🚀 前往康是美頁面...")
            await page.goto(url, wait_until="commit", timeout=60000)
            
            # 等待初始商品載入
            await page.wait_for_selector("[data-qe-id='body-sale-page-title-text']", timeout=20000)

            last_count = 0
            retry_count = 0

            while True:
                # 1. 模擬捲動觸發載入更多
                await page.mouse.wheel(0, 2000)
                await asyncio.sleep(2)
                await page.keyboard.press("End") # 強制跳到最底部觸發 API
                await asyncio.sleep(3)

                # 2. 抓取當前頁面所有商品
                current_items = await page.evaluate("""() => {
                    const results = [];
                    // 使用 data-qe-id 定位，這比隨機 Class 更穩定
                    const titles = document.querySelectorAll("[data-qe-id='body-sale-page-title-text']");
                    
                    titles.forEach(titleNode => {
                        // 往上找最近的商品容器
                        const container = titleNode.closest('li') || titleNode.parentElement.parentElement.parentElement;
                        const priceNode = container.querySelector("[data-qe-id='body-price-text']");
                        
                        const name = titleNode.innerText.trim();
                        const price = priceNode ? priceNode.innerText.trim() : "價格點入查看";

                        if (name) {
                            results.push({
                                name: name,
                                price: price,
                                source: "康是美"
                            });
                        }
                    });
                    return results;
                }""")

                # 3. 合併與去重
                for item in current_items:
                    if not any(x['name'] == item['name'] for x in all_products):
                        all_products.append(item)
                
                print(f"🔄 目前掃描中... 已累計抓取 {len(all_products)} 筆商品")

                # 4. 判斷是否停止 (無限捲軸終止條件)
                if len(all_products) == last_count:
                    retry_count += 1
                    if retry_count >= 3: # 連續三次捲動數量都沒增加，視為底部
                        print("🛑 已到達網頁底部，抓取結束。")
                        break
                else:
                    last_count = len(all_products)
                    retry_count = 0

            # 5. 存檔
            with open('cosmed.json', 'w', encoding='utf-8') as f:
                json.dump(all_products, f, ensure_ascii=False, indent=4)
            print(f"✨ 任務完成！康是美共抓取 {len(all_products)} 筆資料。")

        except Exception as e:
            print(f"💥 發生錯誤: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(run())