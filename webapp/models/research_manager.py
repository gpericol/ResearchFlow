import threading
import time
from datetime import datetime
from typing import Dict, Any, List, Optional

from agents.search_orchestrator import SearchOrchestrator
from agents.rag_storage import RAGStorage
from agents.research_logger import get_research_logger, CompleteAgentOutputRedirector
from webapp.models.data_manager import load_research_data, save_research_data

# Dizionario per tenere traccia delle ricerche in corso, organizzato per {research_id: {group_index: stato}}
research_status = {}

def start_research(research_id: str, group_index: int) -> Dict[str, Any]:
    """
    Avvia un processo di ricerca per tutti i task non completati in un gruppo.
    
    Args:
        research_id: L'ID della ricerca
        group_index: L'indice del gruppo di task per cui avviare la ricerca
        
    Returns:
        Dizionario con il risultato dell'operazione
    """
    # Inizializza il logger per questa ricerca
    logger = get_research_logger(research_id)
    logger.info(f"Avvio ricerca per il gruppo {group_index}")
    
    # Carica i dati della ricerca
    research_data = load_research_data(research_id)
    
    if not research_data:
        logger.error(f"Ricerca non trovata: {research_id}")
        return {"success": False, "error": "Ricerca non trovata"}
    
    # Verifica se l'indice del gruppo è valido
    if not 0 <= group_index < len(research_data.get("tasks", [])):
        logger.error(f"Gruppo non trovato: {group_index}")
        return {"success": False, "error": "Gruppo non trovato"}
    
    # Inizializza il dizionario per questo research_id se non esiste
    if research_id not in research_status:
        research_status[research_id] = {}
    
    # Verifica se c'è già una ricerca in corso per questo gruppo
    if group_index in research_status[research_id] and research_status[research_id][group_index]["in_progress"]:
        logger.warning(f"Ricerca già in corso per il gruppo {group_index}")
        return {"success": False, "error": "Ricerca già in corso per questo gruppo"}
    
    # Inizializza lo stato della ricerca
    task_group = research_data["tasks"][group_index]
    task_indices = [i for i, task in enumerate(task_group.get("tasks", [])) if not task.get("completed", False)]
    
    # Se non ci sono task da completare, restituisci un errore
    if not task_indices:
        logger.warning("Non ci sono task da completare")
        return {"success": False, "error": "Non ci sono task da completare"}
    
    # Inizializza lo stato della ricerca
    research_status[research_id][group_index] = {
        "in_progress": True,
        "completed": False,
        "completed_tasks": [],
        "current_task_index": None,
        "total_tasks": len(task_indices),
        "rag_id": None,
        "start_time": datetime.now().isoformat()
    }
    
    # Aggiungi research_in_progress al gruppo di task
    research_data["tasks"][group_index]["research_in_progress"] = True
    save_research_data(research_id, research_data)
    
    logger.info(f"Preparazione ricerca per {len(task_indices)} task")
    
    # Avvia un thread per eseguire la ricerca in background
    thread = threading.Thread(
        target=perform_research, 
        args=(research_id, group_index, task_indices)
    )
    thread.daemon = True  # Il thread terminerà quando termina l'applicazione principale
    thread.start()
    
    return {"success": True}

def check_research_progress(research_id: str, group_index: int) -> Dict[str, Any]:
    """
    Controlla lo stato di avanzamento di una ricerca.
    
    Args:
        research_id: L'ID della ricerca
        group_index: L'indice del gruppo di task per cui controllare lo stato
        
    Returns:
        Dizionario con lo stato della ricerca
    """
    # Se non esiste lo stato per questa ricerca o gruppo, restituisci un dizionario vuoto
    if research_id not in research_status or group_index not in research_status[research_id]:
        return {
            "in_progress": False,
            "completed": False,
            "completed_tasks": [],
            "current_task_index": None
        }
    
    # Restituisci lo stato attuale
    status = research_status[research_id][group_index].copy()
    
    # Rimuovi alcune informazioni interne che non servono al client
    if "start_time" in status:
        del status["start_time"]
    if "total_tasks" in status:
        del status["total_tasks"]
    
    return status

def perform_research(research_id: str, group_index: int, task_indices: List[int]) -> None:
    """
    Esegue la ricerca per tutti i task non completati in un gruppo.
    Questa funzione viene eseguita in un thread separato.
    
    Args:
        research_id: L'ID della ricerca
        group_index: L'indice del gruppo di task
        task_indices: Lista degli indici dei task da completare
    """
    # Ottieni il logger per questa ricerca
    logger = get_research_logger(research_id)
    logger.info(f"Inizio esecuzione ricerca per il gruppo {group_index}")
    
    # Reindirizza sia i print che i log degli agenti al file di log di questa ricerca
    redirector = CompleteAgentOutputRedirector(research_id)
    
    with redirector:
        # Carica i dati della ricerca
        research_data = load_research_data(research_id)
        
        if not research_data:
            logger.error(f"Errore: ricerca {research_id} non trovata")
            return
        
        task_group = research_data["tasks"][group_index]
        search_orchestrator = SearchOrchestrator()
        rag_storage = RAGStorage()
        all_results = []
        
        # Crea un ID univoco per il RAG di questa ricerca, basato sull'ID della ricerca
        rag_id = f"rag_{research_id}_{group_index}"
        logger.info(f"ID RAG per questa ricerca: {rag_id}")
        
        for i, task_index in enumerate(task_indices):
            # Aggiorna lo stato corrente
            research_status[research_id][group_index]["current_task_index"] = task_index
            
            task = task_group["tasks"][task_index]
            task_prompt = task.get("description", "")  # Usa "description" invece di "point"
            
            logger.info(f"Inizio ricerca per il task {task_index+1}/{len(task_indices)}: {task_prompt}")
            
            try:
                # Esegui la ricerca per il task corrente, passando research_id per il logging
                results = search_orchestrator.search(task_prompt, save_as_rag=False, research_id=research_id)
                
                # Aggiungi i risultati alla lista complessiva
                if results:
                    all_results.extend(results)
                    logger.info(f"Trovati {len(results)} risultati per il task {task_index}")
                else:
                    logger.warning(f"Nessun risultato trovato per il task {task_index}")
                
                # Marca il task come completato
                research_data["tasks"][group_index]["tasks"][task_index]["completed"] = True
                
                # Aggiungi il task alla lista dei task completati
                research_status[research_id][group_index]["completed_tasks"].append(task_index)
                logger.info(f"Task {task_index} completato")
                
                # Salva i dati aggiornati
                save_research_data(research_id, research_data)
                
                # Breve pausa per evitare di sovraccaricare il sistema
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Errore nella ricerca per il task {task_index}: {e}")
        
        # Una volta completati tutti i task, aggiungi i risultati al RAG specifico di questa ricerca
        if all_results:
            try:
                task_prompt = f"Ricerca per il gruppo: {task_group.get('prompt', 'Gruppo di task')}"
                logger.info(f"Creazione/aggiornamento dell'indice RAG con {len(all_results)} risultati totali")
                
                # Crea o aggiorna l'indice RAG per questa ricerca
                if rag_storage.load_rag_index(rag_id) is None:
                    new_rag_id = rag_storage.save_results_as_rag(task_prompt, all_results, metadata={"research_id": research_id})
                    if new_rag_id:
                        rag_id = new_rag_id
                        logger.info(f"Creato nuovo indice RAG: {rag_id}")
                else:
                    success = rag_storage.update_rag_index(rag_id, task_prompt, all_results)
                    if success:
                        logger.info(f"Aggiornato indice RAG esistente: {rag_id}")
                    else:
                        logger.error(f"Errore nell'aggiornare l'indice RAG: {rag_id}")
                
                # Aggiorna il gruppo con l'ID del RAG
                research_data["tasks"][group_index]["rag_id"] = rag_id
                research_status[research_id][group_index]["rag_id"] = rag_id
                
            except Exception as e:
                logger.error(f"Errore nella creazione/aggiornamento dell'indice RAG: {e}")
        else:
            logger.warning("Nessun risultato trovato in tutti i task, non è stato creato un indice RAG")
        
        # Aggiorna lo stato finale
        research_status[research_id][group_index]["in_progress"] = False
        research_status[research_id][group_index]["completed"] = True
        
        # Rimuovi il flag di ricerca in corso
        research_data["tasks"][group_index]["research_in_progress"] = False
        save_research_data(research_id, research_data)
        
        logger.info(f"Ricerca completata per il gruppo {group_index}")

def query_rag(research_id: str, group_index: int, query: str) -> Dict[str, Any]:
    """
    Esegue una query sul RAG di un gruppo specifico.
    
    Args:
        research_id: L'ID della ricerca
        group_index: L'indice del gruppo di task
        query: La query da eseguire sul RAG
        
    Returns:
        Dizionario con il risultato della query
    """
    # Ottieni il logger per questa ricerca
    logger = get_research_logger(research_id)
    logger.info(f"Esecuzione query RAG per il gruppo {group_index}: '{query}'")
    
    # Usa il redirector per catturare eventuali print durante la query
    with CompleteAgentOutputRedirector(research_id):
        # Carica i dati della ricerca
        research_data = load_research_data(research_id)
        
        if not research_data:
            logger.error("Ricerca non trovata")
            return {"success": False, "error": "Ricerca non trovata"}
        
        # Verifica se l'indice del gruppo è valido
        if not 0 <= group_index < len(research_data.get("tasks", [])):
            logger.error(f"Gruppo non trovato: {group_index}")
            return {"success": False, "error": "Gruppo non trovato"}
        
        task_group = research_data["tasks"][group_index]
        
        # Verifica se esiste un RAG per questo gruppo
        if not task_group.get("rag_id"):
            logger.error("Nessun RAG trovato per questo gruppo")
            return {"success": False, "error": "Nessun RAG trovato per questo gruppo"}
        
        # Verifica che la query non sia vuota
        if not query.strip():
            logger.warning("Query vuota")
            return {"success": False, "error": "Query vuota"}
        
        # Esegui la query sul RAG
        try:
            rag_storage = RAGStorage()
            logger.info(f"Interrogazione indice RAG: {task_group['rag_id']}")
            result = rag_storage.query_rag_index(task_group["rag_id"], query)
            
            if not result:
                logger.error("Errore durante l'interrogazione dell'indice RAG")
                return {"success": False, "error": "Errore durante l'interrogazione dell'indice RAG"}
            
            logger.info(f"Query completata, trovate {len(result.get('sources', []))} fonti")
            
            return {
                "success": True, 
                "response": result.get("response", "Nessuna risposta trovata"),
                "sources": result.get("sources", [])
            }
        except Exception as e:
            logger.error(f"Errore durante la query RAG: {e}")
            return {"success": False, "error": str(e)}