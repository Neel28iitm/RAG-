
import sqlite3
import pandas as pd
import json
import os

# Set DB path relative to script
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "rag_app.db")

def view_data():
    if not os.path.exists(DB_PATH):
        print(f"❌ Database not found at: {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    try:
        print(f"📂 Connected to Database: {DB_PATH}\n")
        
        # Get Tables
        tables = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table';", conn)
        print(f"📋 Tables found: {tables['name'].tolist()}\n")

        # View Chat Sessions
        if 'chat_sessions' in tables['name'].values:
            print("--- Table: chat_sessions (Latest 5) ---")
            df = pd.read_sql("SELECT id, title, created_at, messages FROM chat_sessions ORDER BY created_at DESC LIMIT 5", conn)
            
            # Formatting
            pd.set_option('display.max_columns', None)
            pd.set_option('display.width', 1000)
            
            for index, row in df.iterrows():
                msgs = json.loads(row['messages'])
                print(f"🔹 ID: {row['id']}")
                print(f"   Created: {row['created_at']}")
                print(f"   Title: {row['title']}")
                print(f"   Message Count: {len(msgs)}")
                print("-" * 50)
        else:
            print("⚠️ 'chat_sessions' table not found.")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    view_data()
