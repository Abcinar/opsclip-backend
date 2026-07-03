import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api import router
from db.database import Base, engine

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Lumina Clip API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://opsclip.com", "https://www.opsclip.com", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")

@app.get("/")
def root():
    return {"app": "Lumina Clip API", "version": "1.0.0", "status": "ok"}

@app.get("/health")
def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
