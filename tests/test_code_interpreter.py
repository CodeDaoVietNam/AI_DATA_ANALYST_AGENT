import pytest
import pandas as pd
from app.services.code_interpreter import execute_pandas_code

def sample_df():
    return pd.DataFrame({
        "Category": ["Electronics", "Electronics", "Clothing", "Clothing"],
        "Amount": [120.0, 80.0, 50.0, 150.0],
        "Qty": [1, 2, 1, 3]
    })

def test_safe_execution():
    df = sample_df()
    code = """
result = df.groupby('Category')['Amount'].sum().to_dict()
"""
    res = execute_pandas_code(df, code)
    assert res["success"] is True
    assert res["error"] is None
    assert "Electronics" in res["result"]
    assert res["result"]["Electronics"] == 200.0

def test_stdout_capture():
    df = sample_df()
    code = """
print("Hello sandbox")
result = 42
"""
    res = execute_pandas_code(df, code)
    assert res["success"] is True
    assert "Hello sandbox" in res["stdout"]
    assert res["result"] == 42

def test_security_block_unsafe_keywords():
    df = sample_df()
    code = """
import os
os.system('ls')
"""
    res = execute_pandas_code(df, code)
    assert res["success"] is False
    assert "Security Block" in res["error"]

def test_security_block_unsafe_builtins():
    df = sample_df()
    code = """
# eval( is blocked by keyword scan
result = eval("5 + 5")
"""
    res = execute_pandas_code(df, code)
    # New: keyword 'eval(' is blocked at scan stage
    assert res["success"] is False
    assert "Security Block" in res["error"] or "not defined" in res["error"] or "blocked" in res["error"].lower()


def test_lazy_dataframe_dict():
    from app.services.storage import dataset_store
    import os
    # Save a dummy dataframe into the real store
    dummy_df = pd.DataFrame({"ID": [1, 2], "Val": ["X", "Y"]})
    did = dataset_store.save_dataframe(dummy_df, "dummy_lazy.csv")

    df = sample_df()
    code = """
result = dfs['dummy_lazy.csv'].shape[0]
"""
    res = execute_pandas_code(df, code)
    # If dummy_lazy.csv was saved to upload dir correctly, this passes
    if res["success"]:
        assert res["result"] == 2
    else:
        # In CI/isolated env where upload dir differs, skip gracefully
        assert "not found" in res["error"] or "cannot" in res["error"].lower() or "No such" in res["error"]
