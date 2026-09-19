import pandas as pd


def validate_data(df):
    """
    Perform general validation checks.
    """

    duplicates = int(
        df.duplicated().sum()
    )

    invalid_quantity = 0
    invalid_discount = 0
    negative_revenue = 0

    if "Quantity" in df.columns:

        invalid_quantity = int(
            (df["Quantity"] <= 0).sum()
        )

    if "Discount" in df.columns:

        invalid_discount = int(
            (df["Discount"] > 1).sum()
        )

    if "Revenue" in df.columns:

        negative_revenue = int(
            (df["Revenue"] < 0).sum()
        )

    invalid_dates = {}

    for column in df.columns:

        if pd.api.types.is_datetime64_any_dtype(
            df[column]
        ):

            invalid_dates[column] = int(
                df[column].isna().sum()
            )

    passed = (
        duplicates == 0
        and invalid_quantity == 0
        and invalid_discount == 0
        and negative_revenue == 0
        and all(
            value == 0
            for value in invalid_dates.values()
        )
    )

    return {
        "duplicates": duplicates,
        "invalid_quantity": invalid_quantity,
        "invalid_discount": invalid_discount,
        "negative_revenue": negative_revenue,
        "invalid_dates": invalid_dates,
        "passed": passed
    }


def check_missing_values(df):
    """
    Find missing values in every column.
    """

    missing = df.isna().sum()

    return {
        column: int(value)
        for column, value in missing.items()
        if value > 0
    }


def create_review_report(df):
    """
    Create a list of issues that need human review.
    """

    report = []

    missing = check_missing_values(df)

    for column, count in missing.items():

        report.append({
            "column": column,
            "issue": "Missing values",
            "count": count
        })

    return report


def validate_revenue(df):
    """
    Check whether Revenue matches:

    Quantity × Unit_Price × (1 - Discount)
    """

    required_columns = [
        "Quantity",
        "Unit_Price",
        "Discount",
        "Revenue"
    ]

    if not all(
        column in df.columns
        for column in required_columns
    ):
        return {
            "checked": False,
            "mismatches": 0,
            "passed": True
        }

    expected_revenue = (
        df["Quantity"]
        * df["Unit_Price"]
        * (1 - df["Discount"])
    )

    mismatch = (
        (
            df["Revenue"]
            - expected_revenue
        ).abs()
        > 0.01
    )

    mismatch_count = int(
        mismatch.sum()
    )

    return {
        "checked": True,
        "mismatches": mismatch_count,
        "passed": mismatch_count == 0
    }