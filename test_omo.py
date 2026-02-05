import asyncio
from crawlers.sbv_crawler import SBVCrawler
from pathlib import Path
import json

async def test():
    crawler = SBVCrawler(Path('./data'))
    
    # Run full crawl (limited to 1 article for speed)
    result = await crawler.run(max_articles=1, extract_pdf=False)
    
    # Get OMO data
    omo = [x for x in result.data if x.get('type') == 'omo']
    
    print(f'OMO items: {len(omo)}')
    print()
    
    for item in omo:
        print(f"Round {item.get('auction_round')}: {item.get('transaction_type')} - {item.get('term')} - {item.get('volume')}")
    
    print()
    print("Sample OMO data (first 2):")
    for item in omo[:2]:
        print(json.dumps(item, ensure_ascii=False, indent=2))
        print()

if __name__ == "__main__":
    asyncio.run(test())
