"""Load synthetic Medigraph demo CSVs into Neo4j Aura.
All records and medical relationships in this dataset are illustrative placeholders,
not clinically verified guidance. Use a dedicated database for this demo.
"""
import csv, os, sys
from pathlib import Path
from neo4j import GraphDatabase

URI = os.environ.get("NEO4J_URI")
USER = os.environ.get("NEO4J_USERNAME")
PASSWORD = os.environ.get("NEO4J_PASSWORD")
DATABASE = os.environ.get("NEO4J_DATABASE", "neo4j")
DATA_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "data"
if not URI or not USER or not PASSWORD:
    raise SystemExit("Missing Neo4j credentials. Run run.bat and enter your Aura URI, username, and password.")

def rows(name):
    with open(DATA_DIR / name, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

CONSTRAINTS = [
 "CREATE CONSTRAINT drug_id IF NOT EXISTS FOR (n:Drug) REQUIRE n.id IS UNIQUE",
 "CREATE CONSTRAINT disease_id IF NOT EXISTS FOR (n:Disease) REQUIRE n.id IS UNIQUE",
 "CREATE CONSTRAINT side_effect_id IF NOT EXISTS FOR (n:SideEffect) REQUIRE n.id IS UNIQUE",
 "CREATE CONSTRAINT patient_id IF NOT EXISTS FOR (n:Patient) REQUIRE n.id IS UNIQUE",
]
LOADS = [
 ("diseases.csv", "UNWIND $rows AS r MERGE (n:Disease {id:r.id}) SET n.name=r.name, n.category=r.category"),
 ("drugs.csv", "UNWIND $rows AS r MERGE (n:Drug {id:r.id}) SET n.name=r.name, n.drug_class=r.drug_class"),
 ("side_effects.csv", "UNWIND $rows AS r MERGE (n:SideEffect {id:r.id}) SET n.name=r.name"),
 ("patients.csv", "UNWIND $rows AS r MERGE (n:Patient {id:r.id}) SET n.name=r.name, n.age=toInteger(r.age), n.sex=r.sex"),
 ("treats.csv", "UNWIND $rows AS r MATCH (d:Drug {id:r.drug_id}), (x:Disease {id:r.disease_id}) MERGE (d)-[:TREATS]->(x)"),
 ("contraindications.csv", "UNWIND $rows AS r MATCH (d:Drug {id:r.drug_id}), (x:Disease {id:r.disease_id}) MERGE (d)-[c:CONTRAINDICATED_IN]->(x) SET c.severity=r.severity, c.reason=r.reason"),
 ("interactions.csv", "UNWIND $rows AS r MATCH (a:Drug {id:r.drug_a}), (b:Drug {id:r.drug_b}) MERGE (a)-[i:INTERACTS_WITH]->(b) SET i.severity=r.severity, i.description=r.description"),
 ("causes.csv", "UNWIND $rows AS r MATCH (d:Drug {id:r.drug_id}), (s:SideEffect {id:r.side_effect_id}) MERGE (d)-[c:CAUSES]->(s) SET c.frequency=r.frequency"),
 ("patient_conditions.csv", "UNWIND $rows AS r MATCH (p:Patient {id:r.patient_id}), (x:Disease {id:r.disease_id}) MERGE (p)-[:HAS_CONDITION]->(x)"),
 ("patient_drugs.csv", "UNWIND $rows AS r MATCH (p:Patient {id:r.patient_id}), (d:Drug {id:r.drug_id}) MERGE (p)-[:TAKES]->(d)"),
]
def main():
    print(f"Connecting to {URI} using database '{DATABASE}'...")
    driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))
    try:
        driver.verify_connectivity()
        with driver.session(database=DATABASE) as session:
            for q in CONSTRAINTS: session.run(q).consume()
            for filename, query in LOADS:
                records = rows(filename)
                session.run(query, rows=records).consume()
                print(f"Loaded {len(records):>3} rows from {filename}")
            print("\nNode counts:")
            for rec in session.run("MATCH (n) RETURN labels(n)[0] AS label, count(*) AS c ORDER BY label"):
                print(f"  {rec['label']:<14} {rec['c']}")
            print("\nRelationship counts:")
            for rec in session.run("MATCH ()-[r]->() RETURN type(r) AS t, count(*) AS c ORDER BY t"):
                print(f"  {rec['t']:<22} {rec['c']}")
        print("\nSUCCESS: synthetic demo data loaded.")
    finally:
        driver.close()
if __name__ == '__main__': main()
