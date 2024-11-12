# modules/logger.py

import logging

def setup_logger():
    logger = logging.getLogger('WebCrawler')
    logger.setLevel(logging.DEBUG)  # Ustawienie globalnego poziomu na DEBUG

    # Konsola handler - tylko INFO i wyższe
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)

    # Plik handler - DEBUG i wyższe
    fh = logging.FileHandler('crawler.log')
    fh.setLevel(logging.DEBUG)

    # Formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    fh.setFormatter(formatter)

    # Dodaj handler tylko jeśli nie zostały dodane wcześniej
    if not logger.handlers:
        logger.addHandler(ch)
        logger.addHandler(fh)
    return logger

logger = setup_logger()
