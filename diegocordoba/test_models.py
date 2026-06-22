import os
from anthropic import Anthropic

client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

models = [
    "claude-3-5-sonnet-20240620",
    "claude-3-5-sonnet-20241022",
    "claude-3-5-sonnet-latest",
    "claude-3-5-opus-latest",
    "claude-3-opus-20240229"
]

for m in models:
    try:
        response = client.messages.create(
            model=m,
            max_tokens=10,
            messages=[{"role": "user", "content": "hello"}]
        )
        print(f"{m} -> SUCCESS")
    except Exception as e:
        print(f"{m} -> FAILED: {e}")
