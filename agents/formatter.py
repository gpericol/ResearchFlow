#!/usr/bin/env python3
# agents/formatter.py

from typing import List, Dict, Any

def format_search_results(results: List[Dict[str, Any]]) -> str:
    """
    Formatta i risultati della ricerca in un formato leggibile.
    
    Args:
        results (List[Dict[str, Any]]): Risultati della ricerca
        
    Returns:
        str: Testo formattato con i risultati
    """
    if not results:
        return "Nessun risultato rilevante trovato."
        
    formatted_text = f"Trovati {len(results)} risultati rilevanti:\n\n"
    
    for i, result in enumerate(results, 1):
        title = result.get('title', 'Titolo non disponibile')
        url = result.get('link', '')
        rel_score = result.get('relevance_score', 0.0)
        
        content_eval = result.get('content_evaluation', {})
        content_score = content_eval.get('relevance_score', 0.0)
        
        formatted_text += f"{i}. {title}\n"
        formatted_text += f"   URL: {url}\n"
        formatted_text += f"   Rilevanza titolo/descrizione: {rel_score:.2f}\n"
        formatted_text += f"   Rilevanza contenuto: {content_score:.2f}\n"
        
        # Aggiungi i punti chiave se disponibili
        key_points = content_eval.get('key_points', [])
        if key_points:
            formatted_text += "   Punti chiave:\n"
            for point in key_points:
                formatted_text += f"   - {point}\n"
        
        formatted_text += "\n"
    
    return formatted_text

def format_rag_query_result(result: Dict[str, Any]) -> str:
    """
    Formatta il risultato di una query RAG in modo leggibile.
    
    Args:
        result (Dict[str, Any]): Risultato della query RAG
        
    Returns:
        str: Testo formattato con la risposta e le fonti
    """
    if not result:
        return "Nessun risultato di query RAG disponibile."
        
    formatted_text = "Risultato della Query RAG:\n"
    formatted_text += "-" * 50 + "\n"
    formatted_text += f"Risposta: {result.get('response', 'Nessuna risposta generata')}\n\n"
    
    sources = result.get('sources', [])
    if sources:
        formatted_text += f"Fonti utilizzate ({len(sources)}):\n\n"
        
        for i, source in enumerate(sources, 1):
            formatted_text += f"{i}. {source.get('title', 'Titolo non disponibile')} (score: {source.get('score', 0.0):.2f})\n"
            formatted_text += f"   URL: {source.get('url', 'URL non disponibile')}\n"
            formatted_text += f"   Cache: {source.get('cache_file', 'N/A')}\n"
            content = source.get('content', '')
            preview = (content[:150] + "...") if len(content) > 150 else content
            formatted_text += f"   Anteprima: {preview}\n\n"
    else:
        formatted_text += "Nessuna fonte disponibile.\n"
        
    return formatted_text

def format_rag_indices(indices: List[Dict[str, Any]]) -> str:
    """
    Formatta la lista di indici RAG disponibili.
    
    Args:
        indices (List[Dict[str, Any]]): Lista di metadati degli indici RAG
        
    Returns:
        str: Testo formattato con gli indici disponibili
    """
    if not indices:
        return "Nessun indice RAG disponibile."
        
    formatted_text = f"Indici RAG disponibili ({len(indices)}):\n\n"
    
    for idx in indices:
        formatted_text += f"ID: {idx.get('id', 'N/A')}\n"
        formatted_text += f"Task: {idx.get('task', 'N/A')}\n"
        formatted_text += f"Data: {idx.get('created_at', 'N/A')}\n"
        formatted_text += f"Documenti: {idx.get('num_documents', 0)}\n"
        formatted_text += "-" * 50 + "\n"
    
    return formatted_text

def format_cached_pages(cached_pages: List[Dict[str, Any]]) -> str:
    """
    Formatta la lista di pagine in cache.
    
    Args:
        cached_pages (List[Dict[str, Any]]): Lista di metadati delle pagine in cache
        
    Returns:
        str: Testo formattato con le pagine in cache
    """
    if not cached_pages:
        return "Nessuna pagina in cache."
        
    formatted_text = f"Pagine in cache ({len(cached_pages)}):\n\n"
    
    # Ordina per timestamp (più recente prima)
    cached_pages.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
    
    for i, page in enumerate(cached_pages, 1):
        url = page.get('url', 'URL non disponibile')
        timestamp = page.get('timestamp', 0)
        
        # Formatta il timestamp
        import datetime
        date_str = datetime.datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
        
        formatted_text += f"{i}. {url}\n"
        formatted_text += f"   File: {page.get('cache_file', 'N/A')}\n"
        formatted_text += f"   Data: {date_str}\n"
        formatted_text += f"   Dimensione: {page.get('size', 0) / 1024:.1f} KB\n\n"
    
    return formatted_text