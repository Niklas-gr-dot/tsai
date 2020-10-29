# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/007_metrics.ipynb (unless otherwise specified).

__all__ = ['MatthewsCorrCoef']

# Cell
from .imports import *
from fastai.metrics import *

# Cell
def MatthewsCorrCoef(axis=-1, sample_weight=None):
    "Matthews correlation coefficient for binary classification problems"
    return skm_to_fastai(skm.matthews_corrcoef, axis=axis, sample_weight=sample_weight)