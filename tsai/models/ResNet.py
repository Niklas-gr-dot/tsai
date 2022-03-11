# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/101_models.ResNet.ipynb (unless otherwise specified).

__all__ = ['ResBlock', 'ResNet']

# Cell
from ..imports import *
from .layers import *

# Cell
class ResBlock(Module):
    def __init__(self, ni, nf, kss=[13,11,9,7, 5, 3,1]):
        
        self.convblock1 = ConvBlock(ni, nf, kss[0])
        self.convblock2 = ConvBlock(nf, nf, kss[1])
        self.convblock3 = ConvBlock(nf, nf, kss[2])
        self.convblock4 = ConvBlock(nf, nf, kss[3])
        self.convblock5 = ConvBlock(nf, nf, kss[4])
        self.convblock5 = ConvBlock(nf, nf, kss[5])
        self.convblock5 = ConvBlock(nf, nf, kss[6], act=None)

        # expand channels for the sum if necessary
        self.shortcut = BN1d(ni) if ni == nf else ConvBlock(ni, nf, 1, act=None)
        self.add = Add()
        self.act = nn.ReLU()

    def forward(self, x):
        res = x
        x = self.convblock1(x)
        x = self.convblock2(x)
        x = self.convblock3(x)
        #####
        x = self.convblock4(x)
        x = self.convblock5(x)
        x = self.convblock6(x)
        x = self.convblock7(x)
        x = self.add(x, self.shortcut(res))
        x = self.act(x)
        return x

class ResNet(Module):
    def __init__(self, c_in, c_out):
        nf = 64
        kss=[13,11,9,7, 5, 3,1]
        print("number of filters: ", nf)
        print("Kernelsizes  : ", kss)
        self.resblock1 = ResBlock(c_in, nf, kss=kss)
        self.resblock2 = ResBlock(nf, nf * 2, kss=kss)
        self.resblock3 = ResBlock(nf * 2, nf * 2, kss=kss)
        self.gap = nn.AdaptiveAvgPool1d(1)
        self.squeeze = Squeeze(-1)
        self.fc = nn.Linear(nf * 2, c_out)

    def forward(self, x):
        x = self.resblock1(x)
        x = self.resblock2(x)
        x = self.resblock3(x)
        x = self.squeeze(self.gap(x))
        return self.fc(x)