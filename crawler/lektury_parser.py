# crawler/lektury_parser.py

import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import logging
from crawler.parser_base import ParserBase

logger = logging.getLogger('WebCrawler')

class LekturyParser(ParserBase):
    def parse(self, content, base_url, is_start_url):
        soup = BeautifulSoup(content, 'html.parser')

        if is_start_url:
            logger.info(f"Identified as START_URL: {base_url}")
            related_links = self.extract_related_links(soup, base_url)
            text, metadata = self.extract_content(soup, base_url)
            if related_links or text:
                return (related_links, (text, metadata)), 'start_url'
            else:
                logger.warning(f"No related links or text found on START_URL: {base_url}")
                return None, None
        elif self.is_content_page(soup):
            logger.info(f"Identified as content page: {base_url}")
            text, metadata = self.extract_content(soup, base_url)
            return (text, metadata), 'text'
        else:
            logger.warning(f"Unknown page type for URL: {base_url}")
            return None, None

    def is_content_page(self, soup):
        return bool(soup.find('div', id='book-text'))

    def extract_related_links(self, soup, base_url):
        related_links = []
        ul = soup.find('ul', class_='l-aside__zbiory')
        if ul:
            for li in ul.find_all('li'):
                a_tag = li.find('a', href=True)
                if a_tag:
                    href = a_tag['href']
                    absolute_url = urljoin(base_url, href)
                    # Transformacja linków z wolnelektury.pl, aby kończyły się na .html
                    parsed_url = urlparse(absolute_url)
                    if 'wolnelektury.pl' in parsed_url.netloc:
                        if not parsed_url.path.endswith('.html'):
                            absolute_url = absolute_url.rstrip('/') + '.html'
                            logger.debug(f"Przekształcono link do .html: {absolute_url}")
                    if self.is_valid_url(absolute_url, base_url):
                        related_links.append(absolute_url)
        return related_links

    def extract_content(self, soup, base_url):
        book_text_div = soup.find('div', id='book-text')
        if not book_text_div:
            logger.warning(f"Missing <div id='book-text'> on page {base_url}")
            return "", {}

        self.remove_unwanted_elements(book_text_div)

        text = self.clean_text(book_text_div.get_text(separator='\n', strip=True))
        metadata = self.extract_metadata(soup, base_url)

        return text.strip(), metadata

    def remove_unwanted_elements(self, book_text_div):
        for toc in book_text_div.find_all(class_='table_of_contents'):
            toc.decompose()

        for editorial_note in book_text_div.find_all('div', class_='editorial'):
            editorial_note.decompose()

        unwanted_phrases = [
            "Informacja o zmianach we",
            "Spis treści",
        ]
        for p in book_text_div.find_all(['p', 'div']):
            text = p.get_text(strip=True)
            if any(text.startswith(phrase) for phrase in unwanted_phrases):
                p.decompose()

        for footnote in book_text_div.find_all('div', class_='footnotes'):
            footnote.decompose()

        for ed_footnote in book_text_div.find_all(['p', 'div']):
            text = ed_footnote.get_text(strip=True)
            if '[przypis edytorski]' in text:
                ed_footnote.decompose()

        for element in book_text_div.find_all():
            if not element.get_text(strip=True):
                element.decompose()

    def extract_metadata(self, soup, base_url):
        metadata = {}

        metadata['URL'] = base_url

        title_tag = soup.find('h1', class_='chapter-title')
        if title_tag:
            metadata['Title'] = self.clean_text(title_tag.get_text())
        else:
            metadata['Title'] = ''

        author_tag = soup.find('a', class_='author')
        if author_tag:
            metadata['Author'] = self.clean_text(author_tag.get_text())
        else:
            metadata['Author'] = ''

        metadata['Categories'] = []
        metadata['Keywords'] = []

        html_tag = soup.find('html')
        if html_tag and 'lang' in html_tag.attrs:
            metadata['Language'] = html_tag['lang']
        else:
            metadata['Language'] = 'pl'

        metadata['Content-Type'] = 'Lektura'

        return metadata

    def clean_text(self, text):
        text = re.sub(r'\s+', ' ', text).strip()
        text = text.replace('. ', '.\n')
        return text

    def is_valid_url(self, url, base_url):
        parsed_base = urlparse(base_url)
        parsed_url = urlparse(url)
        return (
            parsed_url.netloc == parsed_base.netloc
            and '/katalog/lektura/' in parsed_url.path
            and not re.search(r'/katalog/lektura/(wstep|plik|kategoria|specjalna|pomoc|portal|dyskusja|szablon):', parsed_url.path, re.IGNORECASE)
        )
