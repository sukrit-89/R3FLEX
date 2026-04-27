from __future__ import annotations

"""
Supplier service.
"""
import uuid
from collections.abc import Iterable


from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.supplier import Supplier
from app.schemas.supplier import SupplierCreate, SupplierUpdate

settings = get_settings()


class SupplierService:
    @staticmethod
    async def create(payload: SupplierCreate, db: AsyncSession) -> Supplier:
        supplier = Supplier(
            company_id=payload.company_id or settings.company_id,
            supplier_code=payload.supplier_code,
            legal_name=payload.legal_name,
            business_type=payload.business_type,
            registration_number=payload.registration_number,
            country=payload.country,
            city=payload.city,
            address=payload.address,
            contact_name=payload.contact_name,
            contact_email=payload.contact_email,
            contact_phone=payload.contact_phone,
            status=payload.status,
            material_profiles=payload.material_profiles,
            facilities=payload.facilities,
            lane_preferences=payload.lane_preferences,
            notes=payload.notes,
        )
        db.add(supplier)
        await db.flush()
        return supplier

    @staticmethod
    async def list_suppliers(db: AsyncSession, company_id: str | None = None) -> tuple[list[Supplier], int]:
        scope_company = company_id or settings.company_id
        result = await db.execute(
            select(Supplier)
            .where(Supplier.company_id == scope_company)
            .order_by(Supplier.legal_name.asc())
        )
        count_result = await db.execute(
            select(func.count(Supplier.id)).where(Supplier.company_id == scope_company)
        )
        return list(result.scalars().all()), count_result.scalar() or 0

    @staticmethod
    async def get(supplier_id: uuid.UUID, db: AsyncSession) -> Supplier | None:
        result = await db.execute(select(Supplier).where(Supplier.id == supplier_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def update(supplier_id: uuid.UUID, payload: SupplierUpdate, db: AsyncSession) -> Supplier | None:
        supplier = await SupplierService.get(supplier_id, db)
        if not supplier:
            return None
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(supplier, field, value)
        await db.flush()
        return supplier

    @staticmethod
    async def find_candidates(
        db: AsyncSession,
        materials: Iterable[str] | None = None,
        modes: Iterable[str] | None = None,
        company_id: str | None = None,
    ) -> list[Supplier]:
        items, _ = await SupplierService.list_suppliers(db, company_id)
        material_set = {item.strip().lower() for item in (materials or []) if item and item.strip()}
        mode_set = {item.strip().lower() for item in (modes or []) if item and item.strip()}

        ranked: list[tuple[int, Supplier]] = []
        for supplier in items:
            supplier_materials = {
                str(entry.get("material", "")).strip().lower()
                for entry in supplier.material_profiles
                if isinstance(entry, dict) and entry.get("material")
            }
            supplier_modes = {
                str(entry.get("mode", "")).strip().lower()
                for entry in supplier.lane_preferences
                if isinstance(entry, dict) and entry.get("mode")
            }

            material_hits = len(material_set & supplier_materials) if material_set else 0
            mode_hits = len(mode_set & supplier_modes) if mode_set else 0
            score = material_hits * 3 + mode_hits

            if score > 0 or (not material_set and not mode_set):
                ranked.append((score, supplier))

        ranked.sort(key=lambda item: (-item[0], item[1].legal_name.lower()))
        return [supplier for _, supplier in ranked[:3]]
