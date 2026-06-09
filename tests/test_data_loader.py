from pathlib import Path

import pytest

from app.services.data_loader import load_tabular_file


def test_load_csv_file():
    df = load_tabular_file(b"a,b\n1,2\n", "sample.csv")

    assert list(df.columns) == ["a", "b"]
    assert df.shape == (1, 2)


def test_load_csv_file_with_windows_1252_smart_quote():
    content = "name,notes\nA,O\u2019Reilly\n".encode("cp1252")

    df = load_tabular_file(content, "windows.csv")

    assert df.loc[0, "notes"] == "O\u2019Reilly"


def test_load_xls_superstore_file_if_available():
    path = Path("data/raw/sample_-_superstore.xls")
    if not path.exists():
        pytest.skip("Superstore xls fixture is not available.")

    df = load_tabular_file(path.read_bytes(), path.name)

    assert "Sales" in df.columns
    assert "Profit" in df.columns
    assert "Quantity" in df.columns


def test_load_tabular_file_rejects_unknown_extension():
    with pytest.raises(ValueError):
        load_tabular_file(b"hello", "notes.txt")
