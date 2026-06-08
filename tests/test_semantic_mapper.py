import pandas as pd

from app.services.semantic_mapper import build_semantic_profile


def test_build_semantic_profile_detects_retail_roles():
    df = pd.DataFrame({
        "Order Date": ["2024-01-01"],
        "Sales": [100.0],
        "Quantity": [2],
        "Segment": ["Consumer"],
        "State": ["California"],
    })

    profile = build_semantic_profile(df)

    assert profile.roles["revenue"].column == "Sales"
    assert profile.roles["quantity"].column == "Quantity"
    assert profile.roles["category"].column == "Segment"
    assert profile.roles["date"].column == "Order Date"
    assert profile.domain == "retail"


def test_build_semantic_profile_detects_marketing_domain():
    df = pd.DataFrame({
        "Customer_ID": [1],
        "Campaign_Type": ["Email"],
        "Response": [1],
    })

    profile = build_semantic_profile(df)

    assert profile.domain == "marketing"
    assert profile.roles["campaign"].column == "Campaign_Type"
    assert profile.roles["target"].column == "Response"


def test_build_semantic_profile_detects_hr_domain():
    df = pd.DataFrame({
        "EmployeeNumber": [1],
        "Attrition": ["Yes"],
        "Department": ["Sales"],
        "MonthlyIncome": [5993],
    })

    profile = build_semantic_profile(df)

    assert profile.domain == "hr"
    assert profile.roles["target"].column == "Attrition"
    assert profile.roles["salary"].column == "MonthlyIncome"


def test_build_semantic_profile_detects_logistics_traffic_schema():
    df = pd.DataFrame({
        "CRASH DATE": ["2020-08-29"],
        "CRASH TIME": ["15:40:00"],
        "BOROUGH": ["BRONX"],
        "COLLISION_ID": [4342908],
        "Vehicle Type": ["Sedan"],
        "Accident Count": [1],
    })

    profile = build_semantic_profile(df)

    assert profile.domain == "logistics"
    assert profile.roles["date"].column == "CRASH DATE"
    assert profile.roles["city"].column == "BOROUGH"
    assert profile.roles["category"].column == "Vehicle Type"
    assert profile.roles["quantity"].column == "Accident Count"


def test_build_semantic_profile_detects_logistics_ridership_schema():
    df = pd.DataFrame({
        "Date": ["2020-03-01"],
        "Transit Mode": ["Subways"],
        "Ridership": [2212965],
    })

    profile = build_semantic_profile(df)

    assert profile.domain == "logistics"
    assert profile.roles["date"].column == "Date"
    assert profile.roles["category"].column == "Transit Mode"
    assert profile.roles["quantity"].column == "Ridership"


def test_build_semantic_profile_unknown_schema_is_generic():
    df = pd.DataFrame({"A": [1], "B": ["x"]})

    profile = build_semantic_profile(df)

    assert profile.domain == "generic"
    assert profile.warnings


def test_build_semantic_profile_returns_candidates_and_accepts_overrides():
    df = pd.DataFrame({
        "Sales": [100.0],
        "Profit": [20.0],
        "Segment": ["Consumer"],
        "Order Date": ["2024-01-01"],
    })

    profile = build_semantic_profile(df, overrides={"domain": "finance", "roles": {"revenue": "Profit"}})

    assert profile.domain == "finance"
    assert profile.domain_confidence == 1.0
    assert profile.roles["revenue"].column == "Profit"
    assert profile.roles["revenue"].confidence_label == "override"
    assert profile.candidates["revenue"]
