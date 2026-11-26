from typing import Annotated, List
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from app.api.deps import require_device
from app.db.pool import connection
from app.schemas.events import IngestBatch
from app.services.auth_service import DeviceIdentity
from app.services.ingest_service import IngestService

router = APIRouter(prefix="/v1", tags=["ingest"])


class RejectionItemModel(BaseModel):
    index: int
    reason: str


class IngestResponse(BaseModel):
    batch_id: str
    accepted: int
    rejected: List[RejectionItemModel] = Field(default_factory=list)
    duplicate: bool


@router.post(
    "/ingest",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=IngestResponse,
)
def ingest_batch(
    batch: IngestBatch,
    identity: Annotated[DeviceIdentity, Depends(require_device)],
) -> IngestResponse:
    with connection() as conn:
        service = IngestService(conn)
        result = service.ingest(identity, batch)

    # Capped at 20 rejection reasons
    capped_rejections = [
        RejectionItemModel(index=r.index, reason=r.reason)
        for r in result.rejected[:20]
    ]

    return IngestResponse(
        batch_id=result.batch_id,
        accepted=result.accepted,
        rejected=capped_rejections,
        duplicate=result.duplicate,
    )
