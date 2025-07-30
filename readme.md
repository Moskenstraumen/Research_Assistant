# Research Assistant

[![zh-Hans](https://img.shields.io/badge/lang-zh--Hans-red)](https://github.com/Moskenstraumen/Research_Assistant/blob/main/readme.zh-Hans.md)

## Overview
This program extracts keywords based on user input questions through an agent based on DeepSeek-R1:70B, collects academic papers from the ScienceDirect platform, and adds them to the knowledge base after parsing. 

The workflow is:
1. Keyword extraction from user input
2. Retrieve relevant papers from ScienceDirect
3. Document parsing
4. Augmented QA via retrieval from local knowledge base

## Components

### Main Script (`main.py`)
Orchestrates the complete workflow by:
- Loading configuration
- Processing user queries
- Coordinating between RAGFlow and Elsevier services
- Managing the overall paper collection and upload process

### RAGFlow Agent (`ragflow_client/agent.py`)
Handles communication with RAGFlow's AI agents to:
- Create conversation sessions
- Extract keywords from user queries
- Process streaming responses from the AI

### Elsevier Client (`elsevier_client/client.py`)
Manages interactions with ScienceDirect to:
- Search for academic papers using keywords
- Download full-text content
- Save papers locally as JSON files

### RAGFlow Uploader (`ragflow_client/uploader.py`)
Manages the knowledge base in RAGFlow:
- Creates and manages knowledge bases
- Uploads document content
- Monitors document parsing status
- Provides status updates during the upload process

### Configuration (`utils/config.py`)
Handles configuration management:
- Loads settings from config.json
- Creates necessary directories
- Validates configuration format

## RAGFlow Integration
The system integrates with RAGFlow through two main components:

1. **Agent Communication**:
   - Uses API for agent interactions
   - Manages conversation sessions
   - Handles streaming responses for keyword extraction

2. **Knowledge Base Management**:
   - Creates and manages datasets
   - Uploads documents using the RAGFlow SDK
   - Monitors document parsing status
   - Provides progress updates

## Setup Guide

### Prerequisites
- Python 3.8 or higher
- Access to RAGFlow service
- Elsevier API credentials

### Installation

1. Clone the repository:
```sh
git clone https://github.com/Moskenstraumen/Research_Assistant.git
cd research-assistant
```

2. Install dependencies:
```sh
pip install elsapy ragflow-sdk requests
```

3. Configure the application:
Copy the following settings to `config.json`
```json
{
    "ragflow_api_key": "your-ragflow-api-key",
    "ragflow_base_url": "your-ragflow-url",
    "keyword_agent_id": "your-agent-id",
    "elsevier_api_key": "your-elsevier-api-key",
    "download_directory": "./downloads",
    "max_papers_to_download": 5
}
```

### Configuration Options

| Option | Description |
|--------|-------------|
| `ragflow_api_key` | Your RAGFlow API authentication key |
| `ragflow_base_url` | Base URL for RAGFlow service |
| `keyword_agent_id` | ID of the RAGFlow agent for keyword extraction |
| `elsevier_api_key` | Your Elsevier API key for ScienceDirect access |
| `download_directory` | Local directory for storing downloaded papers |
| `max_papers_to_download` | Maximum number of papers to download per query |

### Running the Application

1. Ensure configuration is set up correctly
2. Run the main script:
```sh
python main.py
```

The program will:
- Process the research query
- Extract keywords
- Search and download relevant papers
- Create a knowledge base in RAGFlow
- Upload and process the papers

### Logging
- All operations are logged with timestamps
- Check the console output for progress
- Detailed logs are available in the logging output