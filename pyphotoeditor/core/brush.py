"""Cached, immutable float32 brush footprints."""
from dataclasses import dataclass
from functools import lru_cache
import numpy as np


@lru_cache(maxsize=256)
def _footprint(shape, size, hardness):
    if shape == 'square':
        mask = np.ones((size,size),dtype=np.float32)
    else:
        yy,xx = np.ogrid[:size,:size]
        radius = np.sqrt((xx-(size-1)/2)**2+(yy-(size-1)/2)**2)/(size/2)
        inner = hardness/100
        mask = (radius <= 1).astype(np.float32) if hardness == 100 else np.clip((1-radius)/max(1e-6,1-inner),0,1).astype(np.float32)
    mask.flags.writeable = False
    return mask


@dataclass(frozen=True)
class Brush:
    shape: str = 'circle'
    size: int = 20
    hardness: float = 100
    strength: float = 100
    spacing: float = 0.15

    def __post_init__(self):
        if self.shape not in ('circle','square'):
            raise ValueError('Brush shape must be circle or square')
        object.__setattr__(self,'size',max(1,min(500,int(self.size))))
        object.__setattr__(self,'hardness',max(0,min(100,float(self.hardness))))
        object.__setattr__(self,'strength',max(1,min(100,float(self.strength))))
        object.__setattr__(self,'spacing',max(0.01,float(self.spacing)))

    def footprint(self):
        return _footprint(self.shape,self.size,self.hardness)
