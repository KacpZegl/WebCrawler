# modules/logger.py

import logging

# Konfiguracja loggera
logger = logging.getLogger('web_crawler')
logger.setLevel(logging.INFO)

# Konsola
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# Formatowanie
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)

# Dodanie handlera do loggera
logger.addHandler(console_handler)
