from fastapi import FastAPI


app = FastAPI(title="AI Call QA & Sales Coach API")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
