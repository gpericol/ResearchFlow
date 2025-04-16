# ResearchFlow

Un sistema avanzato di ricerca e organizzazione delle informazioni basato su intelligenza artificiale.

## Descrizione

ResearchFlow è un'applicazione web che automatizza la ricerca di informazioni sul web, utilizzando tecniche avanzate di elaborazione del linguaggio naturale per trovare, pulire, valutare e organizzare informazioni rilevanti.

## Caratteristiche principali

- **Ricerca automatica**: genera e ottimizza automaticamente query di ricerca Google basate sul task specifico
- **Pulizia dei contenuti**: rimuove elementi non informativi dalle pagine web usando AI
- **Valutazione di rilevanza**: analizza automaticamente la rilevanza dei contenuti rispetto alla ricerca
- **Storage RAG** (Retrieval-Augmented Generation): salva i risultati in un formato ottimizzato per interrogazioni future
- **Interfaccia web**: gestisci le tue ricerche tramite un'interfaccia web intuitiva
- **Generazione di task**: suddivide automaticamente le ricerche complesse in sottotask gestibili
- **Cache intelligente**: evita di scaricare ripetutamente gli stessi contenuti

## Componenti principali

Il sistema è composto da diversi moduli agenti che collaborano:

- `search_orchestrator.py`: coordina l'intero processo di ricerca
- `web_scraper.py`: scarica contenuti da pagine web
- `content_cleaner.py`: purifica i contenuti HTML rimuovendo parti non informative
- `content_relevance.py`: valuta la rilevanza dei contenuti rispetto alla ricerca
- `rag_storage.py`: archivia i contenuti in formato ottimizzato per future interrogazioni
- `taskgenerator.py`: suddivide ricerche complesse in sottotask
- `google_search.py`: interfaccia per la ricerca web

## Installazione

1. Clona il repository
2. Installa le dipendenze: `pip install -r requirements.txt`
3. Configura le variabili d'ambiente (vedi sezione Configurazione)
4. Avvia il server: `python app.py`

## Configurazione

Crea un file `.env` nella directory principale con i seguenti parametri:

```
OPENAI_API_KEY=your_openai_api_key
SECRET_KEY=your_flask_secret_key
SERPAPI_KEY=your_serpapi_key
```

## Utilizzo

1. Apri il browser all'indirizzo `http://localhost:5000`
2. Crea una nuova ricerca
3. Inserisci il prompt di ricerca
4. Rispondi alle domande di approfondimento per migliorare la precisione
5. Avvia la ricerca automatica
6. Interroga i risultati ottenuti

## Uso da linea di comando

È possibile utilizzare il sistema anche da linea di comando:

```
python agents/search_orchestrator.py --task "Descrizione del task di ricerca" --output results.txt
```

## Licenza

```
            DO WHAT THE FUCK YOU WANT TO PUBLIC LICENSE
                    Version 2, December 2004

 Everyone is permitted to copy and distribute verbatim or modified
 copies of this license document, and changing it is allowed as long
 as the name is changed.

            DO WHAT THE FUCK YOU WANT TO PUBLIC LICENSE
   TERMS AND CONDITIONS FOR COPYING, DISTRIBUTION AND MODIFICATION

  0. You just DO WHAT THE FUCK YOU WANT TO.
```

Questo progetto è rilasciato sotto la licenza [WTFPL](http://www.wtfpl.net/).