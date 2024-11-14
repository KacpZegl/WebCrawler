# crawler/robots.py

from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser
from modules.logger import logger
import requests

class RobotsHandler:
    def __init__(self):
        self.parsers = {}

    def can_fetch(self, url, user_agent):
        parsed_url = urlparse(url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        if base_url not in self.parsers:
            robots_url = urljoin(base_url, '/robots.txt')
            rp = RobotFileParser()
            try:
                rp.set_url(robots_url)
                rp.read()
                self.parsers[base_url] = rp
                logger.info(f"Fetched robots.txt from {robots_url}")
            except Exception as e:
                logger.error(f"Failed to fetch robots.txt from {robots_url}: {e}")
                self.parsers[base_url] = None

        rp = self.parsers.get(base_url)
        if rp:
            return rp.can_fetch(user_agent, url)
        else:
            return True
