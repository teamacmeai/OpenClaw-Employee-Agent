from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import require_device
from app.services.auth_service import DeviceIdentity

router = APIRouter(prefix="/v1/device", tags=["device"])


class DeviceWhoamiResponse(BaseModel):
    employee_id: UUID
    workstation_id: UUID


@router.get("/whoami", response_model=DeviceWhoamiResponse)
def whoami(
    device: DeviceIdentity = Depends(require_device),
) -> DeviceWhoamiResponse:
    """Return identity of the authenticated workstation/device."""
    return DeviceWhoamiResponse(
        employee_id=device.employee_id,
        workstation_id=device.workstation_id,
    )
