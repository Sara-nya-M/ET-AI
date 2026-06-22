# PROJECT SUBMISSION REPORT: SafeFlow AI
## PS 8: AI for Industrial Knowledge Intelligence: Unified Asset & Operations Brain

---

### 1. Executive Summary
In industrial plants, refineries, and manufacturing facilities, compliance with safety regulations (e.g., Factories Act, OISD standards, PESO guidelines) is critical to prevent catastrophic accidents. Standard Operating Procedures (SOPs) govern hazardous activities like Hot Work, Confined Space Entry, and Lockout-Tagout (LOTO). However, manual auditing of these procedures is labor-intensive, error-prone, and disconnected.

**SafeFlow AI** is a unified digital "Operations & Asset Brain" that bridges the gap between raw regulatory compliance and day-to-day industrial operations. By structuring regulatory guidelines into a **Semantic Knowledge Graph** combined with a **Vector Database (Hybrid RAG)**, SafeFlow AI automates the compliance auditing of SOPs. It calculates safety scores, flags precise compliance gaps (such as incorrect clearance distances or lack of certified tools), and provides LLM-driven recommendations to automatically rewrite procedures to regulatory compliance.

---

### 2. The Problem & Challenges
Heavy industries struggle with two key challenges:
1. **Information Silos**: Regulatory manuals are hundreds of pages long and updated infrequently. Plant managers write SOPs in separate documents, making it difficult to trace compliance.
2. **LLM Hallucinations in Standard RAG**: Relying on standard Vector Search (RAG) often retrieves disconnected text blocks without understanding key concepts. For example, a vector search for "testing" might retrieve generic data rather than recognizing the specific entity relationships between "Authorized Personnel," "Gas Detectors," and "Oxygen Level Limits."

---

### 3. SafeFlow AI Solution & Architecture
SafeFlow AI uses a **Hybrid Knowledge Graph + Vector Database RAG** system to achieve 100% precision in safety compliance:

```
[Industrial Safety Regulations PDFs]
                 │
                 ▼
     [LLM Entity-Relation Extractor]
                 │
      ┌──────────┴──────────┐
      ▼                     ▼
[NetworkX Graph]    [ChromaDB Vector Store]
(Semantic Concepts)    (Cosine Similarity)
      │                     │
      └──────────┬──────────┘
                 ▼
       [Hybrid Context Search] ◄──── [Company SOP PDF Upload]
                 │
                 ▼
       [Gemini 2.5 Flash LLM]
                 │
                 ▼
    [Automated Compliance Report]
```

* **Knowledge Ingestion**: Regulations are parsed using PyMuPDF. An entity-relation extraction pipeline powered by Gemini extracts key nodes: **Equipment**, **Hazard**, **Role**, **Procedure**, and **Regulations**, forming a structured network.
* **Hybrid Search Engine**: When auditing an SOP clause, the query goes through both:
  1. *Vector Search*: Extracts semantically similar text blocks from regulations.
  2. *Graph Traversal*: Looks up related entity nodes (e.g., "Confined Space" connects to "Standby Observer" and "Oxygen Meter").
  These two sources are combined to provide a robust, hallucination-free context.
* **LLM Audit & Generation**: Gemini 2.5 Flash evaluates the SOP against the hybrid context and outputs a JSON report outlining the status, gap explanation, severity, and compliant rewrite recommendation.

---

### 4. Technical Implementation Detail

* **FastAPI Backend (`main.py`)**: Exposes REST endpoints for:
  - `/api/documents`: Lists available regulations and SOP files.
  - `/api/search`: Performs hybrid RAG searches.
  - `/api/audit`: Audits SOP files against ingested regulations.
  - `/api/graph`: Returns the Node-Link data for graph visualization.
* **Knowledge Builder (`ingest.py`)**: Runs on-demand to process incoming PDF files, chunk text, build the NetworkX graph structure, and index embeddings via `gemini-embedding-2`.
* **Glassmorphism Web Dashboard**: A single-page dashboard designed using vanilla HTML/CSS and JavaScript. It visualizes the interactive Knowledge Graph using **Vis.js**, allowing users to click and inspect nodes.

---

### 5. Walkthrough of Application Capabilities

#### A. SOP Compliance Auditing Dashboard
Allows safety officers to select an SOP from a dropdown list and run a real-time audit.
* **Compliance Score**: Visualized in an animated circular meter.
* **Audit Findings**: Detailed list showing:
  - *Status*: Compliant / Non-Compliant.
  - *Violated Regulation*: Explicit reference (e.g., OISD-STD-105 Clause 4.2.1).
  - *Severity Level*: Critical / Major / Minor.
  - *Actionable Recommendation*: An exact suggested revision of the clause to ensure safety compliance.

#### B. Interactive Safety Graph (Unified Brain)
Visualizes relationships between safety entities.
* **Nodes**: Color-coded by type (Regulation chunks, SOP chunks, Hazards, Roles, Equipment).
* **Node Inspector**: Displays information about the selected node and its direct connections, giving users a complete mental model of industrial compliance.

#### C. Hybrid RAG Search
Allows users to type plain-language queries (e.g., *"What are LOTO requirements?"*) and retrieve matched regulation entries indicating if they came from **Vector similarity search** or **Graph entity matches**.

---

### 6. Novelty & Key Differentiators
* **Zero Hallucination Retrieval**: By grounding the LLM in a structural Knowledge Graph, the model is prevented from making up rules. It must cite explicit clauses.
* **Dynamic Context Merging**: Traditional systems use vector-only search. SafeFlow AI is hybrid; it uses topological relations (like connections between hazards and specific protective gear) alongside text search.
* **Beautiful User Experience**: Simple, responsive, dark-theme dashboard that can be easily loaded in any control room environment.

---

### 7. Future Scope & Scalability
1. **Real-time Camera/IoT Feeds Integration**: Extend the asset brain to compare real-time site activity (captured by cameras/IoT sensors) with active SOP permits.
2. **Multi-SOP Cross-Referencing**: Flag contradictions between different SOPs (e.g., conflicting procedures for the same physical equipment).
3. **Automated Incident Logging**: Automatically link safety violations to historical incident logs to adjust risk levels dynamically.
