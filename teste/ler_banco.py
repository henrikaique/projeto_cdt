import sqlite3

conn = sqlite3.connect("chat_memory.db")
cursor = conn.cursor()

print("=== MEMÓRIAS SALVAS ===")
cursor.execute("SELECT * FROM memorias")
for row in cursor.fetchall():
    print(row)

print("\n=== HISTÓRICO DE MENSAGENS ===")
cursor.execute("SELECT session_id, sender, content, timestamp FROM mensagens")
for row in cursor.fetchall():
    print(f"[{row[3]}] ({row[0]}) {row[1]}: {row[2]}")

conn.close()