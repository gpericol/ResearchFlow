from typing import Dict, Any, List

from agents.brainstorming import generate_questions, generate_refined_prompt
from webapp.models.data_manager import load_data, save_data

def process_questions(original_prompt: str) -> List[str]:
    """
    Genera domande per il processo di brainstorming basate su un prompt iniziale.
    
    Args:
        original_prompt: Il prompt originale dell'utente
        
    Returns:
        Lista di domande generate
    """
    if not original_prompt.strip():
        return []
    
    return generate_questions(original_prompt)

def process_answers(original_prompt: str, answers: Dict[str, str]) -> Dict[str, Any]:
    """
    Elabora le risposte alle domande e genera un prompt raffinato.
    
    Args:
        original_prompt: Il prompt originale dell'utente
        answers: Dizionario delle risposte alle domande
        
    Returns:
        Dizionario con il risultato dell'operazione
    """
    if not original_prompt.strip():
        return {"success": False, "error": "Prompt originale mancante"}
    
    if not answers:
        return {"success": False, "error": "Risposte mancanti"}
    
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
    
    return {"success": True, "refined_prompt": refined_prompt}