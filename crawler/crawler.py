import re
import requests
import time
from urllib.parse import urlparse
from crawler.wiki_parser import WikiParser
from crawler.lektury_parser import LekturyParser
from crawler.storage import Storage
from crawler.robots import RobotsHandler
from modules.logger import logger
from config import USER_AGENT, MAX_PAGES, EXTRACTED_PAGES_MAX, START_URLS
import os
from bs4 import BeautifulSoup

class WebCrawler:
    def __init__(self):
        self.storage = Storage()
        self.robots_handler = RobotsHandler()
        self.parsers = {
            'wolnelektury.pl': LekturyParser(USER_AGENT),
            'lektury.gov.pl': LekturyParser(USER_AGENT),
            'wikipedia.org': WikiParser(USER_AGENT),
        }
        self.visited = set()
        self.page_count = 0

        self.collected_links_wolnelektury = []
        self.collected_links_wikipedia = []
        self.collected_links_file = []  # Linki przetworzone w fazie plikowej

        self.wolnelektury_start = START_URLS[0]
        self.wikipedia_start = START_URLS[1]

        self.start_time = time.time()
        self.skipped_count = 0
        self.saved_count = 0
        self.ignored_count = 0  # Nowe pole: liczba ignorowanych linków

        self.ignored_paths = [
            '/katalog/daisy/',
            '/katalog/motyw/',
            '/katalog/nowe/',
            '/katalog/kolekcje/',
            '/katalog/autor/',
            '/katalog/audiobooki/'
        ]

    def is_ignored_link(self, url):
        parsed = urlparse(url)
        for ipath in self.ignored_paths:
            if parsed.path == ipath:
                return True
        return False

    def fetch(self, url):
        try:
            headers = {'User-Agent': USER_AGENT}
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                response.encoding = response.apparent_encoding
                return response.text
            else:
                logger.warning(f"HTTP error {response.status_code} while fetching {url}")
                self.skipped_count += 1
                return None
        except requests.RequestException as e:
            logger.error(f"Error fetching {url}: {e}")
            self.skipped_count += 1
            return None

    def get_parser(self, domain):
        if re.match(r'.*\.wikipedia\.org$', domain):
            return self.parsers.get('wikipedia.org')
        return self.parsers.get(domain)

    def start_crawling(self):
        # Faza 1: WolneLektury
        self.gather_links_from_domain(self.wolnelektury_start, 'wolnelektury')
        if not self.collected_links_wolnelektury:
            logger.warning("Nie zebrano żadnych linków z WolneLektury.")
        else:
            self.download_and_save_phase(self.collected_links_wolnelektury, "WolneLektury")

        # Faza 2: Wikipedia
        self.gather_links_from_domain(self.wikipedia_start, 'wikipedia')
        if not self.collected_links_wikipedia:
            logger.warning("Nie zebrano żadnych linków z Wikipedii.")
        else:
            self.download_and_save_phase(self.collected_links_wikipedia, "Wikipedia")

        # Faza 3: Linki z pliku
        self.process_links_from_file()

        all_links = set(self.collected_links_wolnelektury + self.collected_links_wikipedia + self.collected_links_file)
        self.storage.save_all_collected_links(all_links)

        # Pobranie statystyk z storage (zakładamy, że takie metody istnieją)
        overall_saved_texts = self.storage.get_saved_texts_count()
        overall_collected_links_count = self.storage.get_all_collected_links_count()

        not_saved_links_count = overall_collected_links_count - overall_saved_texts

        logger.info("Proces zakończony.")

        end_time = time.time()
        duration = end_time - self.start_time
        duration_minutes = duration / 60.0

        visited_count = len(self.visited)
        newly_saved_links_count = len(all_links)

        # Raport końcowy z dodatkowymi informacjami
        logger.info(f"Czas wykonywania programu: {duration:.2f} s ({duration_minutes:.2f} min)")
        logger.info(f"Ilość pominiętych linków: {self.skipped_count}")
        logger.info(f"Ilość odwiedzonych linków: {visited_count}")
        logger.info(f"Ilość ignorowanych stron: {self.ignored_count}")
        logger.info(f"Ilość nowo zapisanych linków do all_collected_links: {newly_saved_links_count}")
        logger.info(f"Ilość nowo zapisanych tekstów do plików txt: {self.saved_count}")
        logger.info(f"Ilość ogólnie zapisanych już tekstów: {overall_saved_texts}")
        logger.info(f"Ilość ogólnie zapisanych już linków w all_collected_links: {overall_collected_links_count}")
        logger.info(f"Ilość linków w all_collected_links, które jeszcze nie zostały zapisane do txt: {not_saved_links_count}")

    def gather_links_from_domain(self, start_url, domain_type):
        links_to_explore = [start_url]
        collected = 0

        while links_to_explore and collected < EXTRACTED_PAGES_MAX:
            url = links_to_explore.pop(0)

            if self.is_ignored_link(url):
                self.ignored_count += 1
                continue

            if url in self.visited:
                continue

            self.visited.add(url)

            domain = urlparse(url).netloc
            if not self.robots_handler.can_fetch(url, USER_AGENT):
                logger.info(f"Access denied by robots.txt: {url}")
                self.skipped_count += 1
                continue

            content = self.fetch(url)
            if not content:
                logger.warning(f"No content fetched for URL: {url}")
                continue

            parser = self.get_parser(domain)
            if not parser:
                logger.warning(f"No parser available for domain: {domain}")
                self.skipped_count += 1
                continue

            parse_result = parser.parse(content, url, is_start_url=(url == start_url))
            if not parse_result:
                logger.warning(f"Parser returned None for URL: {url}")
                self.skipped_count += 1
                continue

            data, data_type = parse_result

            if data_type == 'start_url':
                related_links, (text, metadata) = data
                for link in related_links:
                    if not self.is_ignored_link(link) and link not in self.visited:
                        links_to_explore.append(link)

            elif data_type == 'fallback_urls':
                for link in data:
                    if self.is_ignored_link(link):
                        self.ignored_count += 1
                        continue
                    if link not in self.visited:
                        links_to_explore.append(link)

            elif data_type == 'text':
                if domain_type == 'wolnelektury':
                    self.collected_links_wolnelektury.append(url)
                else:
                    self.collected_links_wikipedia.append(url)
                collected += 1
            else:
                logger.info(f"URL: {url} zwrócił nieoczekiwany typ danych: {data_type}. Ignoruję.")
                self.skipped_count += 1

            time.sleep(1)

    def get_additional_links_from_content(self, url, content, parser):
        soup = BeautifulSoup(content, 'html.parser')
        additional_links = []

        if hasattr(parser, 'extract_online_links'):
            online = parser.extract_online_links(soup, url)
            for link in online:
                if self.is_ignored_link(link):
                    self.ignored_count += 1
                elif link not in self.visited:
                    additional_links.append(link)

        if hasattr(parser, 'extract_katalog_links'):
            katalog = parser.extract_katalog_links(soup, url)
            for link in katalog:
                if self.is_ignored_link(link):
                    self.ignored_count += 1
                elif link not in self.visited:
                    additional_links.append(link)

        if hasattr(parser, 'extract_all_katalog_links'):
            all_kat = parser.extract_all_katalog_links(soup, url)
            for link in all_kat:
                if self.is_ignored_link(link):
                    self.ignored_count += 1
                elif link not in self.visited:
                    additional_links.append(link)

        if hasattr(parser, 'extract_related_links'):
            fallback = parser.extract_related_links(soup, url)
            for link in fallback:
                if self.is_ignored_link(link):
                    self.ignored_count += 1
                elif link not in self.visited:
                    additional_links.append(link)

        return list(set(additional_links))

    def download_and_save_phase(self, links, source_name):
        logger.info(f"Rozpoczynam pobieranie i zapisywanie treści z {len(links)} zebranych linków ({source_name}).")
        index = 0
        while index < len(links):
            if self.page_count >= MAX_PAGES:
                logger.info("Osiągnięto limit MAX_PAGES. Kończę przetwarzanie tekstów.")
                break

            url = links[index]

            if self.is_ignored_link(url):
                self.ignored_count += 1
                index += 1
                continue

            if url in self.visited:
                index += 1
                continue

            self.visited.add(url)

            if not self.robots_handler.can_fetch(url, USER_AGENT):
                logger.info(f"Access denied by robots.txt: {url}")
                self.skipped_count += 1
                index += 1
                continue

            content = self.fetch(url)
            if not content:
                logger.warning(f"No content fetched for URL: {url}")
                index += 1
                continue

            domain = urlparse(url).netloc
            parser = self.get_parser(domain)
            if not parser:
                logger.warning(f"No parser available for domain: {domain}")
                self.skipped_count += 1
                index += 1
                continue

            parse_result = parser.parse(content, url, is_start_url=False)
            if not parse_result:
                logger.warning(f"Parser zwrócił None dla URL: {url}")
                self.skipped_count += 1
                index += 1
                continue

            data, data_type = parse_result
            if data_type == 'text' and data:
                text, metadata = data
                if self.storage.is_already_saved(url, metadata):
                    logger.info(f"SKIP: Tekst dla linku {url} został już zapisany.")
                    self.skipped_count += 1
                    additional_links = self.get_additional_links_from_content(url, content, parser)
                    if additional_links:
                        links[index+1:index+1] = additional_links
                        logger.info(f"Dodano {len(additional_links)} dodatkowych linków z pomijanego linku.")
                    else:
                        logger.info("Brak dodatkowych linków do wyekstrahowania z pomijanego linku.")
                    index += 1
                    continue
                self.storage.save(text, metadata, url)
                self.page_count += 1
                self.saved_count += 1
                logger.debug(f"Inkrementowano page_count: teraz {self.page_count}")
            else:
                logger.info(f"URL: {url} nie zawiera tekstu do zapisania (data_type={data_type}). Ignoruję.")
                self.skipped_count += 1

            index += 1
            time.sleep(1)

        if self.page_count < MAX_PAGES:
            logger.info("Nie udało się osiągnąć MAX_PAGES, pomimo prób dodawania nowych linków z pomijanych stron.")

    def process_links_from_file(self):
        links_file = os.path.join(self.storage.data_dir, 'extracted_links.txt')
        if not os.path.exists(links_file):
            logger.error("Plik extracted_links.txt nie istnieje lub brak linków do przetworzenia.")
            return

        with open(links_file, 'r', encoding='utf-8') as f:
            file_links = [line.strip() for line in f if line.strip()]

        index = 0
        while index < len(file_links):
            if self.page_count >= MAX_PAGES:
                logger.info("Osiągnięto limit MAX_PAGES w fazie plikowej. Kończę przetwarzanie.")
                break

            url = file_links[index]

            if not url or self.is_ignored_link(url):
                if self.is_ignored_link(url):
                    self.ignored_count += 1
                index += 1
                continue

            if url in self.visited:
                index += 1
                continue

            self.visited.add(url)
            domain = urlparse(url).netloc

            if not self.robots_handler.can_fetch(url, USER_AGENT):
                logger.info(f"Access denied by robots.txt: {url}")
                self.skipped_count += 1
                index += 1
                continue

            content = self.fetch(url)
            if not content:
                logger.warning(f"No content fetched for URL: {url}")
                index += 1
                continue

            parser = self.get_parser(domain)
            if not parser:
                logger.warning(f"No parser available for domain: {domain}")
                self.skipped_count += 1
                index += 1
                continue

            parse_result = parser.parse(content, url, is_start_url=False)
            if not parse_result:
                logger.warning(f"Parser zwrócił None dla URL: {url}")
                self.skipped_count += 1
                index += 1
                continue

            data, data_type = parse_result
            if data_type == 'text' and data:
                text, metadata = data
                if self.storage.is_already_saved(url, metadata):
                    logger.info(f"SKIP: Tekst dla linku {url} został już zapisany.")
                    self.skipped_count += 1
                    additional_links = self.get_additional_links_from_content(url, content, parser)
                    # Filtrujemy ignorowane i odwiedzone
                    additional_links = [l for l in additional_links if not self.is_ignored_link(l) and l not in self.visited]
                    if additional_links:
                        links_to_add = []
                        for lnk in additional_links:
                            if self.is_ignored_link(lnk):
                                self.ignored_count += 1
                            elif lnk not in self.visited:
                                links_to_add.append(lnk)
                        if links_to_add:
                            file_links[index+1:index+1] = links_to_add
                            logger.info(f"Dodano {len(links_to_add)} dodatkowych linków z pomijanego linku.")
                    else:
                        logger.info("Brak dodatkowych linków do wyekstrahowania z pomijanego linku.")
                    index += 1
                    continue
                self.storage.save(text, metadata, url)
                self.page_count += 1
                self.saved_count += 1
                self.collected_links_file.append(url)
                logger.debug(f"Inkrementowano page_count: teraz {self.page_count}")
            else:
                logger.info(f"URL: {url} nie zawiera tekstu do zapisania (data_type={data_type}). Ignoruję.")
                self.skipped_count += 1

            index += 1
            time.sleep(1)

        if self.page_count < MAX_PAGES:
            logger.info("Nie udało się osiągnąć MAX_PAGES w fazie plikowej, pomimo prób dodawania nowych linków z pomijanych stron.")
