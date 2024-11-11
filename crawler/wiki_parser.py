# crawler/wiki_parser.py

import re
from bs4 import BeautifulSoup, Comment
from urllib.parse import urljoin, urlparse

class WikiParser:
    def parse(self, content, base_url):
        soup = BeautifulSoup(content, 'html.parser')

        # Usuwanie skryptów, stylów i komentarzy HTML
        for element in soup(["script", "style"]):
            element.decompose()

        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()

        # Usuwanie odnośników do przypisów w tekście (superskryptowane numery)
        for ref in soup.find_all('sup', class_='reference'):
            ref.decompose()

        # Usuwanie elementów z klasami cytowań
        citation_classes = [
            'citation', 'citation-needed', 'citation book',
            'citation web', 'citation journal', 'cite', 'mw-empty-elt',
            'noprint Inline-Template', 'metadata'
        ]
        for citation_class in citation_classes:
            for element in soup.find_all(class_=citation_class):
                element.decompose()

        # Usuwanie elementów zawierających tekst "Sprawdź autora"
        for element in soup.find_all(string=lambda text: 'Sprawdź autora' in text):
            parent = element.find_parent()
            if parent:
                parent.decompose()
            else:
                element.extract()

        # Usuwanie elementów z atrybutem typeof="mw:File" i ich rodziców <li>
        for file_element in soup.find_all(attrs={'typeof': 'mw:File'}):
            # Usuwamy rodzica <li> lub inny element nadrzędny
            parent_li = file_element.find_parent('li')
            if parent_li:
                parent_li.decompose()
            else:
                # Jeśli nie ma rodzica <li>, usuwamy najbliższego rodzica
                parent = file_element.find_parent()
                if parent:
                    parent.decompose()
                else:
                    file_element.decompose()

        # Usuwanie niepożądanych elementów na podstawie klas
        for element in soup.find_all(class_=[
            'mw-editsection', 'navbox', 'vertical-navbox', 'infobox',
            'reference', 'noprint', 'Portal', 'stub', 'catlinks', 'printfooter',
            'mw-panel', 'mw-footer', 'mbox-small', 'sistersitebox'
        ]):
            element.decompose()

        # Usuwanie elementów na dole strony, takich jak linki kategorii i elementy interfejsu
        if catlinks := soup.find('div', id='catlinks'):
            catlinks.decompose()
        if footer := soup.find('footer', id='footer'):
            footer.decompose()
        if siteNotice := soup.find('div', id='siteNotice'):
            siteNotice.decompose()

        # Usuwanie sekcji: "Przypisy", "Bibliografia", "Linki zewnętrzne", itp.
        unwanted_sections = ['Przypisy', 'Bibliografia', 'Linki zewnętrzne', 'Uwagi', 'Zobacz też', 'Źródła']
        for heading in soup.find_all(['h2', 'h3', 'h4', 'h5', 'h6']):
            heading_text = heading.get_text().strip()
            heading_text = re.sub(r'\[.*?\]', '', heading_text)  # Usunięcie odnośników w nagłówkach
            if heading_text in unwanted_sections:
                # Usuwamy nagłówek sekcji i wszystkie następne elementy aż do następnego nagłówka tego samego poziomu
                next_node = heading.find_next_sibling()
                while next_node and not next_node.name in ['h2', 'h3', 'h4', 'h5', 'h6']:
                    to_remove = next_node
                    next_node = next_node.find_next_sibling()
                    to_remove.decompose()
                # Usuwamy sam nagłówek sekcji
                heading.decompose()

        # Usuwanie list przypisów oznaczonych klasą 'references'
        for references in soup.find_all(class_='references'):
            references.decompose()

        # Skupienie się na głównej treści artykułu
        main_content = soup.find('div', id='mw-content-text')
        if not main_content:
            # Jeśli nie znaleziono głównej treści, użyj całej zawartości
            main_content = soup

        data, metadata = self.extract_data(main_content, base_url, soup)
        return data, metadata

    def extract_data(self, content, base_url, soup):
        def clean_text(text, allow_numbers=False):
            text = re.sub(r'\s+', ' ', text).strip()
            if allow_numbers:
                allowed_chars = 'AĄBCĆDEĘFGHIJKLŁMNŃOÓPRSŚTUWYZŹŻaąbcćdeęfghijklłmnńoóprsśtuwyzźż0123456789:.,!?:/ '
            else:
                allowed_chars = 'AĄBCĆDEĘFGHIJKLŁMNŃOÓPRSŚTUWYZŹŻaąbcćdeęfghijklłmnńoóprsśtuwyzźż!? '
            text = ''.join(c for c in text if c in allowed_chars)
            if not allow_numbers:
                text = re.sub(r'(?<!\w)[\-.](?!\w)', '', text)
            return text

        markdown = []
        separator = "\n\n---\n\n"

        metadata = {}

        # URL
        metadata['URL'] = base_url

        # Tytuł
        title_tag = soup.find('title')
        if title_tag:
            title_text = clean_text(title_tag.get_text())
            metadata['Title'] = title_text
        else:
            metadata['Title'] = ''

        # Data
        last_modified = soup.find('li', id='footer-info-lastmod')
        if last_modified:
            last_modified_text = last_modified.get_text()
            date_match = re.search(r'ostatnio edytowano (.+)\.', last_modified_text)
            if date_match:
                date_text = date_match.group(1).strip()
                date_text = clean_text(date_text, allow_numbers=True)
                metadata['Date'] = date_text
            else:
                metadata['Date'] = ''
        else:
            metadata['Date'] = ''

        # Autor (zazwyczaj niedostępne w Wikipedii)
        metadata['Author'] = ''

        # Kategorie
        categories = []
        for cat_link in soup.select('#mw-normal-catlinks ul li a'):
            cat_text = clean_text(cat_link.get_text())
            categories.append(cat_text)
        metadata['Categories'] = categories

        # Słowa kluczowe
        keywords_meta = soup.find('meta', attrs={'name': 'keywords'})
        if keywords_meta and 'content' in keywords_meta.attrs:
            keywords = clean_text(keywords_meta['content'])
            metadata['Keywords'] = keywords.split(',')
        else:
            metadata['Keywords'] = []

        # Język
        html_tag = soup.find('html')
        if html_tag and 'lang' in html_tag.attrs:
            metadata['Language'] = html_tag['lang']
        else:
            metadata['Language'] = 'pl'

        # Typ treści
        metadata['Content-Type'] = 'Artykuł'

        # Blockquote (opcjonalne)
        blockquote = content.find('blockquote')
        if blockquote:
            blockquote_text = clean_text(blockquote.get_text())
            if blockquote_text:
                summary = f"> {blockquote_text}"
                markdown.append(summary)

        # Bieżący nagłówek
        current_heading = None

        # Przetwarzanie elementów treści
        content_elements = content.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'ul', 'ol'], recursive=True)
        for element in content_elements:
            # Pomijamy elementy znajdujące się w wykluczonych sekcjach
            if element.find_parent(class_='references'):
                continue

            if element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                heading_text = clean_text(element.get_text())
                if heading_text:
                    current_heading = heading_text
            elif element.name == 'p':
                paragraph = clean_text(element.get_text())
                if paragraph:
                    if current_heading:
                        markdown.append(f"### {current_heading}")
                        current_heading = None
                    markdown.append(paragraph)
            elif element.name in ['ul', 'ol']:
                # Sprawdzamy, czy lista nie jest częścią wykluczonych sekcji
                if element.find_parent(class_='references'):
                    continue
                list_items = []
                for li in element.find_all('li', recursive=False):
                    li_text = clean_text(li.get_text())
                    if li_text:
                        list_items.append(f"- {li_text}")
                if list_items:
                    if current_heading:
                        markdown.append(f"### {current_heading}")
                        current_heading = None
                    markdown.append("\n".join(list_items))

        # Łączenie treści markdown
        content_text = separator.join(markdown)

        return content_text, metadata

    def is_valid_url(self, url, base_url):
        parsed_base = urlparse(base_url)
        parsed_url = urlparse(url)
        # Akceptuj tylko URL-e z tej samej domeny i z przestrzeni głównej
        return (
            parsed_url.netloc == parsed_base.netloc
            and '/wiki/' in parsed_url.path
            and not '/wiki/Kategoria:' in parsed_url.path
            and not '/wiki/Specjalna:' in parsed_url.path
            and not '/wiki/Pomoc:' in parsed_url.path
            and not '/wiki/Plik:' in parsed_url.path
            and not '/wiki/Portal:' in parsed_url.path
            and not '/wiki/Dyskusja:' in parsed_url.path
            and not '/wiki/Szablon:' in parsed_url.path
        )
