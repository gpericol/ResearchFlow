from typing import Dict, Any, List, Optional

from agents.taskgenerator import generate_tasks
from webapp.models.data_manager import load_research_data, save_research_data

def create_task(research_id: str, group_index: int, task_text: str) -> Dict[str, Any]:
    """
    Crea un nuovo task in un gruppo specifico di una ricerca.
    
    Args:
        research_id: L'ID della ricerca
        group_index: L'indice del gruppo in cui aggiungere il task
        task_text: Il testo del task da aggiungere
        
    Returns:
        Dizionario con il risultato dell'operazione
    """
    if task_text is None or not task_text.strip():
        return {"success": False, "error": "Testo del task mancante"}
    
    # Carica i dati della ricerca
    research_data = load_research_data(research_id)
    
    if not research_data:
        return {"success": False, "error": "Ricerca non trovata"}
    
    if 0 <= group_index < len(research_data.get("tasks", [])):
        # Crea un nuovo task
        new_task = {
            "description": task_text,
            "completed": False
        }
        
        # Aggiungi il task al gruppo appropriato
        research_data["tasks"][group_index]["tasks"].append(new_task)
        
        # Salva i dati aggiornati
        save_research_data(research_id, research_data)
        
        # Restituisci il nuovo task e il suo indice
        new_task_index = len(research_data["tasks"][group_index]["tasks"]) - 1
        return {"success": True, "task": new_task, "index": new_task_index}
    
    return {"success": False, "error": "Gruppo non trovato"}

def remove_task(research_id: str, task_group_index: int, task_index: int) -> Dict[str, Any]:
    """
    Rimuove un task da un gruppo di una ricerca.
    
    Args:
        research_id: L'ID della ricerca
        task_group_index: L'indice del gruppo a cui appartiene il task
        task_index: L'indice del task da rimuovere
        
    Returns:
        Dizionario con il risultato dell'operazione
    """
    # Carica i dati della ricerca
    research_data = load_research_data(research_id)
    
    if not research_data:
        return {"success": False, "error": "Ricerca non trovata"}
    
    if 0 <= task_group_index < len(research_data.get("tasks", [])):
        if 0 <= task_index < len(research_data["tasks"][task_group_index].get("tasks", [])):
            # Rimuovi il task specifico
            research_data["tasks"][task_group_index]["tasks"].pop(task_index)
            
            # Se non ci sono più task nel gruppo, rimuovi l'intero gruppo
            if not research_data["tasks"][task_group_index]["tasks"]:
                research_data["tasks"].pop(task_group_index)
                
            save_research_data(research_id, research_data)
            return {"success": True}
    
    return {"success": False, "error": "Task non trovato"}

def generate_task_list(prompt: str, research_id: str = None) -> Dict[str, Any]:
    """
    Genera una lista di task basata su un prompt.
    
    Args:
        prompt: Il prompt da cui generare i task
        research_id: L'ID della ricerca (opzionale, per compatibilità)
        
    Returns:
        Dizionario con il risultato dell'operazione
    """
    if not prompt.strip():
        return {"success": False, "error": "Prompt vuoto"}
    
    # Usa direttamente la funzione generate_tasks
    task_data = generate_tasks(prompt)
    
    # Crea una nuova task list basata sul prompt
    task_list = [{
        "prompt": prompt,
        "tasks": task_data["research_points"],
        "research_in_progress": False,
        "rag_id": None
    }]
    
    return {"success": True, "tasks": task_list}