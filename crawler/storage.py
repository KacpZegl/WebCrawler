# crawler/storage.py

import os
import re
import hashlib
from urllib.parse import urlparse, unquote

class Storage:
    def __init__(self):
        # Ścieżka do katalogu danych
        project_dir = os.path.dirname(os.path.dirname(__file__))
        self.data_dir = os.path.join(project_dir, 'data')
        os.makedirs(self.data_dir, exist_ok=True)

    def save(self, text, metadata, base_url):
        # Usunięcie nieczytelnych znaków, zachowując znaki nowej linii
        text = ''.join(c for c in text if c.isprintable() or c == '\n')
        # Usunięcie nadmiarowych spacji na końcu linii
        lines = [line.rstrip() for line in text.splitlines()]
        text = '\n'.join(lines)

        # Generowanie nazwy pliku na podstawie domeny i nazwy artykułu
        filename = self.generate_filename(base_url)

        file_path = os.path.join(self.data_dir, filename + '.txt')

        # Przygotowanie metadanych do zapisu
        metadata_lines = []
        metadata_lines.append(f"URL: {metadata.get('URL', '')}")
        metadata_lines.append(f"Title: {metadata.get('Title', '')}")
        metadata_lines.append(f"Date: {metadata.get('Date', '')}")
        metadata_lines.append(f"Author: {metadata.get('Author', '')}")
        metadata_lines.append(f"Categories: {', '.join(metadata.get('Categories', []))}")
        metadata_lines.append(f"Keywords: {', '.join(metadata.get('Keywords', []))}")
        metadata_lines.append(f"Language: {metadata.get('Language', '')}")
        metadata_lines.append(f"Content-Type: {metadata.get('Content-Type', '')}")

        metadata_text = '\n'.join(metadata_lines)

        # Połączenie metadanych i treści
        full_text = metadata_text + '\n\n' + text

        # Zapisanie tekstu do pliku
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(full_text)
        print(f"Dodano tekst do {file_path}.")

    def generate_filename(self, base_url):
        parsed_url = urlparse(base_url)
        domain = parsed_url.netloc
        path = parsed_url.path

        # Wyodrębnienie nazwy artykułu z URL
        article_name = os.path.basename(path)
        article_name = unquote(article_name)  # Dekodowanie znaków URL (np. %C5%81 -> Ł)

        # Oczyszczenie nazwy artykułu
        article_name = self.sanitize_filename(article_name)

        # Ustalenie prefiksu na podstawie domeny
        if 'wikipedia.org' in domain:
            prefix = 'wiki-'
        elif 'lektury.gov.pl' in domain:
            prefix = 'lektura-'
        else:
            prefix = ''

        filename = f"{prefix}{article_name}"
        return filename

    def sanitize_filename(self, name):
        # Usuwanie niedozwolonych znaków w nazwie pliku
        name = name.strip().replace(' ', '_')
        return re.sub(r'[^\w\-_]', '', name)
