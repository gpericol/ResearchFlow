import os
import json
from typing import Dict, Any, List

def load_data() -> Dict[str, Any]:
    """
    Carica i dati dal file JSON, gestendo anche la conversione
    da formati vecchi a nuovi.
    """
    data_file = os.path.join('output', 'data.json')
    if os.path.exists(data_file):
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Se il formato è ancora vecchio, converti alla nuova struttura
            if "tasks" in data and isinstance(data["tasks"], list) and all("prompt" in task for task in data["tasks"]):
                # Formato vecchio con task list multiple
                unified_tasks = {
                    "prompt": "Task List Unificata",
                    "tasks": [],
                    "research_in_progress": False,
                    "rag_id": None
                }
                
                # Unisci tutti i task dalle liste separate
                for task_group in data["tasks"]:
                    for task in task_group.get("tasks", []):
                        unified_tasks["tasks"].append(task)
                    
                    # Se un gruppo aveva un RAG ID, assegnalo alla task list unificata
                    if task_group.get("rag_id"):
                        unified_tasks["rag_id"] = task_group["rag_id"]
                
                # Sostituisci la vecchia struttura con quella nuova
                data["tasks"] = [unified_tasks]
            return data
    return {
        "last_prompt": {"original": "", "refined": ""},
        "prompts": [], 
        "tasks": [{
            "prompt": "Task List Unificata",
            "tasks": [],
            "research_in_progress": False,
            "rag_id": None
        }]
    }

def save_data(data: Dict[str, Any]) -> None:
    """
    Salva i dati nel file JSON.
    """
    os.makedirs('output', exist_ok=True)
    data_file = os.path.join('output', 'data.json')
    with open(data_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)