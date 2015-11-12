from PIL import Image
from os import remove

def generate_images(fn):
    if '.jpeg' in fn:
        fn = fn[:-5]+jpg
    # Saving the full image as JPEG
    im = Image.open(fn)
    im.save(fn[:-4]+'_full.jpg','JPEG',quality=100)
    # Crop 1:1
    im = Image.open(fn)
    width, height = im.size
    print(im.size)
    nheight = height
    nwidth = width
    if width < height:
        nheight = width
        left = 0
        top = int((height-nheight)/2)
        right = int(width)
        bottom = int((height-nheight)/2 + nheight)
    else:
        nwidth = int(height)
        left = int((width-nwidth)/2)
        top = 0
        right = int((width-nwidth)/2 + nwidth)
        bottom = height
    im.crop((left,top,right,bottom)).save(fn[:-4]+'_crop.jpg','JPEG')
    im.close()
    # Making thumbnail = 160x160 = CSS Square
    im = Image.open(fn[:-4]+'_crop.jpg')
    im.thumbnail((160,160))
    im.save(fn[:-4]+'_thumbnail.jpg',"JPEG")
    im.close()
    # Create medium 600x or x600
    im = Image.open(fn)
    w,h = im.size
    newsize = 600
    msize = newsize,newsize
    if w < h:
        # h is the reference
        r = newsize/h
        neww = w*r
        msize = neww,newsize
    elif h < w:
        # w is the reference
        r = newsize/w
        newh = h*r
        msize = newsize,newh

    if msize[0] == 0 or msize[1] == 0:
        msize = newsize,newsize
    print(msize)
    im.thumbnail(msize)
    im.save(fn[:-4]+'_medium.jpg',"JPEG")
    im.close()
    # Saving the icon 40x40
    im = Image.open(fn[:-4]+'_crop.jpg')
    im.thumbnail((40,40))
    im.save(fn[:-4]+'_icon.jpg',"JPEG")
    im.close()
    remove(fn[:-4]+'_crop.jpg')
    remove(fn)
