import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import logging

logger = logging.getLogger('WebCrawler')

class LekturyParser:
    def parse(self, content, base_url):
        soup = BeautifulSoup(content, 'html.parser')

        if self.is_main_page(soup):
            logger.info(f"Identified as main page: {base_url}")
            lektura_url = self.extract_lektura_url(soup, base_url)
            if lektura_url:
                return [lektura_url], 'lektura_link'
            else:
                logger.warning(f"No lektura URL found on main page: {base_url}")
                return None, None
        elif self.is_content_page(soup):
            logger.info(f"Identified as content page: {base_url}")
            text, metadata = self.extract_content(soup, base_url)
            return (text, metadata), 'text'
        else:
            logger.warning(f"Unknown page type for URL: {base_url}")
            return None, None

    def is_main_page(self, soup):
        return bool(soup.find('ul', class_='l-aside__zbiory'))

    def is_content_page(self, soup):
        return bool(soup.find('div', id='book-text'))

    def extract_lektura_url(self, soup, base_url):
        ul = soup.find('ul', class_='l-aside__zbiory')
        if not ul:
            logger.warning("Missing <ul class='l-aside__zbiory'>.")
            return None

        first_li = ul.find('li')
        if first_li:
            a_tag = first_li.find('a', href=True)
            if a_tag:
                href = a_tag['href']
                if href.endswith('/'):
                    href = href[:-1] + '.html'
                else:
                    href = href + '.html'
                absolute_url = urljoin(base_url, href)
                logger.debug(f"Extracted lektura URL: {absolute_url}")
                return absolute_url
        logger.warning("No link found in the first <li> in <ul class='l-aside__zbiory'>.")
        return None

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
