from dataclasses import dataclass, field
import numpy as np


@dataclass
class Effect:
    name: str
    fn: object
    pad: object = 0
    params: dict = field(default_factory=dict)
    icon: str = 'effect'
    alpha_effect: bool = False
    stateful: bool = False
    grid: bool = False
    context: bool = False

    def defaults(self):
        return {key: spec['default'] for key,spec in self.params.items()}


def negative(roi,params):
    out = roi.copy()
    out[...,:3] = 255-out[...,:3]
    return out


EFFECTS = {'negative':Effect('Negative',negative)}
