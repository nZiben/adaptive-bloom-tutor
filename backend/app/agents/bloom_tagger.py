from ..llm.mistral_client import client

SYSTEM = "You are Bloom-Tagger. Map an utterance to a Bloom level. Answer with one token: remember/understand/apply/analyze/evaluate/create."

def tag_bloom(text: str) -> str:
    resp = client.chat(
        [{"role":"system","content":SYSTEM},
         {"role":"user","content":f"Utterance:\n{text}\nLevel? One token."}],
        temperature=0.0
    ).strip().lower()
    for k in ["remember","understand","apply","analyze","evaluate","create"]:
        if k in resp:
            return k
    return "understand"
