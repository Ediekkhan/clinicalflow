from app.services.country_policies import country_policy, radius_for_urgency


def test_emergency_policy_is_country_specific():
    assert country_policy("US").emergency_number == "911"
    assert country_policy("NG").emergency_number == "112"


def test_critical_radius_is_stricter_than_routine():
    assert radius_for_urgency("US", "CRITICAL") < radius_for_urgency("US", "ROUTINE")


def test_unknown_country_is_not_automatically_enabled():
    assert country_policy("ZZ") is None
    assert radius_for_urgency("ZZ", "ROUTINE") is None
