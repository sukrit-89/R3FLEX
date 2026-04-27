"""
Supplier registration router.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.supplier import SupplierCreate, SupplierList, SupplierRead, SupplierUpdate
from app.services.supplier_svc import SupplierService

router = APIRouter()


@router.get("", response_model=SupplierList)
async def list_suppliers(
    company_id: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> SupplierList:
    items, total = await SupplierService.list_suppliers(db, company_id)
    return SupplierList(items=[SupplierRead.model_validate(item) for item in items], total=total)


@router.post("", response_model=SupplierRead, status_code=201)
async def create_supplier(
    payload: SupplierCreate,
    db: AsyncSession = Depends(get_db),
) -> SupplierRead:
    supplier = await SupplierService.create(payload, db)
    return SupplierRead.model_validate(supplier)


@router.patch("/{supplier_id}", response_model=SupplierRead)
async def update_supplier(
    supplier_id: str,
    payload: SupplierUpdate,
    db: AsyncSession = Depends(get_db),
) -> SupplierRead:
    try:
        uid = uuid.UUID(supplier_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format.")
    supplier = await SupplierService.update(uid, payload, db)
    if not supplier:
        raise HTTPException(status_code=404, detail=f"Supplier {supplier_id} not found.")
    return SupplierRead.model_validate(supplier)
