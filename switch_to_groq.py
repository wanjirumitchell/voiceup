with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace API key and model
content = content.replace(
    "CLAUDE_API_KEY = 'sk-ant-your-key-here'",
    "GROQ_API_KEY = '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'"
)
content = content.replace(
    "CLAUDE_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')",
    "GROQ_API_KEY = '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'"
)
content = content.replace(
    "CLAUDE_MODEL   = 'claude-sonnet-4-20250514'",
    "GROQ_MODEL = 'llama-3.3-70b-versatile'"
)

# Replace the claude_api function
old_func = '''def claude_api(prompt, system='You are a helpful assistant.', max_tokens=800):
    """Call Claude API and return text response."""
    try:
        payload = json.dumps({
            'model': CLAUDE_MODEL,
            'max_tokens': max_tokens,
            'system': system,
            'messages': [{'role': 'user', 'content': prompt}]
        }).encode('utf-8')
        req = urllib.request.Request(
            'https://api.anthropic.com/v1/messages',
            data=payload,
            headers={
                'Content-Type': 'application/json',
                'x-api-key': CLAUDE_API_KEY,
                'anthropic-version': '2023-06-01'
            }
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            return data['content'][0]['text']
    except Exception as e:
        print(f'Claude API error: {e}')
        return None'''

new_func = '''def claude_api(prompt, system='You are a helpful assistant.', max_tokens=800):
    """Call Groq API and return text response."""
    try:
        payload = json.dumps({
            'model': GROQ_MODEL,
            'max_tokens': max_tokens,
            'messages': [
                {'role': 'system', 'content': system},
                {'role': 'user',   'content': prompt}
            ]
        }).encode('utf-8')
        req = urllib.request.Request(
            'https://api.groq.com/openai/v1/chat/completions',
            data=payload,
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {GROQ_API_KEY}'
            }
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            return data['choices'][0]['message']['content']
    except Exception as e:
        print(f'Groq API error: {e}')
        return None'''

content = content.replace(old_func, new_func)

# Replace chatbot API call
old_chatbot = '''        payload = json.dumps({
            'model': CLAUDE_MODEL,
            'max_tokens': 400,
            'system': """You are VoiceBot, a helpful AI assistant for VoiceUp — a school suggestion system.
Help students:
1. Decide whether to submit a suggestion
2. Improve their suggestion wording
3. Choose the right category and priority
4. Understand how the system works
5. Track their suggestions

Be friendly, concise and encouraging. If they seem to have a valid suggestion, encourage them to submit it.""",
            'messages': messages
        }).encode('utf-8')

        req = urllib.request.Request(
            'https://api.anthropic.com/v1/messages',
            data=payload,
            headers={
                'Content-Type': 'application/json',
                'x-api-key': CLAUDE_API_KEY,
                'anthropic-version': '2023-06-01'
            }
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            reply  = result['content'][0]['text']
            return jsonify({'reply': reply})'''

new_chatbot = '''        system_msg = """You are VoiceBot, a helpful AI assistant for VoiceUp — a school suggestion system.
Help students:
1. Decide whether to submit a suggestion
2. Improve their suggestion wording
3. Choose the right category and priority
4. Understand how the system works
5. Track their suggestions

Be friendly, concise and encouraging. If they seem to have a valid suggestion, encourage them to submit it."""

        all_messages = [{'role': 'system', 'content': system_msg}] + messages
        payload = json.dumps({
            'model': GROQ_MODEL,
            'max_tokens': 400,
            'messages': all_messages
        }).encode('utf-8')

        req = urllib.request.Request(
            'https://api.groq.com/openai/v1/chat/completions',
            data=payload,
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {GROQ_API_KEY}'
            }
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            reply  = result['choices'][0]['message']['content']
            return jsonify({'reply': reply})'''

content = content.replace(old_chatbot, new_chatbot)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Done! app.py now uses Groq AI.")
