import json
import logging
import requests

class RAGFlowAgent:
    """Handles communication with RAGFlow Agents."""
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
        url = f"{self.base_url}/api/v1/agents/{self.agent_id}/sessions"
        try:
            logging.info("Creating new RAGFlow conversation session...")
            payload = {"user_id": "research_assistant_user"}
            response = requests.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            response_data = response.json()
            session_id = response_data.get('data', {}).get('id')
            if session_id:
                logging.info(f"Obtained session ID: {session_id}")
                return session_id
            else:
                logging.error(f"Failed to get session_id. Response from server: {response_data}")
                return None
        except requests.RequestException as e:
            logging.error(f"Error creating session: {e}")
            return None

    def get_keywords(self, query: str) -> list[str]:
        """
        Connects to the agent, stores the entire raw stream, and then extracts the final keyword answer locally.
        """
        session_id = self._get_session_id()
        if not session_id:
            return None

        url = f"{self.base_url}/api/v1/agents/{self.agent_id}/completions"
        payload = {
            "question": query,
            "session_id": session_id,
            "stream": True
        }
        
        logging.info("Sending query and streaming response...")
        stream_messages = []
        try:
            with requests.post(url, headers=self.headers, json=payload, stream=True, timeout=60) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if line:
                        stream_messages.append(line.decode('utf-8'))
            
            logging.info(f"Stream finished. Captured {len(stream_messages)} lines. Parsing now...")
            
            # Iterate through the stored messages in reverse to find the last valid data message
            for message in reversed(stream_messages):
                if message.startswith('data:'):
                    json_str = message[len('data:'):].strip()
                    if not json_str:
                        continue
                    
                    try:
                        response_data = json.loads(json_str)
                        data_chunk = response_data.get('data', {})

                        # The final message contains 'answer' and 'session_id'
                        if isinstance(data_chunk, dict) and 'answer' in data_chunk and 'session_id' in data_chunk:
                            keywords_str = data_chunk['answer']
                            if "is running" not in keywords_str:
                                keywords = [kw.strip() for kw in keywords_str.split(',') if kw.strip()]
                                logging.info(f"Successfully extracted keywords: {keywords}")
                                return keywords
                    except json.JSONDecodeError:
                        continue # Ignore lines that aren't valid JSON

            logging.warning("Could not find the final keyword message in the stored stream.")
            return None

        except requests.RequestException as e:
            logging.error(f"Error getting keywords from agent: {e}")
            return None

if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Import config loader
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from utils.config import load_config
    
    # Test keyword extraction
    config = load_config()
    agent = RAGFlowAgent(config)
    keywords = agent.get_keywords("What are the latest advancements in llm template-based code generation?")
    print("Extracted keywords:", keywords)