from flask import Blueprint, request, redirect, url_for, jsonify
from webapp.models.task_manager import create_task, remove_task, generate_task_list
from webapp.models.data_manager import load_research_data, save_research_data

task_bp = Blueprint('task', __name__)

@task_bp.route("/research/<research_id>/generate-tasks", methods=["POST"])
def generate_tasks(research_id):
    """
    Gestisce la generazione di task basati su un prompt per una specifica ricerca.
    """
    prompt = request.form.get("prompt", "")
    if not prompt:
        return redirect(url_for("main.research_dashboard", research_id=research_id))
    
    # Carica i dati della ricerca
    research_data = load_research_data(research_id)
    if not research_data:
        return redirect(url_for("main.index"))
    
    # Genera i task
    task_list = generate_task_list(prompt)
    
    if task_list["success"]:
        # Aggiorna i dati della ricerca con i nuovi task
        if not research_data.get("tasks"):
            research_data["tasks"] = []
        
        research_data["tasks"] = task_list["tasks"]
        
        # Salva i dati aggiornati
        save_research_data(research_id, research_data)
    
    return redirect(url_for("main.research_dashboard", research_id=research_id))

@task_bp.route("/research/<research_id>/remove-task/<int:task_group_index>/<int:task_index>", methods=["POST"])
def remove_task_route(research_id, task_group_index, task_index):
    """
    Gestisce la rimozione di un task per una specifica ricerca.
    """
    # Carica i dati della ricerca
    research_data = load_research_data(research_id)
    if not research_data:
        return jsonify({"success": False, "error": "Ricerca non trovata"})
    
    # Verifica se gli indici sono validi
    if not 0 <= task_group_index < len(research_data.get("tasks", [])):
        return jsonify({"success": False, "error": "Gruppo di task non trovato"})
    
    task_group = research_data["tasks"][task_group_index]
    
    if not 0 <= task_index < len(task_group.get("tasks", [])):
        return jsonify({"success": False, "error": "Task non trovato"})
    
    # Rimuovi il task
    task_group["tasks"].pop(task_index)
    
    # Salva i dati aggiornati
    save_research_data(research_id, research_data)
    
    return jsonify({"success": True})

@task_bp.route("/research/<research_id>/add-custom-task", methods=["POST"])
def add_custom_task(research_id):
    """
    Gestisce l'aggiunta di un task personalizzato per una specifica ricerca.
    """
    data = request.json
    group_index = data.get('groupIndex')
    task_text = data.get('taskText')
    
    if group_index is None or task_text is None:
        return jsonify({"success": False, "error": "Parametri mancanti"}), 400
    
    # Carica i dati della ricerca
    research_data = load_research_data(research_id)
    if not research_data:
        return jsonify({"success": False, "error": "Ricerca non trovata"})
    
    # Verifica se l'indice del gruppo è valido
    if not 0 <= group_index < len(research_data.get("tasks", [])):
        return jsonify({"success": False, "error": "Gruppo di task non trovato"})
    
    # Aggiungi il task
    task_group = research_data["tasks"][group_index]
    
    # Crea un nuovo task
    new_task = {
        "description": task_text,
        "completed": False
    }
    
    task_group["tasks"].append(new_task)
    
    # Salva i dati aggiornati
    save_research_data(research_id, research_data)
    
    return jsonify({
        "success": True,
        "task": new_task,
        "index": len(task_group["tasks"]) - 1
    })