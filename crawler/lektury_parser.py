# crawler/lektury_parser.py

import re
import requests
from bs4 import BeautifulSoup
from ebooklib import epub
from io import BytesIO
from modules.logger import logger
from urllib.parse import urljoin, urlparse

class LekturyParser:
    def parse(self, content, base_url):
        # Zapisz pobrany HTML do pliku dla debugowania (opcjonalnie)
        # with open('fetched_lektura_page.html', 'w', encoding='utf-8') as f:
        #     f.write(content)
        
        # Parse the HTML content to extract the title and author
        title, author = self.extract_title_author(content)
        if not title:
            logger.warning(f"Could not extract title from page: {base_url}")
            return None, None

        # Generowanie slugu na podstawie tytułu i autora
        slug = self.generate_slug(title, author)
        if not slug:
            logger.warning(f"Could not generate slug for title: {title}")
            return None, None

        # Tworzenie bezpośredniego linku do pliku EPUB
        epub_url = f"https://wolnelektury.pl/media/book/epub/{slug}.epub"
        logger.info(f"Generated EPUB URL: {epub_url}")

        # Pobranie i wyodrębnienie tekstu z pliku EPUB
        text = self.download_and_extract_epub(epub_url)
        if not text:
            logger.warning(f"Could not download or extract text from EPUB file: {epub_url}")
            return None, None

        # Czyszczenie tekstu
        data = self.clean_text(text)

        # Przygotowanie metadanych
        metadata = self.extract_metadata(title, author, base_url)

        return data, metadata

    def extract_title_author(self, html_content):
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Przykładowe selektory - dostosuj je do rzeczywistej struktury strony
        # Zakładam, że tytuł jest w tagu <h1> z klasą 'title'
        # a autor w tagu <a> z klasą 'author'
        title_tag = soup.find('h1', class_='title')
        author_tag = soup.find('a', class_='author')
        
        title = title_tag.get_text(strip=True) if title_tag else None
        author = author_tag.get_text(strip=True) if author_tag else None

        return title, author

    def generate_slug(self, title, author):
        if not title:
            return None

        # Funkcja do usuwania polskich znaków
        def remove_polish_characters(text):
            polish_chars = {
                'ą': 'a', 'ć': 'c', 'ę': 'e', 'ł': 'l', 'ń': 'n',
                'ó': 'o', 'ś': 's', 'ź': 'z', 'ż': 'z',
                'Ą': 'A', 'Ć': 'C', 'Ę': 'E', 'Ł': 'L', 'Ń': 'N',
                'Ó': 'O', 'Ś': 'S', 'Ź': 'Z', 'Ż': 'Z'
            }
            return ''.join(polish_chars.get(c, c) for c in text)

        # Usunięcie polskich znaków z tytułu i autora
        title_clean = remove_polish_characters(title.lower())
        author_clean = remove_polish_characters(author.lower()) if author else ''

        # Zamiana spacji i znaków specjalnych na myślniki
        title_slug = re.sub(r'[^a-z0-9]+', '-', title_clean).strip('-')
        author_slug = re.sub(r'[^a-z0-9]+', '-', author_clean).strip('-') if author_clean else ''

        if author_slug:
            slug = f"{author_slug}-{title_slug}"
        else:
            slug = title_slug

        return slug

    def download_and_extract_epub(self, epub_url):
        try:
            response = requests.get(epub_url, timeout=20)
            if response.status_code == 200:
                book = epub.read_epub(BytesIO(response.content))
                text = ''
                for item in book.get_items():
                    if item.get_type() == epub.ITEM_DOCUMENT:
                        content = item.get_content().decode('utf-8', errors='ignore')
                        soup = BeautifulSoup(content, 'html.parser')
                        text += soup.get_text(separator='\n')
                return text
            else:
                logger.warning(f"Failed to download EPUB file: {epub_url} (Status Code: {response.status_code})")
        except Exception as e:
            logger.error(f"Error downloading or parsing EPUB file: {e}")
        return None

    def clean_text(self, text):
        # Usuwanie nadmiarowych białych znaków
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def extract_metadata(self, title, author, base_url):
        metadata = {}
        metadata['URL'] = base_url
        metadata['Title'] = title
        metadata['Author'] = author if author else ''
        metadata['Date'] = ''  # Możesz dodać logikę do ekstrakcji daty, jeśli jest dostępna
        metadata['Categories'] = []  # Możesz dodać logikę do ekstrakcji kategorii, jeśli jest dostępna
        metadata['Keywords'] = []  # Możesz dodać logikę do ekstrakcji słów kluczowych, jeśli jest dostępna
        metadata['Language'] = 'pl'
        metadata['Content-Type'] = 'Lektura'
        return metadata
