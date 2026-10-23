import os

from openai import OpenAI

client = OpenAI(
  base_url=os.environ.get("MODEL_BASE_URL", "https://integrate.api.nvidia.com/v1"),
  api_key=os.environ.get("MODEL_API_KEY", ""),
)

if not client.api_key:
  raise SystemExit("Set MODEL_API_KEY in the environment (see local-secrets.bat) before running this.")

completion = client.chat.completions.create(
  model="openai/gpt-oss-20b",
  messages=[{"role":"user","content":"Which number is larger, 9.11 or 9.8?"}],
  temperature=1,
  top_p=1,
  max_tokens=4096,
  stream=False
)

reasoning = getattr(completion.choices[0].message, "reasoning_content", None)
if reasoning:
  print(reasoning)
print(completion.choices[0].message.content)
