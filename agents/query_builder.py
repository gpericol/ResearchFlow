# agent/query_builder.py

from openai import OpenAI
from config import OPENAI_API_KEY, OPENAI_MODEL

client = OpenAI(api_key=OPENAI_API_KEY)

def build_google_query(task: str, context: str = "", previous_queries: list[str] = None, temperature: float = 0.3) -> str:
    """
    Genera una query Google mirata, tenendo conto del contesto e delle query già usate.
    """
    if previous_queries is None:
        previous_queries = []

    system_prompt = """
    Sei un assistente esperto in ricerche online.
    Il tuo compito è trasformare un obiettivo specifico in una query ottimizzata per Google.

    La query deve:
    - usare parole chiave precise
    - essere breve e mirata
    - non contenere testo in eccesso o frasi complete
    - essere diversa dalle query già provate (se presenti)

    Rispondi con **solo la query**, senza virgolette, senza markdown, senza spiegazioni.
    """

    queries_str = "\n- " + "\n- ".join(previous_queries) if previous_queries else "Nessuna."

    user_prompt = f"""
    Subtask: {task}

    Contesto del progetto:
    {context}

    Query già tentate (da evitare):
    {queries_str}

    Genera una nuova query originale da usare su Google.
    """

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt.strip()},
            {"role": "user", "content": user_prompt.strip()},
        ],
        temperature=temperature,
    )

    return response.choices[0].message.content.strip()
