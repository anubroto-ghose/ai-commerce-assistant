from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.chat import router as chat_router
from app.routes.search import router as search_router
from app.routes.system import router as system_router
from dotenv import load_dotenv

load_dotenv()


app = FastAPI(title="GenAI E-Commerce Assistant", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


app.include_router(search_router)
app.include_router(chat_router)
app.include_router(system_router)
