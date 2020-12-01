# -*- coding: utf-8 -*-
"""
Created on Thu Jun 13 10:09:55 2019

@author: aluo
"""
from PyTracer import pyBVH
import numpy as np
from numpy import array, float32
from PyTracer import pyStructs as st
import time
from PySide2.QtWidgets import QOpenGLWidget
from PySide2.QtCore import Signal, Slot, QTimer, QTime, QFileInfo, QFile, QIODevice, QJsonDocument, QRect
from PySide2.QtGui import QVector3D, QOpenGLFunctions, \
    QQuaternion, QOpenGLFramebufferObject, QOpenGLFramebufferObjectFormat, QImage, QMatrix4x4, Qt, QVector2D
from random import random
from multiprocessing import Pool, freeze_support
import cProfile
from functools import reduce

primitives = []


def getbvh():
    middle_bvh = pyBVH.BVH(primitives, 'EqualCounts')
    return middle_bvh

def test():
    iters = 1
    np.random.seed(0)
    N, M = 1000, 10000
    matrix = [np.random.rand(N) for _ in range(M)]
    for idx in range(iters):
        #
        start_time = time.time()
        np.max(matrix, axis=0)
        print(time.time() - start_time)
        start_time = time.time()
        np.max(np.vstack(matrix), axis=0)
        print(time.time() - start_time)
        start_time = time.time()
        reduce(np.maximum, matrix)
        print(time.time() - start_time)
        start_time = time.time()
        np.max(np.asarray(matrix))
        print(time.time() - start_time)


def matrix_test():
    qmatrix = QMatrix4x4()
    qmatrix.translate(0, -0.2, 0)
    # qmatrix.rotate(90, 1, 0, 0)

    qinv_matrix, is_invertible = qmatrix.inverted()
    qnormal_matrix = qinv_matrix.normalMatrix()
    normal_matrix = np.array(qnormal_matrix.data()).reshape(3,3).transpose()
    inv_matrix = np.array(qinv_matrix.data()).reshape(4,4).transpose()
    matrix = np.array(qmatrix.data()).reshape(4,4).transpose()

    p0 = np.array([5, 0, 0])
    n = np.array([0, 1, 0])
    plane = st.Plane(p0, n)
    plane_info = st.PlaneIntersectionInfo()

    number_of_primitives = 5
    primitives = []
    qprimitives = []
    transformed_primitives = []
    for i in range(number_of_primitives):
        t_baricenter = (np.random.rand(3) - 0.5) * 100
        t_baricenter = np.zeros(3)
        v0 = t_baricenter + (np.random.rand(3) - 0.5) * 2
        v1 = t_baricenter + (np.random.rand(3) - 0.5) * 2
        v2 = t_baricenter + (np.random.rand(3) - 0.5) * 2
        primitives.append(st.Triangle(v0, v1, v2))
        qv0 = qmatrix.map(QVector3D(v0[0], v0[1], v0[2]))
        qv1 = qmatrix.map(QVector3D(v1[0], v1[1], v1[2]))
        qv2 = qmatrix.map(QVector3D(v2[0], v2[1], v2[2]))
        qprimitives.append(st.Triangle(np.array(qv0.toTuple()), np.array(qv1.toTuple()), np.array(qv2.toTuple())))

    qbvh = pyBVH.BVH(qprimitives, 'SAH')
    qbvh.plane_all_intersections(plane, plane_info)
    print(plane_info.intersections)
    bvh = pyBVH.BVH(primitives, 'EqualCounts')
    p0 = inv_matrix.dot(np.append(p0, 1))[0:3]
    n = normal_matrix.dot(np.array([0, 1, 0]))
    plane = st.Plane(p0, n)
    plane_info = st.PlaneIntersectionInfo()
    bvh.plane_all_intersections(plane, plane_info)

    # # method 1:
    # start_time = time.time()
    # result = [matrix[0:3, 0:3].dot(x) + matrix[0:3, 3] for x in plane_info.intersections]
    # print(time.time() - start_time)
    # print(result)
    # # method 2:
    # start_time = time.time()
    # intersections = np.array(plane_info.intersections).transpose()
    # result = list(matrix[0:3, 0:3].dot(intersections) + np.array(matrix[0:3, 3])[:,np.newaxis])
    # print(time.time() - start_time)
    # print(result)
    # # method 3:
    start_time = time.time()
    intersections = np.array(plane_info.intersections)
    result = list(intersections.dot(matrix[:3,:3]) + np.array(matrix[0:3, 3]))
    # print(time.time() - start_time)
    print(result)


def bvh_test():
    # p = Pool(5)
    # number_of_primitives = 64000
    #
    # for idx in range(number_of_primitives):
    #     center = (np.random.rand(3) - 0.5) * 100
    #     radius = (random() - 0.5) * 10
    #     primitives.append(st.Sphere(center, radius))

    middle_construction_time_avg = 0
    middle_intersection_time_avg = 0
    equalcounts_construction_time_avg = 0
    equalcounts_intersection_time_avg = 0
    sah_construction_time_avg = 0
    sah_interesection_time_avg = 0
    iterations = 1
    number_of_primitives = 50000

    for j in range(iterations):
        print('iteration:', j)
        for i in range(number_of_primitives):
            v0 = (np.random.rand(3) - 0.5) * 100
            v1 = (np.random.rand(3) - 0.5) * 100
            v2 = (np.random.rand(3) - 0.5) * 100
            primitives.append(st.Triangle(v0, v1, v2))

        x = np.array([0.0, 0.0, 0.0])
        normal = np.array([0.0, 1.0, 0.0])
        plane = st.Plane(x, normal)

        start_time = time.time()
        bvh = pyBVH.BVH(primitives, 'Middle')
        middle_construction_time_avg += time.time() - start_time

        plane_info = st.PlaneIntersectionInfo()
        start_time = time.time()
        result = bvh.plane_all_intersections(plane, plane_info)
        middle_intersection_time_avg += time.time() - start_time

        start_time = time.time()
        bvh = pyBVH.BVH(primitives, 'EqualCounts')
        equalcounts_construction_time_avg += time.time() - start_time

        plane_info = st.PlaneIntersectionInfo()
        start_time = time.time()
        result = bvh.plane_all_intersections(plane, plane_info)
        equalcounts_intersection_time_avg += time.time() - start_time

        start_time = time.time()
        bvh = pyBVH.BVH(primitives, 'SAH')
        sah_construction_time_avg += time.time() - start_time

        plane_info = st.PlaneIntersectionInfo()
        start_time = time.time()
        result = bvh.plane_all_intersections(plane, plane_info)
        sah_interesection_time_avg += time.time() - start_time

    print('Middle', middle_construction_time_avg / iterations, middle_intersection_time_avg / iterations)
    print('EqualCounts', equalcounts_construction_time_avg / iterations, equalcounts_intersection_time_avg / iterations)
    print('SAH', sah_construction_time_avg / iterations, sah_interesection_time_avg / iterations)

def segment_loop_test():
    plane = [array([-44.38325973, -53.129879, -18.99448078]), array([-44.46548332, -53.129879, -18.70555581]),
             array([-44.46548332, -53.129879, -18.70555581]), array([-40.65137103, -53.129879, -7.60944017]),
             array([-44.38325973, -53.129879, -18.99448078]), array([-37.39716897, -53.129879, -27.57872178]),
             array([-36.55294789, -53.129879, -27.79822431]), array([-36.98815045, -53.129879, -27.76465247]),
             array([-37.39716897, -53.129879, -27.57872178]), array([-37.22758847, -53.129879, -27.55818579]),
             array([-37.22758847, -53.129879, -27.55818579]), array([-36.98815045, -53.129879, -27.76465247]),
             array([-16.71650874, -53.129879, -33.91950783]), array([-36.55294789, -53.129879, -27.79822431]),
             array([-16.32343132, -53.129879, -34.19787622]), array([-16.71650874, -53.129879, -33.91950783]),
             array([-16.32343132, -53.129879, -34.19787622]), array([-15.64018579, -53.129879, -34.17737266]),
             array([-10.1568551, -53.129879, -35.18960355]), array([-15.64018579, -53.129879, -34.17737266]),
             array([-40.65137103, -53.129879, -7.60944017]), array([-40.56505984, -53.129879, -7.406419]),
             array([-40.56505984, -53.129879, -7.406419]), array([-40.38451575, -53.129879, -7.4027475]),
             array([-25.27183966, -53.129879, -2.0529753]), array([-39.99660972, -53.129879, -7.04152983]),
             array([-25.27183966, -53.129879, -2.0529753]), array([-24.81664856, -53.129879, -1.60096197]),
             array([-40.38451575, -53.129879, -7.4027475]), array([-39.99660972, -53.129879, -7.04152983]),
             array([-24.7334242, -53.129879, 11.08676318]), array([-24.81664856, -53.129879, -1.60096197]),
             array([-23.7108901, -53.129879, 11.27546475]), array([7.34718016, -53.129879, 16.59947791]),
             array([-24.7334242, -53.129879, 11.08676318]), array([-23.7108901, -53.129879, 11.27546475]),
             array([15.81169541, -53.129879, -32.1204035]), array([-10.1568551, -53.129879, -35.18960355]),
             array([17.28256856, -53.129879, -30.13199807]), array([15.81169541, -53.129879, -32.1204035]),
             array([17.28256856, -53.129879, -30.13199807]), array([17.70882314, -53.129879, -29.9200198]),
             array([19.31698471, -53.129879, -30.30349424]), array([17.70882314, -53.129879, -29.9200198]),
             array([35.51224451, -53.129879, -25.62643911]), array([19.31698471, -53.129879, -30.30349424]),
             array([35.33487935, -53.129879, -23.71458501]), array([29.5688736, -53.129879, -14.55606714]),
             array([30.73120597, -53.129879, -14.35811955]), array([29.5688736, -53.129879, -14.55606714]),
             array([36.10558012, -53.129879, -24.72763977]), array([35.51224451, -53.129879, -25.62643911]),
             array([35.33487935, -53.129879, -23.71458501]), array([36.10558012, -53.129879, -24.72763977]),
             array([21.19191807, -53.129879, 3.52940149]), array([20.6566063, -53.129879, 5.1127162]),
             array([8.88852837, -53.129879, 16.53493281]), array([7.34718016, -53.129879, 16.59947791]),
             array([8.88852837, -53.129879, 16.53493281]), array([20.6566063, -53.129879, 5.1127162]),
             array([24.18192211, -53.129879, 2.69320001]), array([31.67547913, -53.129879, -11.75198999]),
             array([30.73120597, -53.129879, -14.35811955]), array([31.67547913, -53.129879, -11.75198999]),
             array([24.18192211, -53.129879, 2.69320001]), array([21.19191807, -53.129879, 3.52940149])]
    segments = [[plane[idx * 2], plane[idx * 2 + 1]] for idx in range(int(len(plane) / 2))]
    segments =[[array([-44.233707  ,   0.09999847, -18.887403  ], dtype=float32), array([-44.246403  ,   0.09999847, -18.842804  ], dtype=float32)], [array([-44.246403  ,   0.09999847, -18.842804  ], dtype=float32), array([-40.34521   ,   0.09999847,  -7.493355  ], dtype=float32)], [array([-44.233707  ,   0.09999847, -18.887403  ], dtype=float32), array([-37.107513  ,   0.09999847, -27.6438    ], dtype=float32)], [array([-37.07106   ,   0.09999847, -27.653278  ], dtype=float32), array([-37.08985   ,   0.09999847, -27.651829  ], dtype=float32)], [array([-37.107513  ,   0.09999847, -27.6438    ], dtype=float32), array([-37.10019   ,   0.09999847, -27.642914  ], dtype=float32)], [array([-37.10019   ,   0.09999847, -27.642914  ], dtype=float32), array([-37.08985   ,   0.09999847, -27.651829  ], dtype=float32)], [array([-16.33817   ,   0.09999847, -34.051197  ], dtype=float32), array([-37.07106   ,   0.09999847, -27.653278  ], dtype=float32)], [array([-16.300957  ,   0.09999847, -34.07755   ], dtype=float32), array([-16.33817   ,   0.09999847, -34.051197  ], dtype=float32)], [array([-16.300957  ,   0.09999847, -34.07755   ], dtype=float32), array([-16.236275  ,   0.09999847, -34.075607  ], dtype=float32)], [array([-15.71717   ,   0.09999847, -34.171436  ], dtype=float32), array([-16.236275  ,   0.09999847, -34.075607  ], dtype=float32)], [array([-40.34521   ,   0.09999847,  -7.493355  ], dtype=float32), array([-40.334106  ,   0.09999847,  -7.4672403 ], dtype=float32)], [array([-40.334106  ,   0.09999847,  -7.4672403 ], dtype=float32), array([-40.310883  ,   0.09999847,  -7.466768  ], dtype=float32)], [array([-40.260986  ,   0.09999847,  -7.4203043 ], dtype=float32), array([-29.021431  ,   0.09999847,  -3.6124935 ], dtype=float32)], [array([-40.310883  ,   0.09999847,  -7.466768  ], dtype=float32), array([-40.260986  ,   0.09999847,  -7.4203043 ], dtype=float32)], [array([-24.660807  ,   0.09999847,  11.105849  ], dtype=float32), array([-24.667982  ,   0.09999847,  10.011905  ], dtype=float32)], [array([-24.667982  ,   0.09999847,  10.011905  ], dtype=float32), array([-13.456096  ,   0.09999847,   4.384096  ], dtype=float32)], [array([-24.655693  ,   0.09999847,  11.106793  ], dtype=float32), array([ 7.7350063 ,  0.09999847, 16.659246  ], dtype=float32)], [array([-24.660807  ,   0.09999847,  11.105849  ], dtype=float32), array([-24.655693  ,   0.09999847,  11.106793  ], dtype=float32)], [array([ 17.310785  ,   0.09999847, -30.26789   ], dtype=float32), array([-15.71717   ,   0.09999847, -34.171436  ], dtype=float32)], [array([ 18.40357   ,   0.09999847, -27.89112   ], dtype=float32), array([ -3.838113  ,   0.09999847, -26.2946    ], dtype=float32)], [array([ -3.838113  ,   0.09999847, -26.2946    ], dtype=float32), array([ 15.769805  ,   0.09999847, -19.993732  ], dtype=float32)], [array([-29.021431  ,   0.09999847,  -3.6124935 ], dtype=float32), array([ 15.769805  ,   0.09999847, -19.993732  ], dtype=float32)], [array([ 30.199728  ,   0.09999847, -26.46675   ], dtype=float32), array([ 18.40357   ,   0.09999847, -27.89112   ], dtype=float32)], [array([ 17.455063  ,   0.09999847, -30.072851  ], dtype=float32), array([ 17.310785  ,   0.09999847, -30.26789   ], dtype=float32)], [array([ 17.455063  ,   0.09999847, -30.072851  ], dtype=float32), array([ 17.496874  ,   0.09999847, -30.052057  ], dtype=float32)], [array([ 17.654615  ,   0.09999847, -30.089672  ], dtype=float32), array([ 17.496874  ,   0.09999847, -30.052057  ], dtype=float32)], [array([ 30.199728  ,   0.09999847, -26.46675   ], dtype=float32), array([ 17.654615  ,   0.09999847, -30.089672  ], dtype=float32)], [array([ 30.416508  ,   0.09999847, -14.724522  ], dtype=float32), array([ 35.544613  ,   0.09999847, -22.869822  ], dtype=float32)], [array([ 30.648972  ,   0.09999847, -14.684933  ], dtype=float32), array([ 30.416508  ,   0.09999847, -14.724522  ], dtype=float32)], [array([-13.456096  ,   0.09999847,   4.384096  ], dtype=float32), array([ 26.72128   ,   0.09999847, -10.466994  ], dtype=float32)], [array([ 26.72128   ,   0.09999847, -10.466994  ], dtype=float32), array([ 35.544613  ,   0.09999847, -22.869822  ], dtype=float32)], [array([21.254128  ,  0.09999847,  3.4981296 ], dtype=float32), array([21.165865  ,  0.09999847,  3.7591906 ], dtype=float32)], [array([ 7.881519  ,  0.09999847, 16.653112  ], dtype=float32), array([ 7.7350063 ,  0.09999847, 16.659246  ], dtype=float32)], [array([ 7.881519  ,  0.09999847, 16.653112  ], dtype=float32), array([21.165865  ,  0.09999847,  3.7591906 ], dtype=float32)], [array([21.747128  ,  0.09999847,  3.3602545 ], dtype=float32), array([ 30.837824  ,   0.09999847, -14.163713  ], dtype=float32)], [array([ 30.648972  ,   0.09999847, -14.684933  ], dtype=float32), array([ 30.837824  ,   0.09999847, -14.163713  ], dtype=float32)], [array([21.747128  ,  0.09999847,  3.3602545 ], dtype=float32), array([21.254128  ,  0.09999847,  3.4981296 ], dtype=float32)]]
    loops = []
    current_idx = 0
    to_visit_idxs = [idx for idx in range(1, len(segments))]
    visited_idxs = [current_idx]
    current_loop = []
    current_loop.append(segments[current_idx])
    current_segment = segments[current_idx]
    start_time = time.time()
    while True:
        found_new_segment = False
        for idx in to_visit_idxs:
            test_segment = segments[idx]
            comparison_0 = segments[idx][0] == current_segment[1]
            comparison_1 = segments[idx][1] == current_segment[1]
            if comparison_0.all():
                current_idx = idx
                current_loop.append(segments[idx])
                visited_idxs.append(idx)
                to_visit_idxs.remove(idx)
                found_new_segment = True
                current_segment = segments[idx]
                break
            if comparison_1.all():
                current_idx = idx
                current_loop.append([segments[idx][1], segments[idx][0]])
                visited_idxs.append(idx)
                to_visit_idxs.remove(idx)
                found_new_segment = True
                current_segment = [segments[idx][1], segments[idx][0]]
                break
        if not found_new_segment:
            loops.append(current_loop)
            if len(to_visit_idxs) == 0:
                break
            else:
                current_loop = []
                current_idx = to_visit_idxs[0]
                current_loop.append(segments[current_idx])
                to_visit_idxs.remove(current_idx)
                current_segment = segments[current_idx]
        found_new_segment = False
    print(time.time() - start_time)
    print(loops)
    l = np.array(loops).ravel()
    ll = np.vstack(l).ravel()
    lll = np.vstack(np.array(loops)).ravel()
    print( l )




if __name__=="__main__":
    segment_loop_test()