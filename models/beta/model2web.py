import numpy as np
import chainer
from chainer import Chain, Variable
import chainer.functions as F
import chainer.links as L
from chainer import serializers,cuda

import math
import os
import glob
import pickle
from PIL import Image

NUMBER_OF_TAG = 1539
xp = np

#network

class EqualizedConv2d(chainer.Chain):
    def __init__(self, in_dim, out_dim,ksize=3,stride=1,pad=1):
        w = chainer.initializers.Normal(1.0) # equalized learning rate
        self.inv_c = np.sqrt(2.0/(in_dim*ksize**2))
        super(EqualizedConv2d,self).__init__(
            normalize=normalize(),
        )
        with self.init_scope():
            self.c1=L.Convolution2D(in_dim, out_dim, ksize, stride, pad, initialW=w)
    def __call__(self,x,normalize = True,dropout = False):
        h = self.c1(x * self.inv_c)

        if normalize:
            h = self.normalize(h)

        if dropout:
          F.dropout(h)
        return h

class EqualizedLinear(chainer.Chain):
    def __init__(self, in_dim, out_dim):
        w = chainer.initializers.Normal(1.0) # equalized learning rate
        self.inv_c = np.sqrt(2.0/(in_dim))
        super(EqualizedLinear,self).__init__(
        )
        with self.init_scope():
            self.l1=L.Linear(in_dim, out_dim, initialW=w)
    def __call__(self,x):
        h = self.l1(x * self.inv_c)
        return h

class g_block(chainer.Chain):
    def __init__(self, in_dim, out_dim):
        super(g_block,self).__init__(
            normalize=normalize(),
            dc1=EqualizedConv2d(in_dim, out_dim, 3, stride=1, pad=1),
            dc2=EqualizedConv2d(out_dim, out_dim, 3, stride=1, pad=1),
            to_RGB=EqualizedConv2d(out_dim, 3, 1, stride=1, pad=0),
            cr1 = crop(),
        )
    def __call__(self,x,to_rgb=True):
        h = F.unpooling_2d(x, 2, 2, 0, outsize=(x.shape[2]*2, x.shape[3]*2))
        h_r = h
        h = F.leaky_relu(self.dc1(h))
        h = F.leaky_relu(self.dc2(h))
        if to_rgb:
            #h = F.tanh(self.to_RGB(h))
            h = self.to_RGB(h,False)
            h = h + h_r
            h = self.cr1(h)
        return h

class normalize(chainer.Chain):
    def __init__(self):
        super(normalize,self).__init__(
        )
    def __call__(self,x):
        eps = 1e-8
        mean=F.mean(x ** 2,axis=1,keepdims=True)
        mean=F.sqrt(mean + eps)
        mean = F.broadcast_to(mean, (x.shape))
        h = x / mean
        return x
class crop(chainer.Chain):
    def __init__(self):
      super(crop,self).__init__()
    def __call__(self,h):
      h = F.minimum(h,xp.ones(h.shape).astype(np.float32))
      h = F.maximum(h,-1 * xp.ones(h.shape).astype(np.float32))

      return h

class generator(chainer.Chain):
    def __init__(self, width, height, z_size):
        super(generator,self).__init__(
            normalize=normalize(),
            c0 = EqualizedConv2d(z_size, 512, 4, stride=1, pad=3),
            c1 = EqualizedConv2d(512, 512, 3, stride=1, pad=1),

            b0=g_block(3,512),
            b1=g_block(3,512),
            b2=g_block(3,256),
            b3=g_block(3,128),
            b4=g_block(3,64),
            b5=g_block(3,32),
            b6=g_block(3,16),

            to_RGB=EqualizedConv2d(512, 3, 1, stride=1, pad=0),
            cr1 = crop()
        )

    def __call__(self, noise, tag,depth,alpha):
        h = F.reshape(noise,(len(noise),-1,1,1))
        h = F.leaky_relu(self.c0(h))
        h = F.leaky_relu(self.c1(h))
        h = self.to_RGB(h,False)

        for i in range(depth):
            h = getattr(self, "b%d" % i)(h,True)

        #h = getattr(self, "b%d" % (depth-1))(h,True)


        h = self.cr1(h)
        return h


def combine_images(generated_images):
    total = generated_images.shape[0]
    cols = int(math.sqrt(total))
    rows = math.ceil(float(total)/cols)
    width, height = generated_images.shape[1:3]
    combined_image = np.zeros((width*cols, height*rows,3),
                              dtype=generated_images.dtype)
    #coreturn combined_image

    for index, image in enumerate(generated_images):
        i = index % cols
        j = int(index/cols)
        combined_image[width*i:width*(i+1), height*j:height*(j+1),0:3] = image[:,:,0:3 ]
    return combined_image

def save_images(images,file_name):
    print(images.shape)
    Image.fromarray(images.astype(np.uint8))\
        .save("%s.png" % (file_name))

def save_generated_image(image,name):
    Imag=combine_images(image)
    save_images(Imag,name)

z_size = 128

noise=np.random.normal(0, 0.5, [32,z_size])

class normalize2(chainer.Chain):
    def __init__(self):
        super(normalize2,self).__init__(
        )
    def __call__(self,x):
        eps = 1e-8
        mean=F.mean(x ** 2,axis=1,keepdims=True)
        mean=(mean + eps) ** 0.5
        mean = F.broadcast_to(mean, (x.shape))
        h = x / mean
        return h

class EqualizedConv2d2(chainer.Chain):
    def __init__(self, in_dim, out_dim,ksize=3,stride=1,pad=1):
        w = chainer.initializers.Normal(1.0) # equalized learning rate
        self.inv_c = np.sqrt(2.0/(in_dim*ksize**2))
        super(EqualizedConv2d2,self).__init__(
            normalize=normalize2(),
        )
        with self.init_scope():
            self.c1=L.Convolution2D(in_dim, out_dim, ksize, stride, pad, initialW=w)
    def __call__(self,x,normalize = True,dropout = False):
        h = self.c1(x * self.inv_c)

        if normalize:
            h = self.normalize(h)

        if dropout:
          F.dropout(h)
        return h

class g_block2(chainer.Chain):
    def __init__(self, in_dim, out_dim):
        super(g_block2,self).__init__(
            normalize=normalize2(),
            dc1=EqualizedConv2d2(in_dim, out_dim, 3, stride=1, pad=1),
            dc2=EqualizedConv2d2(out_dim, out_dim, 3, stride=1, pad=1),
            to_RGB=EqualizedConv2d2(out_dim, 3, 1, stride=1, pad=0),
        )
    def __call__(self,x,to_rgb=False):
        h = F.unpooling_2d(x, 2, 2, 0, outsize=(x.shape[2]*2, x.shape[3]*2))
        h = F.leaky_relu(self.dc1(h))
        h = F.leaky_relu(self.dc2(h))
        if to_rgb:
            #h = F.tanh(self.to_RGB(h))
            h = self.to_RGB(h,False)
        return h

class generator2(chainer.Chain):
    def __init__(self, width, height, z_size):
        dims = [64, 64, 64, 64, 64, 64, 64, 64]
        super(generator2,self).__init__(
            normalize=normalize2(),
            c0 = EqualizedConv2d2(z_size, dims[0], 4, stride=1, pad=3),
            c1 = EqualizedConv2d2(dims[0], dims[0], 3, stride=1, pad=1),

            b0=g_block2(dims[0],dims[1]),
            b1=g_block2(dims[1],dims[2]),
            b2=g_block2(dims[2],dims[3]),
            b3=g_block2(dims[3],dims[4]),
            b4=g_block2(dims[4],dims[5]),
            b5=g_block2(dims[5],dims[6]),
            b6=g_block2(dims[6],dims[7]),

            to_RGB=EqualizedConv2d2(dims[0], 3, 1, stride=1, pad=0),

        )

    def __call__(self, noise, tag,depth,alpha):
        h = F.reshape(noise,(len(noise),-1,1,1))
        h = F.leaky_relu(self.c0(h,False))
        h = F.leaky_relu(self.c1(h))

        for i in range(depth-1):
            h = getattr(self, "b%d" % i)(h)

        if 0<depth and alpha < 1:
            h2 = getattr(self, "b%d" % (depth-1))(h,True)
            if depth==1:
                #h = F.tanh(self.to_RGB(h))
                h = self.to_RGB(h,False)
            else:
                h = getattr(self, "b%d" % (depth-2)).to_RGB(h,False)
            h=F.unpooling_2d(h, 2, 2, 0, outsize=(2*h.shape[2], 2*h.shape[3]))

            h=h*(1.0-alpha)+h2*alpha
        elif depth == 0:
            #h = F.tanh(self.to_RGB(h))
            h = self.to_RGB(h,False)
        else:
            h = getattr(self, "b%d" % (depth-1))(h,True)

        h = F.minimum(h,xp.ones(h.shape).astype(np.float32))
        #h = F.maximum(h,-1 * xp.ones(h.shape).astype(np.float32))

        return h

z_size = 128
g2 = generator2(512, 512, z_size)
serializers.load_npz("generator03.model", g2)
g = generator(512, 512, z_size)
serializers.load_npz("generator_SRB.model", g)
x = chainer.Variable(np.zeros((1,z_size), dtype=np.float32))
y = g2(x,0,5,1)
y = g.b5(y)
y = F.average_pooling_2d(y, (1,2), (1,2))



noise=np.random.normal(0, 0.5, [1,z_size]).astype(np.float32)
image = g2(noise,np.zeros(NUMBER_OF_TAG),5,1)
image = g.b5(image)
image = F.average_pooling_2d(image, (1,2), (1,2))
image = image.data[0]
image = image.transpose(1,2,0)
save_images((image * 127.5)+127.5,"test")


from webdnn.frontend.chainer import ChainerConverter
from webdnn.backend import generate_descriptor
from webdnn.util import flags

graph = ChainerConverter().convert([x], [y])

flags.optimize.REPLACE_SCALAR_OPERATOR = 0
flags.optimize.OPTIMIZE_MEMORY_ALLOCATION=0
exec_info = generate_descriptor("webassembly", graph)  # also "webassembly", "webgl", "fallback" are available.
exec_info.save("./output")
