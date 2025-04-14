from flask import Flask
from dotenv import load_dotenv
import os

# Importa i blueprint
from webapp.api.main_routes import main_bp
from webapp.api.task_routes import task_bp
from webapp.api.research_routes import research_bp

def create_app():
    """
    Factory function per creare l'applicazione Flask
    """
    # Inizializza l'applicazione Flask
    app = Flask(__name__)
    
    # Carica le variabili d'ambiente
    load_dotenv()
    app.secret_key = os.getenv("SECRET_KEY")
    
    # Registra i blueprint con i prefissi URL corrispondenti
    app.register_blueprint(main_bp)
    app.register_blueprint(task_bp, url_prefix='/task')
    app.register_blueprint(research_bp, url_prefix='/research')
    
    return app

# Crea l'applicazione
app = create_app()

if __name__ == "__main__":
    app.run(debug=True)