import asyncio
import logging
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from dependency_injector.wiring import Provide, inject
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.containers.container import Container
from app.core.exception_handlers import register_exception_handlers
from app.interfaces.service.health_service import IHealthService
from app.interfaces.utilities.response_builder import IResponseBuilder
from app.routers import case_router, evaluation_router, sample_router
from app.schemas.api_response import ApiResponse
from app.schemas.health import LivenessStatus, ReadinessStatus

container = Container()
settings = container.settings()

logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    logger.info("Starting %s (%s)", settings.app_name, settings.environment)
    # Workflow state is saved here after every step, so it must be ready before any case.
    await container.checkpoint_store().open()
    yield
    # Runs still going are stopped; their saved state lets them be retried later.
    await container.utilities.task_runner().cancel_all()
    await container.checkpoint_store().close()
    await container.clients.http_client().aclose()
    await container.database().dispose()
    logger.info("Stopped %s", settings.app_name)


app = FastAPI(
    title=settings.app_name,
    description="Prototype on synthetic data. Not for real patient information.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_allowed_origins),
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app, container.utilities.response_builder())


@app.get("/health/live", tags=["health"])
@inject
async def live(
    health_service: IHealthService = Depends(Provide[Container.services.health_service]),
    response_builder: IResponseBuilder = Depends(Provide[Container.utilities.response_builder]),
) -> ApiResponse[LivenessStatus]:
    return response_builder.success(health_service.liveness())


@app.get("/health/ready", tags=["health"])
@inject
async def ready(
    health_service: IHealthService = Depends(Provide[Container.services.health_service]),
    response_builder: IResponseBuilder = Depends(Provide[Container.utilities.response_builder]),
) -> ApiResponse[ReadinessStatus]:
    return response_builder.success(await health_service.readiness())


app.include_router(case_router.router)
app.include_router(sample_router.router)
app.include_router(evaluation_router.router)

container.wire(modules=[__name__, case_router, sample_router, evaluation_router])


if __name__ == "__main__":
    server = uvicorn.Server(
        uvicorn.Config(app, host=settings.host, port=settings.port, log_config=None)
    )
    # The PostgreSQL driver cannot run on Windows' default event loop.
    asyncio.run(
        server.serve(),
        loop_factory=asyncio.SelectorEventLoop if sys.platform == "win32" else None,
    )
