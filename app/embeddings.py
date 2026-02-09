from sentence_transformers import SentenceTransformer

# Load model once (lazy loading might be better for startup time, but fine for now)
# "nomic-ai/nomic-embed-text-v1.5" needs trust_remote_code=True usually
# But let's stick to a standard one or check if nomic is available directly.
# The user asked for "nomic embedding from huggingface mobdel hub".
# "nomic-ai/nomic-embed-text-v1.5" is the model.

_model = None

def get_model():
    global _model
    if _model is None:
        print("Loading Nomic Embed Text v1.5 model...")
        _model = SentenceTransformer("nomic-ai/nomic-embed-text-v1.5", trust_remote_code=True)
    return _model

def generate_embedding(text: str):
    model = get_model()
    # Nomic v1.5 instruction prefix for documents
    return model.encode(f"search_document: {text}").tolist()

def generate_query_embedding(text: str):
    model = get_model()
    # Nomic v1.5 instruction prefix for queries
    return model.encode(f"search_query: {text}").tolist()
