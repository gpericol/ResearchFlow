#!/usr/bin/env python3
# agents/research_logger.py

import os
import logging
from typing import Optional
import sys
from datetime import datetime

# Base directory for log files
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'output')

# Mantieni traccia degli handler aggiunti a ciascun logger
_logger_handlers = {}

class ResearchLogger:
    """
    Logger specializzato che salva i log in file separati per ogni ricerca.
    Reindirizza anche l'output dei print agli stessi file di log.
    """
    _instances = {}  # Cache delle istanze per research_id

    @classmethod
    def get_logger(cls, research_id: str) -> 'ResearchLogger':
        """
        Factory method per ottenere un'istanza del logger per un dato research_id.
        Usa un'istanza esistente se disponibile, altrimenti ne crea una nuova.
        
        Args:
            research_id (str): ID della ricerca
            
        Returns:
            ResearchLogger: Istanza del logger per la ricerca specificata
        """
        if research_id not in cls._instances:
            cls._instances[research_id] = cls(research_id)
        return cls._instances[research_id]
    
    def __init__(self, research_id: str):
        """
        Inizializza un logger per una specifica ricerca.
        
        Args:
            research_id (str): ID della ricerca per cui creare il logger
        """
        self.research_id = research_id
        self.log_file_path = os.path.join(LOG_DIR, f"{research_id}.log")
        os.makedirs(LOG_DIR, exist_ok=True)
        
        # Configura il logger Python standard
        self.logger = logging.getLogger(f"research.{research_id}")
        self.logger.setLevel(logging.INFO)
        
        # Rimuovi handler esistenti per evitare duplicati
        if self.logger.handlers:
            self.logger.handlers = []
        
        # Crea un file handler
        file_handler = logging.FileHandler(self.log_file_path)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        
        # Aggiungi l'handler al logger
        self.logger.addHandler(file_handler)
        
    def info(self, message: str):
        """Logga un messaggio informativo"""
        self.logger.info(message)
        
    def warning(self, message: str):
        """Logga un avviso"""
        self.logger.warning(message)
        
    def error(self, message: str):
        """Logga un errore"""
        self.logger.error(message)
        
    def debug(self, message: str):
        """Logga un messaggio di debug"""
        self.logger.debug(message)
        
    def critical(self, message: str):
        """Logga un errore critico"""
        self.logger.critical(message)

# Funzione per ottenere il logger per una specifica ricerca
def get_research_logger(research_id: str) -> ResearchLogger:
    """
    Ottiene un'istanza del logger per la ricerca specificata.
    
    Args:
        research_id (str): ID della ricerca
        
    Returns:
        ResearchLogger: Logger configurato per la ricerca
    """
    return ResearchLogger.get_logger(research_id)

# Classe di supporto per catturare l'output dei print
class PrintToLogRedirector:
    """
    Classe che cattura i print e li reindirizza al logger della ricerca.
    Può essere usata come context manager.
    """
    def __init__(self, research_id: str):
        self.research_id = research_id
        self.logger = get_research_logger(research_id)
        self.original_stdout = sys.stdout
        
    def __enter__(self):
        """Avvia la redirezione"""
        sys.stdout = self
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Ripristina lo stdout originale"""
        sys.stdout = self.original_stdout
        
    def write(self, message):
        """Intercetta le chiamate write() e le reindirizza al logger"""
        # Gestisci le nuove linee e altri caratteri speciali
        if message and not message.isspace():
            message = message.rstrip()
            if message:  # Se non è una stringa vuota dopo il rstrip
                self.logger.info(message)
        # Passa comunque il messaggio allo stdout originale
        self.original_stdout.write(message)
        
    def flush(self):
        """Implementa flush per compatibilità"""
        self.original_stdout.flush()

# Handler di log specializzato che duplica i messaggi di log al logger della ricerca
class ResearchLogHandler(logging.Handler):
    """
    Handler di logging che duplica tutti i messaggi di log al logger della ricerca.
    """
    def __init__(self, research_id: str, level=logging.NOTSET):
        super().__init__(level)
        self.research_id = research_id
        self.research_logger = get_research_logger(research_id)
        
    def emit(self, record):
        # Ottieni il messaggio formattato
        msg = self.format(record)
        
        # Invia il messaggio al logger della ricerca con il livello appropriato
        if record.levelno >= logging.ERROR:
            self.research_logger.error(msg)
        elif record.levelno >= logging.WARNING:
            self.research_logger.warning(msg)
        elif record.levelno >= logging.INFO:
            self.research_logger.info(msg)
        elif record.levelno >= logging.DEBUG:
            self.research_logger.debug(msg)

# Funzione per reindirizzare i log di un modulo al logger della ricerca
def redirect_module_logs_to_research(module_name: str, research_id: str):
    """
    Reindirizza tutti i log di un modulo specifico al logger della ricerca.
    
    Args:
        module_name (str): Nome del modulo/logger da reindirizzare
        research_id (str): ID della ricerca a cui reindirizzare i log
    """
    logger = logging.getLogger(module_name)
    
    # Crea una chiave univoca per questo logger e research_id
    handler_key = f"{module_name}_{research_id}"
    
    # Verifica se abbiamo già aggiunto un handler per questa combinazione
    if handler_key not in _logger_handlers:
        # Crea un handler per reindirizzare i log al logger della ricerca
        handler = ResearchLogHandler(research_id)
        formatter = logging.Formatter('%(message)s')  # Formato semplificato per evitare duplicazioni
        handler.setFormatter(formatter)
        
        # Aggiungi l'handler al logger
        logger.addHandler(handler)
        
        # Memorizza l'handler per poterlo rimuovere in seguito
        _logger_handlers[handler_key] = handler
        
    return logger

# Funzione per rimuovere la redirezione dei log
def remove_module_logs_redirection(module_name: str, research_id: str):
    """
    Rimuove la redirezione dei log di un modulo specifico.
    
    Args:
        module_name (str): Nome del modulo/logger da modificare
        research_id (str): ID della ricerca associata alla redirezione
    """
    handler_key = f"{module_name}_{research_id}"
    
    if handler_key in _logger_handlers:
        logger = logging.getLogger(module_name)
        handler = _logger_handlers[handler_key]
        
        # Rimuovi l'handler
        logger.removeHandler(handler)
        
        # Rimuovi dall'elenco degli handler
        del _logger_handlers[handler_key]

# Funzione per reindirizzare i log di tutti i moduli principali al logger della ricerca
def redirect_all_agent_logs_to_research(research_id: str):
    """
    Reindirizza i log di tutti i moduli principali degli agenti al logger della ricerca.
    
    Args:
        research_id (str): ID della ricerca a cui reindirizzare i log
    """
    # Lista dei moduli principali di cui reindirizzare i log
    modules = [
        'content_cleaner', 
        'web_scraper', 
        'google_search',
        'relevance_filter', 
        'content_relevance', 
        'search_orchestrator',
        'query_builder',
        'content_cache',
        'rag_storage',
        'formatter',
        'cli_utils',
        'taskgenerator'
    ]
    
    for module in modules:
        redirect_module_logs_to_research(module, research_id)

# Funzione di utility per reindirizzare i print al logger
def redirect_prints_to_research_log(research_id: str):
    """
    Reindirizza tutte le chiamate print() al logger della ricerca specificata.
    
    Args:
        research_id (str): ID della ricerca
    
    Returns:
        PrintToLogRedirector: L'oggetto redirector che può essere usato come context manager
    """
    return PrintToLogRedirector(research_id)

# Context manager per reindirizzare sia i print che i log di tutti gli agenti
class AgentOutputRedirector:
    """
    Context manager che reindirizza sia i print che i log di tutti gli agenti.
    """
    def __init__(self, research_id: str):
        self.research_id = research_id
        self.print_redirector = PrintToLogRedirector(research_id)
        
    def __enter__(self):
        # Reindirizza i print
        self.print_redirector.__enter__()
        
        # Reindirizza i log di tutti gli agenti
        redirect_all_agent_logs_to_research(self.research_id)
        
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Ripristina lo stdout originale
        self.print_redirector.__exit__(exc_type, exc_val, exc_tb)
        
        # Non c'è bisogno di rimuovere gli handler dei log alla chiusura
        # perché possono continuare a reindirizzare i messaggi

# Funzione per sostituire completamente un logger di modulo con il logger della ricerca
def replace_module_logger(module_name: str, research_id: str):
    """
    Sostituisce completamente il logger di un modulo con il logger della ricerca.
    A differenza di redirect_module_logs_to_research, questo metodo cambia il logger stesso,
    non solo aggiunge un handler.
    
    Args:
        module_name (str): Nome del modulo/logger da sostituire
        research_id (str): ID della ricerca da usare
        
    Returns:
        ResearchLogger: L'istanza del logger della ricerca
    """
    research_logger = get_research_logger(research_id)
    
    # Ottieni il logger originale del modulo
    original_logger = logging.getLogger(module_name)
    
    # Salva il livello di logging originale
    original_level = original_logger.level
    
    # Rimuovi tutti gli handler esistenti
    if original_logger.handlers:
        for handler in original_logger.handlers[:]:
            original_logger.removeHandler(handler)
    
    # Hack: sostituisci i metodi di logging del logger originale con quelli del research logger
    # Questo fa sì che qualsiasi chiamata al logger originale venga reindirizzata al logger della ricerca
    original_logger.info = lambda msg, *args, **kwargs: research_logger.info(msg)
    original_logger.warning = lambda msg, *args, **kwargs: research_logger.warning(msg)
    original_logger.error = lambda msg, *args, **kwargs: research_logger.error(msg)
    original_logger.debug = lambda msg, *args, **kwargs: research_logger.debug(msg)
    original_logger.critical = lambda msg, *args, **kwargs: research_logger.critical(msg)
    
    # Imposta il livello di logging uguale a quello originale
    original_logger.setLevel(original_level)
    
    return research_logger

# Funzione che sostituisce tutti i logger degli agenti con il logger della ricerca
def replace_all_agent_loggers(research_id: str):
    """
    Sostituisce tutti i logger degli agenti con il logger della ricerca.
    
    Args:
        research_id (str): ID della ricerca a cui reindirizzare i log
    """
    # Lista dei moduli principali di cui sostituire i logger
    modules = [
        'content_cleaner', 
        'web_scraper', 
        'google_search',
        'relevance_filter', 
        'content_relevance', 
        'search_orchestrator',
        'query_builder',
        'content_cache',
        'rag_storage',
        'formatter',
        'cli_utils',
        'taskgenerator'
    ]
    
    for module in modules:
        replace_module_logger(module, research_id)

# Versione migliorata del context manager per la redirezione completa
class CompleteAgentOutputRedirector:
    """
    Context manager che reindirizza completamente sia i print che i log di tutti gli agenti.
    Questa versione sostituisce i logger originali invece di aggiungere solo handler.
    """
    def __init__(self, research_id: str):
        self.research_id = research_id
        self.print_redirector = PrintToLogRedirector(research_id)
        
    def __enter__(self):
        # Reindirizza i print
        self.print_redirector.__enter__()
        
        # Sostituisci completamente tutti i logger degli agenti
        replace_all_agent_loggers(self.research_id)
        
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Ripristina lo stdout originale
        self.print_redirector.__exit__(exc_type, exc_val, exc_tb)
        
        # Non è possibile ripristinare facilmente i logger originali, 
        # ma in un contesto di ricerca, di solito questo non è un problema
        # poiché i processi sono relativamente isolati