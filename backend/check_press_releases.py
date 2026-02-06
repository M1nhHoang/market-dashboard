"""Quick script to check press releases and test attachment extraction."""
import json
import asyncio
from pathlib import Path
from crawlers.sbv_crawler import SBVCrawler

# Load crawl result
with open('./data/raw/test_full_crawl_20260203_165739.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print("=== PRESS RELEASES FROM HOMEPAGE ===\n")
press_releases = [x for x in data['homepage_items'] if x.get('type') == 'press_release']

for i, pr in enumerate(press_releases):
    print(f"[{i+1}] {pr.get('title', 'N/A')}")
    print(f"    URL: {pr.get('source_url', 'N/A')}")
    print()

# Test fetching first press release
if press_releases:
    print("\n=== TESTING PRESS RELEASE WITH ATTACHMENTS ===\n")
    
    async def test_press_release():
        crawler = SBVCrawler(data_dir=Path("./data"))
        
        for pr in press_releases:
            url = pr.get('source_url', '')
            print(f"Fetching: {url}")
            
            result = await crawler.fetch_article_content(url)
            
            if result:
                print(f"  Title: {result.get('title', 'N/A')[:80]}")
                print(f"  Has Attachments: {result.get('has_attachments', False)}")
                print(f"  Attachments count: {len(result.get('attachments', []))}")
                
                for att in result.get('attachments', []):
                    print(f"    - [{att['type']}] {att['name']}")
                    print(f"      URL: {att['url'][:100]}...")
                
                print(f"  Content length: {result.get('content_length', 0)} chars")
                print()
            else:
                print(f"  Failed to extract!")
                print()
    
    asyncio.run(test_press_release())
