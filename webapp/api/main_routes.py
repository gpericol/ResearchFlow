from flask import Blueprint, render_template, request, redirect, url_for, jsonify
from webapp.models.data_manager import load_data
from webapp.models.prompt_manager import process_questions, process_answers

main_bp = Blueprint('main', __name__)

@main_bp.route("/", methods=["GET", "POST"])
def index():
    """
    Pagina principale dell'applicazione.
    """
    data = load_data()
    # Usa l'ultimo prompt salvato invece di quello della sessione
    last_prompt = data["last_prompt"]["refined"]
    return render_template("index.html", 
                         refined_prompt=last_prompt, 
                         saved_data=data)

@main_bp.route("/questions", methods=["POST"])
def questions():
    """
    Gestisce la generazione di domande per il brainstorming.
    """
    user_prompt = request.form.get("prompt", "")
    if not user_prompt:
        return redirect(url_for("main.index"))

    questions = process_questions(user_prompt)
    return render_template("questions.html", questions=questions, original_prompt=user_prompt)

@main_bp.route("/submit_answers", methods=["POST"])
def submit_answers():
    """
    Gestisce l'invio delle risposte alle domande e la generazione del prompt raffinato.
    """
    original_prompt = request.form.get("original_prompt", "")
    answers = {key: request.form[key] for key in request.form if key.startswith("answer_")}
    
    result = process_answers(original_prompt, answers)
    
    if not result["success"]:
        # Gestione dell'errore, se necessario
        pass
    
    return redirect(url_for("main.index"))