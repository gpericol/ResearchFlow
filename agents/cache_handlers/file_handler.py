#!/usr/bin/env python3
# agents/cache_handlers/file_handler.py

import os
import json
import time
import hashlib
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger('content_cache.file_handler')

class FileHandler:
    """
    Gestore delle operazioni di file per la cache.
    """
    
    def __init__(self, cache_dir: str):
        """
        Inizializza il gestore dei file.
        
        Args:
            cache_dir (str): Directory per la cache dei contenuti scaricati
        """
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)
    
    def get_cache_path(self, url: str) -> str:
        """
        Ottiene il percorso del file di cache per un URL.
        
        Args:
            url (str): URL della pagina web
            
        Returns:
            str: Percorso del file di cache
        """
        url_hash = hashlib.md5(url.encode()).hexdigest()
        return os.path.join(self.cache_dir, f"{url_hash}.json")
    
    def load_from_cache(self, url: str, cache_path: str) -> Optional[str]:
        """
        Carica il contenuto dalla cache se disponibile.
        
        Args:
            url (str): URL della pagina web
            cache_path (str): Percorso del file di cache
            
        Returns:
            Optional[str]: Contenuto dalla cache o None se non disponibile
        """
        if not os.path.exists(cache_path):
            return None
            
        logger.info(f"Caricamento contenuto dalla cache per: {url}")
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            return cache_data.get('content', '')
        except Exception as e:
            logger.error(f"Errore nel caricamento della cache per {url}: {e}")
            return None
    
    def save_to_cache(self, url: str, cache_path: str, content: str) -> None:
        """
        Salva il contenuto scaricato nella cache.
        
        Args:
            url (str): URL della pagina web
            cache_path (str): Percorso del file di cache
            content (str): Contenuto da salvare
        """
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'url': url,
                    'timestamp': time.time(),
                    'content': content
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Errore nel salvataggio della cache per {url}: {e}")
    
    def list_cached_pages(self) -> List[Dict[str, Any]]:
        """
        Ottiene l'elenco di tutte le pagine nella cache.
        
        Returns:
            List[Dict[str, Any]]: Lista di metadati delle pagine nella cache
        """
        cached_pages = []
        
        if os.path.exists(self.cache_dir):
            for file_name in os.listdir(self.cache_dir):
                if (file_name.endswith('.json')):
                    file_path = os.path.join(self.cache_dir, file_name)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            cache_data = json.load(f)
                            
                            cached_pages.append({
                                'url': cache_data.get('url', ''),
                                'timestamp': cache_data.get('timestamp', 0),
                                'size': len(cache_data.get('content', '')),
                                'cache_file': file_name
                            })
                    except Exception as e:
                        logger.error(f"Errore nella lettura del file cache {file_name}: {e}")
        
        return cached_pages
    
    def clear_cache(self, older_than_days: Optional[int] = None) -> int:
        """
        Cancella la cache o rimuove i file più vecchi di un certo numero di giorni.
        
        Args:
            older_than_days (Optional[int]): Se specificato, rimuove solo i file più 
                                             vecchi di questo numero di giorni
            
        Returns:
            int: Numero di file rimossi dalla cache
        """
        if not os.path.exists(self.cache_dir):
            return 0
            
        files_removed = 0
        current_time = time.time()
        
        for file_name in os.listdir(self.cache_dir):
            if file_name.endswith('.json'):
                file_path = os.path.join(self.cache_dir, file_name)
                
                # Se older_than_days è specificato, controlla l'età del file
                if older_than_days is not None:
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            cache_data = json.load(f)
                            timestamp = cache_data.get('timestamp', 0)
                            
                            # Calcola l'età in giorni
                            age_days = (current_time - timestamp) / (60 * 60 * 24)
                            
                            # Salta i file che non sono abbastanza vecchi
                            if age_days < older_than_days:
                                continue
                    except Exception:
                        # Se non riesce a leggere il file, lo rimuove comunque
                        pass
                
                # Rimuove il file
                try:
                    os.remove(file_path)
                    files_removed += 1
                except Exception as e:
                    logger.error(f"Errore nella rimozione del file cache {file_name}: {e}")
        
        return files_removed