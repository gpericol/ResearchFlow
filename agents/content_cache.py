#!/usr/bin/env python3
# agents/content_cache.py

import os
import json
import time
import hashlib
import logging
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse

# Importo i moduli specializzati
from .cache_handlers.file_handler import FileHandler
from .cache_handlers.url_detector import URLDetector
from .cache_handlers.pdf_extractor import PDFExtractor

# Configure logging
logger = logging.getLogger('content_cache')

class ContentCache:
    """
    Gestore della cache per i contenuti delle pagine web scaricate.
    Classe principale che coordina le operazioni di cache.
    """
    
    def __init__(self, cache_dir="cache"):
        """
        Inizializza il gestore della cache.
        
        Args:
            cache_dir (str): Directory per la cache dei contenuti scaricati
        """
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.cache_dir = os.path.join(base_dir, cache_dir)
        
        # Inizializza i gestori specializzati
        self.file_handler = FileHandler(self.cache_dir)
        self.url_detector = URLDetector()
        self.pdf_extractor = PDFExtractor()
        
        os.makedirs(self.cache_dir, exist_ok=True)
    
    def get_cache_path(self, url: str) -> str:
        """
        Ottiene il percorso del file di cache per un URL.
        
        Args:
            url (str): URL della pagina web
            
        Returns:
            str: Percorso del file di cache
        """
        return self.file_handler.get_cache_path(url)
    
    def get_content(self, url: str, scraper_func=None) -> str:
        """
        Ottiene il contenuto di una pagina web o di un PDF, utilizzando la cache se disponibile.
        
        Args:
            url (str): URL della pagina web o del PDF
            scraper_func (callable): Funzione per scaricare il contenuto se non in cache
            
        Returns:
            str: Contenuto estratto
        """
        cache_path = self.get_cache_path(url)
        
        # Prova a caricare dalla cache
        cached_content = self.file_handler.load_from_cache(url, cache_path)
        if cached_content is not None:
            return cached_content
        
        # Se non è in cache, verifica se è un PDF
        if self.url_detector.is_pdf_url(url):
            logger.info(f"Rilevato URL di tipo PDF: {url}")
            content = self.pdf_extractor.extract_pdf_text(url)
            # Salva nella cache
            self.file_handler.save_to_cache(url, cache_path, content)
            return content
        
        # Se non è un PDF, usa il normale scraper
        if not scraper_func:
            logger.error(f"URL non in cache e nessuna funzione di scraping fornita: {url}")
            return ""
            
        logger.info(f"Scaricamento contenuto per: {url}")
        content = scraper_func(url)
        
        # Salva nella cache
        self.file_handler.save_to_cache(url, cache_path, content)
        
        return content
    
    def list_cached_pages(self) -> List[Dict[str, Any]]:
        """
        Ottiene l'elenco di tutte le pagine nella cache.
        
        Returns:
            List[Dict[str, Any]]: Lista di metadati delle pagine nella cache
        """
        return self.file_handler.list_cached_pages()
    
    def clear_cache(self, older_than_days: Optional[int] = None) -> int:
        """
        Cancella la cache o rimuove i file più vecchi di un certo numero di giorni.
        
        Args:
            older_than_days (Optional[int]): Se specificato, rimuove solo i file più 
                                             vecchi di questo numero di giorni
            
        Returns:
            int: Numero di file rimossi dalla cache
        """
        return self.file_handler.clear_cache(older_than_days)