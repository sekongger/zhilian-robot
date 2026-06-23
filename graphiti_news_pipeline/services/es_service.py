import os
import logging
from elasticsearch import Elasticsearch
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Configuration ---
# Get ES config from environment variables with sensible defaults
ES_HOST = os.environ.get("ES_HOST", "localhost")
ES_PORT = int(os.environ.get("ES_PORT", 9200))
ES_USER = os.environ.get("ES_USER", "elastic")
ES_PASS = os.environ.get("ES_PASS", "password")
GRAPH_NODES_INDEX = "graph_nodes"

class ElasticsearchService:
    def __init__(self):
        self.client = None
        # The explicit connection call is removed.
        # Connection will now be lazily initialized by get_client().

    def connect(self):
        """Initializes or re-initializes the Elasticsearch client."""
        # Prevent reconnecting if already connected and healthy
        if self.client and self.client.ping():
            logging.info("Elasticsearch client is already connected.")
            return

        try:
            # Use https for cloud-hosted, http for local dev if needed
            scheme = "https" if "aliyuncs.com" in ES_HOST else "http"
            
            self.client = Elasticsearch(
                [f"{scheme}://{ES_HOST}:{ES_PORT}"],
                basic_auth=(ES_USER, ES_PASS),
                verify_certs=False, # Set to True in production with proper certs
                request_timeout=30
            )
            if not self.client.ping():
                raise ConnectionError("Could not connect to Elasticsearch.")
            logging.info("Successfully connected to Elasticsearch.")
        except Exception as e:
            logging.error(f"Failed to connect to Elasticsearch: {e}", exc_info=True)
            self.client = None

    def get_client(self) -> Elasticsearch:
        """Returns the active Elasticsearch client, reconnecting if necessary."""
        if not self.client or not self.client.ping():
            logging.warning("Elasticsearch connection lost or not established. Reconnecting...")
            self.connect()
        return self.client

# Instantiate a singleton instance of the service for the application to use
es_service = ElasticsearchService()
