"""
scraper/researcher.py
Fetches context for a given topic using duckduckgo-search (news backend) and returns a synthetic story dictionary.
"""

from duckduckgo_search import DDGS
from scraper.enricher import _fetch_article_text
from utils.logger import get_logger

log = get_logger("researcher")

def research_topic(query: str) -> dict:
    """
    Search the web for the query and extract full text from the top results.
    Returns a dictionary formatted like a normal scraped story.
    """
    log.info(f"Researching topic: {query}")
    
    try:
        ddgs = DDGS()
        # limit to top 3 results for performance and context limits
        results = ddgs.news(query, max_results=3)
    except Exception as e:
        log.error(f"DuckDuckGo search failed: {e}")
        results = []

    combined_context = []
    top_url = ""

    results_list = list(results) if results else []

    if not results_list:
        combined_context.append("No recent context could be fetched from the web. Please rely on your own internal knowledge to discuss the topic and incorporate the user's angle.")
    else:
        for idx, res in enumerate(results_list):
            url = res.get("url")
            title = res.get("title")
            snippet = res.get("body")
            
            if idx == 0:
                top_url = url
                
            combined_context.append(f"Source {idx + 1}: {title}\nURL: {url}\nSnippet: {snippet}")
            
            # Fetch the full text for deeper context
            full_text = _fetch_article_text(url)
            if full_text:
                combined_context.append(f"Content: {full_text[:1500]}") # Cap each article length
            
            combined_context.append("-" * 40)
            
    summary_text = "\n".join(combined_context)
    
    # Cap total context size to stay within LLM limits (e.g. Mistral 8k or Groq limits)
    summary_text = summary_text[:6000]

    # Construct the synthetic story
    story = {
        "id": "research_" + str(hash(query))[:8].replace("-", "0"),
        "source": "manual_research",
        "title": f"Research: {query}",
        "url": top_url,
        "discussion_url": "",
        "summary": summary_text,
        "full_text": summary_text,
        "score": 0,
        "comments": 0,
        "timestamp": 0,
        "is_tool_launch": False,
        "region": "global",
        "age_hours": 0.0,
        "india_relevant": False,
        "is_ai_related": True,
        "is_opportunity": False,
        "final_score": 0.0,
        "format_suggestion": "text"
    }
    
    return story
