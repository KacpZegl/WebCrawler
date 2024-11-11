# crawler/crawler.py

import requests
import time
from crawler.url_manager import URLManager
from crawler.wiki_parser import WikiParser
from crawler.lektury_parser import LekturyParser
from crawler.storage import Storage
from crawler.robots import RobotsHandler
from modules.logger import logger
from config import USER_AGENT
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

class WebCrawler:
    def __init__(self, start_urls, max_pages):
        self.url_manager = URLManager(start_urls)
        self.parsers = {
            'pl.wikipedia.org': WikiParser(),
            'wolnelektury.pl': LekturyParser(),  # Upewnij się, że domena jest poprawnie przypisana
            'lektury.gov.pl': LekturyParser(),  # Jeśli używasz również tej domeny
        }
        self.storage = Storage()
        self.robots_handler = RobotsHandler()
        self.max_pages = max_pages
        self.headers = {
            'User-Agent': USER_AGENT
            # Możesz dodać inne nagłówki, jeśli są potrzebne
        }

    def fetch(self, url):
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                response.encoding = response.apparent_encoding
                return response.text
            else:
                logger.warning(f"HTTP error {response.status_code} while fetching {url}")
                return None
        except requests.RequestException as e:
            logger.error(f"Error fetching {url}: {e}")
            return None

    def start_crawling(self):
        page_count = 0
        while self.url_manager.has_urls() and page_count < self.max_pages:
            next_item = self.url_manager.get_next_url()
            if next_item is None:
                break
            url, origin_url = next_item
            if url in self.url_manager.visited:
                continue  # Unikamy ponownego odwiedzania tej samej strony
            logger.info(f"Fetching: {url} (Origin: {origin_url})")

            domain = urlparse(url).netloc

            # Sprawdzenie robots.txt
            if not self.robots_handler.can_fetch(url, USER_AGENT):
                logger.info(f"Access denied by robots.txt: {url}")
                continue

            content = self.fetch(url)
            if content:
                parser = self.parsers.get(domain)
                if parser:
                    data, metadata = parser.parse(content, url)
                    if data and metadata:
                        self.storage.save(data, metadata, url)
                        page_count += 1
                        self.url_manager.mark_visited(url)

                        # Dodawanie powiązanych URL-i tylko dla Wikipedii
                        if domain == 'pl.wikipedia.org':
                            related_urls = self.extract_related_urls(content, url)
                            if related_urls:
                                self.url_manager.add_urls(origin_url, related_urls)
                    else:
                        logger.warning(f"Parser returned no data for URL: {url}")
                else:
                    logger.warning(f"No parser available for domain: {domain}")
            else:
                logger.warning(f"No content fetched for URL: {url}")

            # Opóźnienie między żądaniami
            time.sleep(1)

        logger.info("Crawling completed.")
        logger.info(f"Visited {page_count} pages.")

    def extract_related_urls(self, content, base_url):
        related_urls = []
        soup = BeautifulSoup(content, 'html.parser')
        # Pobieramy linki do kategorii
        category_elements = soup.select('#mw-normal-catlinks ul li a')
        for cat_elem in category_elements:
            cat_href = cat_elem.get('href')
            full_cat_url = urljoin(base_url, cat_href)
            # Pobieramy stronę kategorii
            category_page_content = self.fetch(full_cat_url)
            if category_page_content:
                cat_soup = BeautifulSoup(category_page_content, 'html.parser')
                # Znajdujemy linki do artykułów w kategorii
                for link in cat_soup.select('.mw-category-group ul li a'):
                    href = link.get('href')
                    if href.startswith('/wiki/'):
                        full_url = urljoin(base_url, href)
                        if self.parsers['pl.wikipedia.org'].is_valid_url(full_url, base_url):
                            related_urls.append(full_url)
        return related_urls
