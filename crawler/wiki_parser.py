import re
from bs4 import BeautifulSoup, Comment
from urllib.parse import urlparse, urljoin
import logging

logger = logging.getLogger('WebCrawler')

class WikiParser:
    def parse(self, content, base_url):
        soup = BeautifulSoup(content, 'html.parser')

        for element in soup(["script", "style"]):
            element.decompose()

        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()

        self.remove_unwanted_elements(soup)

        content_div = soup.find('div', id='mw-content-text')
        if not content_div:
            logger.warning(f"Brak głównej treści na stronie {base_url}")
            return None, None

        text, metadata = self.extract_data(content_div, base_url, soup)

        if not isinstance(text, str) or not isinstance(metadata, dict):
            logger.error(f"Extracted data types are incorrect for URL: {base_url}")
            return None, None

        return (text, metadata), 'text'

    def remove_unwanted_elements(self, soup):
        for ref in soup.find_all('sup', class_='reference'):
            ref.decompose()

        unwanted_classes = [
            'navbox', 'vertical-navbox', 'infobox', 'metadata', 'ambox',
            'hatnote', 'mbox-small', 'sistersitebox', 'thumb', 'gallery',
            'reflist', 'portal', 'noprint', 'stub', 'mw-editsection', 'toc'
        ]
        for class_name in unwanted_classes:
            for element in soup.find_all(class_=class_name):
                element.decompose()

        unwanted_sections = [
            'Przypisy', 'Bibliografia', 'Linki zewnętrzne', 'Uwagi',
            'Zobacz też', 'Źródła', 'Literatura', 'Galeria', 'Nagrody'
        ]
        for heading in soup.find_all(['h2', 'h3', 'h4', 'h5', 'h6']):
            heading_text = heading.get_text().strip()
            heading_text = re.sub(r'\[.*?\]', '', heading_text)
            if heading_text in unwanted_sections:
                next_node = heading.find_next_sibling()
                while next_node and not next_node.name in ['h2', 'h3', 'h4', 'h5', 'h6']:
                    to_remove = next_node
                    next_node = next_node.find_next_sibling()
                    to_remove.decompose()
                heading.decompose()

        if catlinks := soup.find('div', id='catlinks'):
            catlinks.decompose()
        if footer := soup.find('footer', id='footer'):
            footer.decompose()
        if siteNotice := soup.find('div', id='siteNotice'):
            siteNotice.decompose()

    def extract_data(self, content_div, base_url, soup):
        def clean_text(text):
            text = re.sub(r'\s+', ' ', text).strip()
            return text

        metadata = {}

        metadata['URL'] = base_url

        title_tag = soup.find('h1', id='firstHeading')
        metadata['Title'] = clean_text(title_tag.get_text()) if title_tag else ''

        last_modified = soup.find('li', id='footer-info-lastmod')
        if last_modified:
            last_modified_text = last_modified.get_text()
            date_match = re.search(r'ostatnio edytowano (.+)\.', last_modified_text)
            if date_match:
                metadata['Date'] = clean_text(date_match.group(1))
            else:
                metadata['Date'] = ''
        else:
            metadata['Date'] = ''

        metadata['Author'] = ''

        categories = []
        for cat_link in soup.select('#mw-normal-catlinks ul li a'):
            cat_text = clean_text(cat_link.get_text())
            categories.append(cat_text)
        metadata['Categories'] = categories

        metadata['Keywords'] = []

        html_tag = soup.find('html')
        metadata['Language'] = html_tag.get('lang', 'pl') if html_tag else 'pl'

        metadata['Content-Type'] = 'Artykuł'

        text_elements = content_div.find_all(['p', 'h2', 'h3', 'h4', 'h5', 'h6'], recursive=True)
        content_text = ''
        for element in text_elements:
            if element.name in ['h2', 'h3', 'h4', 'h5', 'h6']:
                heading_text = clean_text(element.get_text())
                if heading_text:
                    content_text += f"\n\n### {heading_text}\n\n"
            elif element.name == 'p':
                paragraph_text = clean_text(element.get_text())
                if paragraph_text:
                    content_text += f"{paragraph_text}\n\n"

        content_text = content_text.strip()

        return content_text, metadata

    def is_valid_url(self, url, base_url):
        parsed_base = urlparse(base_url)
        parsed_url = urlparse(url)
        return (
            parsed_url.netloc == parsed_base.netloc
            and '/wiki/' in parsed_url.path
            and not re.search(r'/wiki/(Kategoria|Specjalna|Pomoc|Plik|Portal|Dyskusja|Szablon|Wikipedia):', parsed_url.path, re.IGNORECASE)
        )
