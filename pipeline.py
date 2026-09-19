from file_loader import load_file

from data_analyzer import analyze_data

from cleaner import (
    remove_duplicates,
    standardize_text,
    clean_dates,
    analyze_numeric_columns,
    clean_invalid_values
)

from validator import (
    validate_data,
    check_missing_values,
    create_review_report,
    validate_revenue
)


def run_pipeline(file_path, file_type=None):
    """
    Run the complete data-cleaning pipeline.
    """

    # =====================================
    # 1. LOAD
    # =====================================

    df = load_file(
        file_path,
        file_type
    )

    original_rows = len(df)

    # =====================================
    # 2. ANALYZE
    # =====================================

    analysis = analyze_data(df)

    # =====================================
    # 3. CLEAN
    # =====================================

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
        analyze_numeric_columns(
            cleaned_df
        )
    )

    cleaned_df, invalid_report = (
        clean_invalid_values(
            cleaned_df
        )
    )

    # =====================================
    # 4. VALIDATE
    # =====================================

    validation = validate_data(
        cleaned_df
    )

    missing_values = (
        check_missing_values(
            cleaned_df
        )
    )

    review_report = (
        create_review_report(
            cleaned_df
        )
    )

    revenue_validation = (
        validate_revenue(
            cleaned_df
        )
    )

    # =====================================
    # 5. CREATE FINAL REPORT
    # =====================================

    cleaning_report = {
        **duplicate_report,
        **text_report,
        **date_report,
        **numeric_report,
        **invalid_report,

        "original_rows":
            original_rows,

        "cleaned_rows":
            len(cleaned_df),

        "missing_values":
            missing_values,

        "review_items":
            review_report,

        "validation":
            validation,

        "revenue_validation":
            revenue_validation
    }

    return cleaned_df, cleaning_report


if __name__ == "__main__":

    print(
        "===== DATA CLEANING PIPELINE ====="
    )

    cleaned_df, report = run_pipeline(
        "data/client_sales_data_messy.csv"
    )

    print(
        "\nOriginal rows:",
        report["original_rows"]
    )

    print(
        "Cleaned rows:",
        report["cleaned_rows"]
    )

    print(
        "\n===== CLEANING REPORT ====="
    )

    print(report)

    cleaned_df.to_csv(
        "data/cleaned_sales_data.csv",
        index=False
    )

    print(
        "\n===== PIPELINE COMPLETE ====="
    )