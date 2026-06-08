from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import pandas as pd


DEFAULT_MAX_ROWS = 10000
CSV_ENCODINGS = ("utf-8", "cp1252", "latin1")


def read_csv_any(path: Path, *, sep: str = ",", nrows: int | None = None) -> pd.DataFrame:
    last_error: Exception | None = None
    for encoding in CSV_ENCODINGS:
        try:
            return pd.read_csv(path, sep=sep, nrows=nrows, low_memory=False, encoding=encoding)
        except Exception as exc:
            last_error = exc
    raise ValueError(f"Could not read CSV {path}: {last_error}")


def first_existing(root: Path, paths: list[str]) -> Path | None:
    for item in paths:
        path = root / item
        if path.exists():
            return path
    return None


def write_snapshot(df: pd.DataFrame, destination: Path, *, max_rows: int = DEFAULT_MAX_ROWS) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    output = df.head(max_rows).copy() if max_rows else df.copy()
    output.columns = [str(column).strip() for column in output.columns]
    output.to_csv(destination, index=False)


def numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def money_to_number(series: pd.Series) -> pd.Series:
    clean = series.astype(str).str.replace(r"[$,BMbmkK ]", "", regex=True)
    multiplier = series.astype(str).str.upper().str.extract(r"([BMK])", expand=False).map({"B": 1_000_000_000, "M": 1_000_000, "K": 1_000})
    return pd.to_numeric(clean, errors="coerce") * multiplier.fillna(1)


def write_dictionary(path: Path, domain: str, fields: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for field in fields:
        rows.append({
            "domain": domain,
            "column_name": field["column_name"],
            "business_name": field.get("business_name") or field["column_name"],
            "description": field.get("description") or "",
            "semantic_role": field.get("semantic_role") or "",
            "data_type": field.get("data_type") or "",
            "unit": field.get("unit") or "",
            "aggregation": field.get("aggregation") or "",
            "sensitive": str(bool(field.get("sensitive", False))).lower(),
            "allowed_values": field.get("allowed_values") or "",
        })
    pd.DataFrame(rows).to_csv(path, index=False)


def field(column: str, role: str, data_type: str, aggregation: str = "", *, name: str | None = None, unit: str = "", sensitive: bool = False) -> dict[str, Any]:
    return {
        "column_name": column,
        "business_name": name or column,
        "semantic_role": role,
        "data_type": data_type,
        "aggregation": aggregation,
        "unit": unit,
        "sensitive": sensitive,
    }


def prepare_online_retail(root: Path) -> str:
    source = first_existing(root, [
        "evals/datasets/ecommerce/online_retail_II.csv",
        "data/raw/online_retail_10_11.csv",
        "data/raw/online_retail_09_10.csv",
    ])
    if not source:
        return "skip online_retail: source missing"
    df = read_csv_any(source, nrows=DEFAULT_MAX_ROWS)
    if {"Quantity", "Price"} <= set(df.columns):
        df["Revenue"] = numeric(df["Quantity"]) * numeric(df["Price"])
    write_snapshot(df, root / "evals/datasets/ecommerce/uci_online_retail_ii.csv")
    write_dictionary(root / "evals/dictionaries/ecommerce/uci_online_retail_ii_dictionary.csv", "ecommerce", [
        field("Invoice", "customer", "string", sensitive=True),
        field("Description", "category", "string"),
        field("Quantity", "quantity", "number", "sum"),
        field("InvoiceDate", "date", "date"),
        field("Revenue", "revenue", "number", "sum", unit="GBP"),
        field("Country", "country", "string"),
    ])
    return "prepared ecommerce/uci_online_retail_ii.csv"


def prepare_fuzzy_factory(root: Path) -> str:
    base = root / "evals/datasets/ecommerce/Maven+Fuzzy+Factory"
    required = ["orders.csv", "order_items.csv", "products.csv", "website_sessions.csv"]
    if not all((base / name).exists() for name in required):
        return "skip fuzzy_factory: source package missing"
    orders = read_csv_any(base / "orders.csv")
    items = read_csv_any(base / "order_items.csv")
    products = read_csv_any(base / "products.csv")
    sessions = read_csv_any(base / "website_sessions.csv")
    df = (
        items.merge(orders[["order_id", "created_at", "website_session_id", "user_id", "items_purchased"]], on="order_id", how="left", suffixes=("_item", "_order"))
        .merge(products[["product_id", "product_name"]], on="product_id", how="left")
        .merge(sessions[["website_session_id", "utm_source", "utm_campaign", "device_type"]], on="website_session_id", how="left")
    )
    df["order_date"] = df["created_at_order"]
    df["revenue"] = numeric(df["price_usd"])
    df["cost"] = numeric(df["cogs_usd"])
    df["profit"] = df["revenue"] - df["cost"]
    df["quantity"] = 1
    df["segment"] = df["device_type"]
    df["category"] = df["product_name"]
    keep = ["order_id", "order_date", "user_id", "product_id", "product_name", "category", "segment", "utm_source", "utm_campaign", "quantity", "revenue", "cost", "profit"]
    write_snapshot(df[keep], root / "evals/datasets/ecommerce/maven_toy_store_orders.csv")
    write_dictionary(root / "evals/dictionaries/ecommerce/maven_toy_store_dictionary.csv", "ecommerce", [
        field("order_id", "customer", "string", sensitive=True),
        field("order_date", "date", "date"),
        field("category", "category", "string"),
        field("segment", "segment", "string"),
        field("utm_campaign", "campaign", "string"),
        field("utm_source", "channel", "string"),
        field("quantity", "quantity", "number", "sum"),
        field("revenue", "revenue", "number", "sum", unit="USD"),
        field("cost", "cost", "number", "sum", unit="USD"),
        field("profit", "profit", "number", "sum", unit="USD"),
    ])
    return "prepared ecommerce/maven_toy_store_orders.csv from Maven Fuzzy Factory"


def prepare_northwind(root: Path) -> str:
    base = root / "evals/datasets/retail/Northwind Traders"
    required = ["orders.csv", "order_details.csv", "products.csv", "categories.csv", "customers.csv"]
    if not all((base / name).exists() for name in required):
        return "skip northwind: source package missing"
    orders = read_csv_any(base / "orders.csv")
    details = read_csv_any(base / "order_details.csv")
    products = read_csv_any(base / "products.csv", sep=",")
    categories = read_csv_any(base / "categories.csv")
    customers = read_csv_any(base / "customers.csv")
    df = (
        details.merge(orders, on="orderID", how="left")
        .merge(products[["productID", "productName", "categoryID"]], on="productID", how="left")
        .merge(categories[["categoryID", "categoryName"]], on="categoryID", how="left")
        .merge(customers[["customerID", "city", "country"]], on="customerID", how="left")
    )
    df["sales"] = numeric(df["unitPrice"]) * numeric(df["quantity"]) * (1 - numeric(df["discount"]).fillna(0))
    write_snapshot(df, root / "evals/datasets/retail/northwind_orders.csv")
    write_dictionary(root / "evals/dictionaries/retail/northwind_dictionary.csv", "retail", [
        field("orderDate", "date", "date"),
        field("sales", "revenue", "number", "sum", unit="USD"),
        field("quantity", "quantity", "number", "sum"),
        field("discount", "discount", "number", "mean"),
        field("categoryName", "category", "string"),
        field("country", "country", "string"),
        field("city", "city", "string"),
        field("customerID", "customer", "string", sensitive=True),
    ])
    return "prepared retail/northwind_orders.csv"


def prepare_finance(root: Path) -> list[str]:
    messages = []
    complaints = root / "evals/datasets/finance/Consumer_Complaints.xlsx"
    if complaints.exists():
        df = pd.read_excel(complaints, nrows=DEFAULT_MAX_ROWS, engine="openpyxl")
        df["Complaint Count"] = 1
        write_snapshot(df, root / "evals/datasets/finance/financial_consumer_complaints.csv")
        write_dictionary(root / "evals/dictionaries/finance/financial_consumer_complaints_dictionary.csv", "finance", [
            field("Date received", "date", "date"),
            field("Product", "category", "string"),
            field("State", "state", "string"),
            field("Complaint Count", "quantity", "number", "sum"),
        ])
        messages.append("prepared finance/financial_consumer_complaints.csv")
    sp500 = root / "evals/datasets/finance/S&P 500 Stock Prices 2014-2017.csv"
    if sp500.exists():
        df = read_csv_any(sp500, nrows=DEFAULT_MAX_ROWS)
        write_snapshot(df, root / "evals/datasets/finance/sp500_stock_prices.csv")
        write_dictionary(root / "evals/dictionaries/finance/sp500_stock_prices_dictionary.csv", "finance", [
            field("date", "date", "date"),
            field("symbol", "category", "string"),
            field("close", "revenue", "number", "mean", unit="USD", name="Close Price"),
            field("volume", "quantity", "number", "sum"),
        ])
        messages.append("prepared finance/sp500_stock_prices.csv")
    unicorn = root / "evals/datasets/finance/Unicorn_Companies.csv"
    if unicorn.exists():
        df = read_csv_any(unicorn)
        df["ValuationAmount"] = money_to_number(df["Valuation"])
        df["FundingAmount"] = money_to_number(df["Funding"]) if "Funding" in df.columns else pd.NA
        write_snapshot(df, root / "evals/datasets/finance/unicorn_companies.csv")
        write_dictionary(root / "evals/dictionaries/finance/unicorn_companies_dictionary.csv", "finance", [
            field("Date Joined", "date", "date"),
            field("Industry", "category", "string"),
            field("Country", "country", "string"),
            field("ValuationAmount", "revenue", "number", "sum", unit="USD", name="Valuation"),
            field("FundingAmount", "cost", "number", "sum", unit="USD", name="Funding"),
        ])
        messages.append("prepared finance/unicorn_companies.csv")
    return messages or ["skip finance: source files missing"]


def prepare_bank_marketing(root: Path) -> str:
    source = first_existing(root, [
        "evals/datasets/marketing/bank/bank-full.csv",
        "evals/datasets/marketing/bank-additional/bank-additional-full.csv",
    ])
    if not source:
        return "skip bank_marketing: source missing"
    df = read_csv_any(source, sep=";", nrows=DEFAULT_MAX_ROWS)
    write_snapshot(df, root / "evals/datasets/marketing/uci_bank_marketing.csv")
    write_dictionary(root / "evals/dictionaries/marketing/uci_bank_marketing_dictionary.csv", "marketing", [
        field("age", "customer", "number", "mean", sensitive=True),
        field("job", "segment", "string"),
        field("education", "segment", "string"),
        field("balance", "monetary", "number", "mean"),
        field("contact", "channel", "string"),
        field("month", "date", "string"),
        field("campaign", "campaign", "number", "sum"),
        field("pdays", "recency", "number", "mean"),
        field("y", "target", "string"),
    ])
    return "prepared marketing/uci_bank_marketing.csv"


def prepare_surveys(root: Path) -> list[str]:
    messages = []
    employee = root / "evals/datasets/survey/HR Employee Survey Responses.xlsx"
    if employee.exists():
        df = pd.read_excel(employee, nrows=DEFAULT_MAX_ROWS, engine="openpyxl")
        role_columns = [column for column in ["Director", "Manager", "Supervisor", "Staff"] if column in df.columns]
        if role_columns:
            df["Job Role"] = df[role_columns].apply(_first_truthy_role, axis=1)
        write_snapshot(df, root / "evals/datasets/survey/employee_survey_responses.csv")
        write_dictionary(root / "evals/dictionaries/survey/employee_survey_responses_dictionary.csv", "survey", [
            field("Department", "department", "string"),
            field("Job Role", "job_role", "string"),
            field("Response", "target", "number", "mean"),
        ])
        messages.append("prepared survey/employee_survey_responses.csv")
    remote = first_existing(root, ["evals/datasets/survey/2021_rws.csv", "evals/datasets/survey/2020_rws.csv", "evals/datasets/hr/2021_rws.csv", "evals/datasets/hr/2020_rws.csv"])
    if remote:
        raw = read_csv_any(remote, nrows=DEFAULT_MAX_ROWS)
        df = pd.DataFrame()
        df["Response ID"] = raw[_find_column(raw, ["Response ID"])]
        df["Date"] = "2021-01-01" if "2021" in remote.name else "2020-01-01"
        df["Segment"] = raw[_find_column(raw, ["industry"])]
        df["Region"] = raw[_find_column(raw, ["Metro", "Regional"])]
        target_col = _find_column(raw, ["recommend remote", "Going forward", "prefer"])
        df["Target"] = raw[target_col]
        df["Quantity"] = 1
        write_snapshot(df, root / "evals/datasets/survey/remote_working_survey.csv")
        write_dictionary(root / "evals/dictionaries/survey/remote_working_survey_dictionary.csv", "survey", [
            field("Date", "date", "date"),
            field("Segment", "segment", "string"),
            field("Region", "country", "string"),
            field("Target", "target", "string"),
            field("Quantity", "quantity", "number", "sum"),
        ])
        messages.append("prepared survey/remote_working_survey.csv")
    airline = root / "evals/datasets/survey/airline_passenger_satisfaction.csv"
    if airline.exists():
        df = read_csv_any(airline, nrows=DEFAULT_MAX_ROWS)
        write_snapshot(df, airline)
        write_dictionary(root / "evals/dictionaries/survey/airline_passenger_satisfaction_dictionary.csv", "survey", [
            field("Satisfaction", "target", "string"),
            field("Customer Type", "segment", "string"),
            field("Class", "category", "string"),
            field("Flight Distance", "quantity", "number", "mean"),
        ])
        messages.append("prepared survey/airline_passenger_satisfaction.csv")
    return messages or ["skip surveys: source files missing"]


def _first_truthy_role(row: pd.Series) -> str:
    for column, value in row.items():
        text = str(value).strip().lower()
        if text and text not in {"0", "false", "nan", "no"}:
            return str(column)
    return "Staff"


def _find_column(df: pd.DataFrame, contains: list[str]) -> str:
    lowered = {str(column).lower(): column for column in df.columns}
    for needle in contains:
        needle_lower = needle.lower()
        for lower, original in lowered.items():
            if needle_lower in lower:
                return original
    raise ValueError(f"Cannot find column containing any of: {contains}")


def prepare_logistics(root: Path) -> list[str]:
    messages = []
    candy = root / "evals/datasets/logistics/Candy_Sales.csv"
    if candy.exists():
        df = read_csv_any(candy, nrows=DEFAULT_MAX_ROWS)
        write_snapshot(df, root / "evals/datasets/logistics/us_candy_distributor_orders.csv")
        write_dictionary(root / "evals/dictionaries/logistics/us_candy_distributor_dictionary.csv", "logistics", [
            field("Order Date", "date", "date"),
            field("Sales", "revenue", "number", "sum", unit="USD"),
            field("Cost", "cost", "number", "sum", unit="USD"),
            field("Gross Profit", "profit", "number", "sum", unit="USD"),
            field("Units", "quantity", "number", "sum"),
            field("Division", "category", "string"),
            field("State/Province", "state", "string"),
            field("City", "city", "string"),
        ])
        messages.append("prepared logistics/us_candy_distributor_orders.csv")
    mta = root / "evals/datasets/logistics/MTA_Daily_Ridership.csv"
    if mta.exists():
        wide = read_csv_any(mta)
        value_columns = [column for column in wide.columns if "Total" in str(column)]
        df = wide.melt(id_vars=["Date"], value_vars=value_columns, var_name="Transit Mode", value_name="Ridership")
        df["Transit Mode"] = df["Transit Mode"].astype(str).str.split(":", n=1).str[0]
        df["Ridership"] = numeric(df["Ridership"].astype(str).str.replace(",", "", regex=False))
        write_snapshot(df, root / "evals/datasets/logistics/mta_daily_ridership.csv")
        write_dictionary(root / "evals/dictionaries/logistics/mta_daily_ridership_dictionary.csv", "logistics", [
            field("Date", "date", "date"),
            field("Transit Mode", "category", "string"),
            field("Ridership", "quantity", "number", "sum"),
        ])
        messages.append("prepared logistics/mta_daily_ridership.csv")
    nyc = root / "evals/datasets/logistics/NYC Accidents 2020.csv"
    if nyc.exists():
        df = read_csv_any(nyc, nrows=DEFAULT_MAX_ROWS)
        df["Date"] = df["CRASH DATE"]
        df["City"] = df["BOROUGH"]
        df["Vehicle Type"] = df.get("VEHICLE TYPE CODE 1")
        df["Accident Count"] = 1
        write_snapshot(df, root / "evals/datasets/logistics/nyc_traffic_accidents.csv")
        write_dictionary(root / "evals/dictionaries/logistics/nyc_traffic_accidents_dictionary.csv", "logistics", [
            field("Date", "date", "date"),
            field("City", "city", "string"),
            field("Vehicle Type", "category", "string"),
            field("Accident Count", "quantity", "number", "sum"),
        ])
        messages.append("prepared logistics/nyc_traffic_accidents.csv")
    return messages or ["skip logistics: source files missing"]


def prepare_education(root: Path) -> str:
    source = root / "evals/datasets/education/student-mat.csv"
    if not source.exists():
        return "skip education: source missing"
    df = read_csv_any(source, sep=";")
    write_snapshot(df, root / "evals/datasets/education/uci_student_performance.csv")
    write_dictionary(root / "evals/dictionaries/education/uci_student_performance_dictionary.csv", "education", [
        field("school", "department", "string"),
        field("sex", "segment", "string", sensitive=True),
        field("age", "customer", "number", "mean", sensitive=True),
        field("studytime", "frequency", "number", "mean"),
        field("absences", "quantity", "number", "sum"),
        field("G3", "target", "number", "mean"),
    ])
    return "prepared education/uci_student_performance.csv"


def prepare_generic(root: Path) -> str:
    df = pd.DataFrame([
        {"id": 1, "Country": "Britain", "Neighbor": "Ireland", "Population": 67},
        {"id": 2, "Country": "France", "Neighbor": "Germany", "Population": 68},
        {"id": 3, "Country": "Germany", "Neighbor": "France", "Population": 83},
        {"id": 4, "Country": "Italy", "Neighbor": "France", "Population": 60},
    ])
    write_snapshot(df, root / "evals/datasets/generic/frictionless_countries.csv")
    write_dictionary(root / "evals/dictionaries/generic/frictionless_countries_dictionary.csv", "generic", [
        field("Country", "country", "string"),
        field("Population", "quantity", "number", "sum"),
    ])
    return "prepared generic/frictionless_countries.csv"


def prepare_product(root: Path) -> str:
    source = root / "evals/datasets/product/auto-mpg.csv"
    if not source.exists():
        return "skip product: source missing"
    df = read_csv_any(source)
    df["horsepower"] = numeric(df["horsepower"].replace("?", pd.NA))
    df["Manufacturer"] = df["car name"].astype(str).str.split().str[0].str.title()
    df["Model Date"] = (1900 + numeric(df["model year"]).fillna(0).astype(int)).astype(str) + "-01-01"
    write_snapshot(df, root / "evals/datasets/product/automotive_fuel_economy.csv")
    write_dictionary(root / "evals/dictionaries/product/automotive_fuel_economy_dictionary.csv", "product", [
        field("Model Date", "date", "date"),
        field("Manufacturer", "category", "string"),
        field("mpg", "quantity", "number", "mean"),
    ])
    return "prepared product/automotive_fuel_economy.csv"


def prepare_all(root: Path) -> list[str]:
    messages: list[str] = []
    for prepare in [
        prepare_online_retail,
        prepare_fuzzy_factory,
        prepare_northwind,
        prepare_bank_marketing,
        prepare_education,
        prepare_generic,
        prepare_product,
    ]:
        try:
            messages.append(prepare(root))
        except Exception as exc:
            messages.append(f"error {prepare.__name__}: {exc}")
    for prepare_many in [prepare_finance, prepare_surveys, prepare_logistics]:
        try:
            messages.extend(prepare_many(root))
        except Exception as exc:
            messages.append(f"error {prepare_many.__name__}: {exc}")
    return messages


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare normalized local snapshots for Phase U5 eval.")
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    for message in prepare_all(root):
        print(message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
