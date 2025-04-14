# agents/relevance_filter.py

import openai
from typing import List, Dict, Any, Optional
from config import OPENAI_API_KEY, OPENAI_MODEL

# Configure OpenAI
openai.api_key = OPENAI_API_KEY

def filter_relevant_results(search_results: List[Dict[str, Any]], 
                           query: str, 
                           threshold: float = 0.7) -> List[Dict[str, Any]]:
    """
    Filtra i risultati di ricerca in base alla loro rilevanza rispetto alla query originale usando OpenAI.
    
    Args:
        search_results (List[Dict[str, Any]]): Lista di risultati di ricerca da google_search
        query (str): La query di ricerca originale
        threshold (float): Punteggio minimo di rilevanza (0-1) per includere i risultati
        
    Returns:
        List[Dict[str, Any]]: Lista filtrata di risultati di ricerca rilevanti
    """
    if not search_results:
        return []
    
    filtered_results = []
    
    for result in search_results:
        relevance_score = evaluate_result_relevance(result, query)
        
        # Aggiungi il punteggio di rilevanza al risultato
        result['relevance_score'] = relevance_score
        
        if relevance_score >= threshold:
            filtered_results.append(result)
    
    # Ordina per punteggio di rilevanza (dal più alto)
    filtered_results.sort(key=lambda x: x['relevance_score'], reverse=True)
    return filtered_results

def evaluate_result_relevance(result: Dict[str, Any], query: str) -> float:
    """
    Valuta la rilevanza di un risultato di ricerca rispetto alla query utilizzando OpenAI.
    
    Args:
        result (Dict[str, Any]): Un risultato di ricerca con titolo, link e descrizione
        query (str): La query di ricerca originale
        
    Returns:
        float: Punteggio di rilevanza tra 0 (irrilevante) e 1 (altamente rilevante)
    """
    title = result.get('title', '')
    description = result.get('description', '')
    url = result.get('link', '')
    
    # Prepara il prompt per OpenAI
    system_message = """
    Sei un'IA che valuta la rilevanza dei risultati di ricerca. 
    Analizza il titolo, la descrizione e l'URL del risultato di ricerca, e determina se è rilevante per la query originale.
    Valuta la rilevanza su una scala da 0 a 1, dove:
    - 0 significa completamente irrilevante
    - 0.5 significa parzialmente rilevante
    - 1 significa altamente rilevante
    Restituisci solo un numero decimale che rappresenta il punteggio di rilevanza.
    """
    
    user_message = f"""
    Query originale: {query}
    
    Risultato di ricerca da valutare:
    Titolo: {title}
    Descrizione: {description}
    URL: {url}
    
    Punteggio di rilevanza (da 0 a 1):
    """
    
    try:
        response = openai.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            temperature=0.3,
            max_tokens=5
        )
        
        # Estrai il punteggio di rilevanza dalla risposta
        score_text = response.choices[0].message.content.strip()
        try:
            # Prova a interpretare il punteggio come numero decimale
            relevance_score = float(score_text)
            # Assicurati che il punteggio sia tra 0 e 1
            relevance_score = max(0.0, min(1.0, relevance_score))
            return relevance_score
        except ValueError:
            print(f"Errore nell'interpretazione del punteggio di rilevanza: {score_text}")
            return 0.5  # Valore predefinito di rilevanza neutra in caso di errore
            
    except Exception as e:
        print(f"Errore nella valutazione della rilevanza: {e}")
        return 0.5  # Valore predefinito di rilevanza neutra in caso di errore

def batch_evaluate_relevance(search_results: List[Dict[str, Any]], 
                           query: str) -> List[Dict[str, Any]]:
    """
    Valuta la rilevanza di più risultati di ricerca con una singola chiamata API per maggiore efficienza.
    
    Args:
        search_results (List[Dict[str, Any]]): Lista di risultati di ricerca da google_search
        query (str): La query di ricerca originale
        
    Returns:
        List[Dict[str, Any]]: Risultati di ricerca con punteggi di rilevanza aggiunti
    """
    if not search_results:
        return []
    
    # Prepara il prompt combinato
    system_message = """
    Valuta la rilevanza di ogni risultato di ricerca rispetto alla query originale.
    Assegna un punteggio di rilevanza a ciascun risultato su una scala da 0 a 1, dove:
    - 0 significa completamente irrilevante
    - 0.5 significa parzialmente rilevante
    - 1 significa altamente rilevante
    
    Restituisci solo un array JSON di punteggi. Esempio: [0.8, 0.3, 0.9]
    """
    
    search_results_text = ""
    for i, result in enumerate(search_results):
        title = result.get('title', '')
        description = result.get('description', '')
        url = result.get('link', '')
        
        search_results_text += f"""
        Risultato {i+1}:
        Titolo: {title}
        Descrizione: {description}
        URL: {url}
        
        """
    
    user_message = f"""
    Query originale: {query}
    
    Risultati di ricerca da valutare:
    {search_results_text}
    
    Per favore restituisci un array JSON di punteggi di rilevanza (da 0 a 1) per ciascun risultato, in ordine:
    """
    
    try:
        response = openai.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            temperature=0.3,
            response_format={"type": "json_object"},
            max_tokens=100
        )
        
        # Estrai i punteggi di rilevanza dalla risposta
        import json
        try:
            response_content = response.choices[0].message.content.strip()
            scores_data = json.loads(response_content)
            
            # Controlla se abbiamo ottenuto una lista di punteggi o un dizionario con una chiave scores
            if isinstance(scores_data, dict) and 'scores' in scores_data:
                scores = scores_data['scores']
            elif isinstance(scores_data, dict) and 'relevance_scores' in scores_data:
                scores = scores_data['relevance_scores']
            else:
                # Prova a trovare qualsiasi lista nella risposta
                for key, value in scores_data.items():
                    if isinstance(value, list) and len(value) == len(search_results):
                        scores = value
                        break
                else:
                    # Se non possiamo trovare una lista corrispondente, ripieghiamo sulla valutazione individuale
                    print("Impossibile analizzare i punteggi di rilevanza in batch, ripiego sulla valutazione individuale")
                    return [evaluate_result_relevance(result, query) for result in search_results]
            
            # Aggiungi i punteggi ai risultati
            for i, result in enumerate(search_results):
                if i < len(scores):
                    try:
                        score = float(scores[i])
                        # Assicurati che il punteggio sia tra 0 e 1
                        result['relevance_score'] = max(0.0, min(1.0, score))
                    except (ValueError, TypeError):
                        result['relevance_score'] = 0.5
                else:
                    result['relevance_score'] = 0.5
                    
            return search_results
                
        except json.JSONDecodeError:
            print(f"Errore nell'analisi della risposta JSON: {response_content}")
            # Ripiego sulla valutazione individuale
            return [evaluate_result_relevance(result, query) for result in search_results]
            
    except Exception as e:
        print(f"Errore nella valutazione in batch: {e}")
        # Ripiego sulla valutazione individuale
        return [evaluate_result_relevance(result, query) for result in search_results]

def search_and_filter(query: str, num_results: int = None, threshold: float = 0.7, use_batch: bool = True) -> List[Dict[str, Any]]:
    """
    Esegue una ricerca Google e filtra i risultati in base alla loro rilevanza rispetto alla query.
    
    Args:
        query (str): La query di ricerca
        num_results (int, optional): Numero massimo di risultati di ricerca da restituire prima del filtraggio
        threshold (float, optional): Punteggio minimo di rilevanza (0-1) per includere i risultati
        use_batch (bool, optional): Se utilizzare la valutazione in batch (più efficiente) o la valutazione individuale
        
    Returns:
        List[Dict[str, Any]]: Lista filtrata di risultati di ricerca rilevanti
    """
    from agents.google_search import google_search
    
    # Esegue la ricerca
    search_results = google_search(query, num_results=num_results if num_results else None)
    
    if not search_results:
        return []
    
    # Valuta e filtra i risultati
    if use_batch:
        # Più efficiente per risultati multipli
        results_with_scores = batch_evaluate_relevance(search_results, query)
        filtered_results = [r for r in results_with_scores if r.get('relevance_score', 0) >= threshold]
    else:
        # Valutazione individuale
        filtered_results = filter_relevant_results(search_results, query, threshold)
    
    # Ordina per punteggio di rilevanza (dal più alto)
    filtered_results.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
    return filtered_results

def format_filtered_results(filtered_results: List[Dict[str, Any]]) -> str:
    """
    Formatta i risultati di ricerca filtrati in una stringa leggibile che include i punteggi di rilevanza.
    
    Args:
        filtered_results (List[Dict[str, Any]]): I risultati di ricerca filtrati da formattare
        
    Returns:
        str: Una rappresentazione formattata dei risultati di ricerca con punteggi di rilevanza
    """
    from agents.google_search import format_search_results
    
    if not filtered_results:
        return "Nessun risultato di ricerca rilevante trovato."
    
    formatted_text = "Risultati di Ricerca Rilevanti:\n\n"
    
    for i, result in enumerate(filtered_results, 1):
        formatted_text += f"{i}. {result['title']}\n"
        formatted_text += f"   Link: {result['link']}\n"
        formatted_text += f"   {result['description']}\n"
        formatted_text += f"   Punteggio di Rilevanza: {result.get('relevance_score', 'N/A'):.2f}\n\n"
        
    return formatted_text