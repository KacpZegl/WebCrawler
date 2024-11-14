# crawler/crawler.py

import re
import requests
import time
from urllib.parse import urlparse
from crawler.url_manager import URLManager
from crawler.wiki_parser import WikiParser
from crawler.lektury_parser import LekturyParser
from crawler.storage import Storage
from crawler.robots import RobotsHandler
from modules.logger import logger
from config import USER_AGENT, MAX_PAGES, EXTRACTED_PAGES_MAX

class WebCrawler:
    def __init__(self, start_urls, max_pages, extracted_pages_max):
        self.url_manager = URLManager(start_urls, extracted_pages_max)
        self.parsers = {
            'wolnelektury.pl': LekturyParser(USER_AGENT),
            'lektury.gov.pl': LekturyParser(USER_AGENT),
            'wikipedia.org': WikiParser(USER_AGENT),
        }
        self.storage = Storage()
        self.robots_handler = RobotsHandler()
        self.max_pages = max_pages
        self.page_count = 0

    def fetch(self, url):
        try:
            headers = {'User-Agent': USER_AGENT}
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                response.encoding = response.apparent_encoding
                return response.text
            else:
                logger.warning(f"HTTP error {response.status_code} while fetching {url}")
                return None
        except requests.RequestException as e:
            logger.error(f"Error fetching {url}: {e}")
            return None

    def get_parser(self, domain):
        if re.match(r'.*\.wikipedia\.org$', domain):
            return self.parsers.get('wikipedia.org')
        return self.parsers.get(domain)

    def start_crawling(self):
        while self.url_manager.has_urls() and self.page_count < self.max_pages:
            next_item = self.url_manager.get_next_url()
            if next_item is None:
                break
            url, origin_url = next_item
            if url in self.url_manager.visited:
                logger.debug(f"URL już odwiedzony: {url}")
                continue
            logger.info(f"Fetching: {url} (Origin: {origin_url})")

            domain = urlparse(url).netloc

            if not self.robots_handler.can_fetch(url, USER_AGENT):
                logger.info(f"Access denied by robots.txt: {url}")
                self.url_manager.mark_visited(url)
                continue

            content = self.fetch(url)
            if content:
                parser = self.get_parser(domain)
                if parser:
                    try:
                        is_start_url = url in self.url_manager.start_urls  # Poprawione: sprawdzenie, czy URL jest START_URL
                        parse_result = parser.parse(content, url, is_start_url)
                        if not parse_result:
                            logger.warning(f"Parser zwrócił None dla URL: {url}")
                            self.url_manager.mark_visited(url)
                            continue
                        data, data_type = parse_result

                        if data_type == 'start_url' and data:
                            # `data` zawiera zarówno linki, jak i tekst
                            related_links, (text, metadata) = data
                            # Dodaj linki do URLManager i uzyskaj faktycznie dodane linki
                            added_links = self.url_manager.add_extracted_url(origin_url, related_links)
                            # Zapisz tylko faktycznie dodane linki do extracted_links.txt
                            if added_links:
                                self.storage.save_links(added_links)
                            # Zapisz tekst START_URL
                            self.storage.save(text, metadata, url)
                            self.page_count += 1
                            logger.debug(f"Inkrementowano page_count: teraz {self.page_count}")
                            self.url_manager.mark_visited(url)
                        elif data_type in ['lektura_link', 'wiki_link'] and data:
                            # Dodaj linki do URLManager i uzyskaj faktycznie dodane linki
                            added_links = self.url_manager.add_extracted_url(origin_url, data)
                            # Zapisz tylko faktycznie dodane linki do extracted_links.txt
                            if added_links:
                                self.storage.save_links(added_links)
                            self.url_manager.mark_visited(url)
                        elif data_type == 'text' and data:
                            # Zapisz tekst do pliku .txt
                            text, metadata = data
                            self.storage.save(text, metadata, url)
                            self.page_count += 1
                            logger.debug(f"Inkrementowano page_count: teraz {self.page_count}")
                            self.url_manager.mark_visited(url)
                        else:
                            logger.warning(f"Parser zwrócił nieoczekiwany typ danych dla URL: {url}")
                            self.url_manager.mark_visited(url)

                    except ValueError as ve:
                        logger.error(f"Error unpacking data from parser for URL: {url} - {ve}")
                else:
                    logger.warning(f"No parser available for domain: {domain}")
                    self.url_manager.mark_visited(url)
            else:
                logger.warning(f"No content fetched for URL: {url}")
                self.url_manager.mark_visited(url)

            time.sleep(1)  # Polityka crawl-delay

        logger.info("Crawling completed.")
        logger.info(f"Visited {self.page_count} pages.")
