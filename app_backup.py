from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from agents.brainstorming import generate_questions, generate_refined_prompt
from agents.taskgenerator import generate_tasks
from agents.search_orchestrator import SearchOrchestrator
from agents.rag_storage import RAGStorage
import os
from dotenv import load_dotenv
import json
import threading
import time
from datetime import datetime

app = Flask(__name__)
load_dotenv()
app.secret_key = os.getenv("SECRET_KEY")

# Costante per l'ID del RAG unificato
UNIFIED_RAG_ID = "unified_rag"

# Dizionario per tenere traccia delle ricerche in corso
research_status = {}

def load_data():
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

def save_data(data):
    os.makedirs('output', exist_ok=True)
    data_file = os.path.join('output', 'data.json')
    with open(data_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

@app.route("/", methods=["GET", "POST"])
def index():
    data = load_data()
    # Usa l'ultimo prompt salvato invece di quello della sessione
    last_prompt = data["last_prompt"]["refined"]
    return render_template("index.html", 
                         refined_prompt=last_prompt, 
                         saved_data=data)

@app.route("/questions", methods=["POST"])
def questions():
    user_prompt = request.form.get("prompt", "")
    if not user_prompt:
        return redirect(url_for("index"))

    questions = generate_questions(user_prompt)
    return render_template("questions.html", questions=questions, original_prompt=user_prompt)

@app.route("/submit_answers", methods=["POST"])
def submit_answers():
    original_prompt = request.form.get("original_prompt", "")
    answers = {key: request.form[key] for key in request.form if key.startswith("answer_")}
    refined_prompt = generate_refined_prompt(original_prompt, answers)

    data = load_data()
    # Aggiorna l'ultimo prompt
    data["last_prompt"] = {
        "original": original_prompt,
        "refined": refined_prompt
    }
    # Aggiungi alla cronologia
    data["prompts"].append({
        "original": original_prompt,
        "refined": refined_prompt,
        "answers": answers
    })
    save_data(data)

    return redirect(url_for("index"))

@app.route("/generate-tasks", methods=["POST"])
def generate_task_list():
    prompt = request.form.get("prompt", "")
    if not prompt:
        return redirect(url_for("index"))
    
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
    
    return redirect(url_for("index"))

@app.route("/remove-task/<int:task_group_index>/<int:task_index>", methods=["POST"])
def remove_task(task_group_index, task_index):
    data = load_data()
    
    if 0 <= task_group_index < len(data["tasks"]):
        if 0 <= task_index < len(data["tasks"][task_group_index]["tasks"]):
            # Rimuovi il task specifico
            data["tasks"][task_group_index]["tasks"].pop(task_index)
            
            # Se non ci sono più task nel gruppo, rimuovi l'intero gruppo
            if not data["tasks"][task_group_index]["tasks"]:
                data["tasks"].pop(task_group_index)
                
            save_data(data)
            return jsonify({"success": True})
    
    return jsonify({"success": False}), 404

@app.route("/add-custom-task", methods=["POST"])
def add_custom_task():
    data = request.json
    group_index = data.get('groupIndex')
    task_text = data.get('taskText')
    
    if group_index is None or task_text is None:
        return jsonify({"success": False, "error": "Parametri mancanti"}), 400
    
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
        return jsonify({"success": True, "taskIndex": new_task_index})
    
    return jsonify({"success": False, "error": "Gruppo non trovato"}), 404

@app.route("/start-research/<int:group_index>", methods=["POST"])
def start_research(group_index):
    """
    Avvia un processo di ricerca per tutti i task non completati in un gruppo.
    """
    data = load_data()
    
    # Verifica se l'indice del gruppo è valido
    if not 0 <= group_index < len(data["tasks"]):
        return jsonify({"success": False, "error": "Gruppo non trovato"}), 404
    
    # Verifica se c'è già una ricerca in corso per questo gruppo
    if group_index in research_status and research_status[group_index]["in_progress"]:
        return jsonify({"success": False, "error": "Ricerca già in corso per questo gruppo"}), 400
    
    # Inizializza lo stato della ricerca
    task_group = data["tasks"][group_index]
    task_indices = [i for i, task in enumerate(task_group["tasks"]) if not task["completed"]]
    
    # Se non ci sono task da completare, restituisci un errore
    if not task_indices:
        return jsonify({"success": False, "error": "Non ci sono task da completare"}), 400
    
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
    
    return jsonify({"success": True})

@app.route("/check-research-progress/<int:group_index>")
def check_research_progress(group_index):
    """
    Controlla lo stato di avanzamento di una ricerca.
    """
    # Se non esiste lo stato per questo gruppo, restituisci un errore
    if group_index not in research_status:
        return jsonify({
            "in_progress": False,
            "completed": False,
            "completed_tasks": [],
            "current_task_index": None
        })
    
    # Restituisci lo stato attuale
    status = research_status[group_index].copy()
    
    # Rimuovi alcune informazioni interne che non servono al client
    if "start_time" in status:
        del status["start_time"]
    if "total_tasks" in status:
        del status["total_tasks"]
    
    return jsonify(status)

@app.route("/query-task-rag/<int:group_index>")
def query_task_rag(group_index):
    """
    Mostra l'interfaccia per interrogare il RAG di un gruppo specifico.
    """
    data = load_data()
    
    # Verifica se l'indice del gruppo è valido
    if not 0 <= group_index < len(data["tasks"]):
        return redirect(url_for("index"))
    
    task_group = data["tasks"][group_index]
    
    # Verifica se esiste un RAG per questo gruppo
    if not task_group.get("rag_id"):
        return redirect(url_for("index"))
    
    return render_template("query_rag.html", 
                           task_group=task_group, 
                           group_index=group_index)

@app.route("/query-rag/<int:group_index>", methods=["POST"])
def execute_rag_query(group_index):
    """
    Esegue una query sul RAG di un gruppo specifico.
    """
    data = load_data()
    
    # Verifica se l'indice del gruppo è valido
    if not 0 <= group_index < len(data["tasks"]):
        return jsonify({"success": False, "error": "Gruppo non trovato"}), 404
    
    task_group = data["tasks"][group_index]
    
    # Verifica se esiste un RAG per questo gruppo
    if not task_group.get("rag_id"):
        return jsonify({"success": False, "error": "Nessun RAG trovato per questo gruppo"}), 404
    
    # Ottieni la query dall'utente
    query = request.form.get("query", "").strip()
    if not query:
        return jsonify({"success": False, "error": "Query vuota"}), 400
    
    # Esegui la query sul RAG
    try:
        rag_storage = RAGStorage()
        result = rag_storage.query_rag_index(task_group["rag_id"], query)
        
        return jsonify({
            "success": True, 
            "response": result.get("response", "Nessuna risposta trovata"),
            "sources": result.get("sources", [])
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

def perform_research(group_index, task_indices):
    """
    Esegue la ricerca per tutti i task non completati in un gruppo.
    Questa funzione viene eseguita in un thread separato.
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

if __name__ == "__main__":
    app.run(debug=True)
