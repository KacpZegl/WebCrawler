# main.py

from crawler.crawler import WebCrawler
from config import START_URLS, MAX_PAGES, EXTRACTED_PAGES_MAX

if __name__ == "__main__":
    crawler = WebCrawler(START_URLS, MAX_PAGES, EXTRACTED_PAGES_MAX)
    crawler.start_crawling()
