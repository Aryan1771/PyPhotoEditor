"""Alpha-aware file export; UI supplies any necessary user warning."""
from PIL import Image


def save_image(image,path):
    if str(path).lower().endswith(('.jpg','.jpeg')):
        background = Image.new('RGBA',image.size,(255,255,255,255))
        image = Image.alpha_composite(background,image.convert('RGBA')).convert('RGB')
    image.save(path)
