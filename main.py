import os
import re
import json
import pickle
import numpy as np
import networkx as nx
import fitz  # PyMuPDF
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from typing import List, Optional

from ingest import HybridVectorStore, client, call_gemini_with_retry, DB_DIR, GRAPH_PATH, REGS_DIR, PROCS_DIR

app = FastAPI(title="Industrial Safety Compliance Checker API")

# Add CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load graph safety check
def load_graph():
    if os.path.exists(GRAPH_PATH):
        try:
            with open(GRAPH_PATH, "rb") as f:
                return pickle.load(f)
        except Exception as e:
            print(f"Error loading graph: {e}")
    return nx.Graph()

class SearchQuery(BaseModel):
    query: str
    n_results: int = 5
    doc_type: Optional[str] = None

class SOPAuditRequest(BaseModel):
    sop_name: str  # Must match a file in data/procedures e.g. SOP_Confined_Space_Entry.pdf

class CustomSOPAuditRequest(BaseModel):
    title: str
    content: str

class AuditFinding(BaseModel):
    status: str = Field(description="Must be 'Compliant' or 'Non-compliant'")
    violated_regulation: str = Field(description="Name and section of safety regulations violated, or 'None'")
    gap_explanation: str = Field(description="Explanation of the gap, non-compliance, or how it aligns with regulations.")
    severity: str = Field(description="Must be one of: 'Critical', 'Major', 'Minor', 'None'")
    recommendation: str = Field(description="Detailed recommendation on how to rewrite the clause to make it fully compliant.")

class SOPAuditReport(BaseModel):
    sop_name: str
    compliance_score: int = Field(description="Percentage score from 0 to 100 based on compliance of all clauses.")
    summary: str = Field(description="High level summary of the audit findings.")
    findings: List[AuditFinding]

def get_hybrid_graph_context(query_text, query_embedding, vdb, G, n_results=4):
    """Retrieves relevant safety guidelines using hybrid Vector search + Graph traversal."""
    # 1. Vector Search
    vector_results = []
    try:
        vector_results = vdb.query(query_embedding, n_results=n_results, doc_type="regulation")
    except Exception as e:
        print(f"Vector search failed: {e}")
        
    # 2. Graph Search via Entity matching
    # Standardize words to find entity nodes
    words = re.findall(r'\b\w+\b', query_text.lower())
    matched_entities = []
    for word in words:
        # Match singular form or check if word is substring
        for node, ndata in G.nodes(data=True):
            if ndata.get("type") == "entity" and (node == word or word in node):
                matched_entities.append(node)
                
    graph_chunks = []
    for ent in set(matched_entities):
        if G.has_node(ent):
            for neighbor in G.neighbors(ent):
                ndata = G.nodes[neighbor]
                if ndata.get("type") == "chunk" and ndata.get("doc_type") == "regulation":
                    graph_chunks.append({
                        "id": neighbor,
                        "document": ndata.get("raw_text", ""),
                        "metadata": {
                            "chunk_id": neighbor,
                            "doc_name": ndata.get("doc_name", ""),
                            "reference": ndata.get("reference", ""),
                            "doc_type": "regulation"
                        },
                        "source": f"Graph entity match: '{ent}'"
                    })
                    
    # Combine vector and graph context, preventing duplicates
    combined = []
    seen_ids = set()
    
    # Vector first
    for r in vector_results:
        if r["id"] not in seen_ids:
            seen_ids.add(r["id"])
            r["source"] = "Vector similarity search"
            combined.append(r)
            
    # Graph second
    for g in graph_chunks:
        if g["id"] not in seen_ids:
            seen_ids.add(g["id"])
            combined.append(g)
            
    return combined[:n_results + 2]

@app.get("/api/documents")
def list_documents():
    """Lists all available regulation and procedure files."""
    regs = []
    if os.path.exists(REGS_DIR):
        regs = [f for f in os.listdir(REGS_DIR) if f.endswith(".pdf")]
    
    procs = []
    if os.path.exists(PROCS_DIR):
        procs = [f for f in os.listdir(PROCS_DIR) if f.endswith(".pdf")]
        
    return {
        "regulations": regs,
        "procedures": procs
    }

@app.post("/api/search")
def search_safety(payload: SearchQuery):
    """Executes a hybrid RAG search query."""
    vdb = HybridVectorStore(DB_DIR)
    G = load_graph()
    
    # Generate Query Embedding
    try:
        emb_response = client.models.embed_content(
            model="models/gemini-embedding-2",
            contents=payload.query
        )
        query_embedding = emb_response.embeddings[0].values
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate embedding: {e}")
        
    context_chunks = get_hybrid_graph_context(payload.query, query_embedding, vdb, G, n_results=payload.n_results)
    
    # Format responses
    results = []
    for c in context_chunks:
        results.append({
            "chunk_id": c["id"],
            "doc_name": c["metadata"].get("doc_name", ""),
            "reference": c["metadata"].get("reference", ""),
            "doc_type": c["metadata"].get("doc_type", ""),
            "text": c["document"],
            "source": c.get("source", "Unknown")
        })
        
    return {"results": results}

@app.post("/api/audit")
def audit_sop(payload: SOPAuditRequest):
    """Audits an existing SOP PDF against regulations."""
    sop_path = os.path.join(PROCS_DIR, payload.sop_name)
    if not os.path.exists(sop_path):
        raise HTTPException(status_code=404, detail=f"SOP file {payload.sop_name} not found.")
        
    G = load_graph()
    vdb = HybridVectorStore(DB_DIR)
    
    # Get chunks of this SOP from the graph
    sop_chunks = []
    for node, data in G.nodes(data=True):
        if data.get("type") == "chunk" and data.get("doc_name") == payload.sop_name:
            sop_chunks.append(data)
            
    if not sop_chunks:
        # Fallback if graph is empty: parse PDF on the fly
        print("SOP chunks not found in knowledge graph, parsing on the fly...")
        doc = fitz.open(sop_path)
        full_text = "".join([page.get_text() for page in doc])
        doc.close()
        
        pattern = re.compile(r'(Section \d+(?:\.\d+)*: [^\n]+)')
        parts = pattern.split(full_text)
        
        idx = 1
        while idx < len(parts):
            ref = parts[idx].strip()
            body = parts[idx+1].strip() if idx+1 < len(parts) else ""
            sop_chunks.append({
                "reference": ref,
                "raw_text": f"{ref}\n{body}"
            })
            idx += 2
            
    if not sop_chunks:
        raise HTTPException(status_code=400, detail="Unable to extract clauses from SOP. Ensure standard formatting.")

    findings = []
    total_score = 0
    
    for chunk in sop_chunks:
        ref = chunk.get("reference", "Clause")
        text = chunk.get("raw_text", "")
        
        # 1. Embed SOP clause
        try:
            emb_res = client.models.embed_content(
                model="models/gemini-embedding-2",
                contents=text
            )
            clause_emb = emb_res.embeddings[0].values
        except Exception as e:
            print(f"Embedding failed for clause: {e}")
            continue
            
        # 2. Retrieve regulations context
        context_chunks = get_hybrid_graph_context(text, clause_emb, vdb, G, n_results=3)
        context_str = "\n\n".join([f"Source: {c['metadata']['doc_name']} - {c['metadata']['reference']}\n{c['document']}" for c in context_chunks])
        
        # 3. Call Gemini for Compliance Check
        prompt = f"""
        You are an expert industrial safety compliance officer auditing a company's Standard Operating Procedure (SOP).
        Compare the following SOP clause against the safety regulations context. Identify if there are any compliance gaps or safety violations.

        SOP Clause to Audit:
        ---
        {text}
        ---

        Relevant Safety Regulations Context:
        ---
        {context_str}
        ---

        Assess whether the SOP clause is compliant. If there is any discrepancy, explain the gap and cite the specific regulation.
        Generate a detailed recommendation on how to rewrite the SOP clause to make it fully compliant.
        """
        
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=AuditFinding,
            temperature=0.1
        )
        
        try:
            response = call_gemini_with_retry(
                client.models.generate_content,
                model="gemini-2.5-flash",
                contents=prompt,
                config=config
            )
            finding = json.loads(response.text)
            
            # Simple scoring logic
            if finding["status"] == "Compliant":
                total_score += 100
            elif finding["severity"] == "Critical":
                total_score += 0
            elif finding["severity"] == "Major":
                total_score += 50
            else:
                total_score += 75
                
            findings.append(finding)
        except Exception as e:
            print(f"Audit LLM call failed for clause {ref}: {e}")
            findings.append({
                "status": "Unknown",
                "violated_regulation": "N/A",
                "gap_explanation": f"Failed to audit: {e}",
                "severity": "None",
                "recommendation": "Review manually."
            })
            total_score += 50

    # Calculate compliance score
    compliance_score = int(total_score / len(findings)) if findings else 100
    
    # Generate high-level summary
    summary_prompt = f"""
    Write a brief 2-3 sentence executive summary of the safety audit report for {payload.sop_name}.
    Compliance Score: {compliance_score}%
    Audit findings: {json.dumps(findings, indent=2)}
    """
    
    try:
        summary_res = call_gemini_with_retry(
            client.models.generate_content,
            model="gemini-2.5-flash",
            contents=summary_prompt
        )
        summary = summary_res.text.strip()
    except Exception as e:
        summary = f"Audit completed with score {compliance_score}%. Review details below."

    return {
        "sop_name": payload.sop_name,
        "compliance_score": compliance_score,
        "summary": summary,
        "findings": findings
    }

@app.get("/api/graph")
def get_graph():
    """Formats the NetworkX Knowledge Graph for frontend Vis.js rendering."""
    G = load_graph()
    
    nodes = []
    for node, data in G.nodes(data=True):
        node_type = data.get("type", "unknown")
        
        if node_type == "chunk":
            doc_type = data.get("doc_type", "regulation")
            group = f"chunk_{doc_type}"
            label = data.get("reference", node)
            title = f"Document: {data.get('doc_name')}\nSection: {data.get('reference')}\n\n{data.get('raw_text', '')[:300]}..."
        else:
            category = data.get("category", "unknown")
            group = f"entity_{category}"
            label = node
            title = f"Entity: {node}\nCategory: {category.upper()}"
            
        nodes.append({
            "id": node,
            "label": label,
            "title": title,
            "group": group
        })
        
    edges = []
    for u, v in G.edges():
        edges.append({
            "from": u,
            "to": v
        })
        
    return {"nodes": nodes, "edges": edges}

# Serve single-page dashboard at root
@app.get("/", response_class=HTMLResponse)
def read_root():
    static_index = os.path.join("static", "index.html")
    if os.path.exists(static_index):
        with open(static_index, "r", encoding="utf-8") as f:
            return f.read()
    return HTMLResponse("<h1>Safety Dashboard loading...</h1><p>Please create index.html in the static folder.</p>")

# Mount static folder
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
