import json
import os
import re
import time
import requests
import logging
from ragflow_sdk import RAGFlow
from elsapy.elsclient import ElsClient
from elsapy.elsdoc import FullDoc
from elsapy.elssearch import ElsSearch

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Configuration Loading ---
def load_config(config_path='config.json'):
    """Loads configuration from a JSON file."""
    logging.info(f"Loading configuration from {config_path}...")
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        # Create download directory if it doesn't exist
        os.makedirs(config.get('download_directory', './downloads'), exist_ok=True)
        logging.info("Configuration loaded successfully.")
        return config
    except FileNotFoundError:
        logging.error(f"FATAL: Configuration file not found at {config_path}. Please create it.")
        exit()
    except json.JSONDecodeError:
        logging.error(f"FATAL: Invalid JSON in {config_path}. Please check the file format.")
        exit()

# --- API Client Initialization ---
def initialize_clients(config):
    """Initializes RAGFlow and Elsevier API clients."""
    logging.info("Initializing API clients...")
    try:
        # RAGFlow SDK Client
        rag_client = RAGFlow(api_key=config['ragflow_api_key'], base_url=config['ragflow_base_url'])
        
        # Elsevier (elsapy) Client
        els_client = ElsClient(config['elsevier_api_key'])
        if config.get('elsevier_inst_token'):
            els_client.inst_token = config['elsevier_inst_token']
        
        logging.info("API clients initialized.")
        return rag_client, els_client
    except Exception as e:
        logging.error(f"Failed to initialize API clients: {e}")
        return None, None
    
def extract_keywords_from_agent(query: str, config: dict) -> list[str]:
    """
    Calls the RAGFlow Keyword Extraction Agent to get keywords for a user query.
    """
    logging.info(f"Extracting keywords for query: '{query}'")
    agent_id = config['keyword_agent_id']
    api_key = config['ragflow_api_key']
    url = f"{config['ragflow_base_url']}/api/v1/agents_openai/{agent_id}/chat/completions"

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }
    
    # The payload must follow the OpenAI-compatible format
    payload = {
        "model": "ep-20250325143204-spgcp",  # This MUST be your VolcEngine model endpoint ID
        "messages": [
            {"role": "user", "content": query}
        ],
        "stream": False
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()  # Raises an HTTPError for bad responses (4xx or 5xx)

        response_data = response.json()
        
        # CORRECTED: Handle the case where RAGFlow returns a list directly
        content = ''
        if response_data and isinstance(response_data, list):
            # The response is a list of choices, get the message from the first choice
            content = response_data.get('message', {}).get('content', '')
        elif isinstance(response_data, dict) and 'choices' in response_data and response_data['choices']:
            # Handle standard OpenAI dictionary format as a fallback
            content = response_data['choices'].get('message', {}).get('content', '')
        
        if not content:
            logging.warning("Keyword agent returned an empty or malformed response.")
            return

        # Clean the response: remove punctuation, split by comma or newline, and strip whitespace
        keywords = re.split(r'[,\n]', content)
        cleaned_keywords = [kw.strip() for kw in keywords if kw.strip()]
        
        logging.info(f"Extracted keywords: {cleaned_keywords}")
        return cleaned_keywords

    except requests.exceptions.HTTPError as http_err:
        logging.error(f"HTTP error occurred while calling keyword agent: {http_err}")
        logging.error(f"Response body: {response.text}")
    except requests.exceptions.RequestException as req_err:
        logging.error(f"Request error occurred: {req_err}")
    except json.JSONDecodeError:
        logging.error("Failed to decode JSON response from keyword agent. The endpoint may be incorrect or the agent is misconfigured.")
        logging.error(f"Raw response: {response.text}")
    
    return

def search_sciencedirect_for_papers(keywords: list[str], els_client: ElsClient, config: dict) -> list:
    """
    Searches the ScienceDirect database using the extracted keywords.
    """
    if not keywords:
        logging.warning("No keywords provided for ScienceDirect search. Aborting.")
        return

    # Construct a simple query string. ScienceDirect search syntax can be complex.
    query_string = ' AND '.join(keywords)
    logging.info(f"Constructed ScienceDirect query: {query_string}")

    try:
        # Initialize doc search object using ScienceDirect
        doc_srch = ElsSearch(query_string, 'sciencedirect')
        
        # Execute search, retrieving only the first page of results (default 25)
        doc_srch.execute(els_client, get_all=False)
        
        results = doc_srch.results
        
        if not results:
            logging.warning("ScienceDirect search returned no results.")
            return

        logging.info(f"ScienceDirect search found {len(results)} results.")
        # Limit the number of results to process
        return results[:config['max_papers_to_download']]
        
    except Exception as e:
        logging.error(f"An error occurred during ScienceDirect search: {e}")
        return
    
def download_articles(search_results: list, els_client: ElsClient, config: dict) -> list[str]:
    """
    Attempts to download the full text data of articles from ScienceDirect search results.
    Returns a list of paths to successfully downloaded JSON files.
    """
    downloaded_files = ''
    download_dir = config['download_directory']
    
    if not search_results:
        return

    logging.info(f"Attempting to download up to {len(search_results)} articles...")
    for paper_meta in search_results:
        try:
            doi = paper_meta.get('prism:doi')
            if not doi:
                logging.warning(f"No DOI found for paper titled '{paper_meta.get('dc:title', 'N/A')}'. Skipping.")
                continue

            # Sanitize DOI for use as a filename
            sanitized_doi = re.sub(r'[\\/*?:"<>|]', '_', doi)
            filename = os.path.join(download_dir, f"{sanitized_doi}.json")

            if os.path.exists(filename):
                logging.info(f"Article with DOI '{doi}' already downloaded. Skipping.")
                downloaded_files.append(filename)
                continue

            # Initialize a full-text document object with the DOI
            full_doc = FullDoc(doi=doi)
            
            # Retrieve the document data from the API
            if full_doc.read(els_client):
                logging.info(f"Successfully retrieved data for '{full_doc.title}'.")
                # Save the document's JSON data to a file
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(full_doc.data, f, indent=4)
                downloaded_files.append(filename)
            else:
                logging.warning(f"Failed to read/retrieve full document for DOI '{doi}'. This may be due to access restrictions.")

            # Add a small delay to be respectful to the API
            time.sleep(1)

        except Exception as e:
            logging.error(f"Failed to process or download paper with DOI '{doi}': {e}")
            continue
            
    return downloaded_files

def upload_papers_to_ragflow(rag_client: RAGFlow, file_paths: list[str], kb_name: str):
    """
    Uploads downloaded papers to a specified RAGFlow knowledge base.
    """
    if not file_paths:
        logging.info("No files to upload to RAGFlow.")
        return

    logging.info(f"Preparing to upload {len(file_paths)} files to knowledge base '{kb_name}'...")
    
    try:
        # Check if knowledge base (dataset) exists, create if not
        datasets = rag_client.list_datasets(name=kb_name)
        if datasets:
            dataset = datasets
            logging.info(f"Found existing knowledge base '{kb_name}' (ID: {dataset.id}).")
        else:
            logging.info(f"Knowledge base '{kb_name}' not found. Creating it...")
            dataset = rag_client.create_dataset(
                name=kb_name,
                chunk_method='paper' # Use 'paper' chunking for research articles
            )
            logging.info(f"Created new knowledge base '{kb_name}' (ID: {dataset.id}).")

        # Prepare documents for upload
        docs_to_upload = ''
        for file_path in file_paths:
            try:
                with open(file_path, 'rb') as f:
                    blob = f.read()
                docs_to_upload.append({
                    "name": os.path.basename(file_path),
                    "blob": blob
                })
            except Exception as e:
                logging.error(f"Failed to read file {file_path} for upload: {e}")

        if not docs_to_upload:
            logging.error("No valid documents could be prepared for upload.")
            return

        # Upload documents in a single batch
        logging.info(f"Uploading {len(docs_to_upload)} documents...")
        dataset.upload_documents(docs_to_upload)
        logging.info("Documents uploaded successfully.")

        # Trigger parsing for the newly uploaded documents
        time.sleep(2) # Give RAGFlow a moment to register the new files
        all_docs = dataset.list_documents()
        doc_ids_to_parse = [doc.id for doc in all_docs if doc.status == "not_parsed"]

        if doc_ids_to_parse:
            logging.info(f"Triggering parsing for {len(doc_ids_to_parse)} new documents...")
            dataset.async_parse_documents(doc_ids_to_parse)
            logging.info("Document parsing initiated. Check the RAGFlow UI for progress.")
        else:
            logging.warning("Could not find any new documents to parse.")

    except Exception as e:
        logging.error(f"An error occurred during RAGFlow upload/parsing: {e}")

if __name__ == "__main__":
    logging.info("--- Automated Research Assistant Workflow ---")
    
    # 1. Load configuration and initialize clients
    config = load_config()
    if not config:
        exit()
        
    rag_client, els_client = initialize_clients(config)
    if not rag_client or not els_client:
        exit()

    # 2. Define user query
    user_query = "What are the latest advancements in using reinforcement learning for robotic manipulation tasks?"
    kb_name = "RL_Robotic_Manipulation_KB" # Knowledge base name derived from the query

    # 3. Extract keywords using RAGFlow Agent
    keywords = extract_keywords_from_agent(user_query, config)
    if not keywords:
        logging.error("Workflow halted: Could not extract keywords.")
        exit()

    # 4. Search ScienceDirect for papers
    search_results = search_sciencedirect_for_papers(keywords, els_client, config)
    if not search_results:
        logging.warning("Workflow finished: No papers found on ScienceDirect.")
        exit()

    # 5. Download papers (best-effort)
    downloaded_file_paths = download_articles(search_results, els_client, config)
    if not downloaded_file_paths:
        logging.warning("Workflow finished: No papers could be downloaded.")
        exit()

    # 6. Upload and parse papers in RAGFlow
    upload_papers_to_ragflow(rag_client, downloaded_file_paths, kb_name)

    logging.info("--- Workflow Finished ---")
    logging.info(f"Check the RAGFlow UI for the new knowledge base '{kb_name}'.")