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

from scipy import ndimage
from skimage import color, filters
from PIL import Image


def number(default,low,high):
    return {'default':default,'min':low,'max':high}


def choice(default,*values):
    return {'default':default,'choices':values}


def rgb_effect(fn):
    def apply(roi,p):
        out = roi.copy()
        out[...,:3] = np.rint(fn(roi[...,:3].astype(np.float32),p)).clip(0,255).astype(np.uint8)
        return out
    return apply


def gaussian(rgb,p):
    sigma = float(p.get('radius',2))
    return ndimage.gaussian_filter(rgb,sigma=(sigma,sigma,0),truncate=3)


def sharpen(rgb,p):
    return rgb+(rgb-gaussian(rgb,p))*float(p.get('amount',1.5))


def grayscale(rgb,p):
    return np.repeat((color.rgb2gray(rgb/255)*255)[...,None],3,axis=2)


def sepia(rgb,p):
    return rgb @ np.array([[.393,.349,.272],[.769,.686,.534],[.189,.168,.131]],np.float32)


def emboss(rgb,p):
    kernel = np.array([[-2,-1,0],[-1,1,1],[0,1,2]],np.float32)[...,None]
    return ndimage.convolve(rgb,kernel,mode='reflect')+128


def edge_glow(rgb,p):
    edges = filters.sobel(color.rgb2gray(rgb/255))
    return rgb*.35+edges[...,None]*float(p.get('amount',3))*255


def posterize(rgb,p):
    levels = max(2,int(p.get('levels',5)))
    return np.rint(rgb/255*(levels-1))*255/(levels-1)


def pixelate(rgb,p):
    block = max(1,int(p.get('block',12)))
    h,w = rgb.shape[:2]
    # ROI origin is aligned by StrokeSession. Edge blocks average real pixels only.
    y = np.arange(0,h,block)
    x = np.arange(0,w,block)
    sums = np.add.reduceat(np.add.reduceat(rgb,y,axis=0),x,axis=1)
    counts = np.minimum(block,h-y)[:,None]*np.minimum(block,w-x)[None,:]
    means = sums/counts[...,None]
    return means[np.arange(h)//block][:,np.arange(w)//block]


def ordered_dither(rgb,p):
    n = int(p.get('matrix','4'))
    bayer = np.array([[0,2],[3,1]],dtype=np.float32)
    while bayer.shape[0] < n:
        bayer = np.block([[4*bayer,4*bayer+2],[4*bayer+3,4*bayer+1]])
    x,y = p.get('_origin',(0,0))
    yy,xx = np.ogrid[y:y+rgb.shape[0],x:x+rgb.shape[1]]
    threshold = (bayer[yy%n,xx%n]+.5)/(n*n)
    return np.where(rgb/255 >= threshold[...,None],255,0)


def oil(rgb,p):
    return posterize(ndimage.median_filter(rgb,size=(3,3,1)),p)


def noise(rgb,p):
    x,y = p.get('_origin',(0,0))
    yy,xx = np.ogrid[y:y+rgb.shape[0],x:x+rgb.shape[1]]
    # Coordinate hash: deterministic across ROI sizes, stamps and repeated passes.
    hashed = (xx.astype(np.uint32)*np.uint32(374761393) + yy.astype(np.uint32)*np.uint32(668265263))
    hashed = (hashed ^ (hashed >> 13))*np.uint32(1274126177)
    delta = ((hashed & 65535).astype(np.float32)/65535-.5)*2*float(p.get('amount',25))
    return rgb+delta[...,None]


def hue(rgb,p):
    hsv = color.rgb2hsv(rgb/255)
    hsv[...,0] = (hsv[...,0]+float(p.get('degrees',90))/360)%1
    return color.hsv2rgb(hsv)*255


def dodge_burn(rgb,p):
    luminance = color.rgb2gray(rgb/255)
    region = p.get('range','midtones')
    weight = (1-luminance)**2 if region == 'shadows' else luminance**2 if region == 'highlights' else 4*luminance*(1-luminance)
    amount = float(p.get('amount',35))/100*weight[...,None]
    return rgb+(255-rgb)*amount if p.get('operation','dodge') == 'dodge' else rgb*(1-amount)


def sponge(rgb,p):
    hsv = color.rgb2hsv(rgb/255)
    amount = float(p.get('amount',50))/100
    hsv[...,1] = np.clip(hsv[...,1]*(1+amount if p.get('operation','saturate') == 'saturate' else 1-amount),0,1)
    return color.hsv2rgb(hsv)*255


def cartoon(rgb,p):
    edges = filters.sobel(color.rgb2gray(rgb/255))
    return posterize(rgb,p)*np.clip(1-edges[...,None]*float(p.get('edges',5)),0,1)


def paint(roi,p):
    out = roi.copy()
    out[:] = p.get('color',(0,0,0,255))
    return out


def erase(roi,p):
    out = roi.copy()
    out[...,3] = 0
    return out


def smudge(roi,p):
    state = p['_state']
    carry = state.get('carry')
    if carry is None:
        state['carry'] = roi.copy()
        return roi.copy()
    if carry.shape != roi.shape:
        carry = np.asarray(Image.fromarray(carry).resize((roi.shape[1],roi.shape[0]),Image.Resampling.BILINEAR))
    out = roi.copy()
    out[...,:3] = np.rint(carry[...,:3]*.8+roi[...,:3]*.2).astype(np.uint8)
    state['carry'] = out.copy()
    return out


EFFECTS.update({
    'paint':Effect('Paint',paint,alpha_effect=True),
    'erase':Effect('Eraser',erase,alpha_effect=True),
    'blur':Effect('Blur',rgb_effect(gaussian),pad=lambda p:int(np.ceil(3*p['radius'])),params={'radius':number(2,.3,10)}),
    'sharpen':Effect('Sharpen',rgb_effect(sharpen),pad=lambda p:int(np.ceil(3*p['radius'])),params={'radius':number(2,.3,10),'amount':number(1.5,.1,4)}),
    'smudge':Effect('Smudge',smudge,stateful=True),
    'pixelate':Effect('Pixelate',rgb_effect(pixelate),params={'block':number(12,2,64)},grid=True),
    'grayscale':Effect('Grayscale',rgb_effect(grayscale)),
    'sepia':Effect('Sepia',rgb_effect(sepia)),
    'emboss':Effect('Emboss',rgb_effect(emboss),pad=1),
    'edge_glow':Effect('Edge Glow',rgb_effect(edge_glow),pad=1,params={'amount':number(3,1,8)}),
    'posterize':Effect('Posterize',rgb_effect(posterize),params={'levels':number(5,2,16)}),
    'ordered_dither':Effect('Ordered Dither',rgb_effect(ordered_dither),params={'matrix':choice('4','4','8')}),
    'oil_paint':Effect('Oil Paint',rgb_effect(oil),pad=1,params={'levels':number(6,2,16)}),
    'noise':Effect('Noise / Grain',rgb_effect(noise),params={'amount':number(25,1,100)}),
    'hue_shift':Effect('Hue Shift',rgb_effect(hue),params={'degrees':number(90,-180,180)}),
    'dodge_burn':Effect('Dodge / Burn',rgb_effect(dodge_burn),params={'operation':choice('dodge','dodge','burn'),'range':choice('midtones','shadows','midtones','highlights'),'amount':number(35,1,100)}),
    'sponge':Effect('Sponge',rgb_effect(sponge),params={'operation':choice('saturate','saturate','desaturate'),'amount':number(50,1,100)}),
    'cartoon':Effect('Cartoon',rgb_effect(cartoon),pad=1,params={'levels':number(5,2,16),'edges':number(5,1,12)}),
})
