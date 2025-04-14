from openai import OpenAI
from config import OPENAI_API_KEY, OPENAI_MODEL

client = OpenAI(api_key=OPENAI_API_KEY)

def generate_questions(prompt: str) -> list:
    system_prompt = """
Agisci come un esperto stratega e problem solver. Hai il compito di aiutare un utente a chiarire e raffinare una richiesta che al momento è troppo generica, vaga o poco focalizzata.

Il tuo obiettivo è ottenere rapidamente le informazioni minime necessarie per trasformare quella richiesta in un compito chiaro, mirato, e direttamente azionabile.

Genera esattamente 3 domande che ti servono per capire:
1. Qual è il vero obiettivo dell’utente?
2. Quali sono i vincoli o il contesto rilevante?
3. Cosa manca per trasformare la richiesta in qualcosa di eseguibile?

Evita domande teoriche, aperte o speculative. Sii diretto, concreto, essenziale. Le tue domande devono avere un chiaro valore operativo.
"""

    user_prompt = f"""Richiesta iniziale dell’utente: "{prompt}" """

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.7
    )

    content = response.choices[0].message.content
    questions = [q.strip("- ").strip() for q in content.split("\n") if q.strip()]
    return questions


def generate_refined_prompt(original_prompt: str, answers: dict) -> str:
    question_answer_pairs = "\n".join(
        f"{i+1}. {answers[key]}" for i, key in enumerate(sorted(answers))
    )

    system_prompt = """
Agisci come un esperto che trasforma richieste vaghe in istruzioni operative chiare e realizzabili.

Hai ricevuto una richiesta iniziale seguita da alcune risposte a domande di chiarimento. Il tuo obiettivo è scrivere una nuova versione della richiesta che sia precisa, focalizzata sull’obiettivo, e utile per passare direttamente all’azione.

Ignora ridondanze, vai dritto al punto, mantieni il tono professionale e pragmatico.
"""

    user_prompt = f"""Richiesta iniziale: "{original_prompt}"\n\nRisposte fornite:\n{question_answer_pairs}\n\nGenera una versione migliorata e operativa della richiesta."""

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.7
    )

    return response.choices[0].message.content.strip()
