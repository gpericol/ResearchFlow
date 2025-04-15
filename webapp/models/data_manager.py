import os
import json
import glob
from typing import Dict, Any, List, Optional
import uuid
import time

# Directory per salvare i dati delle ricerche
RESEARCHES_DIR = os.path.join('output', 'researches')

def get_research_list() -> List[Dict[str, Any]]:
    """
    Restituisce la lista di tutte le ricerche salvate.
    """
    researches = []
    
    # Crea la directory se non esiste
    os.makedirs(RESEARCHES_DIR, exist_ok=True)
    
    # Cerca tutti i file JSON nella directory delle ricerche
    research_files = glob.glob(os.path.join(RESEARCHES_DIR, '*.json'))
    
    for file_path in research_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                research_data = json.load(f)
                
                # Estrai l'ID dalla filename
                filename = os.path.basename(file_path)
                research_id = os.path.splitext(filename)[0]
                
                # Aggiungi le informazioni di base sulla ricerca
                researches.append({
                    'id': research_id,
                    'title': research_data.get('title', 'Ricerca senza titolo'),
                    'created_at': research_data.get('created_at', ''),
                    'prompt': research_data.get('last_prompt', {}).get('refined', '')
                })
        except Exception as e:
            print(f"Errore nel caricamento del file {file_path}: {str(e)}")
    
    # Ordina per data di creazione (più recenti prima)
    researches.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    
    return researches

def create_new_research(title: str) -> str:
    """
    Crea una nuova ricerca vuota.
    
    Args:
        title (str): Titolo della ricerca
        
    Returns:
        str: ID della nuova ricerca
    """
    # Genera un ID univoco
    research_id = str(uuid.uuid4())
    
    # Prepara i dati iniziali
    data = {
        "title": title,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "last_prompt": {"original": "", "refined": ""},
        "prompts": [],
        "tasks": [{
            "prompt": "Task List",
            "tasks": [],
            "research_in_progress": False,
            "rag_id": None
        }]
    }
    
    # Salva i dati
    save_research_data(research_id, data)
    
    return research_id

def load_research_data(research_id: str) -> Optional[Dict[str, Any]]:
    """
    Carica i dati di una specifica ricerca.
    
    Args:
        research_id (str): ID della ricerca da caricare
        
    Returns:
        Optional[Dict[str, Any]]: Dati della ricerca o None se non trovata
    """
    file_path = os.path.join(RESEARCHES_DIR, f"{research_id}.json")
    
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Errore nel caricamento del file {file_path}: {str(e)}")
            return None
    
    return None

def save_research_data(research_id: str, data: Dict[str, Any]) -> None:
    """
    Salva i dati di una specifica ricerca.
    
    Args:
        research_id (str): ID della ricerca
        data (Dict[str, Any]): Dati da salvare
    """
    os.makedirs(RESEARCHES_DIR, exist_ok=True)
    file_path = os.path.join(RESEARCHES_DIR, f"{research_id}.json")
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# Funzioni di compatibilità per il vecchio sistema a singola ricerca
def load_data() -> Dict[str, Any]:
    """
    Carica i dati dal file JSON, gestendo anche la conversione
    da formati vecchi a nuovi.
    Per compatibilità con il vecchio sistema.
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
    Per compatibilità con il vecchio sistema.
    """
    os.makedirs('output', exist_ok=True)
    data_file = os.path.join('output', 'data.json')
    with open(data_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)