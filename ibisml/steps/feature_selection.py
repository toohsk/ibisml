from __future__ import annotations

from typing import Any, Iterable

import ibis.expr.types as ir

from ibisml.core import Metadata, Step
from ibisml.select import SelectionType, selector


class ZeroVariance(Step):
    """A step for removing columns with zero variance.

    Parameters
    ----------
    inputs : SelectionType
        A selection of columns to analyze for zero variance.
    tolerance : int | float, optional
        Tolerance level for considering variance as zero.
        Columns with variance less than this tolerance will be removed.
        Default is 1e-4.

    Examples
    --------
    >>> import ibisml as ml

    To remove columns with zero variance:
    >>> step = ml.ZeroVariance(ml.everything())

    To remove all numeric columns with zero variance:
    >>> step = ml.ZeroVariance(ml.numeric())

    To remove all string or categorical columns with only one unique value:
    >>> step = ml.ZeroVariance(ml.nominal())
    """

    def __init__(self, inputs: SelectionType, *, tolerance: int | float = 1e-4):
        self.inputs = selector(inputs)
        self.tolerance = tolerance

    def _repr(self) -> Iterable[tuple[str, Any]]:
        yield ("", self.inputs)
        yield ("tolerance", self.tolerance)

    def fit_table(self, table: ir.Table, metadata: Metadata) -> None:
        columns = self.inputs.select_columns(table, metadata)
        cols = []
        if columns:
            aggs = []
            for name in columns:
                c = table[name]
                if isinstance(c, ir.NumericColumn):
                    # Compute variance for numeric columns
                    aggs.append(c.var().name(f"{name}_var"))
                else:
                    # Compute unique count for non-numeric columns
                    # NULL value is not counted in nunique()
                    aggs.append(c.nunique().name(f"{name}_var"))

            results = table.aggregate(aggs).execute().to_dict("records")[0]
            for name in columns:
                c = table[name]
                if isinstance(c, ir.NumericColumn):
                    # Check variance for numeric columns
                    if results[f"{name}_var"] < self.tolerance:
                        cols.append(name)
                elif results[f"{name}_var"] < 2:
                    # Check unique count for non-numeric columns
                    cols.append(name)

        self.cols_ = cols

    def transform_table(self, table: ir.Table) -> ir.Table:
        return table.drop(self.cols_)
