# modules/logger.py

import logging
import os

# Utwórz logger
logger = logging.getLogger('WebCrawler')
logger.setLevel(logging.DEBUG)  # Ustaw poziom logowania na DEBUG dla pliku

# Utwórz formatery
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Utwórz handler dla pliku
project_dir = os.path.dirname(os.path.dirname(__file__))
log_file = os.path.join(project_dir, 'crawler.log')
file_handler = logging.FileHandler(log_file)
file_handler.setLevel(logging.DEBUG)  # Zapisuj wszystkie logi do pliku
file_handler.setFormatter(formatter)

# Utwórz handler dla konsoli
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)  # Wyświetlaj tylko INFO i wyższe na konsoli
console_handler.setFormatter(formatter)

# Dodaj handlery do loggera
logger.addHandler(file_handler)
logger.addHandler(console_handler)
