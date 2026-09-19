import pandas as pd


def is_date_like(series):
    """
    Check whether a column mostly contains valid dates.
    """

    converted = pd.to_datetime(
        series,
        errors="coerce",
        format="mixed"
    )

    valid_dates = converted.notna().sum()
    total_values = series.notna().sum()

    if total_values == 0:
        return False

    percentage = valid_dates / total_values

    return percentage >= 0.8


def is_categorical(series):
    """
    Check whether a text column behaves like a category column.
    """

    if not pd.api.types.is_string_dtype(series):
        return False

    total_values = series.notna().sum()

    if total_values == 0:
        return False

    unique_values = series.nunique()

    unique_ratio = unique_values / total_values

    return (
        unique_values <= 20
        or unique_ratio <= 0.05
    )


def detect_column_type(series):
    """
    Detect the general type of a column.
    """

    if pd.api.types.is_numeric_dtype(series):
        return "Numeric"

    elif is_date_like(series):
        return "Date"

    elif is_categorical(series):
        return "Categorical"

    else:
        return "Text"


def analyze_data(df):
    """
    Analyze the complete dataset.
    """

    analysis = {
        "rows": len(df),
        "columns": len(df.columns),
        "column_info": {}
    }

    for column in df.columns:

        dtype = df[column].dtype
        missing = int(df[column].isna().sum())
        unique = int(df[column].nunique())

        column_type = detect_column_type(
            df[column]
        )

        analysis["column_info"][column] = {
            "type": column_type,
            "pandas_dtype": str(dtype),
            "missing": missing,
            "unique": unique
        }

    return analysis


if __name__ == "__main__":

    df = pd.read_csv(
        "data/client_sales_data_messy.csv"
    )

    result = analyze_data(df)

    print("===== DATA ANALYSIS =====")

    print("Rows:", result["rows"])
    print("Columns:", result["columns"])

    for column, info in result["column_info"].items():

        print(f"\nColumn: {column}")
        print("Type:", info["type"])
        print("Pandas dtype:", info["pandas_dtype"])
        print("Missing:", info["missing"])
        print("Unique:", info["unique"])