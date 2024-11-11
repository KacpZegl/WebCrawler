# crawler/robots.py

import requests
import time
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser
from modules.logger import logger

class RobotsHandler:
    def __init__(self):
        self.robots_parsers = {}

    def can_fetch(self, url, user_agent):
        parsed_url = urlparse(url)
        domain = parsed_url.scheme + '://' + parsed_url.netloc
        robots_url = domain + '/robots.txt'

        if domain not in self.robots_parsers:
            parser = RobotFileParser()
            parser.set_url(robots_url)
            try:
                parser.read()
                self.robots_parsers[domain] = parser
            except Exception as e:
                logger.error(f"Error reading robots.txt from {robots_url}: {e}")
                # Jeśli nie można odczytać robots.txt, lepiej zablokować dostęp
                return False

            # Szanujemy opóźnienie crawl rate, jeśli jest określone
            crawl_delay = parser.crawl_delay(user_agent)
            if crawl_delay:
                time.sleep(crawl_delay)

        else:
            parser = self.robots_parsers[domain]

        return parser.can_fetch(user_agent, url)
