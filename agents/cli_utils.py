#!/usr/bin/env python3
# agents/cli_utils.py

import sys
import argparse
from typing import Dict, Any, Optional

# Import formattatori
from agents.formatter import format_search_results, format_rag_query_result, format_rag_indices

def create_argument_parser() -> argparse.ArgumentParser:
    """
    Crea il parser degli argomenti da linea di comando.
    
    Returns:
        argparse.ArgumentParser: Parser degli argomenti
    """
    parser = argparse.ArgumentParser(description='Orchestratore di ricerca per task specifici')
    parser.add_argument('task', nargs='?', default=None, 
                       help='Il task di ricerca o la query per interrogare un indice RAG')
    
    parser.add_argument('--max-results', type=int, default=None, 
                        help='Numero massimo di risultati rilevanti')
    parser.add_argument('--max-cycles', type=int, default=None, 
                        help='Numero massimo di cicli di ricerca')
    parser.add_argument('--no-rag', action='store_true', 
                        help='Non salvare i risultati come RAG')
    
    # Opzioni RAG
    parser.add_argument('--query-rag', type=str, 
                        help='ID dell\'indice RAG da interrogare')
    parser.add_argument('--list-indices', action='store_true', 
                        help='Elenca tutti gli indici RAG disponibili')
    
    # Opzioni Cache
    parser.add_argument('--list-cache', action='store_true',
                        help='Elenca tutte le pagine nella cache')
    parser.add_argument('--clear-cache', action='store_true',
                        help='Cancella tutti i file nella cache')
    parser.add_argument('--clear-old-cache', type=int, metavar='DAYS',
                        help='Cancella i file nella cache più vecchi di DAYS giorni')
    
    # Opzioni di analisi del contenuto
    parser.add_argument('--summarize', type=str, metavar='URL',
                        help='Genera un riassunto del contenuto di un URL')
    
    # Opzioni di output
    parser.add_argument('--output', type=str,
                        help='Salva l\'output in un file')
    
    return parser

def handle_cli_commands(args: Dict[str, Any], orchestrator) -> Optional[str]:
    """
    Gestisce i comandi della CLI eseguendo le azioni appropriate.
    
    Args:
        args (Dict[str, Any]): Argomenti della riga di comando
        orchestrator: Istanza di SearchOrchestrator
        
    Returns:
        Optional[str]: Output da visualizzare o salvare, None se non c'è output
    """
    output = None
    
    # Gestione delle opzioni della cache
    if args.get('list_cache'):
        cached_pages = orchestrator.get_cached_pages()
        from agents.formatter import format_cached_pages
        output = format_cached_pages(cached_pages)
    
    elif args.get('clear_cache'):
        from agents.content_cache import ContentCache
        cache = ContentCache()
        files_removed = cache.clear_cache()
        output = f"Cache cancellata: {files_removed} file rimossi."
    
    elif args.get('clear_old_cache') is not None:
        days = args.get('clear_old_cache')
        from agents.content_cache import ContentCache
        cache = ContentCache()
        files_removed = cache.clear_cache(older_than_days=days)
        output = f"File vecchi rimossi dalla cache: {files_removed} file più vecchi di {days} giorni."
    
    # Gestione delle opzioni RAG
    elif args.get('list_indices'):
        if orchestrator.rag_storage and orchestrator.rag_storage.is_initialized:
            indices = orchestrator.rag_storage.list_rag_indices()
            output = format_rag_indices(indices)
        else:
            output = "Sistema RAG non inizializzato. Impossibile elencare gli indici."
    
    elif args.get('query_rag') and args.get('task'):
        rag_id = args.get('query_rag')
        query = args.get('task')
        if orchestrator.rag_storage and orchestrator.rag_storage.is_initialized:
            result = orchestrator.rag_storage.query_rag_index(rag_id, query)
            if result:
                output = format_rag_query_result(result)
            else:
                output = f"Impossibile interrogare l'indice RAG {rag_id}."
        else:
            output = "Sistema RAG non inizializzato. Impossibile eseguire query."
    
    # Gestione dell'opzione di riassunto
    elif args.get('summarize'):
        url = args.get('summarize')
        summary = orchestrator.summarize_content(url)
        output = f"Riassunto di {url}:\n\n{summary}"
    
    # Gestione della ricerca normale
    elif args.get('task'):
        task = args.get('task')
        save_as_rag = not args.get('no_rag', False)
        
        # Imposta i parametri opzionali se forniti
        kwargs = {}
        if args.get('max_results') is not None:
            kwargs['max_relevant_results'] = args.get('max_results')
        if args.get('max_cycles') is not None:
            kwargs['max_search_cycles'] = args.get('max_cycles')
        
        # Esegui la ricerca con i parametri specificati
        if kwargs:
            temp_orchestrator = type(orchestrator)(**kwargs)
            results = temp_orchestrator.search(task, save_as_rag=save_as_rag)
        else:
            results = orchestrator.search(task, save_as_rag=save_as_rag)
        
        # Formatta i risultati
        output = format_search_results(results)
        
        # Aggiungi informazioni sullo stato RAG
        if save_as_rag and orchestrator.rag_storage and orchestrator.rag_storage.is_initialized:
            if results and any('metadata' in r and 'rag_id' in r['metadata'] for r in results):
                rag_id = next(r['metadata']['rag_id'] for r in results if 'metadata' in r and 'rag_id' in r['metadata'])
                output += f"\nRisultati salvati come indice RAG con ID: {rag_id}"
                output += f"\nPer interrogare questo indice in futuro, usa: python search_orchestrator.py --query-rag {rag_id} \"la tua domanda\""
        elif save_as_rag:
            output += "\nNota: Il salvataggio RAG era abilitato ma non è stato possibile salvare i risultati come RAG."
    
    return output

def save_output(output: str, filename: str) -> bool:
    """
    Salva l'output in un file.
    
    Args:
        output (str): Output da salvare
        filename (str): Nome del file
        
    Returns:
        bool: True se il salvataggio è riuscito, False altrimenti
    """
    if not output or not filename:
        return False
        
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(output)
        return True
    except Exception as e:
        print(f"Errore durante il salvataggio dell'output: {e}")
        return False