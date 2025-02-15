# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring

from __future__ import annotations

import streamlit as st
import pandas as pd
from pandas.api.types import (
    CategoricalDtype,
    is_datetime64_any_dtype,
    is_numeric_dtype,
    is_object_dtype,
)
from streamlit_extras.row import row  # type: ignore


class DataFrameFilter:
    # pylint: disable=too-few-public-methods

    def __init__(self, df: pd.DataFrame) -> None:
        self._df = df.copy()
        self._filters: list[str] = []
        modify = st.toggle("Add filters")
        if modify:
            self._convert_datetimes()
            self._set_filters()

    def _set_filters(self) -> None:
        modification_container = st.container()
        with modification_container:
            to_filter_columns = st.multiselect("Filter dataframe on", self._df.columns)
            rows = row(2)
            for column in to_filter_columns:
                # Treat columns with < 10 unique values as categorical
                if (
                    isinstance(self._df[column].dtype, CategoricalDtype)
                    or self._df[column].nunique() < 10
                ):
                    user_cat_input = rows.multiselect(
                        f"Values for {column}",
                        self._df[column].unique(),
                        default=list(self._df[column].unique()),
                    )
                    self._filters.append(
                        "||".join(
                            [f"record['{column}'] == '{cat}'" for cat in user_cat_input]
                        )
                    )
                elif is_numeric_dtype(self._df[column]):
                    _min = float(self._df[column].min())
                    _max = float(self._df[column].max())
                    step = (_max - _min) / 100
                    user_num_input = rows.slider(
                        f"Values for {column}",
                        min_value=_min,
                        max_value=_max,
                        value=(_min, _max),
                        step=step,
                    )
                    self._filters.append(
                        f"record['{column}'] >= {user_num_input[0]} "
                        f"&& record['{column}'] <= {user_num_input[1]}"
                    )
                elif is_datetime64_any_dtype(self._df[column]):
                    user_date_input = rows.date_input(
                        f"Values for {column}",
                        value=(
                            self._df[column].min(),
                            self._df[column].max(),
                        ),
                    )
                    if len(user_date_input) == 2:
                        user_date_input = tuple(map(pd.to_datetime, user_date_input))
                        start_date, end_date = user_date_input
                        # self._df = self._df.loc[self._df[column].between(start_date, end_date)]
                        self._filters.append(
                            f"record['{column}'] <= '{end_date}' "
                            f"&& record['{column}'] >= '{start_date}'"
                        )
                else:
                    user_text_input = rows.text_input(
                        f"Substring or regex in {column}",
                    )
                    if user_text_input:
                        self._filters.append(
                            f"record['{column}'].includes('{user_text_input}')"
                        )
                        # self._df = self._df[
                        #     self._df[column].astype(str).str.contains(user_text_input)
                        # ]

                    # raise NotImplementedError("Cannot filter on this column currently")

        filters_wrapped = [f"({_f})" for _f in self._filters]
        if st.button("Update data"):
            st.session_state["filters"] = (
                " && ".join(filters_wrapped) if filters_wrapped else None
            )

    def _convert_datetimes(self) -> None:
        # Try to convert datetimes into a standard format (datetime, no timezone)
        for col in self._df.columns:
            if is_object_dtype(self._df[col]):
                try:
                    self._df[col] = pd.to_datetime(self._df[col])
                except Exception:  # pylint: disable=broad-exception-caught
                    pass

            if is_datetime64_any_dtype(self._df[col]):
                self._df[col] = self._df[col].dt.tz_localize(None)
