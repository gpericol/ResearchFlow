# agent/google_search.py

from googlesearch import search
from typing import List, Dict, Any
from config import SEARCH_RESULTS_LIMIT

def google_search(query: str, num_results: int = SEARCH_RESULTS_LIMIT) -> List[Dict[str, Any]]:
    """
    Performs a Google search for the given query and returns a list of results
    containing titles, links, and descriptions.
    
    Args:
        query (str): The search query to be used
        num_results (int): Maximum number of search results to return
        
    Returns:
        List[Dict[str, Any]]: A list of dictionaries with 'title', 'link', and 'description' keys
    """
    results = []
    
    try:
        # The search function returns links only
        search_results = search(query, num_results=num_results, unique=True)
        
        # For each link, add it to our results with a placeholder for title and description
        # In a real implementation, you would need to fetch each page to get title and description
        for link in search_results:
            results.append({
                'title': f"Result for {query}",  # Basic placeholder
                'link': link,
                'description': "Description not available without additional scraping"
            })
            
        return results
    except Exception as e:
        print(f"Error during Google search: {e}")
        return []

def format_search_results(results: List[Dict[str, Any]]) -> str:
    """
    Formats the search results into a readable string.
    
    Args:
        results (List[Dict[str, Any]]): The search results to format
        
    Returns:
        str: A formatted string representation of the search results
    """
    if not results:
        return "No search results found."
    
    formatted_text = "Search Results:\n\n"
    
    for i, result in enumerate(results, 1):
        formatted_text += f"{i}. {result['title']}\n"
        formatted_text += f"   Link: {result['link']}\n"
        formatted_text += f"   {result['description']}\n\n"
        
    return formatted_text