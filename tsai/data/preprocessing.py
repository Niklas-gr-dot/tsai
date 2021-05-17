# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/003_data.preprocessing.ipynb (unless otherwise specified).

__all__ = ['ToNumpyCategory', 'OneHot', 'Nan2Value', 'TSStandardize', 'TSNormalize', 'TSClipOutliers', 'TSClip',
           'TSRobustScale', 'TSDiff', 'TSLog', 'TSLogReturn', 'TSAdd', 'ReLabeler']

# Cell
from ..imports import *
from ..utils import *
from .external import *
from .core import *

# Cell
class ToNumpyCategory(Transform):
    "Categorize a numpy batch"
    order = 90

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def encodes(self, o: np.ndarray):
        self.type = type(o)
        self.cat = Categorize()
        self.cat.setup(o)
        self.vocab = self.cat.vocab
        return np.asarray(stack([self.cat(oi) for oi in o]))

    def decodes(self, o: (np.ndarray, torch.Tensor)):
        return stack([self.cat.decode(oi) for oi in o])

# Cell
class OneHot(Transform):
    "One-hot encode/ decode a batch"
    order = 90
    def __init__(self, n_classes=None, **kwargs):
        self.n_classes = n_classes
        super().__init__(**kwargs)
    def encodes(self, o: torch.Tensor):
        if not self.n_classes: self.n_classes = len(np.unique(o))
        return torch.eye(self.n_classes)[o]
    def encodes(self, o: np.ndarray):
        o = ToNumpyCategory()(o)
        if not self.n_classes: self.n_classes = len(np.unique(o))
        return np.eye(self.n_classes)[o]
    def decodes(self, o: torch.Tensor): return torch.argmax(o, dim=-1)
    def decodes(self, o: np.ndarray): return np.argmax(o, axis=-1)

# Cell
class Nan2Value(Transform):
    "Replaces any nan values by a predefined value"
    order = 90
    def __init__(self, value=0, median=True, by_sample_and_var=False): # set to True when torch 1.8.0 is supported by fastai
        store_attr()
    def encodes(self, o:TSTensor):
        mask = torch.isnan(o)
        if mask.any():
            if not self.median:
                median = self.value
                o[mask] = median
                # return torch.nan_to_num(o, nan=self.value) # available in torch 1.8.0
            else:
                if self.by_sample_and_var:
                    median = torch.median(o, dim=2, keepdim=True)[0].repeat(1, 1, o.shape[-1])
                    # median = torch.nanmedian(o, dim=2, keepdim=True)[0].repeat(1, 1, o.shape[-1]) # available in torch 1.8.0
                    o[mask] = median[mask]
                else:
                    median = torch.median(o)
                    # median = torch.nanmedian(o) # available in torch 1.8.0
                    o[mask] = median
                # Just in case any sample or var values are all nan
                mask = torch.isnan(o)
                if mask.any():
                    o[mask] = self.value
        return o

# Cell
class TSStandardize(Transform):
    "Standardizes batch of type `TSTensor`"
    parameters, order = L('mean', 'std'), 90
    def __init__(self, mean=None, std=None, by_sample=False, by_var=False, by_step=False, eps=1e-8, verbose=False):
        self.mean = tensor(mean) if mean is not None else None
        self.std = tensor(std) if std is not None else None
        self.eps = eps
        self.by_sample, self.by_var, self.by_step = by_sample, by_var, by_step
        drop_axes = []
        if by_sample: drop_axes.append(0)
        if by_var and not is_listy(by_var): drop_axes.append(1)
        if by_step: drop_axes.append(2)
        self.axes = tuple([ax for ax in (0, 1, 2) if ax not in drop_axes])
        self.verbose = verbose
        if self.mean is not None or self.std is not None:
            pv(f'{self.__class__.__name__} mean={self.mean}, std={self.std}, by_sample={self.by_sample}, by_var={self.by_var}, by_step={self.by_step}\n', self.verbose)

    @classmethod
    def from_stats(cls, mean, std): return cls(mean, std)

    def setups(self, dl: DataLoader):
        if (self.mean is None or self.std is None):
            o, *_ = dl.one_batch()
            if self.by_var and is_listy(self.by_var):
                _mean = []
                _std = []
                start = 0
                for i,v in enumerate(self.by_var):
                    if is_listy(v): f = v
                    else:
                        end = start + v
                        f = slice(start, end)
                        start += v
                    repeats = len(v) if is_listy(v) else v
                    _mean.append((torch_nanmean(o[:, f], self.axes, keepdim=True)).repeat(1, repeats, 1))
                    _std.append((torch_nanstd(o[:, f], self.axes, keepdim=True) + self.eps).repeat(1, repeats, 1))
                self.mean = torch.cat(_mean, dim=1)
                self.std = torch.clamp_min(torch.cat(_std, dim=1), self.eps)
            else:
                self.mean = torch_nanmean(o, dim=self.axes, keepdim=self.axes!=())
                self.std = torch.clamp_min(torch_nanstd(o, dim=self.axes, keepdim=self.axes!=()), self.eps)
            if len(self.mean.shape) == 0:
                pv(f'{self.__class__.__name__} mean={self.mean}, std={self.std}, by_sample={self.by_sample}, by_var={self.by_var}, by_step={self.by_step}\n',
                   self.verbose)
            else:
                pv(f'{self.__class__.__name__} mean shape={self.mean.shape}, std shape={self.std.shape}, by_sample={self.by_sample}, by_var={self.by_var}, by_step={self.by_step}\n',
                   self.verbose)

    def encodes(self, o:TSTensor):
        if self.by_sample:
            if is_listy(self.by_var):
                _o = []
                start = 0
                for i,v in enumerate(self.by_var):
                    if is_listy(v): f = v
                    else:
                        end = start + v
                        f = slice(start, end)
                        start += v
                    o_mean = torch_nanmean(o[:, f], self.axes, keepdim=True)
                    o_std = torch.clamp_min(torch_nanstd(o[:, f], self.axes, keepdim=True), self.eps)
                    _o.append((o[:, f] - o_mean) / o_std)
                return torch.cat(_o, dim=1)
            else:
                self.mean = torch_nanmean(o, dim=self.axes, keepdim=self.axes!=())
                self.std = torch.clamp_min(torch_nanstd(o, dim=self.axes, keepdim=self.axes!=()), self.eps)
        return (o - self.mean) / self.std

    def decodes(self, o:TSTensor):
        if self.mean is None or self.std is None: return o
        return o * self.std + self.mean

    def __repr__(self): return f'{self.__class__.__name__}(by_sample={self.by_sample}, by_var={self.by_var}, by_step={self.by_step})'

# Cell
@patch
def mul_min(x:(torch.Tensor, TSTensor, NumpyTensor), axes=(), keepdim=False):
    if axes == (): return retain_type(x.min(), x)
    axes = reversed(sorted(axes if is_listy(axes) else [axes]))
    min_x = x
    for ax in axes: min_x, _ = min_x.min(ax, keepdim)
    return retain_type(min_x, x)


@patch
def mul_max(x:(torch.Tensor, TSTensor, NumpyTensor), axes=(), keepdim=False):
    if axes == (): return retain_type(x.max(), x)
    axes = reversed(sorted(axes if is_listy(axes) else [axes]))
    max_x = x
    for ax in axes: max_x, _ = max_x.max(ax, keepdim)
    return retain_type(max_x, x)


class TSNormalize(Transform):
    "Normalizes batch of type `TSTensor`"
    parameters, order = L('min', 'max'), 90

    def __init__(self, min=None, max=None, range=(-1, 1), by_sample=False, by_var=False, by_step=False, verbose=False):
        self.min = tensor(min) if min is not None else None
        self.max = tensor(max) if max is not None else None
        self.range_min, self.range_max = range
        self.by_sample, self.by_var, self.by_step = by_sample, by_var, by_step
        drop_axes = []
        if by_sample: drop_axes.append(0)
        if by_var: drop_axes.append(1)
        if by_step: drop_axes.append(2)
        self.axes = tuple([ax for ax in (0, 1, 2) if ax not in drop_axes])
        self.verbose = verbose
        if self.min is not None or self.max is not None:
            pv(f'{self.__class__.__name__} min={self.min}, max={self.max}, by_sample={self.by_sample}, by_var={self.by_var}, by_step={self.by_step}\n', self.verbose)

    @classmethod
    def from_stats(cls, min, max, range_min=0, range_max=1): return cls(min, max, self.range_min, self.range_max)

    def setups(self, dl: DataLoader):
        if self.min is None or self.max is None:
            x, *_ = dl.one_batch()
            self.min, self.max = x.mul_min(self.axes, keepdim=self.axes!=()), x.mul_max(self.axes, keepdim=self.axes!=())
            if len(self.min.shape) == 0:
                pv(f'{self.__class__.__name__} min={self.min}, max={self.max}, by_sample={self.by_sample}, by_var={self.by_var}, by_step={self.by_step}\n', self.verbose)
            else:
                pv(f'{self.__class__.__name__} min shape={self.min.shape}, max shape={self.max.shape}, by_sample={self.by_sample}, by_var={self.by_var}, by_step={self.by_step}\n',
                   self.verbose)

    def encodes(self, o:TSTensor):
        if self.by_sample: self.min, self.max = o.mul_min(self.axes, keepdim=self.axes!=()), o.mul_max(self.axes, keepdim=self.axes!=())
        return torch.clamp(((o - self.min) / (self.max - self.min)) * (self.range_max - self.range_min) + self.range_min,
                           self.range_min, self.range_max)

    def __repr__(self): return f'{self.__class__.__name__}(by_sample={self.by_sample}, by_var={self.by_var}, by_step={self.by_step})'

# Cell
class TSClipOutliers(Transform):
    "Clip outliers batch of type `TSTensor` based on the IQR"
    parameters, order = L('min', 'max'), 90
    def __init__(self, min=None, max=None, by_sample=False, by_var=False, verbose=False):
        self.su = (min is None or max is None) and not by_sample
        self.min = tensor(min) if min is not None else tensor(-np.inf)
        self.max = tensor(max) if max is not None else tensor(np.inf)
        self.by_sample, self.by_var = by_sample, by_var
        if by_sample and by_var: self.axis = (2)
        elif by_sample: self.axis = (1, 2)
        elif by_var: self.axis = (0, 2)
        else: self.axis = None
        self.verbose = verbose
        if min is not None or max is not None:
            pv(f'{self.__class__.__name__} min={min}, max={max}\n', self.verbose)

    def setups(self, dl: DataLoader):
        if self.su:
            o, *_ = dl.one_batch()
            min, max = get_outliers_IQR(o, self.axis)
            self.min, self.max = tensor(min), tensor(max)
            if self.axis is None: pv(f'{self.__class__.__name__} min={self.min}, max={self.max}, by_sample={self.by_sample}, by_var={self.by_var}\n',
                                     self.verbose)
            else: pv(f'{self.__class__.__name__} min={self.min.shape}, max={self.max.shape}, by_sample={self.by_sample}, by_var={self.by_var}\n',
                     self.verbose)
            self.su = False

    def encodes(self, o:TSTensor):
        if self.axis is None: return torch.clamp(o, self.min, self.max)
        elif self.by_sample:
            min, max = get_outliers_IQR(o, axis=self.axis)
            self.min, self.max = o.new(min), o.new(max)
        return torch_clamp(o, self.min, self.max)

    def __repr__(self): return f'{self.__class__.__name__}(by_sample={self.by_sample}, by_var={self.by_var})'

# Cell
class TSClip(Transform):
    "Clip  batch of type `TSTensor`"
    parameters, order = L('min', 'max'), 90
    def __init__(self, min=-6, max=6):
        self.min = torch.tensor(min)
        self.max = torch.tensor(max)

    def encodes(self, o:TSTensor):
        return torch.clamp(o, self.min, self.max)
    def __repr__(self): return f'{self.__class__.__name__}(min={self.min}, max={self.max})'

# Cell
class TSRobustScale(Transform):
    r"""This Scaler removes the median and scales the data according to the quantile range (defaults to IQR: Interquartile Range)"""
    parameters, order = L('median', 'min', 'max'), 90
    def __init__(self, median=None, min=None, max=None, by_sample=False, by_var=False, verbose=False):
        self.su = (median is None or min is None or max is None) and not by_sample
        self.median = tensor(median) if median is not None else tensor(0)
        self.min = tensor(min) if min is not None else tensor(-np.inf)
        self.max = tensor(max) if max is not None else tensor(np.inf)
        self.by_sample, self.by_var = by_sample, by_var
        if by_sample and by_var: self.axis = (2)
        elif by_sample: self.axis = (1, 2)
        elif by_var: self.axis = (0, 2)
        else: self.axis = None
        self.verbose = verbose
        if median is not None or min is not None or max is not None:
            pv(f'{self.__class__.__name__} median={median} min={min}, max={max}\n', self.verbose)

    def setups(self, dl: DataLoader):
        if self.su:
            o, *_ = dl.one_batch()
            median = get_percentile(o, 50, self.axis)
            min, max = get_outliers_IQR(o, self.axis)
            self.median, self.min, self.max = tensor(median), tensor(min), tensor(max)
            if self.axis is None: pv(f'{self.__class__.__name__} median={self.median} min={self.min}, max={self.max}, by_sample={self.by_sample}, by_var={self.by_var}\n',
                                     self.verbose)
            else: pv(f'{self.__class__.__name__} median={self.median.shape} min={self.min.shape}, max={self.max.shape}, by_sample={self.by_sample}, by_var={self.by_var}\n',
                     self.verbose)
            self.su = False

    def encodes(self, o:TSTensor):
        if self.by_sample:
            median = get_percentile(o, 50, self.axis)
            min, max = get_outliers_IQR(o, axis=self.axis)
            self.median, self.min, self.max = o.new(median), o.new(min), o.new(max)
        return (o - self.median) / (self.max - self.min)

    def __repr__(self): return f'{self.__class__.__name__}(by_sample={self.by_sample}, by_var={self.by_var})'

# Cell
class TSDiff(Transform):
    "Differences batch of type `TSTensor`"
    order = 90
    def __init__(self, lag=1, pad=True):
        self.lag, self.pad = lag, pad

    def encodes(self, o:TSTensor):
        return torch_diff(o, lag=self.lag, pad=self.pad)

    def __repr__(self): return f'{self.__class__.__name__}(lag={self.lag}, pad={self.pad})'

# Cell
class TSLog(Transform):
    "Log transforms batch of type `TSTensor`. For positive values only"
    order = 90

    def encodes(self, o:TSTensor): return torch.log(o)
    def decodes(self, o:TSTensor): return torch.exp(o)
    def __repr__(self): return f'{self.__class__.__name__}()'

# Cell
class TSLogReturn(Transform):
    "Calculates log-return of batch of type `TSTensor`. For positive values only"
    order = 90
    def __init__(self, lag=1, pad=True):
        self.lag, self.pad = lag, pad

    def encodes(self, o:TSTensor):
        return torch_diff(torch.log(o), lag=self.lag, pad=self.pad)

    def __repr__(self): return f'{self.__class__.__name__}(lag={self.lag}, pad={self.pad})'

# Cell
class TSAdd(Transform):
    "Add a defined amount to each batch of type `TSTensor`."
    order = 90
    def __init__(self, add):
        self.add = add

    def encodes(self, o:TSTensor):
        return torch.add(o, self.add)
    def __repr__(self): return f'{self.__class__.__name__}(lag={self.lag}, pad={self.pad})'

# Cell
def ReLabeler(cm):
    r"""Changes the labels in a dataset based on a dictionary (class mapping)
        Args:
            cm = class mapping dictionary
    """
    def _relabel(y):
        obj = len(set([len(listify(v)) for v in cm.values()])) > 1
        keys = cm.keys()
        if obj:
            new_cm = {k:v for k,v in zip(keys, [listify(v) for v in cm.values()])}
            return np.array([new_cm[yi] if yi in keys else listify(yi) for yi in y], dtype=object).reshape(*y.shape)
        else:
            new_cm = {k:v for k,v in zip(keys, [listify(v) for v in cm.values()])}
            return np.array([new_cm[yi] if yi in keys else listify(yi) for yi in y]).reshape(*y.shape)
    return _relabel