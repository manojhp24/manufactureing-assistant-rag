import time

from rag.generation.llm import get_llm

print("Initializing Gemini...", flush=True)

llm = get_llm()

print("Sending test request...", flush=True)

start = time.time()

response = llm.invoke("Reply with only: Gemini connection successful")

print("Response:", response.content)
print("Time taken:", round(time.time() - start, 2), "seconds")
