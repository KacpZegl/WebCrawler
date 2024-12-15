#storage.py

import os
import re
from urllib.parse import urlparse, unquote
from modules.logger import logger

class Storage:
    def __init__(self):
        project_dir = os.path.dirname(os.path.dirname(__file__))
        self.data_dir = os.path.join(project_dir, 'data')
        os.makedirs(self.data_dir, exist_ok=True)
        self.links_file = os.path.join(self.data_dir, 'extracted_links.txt')
        self.saved_links = set()

        # Wczytaj istniejące linki, aby uniknąć duplikatów
        if os.path.exists(self.links_file):
            with open(self.links_file, 'r', encoding='utf-8') as file:
                for line in file:
                    self.saved_links.add(line.strip())

    def save(self, text, metadata, base_url):
        text = ''.join(c for c in text if c.isprintable() or c == '\n')
        lines = [line.rstrip() for line in text.splitlines()]
        text = '\n'.join(lines)

        filename = self.generate_filename(base_url, metadata)
        file_path = os.path.join(self.data_dir, filename + '.txt')

        metadata_lines = [
            f"URL: {metadata.get('URL', '')}",
            f"Title: {metadata.get('Title', '')}",
            f"Date: {metadata.get('Date', '')}",
            f"Author: {metadata.get('Author', '')}",
            f"Categories: {', '.join(metadata.get('Categories', []))}",
            f"Keywords: {', '.join(metadata.get('Keywords', []))}",
            f"Language: {metadata.get('Language', '')}",
            f"Content-Type: {metadata.get('Content-Type', '')}"
        ]
        metadata_text = '\n'.join(metadata_lines)

        full_text = metadata_text + '\n\n' + text

        try:
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(full_text)
            logger.info(f"Dodano tekst do {file_path}.")
        except IOError as e:
            logger.error(f"Błąd podczas zapisu do pliku {file_path}: {e}")

    def save_links(self, links):
        unique_links = [link for link in links if link not in self.saved_links]
        if not unique_links:
            logger.info("Brak nowych linków do zapisania.")
            return unique_links

        try:
            with open(self.links_file, 'a', encoding='utf-8') as file:
                for link in unique_links:
                    file.write(link + '\n')
                    self.saved_links.add(link)
            logger.info(f"Zapisano {len(unique_links)} linków do {self.links_file}.")
            return unique_links
        except IOError as e:
            logger.error(f"Błąd podczas zapisu linków do pliku {self.links_file}: {e}")
            return []

    def save_all_collected_links(self, links):
        all_links_file = os.path.join(self.data_dir, 'all_collected_links.txt')
        try:
            with open(all_links_file, 'w', encoding='utf-8') as file:
                for link in sorted(links):
                    file.write(link + '\n')
            logger.info(f"Zapisano {len(links)} linków do {all_links_file}.")
        except IOError as e:
            logger.error(f"Błąd podczas zapisu linków do {all_links_file}: {e}")

    def generate_filename(self, base_url, metadata):
        parsed_url = urlparse(base_url)
        domain = parsed_url.netloc

        if 'wolnelektury.pl' in domain or 'lektury.gov.pl' in domain:
            path = parsed_url.path
            path = re.sub(r'^/katalog/lektura/', '', path)
            path = path.rstrip('/').replace('.html', '')
            sanitized_path = self.sanitize_filename(path)
            filename = f"lektura-{sanitized_path}"
        elif 'wikipedia.org' in domain:
            article_name = parsed_url.path.split('/wiki/')[-1]
            article_name = unquote(article_name)
            sanitized_title = self.sanitize_filename(article_name)
            filename = f"wiki-{sanitized_title}"
        else:
            path = parsed_url.path
            path = re.sub(r'\.\w+$', '', path)
            sanitized_path = re.sub(r'[/-]', '_', path.strip('/'))
            filename = f"{sanitized_path}"

        return filename

    def sanitize_filename(self, name):
        name = name.strip().replace(' ', '_')
        return re.sub(r'[^\w\-_ąćęłńóśźżĄĆĘŁŃÓŚŹŻ]', '', name)

    def is_already_saved(self, base_url, metadata):
        filename = self.generate_filename(base_url, metadata)
        file_path = os.path.join(self.data_dir, filename + '.txt')
        return os.path.exists(file_path)
