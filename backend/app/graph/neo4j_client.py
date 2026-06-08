from dataclasses import dataclass

from app.services.triage_graph import TRIAGE_CYPHER, get_driver


@dataclass(frozen=True)
class ConditionRoute:
    specialty: str
    urgency: str
    condition_id: str
    condition_name: str


async def route_symptoms(symptom_ids: list[str]) -> ConditionRoute | None:
    driver = get_driver()
    async with driver.session(database="neo4j") as session:
        result = await session.run(TRIAGE_CYPHER, symptom_ids=symptom_ids, extracted_symptom_ids=symptom_ids)
        record = await result.single()
        if not record:
            return None
        return ConditionRoute(
            specialty=record.get("specialty") or record.get("target_specialty"),
            urgency=record.get("urgency") or record.get("derived_urgency"),
            condition_id=record["condition_id"],
            condition_name=record.get("condition_name") or record["condition_id"],
        )

