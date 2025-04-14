from flask import Blueprint, request, redirect, url_for, jsonify
from webapp.models.task_manager import create_task, remove_task, generate_task_list

task_bp = Blueprint('task', __name__)

@task_bp.route("/generate-tasks", methods=["POST"])
def generate_tasks():
    """
    Gestisce la generazione di task basati su un prompt.
    """
    prompt = request.form.get("prompt", "")
    if not prompt:
        return redirect(url_for("main.index"))
    
    result = generate_task_list(prompt)
    
    if not result["success"]:
        # Gestione dell'errore, se necessario
        pass
    
    return redirect(url_for("main.index"))

@task_bp.route("/remove-task/<int:task_group_index>/<int:task_index>", methods=["POST"])
def remove_task_route(task_group_index, task_index):
    """
    Gestisce la rimozione di un task.
    """
    result = remove_task(task_group_index, task_index)
    return jsonify(result)

@task_bp.route("/add-custom-task", methods=["POST"])
def add_custom_task():
    """
    Gestisce l'aggiunta di un task personalizzato.
    """
    data = request.json
    group_index = data.get('groupIndex')
    task_text = data.get('taskText')
    
    if group_index is None or task_text is None:
        return jsonify({"success": False, "error": "Parametri mancanti"}), 400
    
    result = create_task(group_index, task_text)
    return jsonify(result)