with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add Gemini config after the imports section
old = '''import json
import urllib.request
import urllib.error

def claude_api'''

new = '''import json
import urllib.request
import urllib.error

GEMINI_API_KEY = 'YOUR_GEMINI_KEY_HERE'
GEMINI_MODEL   = 'gemini-1.5-flash'

def claude_api'''

content = content.replace(old, new)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Done! Now open notepad app.py and replace YOUR_GEMINI_KEY_HERE with your actual key.")
