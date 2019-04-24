# LINC is an open source shared database and facial recognition
# system that allows for collaboration in wildlife monitoring.
# Copyright (C) 2016  Wildlifeguardians
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# For more information or to contact visit linclion.org or email tech@linclion.org

from PIL import Image
from os import remove
from logging import info


def generate_images(fn):
    if '.jpeg' in fn.lower():
        fn = fn[:-5] + '.jpg'
    if '.png' in fn.lower():
        # Converting the PNG 
        nfn = fn[:-4] + '.jpg'
        im = Image.open(fn)
        im = im.convert('RGB')
        im.save(nfn, 'JPEG', quality=100)
        fn = nfn
    # Saving the full image as JPEG
    im = Image.open(fn)
    # Handling transparent PNGs error 
    im.save(fn[:-4] + '_full.jpg', 'JPEG', quality=100)
    # Crop 1:1
    im = Image.open(fn)
    width, height = im.size
    info(im.size)
    nheight = height
    nwidth = width
    if width < height:
        nheight = width
        left = 0
        top = int((height - nheight) / 2)
        right = int(width)
        bottom = int((height - nheight) / 2 + nheight)
    else:
        nwidth = int(height)
        left = int((width - nwidth) / 2)
        top = 0
        right = int((width - nwidth) / 2 + nwidth)
        bottom = height
    im.crop((left, top, right, bottom)).save(fn[:-4] + '_crop.jpg', 'JPEG')
    im.close()
    # Making thumbnail = 160x160 = CSS Square
    im = Image.open(fn[:-4] + '_crop.jpg')
    im.thumbnail((160, 160))
    im.save(fn[:-4] + '_thumbnail.jpg', "JPEG")
    im.close()
    # Create medium 600x or x600
    im = Image.open(fn)
    w, h = im.size
    newsize = 600
    msize = newsize, newsize
    if w < h:
        # h is the reference
        r = newsize / h
        neww = w * r
        msize = neww, newsize
    elif h < w:
        # w is the reference
        r = newsize / w
        newh = h * r
        msize = newsize, newh

    if msize[0] == 0 or msize[1] == 0:
        msize = newsize, newsize
    info(msize)
    im.thumbnail(msize)
    im.save(fn[:-4] + '_medium.jpg', "JPEG")
    im.close()
    # Saving the icon 40x40
    im = Image.open(fn[:-4] + '_crop.jpg')
    im.thumbnail((40, 40))
    im.save(fn[:-4] + '_icon.jpg', "JPEG")
    im.close()
    remove(fn[:-4] + '_crop.jpg')
    remove(fn)
