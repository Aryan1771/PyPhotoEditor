"""Lab background removal, connected-region preparation and original restoration."""
import numpy as np
from scipy import ndimage
from skimage import color


def lab_distance(rgb,target):
    lab = color.rgb2lab(rgb.astype(np.float32)/255)
    target_lab = color.rgb2lab(np.asarray(target,dtype=np.float32).reshape(1,1,3)/255)[0,0]
    return np.linalg.norm(lab-target_lab,axis=-1)


def alpha_factor(distance,tolerance,softness):
    tolerance,softness = float(tolerance),float(softness)
    if softness <= 0:
        return (distance > tolerance).astype(np.float32)
    low = max(0,tolerance-softness)
    return np.clip((distance-low)/max(tolerance-low,1e-6),0,1)


def prepare(base,params,point,brush):
    """Run off the UI thread: label global regions connected to the first footprint.

    Connectivity is four-neighbor. Continuous sampling changes the local target,
    but connectivity remains anchored to this initial background component.
    """
    h,w = base.shape[:2]
    x,y = point
    target = (255,255,255) if params.get('sampling','Fixed white') == 'Fixed white' else tuple(base[y,x,:3])
    state = {'target':target}
    if params.get('limits','Contiguous') == 'Contiguous':
        distance = np.empty((h,w),dtype=np.float32)
        for row in range(0,h,256):
            distance[row:row+256] = lab_distance(base[row:row+256,:,:3],target)
        labels,count = ndimage.label(distance <= float(params.get('tolerance',25)))
        del distance
        size = brush.size
        left,top = x-size//2,y-size//2
        l,t,r,b = max(0,left),max(0,top),min(w,left+size),min(h,top+size)
        footprint = brush.footprint()[t-top:b-top,l-left:r-left] > 0
        seeds = np.unique(labels[t:b,l:r][footprint])
        lookup = np.zeros(count+1,dtype=bool)
        lookup[seeds] = True
        lookup[0] = False
        state['connected'] = lookup[labels]
    return state


def erase_background(roi,p):
    state = p['_state']
    target = state.get('target',(255,255,255))
    if p.get('sampling','Fixed white') == 'Continuous':
        px,py = p['_point']
        target = tuple(p['_base'][py,px,:3])
    distance = lab_distance(roi[...,:3],target)
    factor = alpha_factor(distance,p.get('tolerance',25),p.get('softness',10))
    ox,oy = p['_origin']
    if 'connected' in state:
        allowed = state['connected'][oy:oy+roi.shape[0],ox:ox+roi.shape[1]]
        factor = np.where(allowed,factor,1)
    out = roi.copy()
    out[...,3] = np.minimum(roi[...,3],np.rint(factor*255).astype(np.uint8))
    if p.get('defringe',False):
        # Estimate foreground color after removing the sampled matte.
        a = out[...,3:4].astype(np.float32)/255
        matte = np.asarray(target,dtype=np.float32)
        foreground = (roi[...,:3].astype(np.float32)-(1-a)*matte)/np.maximum(a,1/255)
        edge = ((factor>0)&(factor<1))[...,None]
        out[...,:3] = np.where(edge,np.rint(foreground).clip(0,255),roi[...,:3]).astype(np.uint8)
    return out


def restore(roi,p):
    doc = p['_document']
    if not doc.can_restore:
        return roi.copy()
    x,y = p['_origin']
    return np.array(doc.original.crop((x,y,x+roi.shape[1],y+roi.shape[0])))
