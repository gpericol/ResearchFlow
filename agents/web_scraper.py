#!/usr/bin/env python3
# agents/web_scraper.py

import time
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException, TimeoutException
from webdriver_manager.chrome import ChromeDriverManager

# Configurazione del logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('web_scraper')

class WebScraper:
    """
    Agente per scaricare il contenuto di una pagina web utilizzando Selenium.
    Supporta la modalità headless con fallback alla modalità visibile.
    """
    
    def __init__(self, headless=True, timeout=30):
        """
        Inizializza lo scraper web.
        
        Args:
            headless (bool): Se True, avvia Chrome in modalità headless
            timeout (int): Timeout in secondi per il caricamento della pagina
        """
        self.headless = headless
        self.timeout = timeout
        self.driver = None
        
    def _setup_driver(self, headless=True):
        """
        Configura e avvia il WebDriver.
        
        Args:
            headless (bool): Se True, avvia Chrome in modalità headless
            
        Returns:
            WebDriver: Istanza del driver configurato
        """
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--disable-gpu")
        
        # Opzioni comuni per entrambe le modalità
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-notifications")
        chrome_options.add_argument("--disable-popup-blocking")
        
        # User agent per simulare un browser normale
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        try:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            driver.set_page_load_timeout(self.timeout)
            return driver
        except Exception as e:
            logger.error(f"Errore durante la configurazione del driver: {e}")
            raise
    
    def get_page_content(self, url):
        """
        Scarica il contenuto di una pagina web.
        Prova prima in modalità headless, poi fallback alla modalità visibile se necessario.
        
        Args:
            url (str): URL della pagina da scaricare
            
        Returns:
            str: Contenuto testuale della pagina web
        """
        page_content = ""
        
        try:
            # Prima prova con headless se abilitato
            if self.headless:
                logger.info(f"Tentativo di accesso a {url} in modalità headless")
                try:
                    self.driver = self._setup_driver(headless=True)
                    page_content = self._fetch_content(url)
                    logger.info("Accesso in modalità headless riuscito")
                    return page_content
                except (WebDriverException, TimeoutException) as e:
                    logger.warning(f"Errore in modalità headless: {e}. Passaggio alla modalità visibile")
                    if self.driver:
                        self.driver.quit()
                        self.driver = None
            
            # Fallback o modalità visibile diretta
            logger.info(f"Tentativo di accesso a {url} in modalità visibile")
            self.driver = self._setup_driver(headless=False)
            page_content = self._fetch_content(url)
            logger.info("Accesso in modalità visibile riuscito")
            
        except Exception as e:
            logger.error(f"Errore durante lo scaricamento della pagina {url}: {e}")
        finally:
            if self.driver:
                self.driver.quit()
                self.driver = None
        
        return page_content
    
    def _fetch_content(self, url):
        """
        Esegue l'effettivo scaricamento del contenuto della pagina.
        
        Args:
            url (str): URL della pagina da scaricare
            
        Returns:
            str: Contenuto testuale della pagina web
        """
        try:
            self.driver.get(url)
            
            # Aspetta un po' per permettere il caricamento dei contenuti dinamici
            time.sleep(2)
            
            # Scorre verso il basso per caricare contenuti lazy-loaded
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 2);")
            time.sleep(1)
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
            
            # Ottiene il testo dell'intera pagina
            body_text = self.driver.find_element("tag name", "body").text
            
            # Ottiene anche l'HTML per casi in cui il testo puro non è sufficiente
            html_content = self.driver.page_source
            
            # Se il testo del body è troppo corto, potrebbe essere un sito che nasconde il contenuto
            if len(body_text.strip()) < 100 and len(html_content) > 1000:
                logger.warning("Testo del body troppo corto, utilizzo l'html completo")
                return html_content
            
            return body_text
            
        except Exception as e:
            logger.error(f"Errore durante l'estrazione del contenuto della pagina: {e}")
            raise

# Funzione di utilità per uso esterno
def scrape_webpage(url, headless=True, timeout=30):
    """
    Funzione di utilità per scaricare il contenuto di una pagina web.
    
    Args:
        url (str): URL della pagina da scaricare
        headless (bool, optional): Se True, avvia Chrome in modalità headless
        timeout (int, optional): Timeout in secondi per il caricamento della pagina
        
    Returns:
        str: Contenuto testuale della pagina web
    """
    scraper = WebScraper(headless=headless, timeout=timeout)
    return scraper.get_page_content(url)

# Test dello scraper
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        url = sys.argv[1]
        print(f"Scaricamento del contenuto di: {url}")
        content = scrape_webpage(url)
        print(f"Contenuto scaricato ({len(content)} caratteri)")
        print("Prime 500 caratteri:")
        print(content[:500])
    else:
        print("Utilizzo: python web_scraper.py <url>")