from flask import Blueprint, render_template, request, redirect, url_for, jsonify
from webapp.models.data_manager import get_research_list, create_new_research, load_research_data, save_research_data
from webapp.models.prompt_manager import process_questions, process_answers

main_bp = Blueprint('main', __name__)

@main_bp.route("/", methods=["GET"])
def index():
    """
    Pagina principale che mostra la lista delle ricerche disponibili.
    """
    # Ottieni la lista delle ricerche
    researches = get_research_list()
    return render_template("research_list.html", researches=researches)

@main_bp.route("/create-research", methods=["POST"])
def create_research():
    """
    Gestisce la creazione di una nuova ricerca.
    """
    title = request.form.get("title", "").strip()
    if not title:
        title = "Nuova ricerca"
    
    # Crea una nuova ricerca
    research_id = create_new_research(title)
    
    # Reindirizza alla pagina della ricerca
    return redirect(url_for("main.research_dashboard", research_id=research_id))

@main_bp.route("/research/<research_id>", methods=["GET"])
def research_dashboard(research_id):
    """
    Dashboard di una specifica ricerca.
    """
    # Carica i dati della ricerca
    research_data = load_research_data(research_id)
    
    if not research_data:
        # Se la ricerca non esiste, torna alla pagina principale
        return redirect(url_for("main.index"))
    
    # Usa l'ultimo prompt salvato
    last_prompt = research_data.get("last_prompt", {}).get("refined", "")
    
    return render_template("index.html", 
                         refined_prompt=last_prompt, 
                         saved_data=research_data,
                         research_id=research_id)

@main_bp.route("/research/<research_id>/questions", methods=["POST"])
def research_questions(research_id):
    """
    Gestisce la generazione di domande per il brainstorming di una specifica ricerca.
    """
    user_prompt = request.form.get("prompt", "")
    if not user_prompt:
        return redirect(url_for("main.research_dashboard", research_id=research_id))

    questions = process_questions(user_prompt)
    return render_template("questions.html", 
                         questions=questions, 
                         original_prompt=user_prompt,
                         research_id=research_id)

@main_bp.route("/research/<research_id>/submit_answers", methods=["POST"])
def research_submit_answers(research_id):
    """
    Gestisce l'invio delle risposte alle domande per una specifica ricerca.
    """
    original_prompt = request.form.get("original_prompt", "")
    answers = {key: request.form[key] for key in request.form if key.startswith("answer_")}
    
    # Elabora le risposte per ottenere il prompt raffinato
    result = process_answers(original_prompt, answers)
    
    if result["success"]:
        # Carica i dati della ricerca
        research_data = load_research_data(research_id)
        
        if not research_data:
            return redirect(url_for("main.index"))
        
        # Aggiorna l'ultimo prompt
        research_data["last_prompt"] = {
            "original": original_prompt,
            "refined": result["refined_prompt"]
        }
        
        # Aggiungi alla cronologia dei prompt
        research_data["prompts"].append({
            "original": original_prompt,
            "refined": result["refined_prompt"],
            "answers": answers
        })
        
        # Salva i dati aggiornati
        save_research_data(research_id, research_data)
    
    return redirect(url_for("main.research_dashboard", research_id=research_id))