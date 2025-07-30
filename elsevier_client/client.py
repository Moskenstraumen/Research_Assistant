import json
import logging
import os
import re
import time
from elsapy.elsclient import ElsClient
from elsapy.elsdoc import FullDoc
from elsapy.elssearch import ElsSearch

class ElsevierClient:
    """Handles paper search and download from Elsevier."""
    def __init__(self, config: dict):
        self.client = ElsClient(config['elsevier_api_key'])
        self.download_dir = config.get('download_directory', './downloads')
        self.max_papers = config.get('max_papers_to_download', 5)
        os.makedirs(self.download_dir, exist_ok=True)

    def search_papers(self, keywords: list[str]) -> list:
        """Searches ScienceDirect using keywords."""
        if not keywords:
            logging.warning("No keywords provided for ScienceDirect search.")
            return None
            
        query_string = ' , '.join(f'{kw}' for kw in keywords)
        logging.info(f"Constructed ScienceDirect query: {query_string}")

        try:
            doc_srch = ElsSearch(query_string, 'sciencedirect')
            doc_srch.execute(self.client, get_all=False)
            results = doc_srch.results
            if not results:
                logging.warning("ScienceDirect search returned no results.")
                return None
            logging.info(f"ScienceDirect search found {len(results)} results.")
            return results[:self.max_papers]
        except Exception as e:
            logging.error(f"An error occurred during ScienceDirect search: {e}")
            return None

    def download_papers(self, search_results: list) -> list[str]:
        """Downloads the full text of articles and returns paths to saved JSON files."""
        if not search_results:
            return None

        downloaded_files = []

        logging.info(f"Attempting to download up to {len(search_results)} articles to '{self.download_dir}'...")
        for paper_meta in search_results:
            doi = paper_meta.get('prism:doi')
            if not doi:
                logging.warning(f"No DOI for paper: '{paper_meta.get('dc:title', 'N/A')}'. Skipping.")
                continue

            try:
                # Sanitize DOI to create a valid filename
                sanitized_doi = re.sub(r'[\\/*?:"<>|]', '_', doi)
                filename = os.path.join(self.download_dir, f"{sanitized_doi}.json")

                if os.path.exists(filename):
                    logging.info(f"Already downloaded: {os.path.basename(filename)}. Skipping.")
                    downloaded_files.append(filename)
                    continue

                full_doc = FullDoc(doi=doi)
                if full_doc.read(self.client):
                    # Save the article's full data as a JSON file
                    with open(filename, 'w', encoding='utf-8') as f:
                        json.dump(full_doc.data, f, indent=4)
                    downloaded_files.append(filename)
                    logging.info(f"Successfully saved: {os.path.basename(filename)}")
                else:
                    logging.warning(f"Failed to retrieve full text for DOI '{doi}'. This may be due to access restrictions.")
                
                # Be respectful to the API server by waiting a moment between requests
                time.sleep(1) 
                
            except Exception as e:
                logging.error(f"Failed to download paper with DOI '{doi}': {e}")
                
        return downloaded_files

if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Import config loader
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from utils.config import load_config
    
    ''' # Test paper search and download
    config = load_config()
    client = ElsevierClient(config)
    results = client.search_papers(["llm", "tokamak"])
    if results:
        files = client.download_papers(results)
        print("Downloaded files:", files) '''