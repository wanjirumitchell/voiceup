import urllib.request
import json

GEMINI_API_KEY = 'AIzaSyCDtAE2AHRHzuVaKgmMTdK7CAxNpMHeUHk'
GEMINI_MODEL = 'gemini-2.5-flash'

url = f'https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}'
payload = json.dumps({'contents': [{'parts': [{'text': 'say hello'}]}]}).encode()
req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})

try:
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode())
        print("SUCCESS:", data['candidates'][0]['content']['parts'][0]['text'])
except Exception as e:
    print(f"ERROR: {e}")