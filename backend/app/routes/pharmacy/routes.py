from __future__ import annotations

from fastapi import APIRouter

from app.routes.sector_helpers import *  # noqa: F403

router = APIRouter(prefix="/api/v1")


@router.post("/pharmacy/medications", status_code=201)
async def create_medication(
    request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    account = await require_pharmacy(request, session)
    payload = await request.json()
    code, name = (
        str(payload.get("code") or "").strip(),
        str(payload.get("generic_name") or "").strip(),
    )
    if not code or not name:
        raise HTTPException(
            status_code=422, detail="Medication code and generic name are required"
        )
    row = Medication(
        country_code=str(payload.get("country_code") or "NG").upper(),
        code=code,
        generic_name=name,
        form=payload.get("form"),
        strength=payload.get("strength"),
        controlled_schedule=payload.get("controlled_schedule"),
    )
    session.add(row)
    await session.flush()
    await audit(
        session, request, account, "CREATED", "Medication", row.id, account.tenant_id
    )
    await session.commit()
    return {
        "id": str(row.id),
        "code": row.code,
        "generic_name": row.generic_name,
        "controlled_schedule": row.controlled_schedule,
    }


@router.post("/pharmacy/inventory", status_code=201)
async def create_inventory(
    request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    account = await require_pharmacy(request, session)
    payload = await request.json()
    medication_id = parse_uuid(payload.get("medication_id"), "medication_id")
    if not await session.get(Medication, medication_id):
        raise HTTPException(status_code=404, detail="Medication not found")
    quantity = int(payload.get("quantity_on_hand") or 0)
    if quantity < 0:
        raise HTTPException(
            status_code=422, detail="Inventory quantity cannot be negative"
        )
    row = InventoryItem(
        pharmacy_id=account.tenant_id,
        medication_id=medication_id,
        batch_number=str(payload.get("batch_number") or "").strip(),
        quantity_on_hand=quantity,
        reorder_level=max(0, int(payload.get("reorder_level") or 0)),
        expires_at=parse_datetime(payload.get("expires_at"), "expires_at"),
    )
    if not row.batch_number:
        raise HTTPException(status_code=422, detail="Batch number is required")
    session.add(row)
    await session.flush()
    session.add(
        StockMovement(
            inventory_item_id=row.id,
            movement_type="RECEIPT",
            quantity=quantity,
            actor_id=account.id,
        )
    )
    await session.commit()
    return {
        "id": str(row.id),
        "quantity_on_hand": row.quantity_on_hand,
        "status": row.status,
    }


@router.post("/prescriptions", status_code=201)
async def create_prescription(
    request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    account = await require_roles(request, session, {"doctor", "specialist"})
    membership = await require_staff_workspace(
        session, account, roles={"doctor", "specialist"}
    )
    privilege = await session.scalar(
        select(ClinicalPrivilege).where(
            ClinicalPrivilege.membership_id == membership.id,
            ClinicalPrivilege.code == "PRESCRIBE",
            ClinicalPrivilege.status == "ACTIVE",
            ClinicalPrivilege.revoked_at.is_(None),
        )
    )
    if not privilege:
        raise HTTPException(
            status_code=403, detail="Active prescribing privilege is required"
        )
    payload = await request.json()
    patient_id, pharmacy_id = parse_uuid(
        payload.get("patient_id"), "patient_id"
    ), parse_uuid(payload.get("pharmacy_id"), "pharmacy_id")
    patient = await session.scalar(
        select(AuthAccount).where(
            AuthAccount.id == patient_id,
            AuthAccount.role == "patient",
            AuthAccount.is_active.is_(True),
        )
    )
    pharmacy = await session.scalar(
        select(Tenant).where(Tenant.id == pharmacy_id, Tenant.status == "ACTIVE")
    )
    items = payload.get("items")
    if not patient or not pharmacy or not isinstance(items, list) or not items:
        raise HTTPException(
            status_code=422,
            detail="An active patient, pharmacy, and at least one item are required",
        )
    policy = await country_policy(session, str(payload.get("country_code") or "NG"))
    if account.role not in set(
        nested_policy(policy, "prescription", "allowed_prescriber_roles", default=[])
    ):
        raise HTTPException(
            status_code=403,
            detail="This country policy does not permit the account role to prescribe",
        )
    row = Prescription(
        patient_id=patient.id,
        encounter_id=(
            parse_uuid(payload["encounter_id"], "encounter_id")
            if payload.get("encounter_id")
            else None
        ),
        prescriber_id=account.id,
        prescriber_membership_id=membership.id,
        facility_id=membership.hospital_id,
        pharmacy_id=pharmacy.id,
        country_code=str(payload.get("country_code") or "NG").upper(),
        expires_at=utc_now()
        + timedelta(
            days=int(
                nested_policy(policy, "prescription", "default_valid_days", default=30)
            )
        ),
    )
    session.add(row)
    await session.flush()
    for value in items:
        medication_id = parse_uuid(value.get("medication_id"), "medication_id")
        medication = await session.get(Medication, medication_id)
        quantity, days = int(value.get("quantity") or 0), int(
            value.get("duration_days") or 0
        )
        if (
            not medication
            or medication.status != "ACTIVE"
            or quantity <= 0
            or days <= 0
            or not str(value.get("dosage") or "").strip()
            or not str(value.get("frequency") or "").strip()
        ):
            raise HTTPException(
                status_code=422,
                detail="Every prescription item requires an active medication, dosage, frequency, duration, and positive quantity",
            )
        session.add(
            PrescriptionItem(
                prescription_id=row.id,
                medication_id=medication.id,
                dosage=str(value["dosage"]).strip(),
                route=value.get("route"),
                frequency=str(value["frequency"]).strip(),
                duration_days=days,
                quantity=quantity,
                substitution_allowed=bool(value.get("substitution_allowed", False)),
            )
        )
    order = PharmacyOrder(prescription_id=row.id, pharmacy_id=pharmacy.id)
    session.add(order)
    await session.flush()
    pharmacy_users = list(
        (
            await session.execute(
                select(AuthAccount).where(
                    AuthAccount.tenant_id == pharmacy.id,
                    AuthAccount.role.in_(["admin", "pharmacy", "pharmacist"]),
                    AuthAccount.is_active.is_(True),
                )
            )
        )
        .scalars()
        .all()
    )
    for recipient in pharmacy_users:
        session.add_all(
            notification(
                pharmacy.id,
                recipient,
                "PRESCRIPTION_RECEIVED",
                "Prescription received",
                "A signed prescription is ready for pharmacy validation.",
                {"order_id": str(order.id)},
            )
        )
    await audit(
        session,
        request,
        account,
        "SIGNED",
        "Prescription",
        row.id,
        membership.hospital_id,
    )
    await session.commit()
    return {
        "id": str(row.id),
        "order_id": str(order.id),
        "status": row.status,
        "expires_at": row.expires_at,
    }


@router.get("/pharmacy/prescriptions")
async def list_pharmacy_orders(
    request: Request, session: AsyncSession = Depends(get_db)
) -> list[dict[str, Any]]:
    account = await require_pharmacy(request, session)
    rows = list(
        (
            await session.execute(
                select(PharmacyOrder, Prescription, AuthAccount)
                .join(Prescription, Prescription.id == PharmacyOrder.prescription_id)
                .join(AuthAccount, AuthAccount.id == Prescription.patient_id)
                .where(PharmacyOrder.pharmacy_id == account.tenant_id)
                .order_by(PharmacyOrder.created_at.desc())
                .limit(200)
            )
        ).all()
    )
    return [
        order_json(order, prescription, patient)
        for order, prescription, patient in rows
    ]


@router.get("/pharmacy/inventory")
async def list_inventory(
    request: Request, session: AsyncSession = Depends(get_db)
) -> list[dict[str, Any]]:
    account = await require_pharmacy(request, session)
    rows = list(
        (
            await session.execute(
                select(InventoryItem, Medication)
                .join(Medication, Medication.id == InventoryItem.medication_id)
                .where(InventoryItem.pharmacy_id == account.tenant_id)
                .order_by(InventoryItem.expires_at)
            )
        ).all()
    )
    return [
        {
            "id": str(row.id),
            "medication": medication.generic_name,
            "batch_number": row.batch_number,
            "quantity_on_hand": row.quantity_on_hand,
            "reorder_level": row.reorder_level,
            "expires_at": row.expires_at,
            "low_stock": row.quantity_on_hand <= row.reorder_level,
            "status": row.status,
        }
        for row, medication in rows
    ]


@router.get("/pharmacy/dashboard")
async def pharmacy_dashboard(
    request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    account = await require_pharmacy(request, session)
    pending = await session.scalar(
        select(func.count())
        .select_from(PharmacyOrder)
        .where(
            PharmacyOrder.pharmacy_id == account.tenant_id,
            PharmacyOrder.status.in_(["RECEIVED", "VALIDATED", "PARTIALLY_DISPENSED"]),
        )
    )
    low = await session.scalar(
        select(func.count())
        .select_from(InventoryItem)
        .where(
            InventoryItem.pharmacy_id == account.tenant_id,
            InventoryItem.quantity_on_hand <= InventoryItem.reorder_level,
        )
    )
    return {
        "stats": {"pending_prescriptions": pending, "low_stock_items": low},
        "recent": await list_pharmacy_orders(request, session),
    }


@router.post("/pharmacy/orders/{order_id}/validate")
async def validate_order(
    order_id: str, request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    account = await require_pharmacy(request, session)
    order = await session.scalar(
        select(PharmacyOrder)
        .where(
            PharmacyOrder.id == parse_uuid(order_id, "order_id"),
            PharmacyOrder.pharmacy_id == account.tenant_id,
        )
        .with_for_update()
    )
    if not order:
        raise HTTPException(status_code=404, detail="Pharmacy order not found")
    prescription = await session.get(Prescription, order.prescription_id)
    if not prescription or is_expired(prescription.expires_at):
        order.status = "EXPIRED"
        await session.commit()
        raise HTTPException(status_code=409, detail="Prescription has expired")
    alerts = await session.scalar(
        select(func.count())
        .select_from(InteractionAlert)
        .where(
            InteractionAlert.prescription_id == prescription.id,
            InteractionAlert.severity == "CRITICAL",
            InteractionAlert.acknowledged_at.is_(None),
        )
    )
    if alerts:
        raise HTTPException(
            status_code=409,
            detail="Critical interaction alerts must be acknowledged before validation",
        )
    payload = await request.json()
    order.status, order.validated_by_id, order.validation_notes, order.validated_at = (
        "VALIDATED",
        account.id,
        str(payload.get("notes") or "").strip() or None,
        utc_now(),
    )
    await session.commit()
    return {"id": str(order.id), "status": order.status}


@router.post("/pharmacy/orders/{order_id}/dispense")
async def dispense_order(
    order_id: str, request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    account = await require_pharmacy(request, session)
    key = str(request.headers.get("x-idempotency-key") or "").strip()
    if not key:
        raise HTTPException(status_code=422, detail="X-Idempotency-Key is required")
    payload = await request.json()
    item_id, inventory_id = parse_uuid(
        payload.get("prescription_item_id"), "prescription_item_id"
    ), parse_uuid(payload.get("inventory_item_id"), "inventory_item_id")
    existing = await session.scalar(
        select(DispenseEvent).where(
            DispenseEvent.prescription_item_id == item_id,
            DispenseEvent.idempotency_key == key,
        )
    )
    if existing:
        return {
            "id": str(existing.id),
            "status": "ALREADY_PROCESSED",
            "quantity": existing.quantity,
        }
    order = await session.scalar(
        select(PharmacyOrder)
        .where(
            PharmacyOrder.id == parse_uuid(order_id, "order_id"),
            PharmacyOrder.pharmacy_id == account.tenant_id,
        )
        .with_for_update()
    )
    if not order or order.status not in {"VALIDATED", "PARTIALLY_DISPENSED"}:
        raise HTTPException(
            status_code=409, detail="A validated pharmacy order is required"
        )
    prescription = await session.get(Prescription, order.prescription_id)
    item = await session.scalar(
        select(PrescriptionItem)
        .where(
            PrescriptionItem.id == item_id,
            PrescriptionItem.prescription_id == order.prescription_id,
        )
        .with_for_update()
    )
    inventory = await session.scalar(
        select(InventoryItem)
        .where(
            InventoryItem.id == inventory_id,
            InventoryItem.pharmacy_id == account.tenant_id,
        )
        .with_for_update()
    )
    medication = await session.get(Medication, item.medication_id) if item else None
    quantity = int(payload.get("quantity") or 0)
    if (
        not prescription
        or is_expired(prescription.expires_at)
        or not item
        or not inventory
        or inventory.medication_id != item.medication_id
    ):
        raise HTTPException(
            status_code=422,
            detail="Prescription item and matching pharmacy inventory are required",
        )
    remaining = item.quantity - item.quantity_dispensed
    if (
        quantity <= 0
        or quantity > remaining
        or quantity > inventory.quantity_on_hand
        or is_expired(inventory.expires_at)
    ):
        raise HTTPException(
            status_code=409,
            detail="Requested quantity is unavailable, expired, or exceeds the prescription",
        )
    if (
        medication
        and medication.controlled_schedule
        and (
            not payload.get("witness_id")
            or not str(payload.get("register_reference") or "").strip()
        )
    ):
        raise HTTPException(
            status_code=422,
            detail="Controlled medicine dispensing requires a witness and register reference",
        )
    event = DispenseEvent(
        pharmacy_order_id=order.id,
        prescription_item_id=item.id,
        inventory_item_id=inventory.id,
        quantity=quantity,
        dispenser_id=account.id,
        idempotency_key=key,
    )
    session.add(event)
    await session.flush()
    item.quantity_dispensed += quantity
    item.status = (
        "DISPENSED"
        if item.quantity_dispensed == item.quantity
        else "PARTIALLY_DISPENSED"
    )
    inventory.quantity_on_hand -= quantity
    inventory.status = (
        "LOW_STOCK"
        if inventory.quantity_on_hand <= inventory.reorder_level
        else "AVAILABLE"
    )
    session.add(
        StockMovement(
            inventory_item_id=inventory.id,
            movement_type="DISPENSE",
            quantity=-quantity,
            reference_type="DispenseEvent",
            reference_id=event.id,
            actor_id=account.id,
        )
    )
    if medication and medication.controlled_schedule:
        session.add(
            ControlledMedicationLog(
                dispense_event_id=event.id,
                schedule=medication.controlled_schedule,
                witness_id=parse_uuid(payload.get("witness_id"), "witness_id"),
                register_reference=str(payload["register_reference"]).strip(),
            )
        )
    open_items = await session.scalar(
        select(func.count())
        .select_from(PrescriptionItem)
        .where(
            PrescriptionItem.prescription_id == prescription.id,
            PrescriptionItem.id != item.id,
            PrescriptionItem.status != "DISPENSED",
        )
    )
    order.status = (
        "DISPENSED"
        if item.status == "DISPENSED" and not open_items
        else "PARTIALLY_DISPENSED"
    )
    if order.status == "DISPENSED":
        prescription.status = "DISPENSED"
    session.add(
        MedicationHistory(
            patient_id=prescription.patient_id,
            encounter_id=prescription.encounter_id,
            medication_name=medication.generic_name if medication else "Medication",
            dosage=item.dosage,
            status="DISPENSED",
            started_at=utc_now(),
        )
    )
    patient = await session.get(AuthAccount, prescription.patient_id)
    if patient:
        session.add_all(
            notification(
                account.tenant_id,
                patient,
                "PRESCRIPTION_DISPENSED",
                "Prescription update",
                "Your prescription dispensing status has changed.",
                {"order_id": str(order.id), "status": order.status},
            )
        )
    await audit(
        session,
        request,
        account,
        "DISPENSED",
        "PharmacyOrder",
        order.id,
        account.tenant_id,
    )
    try:
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        raise HTTPException(
            status_code=409, detail="This dispensing action was already processed"
        ) from error
    return {"id": str(event.id), "status": order.status, "quantity": quantity}


@router.post("/pharmacy/orders/{order_id}/counselling", status_code=201)
async def record_counselling(
    order_id: str, request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    account = await require_pharmacy(request, session)
    order = await session.scalar(
        select(PharmacyOrder).where(
            PharmacyOrder.id == parse_uuid(order_id, "order_id"),
            PharmacyOrder.pharmacy_id == account.tenant_id,
        )
    )
    payload = await request.json()
    topics = payload.get("topics")
    if not order or not isinstance(topics, list) or not topics:
        raise HTTPException(
            status_code=422,
            detail="A pharmacy order and counselling topics are required",
        )
    row = PatientCounselling(
        pharmacy_order_id=order.id,
        pharmacist_id=account.id,
        topics_json=json.dumps(topics),
        patient_understood=bool(payload.get("patient_understood")),
        notes=str(payload.get("notes") or "").strip() or None,
    )
    session.add(row)
    await session.commit()
    return {"id": str(row.id), "patient_understood": row.patient_understood}
