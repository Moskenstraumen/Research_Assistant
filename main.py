import logging
import re
from utils.config import load_config
from ragflow_client.agent import RAGFlowAgent
from ragflow_client.uploader import RAGFlowUploader
from elsevier_client.client import ElsevierClient

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    """Main function to orchestrate the research assistant workflow."""
    logging.info("--- Automated Research Assistant Workflow ---")
    
    config = load_config()
    if not config:
        exit()

    user_query = "Whats the latest advancement in nuclear fusion"
    
    sanitized_query = re.sub(r'\W+', '_', user_query)
    kb_name = f"{sanitized_query[:50]}_KB"

    # Initialize components
    keyword_agent = RAGFlowAgent(config)
    elsevier_client = ElsevierClient(config)
    uploader = RAGFlowUploader(config)

    # Extract keywords
    keywords = keyword_agent.get_keywords(user_query)
    if not keywords:
        logging.error("Workflow halted: Could not extract keywords.")
        exit()

    # Search and download papers
    search_results = elsevier_client.search_papers(keywords)
    if not search_results:
        logging.warning("Workflow finished: No papers found on ScienceDirect.")
        exit()

    downloaded_file_paths = elsevier_client.download_papers(search_results)
    if not downloaded_file_paths:
        logging.warning("Workflow finished: No papers could be downloaded.")
        exit()

    # Upload to RAGFlow
    uploader.upload_papers(downloaded_file_paths, kb_name)

    logging.info("--- Workflow Finished ---")
    logging.info(f"Check the RAGFlow UI for the new knowledge base '{kb_name}'.")

if __name__ == "__main__":
    main()