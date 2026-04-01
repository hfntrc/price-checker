import asyncio
import json
import random
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        print("🌐 啟動全聯買一送一爬蟲...")
        
        # 使用原生偽裝啟動
        browser = await p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )
        
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 1000},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        )
        
        page = await context.new_page()
        # 抹除自動化標記
        await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        # 全聯買一送一專區網址
        url = "https://www.pxmart.com.tw/campaign/life-will/best-buy/%E8%B2%B7%E4%B8%80%E9%80%81%E4%B8%80%E5%A4%A7%E9%9B%86%E5%90%88"
        
        all_products = []

        try:
            print("🚀 前往全聯專區...")
            await page.goto(url, wait_until="commit", timeout=60000)
            
            # 等待商品卡片載入
            print("⏳ 等待商品渲染... 請手動向下捲動以觸發載入")
            await page.wait_for_selector("h5[class*='card-title']", timeout=30000)

            # 模擬捲動以確保所有 Lazy Load 的商品都出現
            for i in range(10):
                await page.mouse.wheel(0, 1000)
                await asyncio.sleep(1.5)
                print(f"已捲動 {i+1}/10...")

            # --- 執行資料抓取 ---
            print("🔎 開始解析商品資訊...")
            new_items = await page.evaluate("""() => {
                const results = [];
                // 定位所有商品卡片 (通常是在 h5 標題的祖先節點)
                const titles = document.querySelectorAll("h5[class*='card-title']");
                
                titles.forEach(titleNode => {
                    // 尋找包裹整個商品的容器
                    const container = titleNode.closest('div[class*="Card_card-container"]') || titleNode.parentElement.parentElement;
                    
                    // 1. 抓取品名
                    const name = titleNode.innerText.trim();
                    
                    // 2. 抓取商品標示 (買一送一、任2袋等資訊)
                    const infoList = container.querySelectorAll("ul[class*='card-list'] li");
                    let promoInfo = "";
                    infoList.forEach(li => {
                        promoInfo += li.innerText.trim() + " ";
                    });

                    // 3. 抓取價格 (平均價格)
                    const priceUnit = container.querySelector("p[class*='card-productUnit']"); // 如：平均一袋
                    const priceVal = container.querySelector("p[class*='card-productPrice']"); // 如：58元
                    
                    let finalPrice = "";
                    if (priceVal) {
                        const unitText = priceUnit ? priceUnit.innerText.trim() : "";
                        const priceText = priceVal.innerText.trim();
                        finalPrice = `${unitText}${priceText}`;
                    } else {
                        finalPrice = "見標示";
                    }

                    if (name) {
                        results.push({
                            name: name,
                            price: finalPrice || "買一送一",
                            info: promoInfo.trim(),
                            source: "全聯"
                        });
                    }
                });
                return results;
            }""")

            # 去重並儲存
            for item in new_items:
                if not any(x['name'] == item['name'] for x in all_products):
                    all_products.append(item)
            
            print(f"✅ 抓取完成！共計 {len(all_products)} 筆全聯商品資料。")

            # 存檔為 data.json
            with open('pxmart.json', 'w', encoding='utf-8') as f:
                json.dump(all_products, f, ensure_ascii=False, indent=4)

        except Exception as e:
            print(f"💥 發生錯誤: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(run())