# main.py

from crawler.crawler import WebCrawler
from config import START_URLS, MAX_PAGES, EXTRACTED_PAGES_MAX

if __name__ == "__main__":
    crawler = WebCrawler()
    crawler.start_crawling()
