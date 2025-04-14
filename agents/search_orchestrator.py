#!/usr/bin/env python3
# agents/search_orchestrator.py

import os
import logging
import sys
from typing import List, Dict, Any, Optional

# Import modules
from agents.query_builder import build_google_query
from agents.google_search import google_search
from agents.relevance_filter import evaluate_result_relevance
from agents.web_scraper import scrape_webpage
from agents.content_cleaner import clean_webpage_content
from agents.content_relevance import evaluate_content_relevance
from agents.content_cache import ContentCache
from agents.rag_storage import RAGStorage
from agents.formatter import format_search_results

# Import configurations
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (
    OPENAI_API_KEY, 
    OPENAI_MODEL, 
    MAX_RELEVANT_RESULTS, 
    MAX_SEARCH_CYCLES, 
    LINK_RELEVANCE_THRESHOLD,
    CONTENT_RELEVANCE_THRESHOLD,
    CACHE_DIR
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('search_orchestrator')

class SearchOrchestrator:
    """
    Orchestratore che gestisce il processo di ricerca, scaricamento e valutazione di contenuti web
    in base a un task specifico.
    """
    
    def __init__(self, 
                max_relevant_results: int = MAX_RELEVANT_RESULTS,
                max_search_cycles: int = MAX_SEARCH_CYCLES,
                link_relevance_threshold: float = LINK_RELEVANCE_THRESHOLD,
                content_relevance_threshold: float = CONTENT_RELEVANCE_THRESHOLD,
                cache_dir: str = CACHE_DIR):
        """
        Inizializza l'orchestratore di ricerca.
        
        Args:
            max_relevant_results (int): Numero massimo di risultati rilevanti da trovare
            max_search_cycles (int): Numero massimo di cicli di ricerca da tentare
            link_relevance_threshold (float): Punteggio minimo per considerare un risultato di ricerca rilevante
            content_relevance_threshold (float): Punteggio minimo per considerare il contenuto di una pagina rilevante
            cache_dir (str): Directory per la cache dei contenuti scaricati
        """
        self.max_relevant_results = max_relevant_results
        self.max_search_cycles = max_search_cycles
        self.link_relevance_threshold = link_relevance_threshold
        self.content_relevance_threshold = content_relevance_threshold
        self.cache_dir = cache_dir
        
        # Inizializza il gestore della cache
        self.content_cache = ContentCache(cache_dir=cache_dir)
        
        # Inizializza RAGStorage per salvare i risultati
        try:
            self.rag_storage = RAGStorage()
        except Exception as e:
            logger.warning(f"Impossibile inizializzare RAGStorage: {e}. Funzionalità RAG disabilitata.")
            self.rag_storage = None
        
    def search(self, task: str, save_as_rag: bool = True) -> List[Dict[str, Any]]: 
        """
        Esegue il processo di ricerca completo per un task specifico.
        
        Args:
            task (str): Il task di ricerca
            save_as_rag (bool): Se True, salva i risultati in formato RAG
            
        Returns:
            List[Dict[str, Any]]: Lista di risultati rilevanti con contenuti
        """
        logger.info(f"Avvio ricerca per il task: {task}")
        
        relevant_results = []  # Risultati finali rilevanti
        visited_urls = set()  # URL già visitati
        previous_queries = []  # Query già utilizzate
        
        # Esegui fino a max_search_cycles cicli di ricerca
        for cycle in range(1, self.max_search_cycles + 1):
            logger.info(f"Ciclo di ricerca {cycle}/{self.max_search_cycles}")
            
            # 1. Genera una nuova query basata sul task
            query = build_google_query(task, previous_queries=previous_queries)
            previous_queries.append(query)
            logger.info(f"Query generata: {query}")
            
            # 2. Esegui la ricerca su Google
            search_results = google_search(query)
            if not search_results:
                logger.warning(f"Nessun risultato trovato per la query: {query}")
                continue
                
            logger.info(f"Trovati {len(search_results)} risultati di ricerca")
            
            # 3. Valuta la rilevanza dei risultati di ricerca
            for result in search_results:
                url = result.get('link')
                
                # Salta URL già visitati
                if url in visited_urls:
                    logger.info(f"URL già visitato, saltato: {url}")
                    continue
                
                # Aggiungi agli URL visitati
                visited_urls.add(url)
                
                # Valuta la rilevanza del risultato rispetto al task
                relevance_score = evaluate_result_relevance(result, task)
                result['relevance_score'] = relevance_score
                
                # Se il punteggio di rilevanza è sufficiente, scarica e valuta il contenuto
                if relevance_score >= self.link_relevance_threshold:
                    logger.info(f"Risultato rilevante trovato (score: {relevance_score:.2f}): {url}")
                    
                    try:
                        # 4. Scarica il contenuto della pagina web (o usa la cache)
                        content = self.content_cache.get_content(url, scraper_func=scrape_webpage)
                        
                        # 5. Pulisci il contenuto
                        clean_content = clean_webpage_content(content)
                        
                        # 6. Valuta la rilevanza del contenuto rispetto al task
                        content_evaluation = evaluate_content_relevance(task, clean_content, detailed=True)
                        
                        # Se il contenuto è rilevante, aggiungilo ai risultati
                        if (content_evaluation['is_relevant'] and 
                            content_evaluation['relevance_score'] >= self.content_relevance_threshold):
                            
                            # Aggiungi i risultati della valutazione del contenuto
                            result['content'] = clean_content
                            result['content_evaluation'] = content_evaluation
                            
                            relevant_results.append(result)
                            logger.info(f"Contenuto rilevante aggiunto ai risultati (score: {content_evaluation['relevance_score']:.2f}): {url}")
                            
                            # Se abbiamo raggiunto il numero desiderato di risultati rilevanti, termina
                            if len(relevant_results) >= self.max_relevant_results:
                                logger.info(f"Raggiunto il numero massimo di risultati rilevanti ({self.max_relevant_results})")
                                break
                        else:
                            logger.info(f"Contenuto non rilevante (score: {content_evaluation['relevance_score']:.2f}): {url}")
                    
                    except Exception as e:
                        logger.error(f"Errore durante l'elaborazione dell'URL {url}: {e}")
            
            # Se questo è l'ultimo ciclo o abbiamo trovato almeno alcuni risultati, termina
            if cycle == self.max_search_cycles or len(relevant_results) > 0:
                break
                
        # Ordina i risultati per punteggio di rilevanza del contenuto
        relevant_results.sort(key=lambda x: x['content_evaluation']['relevance_score'], reverse=True)
        
        logger.info(f"Ricerca completata. Trovati {len(relevant_results)} risultati rilevanti.")
        
        # Salva i risultati in formato RAG se richiesto
        if save_as_rag and self.rag_storage and relevant_results:
            rag_id = self.rag_storage.save_results_as_rag(task, relevant_results)
            if rag_id:
                logger.info(f"Risultati salvati come RAG con ID: {rag_id}")
                
                # Aggiungi l'ID RAG ai metadati dei risultati
                for result in relevant_results:
                    if 'metadata' not in result:
                        result['metadata'] = {}
                    result['metadata']['rag_id'] = rag_id
        
        return relevant_results
    
    def summarize_content(self, url_or_content: str, is_url: bool = True) -> str:
        """
        Crea un riassunto del contenuto di una pagina utilizzando OpenAI.
        
        Args:
            url_or_content (str): URL o contenuto diretto da riassumere
            is_url (bool): Se True, il primo argomento è un URL, altrimenti è già il contenuto
            
        Returns:
            str: Riassunto del contenuto
        """
        # Se è un URL, ottieni il contenuto (dalla cache se disponibile)
        if is_url:
            content = self.content_cache.get_content(url_or_content, scraper_func=scrape_webpage)
            # Pulisci il contenuto
            content = clean_webpage_content(content)
        else:
            content = url_or_content
        
        # Se il contenuto è vuoto o troppo breve, ritorna un messaggio di errore
        if not content or len(content.strip()) < 50:
            return "Contenuto non disponibile o troppo breve per essere riassunto."
        
        try:
            # Tronca il contenuto se troppo lungo per il prompt
            max_content_length = 10000
            if len(content) > max_content_length:
                content = content[:max_content_length] + "\n...[contenuto troncato]..."
                logger.info(f"Contenuto troncato da {len(content)} a {max_content_length} caratteri per il riassunto")
            
            # Usa OpenAI per generare un riassunto
            import openai
            
            system_message = """
            Sei un'IA specializzata nel riassumere contenuti web.
            Crea un riassunto conciso ma informativo del testo fornito, evidenziando:
            1. I punti chiave e le informazioni principali
            2. I dati rilevanti e le statistiche, se presenti
            3. Le conclusioni o raccomandazioni
            
            Il riassunto deve essere chiaro, obiettivo e mantenere l'essenza del contenuto originale.
            Struttura il riassunto in paragrafi o punti elenco se opportuno per una migliore leggibilità.
            """
            
            user_message = f"Ecco il contenuto da riassumere:\n\n{content}"
            
            response = openai.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.5,
                max_tokens=1024
            )
            
            summary = response.choices[0].message.content.strip()
            logger.info(f"Riassunto generato ({len(summary)} caratteri)")
            
            return summary
            
        except Exception as e:
            logger.error(f"Errore durante la generazione del riassunto: {e}")
            return f"Errore nella generazione del riassunto: {str(e)}"
        
    def get_cached_pages(self) -> List[Dict[str, Any]]:
        """
        Ottiene l'elenco di tutte le pagine nella cache.
        
        Returns:
            List[Dict[str, Any]]: Lista di metadati delle pagine nella cache
        """
        return self.content_cache.list_cached_pages()

# Funzione principale per l'uso diretto dello script
def main():
    """
    Funzione principale per l'esecuzione della ricerca da riga di comando.
    """
    from agents.cli_utils import create_argument_parser, handle_cli_commands, save_output
    
    # Parse degli argomenti
    parser = create_argument_parser()
    args = vars(parser.parse_args())
    
    # Se non ci sono argomenti sufficienti, mostra l'help
    if not any([args.get('task'), args.get('list_indices'), args.get('list_cache'), 
               args.get('clear_cache'), args.get('clear_old_cache'), args.get('summarize')]):
        parser.print_help()
        return
    
    # Crea l'orchestrator con parametri personalizzati se necessario
    orchestrator_kwargs = {}
    
    if args.get('max_results'):
        orchestrator_kwargs['max_relevant_results'] = args['max_results']
    
    if args.get('max_cycles'):
        orchestrator_kwargs['max_search_cycles'] = args['max_cycles']
        
    orchestrator = SearchOrchestrator(**orchestrator_kwargs)
    
    # Gestisci i comandi della CLI
    output = handle_cli_commands(args, orchestrator)
    
    if output:
        # Salva l'output su file se richiesto
        if args.get('output'):
            if save_output(output, args['output']):
                print(f"Output salvato nel file: {args['output']}")
            else:
                print(f"Errore durante il salvataggio dell'output nel file: {args['output']}")
        
        # Altrimenti, stampa l'output
        else:
            print(output)

# Esecuzione diretta dello script
if __name__ == "__main__":
    main()