from fastapi import FastAPI


app = FastAPI(
    title="SentinelAgent",
    description="AI-Powered Security Operations Platform",
    version="0.1.0"
)


@app.get("/")
def root():
    return {
        "name": "SentinelAgent",
        "version": "0.1.0",
        "status": "running"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }