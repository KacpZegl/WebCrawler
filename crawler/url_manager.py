# crawler/url_manager.py

from collections import deque
from urllib.parse import urlparse

class URLManager:
    def __init__(self, start_urls):
        self.start_urls = start_urls
        self.to_visit = {}
        self.visited = set()
        self.current_index = 0  # Indeks do round-robin

        for url in start_urls:
            domain = urlparse(url).netloc
            if domain not in self.to_visit:
                self.to_visit[domain] = deque()
            self.to_visit[domain].append((url, url))  # (url, origin_url)

    def has_urls(self):
        return any(len(queue) > 0 for queue in self.to_visit.values())

    def get_next_url(self):
        domains = list(self.to_visit.keys())
        num_domains = len(domains)
        attempts = 0
        while attempts < num_domains:
            domain = domains[self.current_index]
            queue = self.to_visit[domain]
            if len(queue) > 0:
                url_item = queue.popleft()
                # Przesuwamy indeks dla następnego wywołania
                self.current_index = (self.current_index + 1) % num_domains
                return url_item  # (url, origin_url)
            else:
                # Przesuwamy indeks, jeśli kolejka jest pusta
                self.current_index = (self.current_index + 1) % num_domains
                attempts += 1
        return None, None

    def add_urls(self, origin_url, urls):
        domain = urlparse(origin_url).netloc
        queue = self.to_visit.get(domain)
        if queue is not None:
            for url in urls:
                if url not in self.visited and not any(url == item[0] for item in queue):
                    queue.append((url, origin_url))

    def mark_visited(self, url):
        self.visited.add(url)

    def visited_count(self):
        return len(self.visited)
