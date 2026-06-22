import os
import re
import math
import pickle
import numpy as np

STOP_WORDS = {
    'the', 'a', 'an', 'and', 'or', 'but', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
    'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'about', 'against', 'between', 'into',
    'through', 'during', 'before', 'after', 'above', 'below', 'from', 'up', 'down', 'in', 'out',
    'this', 'that', 'these', 'those', 'am', 'has', 'have', 'had', 'do', 'does', 'did', 'shall',
    'will', 'should', 'would', 'may', 'might', 'must', 'can', 'could', 'should'
}

class LocalTFIDFStore:
    def __init__(self):
        self.documents = {}  # doc_id -> raw_text
        self.metadatas = {}  # doc_id -> metadata
        self.vocab = {}      # word -> word_index
        self.idf = {}        # word -> idf_score
        self.vectors = {}    # doc_id -> vector (numpy array)
        
    def tokenize(self, text):
        # Convert to lowercase and find all alphanumeric tokens
        tokens = re.findall(r'\b\w+\b', text.lower())
        # Filter stop words and single characters
        return [t for t in tokens if t not in STOP_WORDS and len(t) > 1]

    def fit_and_index(self, chunks):
        """
        chunks is a list of dicts: {chunk_id, raw_text, metadata}
        """
        self.documents = {c["chunk_id"]: c["raw_text"] for c in chunks}
        self.metadatas = {c["chunk_id"]: c["metadata"] for c in chunks}
        
        # Tokenize all documents
        doc_tokens = {c["chunk_id"]: self.tokenize(c["raw_text"]) for c in chunks}
        
        # Build vocabulary
        all_words = set()
        for tokens in doc_tokens.values():
            all_words.update(tokens)
        self.vocab = {word: idx for idx, word in enumerate(sorted(all_words))}
        
        # Calculate document frequency (df) for IDF
        N = len(chunks)
        df = {word: 0 for word in self.vocab}
        for tokens in doc_tokens.values():
            unique_tokens = set(tokens)
            for t in unique_tokens:
                if t in df:
                    df[t] += 1
                    
        # Calculate IDF (with smoothing)
        self.idf = {}
        for word, count in df.items():
            self.idf[word] = math.log((N + 1) / (count + 1)) + 1.0
            
        # Build TF-IDF vectors for all documents
        vocab_size = len(self.vocab)
        self.vectors = {}
        for chunk_id, tokens in doc_tokens.items():
            vec = np.zeros(vocab_size)
            if not tokens:
                self.vectors[chunk_id] = vec
                continue
                
            # Term Frequency (TF)
            tf = {}
            for t in tokens:
                tf[t] = tf.get(t, 0) + 1
                
            for word, count in tf.items():
                if word in self.vocab:
                    idx = self.vocab[word]
                    vec[idx] = count * self.idf[word]
            
            # Normalize vector (L2 norm)
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec = vec / norm
            self.vectors[chunk_id] = vec
            
        print(f"Indexed {N} documents locally. Vocabulary size: {vocab_size}")

    def query(self, query_text, n_results=5, doc_type=None):
        """
        Queries the index using cosine similarity and returns ranked results.
        """
        query_tokens = self.tokenize(query_text)
        vocab_size = len(self.vocab)
        query_vec = np.zeros(vocab_size)
        
        if not query_tokens:
            # If empty query, return first N items
            results = []
            for chunk_id in list(self.documents.keys())[:n_results]:
                results.append({
                    "id": chunk_id,
                    "document": self.documents[chunk_id],
                    "metadata": self.metadatas[chunk_id],
                    "distance": 1.0  # max distance
                })
            return results
            
        # Compute TF-IDF for query
        tf = {}
        for t in query_tokens:
            tf[t] = tf.get(t, 0) + 1
            
        for word, count in tf.items():
            if word in self.vocab:
                idx = self.vocab[word]
                query_vec[idx] = count * self.idf[word]
                
        # Normalize query vector
        norm_q = np.linalg.norm(query_vec)
        if norm_q > 0:
            query_vec = query_vec / norm_q
            
        # Calculate Cosine Similarities
        candidates = []
        for chunk_id, doc_vec in self.vectors.items():
            meta = self.metadatas[chunk_id]
            if doc_type and meta.get("doc_type") != doc_type:
                continue
                
            similarity = np.dot(query_vec, doc_vec)
            # Distance is 1 - similarity (0 = identical, 1 = orthogonal)
            candidates.append((chunk_id, float(1 - similarity)))
            
        # Sort by distance ascending (similarity descending)
        candidates.sort(key=lambda x: x[1])
        
        results = []
        for chunk_id, dist in candidates[:n_results]:
            results.append({
                "id": chunk_id,
                "document": self.documents[chunk_id],
                "metadata": self.metadatas[chunk_id],
                "distance": dist
            })
        return results

    def save(self, filepath):
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "wb") as f:
            pickle.dump(self, f)
        print(f"Vector store saved to {filepath}")

    @staticmethod
    def load(filepath):
        with open(filepath, "rb") as f:
            store = pickle.load(f)
        print(f"Loaded vector store from {filepath} with {len(store.documents)} documents.")
        return store
