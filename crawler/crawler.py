import re
import requests
import time
from crawler.url_manager import URLManager
from crawler.wiki_parser import WikiParser
from crawler.lektury_parser import LekturyParser
from crawler.storage import Storage
from crawler.robots import RobotsHandler
from modules.logger import logger
from config import USER_AGENT, MAX_PAGES
from urllib.parse import urlparse

class WebCrawler:
    def __init__(self, start_urls, max_pages):
        self.url_manager = URLManager(start_urls)
        self.parsers = {
            'wolnelektury.pl': LekturyParser(),
            'lektury.gov.pl': LekturyParser(),
        }
        self.storage = Storage()
        self.robots_handler = RobotsHandler()
        self.max_pages = max_pages
        self.headers = {
            'User-Agent': USER_AGENT
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

    def get_parser(self, domain):
        if re.match(r'.*\.wikipedia\.org$', domain):
            return WikiParser()
        return self.parsers.get(domain)

    def start_crawling(self):
        page_count = 0
        while self.url_manager.has_urls() and page_count < self.max_pages:
            next_item = self.url_manager.get_next_url()
            if next_item is None:
                break
            url, origin_url = next_item
            if url in self.url_manager.visited:
                continue
            logger.info(f"Fetching: {url} (Origin: {origin_url})")

            domain = urlparse(url).netloc

            if not self.robots_handler.can_fetch(url, USER_AGENT):
                logger.info(f"Access denied by robots.txt: {url}")
                continue

            content = self.fetch(url)
            if content:
                parser = self.get_parser(domain)
                if parser:
                    try:
                        parse_result = parser.parse(content, url)
                        if not isinstance(parse_result, tuple) or len(parse_result) != 2:
                            logger.error(f"Parser returned unexpected format for URL: {url}")
                            continue
                        data, data_type = parse_result

                        if data_type == 'lektura_link' and data:
                            remaining = self.max_pages - page_count
                            if remaining > 0:
                                self.url_manager.add_urls(url, data[:remaining])
                            self.url_manager.mark_visited(url)
                        elif data_type == 'text' and data:
                            text, metadata = data
                            self.storage.save(text, metadata, url)
                            page_count += 1
                            self.url_manager.mark_visited(url)
                        else:
                            logger.warning(f"Parser returned no data for URL: {url}")

                    except ValueError as ve:
                        logger.error(f"Error unpacking data from parser for URL: {url} - {ve}")
                else:
                    logger.warning(f"No parser available for domain: {domain}")
            else:
                logger.warning(f"No content fetched for URL: {url}")

            time.sleep(1)

        logger.info("Crawling completed.")
        logger.info(f"Visited {page_count} pages.")
