from openai import OpenAI
from config import OPENAI_API_KEY, OPENAI_MODEL
from datetime import datetime
import json
import os

client = OpenAI(api_key=OPENAI_API_KEY)

def ensure_output_dir():
    output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")
    os.makedirs(output_dir, exist_ok=True)
    return output_dir

def generate_tasks(refined_prompt: str, existing_tasks: list = None) -> dict:
    # Assicurati che la directory di output esista
    ensure_output_dir()
    
    # Prepara un elenco di task esistenti per evitare duplicati
    existing_tasks_text = ""
    if existing_tasks and len(existing_tasks) > 0:
        existing_tasks_points = []
        # Con la nuova struttura, abbiamo un'unica task list
        for task_group in existing_tasks:
            for task in task_group.get("tasks", []):
                existing_tasks_points.append(task.get("point", ""))
        
        if existing_tasks_points:
            existing_tasks_text = "Task già esistenti (da evitare di duplicare):\n" + "\n".join(existing_tasks_points)

    system_prompt = """
    Agisci come un ricercatore esperto. Data una richiesta, crea una lista ordinata 
    di punti da investigare o approfondire. I task devono:
    - Essere originali e non ripetere task esistenti o simili
    - Essere ordinati in modo logico
    - Procedere dal generale al particolare
    - Essere formulati come punti di ricerca
    - Essere indipendenti e autocontenuti
    - Non devono essere numerati
    
    Non includere stime temporali o priorità numeriche.
    
    IMPORTANTE: Se vengono forniti task già esistenti, assicurati di creare nuovi task che:
    1. Non siano semanticamente simili a quelli esistenti
    2. Esplorino aspetti diversi o complementari della ricerca
    3. Non contengano informazioni duplicate o ridondanti
    """

    # Prepara il prompt utente con o senza i task esistenti
    user_prompt = f"Crea una lista di punti da ricercare per: {refined_prompt}"
    if existing_tasks_text:
        user_prompt += f"\n\n{existing_tasks_text}"

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.7
    )

    task_data = {
        "refined_prompt": refined_prompt,
        "created_at": datetime.now().isoformat(),
        "research_points": [
            {
                "point": point.strip().lstrip("-").strip(),
                "completed": False,
                "notes": ""
            }
            for point in response.choices[0].message.content.split("\n")
            if point.strip()
        ]
    }

    return task_data