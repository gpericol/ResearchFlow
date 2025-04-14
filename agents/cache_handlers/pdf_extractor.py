#!/usr/bin/env python3
# agents/cache_handlers/pdf_extractor.py

import os
import tempfile
import logging
import requests

logger = logging.getLogger('content_cache.pdf_extractor')

class PDFExtractor:
    """
    Classe specializzata per l'estrazione di testo dai file PDF.
    """
    
    def extract_pdf_text(self, url: str) -> str:
        """
        Scarica un file PDF da un URL ed estrae il testo.
        
        Args:
            url (str): URL del file PDF
            
        Returns:
            str: Testo estratto dal PDF o stringa vuota in caso di errore
        """
        try:
            import pypdf
            
            logger.info(f"Scaricamento del PDF da: {url}")
            
            # Scarica il file PDF
            response = requests.get(url, stream=True, timeout=30)
            if response.status_code != 200:
                logger.error(f"Errore nel download del PDF da {url}: status code {response.status_code}")
                return ""
                
            # Salva temporaneamente il PDF
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
                tmp_path = tmp_file.name
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        tmp_file.write(chunk)
            
            # Estrai il testo dal PDF
            extracted_text = ""
            try:
                with open(tmp_path, 'rb') as pdf_file:
                    reader = pypdf.PdfReader(pdf_file)
                    num_pages = len(reader.pages)
                    
                    logger.info(f"Estrazione del testo da PDF con {num_pages} pagine")
                    
                    # Estrai il testo da ogni pagina
                    for page_num in range(num_pages):
                        page = reader.pages[page_num]
                        page_text = page.extract_text()
                        if page_text:
                            extracted_text += page_text + "\n\n"
                
                logger.info(f"Estrazione completata: {len(extracted_text)} caratteri estratti")
                
            except Exception as e:
                logger.error(f"Errore nell'estrazione del testo dal PDF: {e}")
                return ""
            finally:
                # Rimuovi il file temporaneo
                try:
                    os.unlink(tmp_path)
                except Exception as e:
                    logger.warning(f"Errore nella rimozione del file temporaneo: {e}")
            
            return extracted_text.strip()
            
        except ImportError:
            logger.error("Libreria pypdf non disponibile per l'estrazione di testo dai PDF")
            return ""
        except Exception as e:
            logger.error(f"Errore generale nell'estrazione del testo dal PDF {url}: {e}")
            return ""