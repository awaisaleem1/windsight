from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router


app = FastAPI(
    title="WindSight API",
    description=(
        "Day-ahead wind generation forecast intelligence "
        "using historical Elexon BMRS data."
    ),
    version="1.0.0",
)

# Development configuration.
# Restrict these origins to your actual frontend domains before deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
    ],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(
    router,
    prefix="/api",
    tags=["Wind Forecasting"],
)


@app.get("/")
async def root():
    return {
        "message": "Welcome to WindSight API",
        "docs": "/docs",
        "health": "/api/health",
    }
