#!/usr/bin/env python3
# agents/content_cleaner.py

import re
import time
import openai
import logging
import concurrent.futures
from typing import List, Dict, Any
from bs4 import BeautifulSoup

# Importa configurazioni
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import OPENAI_API_KEY, OPENAI_MODEL

# Configurazione del logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('content_cleaner')

# Configurazione OpenAI
openai.api_key = OPENAI_API_KEY

# Configurazione predefinita
DEFAULT_MAX_THREADS = 5
DEFAULT_BLOCK_SIZE = 5000  # caratteri per blocco
DEFAULT_OVERLAP = 150      # caratteri di sovrapposizione tra blocchi consecutivi

class ContentCleaner:
    """
    Agente per pulire il contenuto di una pagina web dividendolo in blocchi
    e processandolo con OpenAI in modalità multithread.
    """
    
    def __init__(self, max_threads=DEFAULT_MAX_THREADS, model=OPENAI_MODEL):
        """
        Inizializza il pulitore di contenuti.
        
        Args:
            max_threads (int): Numero massimo di thread paralleli
            model (str): Modello OpenAI da utilizzare
        """
        self.max_threads = max_threads
        self.model = model
        
    def clean_content(self, content: str, block_size=DEFAULT_BLOCK_SIZE, overlap=DEFAULT_OVERLAP, search_query: str = None) -> str:
        """
        Pulisce il contenuto di una pagina web rimuovendo menu, pubblicità, ecc.
        
        Args:
            content (str): Contenuto HTML o testo della pagina
            block_size (int): Dimensione massima (in caratteri) di ciascun blocco
            overlap (int): Sovrapposizione tra blocchi consecutivi
            search_query (str, optional): Query di ricerca o task per cui si sta pulendo il testo
            
        Returns:
            str: Contenuto pulito con solo le parti informative
        """
        # Se il contenuto sembra essere HTML, lo pre-elabora con BeautifulSoup
        if '<html' in content.lower() or '<body' in content.lower():
            logger.info("Il contenuto sembra essere HTML, eseguendo pre-elaborazione.")
            content = self._preprocess_html(content)
        
        # Divide il contenuto in blocchi di testo
        text_blocks = self._split_into_blocks(content, block_size, overlap)
        logger.info(f"Contenuto diviso in {len(text_blocks)} blocchi")
        
        # Pulisce i blocchi in parallelo
        clean_blocks = self._clean_blocks_parallel(text_blocks, search_query)
        
        # Riassembla i blocchi puliti
        cleaned_content = self._reassemble_blocks(clean_blocks)
        
        return cleaned_content
    
    def _preprocess_html(self, html_content: str) -> str:
        """
        Esegue una pulizia preliminare dell'HTML rimuovendo script, stili e tag comuni di navigazione.
        
        Args:
            html_content (str): Contenuto HTML della pagina
            
        Returns:
            str: Testo estratto dalla pagina HTML
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Rimuove elementi tipici di navigazione, pubblicità, ecc.
            for element in soup.select('script, style, nav, header, footer, aside, .ads, .ad, .advertisement, .menu'):
                element.extract()
            
            # Estrai solo il testo dal body
            if soup.body:
                return soup.body.get_text(separator='\n', strip=True)
            else:
                return soup.get_text(separator='\n', strip=True)
                
        except Exception as e:
            logger.error(f"Errore durante la pre-elaborazione dell'HTML: {e}")
            # In caso di errore, ritorna il testo originale
            return html_content
    
    def _split_into_blocks(self, content: str, block_size: int, overlap: int) -> List[str]:
        """
        Divide il contenuto in blocchi di testo sovrapposti con una strategia migliorata.
        
        Args:
            content (str): Contenuto testuale della pagina
            block_size (int): Dimensione massima (in caratteri) di ciascun blocco
            overlap (int): Sovrapposizione tra blocchi consecutivi
            
        Returns:
            List[str]: Lista di blocchi di testo
        """
        if not content:
            return []
        
        # Rimuove linee vuote multiple e spazi extra
        content = re.sub(r'\n\s*\n', '\n\n', content)
        content = re.sub(r' +', ' ', content)
        
        # Verifica se il contenuto è abbastanza corto da essere gestito in un unico blocco
        if len(content) <= block_size * 1.5:
            logger.info("Contenuto breve, elaborato come blocco unico")
            return [content]
        
        # Dividi il contenuto in paragrafi
        paragraphs = re.split(r'\n\n+', content)
        
        # Strategia migliorata: raggruppa i paragrafi in blocchi più grandi
        blocks = []
        current_block = ""
        
        for para in paragraphs:
            # Se aggiungere il paragrafo supererebbe block_size, inizia un nuovo blocco
            if len(current_block) + len(para) > block_size and current_block:
                blocks.append(current_block.strip())
                # Mantieni parte della sovrapposizione se necessario
                last_sentences = re.findall(r'[^.!?]*[.!?]', current_block)
                overlap_text = "".join(last_sentences[-2:]) if len(last_sentences) >= 2 else ""
                current_block = overlap_text + para
            else:
                if current_block:
                    current_block += "\n\n" + para
                else:
                    current_block = para
        
        # Aggiungi l'ultimo blocco se non è vuoto
        if current_block.strip():
            blocks.append(current_block.strip())
        
        logger.info(f"Contenuto diviso in {len(blocks)} blocchi (invece di potenzialmente {len(content) // block_size + 1})")
        return blocks
    
    def _clean_blocks_parallel(self, text_blocks: List[str], search_query: str = None) -> List[str]:
        """
        Pulisce i blocchi di testo in parallelo usando OpenAI.
        
        Args:
            text_blocks (List[str]): Lista di blocchi di testo da pulire
            search_query (str, optional): Query di ricerca o task per cui si sta pulendo il testo
            
        Returns:
            List[str]: Lista di blocchi di testo puliti
        """
        clean_blocks = []
        
        # Se non ci sono blocchi da elaborare
        if not text_blocks:
            return clean_blocks
            
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_threads) as executor:
            # Sottomette tutti i blocchi per l'elaborazione
            future_to_index = {
                executor.submit(self._clean_text_block, block, i, search_query): i 
                for i, block in enumerate(text_blocks)
            }
            
            # Elabora i risultati man mano che diventano disponibili
            completed = 0
            total = len(text_blocks)
            
            for future in concurrent.futures.as_completed(future_to_index):
                try:
                    index = future_to_index[future]
                    clean_text = future.result()
                    completed += 1
                    
                    # Aggiorna lo stato di avanzamento
                    if completed % 5 == 0 or completed == total:
                        logger.info(f"Elaborazione: {completed}/{total} blocchi completati")
                    
                    # Mantieni l'ordine originale dei blocchi
                    clean_blocks.append((index, clean_text))
                    
                except Exception as e:
                    logger.error(f"Errore durante la pulizia di un blocco: {e}")
        
        # Riordina i blocchi puliti in base all'indice originale
        clean_blocks.sort(key=lambda x: x[0])
        return [block for _, block in clean_blocks]
    
    def _clean_text_block(self, text: str, block_index: int, search_query: str = None) -> str:
        """
        Pulisce un singolo blocco di testo utilizzando OpenAI.
        
        Args:
            text (str): Blocco di testo da pulire
            block_index (int): Indice del blocco (per il logging)
            search_query (str, optional): Query di ricerca o task per cui si sta pulendo il testo
            
        Returns:
            str: Blocco di testo pulito
        """
        if not text.strip():
            return ""
            
        try:
            system_message = """
            Sei un'IA specializzata nel ripulire il testo estratto da pagine web.
            Il tuo compito è rimuovere elementi non informativi come:
            - Menu di navigazione
            - Link non pertinenti
            - Elementi di interfaccia
            - Testo ripetitivo di intestazioni/piè di pagina
            - Pubblicità
            - Cookie banner
            - Notifiche
            
            Mantieni SOLO il contenuto informativo principale, come:
            - Paragrafi del corpo del testo
            - Intestazioni pertinenti all'argomento
            - Elementi informativi come elenchi e citazioni
            
            Restituisci il testo pulito in formato semplice, mantenendo la struttura a paragrafi.
            NON aggiungere commenti o spiegazioni aggiuntive.
            """
            
            user_message = f"Ecco il testo da ripulire, mantenendo solo il contenuto informativo"
            
            # Se è presente una query di ricerca, include istruzioni specifiche per filtrare in base a essa
            if search_query:
                system_message += f"""
                Inoltre, considera che sto cercando informazioni su: "{search_query}"
                Concentrati particolarmente sul contenuto rilevante per questa ricerca.
                Mantieni prioritariamente i paragrafi e le sezioni che si riferiscono a questo argomento.
                Se ci sono sezioni che sembrano completamente irrilevanti per la ricerca, puoi rimuoverle.
                """
                user_message += f", con particolare attenzione alle informazioni relative a: {search_query}"
            
            user_message += f":\n\n{text}"
            
            # Usa l'API di OpenAI per pulire il testo
            response = openai.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.3,
                max_tokens=2048
            )
            
            clean_text = response.choices[0].message.content.strip()
            
            # Piccolo ritardo per evitare di raggiungere i limiti di rate dell'API
            time.sleep(0.5)
            
            return clean_text
            
        except Exception as e:
            logger.error(f"Errore durante la pulizia del blocco {block_index}: {e}")
            # In caso di errore, restituisci il testo originale
            return text
    
    def _reassemble_blocks(self, clean_blocks: List[str]) -> str:
        """
        Riassembla i blocchi di testo puliti in un unico contenuto.
        
        Args:
            clean_blocks (List[str]): Lista di blocchi di testo puliti
            
        Returns:
            str: Contenuto complessivo pulito
        """
        if not clean_blocks:
            return ""
            
        # Rimuove duplicazioni alle giunzioni tra blocchi a causa della sovrapposizione
        assembled_text = clean_blocks[0]
        
        for i in range(1, len(clean_blocks)):
            current_block = clean_blocks[i]
            
            # Evita duplicazione all'inizio dei blocchi
            # Cerca una sovrapposizione significativa
            overlap_size = min(100, len(assembled_text), len(current_block))
            
            if overlap_size > 0:
                prev_end = assembled_text[-overlap_size:]
                curr_start = current_block[:overlap_size]
                
                # Cerca la più lunga sottostringa comune
                max_overlap = 0
                best_pos = 0
                
                for j in range(1, overlap_size):
                    if prev_end[-j:] == curr_start[:j]:
                        if j > max_overlap:
                            max_overlap = j
                            best_pos = j
                
                # Se c'è una sovrapposizione significativa, unisci i blocchi
                if max_overlap > 10:  # Sovrapposizione minima per essere significativa
                    assembled_text = assembled_text[:-best_pos] + current_block
                else:
                    # Altrimenti, aggiungi un separatore di paragrafo
                    assembled_text += "\n\n" + current_block
            else:
                assembled_text += "\n\n" + current_block
        
        return assembled_text

# Funzione di utilità per uso esterno
def clean_webpage_content(content: str, max_threads=DEFAULT_MAX_THREADS, block_size=DEFAULT_BLOCK_SIZE, overlap=DEFAULT_OVERLAP, search_query: str = None) -> str:
    """
    Funzione di utilità per pulire il contenuto di una pagina web.
    
    Args:
        content (str): Contenuto HTML o testo della pagina
        max_threads (int, optional): Numero massimo di thread paralleli
        block_size (int, optional): Dimensione massima (in caratteri) di ciascun blocco
        overlap (int, optional): Sovrapposizione tra blocchi consecutivi
        search_query (str, optional): Query di ricerca o task per cui si sta pulendo il testo
        
    Returns:
        str: Contenuto pulito con solo le parti informative
    """
    # Pre-pulizia con BeautifulSoup per ridurre la dimensione del contenuto
    if '<html' in content.lower() or '<body' in content.lower():
        soup = BeautifulSoup(content, 'html.parser')
        
        # Rimuovi elementi non necessari
        for elem in soup.select('script, style, nav, header, footer, aside, .ads, .ad, .advertisement, .menu, .popup, .cookie'):
            elem.extract()
        
        # Estrai il testo principale
        content = soup.get_text(separator='\n', strip=True)
    
    # Se il contenuto è piccolo, elaboralo direttamente senza suddividerlo
    if len(content) < block_size * 2:
        cleaner = ContentCleaner(max_threads=1)  # Un solo thread è sufficiente
        return cleaner.clean_content(content, block_size=len(content), overlap=0, search_query=search_query)
    
    # Altrimenti usa la versione ottimizzata con più blocchi
    cleaner = ContentCleaner(max_threads=max_threads)
    return cleaner.clean_content(content, block_size=block_size, overlap=overlap, search_query=search_query)

# Test del cleaner
if __name__ == "__main__":
    import sys
    from web_scraper import scrape_webpage
    
    if len(sys.argv) > 1:
        url = sys.argv[1]
        print(f"Scaricamento e pulizia del contenuto di: {url}")
        
        # Ottieni il contenuto della pagina
        raw_content = scrape_webpage(url)
        
        # Pulisci il contenuto
        clean_content = clean_webpage_content(raw_content)
        
        print(f"Contenuto pulito ({len(clean_content)} caratteri)")
        print("Prime 1000 caratteri del contenuto pulito:")
        print(clean_content[:1000])
    else:
        print("Utilizzo: python content_cleaner.py <url>")