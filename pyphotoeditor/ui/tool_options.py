"""Shared brush controls plus registry-generated effect parameters."""
import tkinter as tk
from tkinter import ttk
from . import theme as T
from .widgets import Slider, SegmentedControl
from ..core.brush_effects import EFFECTS


def build_options(app):
    for child in app.options.winfo_children():
        child.destroy()
    app.option_vars = []
    tool = app.active_tool
    if not hasattr(tool,'engine_key'):
        tk.Label(app.options,text=tool.name.title()+' — drag a box, or click to sample',fg=T.TEXT_MUTED).pack(anchor='w',padx=T.PAD,pady=T.GAP)
        return
    row = tk.Frame(app.options)
    row.pack(fill='x',padx=T.GAP,pady=T.SMALL)
    shape = tk.StringVar(value=app.brush_shape)
    SegmentedControl(row,('circle','square'),shape,lambda v:setattr(app,'brush_shape',v)).pack(side='left')
    row = tk.Frame(app.options)
    row.pack(fill='x',padx=T.GAP,pady=T.SMALL)
    for label,attr,low,high in [('Size','brush_size',1,500),('Strength','brush_strength',1,100),('Hardness','brush_hardness',0,100)]:
        var = tk.DoubleVar(value=getattr(app,attr))
        app.option_vars.append(var)
        def update(value,a=attr):
            setattr(app,a,int(value) if a == 'brush_size' else value)
        Slider(row,label,var,low,high,update).pack(side='left',padx=T.SMALL)
        if attr == 'brush_size':
            app.size_var = var
    row2 = tk.Frame(app.options)
    row2.pack(fill='x',padx=T.PAD,pady=T.SMALL)
    mode = tk.StringVar(value=app.stroke_mode)
    combo = ttk.Combobox(row2,textvariable=mode,values=('Once per stroke','Build up'),state='readonly')
    combo.pack(side='left',padx=T.SMALL)
    combo.bind('<<ComboboxSelected>>',lambda e:setattr(app,'stroke_mode',mode.get()))
    key = getattr(tool,'effect_key',tool.engine_key)
    effect = EFFECTS[key]
    values = app.effect_params.setdefault(key,effect.defaults())
    app.option_vars.extend((shape,mode))
    # Parameter controls wrap onto rows so even the eraser fits the minimum window.
    for index,(name,spec) in enumerate(effect.params.items()):
        if index % T.PARAMS_PER_ROW == 0:
            row2 = tk.Frame(app.options)
            row2.pack(fill='x',padx=T.PAD,pady=T.SMALL)
        if 'choices' in spec:
            var = tk.StringVar(value=values[name])
            tk.Label(row2,text=name.replace('_',' ').title(),fg=T.TEXT_MUTED).pack(side='left',padx=T.SMALL)
            control = ttk.Combobox(row2,textvariable=var,values=spec['choices'],state='readonly',width=T.ICON_SIZE)
            control.pack(side='left',padx=T.SMALL)
            control.bind('<<ComboboxSelected>>',lambda e,n=name,v=var:values.__setitem__(n,v.get()))
        elif isinstance(spec['default'],bool):
            var = tk.BooleanVar(value=values[name])
            ttk.Checkbutton(row2,text=name.title(),variable=var,command=lambda n=name,v=var:values.__setitem__(n,v.get())).pack(side='left')
        else:
            var = tk.DoubleVar(value=values[name])
            Slider(row2,name.title(),var,spec['min'],spec['max'],lambda v,n=name:values.__setitem__(n,v)).pack(side='left')
        app.option_vars.append(var)
    if effect.stateful:
        tk.Label(row2,text='Stateful: carries pixels between stamps',fg=T.TEXT_MUTED).pack(side='left',padx=T.PAD)
