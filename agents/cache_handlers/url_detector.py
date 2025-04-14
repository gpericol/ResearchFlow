#!/usr/bin/env python3
# agents/cache_handlers/url_detector.py

import logging
from urllib.parse import urlparse

logger = logging.getLogger('content_cache.url_detector')

class URLDetector:
    """
    Classe per identificare il tipo di URL (PDF, HTML, ecc).
    """
    
    def is_pdf_url(self, url: str) -> bool:
        """
        Verifica se un URL punta a un file PDF.
        
        Args:
            url (str): URL da verificare
            
        Returns:
            bool: True se l'URL punta a un PDF, False altrimenti
        """
        # Controlla l'estensione nell'URL
        parsed_url = urlparse(url)
        path = parsed_url.path.lower()
        
        # Se il percorso termina con .pdf, è probabilmente un PDF
        if path.endswith('.pdf'):
            return True
            
        # Controlla anche i parametri (per URL dinamici che generano PDF)
        return 'pdf' in parsed_url.query.lower() and 'pdf=true' in parsed_url.query.lower()