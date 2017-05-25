import numpy as np
import Image
cimport numpy as np
cimport cython

cdef extern from "math.h":
    double sqrt(double i)
    double fabs(double i)
    double floor(double i)

cpdef hog(im, int sbin = 8): 
    """
    Computes a histogram of oriented gradient features.

    Adopted from Pedro Felzenszwalb's features.cc
    """
    cdef np.ndarray[np.double_t, ndim=3] data, feat
    cdef np.ndarray[np.double_t, ndim=1] hist, norm

    cdef int blocks0, blocks1
    cdef int out0, out1, out2
    cdef int visible0, visible1

    cdef double dy, dx, v
    cdef double dy2, dx2, v2
    cdef double dy3, dx3, v3
    cdef double best_dot, dot
    cdef int best_o

    cdef double xp, yp, vx0, vy0, vx1, vy1
    cdef int ixp, iyp
    cdef double n1, n2, n3, n4, t1, t2, t3, t4, h1, h2, h3, h4
    cdef int p

    cdef np.ndarray[np.double_t, ndim=1] uu
    uu = np.array([ 1.0000,  0.9397,  0.7660,  0.500,  0.1736, 
                   -0.1736, -0.5000, -0.7660, -0.9397])
    cdef np.ndarray[np.double_t, ndim=1] vv
    vv = np.array([0.0000, 0.3420, 0.6428, 0.8660, 0.9848, 
                   0.9848, 0.8660, 0.6428, 0.3420])

    cdef double eps = 0.0001 # to avoid division by 0
    cdef unsigned int cc0, cc1, cc2

    cdef int x, y, o, q
    cdef int dstptr, srcptr

    width, height = im.size
    blocks0 = height / sbin 
    blocks1 = width / sbin

    out0 = blocks0 - 2
    out1 = blocks1 - 2
    out2 = 9 + 4

    visible0 = blocks0 * sbin
    visible1 = blocks1 * sbin

    data = np.asarray(im, dtype=np.double)

    cc0 = <unsigned int>(0)
    cc1 = <unsigned int>(1)
    cc2 = <unsigned int>(2)

    hist = np.zeros(shape=(blocks0 * blocks1 * 9), dtype=np.double)
    norm = np.zeros(shape=(blocks0 * blocks1), dtype=np.double)
    feat = np.zeros(shape=(out0, out1, out2), dtype=np.double)

    for x from 1 <= x < visible1 - 1:
        for y from 1 <= y < visible0 - 1:
            dy = data[y + 1, x, cc0] - data[y - 1, x, cc0]
            dx = data[y, x + 1, cc0] - data[y, x - 1, cc0]
            v = dx * dx + dy * dy

            dy2 = data[y + 1, x, cc1] - data[y - 1, x, cc1]
            dx2 = data[y, x + 1, cc1] - data[y, x - 1, cc1]
            v2 = dx2 * dx2 + dy2 * dy2

            dy3 = data[y + 1, x, cc2] - data[y - 1, x, cc2]
            dx3 = data[y, x + 1, cc2] - data[y, x - 1, cc2]
            v3 = dx3 * dx3 + dy3 * dy3

            if v2 > v: # pick channel with strongest gradient
                v = v2
                dx = dx2
                dy = dy2
            if v3 > v:
                v = v3
                dx = dx3
                dy = dy3

            # snap to one of 9 orientations
            best_dot = 0.
            best_o = 0
            for o from 0 <= o < 9:
                dot = fabs(uu[o] * dx + vv[o] * dy)
                if dot > best_dot:
                    best_dot = dot
                    best_o = o

            # add to 4 histograms around pixel using linear interpolation
            xp = (<double>(x) + 0.5) / <double>(sbin) - 0.5 
            yp = (<double>(y) + 0.5) / <double>(sbin) - 0.5

            ixp = <int>floor(xp)
            iyp = <int>floor(yp)

            vx0 = xp - ixp
            vy0 = yp - iyp
            vx1 = 1.0 - vx0
            vy1 = 1.0 - vy0
            v = sqrt(v)

            if ixp >= 0 and iyp >= 0:
                hist[ixp * blocks0 + iyp + best_o*blocks0*blocks1] += vx1 * vy1 * v
            if ixp + 1 < blocks1 and iyp >= 0:
                hist[(ixp + 1) * blocks0 + iyp + best_o*blocks0*blocks1] += vx0 * vy1 * v
            if ixp >= 0 and iyp + 1 < blocks0:
                hist[ixp * blocks0 + (iyp + 1) + best_o*blocks0*blocks1] += vx1 * vy0 * v
            if ixp + 1 < blocks1 and iyp + 1 < blocks0:
                hist[(ixp + 1) * blocks0 + (iyp + 1) + best_o * blocks0 * blocks1] += vx0 * vy0 * v
    
    # compute energy in each block by summing over orientations
    for o from 0 <= o < 9:
        for q from 0 <= q < blocks0 * blocks1:
            norm[q] += hist[o * blocks0 * blocks1 + q] * hist[o * blocks0 * blocks1 + q] 

    # compute normalized values 
    for x from 0 <= x < out1:
        for y from 0 <= y < out0:
            p = (x+1) * blocks0 + y + 1
            n1 = 1.0 / sqrt(norm[p] + norm[p+1] + norm[p+blocks0] + norm[p+blocks0+1] + eps)
            p = (x+1) * blocks0 + y 
            n2 = 1.0 / sqrt(norm[p] + norm[p+1] + norm[p+blocks0] + norm[p+blocks0+1] + eps)
            p = x * blocks0 + y + 1
            n3 = 1.0 / sqrt(norm[p] + norm[p+1] + norm[p+blocks0] + norm[p+blocks0+1] + eps)
            p = x * blocks0 + y
            n4 = 1.0 / sqrt(norm[p] + norm[p+1] + norm[p+blocks0] + norm[p+blocks0+1] + eps)

            t1 = 0
            t2 = 0
            t3 = 0
            t4 = 0

            srcptr = (x+1) * blocks0 + y + 1
            for o from 0 <= o < 9:
                h1 = hist[srcptr] * n1
                h2 = hist[srcptr] * n2
                h3 = hist[srcptr] * n3
                h4 = hist[srcptr] * n4
                # for some reason, gcc will not automatically inline
                # the min function here, so we just do it ourselves
                # for impressive speedups
                if h1 > 0.2:
                    h1 = 0.2
                if h2 > 0.2:
                    h2 = 0.2
                if h3 > 0.2:
                    h3 = 0.2
                if h4 > 0.2:
                    h4 = 0.2
                feat[y, x, o] = 0.5 * (h1 + h2 + h3 + h4)
                t1 += h1
                t2 += h2
                t3 += h3
                t4 += h4
                srcptr += blocks0 * blocks1

            feat[y, x, 9] = 0.2357 * t1
            dstptr += out0 * out1
            feat[y, x, 10] = 0.2357 * t2
            dstptr += out0 * out1
            feat[y, x, 11] = 0.2357 * t3
            dstptr += out0 * out1
            feat[y, x, 12] = 0.2357 * t4
    
    return feat

cpdef hogpad(np.ndarray[np.double_t, ndim=3] hog):
    cdef np.ndarray[np.double_t, ndim=3] out
    cdef int i, j, k
    cdef int w = hog.shape[0], h = hog.shape[1], z = hog.shape[2]
    out = np.zeros((w + 2, h + 2, z))

    for i in range(w):
        for j in range(h):
            for k in range(z):
                out[i+1, j+1, k] = hog[i, j, k]
    return out

cpdef rgbhist(im, int binsize = 8):
    """
    Computes an RGB color histogram with a binsize.
    """
    cdef int w = im.size[0], h = im.size[1]
    cdef np.ndarray[np.uint8_t, ndim=3] data = np.asarray(im)
    cdef np.ndarray[np.double_t, ndim=1] hist 
    hist = np.zeros(binsize * binsize * binsize)

    for i from 0 <= i < w:
        for j from 0 <= j < h:
            bin  = (<int>data[j,i,0]) / (256/binsize)
            bin += (<int>data[j,i,1]) / (256/binsize) * binsize
            bin += (<int>data[j,i,2]) / (256/binsize) * binsize * binsize
            hist[bin] += 1
    return hist

cpdef rgbmean(im):
    """
    Computes mean and covariances of RGB colors.
    """
    cdef int w = im.size[0], h = im.size[1]
    cdef double r, g, b
    cdef np.ndarray[np.uint8_t, ndim=3] data = np.asarray(im)
    cdef np.ndarray[np.double_t, ndim=1] out = np.zeros(9)

    for i in range(w):
        for j in range(h):
            r = data[j, i, 0] / 255.
            g = data[j, i, 1] / 255.
            b = data[j, i, 2] / 255.

            out[0] += r
            out[1] += g
            out[2] += b

            out[3] += r * r 
            out[4] += r * g 
            out[5] += r * b

            out[6] += g * g
            out[7] += g * b

            out[8] += b * b
    return out  / (w * h)
