"""
Test script for SBV Crawler run_full() method.

This tests the main entry point that:
1. Fetches all data from homepage
2. Fetches full content for news articles
3. Extracts PDF attachments
4. Saves everything to JSON
"""
import asyncio
import json
from datetime import datetime
from pathlib import Path

from crawlers.sbv_crawler import SBVCrawler


def print_separator(char="=", length=80):
    print(char * length)


async def main():
    print_separator()
    print("TESTING SBV CRAWLER - run() METHOD")
    print_separator()
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Initialize crawler
    data_dir = Path("./data")
    crawler = SBVCrawler(data_dir)
    
    print("🚀 Starting SBV full crawl...")
    print(f"   Source: {crawler.base_url}")
    print(f"   Max articles: 5")
    print(f"   Extract PDF: True")
    print()
    
    # Run full crawl
    result = await crawler.run(max_articles=5, extract_pdf=True)
    
    print_separator()
    print("RESULTS")
    print_separator()
    
    print(f"\n✅ Success: {result.success}")
    print(f"📅 Crawled at: {result.crawled_at.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🔢 Total items: {len(result.data)}")
    
    if result.error:
        print(f"⚠️  Errors: {result.error}")
    
    # Find and display metadata/stats
    metadata = next((x for x in result.data if x.get('type') == 'metadata'), None)
    if metadata:
        stats = metadata.get('stats', {})
        print(f"\n📊 Statistics:")
        print(f"   Exchange rates: {metadata.get('exchange_rates_count', 0)}")
        print(f"   Credit data: {metadata.get('credit_data_count', 0)}")
        print(f"   News with content: {metadata.get('news_with_content', 0)}")
        print(f"   News failed: {metadata.get('news_failed', 0)}")
        print(f"   News list only: {metadata.get('news_list_only', 0)}")
        print(f"\n📄 Content extracted:")
        print(f"   HTML chars: {stats.get('total_html_chars', 0):,}")
        print(f"   PDF files: {stats.get('total_pdf_files', 0)}")
        print(f"   PDF chars: {stats.get('total_pdf_chars', 0):,}")
    
    # Show sample articles with content
    articles_with_content = [
        x for x in result.data 
        if x.get('type') in ['news', 'press_release'] and x.get('fetch_success') == True
    ]
    
    if articles_with_content:
        print(f"\n📰 Sample articles with content:")
        for i, art in enumerate(articles_with_content[:3], 1):
            title = art.get('full_title') or art.get('title', 'N/A')
            content_len = art.get('content_length', 0)
            pdf_count = len(art.get('pdf_content', []))
            
            print(f"\n   [{i}] {title[:60]}...")
            print(f"       Content: {content_len:,} chars")
            print(f"       PDFs: {pdf_count}")
            
            # Show content preview
            content = art.get('content', '')
            if content:
                preview = content[:200].replace('\n', ' ')
                print(f"       Preview: {preview}...")
    
    print_separator()
    print("TEST COMPLETE - Data saved to ./data/raw/")
    print_separator()
    
    return result


if __name__ == "__main__":
    asyncio.run(main())
