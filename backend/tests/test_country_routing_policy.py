from app.services.facility_routing import same_country


def test_country_filter_is_applied_before_distance(monkeypatch):
    assert same_country("US", "US")
    assert not same_country("US", "NG")
    assert not same_country(None, "NG")
