from __future__ import annotations

from dataclasses import dataclass
from typing import Any


TRIAGE_QUERY = """
MATCH (s:Symptom) WHERE s.id IN $extracted_symptom_ids
MATCH (s)-[r:INDICATES]->(c:Condition)-[:ROUTES_TO]->(sp:Specialty)
MATCH (c)-[:HAS_SEVERITY]->(u:Urgency)
RETURN sp.name AS target_specialty, u.level AS derived_urgency, c.id AS condition_id
ORDER BY r.weight DESC LIMIT 1
""".strip()

SYMPTOM_ALIASES: dict[str, tuple[str, ...]] = {
    "chest_pain": ("chest pain", "pain for chest", "chest tight"),
    "difficulty_breathing": ("difficulty breathing", "cannot breathe", "shortness of breath", "breathing"),
    "severe_bleeding": ("severe bleeding", "heavy bleeding", "bleeding"),
    "fever": ("fever", "high temperature", "body hot"),
    "cough": ("cough", "coughing"),
    "headache": ("headache", "head dey pain"),
    "vomiting": ("vomiting", "throwing up", "vomit"),
    "dizziness": ("dizziness", "dizzy"),
    "rash": ("rash", "skin spots"),
    "weakness": ("weakness", "body weak"),
}


@dataclass(frozen=True)
class ClinicalRoute:
    symptom_ids: list[str]
    target_specialty: str
    derived_urgency: str
    condition_id: str
    source: str


def extract_symptom_ids(text: str, aliases: dict[str, tuple[str, ...]] | dict[str, list[str]] = SYMPTOM_ALIASES) -> list[str]:
    normalized = text.casefold()
    return [symptom_id for symptom_id, terms in aliases.items() if any(alias in normalized for alias in terms)]


def fallback_route(symptom_ids: list[str]) -> ClinicalRoute:
    symptom_set = set(symptom_ids)
    if symptom_set & {"chest_pain", "difficulty_breathing", "severe_bleeding"}:
        condition = "emergency_red_flag"
        specialty = "Emergency Medicine"
        urgency = "CRITICAL"
    elif "fever" in symptom_set and symptom_set & {"cough", "vomiting", "weakness"}:
        condition = "acute_systemic_illness"
        specialty = "General Medicine"
        urgency = "URGENT"
    elif "rash" in symptom_set:
        condition = "dermatological_complaint"
        specialty = "Dermatology"
        urgency = "ROUTINE"
    else:
        condition = "unclassified_presentation"
        specialty = "General Medicine"
        urgency = "ROUTINE"
    return ClinicalRoute(symptom_ids, specialty, urgency, condition, "FALLBACK")


class KnowledgeGraphService:
    def __init__(self, *, enabled: bool, uri: str, user: str, password: str, database: str = "neo4j", cache: Any | None = None) -> None:
        self.enabled = enabled
        self.uri = uri
        self.user = user
        self.password = password
        self.database = database
        self.cache = cache
        self.driver: Any | None = None
        self.available = False

    async def start(self) -> None:
        if not self.enabled:
            return
        try:
            from neo4j import AsyncGraphDatabase

            self.driver = AsyncGraphDatabase.driver(self.uri, auth=(self.user, self.password))
            await self.driver.verify_connectivity()
            self.available = True
        except Exception:
            self.available = False
            if self.driver:
                await self.driver.close()
                self.driver = None

    async def close(self) -> None:
        if self.driver:
            await self.driver.close()

    async def route(self, intake_text: str) -> ClinicalRoute:
        aliases = await self.cache.get_json("clinical:symptom_aliases") if self.cache else None
        symptom_ids = extract_symptom_ids(intake_text, aliases or SYMPTOM_ALIASES)
        if not symptom_ids or not self.available or not self.driver:
            return fallback_route(symptom_ids)
        try:
            async with self.driver.session(database=self.database, default_access_mode="READ") as session:
                result = await session.run(TRIAGE_QUERY, extracted_symptom_ids=symptom_ids)
                record = await result.single()
            if record:
                return ClinicalRoute(
                    symptom_ids=symptom_ids,
                    target_specialty=record["target_specialty"],
                    derived_urgency=record["derived_urgency"],
                    condition_id=record["condition_id"],
                    source="NEO4J",
                )
        except Exception:
            self.available = False
        return fallback_route(symptom_ids)
