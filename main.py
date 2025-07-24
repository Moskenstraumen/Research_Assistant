import json
import logging
import os
import re
import requests
import time
from ragflow_sdk import RAGFlow
from elsapy.elsclient import ElsClient
from elsapy.elsdoc import FullDoc
from elsapy.elssearch import ElsSearch

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_config(config_path='config.json'):
    """Loads configuration from a JSON file."""
    logging.info(f"Loading configuration from {config_path}...")
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        os.makedirs(config.get('download_directory', './downloads'), exist_ok=True)
        logging.info("Configuration loaded successfully.")
        return config
    except FileNotFoundError:
        logging.error(f"FATAL: Configuration file not found at {config_path}. Please create it.")
        exit()
    except json.JSONDecodeError:
        logging.error(f"FATAL: Invalid JSON in {config_path}. Please check the file format.")
        exit()

class RAGFlowAgent:
    """
    Handles communication with a RAGFlow Agent, following the official
    session-based API documentation.
    """
    def __init__(self, config: dict):
        self.base_url = config['ragflow_base_url']
        self.api_key = config['ragflow_api_key']
        self.agent_id = config['keyword_agent_id']
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }

    def _get_session_id(self) -> str:
        """Creates a new conversation session and returns the session_id."""
        url = f"{self.base_url}/api/v1/agents/{self.agent_id}/sessions?user_id=moskenstraumen"
        try:
            logging.info("Creating new RAGFlow conversation session...")
            response = requests.post(url, headers=self.headers, data={})
            response.raise_for_status()
            response_data = response.json()
            session_id = response_data.get('data', {}).get('id')
            if session_id:
                logging.info(f"Obtained session ID: {session_id}")
                return session_id
            else:
                logging.error(f"Failed to get session_id. Response: {response_data}")
                return None
        except requests.RequestException as e:
            logging.error(f"Error creating session: {e}")
            return None

    def get_keywords(self, query: str) -> list[str]:
        """
        Connects to the agent and prints the entire raw stream message for debugging.
        """
        session_id = self._get_session_id()
        if not session_id:
            return None

        url = f"{self.base_url}/api/v1/agents/{self.agent_id}/completions"
        payload = {
            "id": self.agent_id,
            "question": query,
            "session_id": session_id,
            "stream": True
        }
        
        logging.info("Sending query and streaming response...")
        print("--- Agent Raw Stream Response ---")
        try:
            with requests.post(url, headers=self.headers, json=payload, stream=True, timeout=60) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if line:
                        # Print the raw decoded line from the stream
                        print(line.decode('utf-8'))
            
            print("--- End of Stream ---")
            # Return None because we are only printing, not extracting keywords.
            return None

        except requests.RequestException as e:
            logging.error(f"Error getting keywords from agent: {e}")
            return None

def extract_keywords_from_agent(query: str, config: dict) -> list[str]:
    """Orchestrates the keyword extraction process."""
    agent = RAGFlowAgent(config)
    keywords = agent.get_keywords(query)
    if not keywords:
        logging.error("Halting due to failure to extract keywords.")
        return None
    return keywords

def search_sciencedirect_for_papers(keywords: list[str], config: dict) -> list:
    """Searches the ScienceDirect database using the extracted keywords."""
    if not keywords:
        logging.warning("No keywords provided for ScienceDirect search.")
        return None
        
    client = ElsClient(config['elsevier_api_key'])
    query_string = ' AND '.join(f'"{kw}"' for kw in keywords)
    logging.info(f"Constructed ScienceDirect query: {query_string}")

    try:
        doc_srch = ElsSearch(query_string, 'sciencedirect')
        doc_srch.execute(client, get_all=False)
        results = doc_srch.results
        if not results:
            logging.warning("ScienceDirect search returned no results.")
            return None
        logging.info(f"ScienceDirect search found {len(results)} results.")
        return results[:config.get('max_papers_to_download', 5)]
    except Exception as e:
        logging.error(f"An error occurred during ScienceDirect search: {e}")
        return None
    
def download_articles(search_results: list, config: dict) -> list[str]:
    """Downloads the full text of articles and returns paths to saved JSON files."""
    if not search_results:
        return None

    client = ElsClient(config['elsevier_api_key'])
    download_dir = config['download_directory']
    downloaded_files = []

    logging.info(f"Attempting to download up to {len(search_results)} articles...")
    for paper_meta in search_results:
        doi = paper_meta.get('prism:doi')
        if not doi:
            logging.warning(f"No DOI for paper: '{paper_meta.get('dc:title', 'N/A')}'. Skipping.")
            continue

        try:
            sanitized_doi = re.sub(r'[\\/*?:"<>|]', '_', doi)
            filename = os.path.join(download_dir, f"{sanitized_doi}.json")

            if os.path.exists(filename):
                logging.info(f"Already downloaded: {os.path.basename(filename)}. Skipping.")
                downloaded_files.append(filename)
                continue

            full_doc = FullDoc(doi=doi)
            if full_doc.read(client):
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(full_doc.data, f, indent=4)
                downloaded_files.append(filename)
                logging.info(f"Successfully saved: {os.path.basename(filename)}")
            else:
                logging.warning(f"Failed to retrieve full text for DOI '{doi}'. May be due to access restrictions.")
            time.sleep(1)
        except Exception as e:
            logging.error(f"Failed to download paper with DOI '{doi}': {e}")
            
    return downloaded_files

def upload_papers_to_ragflow(config: dict, file_paths: list[str], kb_name: str):
    """Creates a RAGFlow KB and uploads downloaded papers."""
    if not file_paths:
        logging.info("No new files to upload to RAGFlow.")
        return

    logging.info(f"Preparing to upload {len(file_paths)} files to knowledge base '{kb_name}'...")
    
    try:
        rag_client = RAGFlow(api_key=config['ragflow_api_key'], base_url=config['ragflow_base_url'])
        
        datasets_info = rag_client.get_datasets().get('data', [])
        dataset_id = next((ds['id'] for ds in datasets_info if ds['name'] == kb_name), None)
        
        if dataset_id:
            dataset = rag_client.get_dataset(dataset_id)
            logging.info(f"Using existing knowledge base '{kb_name}' (ID: {dataset.id}).")
        else:
            rag_client.create_dataset(name=kb_name)
            datasets_info = rag_client.get_datasets().get('data', [])
            dataset_id = next((ds['id'] for ds in datasets_info if ds['name'] == kb_name), None)
            dataset = rag_client.get_dataset(dataset_id)
            logging.info(f"Created new knowledge base '{kb_name}' (ID: {dataset.id}).")
        
        logging.info(f"Uploading {len(file_paths)} documents...")
        result = dataset.upload_documents(file_paths)

        if result and result.get('code') == 0:
            logging.info("Documents uploaded successfully. Parsing will be handled by RAGFlow automatically.")
        else:
             logging.error(f"Failed to upload documents. Response: {result}")

    except Exception as e:
        logging.error(f"An error occurred during RAGFlow upload: {e}")

def main():
    """Main function to orchestrate the research assistant workflow."""
    logging.info("--- Automated Research Assistant Workflow ---")
    
    config = load_config()
    if not config:
        exit()

    user_query = "Find paper about transformer"
    
    sanitized_query = re.sub(r'\W+', '_', user_query)
    kb_name = f"{sanitized_query[:50]}_KB"

    keywords = extract_keywords_from_agent(user_query, config)
    if not keywords:
        logging.error("Workflow halted: Could not extract keywords.")
        exit()

    search_results = search_sciencedirect_for_papers(keywords, config)
    if not search_results:
        logging.warning("Workflow finished: No papers found on ScienceDirect.")
        exit()

    downloaded_file_paths = download_articles(search_results, config)
    if not downloaded_file_paths:
        logging.warning("Workflow finished: No papers could be downloaded.")
        exit()

    upload_papers_to_ragflow(config, downloaded_file_paths, kb_name)

    logging.info("--- Workflow Finished ---")
    logging.info(f"Check the RAGFlow UI for the new knowledge base '{kb_name}'.")

if __name__ == "__main__":
    main()