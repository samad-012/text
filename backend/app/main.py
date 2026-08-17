import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.turn_based import router as turn_based_router
from app.routes.streaming import router as streaming_router

# Configure standard logging to output to stdout/stderr
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

app = FastAPI(title="Saffron ")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}


app.include_router(turn_based_router, prefix="/api")
app.include_router(streaming_router)