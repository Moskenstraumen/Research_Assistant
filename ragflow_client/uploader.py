import logging
import os
import time
from ragflow_sdk import RAGFlow

class RAGFlowUploader:
    """Handles syncing local files to a RAGFlow knowledge base."""
    def __init__(self, config: dict):
        self.rag_client = RAGFlow(
            api_key=config['ragflow_api_key'], 
            base_url=config['ragflow_base_url']
        )
        self.kb_name = ""
        self.dataset = None

    def _get_or_create_kb(self, kb_name: str):
        """Finds an existing KB or creates a new one."""
        self.kb_name = kb_name
        logging.info(f"Accessing knowledge base: '{self.kb_name}'...")
        all_datasets = self.rag_client.list_datasets()
        existing_dataset = next((ds for ds in all_datasets if ds.name == self.kb_name), None)
        
        if existing_dataset:
            logging.info("Knowledge base already exists.")
            self.dataset = existing_dataset
        else:
            logging.info("Knowledge base not found. Creating a new one...")
            self.dataset = self.rag_client.create_dataset(name=self.kb_name)
            logging.info(f"Successfully created KB with ID: {self.dataset.id}")
        
        if not self.dataset:
            raise Exception("Failed to get or create the knowledge base.")

    def manage_kb_sync(self, file_paths: list[str], kb_name: str):
        """
        Manages the full sync process: lists new files, uploads,
        lists unparsed, parses, and lists parsed.
        """
        try:
            self._get_or_create_kb(kb_name)
            
            # --- 1. List new documents pending upload ---
            logging.info("### Step 1: Checking for New Documents ###")
            existing_docs = self.dataset.list_documents()
            existing_doc_names = {doc.name for doc in existing_docs}
            
            new_files_to_upload = [
                fp for fp in file_paths if os.path.basename(fp) not in existing_doc_names
            ]

            if not new_files_to_upload:
                logging.info("No new documents to upload.")
            else:
                logging.info(f"Found {len(new_files_to_upload)} new documents pending upload:")
                for fp in new_files_to_upload:
                    print(f"  - {os.path.basename(fp)}")
                
                document_list = []
                for file_path in new_files_to_upload:
                    with open(file_path, 'rb') as f:
                        document_list.append({
                            "display_name": os.path.basename(file_path),
                            "blob": f.read()
                        })
                logging.info(f"Uploading {len(document_list)} new documents...")
                self.dataset.upload_documents(document_list)
                logging.info("Upload complete.")

            # --- 2. List all documents in the knowledge base ---
            logging.info("### Step 2: Listing All Documents in Knowledge Base ###")
            all_docs = self.dataset.list_documents()
            logging.info(f"Total documents in '{self.kb_name}': {len(all_docs)}")
            for doc in all_docs:
                # CORRECTED: Use doc.run to get the status
                print(f"  - {doc.name} (Status: {doc.run})")

            # --- 3. List unparsed documents before parsing starts ---
            logging.info("### Step 3: Checking for Unparsed Documents ###")
            # CORRECTED: Check for 'UNSTART' status in the 'run' attribute
            unparsed_docs = [doc for doc in all_docs if doc.run == 'UNSTART']

            if not unparsed_docs:
                logging.info("No documents are pending parsing.")
                return
            
            logging.info(f"Found {len(unparsed_docs)} unparsed documents:")
            for doc in unparsed_docs:
                print(f"  - {doc.name}")

            unparsed_doc_ids = [doc.id for doc in unparsed_docs]
            logging.info("Triggering asynchronous parsing...")
            self.dataset.async_parse_documents(unparsed_doc_ids)
            logging.info("Parsing initiated. Monitoring progress...")

            # --- 4. List parsed documents when parsing is finished ---
            while True:
                time.sleep(10)
                current_docs = self.dataset.list_documents()
                
                still_parsing_count = 0
                for doc in current_docs:
                    if doc.id in unparsed_doc_ids:
                        # CORRECTED: Check for completion status 'DONE' in the 'run' attribute
                        if doc.run != 'DONE':
                            still_parsing_count += 1
                
                if still_parsing_count == 0:
                    logging.info("### Step 4: Listing Parsed Documents ###")
                    logging.info("All documents have been parsed successfully.")
                    parsed_docs = self.dataset.list_documents()
                    for doc in parsed_docs:
                        # CORRECTED: Use doc.run to get the final status
                        print(f"  - {doc.name} (Final Status: {doc.run})")
                    break
                
                logging.info(f"{still_parsing_count} documents are still parsing. Checking again in 10 seconds...")

        except Exception as e:
            logging.error(f"An error occurred during the RAGFlow workflow: {e}")

if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Loads utility functions from utils
    try:
        import sys
        # This allows the script to find the 'utils' folder in a parent directory
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from utils.config import load_config
        
        # Test file upload
        config = load_config()
        uploader = RAGFlowUploader(config)
        
        # Example: Find and upload all JSON files from the configured downloads directory
        import glob
        download_dir = config.get('download_directory', './downloads')
        files_to_upload = glob.glob(os.path.join(download_dir, '*.json'))
        
        if files_to_upload:
            # CORRECTED: Call the new manage_kb_sync function
            uploader.manage_kb_sync(files_to_upload, "test_knowledge_base")
        else:
            print(f"No .json files found in '{download_dir}' to upload.")

    except ImportError:
        logging.warning("Could not import 'load_config' from 'utils.config'. This script will not run standalone.")
    except Exception as e:
        logging.error(f"An error occurred in the main execution block: {e}")