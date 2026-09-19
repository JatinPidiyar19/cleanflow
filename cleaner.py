import pandas as pd

from data_analyzer import detect_column_type


def remove_duplicates(df):
    """
    Remove completely duplicated rows.
    """

    df = df.copy()

    before = len(df)

    df = df.drop_duplicates()

    after = len(df)

    removed = before - after

    print(
        "Duplicate rows removed:",
        removed
    )

    return df, {
        "duplicates_removed": removed
    }


def standardize_text(df):
    """
    Remove extra spaces and standardize
    simple categorical text.
    """

    df = df.copy()

    standardized_columns = 0

    for column in df.columns:

        if pd.api.types.is_string_dtype(
            df[column]
        ):

            original = df[column].copy()

            # Remove spaces at beginning/end
            df[column] = (
                df[column]
                .str.strip()
            )

            unique_values = df[column].nunique()
            total_values = df[column].notna().sum()

            if total_values > 0:

                unique_ratio = (
                    unique_values / total_values
                )

                if unique_ratio <= 0.05:

                    df[column] = (
                        df[column]
                        .str.title()
                    )

            if not df[column].equals(original):
                standardized_columns += 1

    print(
        "Text columns standardized:",
        standardized_columns
    )

    return df, {
        "text_columns_standardized":
            standardized_columns
    }


def clean_dates(df):
    """
    Convert date-like columns into datetime.
    Invalid dates become NaT for review.
    """

    df = df.copy()

    invalid_dates_total = 0
    date_columns = 0

    for column in df.columns:

        column_type = detect_column_type(
            df[column]
        )

        if column_type == "Date":

            date_columns += 1

            original_missing = (
                df[column].isna().sum()
            )

            df[column] = pd.to_datetime(
                df[column],
                errors="coerce",
                format="mixed"
            )

            new_missing = (
                df[column].isna().sum()
            )

            invalid_dates = (
                new_missing - original_missing
            )

            if invalid_dates < 0:
                invalid_dates = 0

            invalid_dates_total += (
                invalid_dates
            )

            print(
                f"{column} - Invalid dates:",
                invalid_dates
            )

    return df, {
        "invalid_dates": invalid_dates_total,
        "date_columns": date_columns
    }


def analyze_numeric_columns(df):
    """
    Analyze missing numeric values.
    """

    missing_numeric = 0

    for column in df.columns:

        column_type = detect_column_type(
            df[column]
        )

        if column_type == "Numeric":

            missing = int(
                df[column].isna().sum()
            )

            if missing > 0:
                print(
                    f"{column} - Missing numeric values:",
                    missing
                )

            missing_numeric += missing

    return {
        "missing_numeric_values":
            missing_numeric
    }


def clean_invalid_values(df):
    """
    Apply domain-specific validation rules.

    Currently includes sales-data rules.
    """

    df = df.copy()

    # If this is not sales data,
    # do not apply sales-specific rules.
    if "Quantity" not in df.columns:
        return df, {
            "invalid_quantity_rows": 0,
            "invalid_discount_rows": 0,
            "negative_revenue_rows": 0,
            "rows_removed": 0
        }

    invalid_quantity = (
        df["Quantity"] <= 0
    )

    if "Discount" in df.columns:
        invalid_discount = (
            df["Discount"] > 1
        )
    else:
        invalid_discount = pd.Series(
            False,
            index=df.index
        )

    if "Revenue" in df.columns:
        negative_revenue = (
            df["Revenue"] < 0
        )
    else:
        negative_revenue = pd.Series(
            False,
            index=df.index
        )

    invalid_rows = (
        invalid_quantity
        | invalid_discount
        | negative_revenue
    )

    quantity_count = int(
        invalid_quantity.sum()
    )

    discount_count = int(
        invalid_discount.sum()
    )

    revenue_count = int(
        negative_revenue.sum()
    )

    rows_removed = int(
        invalid_rows.sum()
    )

    print(
        "Invalid quantities:",
        quantity_count
    )

    print(
        "Invalid discounts:",
        discount_count
    )

    print(
        "Negative revenue:",
        revenue_count
    )

    print(
        "Invalid rows removed:",
        rows_removed
    )

    df = df[~invalid_rows]

    return df, {
        "invalid_quantity_rows":
            quantity_count,

        "invalid_discount_rows":
            discount_count,

        "negative_revenue_rows":
            revenue_count,

        "rows_removed":
            rows_removed
    }


if __name__ == "__main__":

    df = pd.read_csv(
        "data/client_sales_data_messy.csv"
    )

    cleaned_df, duplicate_report = (
        remove_duplicates(df)
    )

    cleaned_df, text_report = (
        standardize_text(cleaned_df)
    )

    cleaned_df, date_report = (
        clean_dates(cleaned_df)
    )

    numeric_report = (
        analyze_numeric_columns(cleaned_df)
    )

    cleaned_df, invalid_report = (
        clean_invalid_values(cleaned_df)
    )

    print("\n===== CLEANING REPORT =====")

    print(duplicate_report)
    print(text_report)
    print(date_report)
    print(numeric_report)
    print(invalid_report)

    cleaned_df.to_csv(
        "data/cleaned_sales_data.csv",
        index=False
    )

    print(
        "\nCleaned file saved successfully!"
    )