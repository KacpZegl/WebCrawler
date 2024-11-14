# crawler/parser_base.py

import requests
from urllib.parse import urlparse
from modules.logger import logger

class ParserBase:
    def __init__(self, user_agent):
        self.headers = {'User-Agent': user_agent}

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

    def parse(self, content, base_url, is_start_url):
        raise NotImplementedError("Metoda parse musi być zaimplementowana przez klasę potomną.")

    def get_related_links(self, base_url):
        raise NotImplementedError("Metoda get_related_links musi być zaimplementowana przez klasę potomną.")
