"""Alpha preservation for RGB-only global operations."""
from functools import wraps


def preserve_alpha(fn):
    @wraps(fn)
    def apply(image,*args,**kwargs):
        out = fn(image,*args,**kwargs).convert('RGBA')
        out.putalpha(image.convert('RGBA').getchannel('A'))
        return out
    return apply
