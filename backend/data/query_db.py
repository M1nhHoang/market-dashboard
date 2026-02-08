import sqlite3
import json

conn = sqlite3.connect(r'c:\Users\minhhoang\Desktop\market-intelligence\backend\data\market.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# List tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cursor.fetchall()]
print("Tables:", tables)

# Check causal_analyses
cursor.execute("SELECT COUNT(*) FROM causal_analyses")
count = cursor.fetchone()[0]
print(f"\ncausal_analyses count: {count}")

if count > 0:
    cursor.execute("SELECT id, event_id, reasoning, confidence, chain_steps, needs_investigation FROM causal_analyses LIMIT 3")
    for row in cursor.fetchall():
        print("\n" + "="*80)
        print(f"ID: {row['id']}")
        print(f"Event ID: {row['event_id']}")
        print(f"Confidence: {row['confidence']}")
        print(f"Reasoning: {row['reasoning']}")
        print(f"Chain Steps: {row['chain_steps']}")
        print(f"Needs Investigation: {row['needs_investigation']}")

# Check events content
print("\n\n" + "="*80)
print("EVENTS DATA:")
cursor.execute("SELECT id, title, summary, content FROM events LIMIT 3")
for row in cursor.fetchall():
    print("\n" + "-"*40)
    print(f"ID: {row['id']}")
    print(f"Title: {row['title']}")
    print(f"Summary: {row['summary']}")
    print(f"Content: {row['content'][:200] if row['content'] else 'None'}...")

conn.close()
