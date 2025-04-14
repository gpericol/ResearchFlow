#!/usr/bin/env python3
# agents/content_relevance.py

import openai
import logging
from typing import Dict, Any, Tuple, List, Optional
import json

# Import configurations
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import OPENAI_API_KEY, OPENAI_MODEL

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('content_relevance')

# Configure OpenAI
openai.api_key = OPENAI_API_KEY

class ContentRelevanceEvaluator:
    """
    Agente che valuta la rilevanza di un testo rispetto a un task specifico.
    Determina se il testo è utile per costruire una knowledge base per quel task.
    """
    
    def __init__(self, model=OPENAI_MODEL):
        """
        Inizializza l'evaluator di rilevanza.
        
        Args:
            model (str): Modello OpenAI da utilizzare
        """
        self.model = model
    
    def evaluate_relevance(self, task: str, content: str) -> Dict[str, Any]:
        """
        Valuta se un contenuto testuale è rilevante per un task specifico.
        
        Args:
            task (str): Descrizione del task per cui si sta costruendo la knowledge base
            content (str): Testo ripulito della pagina web da valutare
            
        Returns:
            Dict[str, Any]: Risultato della valutazione con punteggio di rilevanza e motivazione
        """
        if not content or not task:
            logger.warning("Task o contenuto mancante per la valutazione di rilevanza")
            return {
                "is_relevant": False,
                "relevance_score": 0.0,
                "reason": "Task o contenuto mancante"
            }
        
        # Tronca il contenuto se troppo lungo
        max_content_length = 8000  # Limite per evitare token troppo lunghi
        content_preview = content[:max_content_length]
        if len(content) > max_content_length:
            content_preview += "\n...[contenuto troncato]..."
            logger.info(f"Contenuto troncato da {len(content)} a {max_content_length} caratteri")
        
        # Crea il prompt per valutare la rilevanza
        system_message = """
        Sei un'IA specializzata nella valutazione della rilevanza di contenuti web rispetto a task specifici.
        Il tuo compito è determinare se il testo fornito è utile per costruire una knowledge base relativa al task specificato.
        
        Rispondi con un oggetto JSON con i seguenti campi:
        1. is_relevant: boolean (true/false)
        2. relevance_score: float (0.0-1.0, dove 0 significa completamente irrilevante e 1 significa estremamente rilevante)
        3. reason: string (spiegazione concisa della tua valutazione)
        4. key_points: array di stringhe (elenco di punti chiave rilevanti per il task identificati nel contenuto, massimo 5 punti)
        """
        
        user_message = f"""
        TASK: {task}
        
        CONTENUTO:
        {content_preview}
        
        Valuta la rilevanza di questo contenuto rispetto al task specificato.
        """
        
        try:
            response = openai.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.3,
                response_format={"type": "json_object"},
                max_tokens=1024
            )
            
            result_text = response.choices[0].message.content.strip()
            
            try:
                result = json.loads(result_text)
                
                # Assicurati che tutti i campi necessari siano presenti
                if 'is_relevant' not in result:
                    result['is_relevant'] = False
                if 'relevance_score' not in result:
                    result['relevance_score'] = 0.0
                if 'reason' not in result:
                    result['reason'] = "Nessuna motivazione fornita"
                if 'key_points' not in result:
                    result['key_points'] = []
                    
                # Normalizza il punteggio tra 0 e 1
                result['relevance_score'] = max(0.0, min(1.0, float(result['relevance_score'])))
                
                logger.info(f"Valutazione completata: Rilevanza {result['relevance_score']:.2f}, Rilevante: {result['is_relevant']}")
                return result
                
            except json.JSONDecodeError as e:
                logger.error(f"Errore nel parsing del risultato JSON: {e}")
                # Fallback manuale
                return {
                    "is_relevant": False,
                    "relevance_score": 0.0,
                    "reason": f"Errore nell'analisi della risposta: {e}",
                    "key_points": []
                }
                
        except Exception as e:
            logger.error(f"Errore durante la valutazione della rilevanza: {e}")
            return {
                "is_relevant": False,
                "relevance_score": 0.0,
                "reason": f"Errore durante la valutazione: {str(e)}",
                "key_points": []
            }
    
    def evaluate_content_sections(self, task: str, content: str, section_size: int = 2000) -> Dict[str, Any]:
        """
        Valuta la rilevanza di un contenuto lungo suddividendolo in sezioni.
        Utile per testi molto lunghi che supererebbero i limiti di token.
        
        Args:
            task (str): Descrizione del task per cui si sta costruendo la knowledge base
            content (str): Testo ripulito della pagina web da valutare
            section_size (int): Dimensione di ciascuna sezione in caratteri
            
        Returns:
            Dict[str, Any]: Risultato della valutazione con sezioni rilevanti
        """
        if not content or len(content) <= section_size:
            return self.evaluate_relevance(task, content)
        
        # Dividi il contenuto in sezioni più piccole
        sections = self._split_content(content, section_size)
        logger.info(f"Contenuto diviso in {len(sections)} sezioni per valutazione")
        
        section_results = []
        relevant_sections = []
        overall_relevant = False
        max_score = 0.0
        
        # Valuta ciascuna sezione
        for i, section in enumerate(sections):
            logger.info(f"Valutazione sezione {i+1}/{len(sections)}")
            result = self.evaluate_relevance(task, section)
            
            section_results.append({
                "section_index": i,
                "is_relevant": result["is_relevant"],
                "relevance_score": result["relevance_score"],
                "reason": result["reason"],
                "key_points": result.get("key_points", [])
            })
            
            # Aggiorna il punteggio massimo
            max_score = max(max_score, result["relevance_score"])
            
            # Se la sezione è rilevante, aggiungi alla lista
            if result["is_relevant"]:
                overall_relevant = True
                relevant_sections.append({
                    "section_index": i,
                    "section_text": section[:500] + "..." if len(section) > 500 else section,
                    "relevance_score": result["relevance_score"]
                })
        
        # Determina la rilevanza generale
        overall_result = {
            "is_relevant": overall_relevant,
            "relevance_score": max_score,
            "section_results": section_results,
            "relevant_sections": relevant_sections,
            "summary": f"Il contenuto contiene {len(relevant_sections)}/{len(sections)} sezioni rilevanti",
            "reason": "Almeno una sezione del contenuto è rilevante per il task" if overall_relevant else "Nessuna sezione del contenuto è rilevante per il task"
        }
        
        return overall_result
    
    def _split_content(self, content: str, section_size: int) -> List[str]:
        """
        Divide il contenuto in sezioni di dimensioni gestibili.
        
        Args:
            content (str): Il testo da dividere
            section_size (int): Dimensione massima di ciascuna sezione in caratteri
            
        Returns:
            List[str]: Lista di sezioni di testo
        """
        sections = []
        start = 0
        
        while start < len(content):
            end = start + section_size
            
            # Se non siamo alla fine, cerca un punto di interruzione logico
            if end < len(content):
                # Cerca il fine paragrafo più vicino
                paragraph_end = content.rfind('\n\n', start, end)
                sentence_end = content.rfind('. ', start, end)
                
                if paragraph_end > start + section_size // 2:
                    end = paragraph_end + 2
                elif sentence_end > start + section_size // 2:
                    end = sentence_end + 2
            
            sections.append(content[start:end].strip())
            start = end
        
        return sections

# Funzione di utilità per uso esterno
def evaluate_content_relevance(task: str, content: str, detailed: bool = False) -> Dict[str, Any]:
    """
    Funzione di utilità per valutare la rilevanza di un contenuto rispetto a un task.
    
    Args:
        task (str): Descrizione del task per cui si sta costruendo la knowledge base
        content (str): Testo ripulito della pagina web da valutare
        detailed (bool): Se True, restituisce una valutazione dettagliata per contenuti lunghi
        
    Returns:
        Dict[str, Any]: Risultato della valutazione di rilevanza
    """
    evaluator = ContentRelevanceEvaluator()
    
    if detailed and len(content) > 2000:
        return evaluator.evaluate_content_sections(task, content)
    else:
        return evaluator.evaluate_relevance(task, content)

def format_relevance_result(result: Dict[str, Any]) -> str:
    """
    Formatta il risultato della valutazione di rilevanza in un formato leggibile.
    
    Args:
        result (Dict[str, Any]): Risultato della valutazione di rilevanza
        
    Returns:
        str: Testo formattato con i risultati
    """
    if not result:
        return "Nessun risultato di valutazione disponibile."
    
    formatted_text = "Valutazione di Rilevanza del Contenuto:\n\n"
    
    # Se è un risultato semplice
    if 'section_results' not in result:
        formatted_text += f"Rilevanza: {result['relevance_score']:.2f}/1.00\n"
        formatted_text += f"È Rilevante: {'Sì' if result['is_relevant'] else 'No'}\n"
        formatted_text += f"Motivazione: {result['reason']}\n\n"
        
        if 'key_points' in result and result['key_points']:
            formatted_text += "Punti Chiave Rilevanti:\n"
            for i, point in enumerate(result['key_points'], 1):
                formatted_text += f"{i}. {point}\n"
    
    # Se è un risultato dettagliato con più sezioni
    else:
        formatted_text += f"Rilevanza Complessiva: {result['relevance_score']:.2f}/1.00\n"
        formatted_text += f"È Rilevante: {'Sì' if result['is_relevant'] else 'No'}\n"
        formatted_text += f"Riepilogo: {result['summary']}\n"
        formatted_text += f"Motivazione: {result['reason']}\n\n"
        
        if result['relevant_sections']:
            formatted_text += f"Sezioni Rilevanti Trovate: {len(result['relevant_sections'])}\n\n"
            for i, section in enumerate(result['relevant_sections']):
                formatted_text += f"Sezione {section['section_index']+1} - Rilevanza: {section['relevance_score']:.2f}\n"
                formatted_text += f"Anteprima: {section['section_text'][:150]}...\n\n"
    
    return formatted_text

# Test dell'evaluator
if __name__ == "__main__":
    import sys
    from content_cleaner import clean_webpage_content
    from web_scraper import scrape_webpage
    
    if len(sys.argv) > 2:
        task = sys.argv[1]
        url = sys.argv[2]
        print(f"Valutazione della rilevanza del contenuto di {url} per il task: {task}")
        
        # Ottieni e pulisci il contenuto della pagina
        raw_content = scrape_webpage(url)
        clean_content = clean_webpage_content(raw_content)
        
        # Valuta la rilevanza
        result = evaluate_content_relevance(task, clean_content, detailed=True)
        
        # Mostra i risultati
        print(format_relevance_result(result))
    else:
        print("Utilizzo: python content_relevance.py \"descrizione del task\" <url>")