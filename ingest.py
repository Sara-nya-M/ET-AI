import os
import re
import json
import time
import random
import pickle
import fitz  # PyMuPDF
import networkx as nx
import chromadb
from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai.errors import APIError
from pydantic import BaseModel, Field
from typing import List

# Load environment variables
load_dotenv()

# Initialize Gemini Client
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

# Define directories
DATA_DIR = "data"
REGS_DIR = os.path.join(DATA_DIR, "regulations")
PROCS_DIR = os.path.join(DATA_DIR, "procedures")
DB_DIR = os.path.join(DATA_DIR, "db")
GRAPH_PATH = os.path.join(DATA_DIR, "knowledge_graph.pkl")

# Pydantic schema for Entity Extraction
class Entity(BaseModel):
    name: str = Field(description="The name of the entity, standardized, e.g. 'gas testing', 'steel hammer', 'oxygen', 'standby observer'. Standardize to lowercase singular.")
    category: str = Field(description="The category of the entity, e.g. 'equipment', 'permit_type', 'hazard', 'role', 'procedure'.")

class EntityList(BaseModel):
    entities: List[Entity]

def call_gemini_with_retry(func, *args, **kwargs):
    """Wrapper to call Gemini API with retry and backoff."""
    max_retries = 8
    base_delay = 2.0
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if attempt == max_retries - 1:
                print("Max retries reached. Gemini API call failed.")
                raise e
            
            error_str = str(e).lower()
            if "429" in error_str or "resource_exhausted" in error_str or "quota" in error_str:
                delay = 35.0 + random.uniform(1.0, 5.0)
                print(f"Gemini API rate limit (429) encountered. Sleeping for {delay:.2f} seconds to reset quota...")
            else:
                delay = base_delay * (2 ** attempt) + random.uniform(0.1, 1.0)
                print(f"Gemini API error encountered: {e}. Retrying in {delay:.2f} seconds...")
                
            time.sleep(delay)

class HybridVectorStore:
    """ChromaDB wrapper with a clean fallback to a local pickle file in case of native build errors."""
    def __init__(self, persist_dir):
        self.persist_dir = persist_dir
        self.use_fallback = False
        self.fallback_data = []
        os.makedirs(persist_dir, exist_ok=True)
        
        try:
            self.chroma_client = chromadb.PersistentClient(path=persist_dir)
            self.collection = self.chroma_client.get_or_create_collection("industrial_knowledge")
            print("Successfully initialized ChromaDB persistent client.")
        except Exception as e:
            print(f"ChromaDB initialization failed ({e}). Falling back to file-based vector storage.")
            self.use_fallback = True
            self.fallback_path = os.path.join(persist_dir, "fallback_db.pkl")
            if os.path.exists(self.fallback_path):
                with open(self.fallback_path, "rb") as f:
                    self.fallback_data = pickle.load(f)
                print(f"Loaded {len(self.fallback_data)} records from fallback database.")

    def add(self, doc_id, document, embedding, metadata):
        if not self.use_fallback:
            try:
                self.collection.add(
                    ids=[doc_id],
                    embeddings=[embedding],
                    documents=[document],
                    metadatas=[metadata]
                )
                return
            except Exception as e:
                print(f"ChromaDB write error ({e}), switching to fallback store.")
                self.use_fallback = True
                self.fallback_path = os.path.join(self.persist_dir, "fallback_db.pkl")
        
        # Fallback mechanism
        # Remove existing if updates occur
        self.fallback_data = [item for item in self.fallback_data if item["id"] != doc_id]
        self.fallback_data.append({
            "id": doc_id,
            "document": document,
            "embedding": embedding,
            "metadata": metadata
        })
        with open(self.fallback_path, "wb") as f:
            pickle.dump(self.fallback_data, f)

    def query(self, query_embedding, n_results=5, doc_type=None):
        if not self.use_fallback:
            try:
                where_clause = {}
                if doc_type:
                    where_clause = {"doc_type": doc_type}
                results = self.collection.query(
                    query_embeddings=[query_embedding],
                    n_results=n_results,
                    where=where_clause if where_clause else None
                )
                # Parse to consistent format
                formatted = []
                if results and 'documents' in results and results['documents']:
                    for idx in range(len(results['documents'][0])):
                        formatted.append({
                            "id": results['ids'][0][idx],
                            "document": results['documents'][0][idx],
                            "metadata": results['metadatas'][0][idx],
                            "distance": results['distances'][0][idx] if 'distances' in results else 0
                        })
                return formatted
            except Exception as e:
                print(f"ChromaDB query error ({e}), reading from fallback store.")
                self.use_fallback = True
        
        # Fallback cosine similarity
        import numpy as np
        query_vec = np.array(query_embedding)
        candidates = []
        for item in self.fallback_data:
            if doc_type and item["metadata"].get("doc_type") != doc_type:
                continue
            item_vec = np.array(item["embedding"])
            # Cosine similarity
            dot_product = np.dot(query_vec, item_vec)
            norm_q = np.linalg.norm(query_vec)
            norm_i = np.linalg.norm(item_vec)
            similarity = dot_product / (norm_q * norm_i) if norm_q * norm_i > 0 else 0
            candidates.append((item, 1 - similarity)) # convert to distance-like (lower distance = closer)
            
        candidates.sort(key=lambda x: x[1])
        formatted = []
        for item, dist in candidates[:n_results]:
            formatted.append({
                "id": item["id"],
                "document": item["document"],
                "metadata": item["metadata"],
                "distance": float(dist)
            })
        return formatted

def extract_chunks_from_pdf(filepath, doc_type):
    """
    Parses a PDF into chunks splitting on clause numbers and section headers.
    Returns a list of dicts: {chunk_id, doc_name, reference, raw_text, doc_type}
    """
    doc_name = os.path.basename(filepath)
    doc = fitz.open(filepath)
    full_text = ""
    for page in doc:
        full_text += page.get_text()
    doc.close()
    
    # Split using Regex matching:
    # "Section X.Y: Header" or "Clause X.Y.Z: Header"
    pattern = re.compile(r'(Section \d+(?:\.\d+)*: [^\n]+|Clause \d+(?:\.\d+)*: [^\n]+)')
    parts = pattern.split(full_text)
    
    chunks = []
    # If the document text starts with text before the first section, parts[0] is that text.
    title_text = parts[0].strip()
    
    idx = 1
    while idx < len(parts):
        ref = parts[idx].strip()
        body = parts[idx+1].strip() if idx+1 < len(parts) else ""
        
        # Create standard ID: e.g. Factory_Act_1948_pdf_Section_36_1
        clean_ref = re.sub(r'[^a-zA-Z0-9]', '_', ref)
        chunk_id = f"{doc_name.replace('.', '_')}_{clean_ref}"
        
        chunks.append({
            "chunk_id": chunk_id,
            "doc_name": doc_name,
            "reference": ref,
            "raw_text": f"{ref}\n{body}",
            "doc_type": doc_type
        })
        idx += 2
        
    return chunks

API_RATE_LIMITED = False

def local_extract_entities(text):
    """Local rule-based entity extractor to fallback to if Gemini API rate limits are hit."""
    categories = {
        "equipment": ["gas detector", "detector", "steel hammer", "hammer", "vessel", "breathing apparatus", "safety harness", "lifeline", "harness", "chisel", "led flashlight", "flashlight", "lighting", "dielectric gloves", "gloves", "safety boots", "boots", "voltage tester", "mask", "rope", "suit", "extinguisher", "hose"],
        "permit_type": ["hot work permit", "hot work", "confined space entry permit", "confined space", "cold work permit", "cold work", "work permit", "permit"],
        "hazard": ["toxic fumes", "fumes", "explosive gas", "gas", "ignition sources", "ignition", "combustible materials", "combustible", "combustibles", "flammable", "toxic", "dust", "vapor", "fume", "explosion", "spark", "odor", "pressure"],
        "role": ["standby observer", "observer", "standby person", "competent person", "technician", "operator", "fire watch", "rescue team", "entrant", "receiver", "issuer"],
        "procedure": ["gas testing", "testing", "lockout tagout", "loto", "energy isolation", "isolation", "vessel cleaning", "cleaning", "calibration", "rescue", "blinding", "disconnection", "unloading", "ventilation", "welding", "cutting", "grinding"]
    }
    
    extracted = []
    text_lower = text.lower()
    for cat, terms in categories.items():
        for term in terms:
            pattern = r'\b' + re.escape(term) + r'\b'
            if re.search(pattern, text_lower):
                extracted.append({
                    "name": term,
                    "category": cat
                })
    return extracted

def extract_entities_from_chunk(chunk_text):
    """Calls Gemini-2.5-flash with structured JSON response schema to extract entities, with local fallback."""
    global API_RATE_LIMITED
    if API_RATE_LIMITED:
        return local_extract_entities(chunk_text)
        
    prompt = f"""
    You are an expert industrial knowledge graph system.
    Extract key entities from the following text chunk.
    Entities of interest:
    1. 'equipment' (e.g. gas detector, steel hammer, vessel, breathing apparatus, safety harness)
    2. 'permit_type' (e.g. hot work permit, confined space entry permit, cold work permit)
    3. 'hazard' (e.g. toxic fumes, explosive gas, ignition sources, combustible materials)
    4. 'role' (e.g. standby observer, competent person, technician)
    5. 'procedure' (e.g. gas testing, lockout tagout, energy isolation, vessel cleaning)

    Standardize entity names to lowercase singular. For example, "oxygen meters" -> "oxygen meter", "gas tests" -> "gas testing".
    
    Text chunk:
    ---
    {chunk_text}
    ---
    """
    
    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema={
            "type": "OBJECT",
            "properties": {
                "entities": {
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "name": {
                                "type": "STRING",
                                "description": "The name of the entity, standardized to lowercase singular, e.g. 'gas testing', 'steel hammer'."
                            },
                            "category": {
                                "type": "STRING",
                                "description": "The category of the entity, e.g. 'equipment', 'permit_type', 'hazard', 'role', 'procedure'."
                            }
                        },
                        "required": ["name", "category"]
                    }
                }
            },
            "required": ["entities"]
        },
        temperature=0.1
    )
    
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=config
        )
        extracted = json.loads(response.text)
        return extracted.get("entities", [])
    except Exception as e:
        error_str = str(e).lower()
        if "429" in error_str or "resource_exhausted" in error_str or "quota" in error_str:
            print("Gemini API rate limit (429) detected. Switching to local keyword entity extractor for the remaining chunks.")
            API_RATE_LIMITED = True
        else:
            print(f"Gemini entity extraction failed: {e}. Falling back to local extractor.")
        return local_extract_entities(chunk_text)

def run_ingestion():
    print("Starting document ingestion pipeline...")
    
    # 1. Initialize Hybrid Vector Database
    vdb = HybridVectorStore(DB_DIR)
    
    # 2. Find all PDF files
    pdf_files = []
    if os.path.exists(REGS_DIR):
        for f in os.listdir(REGS_DIR):
            if f.endswith(".pdf"):
                pdf_files.append((os.path.join(REGS_DIR, f), "regulation"))
    if os.path.exists(PROCS_DIR):
        for f in os.listdir(PROCS_DIR):
            if f.endswith(".pdf"):
                pdf_files.append((os.path.join(PROCS_DIR, f), "procedure"))
                
    if not pdf_files:
        print("No PDF files found! Please run generate_docs.py first.")
        return

    # 3. Parse PDFs into Chunks
    all_chunks = []
    for filepath, doc_type in pdf_files:
        print(f"Parsing {filepath} ({doc_type})...")
        chunks = extract_chunks_from_pdf(filepath, doc_type)
        all_chunks.extend(chunks)
    
    print(f"Total chunks extracted: {len(all_chunks)}")
    
    # 4. Initialize NetworkX Knowledge Graph
    G = nx.Graph()
    
    # 5. Process each Chunk (Embed, Index, Extract Entities, build Graph)
    for i, chunk in enumerate(all_chunks):
        chunk_id = chunk["chunk_id"]
        raw_text = chunk["raw_text"]
        doc_name = chunk["doc_name"]
        ref = chunk["reference"]
        doc_type = chunk["doc_type"]
        
        print(f"[{i+1}/{len(all_chunks)}] Processing chunk: {chunk_id}")
        
        # 5a. Generate Embedding (models/gemini-embedding-2)
        def generate_emb():
            return client.models.embed_content(
                model="models/gemini-embedding-2",
                contents=raw_text
            )
        emb_response = call_gemini_with_retry(generate_emb)
        embedding = emb_response.embeddings[0].values
        
        # 5b. Index in Vector Store
        metadata = {
            "chunk_id": chunk_id,
            "doc_name": doc_name,
            "reference": ref,
            "doc_type": doc_type
        }
        vdb.add(chunk_id, raw_text, embedding, metadata)
        
        # 5c. Extract Entities
        entities = extract_entities_from_chunk(raw_text)
        print(f"   Extracted {len(entities)} entities: {[e['name'] for e in entities]}")
        
        # 5d. Add to NetworkX Graph
        # Node for the chunk
        G.add_node(chunk_id, type="chunk", doc_name=doc_name, reference=ref, doc_type=doc_type, raw_text=raw_text)
        
        # Nodes and edges for entities
        for ent in entities:
            ent_name = ent["name"].strip().lower()
            ent_cat = ent["category"].strip().lower()
            if not ent_name:
                continue
            # Ensure entity node exists
            if not G.has_node(ent_name):
                G.add_node(ent_name, type="entity", category=ent_cat)
            # Add edge connecting chunk to entity
            G.add_edge(chunk_id, ent_name)
            
        # Rate limit protection sleep for free tier (4.5s keeps us under 15 RPM)
        time.sleep(4.5)
        
    # 6. Save Knowledge Graph
    with open(GRAPH_PATH, "wb") as f:
        pickle.dump(G, f)
        
    print(f"Knowledge Graph saved to {GRAPH_PATH} with {G.number_of_nodes()} nodes and {G.number_of_edges()} edges.")
    print("Ingestion pipeline completed successfully!")

if __name__ == "__main__":
    run_ingestion()
