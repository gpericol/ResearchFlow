from dotenv import load_dotenv
import os

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"  # Modello di embedding da utilizzare
OPENAI_MODEL = "gpt-4o-mini"
SEARCH_RESULTS_LIMIT = 20

# Search orchestrator configuration
MAX_RELEVANT_RESULTS = 3  # Maximum number of relevant results to find
MAX_SEARCH_CYCLES = 3     # Maximum number of search cycles to attempt
LINK_RELEVANCE_THRESHOLD = 0.7  # Minimum score to consider a search result relevant
CONTENT_RELEVANCE_THRESHOLD = 0.7  # Minimum score to consider page content relevant
CACHE_DIR = "cache"  # Directory for cached web pages