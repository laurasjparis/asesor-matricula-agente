import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(base_url="https://integrate.api.nvidia.com/v1",
                api_key=os.getenv("NVIDIA_API_KEY"))
r = client.chat.completions.create(
    model="nvidia/nemotron-3.5-super-vl-120b-a12b",
    messages=[{"role": "user", "content": "Di hola"}],
)
print(r.choices[0].message.content)