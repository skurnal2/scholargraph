from fastembed import TextEmbedding

model = TextEmbedding("BAAI/bge-small-en-v1.5")

sentences = [
    "We trained the model with the AdamW optimizer.",
    "Optimization used Adam with weight decay.",
    "The learning rate was 0.0001.",
    "The learning rate was 0.01.",
    "I had pizza for dinner.",
]
vectors = list(model.embed(sentences))


def cosine(a, b) -> float:
    return float(a @ b / ((a @ a) ** 0.5 * (b @ b) ** 0.5))


query = next(model.query_embed("Which optimizer was used?"))

for sentence, vec in zip(sentences, vectors):
    print(f"{cosine(query, vec):.3f}  {sentence}")

print()
print("Comparing the two learning rates to each other:")
print(f"{cosine(vectors[2], vectors[3]):.3f}  '0.0001' vs '0.01'")