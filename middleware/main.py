from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from api.routes import hl7_endpoint
from utils.logging_config import logger
from api.routes import patients, health

app = FastAPI(
    title=settings.API_TITLE,
    description=settings.API_DESCRIPTION,
    version=settings.API_VERSION,
    docs_url="/docs",
    redoc_url=None
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # en PRO habería que limitar
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# routers
app.include_router(health.router)
app.include_router(patients.router) # uso pruebas, borrable
app.include_router(hl7_endpoint.router)

# raíz
@app.get("/")
async def root():
    return {
        "message": "Middleware FHIR para interoperabilidad sanitaria",
        "version": settings.API_VERSION,
        "docs": "/docs",
        "health": "/health"
    }

# para logs de inicio / apagado
async def startup_event():
    logger.info(f"Iniciando {settings.API_TITLE} v{settings.API_VERSION}")
    logger.info(f"FHIR Server URL: {settings.FHIR_SERVER_URL}")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Apagando middleware FHIR")

# arranque en local
if __name__ == "__main__":
    import uvicorn
    from core.config import settings
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.API_PORT,
        reload=True
    )