import os
import json
import sys
from neo4j import GraphDatabase

sys.stdout.reconfigure(encoding='utf-8')

# Connection settings from environment or defaults
NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "password")

# Categories classification helpers
STANDARD_EMOTIONS = ["우울", "슬픔", "불안", "분노", "상처", "당황", "기쁨"]

def load_tea_data_to_neo4j():
    dataset_path = r"c:\dev\project\SKN27-FINAL-4Team\storage\마시는_차_추천_데이터셋.json"
    if not os.path.exists(dataset_path):
        print(f"[!] Dataset file not found: {dataset_path}")
        return

    with open(dataset_path, 'r', encoding='utf-8') as f:
        teas = json.load(f)

    print(f"Connecting to Neo4j at {NEO4J_URI}...")
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    except Exception as e:
        print(f"[!] Failed to connect to Neo4j: {e}")
        return

    with driver.session() as session:
        # Clear existing Tea-related nodes and relationships to ensure idempotence
        print("Clearing existing Tea, Weather, Symptom nodes and relationships...")
        session.run("MATCH (t:Tea) DETACH DELETE t")
        session.run("MATCH (w:Weather) DETACH DELETE w")
        session.run("MATCH (s:Symptom) DETACH DELETE s")
        
        # We don't delete standard Emotion nodes completely, but detach relations to Teas
        session.run("MATCH (e:Emotion) MATCH (e)-[r:RECOMMENDED_FOR]-() DELETE r")

        # Create constraints if possible (optional)
        try:
            session.run("CREATE CONSTRAINT tea_name_uniq IF NOT EXISTS FOR (t:Tea) REQUIRE t.name IS UNIQUE")
            session.run("CREATE CONSTRAINT weather_uniq IF NOT EXISTS FOR (w:Weather) REQUIRE w.condition IS UNIQUE")
            session.run("CREATE CONSTRAINT symptom_uniq IF NOT EXISTS FOR (s:Symptom) REQUIRE s.name IS UNIQUE")
            session.run("CREATE CONSTRAINT emotion_uniq IF NOT EXISTS FOR (e:Emotion) REQUIRE e.name IS UNIQUE")
        except Exception as ce:
            # Constraints might fail depending on Neo4j version/edition; ignore.
            pass

        print(f"Loading {len(teas)} teas into Neo4j...")
        for idx, tea in enumerate(teas, 1):
            tea_name = tea["tea_name"]
            
            # Create Tea Node
            create_tea_query = """
            CREATE (t:Tea {
                id: $id,
                name: $name,
                english_name: $english_name,
                scientific_name: $scientific_name,
                efficacy: $efficacy,
                scientific_reason: $scientific_reason,
                tip: $tip,
                official_source: $official_source,
                reference_db: $reference_db,
                has_caffeine: $has_caffeine,
                allergy_triggers: $allergy_triggers
            })
            RETURN id(t) as node_id
            """
            res = session.run(create_tea_query, {
                "id": tea["id"],
                "name": tea_name,
                "english_name": tea.get("english_name", ""),
                "scientific_name": tea.get("scientific_name", ""),
                "efficacy": tea.get("efficacy", ""),
                "scientific_reason": tea.get("scientific_reason", ""),
                "tip": tea.get("tip", ""),
                "official_source": tea.get("official_source", ""),
                "reference_db": tea.get("reference_db", ""),
                "has_caffeine": tea.get("has_caffeine", False),
                "allergy_triggers": tea.get("allergy_triggers", [])
            })
            
            # Map recommended moods to Emotions or Symptoms
            for mood in tea.get("recommended_moods", []):
                if mood in STANDARD_EMOTIONS:
                    # Merge Emotion node
                    merge_emotion_query = """
                    MERGE (e:Emotion {name: $name})
                    ON CREATE SET e.code = $code
                    WITH e
                    MATCH (t:Tea {name: $tea_name})
                    MERGE (t)-[:RECOMMENDED_FOR]->(e)
                    """
                    # Assign standard codes
                    codes = {"우울": "E20", "슬픔": "E20", "불안": "E30", "분노": "E10", "상처": "E40", "당황": "E50", "기쁨": "E60"}
                    session.run(merge_emotion_query, {
                        "name": mood,
                        "code": codes.get(mood, "E00"),
                        "tea_name": tea_name
                    })
                else:
                    # Merge Symptom node
                    merge_symptom_query = """
                    MERGE (s:Symptom {name: $name})
                    WITH s
                    MATCH (t:Tea {name: $tea_name})
                    MERGE (t)-[:RECOMMENDED_FOR]->(s)
                    """
                    session.run(merge_symptom_query, {
                        "name": mood,
                        "tea_name": tea_name
                    })

            # Map recommended weathers
            for weather in tea.get("recommended_weathers", []):
                merge_weather_query = """
                MERGE (w:Weather {condition: $condition})
                WITH w
                MATCH (t:Tea {name: $tea_name})
                MERGE (t)-[:RECOMMENDED_FOR]->(w)
                """
                session.run(merge_weather_query, {
                    "condition": weather,
                    "tea_name": tea_name
                })
                
            print(f"  Loaded graph entities for tea: {tea_name}")

    driver.close()
    print("[+] Neo4j loading process completed successfully.")

if __name__ == "__main__":
    load_tea_data_to_neo4j()
