from dataclasses import dataclass

from neo4j import AsyncGraphDatabase

from app.core.config import get_settings


TRIAGE_CYPHER = """
MATCH (s:Symptom) WHERE s.id IN $extracted_symptom_ids
MATCH (s)-[r:INDICATES]->(c:Condition)-[:ROUTES_TO]->(sp:Specialty)
MATCH (c)-[:HAS_SEVERITY]->(u:Urgency)
RETURN sp.name AS target_specialty, u.level AS derived_urgency, c.id AS condition_id
     , sp.name AS specialty, u.level AS urgency, c.name AS condition_name
ORDER BY r.weight DESC LIMIT 1
"""

FALLBACK_RULES: dict[str, tuple[str, str, str, int]] = {
    "chest_pain": ("Emergency Medicine", "CRITICAL", "acute_coronary_warning", 100),
    "short_breath": ("Emergency Medicine", "CRITICAL", "respiratory_distress", 95),
    "bleeding": ("Emergency Medicine", "CRITICAL", "active_bleeding", 90),
    "pregnancy_pain": ("Obstetrics", "URGENT", "pregnancy_abdominal_pain", 80),
    "fever": ("General Practice", "ROUTINE", "febrile_illness", 45),
    "headache": ("General Practice", "ROUTINE", "headache_non_focal", 35),
    "cough": ("General Practice", "ROUTINE", "cough_uncomplicated", 30),
    "abdominal_pain": ("General Practice", "URGENT", "abdominal_pain_unspecified", 55),
}


@dataclass(frozen=True)
class TriageDecision:
    target_specialty: str
    derived_urgency: str
    condition_id: str


_driver = None


def get_driver():
    global _driver
    settings = get_settings()
    if _driver is None:
        _driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
    return _driver


async def derive_triage(symptom_ids: list[str]) -> TriageDecision:
    if not symptom_ids:
        return TriageDecision("Front Desk Review", "ROUTINE", "unclassified")

    try:
        driver = get_driver()
        async with driver.session(database="neo4j") as session:
            result = await session.run(TRIAGE_CYPHER, extracted_symptom_ids=symptom_ids)
            record = await result.single()
            if record:
                return TriageDecision(
                    target_specialty=record["target_specialty"],
                    derived_urgency=record["derived_urgency"],
                    condition_id=record["condition_id"],
                )
    except Exception:
        pass

    ranked = [
        FALLBACK_RULES[symptom_id]
        for symptom_id in symptom_ids
        if symptom_id in FALLBACK_RULES
    ]
    if not ranked:
        return TriageDecision("Front Desk Review", "ROUTINE", "unclassified")
    specialty, urgency, condition_id, _weight = sorted(ranked, key=lambda row: row[3], reverse=True)[0]
    return TriageDecision(specialty, urgency, condition_id)
