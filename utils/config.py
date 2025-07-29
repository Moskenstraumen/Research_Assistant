import json
import logging
import os

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

if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    # Test config loading
    config = load_config()
    print("Loaded config:", config)