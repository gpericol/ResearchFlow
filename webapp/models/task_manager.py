from typing import Dict, Any, List, Optional

from agents.taskgenerator import generate_tasks
from webapp.models.data_manager import load_data, save_data

def create_task(group_index: int, task_text: str) -> Dict[str, Any]:
    """
    Crea un nuovo task in un gruppo specifico.
    
    Args:
        group_index: L'indice del gruppo in cui aggiungere il task
        task_text: Il testo del task da aggiungere
        
    Returns:
        Dizionario con il risultato dell'operazione
    """
    if task_text is None or not task_text.strip():
        return {"success": False, "error": "Testo del task mancante"}
    
    stored_data = load_data()
    
    if 0 <= group_index < len(stored_data["tasks"]):
        # Crea un nuovo task con la stessa struttura degli altri
        new_task = {
            "point": task_text,
            "completed": False,
            "notes": ""
        }
        
        # Aggiungi il task al gruppo appropriato
        stored_data["tasks"][group_index]["tasks"].append(new_task)
        # Salva i dati aggiornati
        save_data(stored_data)
        
        # Restituisci l'indice del nuovo task
        new_task_index = len(stored_data["tasks"][group_index]["tasks"]) - 1
        return {"success": True, "taskIndex": new_task_index}
    
    return {"success": False, "error": "Gruppo non trovato"}

def remove_task(task_group_index: int, task_index: int) -> Dict[str, Any]:
    """
    Rimuove un task da un gruppo.
    
    Args:
        task_group_index: L'indice del gruppo a cui appartiene il task
        task_index: L'indice del task da rimuovere
        
    Returns:
        Dizionario con il risultato dell'operazione
    """
    data = load_data()
    
    if 0 <= task_group_index < len(data["tasks"]):
        if 0 <= task_index < len(data["tasks"][task_group_index]["tasks"]):
            # Rimuovi il task specifico
            data["tasks"][task_group_index]["tasks"].pop(task_index)
            
            # Se non ci sono più task nel gruppo, rimuovi l'intero gruppo
            if not data["tasks"][task_group_index]["tasks"]:
                data["tasks"].pop(task_group_index)
                
            save_data(data)
            return {"success": True}
    
    return {"success": False, "error": "Task non trovato"}

def generate_task_list(prompt: str) -> Dict[str, Any]:
    """
    Genera una lista di task basata su un prompt.
    
    Args:
        prompt: Il prompt da cui generare i task
        
    Returns:
        Dizionario con il risultato dell'operazione
    """
    if not prompt.strip():
        return {"success": False, "error": "Prompt vuoto"}
    
    data = load_data()
    
    # Usa direttamente la funzione generate_tasks invece della classe
    # Passa alla funzione i task esistenti per evitare duplicati
    task_data = generate_tasks(prompt, existing_tasks=data.get("tasks", []))
    
    # Aggiorna l'ultimo prompt anche quando generiamo i task
    data["last_prompt"] = {
        "original": prompt,
        "refined": prompt
    }
    
    # Aggiungi i nuovi task alla task list unificata (che sarà sempre all'indice 0)
    if not data["tasks"]:
        # Se per qualche motivo non esiste una task list, creane una
        data["tasks"] = [{
            "prompt": "Task List Unificata",
            "tasks": task_data["research_points"],
            "research_in_progress": False,
            "rag_id": None
        }]
    else:
        # Aggiungi i nuovi task alla task list esistente
        data["tasks"][0]["tasks"].extend(task_data["research_points"])
    
    save_data(data)
    
    return {"success": True}