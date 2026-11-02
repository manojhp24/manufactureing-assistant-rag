from rag.embeddings.embedding_model import get_embedding_model

embeddings = get_embedding_model()

text = """
HP-200 is a hydraulic forming press.
Normal hydraulic pressure is 120 to 140 bar.
"""


# Generate embedding
vector = embeddings.embed_query(text)


print("Embedding generated successfully")

print("Vector dimensions:", len(vector))

print("First 10 values:", vector[:10])
