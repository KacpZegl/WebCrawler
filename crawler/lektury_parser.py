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
            # Najpierw próbujemy wyciągnąć linki /katalog/lektura/
            katalog_links = self.extract_katalog_links(soup, base_url)
            if katalog_links:
                return katalog_links, 'fallback_urls'
            else:
                # Jeśli brak, próbujemy wyciągnąć ogólne linki katalogowe
                all_katalog_links = self.extract_all_katalog_links(soup, base_url)
                if all_katalog_links:
                    return all_katalog_links, 'fallback_urls'
                else:
                    logger.warning(f"No related links found on START_URL: {base_url}")
                    return None, None
        else:
            # Sprawdzamy czy mamy treść lektury (.html)
            book_text_div = soup.find('div', id='book-text')
            if book_text_div:
                # Strona z treścią
                logger.info(f"Identified as content page: {base_url}")
                text, metadata = self.extract_content(soup, base_url)
                return (text, metadata), 'text'
            else:
                # Próba wyciągnięcia linków "czytaj online" (strony .html) ze stron /katalog/lektura/tytul/
                online_links = self.extract_online_links(soup, base_url)
                if online_links:
                    return online_links, 'fallback_urls'

                # Próba wyciągnięcia linków katalogowych do /katalog/lektura/
                katalog_links = self.extract_katalog_links(soup, base_url)
                if katalog_links:
                    return katalog_links, 'fallback_urls'

                # Ostatnia próba: ogólne linki katalogowe
                all_katalog_links = self.extract_all_katalog_links(soup, base_url)
                if all_katalog_links:
                    return all_katalog_links, 'fallback_urls'

                logger.warning(f"No fallback links found for {base_url}")
                return None, None

    def extract_katalog_links(self, soup, base_url):
        related_links = []
        # Szukamy linków do /katalog/lektura/... bez .html
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            if '/katalog/lektura/' in href:
                absolute_url = urljoin(base_url, href)
                parsed_url = urlparse(absolute_url)
                if parsed_url.netloc == urlparse(base_url).netloc:
                    if not parsed_url.path.endswith('.html'):
                        related_links.append(absolute_url)
        # Usuwamy duplikaty, jeśli wystąpią
        return list(set(related_links))

    def extract_all_katalog_links(self, soup, base_url):
        # Zwracamy wszelkie linki zawierające '/katalog/' bez względu na .html
        # przyda się do głębszej eksploracji katalogu
        related_links = []
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            if '/katalog/' in href:
                absolute_url = urljoin(base_url, href)
                parsed_url = urlparse(absolute_url)
                if parsed_url.netloc == urlparse(base_url).netloc:
                    if not parsed_url.path.endswith('.html'):
                        related_links.append(absolute_url)
        return list(set(related_links))

    def extract_online_links(self, soup, base_url):
        # Ekstrahuje linki "czytaj online" do .html ze stron /katalog/lektura/tytul/
        online_links = []
        for a_tag in soup.find_all('a', href=True, class_=re.compile(r'l-button.*media.*full')):
            link_text = a_tag.get_text(strip=True).lower()
            if 'czytaj online' in link_text or a_tag.find('i', class_='icon-eye'):
                href = a_tag['href']
                absolute_url = urljoin(base_url, href)
                parsed_url = urlparse(absolute_url)
                if not parsed_url.path.endswith('.html'):
                    absolute_url = absolute_url.rstrip('/') + '.html'
                online_links.append(absolute_url)
        return list(set(online_links))

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
        # Usuwamy elementy typu 'table_of_contents', 'editorial', footnotes, puste elementy
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

        # Usuwamy elementy theme-begin
        for theme_begin in book_text_div.find_all('a', class_='theme-begin'):
            theme_begin.decompose()

        # Usuwamy dodatkowe elementy, takie jak:
        # <div id="themes">, <div id="nota_red">, <div id="wltoc">, <div id="settings">, <div id="info">
        unwanted_ids = ['themes', 'nota_red', 'wltoc', 'settings', 'info']
        for uid in unwanted_ids:
            for div_to_remove in book_text_div.find_all('div', id=uid):
                div_to_remove.decompose()

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
        # Usuwanie przypisów typu [1], [2], [123]
        text = re.sub(r'\[\d+\]', '', text)

        # Znajdź pierwsze wystąpienie <p class="paragraph" i przytnij tekst, by zaczynał się od niego
        start_index = text.find('<p class="paragraph"')
        if start_index != -1:
            text = text[start_index:]

        # Usuwanie linii zawierających tylko kropki
        text = re.sub(r'^[.]+\s*$', '', text, flags=re.MULTILINE)

        # Usuwanie nadmiarowych spacji i formatowanie zdań
        text = re.sub(r'\s+', ' ', text).strip()
        text = text.replace('. ', '.\n')

        return text
