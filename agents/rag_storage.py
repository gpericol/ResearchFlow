#!/usr/bin/env python3
# agents/rag_storage.py

import os
import json
import datetime
import uuid
import hashlib
import logging
from typing import List, Dict, Any, Optional, Tuple
import sys

try:
    from llama_index.core import (
        Document, 
        VectorStoreIndex, 
        StorageContext,
        load_index_from_storage,
        Settings
    )
    from llama_index.core.node_parser import SentenceSplitter
    from llama_index.embeddings.openai import OpenAIEmbedding
    from llama_index.core.vector_stores.simple import SimpleVectorStore
except ImportError:
    logger = logging.getLogger('rag_storage')
    logger.warning("LlamaIndex non è installato. Esegui 'pip install llama-index llama-index-embeddings-openai llama-index-vector-stores-simple'")

# Import configurations
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import OPENAI_API_KEY, OPENAI_EMBEDDING_MODEL, OPENAI_MODEL

# Inizializza OpenAI client
from openai import OpenAI
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# Configure logging
logger = logging.getLogger('rag_storage')

class RAGStorage:
    """
    Gestore per il salvataggio e il recupero di dati in formato RAG (Retrieval-Augmented Generation)
    utilizzando LlamaIndex.
    """
    
    def __init__(self, rag_dir="output/rag"):
        """
        Inizializza lo storage RAG.
        
        Args:
            rag_dir (str): Directory per il salvataggio degli indici RAG
        """
        self.rag_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
            rag_dir
        )
        os.makedirs(self.rag_dir, exist_ok=True)
        
        # Configura le impostazioni di LlamaIndex
        try:
            # Configura l'embedding model
            embed_model = OpenAIEmbedding(
                api_key=OPENAI_API_KEY,
                model=OPENAI_EMBEDDING_MODEL
            )
            
            # Configura le impostazioni globali di LlamaIndex
            Settings.embed_model = embed_model
            Settings.chunk_size = 512
            
            self.is_initialized = True
            logger.info(f"RAGStorage inizializzato con successo usando il modello di embedding {OPENAI_EMBEDDING_MODEL}")
        except Exception as e:
            logger.error(f"Errore nell'inizializzazione di RAGStorage: {e}")
            self.is_initialized = False
    
    def save_results_as_rag(self, task: str, results: List[Dict[str, Any]], metadata: Dict[str, Any] = None) -> Optional[str]:
        """
        Salva i risultati di ricerca in un indice RAG.
        
        Args:
            task (str): Il task di ricerca originale
            results (List[Dict[str, Any]]): I risultati di ricerca trovati
            metadata (Dict[str, Any]): Metadati aggiuntivi da salvare
            
        Returns:
            Optional[str]: ID dell'indice RAG creato, o None in caso di errore
        """
        if not self.is_initialized:
            logger.error("RAGStorage non inizializzato correttamente")
            return None
            
        if not results:
            logger.warning("Nessun risultato da salvare come RAG")
            return None
            
        try:
            # Genera ID univoco per questa collezione di risultati
            rag_id = str(uuid.uuid4())[:8]
            index_dir = os.path.join(self.rag_dir, f"index_{rag_id}")
            
            # Crea documenti da risultati di ricerca
            documents = []
            cache_references = []
            
            for result in results:
                if 'content' in result and result['content']:
                    # Usa URL come ID univoco per il documento
                    url = result.get('link', '')
                    title = result.get('title', 'Titolo non disponibile')
                    
                    # Ottieni hash URL per riferimento alla cache
                    url_hash = hashlib.md5(url.encode()).hexdigest()
                    cache_file = f"{url_hash}.json"
                    
                    # Crea documento per l'indicizzazione
                    doc = Document(
                        text=result['content'],
                        metadata={
                            "source": "web",
                            "url": url,
                            "title": title,
                            "relevance_score": result.get('relevance_score', 0.0),
                            "content_relevance_score": result.get('content_evaluation', {}).get('relevance_score', 0.0),
                            "cache_file": cache_file
                        }
                    )
                    documents.append(doc)
                    
                    # Memorizza riferimenti alla cache
                    cache_references.append({
                        "url": url,
                        "cache_file": cache_file,
                        "title": title
                    })
            
            if not documents:
                logger.warning("Nessun documento valido da indicizzare")
                return None
            
            # Crea indice con i documenti
            logger.info(f"Creazione indice RAG con {len(documents)} documenti")
            node_parser = SentenceSplitter(chunk_size=512, chunk_overlap=50)
            vector_store = SimpleVectorStore()
            storage_context = StorageContext.from_defaults(vector_store=vector_store)
            
            index = VectorStoreIndex.from_documents(
                documents,
                storage_context=storage_context
            )
            
            # Salva indice su disco
            index.storage_context.persist(persist_dir=index_dir)
            
            # Salva metadati dell'indice
            metadata_file = os.path.join(index_dir, "metadata.json")
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "id": rag_id,
                    "task": task,
                    "created_at": datetime.datetime.now().isoformat(),
                    "num_documents": len(documents),
                    "cache_references": cache_references,
                    "metadata": metadata or {}
                }, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Indice RAG salvato con ID: {rag_id}")
            return rag_id
            
        except Exception as e:
            logger.error(f"Errore durante il salvataggio dei risultati come RAG: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def load_rag_index(self, rag_id: str) -> Optional[Tuple[VectorStoreIndex, Dict[str, Any]]]:
        """
        Carica un indice RAG dal disco.
        
        Args:
            rag_id (str): ID dell'indice RAG da caricare
            
        Returns:
            Optional[Tuple[VectorStoreIndex, Dict[str, Any]]]: Tupla con indice e metadati, o None se non trovato
        """
        if not self.is_initialized:
            logger.error("RAGStorage non inizializzato correttamente")
            return None
            
        index_dir = os.path.join(self.rag_dir, f"index_{rag_id}")
        metadata_file = os.path.join(index_dir, "metadata.json")
        
        if not os.path.exists(index_dir) or not os.path.exists(metadata_file):
            logger.error(f"Indice RAG {rag_id} non trovato")
            return None
            
        try:
            # Carica metadati
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            # Carica indice
            storage_context = StorageContext.from_defaults(persist_dir=index_dir)
            index = load_index_from_storage(storage_context)
            
            return index, metadata
        except Exception as e:
            logger.error(f"Errore durante il caricamento dell'indice RAG {rag_id}: {e}")
            return None
    
    def query_rag_index(self, rag_id: str, query: str, similarity_top_k: int = 5, relevance_threshold: float = 0.6) -> Optional[Dict[str, Any]]:
        """
        Interroga un indice RAG con una query.
        
        Args:
            rag_id (str): ID dell'indice RAG da interrogare
            query (str): Query di ricerca
            similarity_top_k (int): Numero di risultati simili da restituire
            relevance_threshold (float): Soglia minima di rilevanza per includere un risultato
            
        Returns:
            Optional[Dict[str, Any]]: Risultati della query, o None in caso di errore
        """
        if not self.is_initialized:
            logger.error("RAGStorage non inizializzato correttamente")
            return None
            
        loaded = self.load_rag_index(rag_id)
        if not loaded:
            return None
            
        index, metadata = loaded
        
        try:
            # Crea query engine
            query_engine = index.as_query_engine(similarity_top_k=similarity_top_k)
            
            # Esegui query per ottenere i nodi sorgenti
            retriever_response = query_engine.retriever.retrieve(query)
            
            # Filtra i nodi sorgenti in base alla soglia di rilevanza
            filtered_nodes = [node for node in retriever_response if node.score >= relevance_threshold]
            
            # Se non ci sono nodi sopra la soglia, considera i top 3 comunque
            if not filtered_nodes and retriever_response:
                filtered_nodes = sorted(retriever_response, key=lambda x: x.score, reverse=True)[:3]
                logger.info(f"Nessun nodo sopra la soglia {relevance_threshold}, uso i top 3 disponibili")
            
            # Prepara le informazioni sulle fonti
            sources = []
            context_texts = []
            
            for node in filtered_nodes:
                source_info = {
                    "content": node.text,
                    "score": node.score,
                    "url": node.metadata.get("url", ""),
                    "title": node.metadata.get("title", ""),
                    "cache_file": node.metadata.get("cache_file", "")
                }
                sources.append(source_info)
                context_texts.append(node.text)
            
            # Genera una risposta utilizzando direttamente OpenAI con OPENAI_MODEL
            combined_context = "\n\n---\n\n".join(context_texts)
            
            prompt = f"""Basandoti sulle seguenti informazioni, rispondi alla domanda. 
Includi solo fatti presenti nei dati forniti e non aggiungere informazioni non presenti.
Se le informazioni fornite non sono sufficienti per rispondere, dillo chiaramente.

INFORMAZIONI:
{combined_context}

DOMANDA: {query}

RISPOSTA:"""
            print(prompt)

            logger.info(f"Generazione risposta con il modello {OPENAI_MODEL}")
            completion = openai_client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "Sei un assistente di ricerca che risponde alle domande basandosi solo sui dati forniti."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            
            generated_response = completion.choices[0].message.content
            
            return {
                "query": query,
                "response": generated_response,
                "sources": sources,
                "task": metadata.get("task", ""),
                "rag_id": rag_id
            }
            
        except Exception as e:
            logger.error(f"Errore durante l'interrogazione dell'indice RAG {rag_id}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def list_rag_indices(self) -> List[Dict[str, Any]]:
        """
        Elenca tutti gli indici RAG disponibili.
        
        Returns:
            List[Dict[str, Any]]: Lista di metadati degli indici RAG
        """
        indices = []
        
        if os.path.exists(self.rag_dir):
            for dirname in os.listdir(self.rag_dir):
                if dirname.startswith("index_"):
                    metadata_file = os.path.join(self.rag_dir, dirname, "metadata.json")
                    
                    if os.path.exists(metadata_file):
                        try:
                            with open(metadata_file, 'r', encoding='utf-8') as f:
                                metadata = json.load(f)
                                indices.append(metadata)
                        except Exception as e:
                            logger.error(f"Errore nella lettura dei metadati dell'indice {dirname}: {e}")
        
        return indices

    def update_rag_index(self, rag_id: str, task: str, new_results: List[Dict[str, Any]]) -> bool:
        """
        Aggiorna un indice RAG esistente con nuovi risultati.
        
        Args:
            rag_id (str): ID dell'indice RAG da aggiornare
            task (str): Il task di ricerca associato ai nuovi risultati
            new_results (List[Dict[str, Any]]): I nuovi risultati di ricerca da aggiungere
            
        Returns:
            bool: True se l'aggiornamento è riuscito, False altrimenti
        """
        if not self.is_initialized:
            logger.error("RAGStorage non inizializzato correttamente")
            return False
            
        if not new_results:
            logger.warning("Nessun risultato da aggiungere al RAG")
            return False
            
        # Verifica se l'indice esiste già
        loaded = self.load_rag_index(rag_id)
        if not loaded:
            logger.info(f"L'indice RAG {rag_id} non esiste, ne verrà creato uno nuovo")
            new_rag_id = self.save_results_as_rag(task, new_results)
            return new_rag_id == rag_id
            
        index, metadata = loaded
        index_dir = os.path.join(self.rag_dir, f"index_{rag_id}")
        
        try:
            # Crea documenti da nuovi risultati di ricerca
            documents = []
            existing_cache_references = metadata.get("cache_references", [])
            existing_urls = {ref.get("url", "") for ref in existing_cache_references}
            new_cache_references = []
            
            for result in new_results:
                if 'content' in result and result['content']:
                    # Usa URL come ID univoco per il documento
                    url = result.get('link', '')
                    
                    # Salta i risultati già presenti nell'indice (basati sull'URL)
                    if url in existing_urls:
                        logger.debug(f"URL già presente nell'indice: {url}")
                        continue
                        
                    title = result.get('title', 'Titolo non disponibile')
                    
                    # Ottieni hash URL per riferimento alla cache
                    url_hash = hashlib.md5(url.encode()).hexdigest()
                    cache_file = f"{url_hash}.json"
                    
                    # Crea documento per l'indicizzazione
                    doc = Document(
                        text=result['content'],
                        metadata={
                            "source": "web",
                            "url": url,
                            "title": title,
                            "relevance_score": result.get('relevance_score', 0.0),
                            "content_relevance_score": result.get('content_evaluation', {}).get('relevance_score', 0.0),
                            "cache_file": cache_file
                        }
                    )
                    documents.append(doc)
                    
                    # Memorizza riferimenti alla cache
                    new_cache_references.append({
                        "url": url,
                        "cache_file": cache_file,
                        "title": title
                    })
            
            if not documents:
                logger.warning("Nessun nuovo documento valido da aggiungere all'indice")
                return True  # Consideriamo questo un successo (nessuna modifica necessaria)
            
            # Aggiorna indice con i nuovi documenti
            logger.info(f"Aggiunta di {len(documents)} nuovi documenti all'indice RAG {rag_id}")
            node_parser = SentenceSplitter(chunk_size=512, chunk_overlap=50)
            
            # Aggiungiamo i nuovi documenti all'indice esistente
            for doc in documents:
                index.insert(doc)
                
            # Salva indice aggiornato su disco
            index.storage_context.persist(persist_dir=index_dir)
            
            # Aggiorna e salva metadati dell'indice
            metadata["cache_references"].extend(new_cache_references)
            metadata["num_documents"] = metadata.get("num_documents", 0) + len(documents)
            metadata["updated_at"] = datetime.datetime.now().isoformat()
            metadata["task"] = f"{metadata.get('task', '')} + {task}"
            
            metadata_file = os.path.join(index_dir, "metadata.json")
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Indice RAG {rag_id} aggiornato con successo")
            return True
            
        except Exception as e:
            logger.error(f"Errore durante l'aggiornamento dell'indice RAG {rag_id}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
            
    def get_or_create_unified_rag(self, rag_id: str) -> Optional[str]:
        """
        Ottiene o crea un indice RAG unificato con l'ID specificato.
        
        Args:
            rag_id (str): ID dell'indice RAG unificato
            
        Returns:
            Optional[str]: ID dell'indice RAG, o None in caso di errore
        """
        index_dir = os.path.join(self.rag_dir, f"index_{rag_id}")
        
        # Se l'indice esiste già, restituisci l'ID
        if os.path.exists(index_dir):
            return rag_id
            
        # Altrimenti, crea un nuovo indice vuoto
        try:
            # Crea una directory per l'indice
            os.makedirs(index_dir, exist_ok=True)
            
            # Crea un indice vuoto
            vector_store = SimpleVectorStore()
            storage_context = StorageContext.from_defaults(vector_store=vector_store)
            index = VectorStoreIndex([], storage_context=storage_context)
            
            # Salva indice su disco
            index.storage_context.persist(persist_dir=index_dir)
            
            # Salva metadati dell'indice
            metadata_file = os.path.join(index_dir, "metadata.json")
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "id": rag_id,
                    "task": "Indice RAG unificato",
                    "created_at": datetime.datetime.now().isoformat(),
                    "num_documents": 0,
                    "cache_references": [],
                    "metadata": {
                        "type": "unified"
                    }
                }, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Indice RAG unificato creato con ID: {rag_id}")
            return rag_id
            
        except Exception as e:
            logger.error(f"Errore durante la creazione dell'indice RAG unificato: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None