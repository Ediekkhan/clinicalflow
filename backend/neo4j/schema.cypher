CREATE CONSTRAINT symptom_id IF NOT EXISTS FOR (s:Symptom) REQUIRE s.id IS UNIQUE;
CREATE CONSTRAINT condition_id IF NOT EXISTS FOR (c:Condition) REQUIRE c.id IS UNIQUE;
CREATE CONSTRAINT specialty_name IF NOT EXISTS FOR (s:Specialty) REQUIRE s.name IS UNIQUE;
CREATE CONSTRAINT urgency_level IF NOT EXISTS FOR (u:Urgency) REQUIRE u.level IS UNIQUE;

MERGE (critical:Urgency {level: 'CRITICAL'})
MERGE (urgent:Urgency {level: 'URGENT'})
MERGE (routine:Urgency {level: 'ROUTINE'})
MERGE (emergency:Specialty {name: 'Emergency Medicine'})
MERGE (general:Specialty {name: 'General Medicine'})
MERGE (dermatology:Specialty {name: 'Dermatology'})

MERGE (chest:Symptom {id: 'chest_pain'}) SET chest.name = 'Chest pain', chest.pidgin_aliases = ['pain for chest']
MERGE (breathing:Symptom {id: 'difficulty_breathing'}) SET breathing.name = 'Difficulty breathing', breathing.pidgin_aliases = ['I no fit breathe']
MERGE (bleeding:Symptom {id: 'severe_bleeding'}) SET bleeding.name = 'Severe bleeding', bleeding.pidgin_aliases = ['blood no dey stop']
MERGE (fever:Symptom {id: 'fever'}) SET fever.name = 'Fever', fever.pidgin_aliases = ['body hot']
MERGE (cough:Symptom {id: 'cough'}) SET cough.name = 'Cough', cough.pidgin_aliases = []
MERGE (rash:Symptom {id: 'rash'}) SET rash.name = 'Rash', rash.pidgin_aliases = []

MERGE (red_flag:Condition {id: 'emergency_red_flag'}) SET red_flag.name = 'Emergency red flag'
MERGE (systemic:Condition {id: 'acute_systemic_illness'}) SET systemic.name = 'Acute systemic illness'
MERGE (skin:Condition {id: 'dermatological_complaint'}) SET skin.name = 'Dermatological complaint'

MERGE (chest)-[:INDICATES {weight: 100}]->(red_flag)
MERGE (breathing)-[:INDICATES {weight: 100}]->(red_flag)
MERGE (bleeding)-[:INDICATES {weight: 100}]->(red_flag)
MERGE (fever)-[:INDICATES {weight: 70}]->(systemic)
MERGE (cough)-[:INDICATES {weight: 60}]->(systemic)
MERGE (rash)-[:INDICATES {weight: 50}]->(skin)
MERGE (red_flag)-[:ROUTES_TO]->(emergency)
MERGE (red_flag)-[:HAS_SEVERITY]->(critical)
MERGE (systemic)-[:ROUTES_TO]->(general)
MERGE (systemic)-[:HAS_SEVERITY]->(urgent)
MERGE (skin)-[:ROUTES_TO]->(dermatology)
MERGE (skin)-[:HAS_SEVERITY]->(routine);
