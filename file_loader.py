import os

import pandas as pd
import pdfplumber


def load_file(file_path, file_type=None):
    """
    Load CSV, Excel, JSON or PDF into a DataFrame.
    """

    if file_type is None:
        file_type = os.path.splitext(
            file_path
        )[1].lower()

    else:
        file_type = file_type.lower()

        if not file_type.startswith("."):
            file_type = "." + file_type

    if file_type == ".csv":

        return pd.read_csv(file_path)

    elif file_type == ".xlsx":

        return pd.read_excel(file_path)

    elif file_type == ".json":

        return pd.read_json(file_path)

    elif file_type == ".pdf":

        return load_pdf(file_path)

    else:

        raise ValueError(
            f"Unsupported file format: {file_type}"
        )


def load_pdf(file_path):
    """
    Extract tables from a PDF
    and convert them into a DataFrame.
    """

    all_rows = []

    with pdfplumber.open(file_path) as pdf:

        for page in pdf.pages:

            tables = page.extract_tables()

            for table in tables:

                if table:
                    all_rows.extend(table)

    if not all_rows:

        raise ValueError(
            "No table found in PDF"
        )

    headers = all_rows[0]

    data = all_rows[1:]

    df = pd.DataFrame(
        data,
        columns=headers
    )

    return df


if __name__ == "__main__":

    df = load_file(
        "data/messy_sales_report.pdf"
    )

    print(
        "File loaded successfully!"
    )

    print(
        "Shape:",
        df.shape
    )

    print(
        df.head()
    )