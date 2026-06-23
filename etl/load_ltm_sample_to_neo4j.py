import os
import sys
from neo4j import GraphDatabase

sys.stdout.reconfigure(encoding='utf-8')

# Connection settings from environment or defaults
NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "password")

def load_ltm_sample_data():
    print(f"Connecting to Neo4j at {NEO4J_URI}...")
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    except Exception as e:
        print(f"[!] Failed to connect to Neo4j: {e}")
        return

    with driver.session() as session:
        print("Clearing existing LTM-related nodes and relationships...")
        # Clear LTM Nodes
        session.run("MATCH (u:User) DETACH DELETE u")
        session.run("MATCH (ev:LifeEvent) DETACH DELETE ev")
        session.run("MATCH (ct:CognitiveThought) DETACH DELETE ct")
        session.run("MATCH (em:EmotionState) DETACH DELETE em")
        session.run("MATCH (cb:CoreBelief) DETACH DELETE cb")

        # Create constraints if possible
        try:
            session.run("CREATE CONSTRAINT user_id_uniq IF NOT EXISTS FOR (u:User) REQUIRE u.user_id IS UNIQUE")
            session.run("CREATE CONSTRAINT event_id_uniq IF NOT EXISTS FOR (ev:LifeEvent) REQUIRE ev.event_id IS UNIQUE")
            session.run("CREATE CONSTRAINT thought_id_uniq IF NOT EXISTS FOR (ct:CognitiveThought) REQUIRE ct.thought_id IS UNIQUE")
            session.run("CREATE CONSTRAINT belief_id_uniq IF NOT EXISTS FOR (cb:CoreBelief) REQUIRE cb.belief_id IS UNIQUE")
        except Exception as ce:
            print(f"  [!] Constraint creation skipped or failed (check version/permissions): {ce}")

        print("Seeding sample Causal LTM Nodes and Relationships for mock User (ID: 1001)...")

        # 1. Create User Node
        session.run("CREATE (:User {user_id: 1001})")

        # 2. Create Core Belief Node
        session.run("""
        CREATE (:CoreBelief {
            belief_id: 'cb-01',
            belief_text: '나는 무능하고 가치 없는 존재이다',
            category: 'Worthlessness'
        })
        """)

        # Link User to Core Belief
        session.run("""
        MATCH (u:User {user_id: 1001}), (cb:CoreBelief {belief_id: 'cb-01'})
        CREATE (u)-[:HOLDS_BELIEF {confidence: 0.75}]->(cb)
        """)

        # 3. Create Event 1, Automatic Thought 1, Emotion 1
        # Event 1: Category "work", description "중요 발표에서 말을 더듬었다"
        # Thought 1: "나는 발표도 제대로 못하는 무능한 사람이다" (Overgeneralization)
        # Emotion 1: "Anxiety" (intensity: 8)
        session.run("""
        CREATE (ev:LifeEvent {
            event_id: 'ev-01',
            category: 'work',
            description: '중요 발표에서 말을 더듬었다',
            created_at: '2026-06-12T10:00:00Z'
        })
        CREATE (ct:CognitiveThought {
            thought_id: 'ct-01',
            thought_text: '나는 발표도 제대로 못하는 무능한 사람이다',
            cognitive_distortion: 'Overgeneralization'
        })
        CREATE (em:EmotionState {
            emotion_name: 'Anxiety',
            intensity: 8
        })
        WITH ev, ct, em
        MATCH (u:User {user_id: 1001}), (cb:CoreBelief {belief_id: 'cb-01'})
        CREATE (u)-[:EXPERIENCED {date: '2026-06-12'}]->(ev)
        CREATE (ev)-[:TRIGGERED_THOUGHT]->(ct)
        CREATE (ct)-[:CAUSED_EMOTION]->(em)
        CREATE (ct)-[:REINFORCES]->(cb)
        """)

        # 4. Create Event 2, Automatic Thought 2, Emotion 2
        # Event 2: Category "relationship", description "친구가 답장을 3시간 동안 하지 않았다"
        # Thought 2: "친구가 나를 싫어해서 답장을 안 하는 게 틀림없다" (Personalization)
        # Emotion 2: "Sadness" (intensity: 6)
        session.run("""
        CREATE (ev:LifeEvent {
            event_id: 'ev-02',
            category: 'relationship',
            description: '친구가 답장을 3시간 동안 하지 않았다',
            created_at: '2026-06-15T18:30:00Z'
        })
        CREATE (ct:CognitiveThought {
            thought_id: 'ct-02',
            thought_text: '친구가 나를 싫어해서 답장을 안 하는 게 틀림없다',
            cognitive_distortion: 'Personalization'
        })
        CREATE (em:EmotionState {
            emotion_name: 'Sadness',
            intensity: 6
        })
        WITH ev, ct, em
        MATCH (u:User {user_id: 1001})
        CREATE (u)-[:EXPERIENCED {date: '2026-06-15'}]->(ev)
        CREATE (ev)-[:TRIGGERED_THOUGHT]->(ct)
        CREATE (ct)-[:CAUSED_EMOTION]->(em)
        """)

        # 5. Create Event 3, Automatic Thought 3, Emotion 3
        # Event 3: Category "work", description "상사에게 기획안 피드백을 받았다"
        # Thought 3: "기획안 피드백을 받았으니 내 기획은 완전히 실패작이다" (All-or-Nothing)
        # Emotion 3: "Anxiety" (intensity: 7)
        session.run("""
        CREATE (ev:LifeEvent {
            event_id: 'ev-03',
            category: 'work',
            description: '상사에게 기획안 피드백을 받았다',
            created_at: '2026-06-18T14:15:00Z'
        })
        CREATE (ct:CognitiveThought {
            thought_id: 'ct-03',
            thought_text: '기획안 피드백을 받았으니 내 기획은 완전히 실패작이다',
            cognitive_distortion: 'All-or-Nothing'
        })
        CREATE (em:EmotionState {
            emotion_name: 'Anxiety',
            intensity: 7
        })
        WITH ev, ct, em
        MATCH (u:User {user_id: 1001}), (cb:CoreBelief {belief_id: 'cb-01'})
        CREATE (u)-[:EXPERIENCED {date: '2026-06-18'}]->(ev)
        CREATE (ev)-[:TRIGGERED_THOUGHT]->(ct)
        CREATE (ct)-[:CAUSED_EMOTION]->(em)
        CREATE (ct)-[:REINFORCES]->(cb)
        """)

        print("[+] Seeded mock LTM database for User: 1001.")

        # Print simple validation verification query
        print("\nVerifying seeded LTM paths in Neo4j...")
        result = session.run("""
        MATCH (u:User {user_id: 1001})-[:EXPERIENCED]->(ev:LifeEvent)-[:TRIGGERED_THOUGHT]->(th:CognitiveThought)-[:CAUSED_EMOTION]->(em:EmotionState)
        RETURN ev.category as category, ev.description as situation, th.thought_text as thought, th.cognitive_distortion as distortion, em.emotion_name as emotion, em.intensity as intensity
        """)
        for record in result:
            print(f"- [{record['category']}] Situation: {record['situation']}")
            print(f"  Thought: '{record['thought']}' ({record['distortion']})")
            print(f"  Emotion: {record['emotion']} (intensity: {record['intensity']})")

    driver.close()
    print("\n[✔] Causal LTM Seed process completed successfully.")

if __name__ == "__main__":
    load_ltm_sample_data()
