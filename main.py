# main.py

from crawler.crawler import WebCrawler
from config import START_URLS, MAX_PAGES

if __name__ == "__main__":
    crawler = WebCrawler(START_URLS, MAX_PAGES)
    crawler.start_crawling()
