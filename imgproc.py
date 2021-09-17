import PIL
from PIL import Image
import io

def load_img_from_bin(b):
    im = Image.open(io.BytesIO(b))
    return im.convert(mode='RGBA')

def resize_to(im, target=72):
    w,h = ow,oh = im.size
    longer = max(w,h)
    shorter = min(w,h)

    # crop the thing to square
    l = int((longer-shorter)/2+.5)
    if longer==w:
        nim = im.crop((l,0,w-l,h))
    else:
        nim = im.crop((0,l,w,h-l))

    # resize to a smaller square
    w,h = nim.size
    ratio = target/w
    nw,nh = round(w*ratio), round(w*ratio)

    if nw == ow and nh==oh:
        return im
    return nim.resize((nw,nh), resample=Image.BICUBIC, reducing_gap=3.5)

def avatar_pipeline(b):
    # user upload binary file
    # convert it into avatar format
    # output binary

    im = load_img_from_bin(b)
    im = resize_to(im, 96).quantize(
        colors=64,
        method=Image.FASTOCTREE, # only applicapable
        kmeans=1, # larger faster
        dither=Image.FLOYDSTEINBERG,
    )
    print(im.size)
    result_file = io.BytesIO()
    im.save(result_file,'PNG',optimize=True)
    return result_file.getvalue()

if __name__ == '__main__':
    import sys
    if len(sys.argv)>1:
        fn = sys.argv[1]

        im = load_img_from_bin(open(fn,'rb').read())

        im = im.quantize(
            colors=128,
            method=Image.FASTOCTREE, # only applicapable
            kmeans=1, # larger faster
            dither=Image.FLOYDSTEINBERG,
        )

        im.save(fn,'PNG',optimize=True)
        print('saved to', fn)
    else:
        print('no args')

    # b = open('templates/images/logo.png','rb').read()
    # # b = b[:100]
    # im = load_img_from_bin(b)
    #
    # print(im)
    # # resize_to(im, 84).quantize(
    # #     colors=32,
    # #     method=Image.FASTOCTREE, # only applicapable
    # #     kmeans=1, # larger faster
    # #     dither=Image.FLOYDSTEINBERG,
    # # ).save('test.png')
