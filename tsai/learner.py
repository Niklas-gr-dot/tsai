# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/052_learner.ipynb (unless otherwise specified).

__all__ = ['load_all', 'load_learner_all', 'get_arch', 'all_archs_names', 'ts_learner', 'tsimage_learner']

# Cell
from sklearn import metrics
from .imports import *
from .utils import random_shuffle
from .data.core import *
from .data.validation import *
from .models.utils import *
from .models.InceptionTimePlus import *
from fastai.learner import *
from fastai.vision.models.all import *
from fastai.data.transforms import *
import pandas as pd
# Cell
@patch
def show_batch(self:Learner, **kwargs):
    self.dls.show_batch(**kwargs)

# Cell
@patch
def remove_all_cbs(self:Learner, max_iters=10):
    i = 0
    while len(self.cbs) > 0 and i < max_iters:
        self.remove_cbs(self.cbs)
        i += 1
    if len(self.cbs) > 0: print(f'Learner still has {len(self.cbs)} callbacks: {self.cbs}')

# Cell
@patch
def one_batch(self:Learner, i, b): # this fixes a bug that will be managed in the next release of fastai
    self.iter = i
#     b_on_device = tuple( e.to(device=self.dls.device) for e in b if hasattr(e, "to")) if self.dls.device is not None else b
    b_on_device = to_device(b, device=self.dls.device) if self.dls.device is not None else b
    self._split(b_on_device)
    self._with_events(self._do_one_batch, 'batch', CancelBatchException)

# Cell
@patch
def save_all(self:Learner, path='export', dls_fname='dls', model_fname='model', learner_fname='learner', verbose=False):
    path = Path(path)
    if not os.path.exists(path): os.makedirs(path)

    self.dls_type = self.dls.__class__.__name__
    if self.dls_type == "MixedDataLoaders":
        self.n_loaders = (len(self.dls.loaders), len(self.dls.loaders[0].loaders))
        dls_fnames = []
        for i,dl in enumerate(self.dls.loaders):
            for j,l in enumerate(dl.loaders):
                l = l.new(num_workers=1)
                torch.save(l, path/f'{dls_fname}_{i}_{j}.pth')
                dls_fnames.append(f'{dls_fname}_{i}_{j}.pth')
    else:
        dls_fnames = []
        self.n_loaders = len(self.dls.loaders)
        for i,dl in enumerate(self.dls):
            dl = dl.new(num_workers=1)
            torch.save(dl, path/f'{dls_fname}_{i}.pth')
            dls_fnames.append(f'{dls_fname}_{i}.pth')

    # Saves the model along with optimizer
    self.model_dir = path
    self.save(f'{model_fname}', with_opt=True)

    # Export learn without the items and the optimizer state for inference
    self.export(path/f'{learner_fname}.pkl')

    pv(f'Learner saved:', verbose)
    pv(f"path          = '{path}'", verbose)
    pv(f"dls_fname     = '{dls_fnames}'", verbose)
    pv(f"model_fname   = '{model_fname}.pth'", verbose)
    pv(f"learner_fname = '{learner_fname}.pkl'", verbose)


def load_all(path='export', dls_fname='dls', model_fname='model', learner_fname='learner', device=None, pickle_module=pickle, verbose=False):

    if isinstance(device, int): device = torch.device('cuda', device)
    elif device is None: device = default_device()
    if device == 'cpu': cpu = True
    else: cpu = None

    path = Path(path)
    learn = load_learner(path/f'{learner_fname}.pkl', cpu=cpu, pickle_module=pickle_module)
    learn.load(f'{model_fname}', with_opt=True, device=device)


    if learn.dls_type == "MixedDataLoaders":
        dls_fnames = []
        _dls = []
        for i in range(learn.n_loaders[0]):
            _dl = []
            for j in range(learn.n_loaders[1]):
                l = torch.load(path/f'{dls_fname}_{i}_{j}.pth', map_location=device, pickle_module=pickle_module)
                l = l.new(num_workers=0)
                l.to(device)
                dls_fnames.append(f'{dls_fname}_{i}_{j}.pth')
                _dl.append(l)
            _dls.append(MixedDataLoader(*_dl, path=learn.dls.path, device=device, shuffle=l.shuffle))
        learn.dls = MixedDataLoaders(*_dls, path=learn.dls.path, device=device)

    else:
        loaders = []
        dls_fnames = []
        for i in range(learn.n_loaders):
            dl = torch.load(path/f'{dls_fname}_{i}.pth', map_location=device, pickle_module=pickle_module)
            dl = dl.new(num_workers=0)
            dl.to(device)
            first(dl)
            loaders.append(dl)
            dls_fnames.append(f'{dls_fname}_{i}.pth')
        learn.dls = type(learn.dls)(*loaders, path=learn.dls.path, device=device)


    pv(f'Learner loaded:', verbose)
    pv(f"path          = '{path}'", verbose)
    pv(f"dls_fname     = '{dls_fnames}'", verbose)
    pv(f"model_fname   = '{model_fname}.pth'", verbose)
    pv(f"learner_fname = '{learner_fname}.pkl'", verbose)
    return learn

load_learner_all = load_all

def get_metrics(data):
    print("MEEETRICS", data)
    print("TYYYYYPE", type(data))
    df = pd.DataFrame(data)

    df.to_csv('/gdrive/MyDrive/Masterthesis/LSTM/Results/Results LSTM FCN.csv', mode= 'a')
    print(df)

# Cell
@patch
@delegates(subplots)
def plot_metrics(self: Recorder, nrows=None, ncols=None, figsize=None, final_losses=True, perc=.5, **kwargs):

    n_values = len(self.recorder.values)
    if n_values < 2:
        print('not enough values to plot a chart')
        return
    metrics = np.stack(self.values)
    names = self.metric_names[1:-1]
    metric_names = [m.replace("valid_", "") for m in self.metric_names[1:-1] if 'loss' not in m and 'train' not in m]
    if final_losses:
        sel_idxs = int(round(n_values * perc))
        if sel_idxs < 2:
            final_losses = False
        else:
            names = names + ['train_final_loss', 'valid_final_loss']
            self.loss_idxs = L([i for i,n in enumerate(self.metric_names[1:-1]) if 'loss' in n])
            metrics = np.concatenate([metrics, metrics[:, self.loss_idxs]], -1)

    n = int(1 + final_losses + len(self.metrics))
    if nrows is None and ncols is None:
        if n <= 3:
            nrows = 1
        else:
            nrows = int(math.sqrt(n))
        ncols = int(np.ceil(n / nrows))
    elif nrows is None: nrows = int(np.ceil(n / ncols))
    elif ncols is None: ncols = int(np.ceil(n / nrows))
    figsize = figsize or (ncols * 6 + ncols - 1, nrows * 4 + nrows - 1)
    fig, axs = subplots(nrows, ncols, figsize=figsize, **kwargs)
    axs = axs.flatten()[:n]
    
    for i,name in enumerate(names):
        xs = np.arange(0, len(metrics))
        if name in ['train_loss', 'valid_loss']:
            ax_idx = 0
            m = metrics[:,i]
            title = 'losses'
        elif name in ['train_final_loss', 'valid_final_loss']:
            ax_idx = 1
            m = metrics[-sel_idxs:,i]
            xs = xs[-sel_idxs:]
            title = 'final losses'
        else:
            ax_idx = metric_names.index(name.replace("valid_", "").replace("train_", "")) + 1 + final_losses
            m = metrics[:,i]
            title = name.replace("valid_", "").replace("train_", "")
        if 'train' in name:
            color = '#1f77b4'
            label = 'train'
        else:
            color = '#ff7f0e'
            label = 'valid'
            axs[ax_idx].grid(color='gainsboro', linewidth=.5)
        axs[ax_idx].plot(xs, m, color=color, label=label)
        axs[ax_idx].set_xlim(xs[0], xs[-1])
        axs[ax_idx].legend(loc='best')
        axs[ax_idx].set_title(title)
    plt.show()
    return print(metrics) #get_metrics(metrics)


@patch
@delegates(subplots)
def plot_metrics(self: Learner, **kwargs):
    self.recorder.plot_metrics(**kwargs)

# Cell
all_archs_names = ['FCN', 'FCNPlus', 'InceptionTime', 'InceptionTimePlus', 'InCoordTime', 'XCoordTime', 'InceptionTimePlus17x17', 'InceptionTimePlus32x32',
                   'InceptionTimePlus47x47', 'InceptionTimePlus62x62', 'InceptionTimeXLPlus', 'MultiInceptionTimePlus', 'MiniRocketClassifier',
                   'MiniRocketRegressor', 'MiniRocketVotingClassifier', 'MiniRocketVotingRegressor', 'MiniRocketFeaturesPlus', 'MiniRocketPlus',
                   'MiniRocketHead', 'InceptionRocketFeaturesPlus', 'InceptionRocketPlus', 'MLP', 'MultiInputNet', 'OmniScaleCNN', 'RNN', 'LSTM', 'GRU',
                   'RNNPlus', 'LSTMPlus', 'GRUPlus', 'RNN_FCN', 'LSTM_FCN', 'GRU_FCN', 'MRNN_FCN', 'MLSTM_FCN', 'MGRU_FCN', 'ROCKET', 'RocketClassifier',
                   'RocketRegressor', 'ResCNN', 'ResNet', 'ResNetPlus', 'TCN', 'TSPerceiver', 'TST', 'TSTPlus', 'MultiTSTPlus', 'TSiTPlus', 'TSiTPlus',
                   'TabFusionTransformer', 'TSTabFusionTransformer', 'TabModel', 'TabTransformer', 'TransformerModel', 'XCM', 'XCMPlus', 'xresnet1d18',
                   'xresnet1d34', 'xresnet1d50', 'xresnet1d101', 'xresnet1d152', 'xresnet1d18_deep', 'xresnet1d34_deep', 'xresnet1d50_deep',
                   'xresnet1d18_deeper', 'xresnet1d34_deeper', 'xresnet1d50_deeper', 'XResNet1dPlus', 'xresnet1d18plus', 'xresnet1d34plus',
                   'xresnet1d50plus', 'xresnet1d101plus', 'xresnet1d152plus', 'xresnet1d18_deepplus', 'xresnet1d34_deepplus', 'xresnet1d50_deepplus',
                   'xresnet1d18_deeperplus', 'xresnet1d34_deeperplus', 'xresnet1d50_deeperplus', 'XceptionTime', 'XceptionTimePlus', 'mWDN']


def get_arch(arch_name):
    if arch_name == "FCN":
        from .models.FCN import FCN
        arch = FCN
    elif arch_name == "FCNPlus":
        from .models.FCNPlus import FCNPlus
        arch = FCNPlus
    elif arch_name == "InceptionTime":
        from .models.InceptionTime import InceptionTime
        arch = InceptionTime
    elif arch_name == "InceptionTimePlus":
        from .models.InceptionTimePlus import InceptionTimePlus
        arch = InceptionTimePlus
    elif arch_name == "InCoordTime":
        from .models.InceptionTimePlus import InCoordTime
        arch = InCoordTime
    elif arch_name == "XCoordTime":
        from .models.InceptionTimePlus import XCoordTime
        arch = XCoordTime
    elif arch_name == "InceptionTimePlus17x17":
        from .models.InceptionTimePlus import InceptionTimePlus17x17
        arch = InceptionTimePlus17x17
    elif arch_name == "InceptionTimePlus32x32":
        from .models.InceptionTimePlus import InceptionTimePlus32x32
        arch = InceptionTimePlus32x32
    elif arch_name == "InceptionTimePlus47x47":
        from .models.InceptionTimePlus import InceptionTimePlus47x47
        arch = InceptionTimePlus47x47
    elif arch_name == "InceptionTimePlus62x62":
        from .models.InceptionTimePlus import InceptionTimePlus62x62
        arch = InceptionTimePlus62x62
    elif arch_name == "InceptionTimeXLPlus":
        from .models.InceptionTimePlus import InceptionTimeXLPlus
        arch = InceptionTimeXLPlus
    elif arch_name == "MultiInceptionTimePlus":
        from .models.InceptionTimePlus import MultiInceptionTimePlus
        arch = MultiInceptionTimePlus
    elif arch_name == "MiniRocketClassifier":
        from .models.MINIROCKET import MiniRocketClassifier
        arch = MiniRocketClassifier
    elif arch_name == "MiniRocketRegressor":
        from .models.MINIROCKET import MiniRocketRegressor
        arch = MiniRocketRegressor
    elif arch_name == "MiniRocketVotingClassifier":
        from .models.MINIROCKET import MiniRocketVotingClassifier
        arch = MiniRocketVotingClassifier
    elif arch_name == "MiniRocketVotingRegressor":
        from .models.MINIROCKET import MiniRocketVotingRegressor
        arch = MiniRocketVotingRegressor
    elif arch_name == "MiniRocketFeaturesPlus":
        from .models.MINIROCKETPlus_Pytorch import MiniRocketFeaturesPlus
        arch = MiniRocketFeaturesPlus
    elif arch_name == "MiniRocketPlus":
        from .models.MINIROCKETPlus_Pytorch import MiniRocketPlus
        arch = MiniRocketPlus
    elif arch_name == "MiniRocketHead":
        from .models.MINIROCKETPlus_Pytorch import MiniRocketHead
        arch = MiniRocketHead
    elif arch_name == "InceptionRocketFeaturesPlus":
        from .models.MINIROCKETPlus_Pytorch import InceptionRocketFeaturesPlus
        arch = InceptionRocketFeaturesPlus
    elif arch_name == "InceptionRocketPlus":
        from .models.MINIROCKETPlus_Pytorch import InceptionRocketPlus
        arch = InceptionRocketPlus
    elif arch_name == "MLP":
        from .models.MLP import MLP
        arch = MLP
    elif arch_name == "MultiInputNet":
        from .models.MultiInputNet import MultiInputNet
        arch = MultiInputNet
    elif arch_name == "OmniScaleCNN":
        from .models.OmniScaleCNN import OmniScaleCNN
        arch = OmniScaleCNN
    elif arch_name == "RNN":
        from .models.RNN import RNN
        arch = RNN
    elif arch_name == "LSTM":
        from .models.RNN import LSTM
        arch = LSTM
    elif arch_name == "GRU":
        from .models.RNN import GRU
        arch = GRU
    elif arch_name == "RNNPlus":
        from .models.RNNPlus import RNNPlus
        arch = RNNPlus
    elif arch_name == "LSTMPlus":
        from .models.RNNPlus import LSTMPlus
        arch = LSTMPlus
    elif arch_name == "GRUPlus":
        from .models.RNNPlus import GRUPlus
        arch = GRUPlus
    elif arch_name == "RNN_FCN":
        from .models.RNN_FCN import RNN_FCN
        arch = RNN_FCN
    elif arch_name == "LSTM_FCN":
        from .models.RNN_FCN import LSTM_FCN
        arch = LSTM_FCN
    elif arch_name == "GRU_FCN":
        from .models.RNN_FCN import GRU_FCN
        arch = GRU_FCN
    elif arch_name == "MRNN_FCN":
        from .models.RNN_FCN import MRNN_FCN
        arch = MRNN_FCN
    elif arch_name == "MLSTM_FCN":
        from .models.RNN_FCN import MLSTM_FCN
        arch = MLSTM_FCN
    elif arch_name == "MGRU_FCN":
        from .models.RNN_FCN import MGRU_FCN
        arch = MGRU_FCN
    elif arch_name == "RNN_FCNPlus":
        from .models.RNN_FCNPlus import RNN_FCNPlus
        arch = RNN_FCNPlus
    elif arch_name == "LSTM_FCNPlus":
        from .models.RNN_FCNPlus import LSTM_FCNPlus
        arch = LSTM_FCNPlus
    elif arch_name == "GRU_FCNPlus":
        from .models.RNN_FCNPlus import GRU_FCNPlus
        arch = GRU_FCNPlus
    elif arch_name == "MRNN_FCNPlus":
        from .models.RNN_FCNPlus import MRNN_FCNPlus
        arch = MRNN_FCNPlus
    elif arch_name == "MLSTM_FCNPlus":
        from .models.RNN_FCNPlus import MLSTM_FCNPlus
        arch = MLSTM_FCNPlus
    elif arch_name == "MGRU_FCNPlus":
        from .models.RNN_FCNPlus import MGRU_FCNPlus
        arch = MGRU_FCNPlus
    elif arch_name == "ROCKET":
        from .models.ROCKET import ROCKET
        arch = ROCKET
    elif arch_name == "RocketClassifier":
        from .models.ROCKET import RocketClassifier
        arch = RocketClassifier
    elif arch_name == "RocketRegressor":
        from .models.ROCKET import RocketRegressor
        arch = RocketRegressor
    elif arch_name == "ResCNN":
        from .models.ResCNN import ResCNN
        arch = ResCNN
    elif arch_name == "ResNet":
        from .models.ResNet import ResNet
        arch = ResNet
    elif arch_name == "ResNetPlus":
        from .models.ResNetPlus import ResNetPlus
        arch = ResNetPlus
    elif arch_name == "TCN":
        from .models.TCN import TCN
        arch = TCN
    elif arch_name == "TSPerceiver":
        from .models.TSPerceiver import TSPerceiver
        arch = TSPerceiver
    elif arch_name == "TST":
        from .models.TST import TST
        arch = TST
    elif arch_name == "TSTPlus":
        from .models.TSTPlus import TSTPlus
        arch = TSTPlus
    elif arch_name == "MultiTSTPlus":
        from .models.TSTPlus import MultiTSTPlus
        arch = MultiTSTPlus
    elif arch_name == "TSiT":
        from .models.TSiTPlus import TSiT
        arch = TSiT
    elif arch_name == "TSiTPlus":
        from .models.TSiTPlus import TSiTPlus
        arch = TSiTPlus
    elif arch_name == "TabFusionTransformer":
        from .models.TabFusionTransformer import TabFusionTransformer
        arch = TabFusionTransformer
    elif arch_name == "TSTabFusionTransformer":
        from .models.TabFusionTransformer import TSTabFusionTransformer
        arch = TSTabFusionTransformer
    elif arch_name == "TabModel":
        from .models.TabModel import TabModel
        arch = TabModel
    elif arch_name == "TabTransformer":
        from .models.TabTransformer import TabTransformer
        arch = TabTransformer
    elif arch_name == "TransformerModel":
        from .models.TransformerModel import TransformerModel
        arch = TransformerModel
    elif arch_name == "XCM":
        from .models.XCM import XCM
        arch = XCM
    elif arch_name == "XCMPlus":
        from .models.XCMPlus import XCMPlus
        arch = XCMPlus
    elif arch_name == "XResNet1d":
        from .models.XResNet1d import XResNet1d
        arch = XResNet1d
    elif arch_name == "xresnet1d18":
        from .models.XResNet1d import xresnet1d18
        arch = xresnet1d18
    elif arch_name == "xresnet1d34":
        from .models.XResNet1d import xresnet1d34
        arch = xresnet1d34
    elif arch_name == "xresnet1d50":
        from .models.XResNet1d import xresnet1d50
        arch = xresnet1d50
    elif arch_name == "xresnet1d101":
        from .models.XResNet1d import xresnet1d101
        arch = xresnet1d101
    elif arch_name == "xresnet1d152":
        from .models.XResNet1d import xresnet1d152
        arch = xresnet1d152
    elif arch_name == "xresnet1d18_deep":
        from .models.XResNet1d import xresnet1d18_deep
        arch = xresnet1d18_deep
    elif arch_name == "xresnet1d34_deep":
        from .models.XResNet1d import xresnet1d34_deep
        arch = xresnet1d34_deep
    elif arch_name == "xresnet1d50_deep":
        from .models.XResNet1d import xresnet1d50_deep
        arch = xresnet1d50_deep
    elif arch_name == "xresnet1d18_deeper":
        from .models.XResNet1d import xresnet1d18_deeper
        arch = xresnet1d18_deeper
    elif arch_name == "xresnet1d34_deeper":
        from .models.XResNet1d import xresnet1d34_deeper
        arch = xresnet1d34_deeper
    elif arch_name == "xresnet1d50_deeper":
        from .models.XResNet1d import xresnet1d50_deeper
        arch = xresnet1d50_deeper
    elif arch_name == "XResNet1dPlus":
        from .models.XResNet1dPlus import XResNet1dPlus
        arch = XResNet1dPlus
    elif arch_name == "xresnet1d18plus":
        from .models.XResNet1dPlus import xresnet1d18plus
        arch = xresnet1d18plus
    elif arch_name == "xresnet1d34plus":
        from .models.XResNet1dPlus import xresnet1d34plus
        arch = xresnet1d34plus
    elif arch_name == "xresnet1d50plus":
        from .models.XResNet1dPlus import xresnet1d50plus
        arch = xresnet1d50plus
    elif arch_name == "xresnet1d101plus":
        from .models.XResNet1dPlus import xresnet1d101plus
        arch = xresnet1d101plus
    elif arch_name == "xresnet1d152plus":
        from .models.XResNet1dPlus import xresnet1d152plus
        arch = xresnet1d152plus
    elif arch_name == "xresnet1d18_deepplus":
        from .models.XResNet1dPlus import xresnet1d18_deepplus
        arch = xresnet1d18_deepplus
    elif arch_name == "xresnet1d34_deepplus":
        from .models.XResNet1dPlus import xresnet1d34_deepplus
        arch = xresnet1d34_deepplus
    elif arch_name == "xresnet1d50_deepplus":
        from .models.XResNet1dPlus import xresnet1d50_deepplus
        arch = xresnet1d50_deepplus
    elif arch_name == "xresnet1d18_deeperplus":
        from .models.XResNet1dPlus import xresnet1d18_deeperplus
        arch = xresnet1d18_deeperplus
    elif arch_name == "xresnet1d34_deeperplus":
        from .models.XResNet1dPlus import xresnet1d34_deeperplus
        arch = xresnet1d34_deeperplus
    elif arch_name == "xresnet1d50_deeperplus":
        from .models.XResNet1dPlus import xresnet1d50_deeperplus
        arch = xresnet1d50_deeperplus
    elif arch_name == "XceptionTime":
        from .models.XceptionTime import XceptionTime
        arch = XceptionTime
    elif arch_name == "XceptionTimePlus":
        from .models.XceptionTimePlus import XceptionTimePlus
        arch = XceptionTimePlus
    elif arch_name == "mWDN":
        from .models.mWDN import mWDN
        arch = mWDN
    else: print(f"please, confirm the name of the architecture ({arch_name})")
    assert arch.__name__ == arch_name
    return arch

class SilenceRecorder(Callback):
    learn:Learner
    def __post_init__(self):
      self.learn.recorder.silent = True
# Cell
@delegates(build_ts_model)
def ts_learner(dls, arch=None, c_in=None, c_out=None, seq_len=None, d=None, splitter=trainable_params,
               # learner args
               loss_func=None, opt_func=Adam, lr=defaults.lr, cbs=None, metrics=None, path=None,
               model_dir='models', wd=None, wd_bn_bias=False, train_bn=True, moms=(0.95,0.85,0.95), train_metrics=False,
               # other model args
               **kwargs):

    if arch is None: arch = InceptionTimePlus
    elif isinstance(arch, str): arch = get_arch(arch)
    model = build_ts_model(arch, dls=dls, c_in=c_in, c_out=c_out, seq_len=seq_len, d=d, **kwargs)
    if hasattr(model, "backbone") and hasattr(model, "head"):
        splitter = ts_splitter
    if loss_func is None:
        if hasattr(dls, 'loss_func'): loss_func = dls.loss_func
        elif hasattr(dls, 'train_ds') and hasattr(dls.train_ds, 'loss_func'): loss_func = dls.train_ds.loss_func
        elif hasattr(dls, 'cat') and not dls.cat: loss_func = MSELossFlat()

    learn = Learner(dls=dls, model=model,
                    loss_func=loss_func, opt_func=opt_func, lr=lr, cbs=cbs, metrics=metrics, path=path, splitter=splitter,
                    model_dir=model_dir, wd=wd, wd_bn_bias=wd_bn_bias, train_bn=train_bn, moms=moms,callback_fns=[SilenceRecorder] )

    if train_metrics and hasattr(learn, "recorder"):
        learn.recorder.train_metrics = True

    # keep track of args for loggers
    store_attr('arch', self=learn)

    return learn

# Cell
@delegates(build_tsimage_model)
def tsimage_learner(dls, arch=None, pretrained=False,
               # learner args
               loss_func=None, opt_func=Adam, lr=defaults.lr, cbs=None, metrics=None, path=None,
               model_dir='models', wd=None, wd_bn_bias=False, train_bn=True, moms=(0.95,0.85,0.95),
               # other model args
               **kwargs):

    if arch is None: arch = xresnet34
    elif isinstance(arch, str): arch = get_arch(arch)
    model = build_tsimage_model(arch, dls=dls, pretrained=pretrained, **kwargs)
    learn = Learner(dls=dls, model=model,
                    loss_func=loss_func, opt_func=opt_func, lr=lr, cbs=cbs, metrics=metrics, path=path,
                    model_dir=model_dir, wd=wd, wd_bn_bias=wd_bn_bias, train_bn=train_bn, moms=moms)

    # keep track of args for loggers
    store_attr('arch', self=learn)

    return learn

# Cell
@patch
def decoder(self:Learner, o): return L([self.dls.decodes(oi) for oi in o])