# crawler/url_manager.py

from collections import deque
from modules.logger import logger

class URLManager:
    def __init__(self, start_urls, extracted_pages_max):
        self.start_urls = start_urls
        self.extracted_pages_max = extracted_pages_max
        self.start_queue = deque(start_urls)  # Kolejka START_URLS
        self.extracted_queues = {url: deque() for url in start_urls}  # Kolejki EXTRACTED_URLS per START_URL
        self.visited = set()
        self.in_queue = set(start_urls)  # Zestaw do szybkiego sprawdzania obecności URL-i
        self.origin_urls = list(start_urls)  # Lista origin_urls do round-robin
        self.last_origin_index = -1  # Indeks ostatniego origin_url użytego w round-robin
        self.extracted_counts = {url: 0 for url in start_urls}  # Liczba ekstraktowanych linków per START_URL

    def has_urls(self):
        # Sprawdź, czy są URL-i do odwiedzenia w start_queue lub extracted_queues
        if self.start_queue:
            return True
        for queue in self.extracted_queues.values():
            if queue:
                return True
        return False

    def get_next_url(self):
        # Faza 1: Przetwarzanie START_URLS
        if self.start_queue:
            url = self.start_queue.popleft()
            self.in_queue.remove(url)
            logger.debug(f"Pobrano URL z start_queue: {url}")
            return (url, url)  # origin_url jest samym URL-em

        # Faza 2: Naprzemienne przetwarzanie EXTRACTED_URLS w round-robin
        origin_count = len(self.origin_urls)
        for i in range(origin_count):
            next_index = (self.last_origin_index + 1 + i) % origin_count
            origin_url = self.origin_urls[next_index]
            queue = self.extracted_queues[origin_url]
            if queue:
                url = queue.popleft()
                self.in_queue.remove(url)
                self.last_origin_index = next_index
                logger.debug(f"Pobrano URL z extracted_queues ({origin_url}): {url}")
                return (url, origin_url)

        return None

    def add_extracted_url(self, origin_url, urls):
        added_links = []
        if origin_url not in self.extracted_counts:
            self.extracted_counts[origin_url] = 0

        for url in urls:
            if self.extracted_counts[origin_url] >= self.extracted_pages_max:
                logger.debug(f"Osiągnięto limit ekstrakcji dla START_URL: {origin_url}")
                break  # Osiągnięto limit ekstrakcji dla tego START_URL
            if url not in self.visited and url not in self.in_queue:
                self.extracted_queues[origin_url].append(url)
                self.in_queue.add(url)
                self.extracted_counts[origin_url] += 1
                added_links.append(url)
                logger.debug(f"Dodano link: {url} do kolejki EXTRACTED_URLS dla START_URL: {origin_url}")
        return added_links

    def mark_visited(self, url):
        self.visited.add(url)
        logger.debug(f"Oznaczono jako odwiedzony: {url}")
