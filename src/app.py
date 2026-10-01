from fastapi import FastAPI
from fastapi.responses import JSONResponse
from src.adapter.rest.server_router import router as financial_fleet_agent_router

def create_app() -> FastAPI:
    app = FastAPI(
      title="Financial Analyst Agent API",
      description="API para interactuar con el asistente financiero.",
      version="1.0.0",
    )

    app.include_router(financial_fleet_agent_router)

    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        return JSONResponse(
            status_code=500,
            content={"message": "An unexpected error occurred."},
        )

    @app.get("/health", tags=["Health"])
    async def health_check():
        return {"status": "healthy"}

    @app.get("/health/liveness", tags=["Health"])
    async def liveness_check():
        return {"status": "alive"}

    @app.get("/health/readiness", tags=["Health"])
    async def readiness_check():
        return {"status": "ready"}

    return app

app = create_app()