from flask import Blueprint, request, redirect, url_for, jsonify, render_template
from webapp.models.research_manager import start_research, check_research_progress, query_rag
from webapp.models.data_manager import load_research_data, save_research_data

research_bp = Blueprint('research', __name__)

@research_bp.route("/<research_id>/start-research/<int:group_index>", methods=["POST"])
def start_research_route(research_id, group_index):
    """
    Gestisce l'avvio di una ricerca per un gruppo di task in una specifica ricerca.
    """
    result = start_research(research_id, group_index)
    return jsonify(result)

@research_bp.route("/<research_id>/check-research-progress/<int:group_index>")
def check_research_progress_route(research_id, group_index):
    """
    Gestisce il controllo dello stato di avanzamento di una ricerca.
    """
    status = check_research_progress(research_id, group_index)
    return jsonify(status)

@research_bp.route("/<research_id>/query-task-rag/<int:group_index>")
def query_task_rag_route(research_id, group_index):
    """
    Mostra l'interfaccia per interrogare il RAG di un gruppo specifico.
    """
    research_data = load_research_data(research_id)
    
    if not research_data:
        return redirect(url_for("main.index"))
    
    # Verifica se l'indice del gruppo è valido
    if not 0 <= group_index < len(research_data.get("tasks", [])):
        return redirect(url_for("main.research_dashboard", research_id=research_id))
    
    task_group = research_data["tasks"][group_index]
    
    # Verifica se esiste un RAG per questo gruppo
    if not task_group.get("rag_id"):
        return redirect(url_for("main.research_dashboard", research_id=research_id))
    
    return render_template("query_rag.html", 
                           task_group=task_group, 
                           group_index=group_index,
                           research_id=research_id)

@research_bp.route("/<research_id>/query-rag/<int:group_index>", methods=["POST"])
def execute_rag_query_route(research_id, group_index):
    """
    Esegue una query sul RAG di un gruppo specifico.
    """
    # Ottieni la query dall'utente
    query = request.form.get("query", "").strip()
    
    result = query_rag(research_id, group_index, query)
    return jsonify(result)