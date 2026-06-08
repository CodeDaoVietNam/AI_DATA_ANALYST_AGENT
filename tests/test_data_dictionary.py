import json

import pandas as pd
import pytest

from app.services.data_dictionary import (
    dictionary_to_semantic_overrides,
    parse_data_dictionary_csv,
    parse_data_dictionary_json,
    validate_data_dictionary,
)
from app.services.semantic_mapper import build_semantic_profile


def test_parse_data_dictionary_csv():
    content = b"""column_name,business_name,description,semantic_role,data_type,unit,aggregation,sensitive,allowed_values
Sales,Revenue,Total sales amount,revenue,number,USD,sum,false,
Segment,Customer Segment,Customer group,segment,string,,,true,A|B
"""

    dictionary = parse_data_dictionary_csv(content)

    assert dictionary["fields"][0]["column_name"] == "Sales"
    assert dictionary["fields"][0]["semantic_role"] == "revenue"
    assert dictionary["fields"][1]["sensitive"] is True
    assert dictionary["fields"][1]["allowed_values"] == ["A", "B"]


def test_parse_data_dictionary_csv_reads_optional_domain_column():
    content = b"""domain,column_name,business_name,description,semantic_role,data_type,unit,aggregation,sensitive,allowed_values
logistics,Sales,Revenue,Total sales amount,revenue,number,USD,sum,false,
logistics,State,State,Shipping state,state,string,,,false,
"""

    dictionary = parse_data_dictionary_csv(content)

    assert dictionary["domain"] == "logistics"
    assert dictionary["fields"][0]["column_name"] == "Sales"


def test_parse_data_dictionary_json():
    raw = {
        "domain": "retail",
        "fields": [{
            "column_name": "Sales",
            "business_name": "Revenue",
            "semantic_role": "revenue",
            "allowed_values": [],
        }],
    }

    dictionary = parse_data_dictionary_json(json.dumps(raw).encode("utf-8"))

    assert dictionary["domain"] == "retail"
    assert dictionary["fields"][0]["column_name"] == "Sales"


def test_validate_data_dictionary_rejects_missing_column():
    dictionary = {"fields": [{"column_name": "Missing", "semantic_role": "revenue"}]}

    with pytest.raises(ValueError, match="missing columns"):
        validate_data_dictionary(dictionary, ["Sales"])


def test_dictionary_to_semantic_overrides():
    dictionary = {
        "domain": "retail",
        "fields": [
            {"column_name": "Sales", "semantic_role": "revenue"},
            {"column_name": "Order Date", "semantic_role": "date"},
        ],
    }

    overrides = dictionary_to_semantic_overrides(dictionary)

    assert overrides["domain"] == "retail"
    assert overrides["roles"]["revenue"] == "Sales"
    assert overrides["roles"]["date"] == "Order Date"


def test_semantic_mapper_prefers_dictionary_over_auto_detection():
    df = pd.DataFrame({
        "amt": [100.0, 200.0],
        "dt": ["2024-01-01", "2024-01-02"],
        "prod_grp": ["A", "B"],
    })
    dictionary = {
        "domain": "retail",
        "fields": [
            {"column_name": "amt", "semantic_role": "revenue"},
            {"column_name": "dt", "semantic_role": "date"},
            {"column_name": "prod_grp", "semantic_role": "category"},
        ],
    }

    profile = build_semantic_profile(df, overrides={"data_dictionary": dictionary})

    assert profile.domain == "retail"
    assert profile.roles["revenue"].column == "amt"
    assert profile.roles["revenue"].confidence_label == "dictionary"
    assert profile.roles["date"].source == "dictionary"


def test_semantic_mapper_user_override_wins_over_dictionary():
    df = pd.DataFrame({"Sales": [100.0], "Profit": [20.0]})
    dictionary = {
        "domain": "retail",
        "fields": [{"column_name": "Sales", "semantic_role": "revenue"}],
    }

    profile = build_semantic_profile(df, overrides={
        "data_dictionary": dictionary,
        "roles": {"revenue": "Profit"},
    })

    assert profile.roles["revenue"].column == "Profit"
    assert profile.roles["revenue"].confidence_label == "override"
