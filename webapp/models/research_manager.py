import threading
import time
from datetime import datetime
from typing import Dict, Any, List, Optional

from agents.search_orchestrator import SearchOrchestrator
from agents.rag_storage import RAGStorage
from webapp.models.data_manager import load_data, save_data

# Costante per l'ID del RAG unificato
UNIFIED_RAG_ID = "unified_rag"

# Dizionario per tenere traccia delle ricerche in corso
research_status = {}

def start_research(group_index: int) -> Dict[str, Any]:
    """
    Avvia un processo di ricerca per tutti i task non completati in un gruppo.
    
    Args:
        group_index: L'indice del gruppo di task per cui avviare la ricerca
        
    Returns:
        Dizionario con il risultato dell'operazione
    """
    data = load_data()
    
    # Verifica se l'indice del gruppo è valido
    if not 0 <= group_index < len(data["tasks"]):
        return {"success": False, "error": "Gruppo non trovato"}
    
    # Verifica se c'è già una ricerca in corso per questo gruppo
    if group_index in research_status and research_status[group_index]["in_progress"]:
        return {"success": False, "error": "Ricerca già in corso per questo gruppo"}
    
    # Inizializza lo stato della ricerca
    task_group = data["tasks"][group_index]
    task_indices = [i for i, task in enumerate(task_group["tasks"]) if not task["completed"]]
    
    # Se non ci sono task da completare, restituisci un errore
    if not task_indices:
        return {"success": False, "error": "Non ci sono task da completare"}
    
    # Inizializza lo stato della ricerca
    research_status[group_index] = {
        "in_progress": True,
        "completed": False,
        "completed_tasks": [],
        "current_task_index": None,
        "total_tasks": len(task_indices),
        "rag_id": None,
        "start_time": datetime.now().isoformat()
    }
    
    # Aggiungi research_in_progress al gruppo di task
    data["tasks"][group_index]["research_in_progress"] = True
    save_data(data)
    
    # Avvia un thread per eseguire la ricerca in background
    thread = threading.Thread(target=perform_research, args=(group_index, task_indices))
    thread.daemon = True  # Il thread terminerà quando termina l'applicazione principale
    thread.start()
    
    return {"success": True}

def check_research_progress(group_index: int) -> Dict[str, Any]:
    """
    Controlla lo stato di avanzamento di una ricerca.
    
    Args:
        group_index: L'indice del gruppo di task per cui controllare lo stato
        
    Returns:
        Dizionario con lo stato della ricerca
    """
    # Se non esiste lo stato per questo gruppo, restituisci un dizionario vuoto
    if group_index not in research_status:
        return {
            "in_progress": False,
            "completed": False,
            "completed_tasks": [],
            "current_task_index": None
        }
    
    # Restituisci lo stato attuale
    status = research_status[group_index].copy()
    
    # Rimuovi alcune informazioni interne che non servono al client
    if "start_time" in status:
        del status["start_time"]
    if "total_tasks" in status:
        del status["total_tasks"]
    
    return status

def perform_research(group_index: int, task_indices: List[int]) -> None:
    """
    Esegue la ricerca per tutti i task non completati in un gruppo.
    Questa funzione viene eseguita in un thread separato.
    
    Args:
        group_index: L'indice del gruppo di task
        task_indices: Lista degli indici dei task da completare
    """
    data = load_data()
    task_group = data["tasks"][group_index]
    search_orchestrator = SearchOrchestrator()
    rag_storage = RAGStorage()
    all_results = []
    
    # Assicurati che l'indice RAG unificato esista
    unified_rag_id = rag_storage.get_or_create_unified_rag(UNIFIED_RAG_ID)
    
    for i, task_index in enumerate(task_indices):
        # Aggiorna lo stato corrente
        research_status[group_index]["current_task_index"] = task_index
        
        task = task_group["tasks"][task_index]
        task_prompt = task["point"]
        
        try:
            # Esegui la ricerca per il task corrente
            results = search_orchestrator.search(task_prompt, save_as_rag=False)
            
            # Aggiungi i risultati alla lista complessiva
            if results:
                all_results.extend(results)
            
            # Marca il task come completato
            data["tasks"][group_index]["tasks"][task_index]["completed"] = True
            
            # Aggiungi il task alla lista dei task completati
            research_status[group_index]["completed_tasks"].append(task_index)
            
            # Salva i dati aggiornati
            save_data(data)
            
            # Breve pausa per evitare di sovraccaricare il sistema
            time.sleep(1)
            
        except Exception as e:
            print(f"Errore nella ricerca per il task {task_index}: {e}")
    
    # Una volta completati tutti i task, aggiungi i risultati al RAG unificato
    if all_results:
        try:
            task_prompt = f"Ricerca per il gruppo: {task_group.get('prompt', 'Gruppo di task')}"
            
            # Aggiorna il RAG unificato con i nuovi risultati
            if unified_rag_id:
                success = rag_storage.update_rag_index(unified_rag_id, task_prompt, all_results)
                if success:
                    # Aggiorna il gruppo con l'ID del RAG unificato
                    data["tasks"][group_index]["rag_id"] = unified_rag_id
                    research_status[group_index]["rag_id"] = unified_rag_id
                else:
                    print(f"Errore nell'aggiornare il RAG unificato")
        except Exception as e:
            print(f"Errore nell'aggiornare il RAG unificato: {e}")
    
    # Aggiorna lo stato finale
    research_status[group_index]["in_progress"] = False
    research_status[group_index]["completed"] = True
    
    # Rimuovi il flag di ricerca in corso
    data["tasks"][group_index]["research_in_progress"] = False
    save_data(data)

def query_rag(group_index: int, query: str) -> Dict[str, Any]:
    """
    Esegue una query sul RAG di un gruppo specifico.
    
    Args:
        group_index: L'indice del gruppo di task
        query: La query da eseguire sul RAG
        
    Returns:
        Dizionario con il risultato della query
    """
    data = load_data()
    
    # Verifica se l'indice del gruppo è valido
    if not 0 <= group_index < len(data["tasks"]):
        return {"success": False, "error": "Gruppo non trovato"}
    
    task_group = data["tasks"][group_index]
    
    # Verifica se esiste un RAG per questo gruppo
    if not task_group.get("rag_id"):
        return {"success": False, "error": "Nessun RAG trovato per questo gruppo"}
    
    # Verifica che la query non sia vuota
    if not query.strip():
        return {"success": False, "error": "Query vuota"}
    
    # Esegui la query sul RAG
    try:
        rag_storage = RAGStorage()
        result = rag_storage.query_rag_index(task_group["rag_id"], query)
        
        return {
            "success": True, 
            "response": result.get("response", "Nessuna risposta trovata"),
            "sources": result.get("sources", [])
        }
    except Exception as e:
        return {"success": False, "error": str(e)}