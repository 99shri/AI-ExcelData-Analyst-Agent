import pandas as pd
import numpy as np


class ExcelAnalyzer:

    def __init__(self, file_path):
        self.file_path = file_path
        self.df = self._load_file()

    # -----------------------------
    # LOAD DATA
    # -----------------------------

    def _load_file(self):

        if self.file_path.endswith(".csv"):
            return pd.read_csv(self.file_path)

        elif self.file_path.endswith(".xlsx"):
            return pd.read_excel(self.file_path)

        elif self.file_path.endswith(".xls"):
            return pd.read_excel(self.file_path)

        else:
            raise ValueError(
                "Unsupported file format. Use CSV, XLSX or XLS."
            )

    # -----------------------------
    # BASIC SUMMARY
    # -----------------------------

    def get_summary(self):

        return {
            "rows": int(self.df.shape[0]),
            "columns": int(self.df.shape[1]),
            "duplicate_rows": int(self.df.duplicated().sum()),
            "missing_cells": int(self.df.isna().sum().sum()),
        }

    # -----------------------------
    # COLUMN INFORMATION
    # -----------------------------

    def get_column_info(self):

        result = []

        for column in self.df.columns:

            result.append({
                "column": column,
                "data_type": str(self.df[column].dtype),
                "missing": int(self.df[column].isna().sum()),
                "unique_values": int(self.df[column].nunique()),
            })

        return result

    # -----------------------------
    # NUMERIC STATISTICS
    # -----------------------------

    def get_numeric_summary(self):

        numeric_df = self.df.select_dtypes(
            include=np.number
        )

        if numeric_df.empty:
            return {}

        return numeric_df.describe().round(2).to_dict()

    # -----------------------------
    # OUTLIER DETECTION
    # -----------------------------

    def detect_outliers(self):

        numeric_df = self.df.select_dtypes(
            include=np.number
        )

        result = {}

        for column in numeric_df.columns:

            q1 = numeric_df[column].quantile(0.25)
            q3 = numeric_df[column].quantile(0.75)

            iqr = q3 - q1

            lower = q1 - 1.5 * iqr
            upper = q3 + 1.5 * iqr

            count = (
                (numeric_df[column] < lower) |
                (numeric_df[column] > upper)
            ).sum()

            result[column] = {
                "outliers": int(count),
                "lower_limit": round(float(lower), 2),
                "upper_limit": round(float(upper), 2)
            }

        return result

    # -----------------------------
    # DATA QUALITY SCORE
    # -----------------------------

    def get_quality_score(self):

        total_cells = self.df.shape[0] * self.df.shape[1]

        if total_cells == 0:
            return 0

        missing = self.df.isna().sum().sum()
        duplicates = self.df.duplicated().sum()

        missing_penalty = (missing / total_cells) * 50

        duplicate_penalty = (
            duplicates / max(len(self.df), 1)
        ) * 30

        score = 100 - missing_penalty - duplicate_penalty

        return round(max(score, 0), 2)

    # -----------------------------
    # AUTOMATIC KPI DETECTION
    # -----------------------------

    def detect_kpis(self):

        kpis = []

        numeric_columns = self.df.select_dtypes(
            include=np.number
        ).columns

        for column in numeric_columns:

            series = self.df[column].dropna()

            if len(series) == 0:
                continue

            kpis.append({
                "metric": column,
                "sum": round(float(series.sum()), 2),
                "average": round(float(series.mean()), 2),
                "minimum": round(float(series.min()), 2),
                "maximum": round(float(series.max()), 2)
            })

        return kpis

    # -----------------------------
    # COMPLETE PROFILE
    # -----------------------------

    def generate_profile(self):

        return {

            "basic_summary": self.get_summary(),

            "column_information": self.get_column_info(),

            "numeric_statistics": self.get_numeric_summary(),

            "outliers": self.detect_outliers(),

            "quality_score": self.get_quality_score(),

            "kpis": self.detect_kpis()
        }

    # -----------------------------
    # CALCULATIONS
    # -----------------------------

    def calculate(self, column, operation):

        if column not in self.df.columns:
            return f"Column '{column}' not found."

        series = self.df[column]

        if operation == "sum":
            return float(series.sum())

        elif operation == "average":
            return float(series.mean())

        elif operation == "minimum":
            return float(series.min())

        elif operation == "maximum":
            return float(series.max())

        elif operation == "count":
            return int(series.count())

        else:
            return "Unsupported operation."

    # -----------------------------
    # TOP VALUES
    # -----------------------------

    def get_top_values(self, column, n=5):

        if column not in self.df.columns:
            return f"Column '{column}' not found."

        return (
            self.df[column]
            .value_counts()
            .head(n)
            .to_dict()
        )

    # -----------------------------
    # FILTER DATA
    # -----------------------------

    def filter_data(self, column, value):

        if column not in self.df.columns:
            return f"Column '{column}' not found."

        result = self.df[
            self.df[column].astype(str).str.lower()
            == str(value).lower()
        ]

        return result.head(20).to_dict(
            orient="records"
        )