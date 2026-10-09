from datetime import date, timedelta
from types import SimpleNamespace as NS

from app.matching import DEFAULT_WEIGHTS, evaluate, normalize_weights


def req(**kw):
    base = dict(property_types=None, transaction=None, cities=None, postal_codes=None, departments=None, regions=None,
                center_label=None, center_latitude=None, center_longitude=None, radius_km=None, surface_min=None, surface_max=None,
                budget_max=None, budget_per_sqm_max=None, min_clear_height=None, min_docks=None, requires_hgv_access=None,
                min_floor_load=None, min_power_kva=None, min_parking=None, desired_date=None, imperatives=[])
    base.update(kw)
    return NS(**base)


def prop(**kw):
    base = dict(property_type=None, transaction=None, city=None, postal_code=None, department=None, region=None, latitude=None,
                longitude=None, surface_total=None, surface_divisible_min=None, sale_price=None, annual_rent=None, rent_per_sqm=None,
                clear_height=None, dock_count=None, hgv_access=None, floor_load=None, power_kva=None, parking_spaces=None,
                available_from=None, availability_note=None)
    base.update(kw)
    return NS(**base)


def test_weights_default_sum_100():
    assert sum(DEFAULT_WEIGHTS.values()) == 100
    w = normalize_weights({"localisation": 60, "surface": 0, "budget": 0, "typologie": 0, "technique": 0, "disponibilite": 0})
    assert round(w["localisation"]) == 100


def test_unconstrained_request_scores_100():
    assert evaluate(req(), prop())["score"] == 100


def test_perfect_match():
    r = req(property_types=["entrepot"], transaction="location", departments=["69"], surface_min=4000, surface_max=6000,
            budget_max=400000, min_clear_height=9, min_docks=4, requires_hgv_access=True, desired_date=date.today() + timedelta(days=30))
    p = prop(property_type="entrepot", transaction="location", postal_code="69800", city="Saint-Priest", surface_total=5000,
             annual_rent=350000, clear_height=10, dock_count=6, hgv_access=True, available_from=date.today())
    res = evaluate(r, p)
    assert res["score"] == 100
    assert not res["eliminated"]
    assert not res["missing"]


def test_missing_information_is_not_validated():
    r = req(surface_min=4000, min_clear_height=9, budget_max=400000)
    p = prop(surface_total=5000)  # hauteur et loyer inconnus
    res = evaluate(r, p)
    assert res["score"] < res["score_potential"]
    assert res["score_potential"] == 100
    assert len(res["missing"]) == 2
    tech = next(g for g in res["groups"] if g["group"] == "technique")
    assert any(c["status"] == "manquant" for c in tech["checks"])


def test_imperative_criterion_eliminates_only_when_unsatisfied():
    r = req(transaction="vente", imperatives=["transaction"])
    assert evaluate(r, prop(transaction="location"))["eliminated"] is True
    assert evaluate(r, prop(transaction="vente_ou_location"))["eliminated"] is False
    # information manquante sur un critère impératif : jamais éliminatoire
    assert evaluate(r, prop(transaction=None))["eliminated"] is False


def test_non_imperative_gap_does_not_eliminate():
    r = req(transaction="vente")
    res = evaluate(r, prop(transaction="location"))
    assert res["eliminated"] is False
    assert res["score"] < 100


def test_divisible_surface_and_proportional_rent():
    r = req(surface_min=3000, surface_max=5000, budget_max=200000, transaction="location")
    p = prop(surface_total=20000, surface_divisible_min=4000, rent_per_sqm=45, annual_rent=900000, transaction="location")
    res = evaluate(r, p)
    surface = next(g for g in res["groups"] if g["group"] == "surface")
    assert surface["earned"] == surface["weight"]
    budget = next(g for g in res["groups"] if g["group"] == "budget")
    assert budget["earned"] == budget["weight"]  # 4000 m² x 45 € = 180 000 € <= 200 000 €


def test_radius_distance():
    r = req(center_latitude=45.764, center_longitude=4.8357, radius_km=20, center_label="Lyon")
    near = evaluate(r, prop(latitude=45.6967, longitude=4.9442))
    far = evaluate(r, prop(latitude=48.86, longitude=2.35))
    assert near["groups"][0]["earned"] == 30
    assert far["groups"][0]["earned"] == 0
    no_gps = evaluate(r, prop(city="Lyon"))
    assert no_gps["groups"][0]["checks"][0]["status"] == "manquant"


def test_region_match_from_postal_code():
    r = req(regions=["Hauts-de-France"])
    assert evaluate(r, prop(postal_code="59810"))["groups"][0]["earned"] == 30
    assert evaluate(r, prop(postal_code="69800"))["groups"][0]["earned"] == 0


def test_type_family_partial():
    r = req(property_types=["entrepot"])
    res = evaluate(r, prop(property_type="plateforme_logistique"))
    typ = next(g for g in res["groups"] if g["group"] == "typologie")
    assert 0 < typ["earned"] < typ["weight"]
