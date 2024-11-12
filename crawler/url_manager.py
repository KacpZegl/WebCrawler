from collections import deque
from urllib.parse import urlparse

class URLManager:
    def __init__(self, start_urls):
        self.to_visit = {}  # origin_url -> deque of URLs
        self.origin_order = deque()
        self.visited = set()
        
        for url in start_urls:
            self.to_visit[url] = deque([(url, url)])
            self.origin_order.append(url)

    def has_urls(self):
        return any(len(queue) > 0 for queue in self.to_visit.values())

    def get_next_url(self):
        num_origins = len(self.origin_order)
        for _ in range(num_origins):
            origin_url = self.origin_order[0]
            queue = self.to_visit.get(origin_url, deque())

            if queue:
                url_item = queue.popleft()
                self.origin_order.rotate(-1)
                return url_item
            else:
                self.origin_order.rotate(-1)

        return None

    def add_urls(self, origin_url, urls):
        if origin_url not in self.to_visit:
            self.to_visit[origin_url] = deque()
            self.origin_order.append(origin_url)
        
        for url in urls:
            if url not in self.visited and not self.is_in_queue(url):
                self.to_visit[origin_url].append((url, origin_url))

    def is_in_queue(self, url):
        for queue in self.to_visit.values():
            if any(url == item[0] for item in queue):
                return True
        return False

    def mark_visited(self, url):
        self.visited.add(url)

    def visited_count(self):
        return len(self.visited)
