// SAMPLE CODE FOR DEMO - contains INTENTIONAL vulnerabilities for the scanner to find.
// The API_KEY below is a FAKE placeholder (Stripe test key format) and is never used.
export const sampleCode = `import sqlite3

conn = sqlite3.connect("app.db")
cur = conn.cursor()

username = input("username: ")
cur.execute(f"SELECT * FROM users WHERE username = '{username}'")

API_KEY = "sk_live_4eC39HqLyjWDarjtT1zdp7dc"

def fetch_users(ids):
    results = ""
    for i in ids:
        results += str(i)
        cur.execute("SELECT * FROM orders WHERE user_id = ?", i)
    return results

def process(items=[]):
    items.append("x")
    return items

try:
    value = int(input("n: "))
except Exception:
    pass
`