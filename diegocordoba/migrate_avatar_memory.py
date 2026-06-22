import json
import os
import sys

# We'll import these after assuming they are installed
try:
    import chromadb
    from chromadb.utils import embedding_functions
except ImportError:
    print("Error: chromadb or sentence-transformers not installed.")
    print("Run: pip install chromadb sentence-transformers")
    sys.exit(1)

# Paths
json_path = os.path.expanduser("~/.prime_avatar_memory.json")
db_path = os.path.expanduser("~/.prime_avatar_chroma_db")

def main():
    print("Initializing ChromaDB...")
    client = chromadb.PersistentClient(path=db_path)
    
    print("Loading embedding model (this may take a minute the first time)...")
    # Using the lightweight, fast MiniLM model
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
    
    collection = client.get_or_create_collection(
        name="chat_history", 
        embedding_function=ef
    )

    if not os.path.exists(json_path):
        print(f"File not found: {json_path}")
        return

    print(f"Reading {json_path}...")
    with open(json_path, 'r', encoding='utf-8') as f:
        messages = json.load(f)

    documents = []
    metadatas = []
    ids = []

    msg_id = 0
    for msg in messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        
        text_content = ""
        # Handle simple string content
        if isinstance(content, str):
            text_content = content
            
        # Handle Anthropic/OpenAI array-style content blocks
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_content += block.get("text", "") + "\n"
        
        text_content = text_content.strip()
        
        if text_content:
            documents.append(text_content)
            metadatas.append({"role": role})
            ids.append(f"msg_{msg_id}")
            msg_id += 1

    if documents:
        print(f"Found {len(documents)} text messages.")
        print("Inserting into local ChromaDB... (Generating vectors)")
        
        # Add to database
        collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        print("\n✅ Migration complete!")
        print(f"Database saved to: {db_path}")
        
        # Test a query
        print("\n--- Running a quick test query ---")
        test_query = "What did we talk about regarding Reto Actinver?"
        print(f"Query: '{test_query}'")
        
        results = collection.query(
            query_texts=[test_query],
            n_results=2
        )
        
        for i, doc in enumerate(results['documents'][0]):
            print(f"\nResult {i+1}:")
            print(doc[:200] + "..." if len(doc) > 200 else doc)
            
    else:
        print("No valid text found to migrate.")

if __name__ == "__main__":
    main()
