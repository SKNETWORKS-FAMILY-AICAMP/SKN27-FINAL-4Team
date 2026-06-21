import os
import re
import sys
import json
import psycopg2
from psycopg2.extras import execute_values
from neo4j import GraphDatabase

sys.stdout.reconfigure(encoding='utf-8')

# DB Connection settings from environment or defaults
NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "password")

PG_HOST = os.environ.get("PG_HOST", "localhost")
PG_PORT = os.environ.get("PG_PORT", "5432")
PG_DB = os.environ.get("PG_DB", "wellness_db")
PG_USER = os.environ.get("PG_USER", "postgres")
PG_PASSWORD = os.environ.get("PG_PASSWORD", "password")

THEORIES_DIR = r"c:\Users\Playdata\Documents\Obsidian Vault\AOS-project\02-도메인리서치\심리이론"

def parse_markdown_to_chunks(file_path):
    """
    Parses a markdown theory file into logical chunks split by headings (##, ###).
    Returns a list of dicts with title, heading, and content.
    """
    if not os.path.exists(file_path):
        return []
        
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
        
    file_name = os.path.basename(file_path)
    title = ""
    # Extract main title (# Title)
    for line in lines:
        if line.startswith("# "):
            title = line.replace("# ", "").strip()
            break
    if not title:
        title = file_name.replace(".md", "")
        
    # Extract tags or other metadata if present
    tags = []
    in_frontmatter = False
    for line in lines:
        if line.strip() == "---":
            in_frontmatter = not in_frontmatter
            continue
        if in_frontmatter and ":" in line:
            parts = line.split(":", 1)
            key = parts[0].strip().lower()
            val = parts[1].strip()
            if key == "tags":
                # Clean tag formats like [tag1, tag2] or just tags
                val = val.replace("[", "").replace("]", "")
                tags = [t.strip() for t in val.split(",") if t.strip()]

    chunks = []
    current_heading = ""
    current_chunk_lines = []
    
    for line in lines:
        # Skip frontmatter lines
        if line.strip() == "---" or in_frontmatter:
            continue
            
        # Detect headings
        if line.startswith("## ") or line.startswith("### "):
            if current_chunk_lines:
                content = "".join(current_chunk_lines).strip()
                if content:
                    chunks.append({
                        "file_name": file_name,
                        "title": title,
                        "heading": current_heading,
                        "content": content,
                        "tags": tags
                    })
            current_heading = line.replace("#", "").strip()
            current_chunk_lines = [line]
        else:
            # Skip Title lines to avoid duplicate title indexing
            if line.startswith("# "):
                continue
            current_chunk_lines.append(line)
            
    # Append the last chunk
    if current_chunk_lines:
        content = "".join(current_chunk_lines).strip()
        if content:
            chunks.append({
                "file_name": file_name,
                "title": title,
                "heading": current_heading,
                "content": content,
                "tags": tags
            })
            
    return chunks

def get_openai_embedding(text, model="text-embedding-3-small"):
    """
    Generates a 1536-dimension vector embedding using OpenAI API.
    If OPENAI_API_KEY is not set, returns a mock 1536-dimensional float vector.
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        # Return mock zero vector (useful for testing pipeline without API charges)
        return [0.0] * 1536
        
    try:
        import openai
        client = openai.OpenAI(api_key=api_key)
        response = client.embeddings.create(
            input=[text],
            model=model
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"  [!] OpenAI embedding error: {e}")
        return [0.0] * 1536

def load_theories_to_postgres(all_chunks):
    """
    Loads theory chunks into PostgreSQL with pgvector extension.
    """
    print(f"\n[PostgreSQL Ingestion] Loading {len(all_chunks)} chunks to Postgres...")
    try:
        conn = psycopg2.connect(
            host=PG_HOST,
            port=PG_PORT,
            database=PG_DB,
            user=PG_USER,
            password=PG_PASSWORD
        )
        cur = conn.cursor()
    except Exception as e:
        print(f"  [!] Failed to connect to PostgreSQL: {e}")
        print("  [!] Skipping PostgreSQL loading.")
        return

    # Enable pgvector if not enabled
    try:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        conn.commit()
    except Exception as e:
        print(f"  [!] Failed to enable pgvector extension: {e}. Check if pgvector is installed.")
        conn.rollback()

    # Create table for chunks
    create_table_query = """
    CREATE TABLE IF NOT EXISTS psychology_theory_chunks (
        id SERIAL PRIMARY KEY,
        file_name VARCHAR(100) NOT NULL,
        title VARCHAR(200) NOT NULL,
        section_heading VARCHAR(200),
        content TEXT NOT NULL,
        embedding VECTOR(1536), -- Dimension for text-embedding-3-small
        tags VARCHAR(100)[]
    );
    """
    cur.execute(create_table_query)
    conn.commit()
    
    # Clear existing theories
    cur.execute("TRUNCATE TABLE psychology_theory_chunks;")
    conn.commit()
    
    # Ingest chunks
    records = []
    print("Generating embeddings and preparing records for Postgres...")
    for idx, chunk in enumerate(all_chunks, 1):
        embedding = get_openai_embedding(chunk["content"])
        records.append((
            chunk["file_name"],
            chunk["title"],
            chunk["heading"],
            chunk["content"],
            embedding,
            chunk["tags"]
        ))
        if idx % 20 == 0 or idx == len(all_chunks):
            print(f"  Processed {idx}/{len(all_chunks)} embeddings...")
            
    insert_query = """
    INSERT INTO psychology_theory_chunks (file_name, title, section_heading, content, embedding, tags)
    VALUES %s;
    """
    try:
        execute_values(cur, insert_query, records)
        conn.commit()
        # Create HNSW index for vector similarity search
        cur.execute("CREATE INDEX IF NOT EXISTS psychology_theory_hnsw_idx ON psychology_theory_chunks USING hnsw (embedding vector_cosine_ops);")
        conn.commit()
        print(f"[+] Successfully loaded {len(all_chunks)} chunks to PostgreSQL!")
    except Exception as e:
        print(f"  [!] Failed to insert records into Postgres: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

def load_theories_to_neo4j(all_chunks):
    """
    Loads theory chunks into Neo4j Graph Database and sets up Vector Search.
    Nodes will represent (:TheoryChunk) with attributes, linked to main (:Theory) nodes.
    """
    print(f"\n[Neo4j Ingestion] Loading {len(all_chunks)} chunks to Neo4j...")
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    except Exception as e:
        print(f"  [!] Failed to connect to Neo4j: {e}")
        print("  [!] Skipping Neo4j loading.")
        return

    with driver.session() as session:
        # Clear existing Theory nodes
        session.run("MATCH (t:TheoryChunk) DETACH DELETE t")
        session.run("MATCH (t:Theory) DETACH DELETE t")
        
        # Set up constraints
        try:
            session.run("CREATE CONSTRAINT theory_title_uniq IF NOT EXISTS FOR (t:Theory) REQUIRE t.title IS UNIQUE")
        except Exception:
            pass

        print("Generating embeddings and loading nodes to Neo4j...")
        for idx, chunk in enumerate(all_chunks, 1):
            embedding = get_openai_embedding(chunk["content"])
            
            # Create/Merge main Theory node, then create TheoryChunk and relate them
            cypher = """
            MERGE (parent:Theory {title: $title, file_name: $file_name})
            CREATE (c:TheoryChunk {
                heading: $heading,
                content: $content,
                embedding: $embedding,
                tags: $tags
            })
            CREATE (parent)-[:HAS_CHUNK]->(c)
            """
            session.run(cypher, {
                "title": chunk["title"],
                "file_name": chunk["file_name"],
                "heading": chunk["heading"],
                "content": chunk["content"],
                "embedding": embedding,
                "tags": chunk["tags"]
            })
            
            if idx % 20 == 0 or idx == len(all_chunks):
                print(f"  Loaded {idx}/{len(all_chunks)} nodes into Neo4j...")
                
        # Setup vector index in Neo4j (for Neo4j vector search)
        try:
            # Drop index if exists, then create new index for 1536 dim
            session.run("DROP INDEX theory_vector_index IF EXISTS")
            session.run("""
            CREATE VECTOR INDEX theory_vector_index IF NOT EXISTS
            FOR (c:TheoryChunk) ON (c.embedding)
            OPTIONS {
              indexConfig: {
                `vector.dimensions`: 1536,
                `vector.similarity_function`: 'cosine'
              }
            }
            """)
            print("[+] Neo4j vector index 'theory_vector_index' created successfully!")
        except Exception as ve:
            print(f"  [!] Could not create vector index in Neo4j (check version support): {ve}")
            
    driver.close()
    print("[+] Neo4j loading process completed.")

def main():
    if not os.path.exists(THEORIES_DIR):
        print(f"[!] Theories directory not found: {THEORIES_DIR}")
        print("Please check your Obsidian Vault path.")
        return
        
    print(f"Scanning directory: {THEORIES_DIR}...")
    files = [f for f in os.listdir(THEORIES_DIR) if f.endswith(".md")]
    print(f"Found {len(files)} markdown files.")
    
    all_chunks = []
    for f in files:
        file_path = os.path.join(THEORIES_DIR, f)
        chunks = parse_markdown_to_chunks(file_path)
        all_chunks.extend(chunks)
        
    print(f"Parsed total {len(all_chunks)} chunks from {len(files)} files.")
    
    # Load to targets
    load_theories_to_postgres(all_chunks)
    load_theories_to_neo4j(all_chunks)
    
    print("\n[✔] ETL Pipeline Completed successfully!")

if __name__ == "__main__":
    main()
