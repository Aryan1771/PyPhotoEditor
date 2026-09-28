"""Stroke-start evaluation, coverage memory and one dirty patch per stroke."""
import math
import numpy as np
from PIL import Image
from .document import PatchCommand


def union(a,b):
    if a is None:
        return b
    if b is None:
        return a
    return min(a[0],b[0]),min(a[1],b[1]),max(a[2],b[2]),max(a[3],b[3])


class StrokeSession:
    def __init__(self, document, effect, brush, mode='Once per stroke', params=None, source_image=None):
        if document.image is None:
            raise ValueError('A stroke requires an image')
        self.document, self.effect, self.brush, self.mode = document,effect,brush,mode
        self.params = effect.defaults() if hasattr(effect,'defaults') else {}
        self.params.update(params or {})
        self.base = np.array(source_image if source_image is not None else document.image,dtype=np.uint8)
        self.work = self.base.copy()
        self.coverage = np.zeros(self.base.shape[:2],dtype=np.float32)
        self.dirty = self.last = None
        self.distance = 0.0
        self.closed = False
        self.state = {}
        self.last_stamp = None
        self.selection = document.selection
        if self.selection is not None and self.selection.shape != self.base.shape[:2]:
            raise ValueError('Selection dimensions must match document')

    def stamp(self, point):
        if self.closed:
            raise RuntimeError('Stroke is closed')
        x,y = map(lambda v:int(round(v)),point)
        self.last_stamp = point
        if self.effect.fn.__name__ == "erase_background" and "target" not in self.state:
            from .bg_eraser import prepare
            self.state.update(prepare(self.base,self.params,(x,y),self.brush))
        h,w = self.base.shape[:2]
        size = self.brush.size
        left,top = x-size//2,y-size//2
        l,t,r,b = max(0,left),max(0,top),min(w,left+size),min(h,top+size)
        if r <= l or b <= t:
            return None
        mask = self.brush.footprint()[t-top:b-top,l-left:r-left]*np.float32(self.brush.strength/100)
        if self.selection is not None:
            mask = mask*np.clip(self.selection[t:b,l:r],0,1)
        stateful = getattr(self.effect,'stateful',False)
        buildup = self.mode == 'Build up' or stateful
        cov = self.coverage[t:b,l:r]
        updated = mask if buildup else np.maximum(cov,mask)
        changed = mask > 0 if buildup else updated > cov
        if not changed.any():
            return None
        ys,xs = np.nonzero(changed)
        cl,ct,cr,cb = int(xs.min()),int(ys.min()),int(xs.max())+1,int(ys.max())+1
        l2,t2,r2,b2 = l+cl,t+ct,l+cr,t+cb
        pad = self.effect.pad(self.params) if callable(self.effect.pad) else self.effect.pad
        el,et,er,eb = max(0,l2-pad),max(0,t2-pad),min(w,r2+pad),min(h,b2+pad)
        # Complete image-grid blocks are supplied for stable mosaic averages.
        if getattr(self.effect,'grid',False):
            block = max(1,int(self.params.get('block',12)))
            el,et = el//block*block,et//block*block
            er,eb = min(w,math.ceil(er/block)*block),min(h,math.ceil(eb/block)*block)
        source = self.work if buildup else self.base
        roi = source[et:eb,el:er].copy()
        params = dict(self.params, _origin=(el,et), _point=(x,y), _state=self.state)
        if stateful or getattr(self.effect,'context',False):
            params.update(_base=self.base,_document=self.document,_stamp=(l,t,r,b),_mask=mask)
        result = self.effect.fn(roi,params)
        if not getattr(self.effect,'alpha_effect',False):
            result[...,3] = roi[...,3]
        target = result[t2-et:b2-et,l2-el:r2-el].astype(np.float32)
        original = source[t2:b2,l2:r2].astype(np.float32)
        weight = updated[ct:cb,cl:cr,None]
        blended = np.rint(original+(target-original)*weight).clip(0,255).astype(np.uint8)
        active = changed[ct:cb,cl:cr]
        destination = self.work[t2:b2,l2:r2]
        destination[active] = blended[active]
        cov[:] = updated
        box = (l2,t2,r2,b2)
        self.dirty = union(self.dirty,box)
        return box

    def iter_move(self, point):
        """Yield stamps incrementally so UI callers can bound each work batch."""
        if point is None:
            return
        if self.last is None:
            yield self.stamp(point)
        else:
            dx,dy = point[0]-self.last[0],point[1]-self.last[1]
            length = math.hypot(dx,dy)
            spacing = max(1,self.brush.size*self.brush.spacing)
            step = spacing-self.distance
            while step <= length:
                yield self.stamp((self.last[0]+dx*step/length,self.last[1]+dy*step/length))
                step += spacing
            self.distance = (self.distance+length)%spacing
        self.last = point

    def move_to(self, point):
        dirty = None
        for box in self.iter_move(point):
            dirty = union(dirty,box)
        self.publish(dirty)
        return dirty

    def publish(self, box):
        if box:
            l,t,r,b = box
            self.document.image.paste(Image.fromarray(self.work[t:b,l:r]),(l,t))

    def finish(self):
        if self.closed:
            return None
        if self.last is not None and self.last != self.last_stamp:
            self.publish(self.stamp(self.last))
        command = None
        if self.dirty:
            l,t,r,b = self.dirty
            before,after = self.base[t:b,l:r].copy(),self.work[t:b,l:r].copy()
            if not np.array_equal(before,after):
                command = PatchCommand(self.dirty,before,after,self.effect.name+' brush')
                self.document.record(command)
        self.closed = True
        self.base = self.work = self.coverage = self.selection = None
        self.state.clear()
        return command

    def cancel(self):
        if not self.closed:
            if self.dirty:
                l,t,r,b = self.dirty
                self.document.image.paste(Image.fromarray(self.base[t:b,l:r]),(l,t))
            self.closed = True
            self.base = self.work = self.coverage = self.selection = None
            self.state.clear()
