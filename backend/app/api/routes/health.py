from fastapi import APIRouter

router = APIRouter(tags=["Health"])


@router.get("/health", summary="Liveness check", description="Returns 200 when the API is up.")
def health() -> dict[str, str]:
    return {"status": "ok"}