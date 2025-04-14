from flask import Blueprint, request, redirect, url_for, jsonify, render_template
from webapp.models.research_manager import start_research, check_research_progress, query_rag
from webapp.models.data_manager import load_data

research_bp = Blueprint('research', __name__)

@research_bp.route("/start-research/<int:group_index>", methods=["POST"])
def start_research_route(group_index):
    """
    Gestisce l'avvio di una ricerca per un gruppo di task.
    """
    result = start_research(group_index)
    return jsonify(result)

@research_bp.route("/check-research-progress/<int:group_index>")
def check_research_progress_route(group_index):
    """
    Gestisce il controllo dello stato di avanzamento di una ricerca.
    """
    status = check_research_progress(group_index)
    return jsonify(status)

@research_bp.route("/query-task-rag/<int:group_index>")
def query_task_rag_route(group_index):
    """
    Mostra l'interfaccia per interrogare il RAG di un gruppo specifico.
    """
    data = load_data()
    
    # Verifica se l'indice del gruppo è valido
    if not 0 <= group_index < len(data["tasks"]):
        return redirect(url_for("main.index"))
    
    task_group = data["tasks"][group_index]
    
    # Verifica se esiste un RAG per questo gruppo
    if not task_group.get("rag_id"):
        return redirect(url_for("main.index"))
    
    return render_template("query_rag.html", 
                           task_group=task_group, 
                           group_index=group_index)

@research_bp.route("/query-rag/<int:group_index>", methods=["POST"])
def execute_rag_query_route(group_index):
    """
    Esegue una query sul RAG di un gruppo specifico.
    """
    # Ottieni la query dall'utente
    query = request.form.get("query", "").strip()
    
    result = query_rag(group_index, query)
    return jsonify(result)