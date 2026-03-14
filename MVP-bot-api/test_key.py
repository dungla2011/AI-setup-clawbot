import os
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()
key = os.getenv('ANTHROPIC_API_KEY')
print(f'Key: {key[:30]}...')

c = Anthropic(api_key=key)

models = [
    'claude-sonnet-4-20250514',
    'claude-3-7-sonnet-20250219',
    'claude-3-5-sonnet-latest',
    'claude-3-haiku-20240307',
]

for m in models:
    try:
        print(f'Trying: {m}...')
        r = c.messages.create(model=m, max_tokens=10, messages=[{'role':'user','content':'hi'}])
        print(f'  OK: {r.content[0].text}')
        break
    except Exception as e:
        print(f'  FAIL: {str(e)[:100]}')
