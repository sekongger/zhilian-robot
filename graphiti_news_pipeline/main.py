# --- ROBUST MONKEY-PATCH FOR graphiti-core DATETIME SERIALIZATION BUG ---
# This patch modifies the default JSON encoder to handle datetime objects.
# This is a more robust method than replacing json.dumps and should be respected
# by all parts of the application, including the graphiti-core library.
import json
from datetime import date, datetime
from neo4j.time import DateTime as Neo4jDateTime # Import the specific Neo4j DateTime type

_original_default = json.JSONEncoder.default
def _new_default(self, o):
    # Now check for standard datetime, date, AND neo4j.time.DateTime
    if isinstance(o, (datetime, date, Neo4jDateTime)):
        return o.isoformat() # neo4j.time.DateTime objects also have .isoformat()
    return _original_default(self, o)

json.JSONEncoder.default = _new_default
# --- END MONKEY-PATCH ---

from fastapi import FastAPI
from api import graph_routes
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Graphiti Industry Knowledge Graph API",
    description="API for building and querying an industry knowledge graph.",
    version="1.0.0"
)

# --- CORS Middleware Configuration ---
# This is necessary to allow the frontend (running on a different port)
# to communicate with the backend API.
origins = ["*"]  # Allows all origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the graph API routes
app.include_router(graph_routes.router, prefix="/api", tags=["Knowledge Graph"])

@app.get("/", tags=["Health Check"])
async def read_root():
    """
    Root endpoint for health check.
    """
    return {"status": "ok", "message": "Welcome to the Graphiti API!"}

# The following lines are for running the server directly with `python main.py`
# For production, it's better to use `uvicorn main:app --reload`
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
