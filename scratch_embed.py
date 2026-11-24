from sentence_transformers import SentenceTransformer

for name in ["BAAI/bge-small-en-v1.5", "sentence-transformers/all-MiniLM-L6-v2"]:
    model = SentenceTransformer(name)
    vectors = model.encode(
        ["Database connection pool exhausted",
         "Payment cannot get a database connection",
         "Card declined by issuer: insufficient funds"],
        normalize_embeddings=True,
    )
    print(name, "-> vector size:", vectors.shape[1])
    print("  pool vs 'cannot get connection':", round(float(vectors[0] @ vectors[1]), 3))
    print("  pool vs 'card declined':        ", round(float(vectors[0] @ vectors[2]), 3))