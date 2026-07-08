import pytest


pytestmark = pytest.mark.integration


@pytest.mark.skip(reason="Requires PostgreSQL test container and app client fixture.")
async def test_clinic_a_cannot_see_clinic_b_patients():
    """Staff from Clinic A should only receive Clinic A tickets.

    Integration fixture should:
    1. create Clinic A and Clinic B
    2. insert patients and tickets for both tenants
    3. log in as Clinic A staff
    4. call GET /api/v1/tickets
    5. assert Clinic B ticket IDs are absent even if the route query has no tenant WHERE clause
    """


@pytest.mark.skip(reason="Requires PostgreSQL test container and app client fixture.")
async def test_patient_sees_only_own_tickets():
    """A patient should only receive their own tickets from patient routes."""
