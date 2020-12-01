# -*- coding: utf-8 -*-
"""
Created on Thu Jun 13 10:21:17 2019

@author: aluo
"""

import numpy as np
import random as rnd


machine_epsilon = np.finfo(np.float32).eps * 0.5


def normalize(x):
    if np.linalg.norm(x) > 0 :
        return x / np.linalg.norm(x)


# ROTATION AROUND ARBITRARY AXIS, ANGLE IS IN RADIANS
def rotate_around_axis(angle, axis):
    axis = normalize(axis)
    s = np.sin(angle)
    c = np.cos(angle)
    
    m_00 = axis[0] * axis[0] + (1.0 - axis[0] * axis[0] ) * c
    m_01 = axis[0] * axis[1] * (1.0 - c) - axis[2] * s
    m_02 = axis[0] * axis[2] * (1.0 - c) + axis[1] * s
    m_03 = 0
    m_0 = [m_00, m_01, m_02, m_03]
    
    m_10 = axis[0] * axis[1] * (1.0 - c) + axis[2] * s
    m_11 = axis[1] * axis[1] + (1.0 - axis[1] * axis[1] ) * c
    m_12 = axis[1] * axis[2] * (1.0 - c) - axis[0] * s
    m_13 = 0
    m_1 = [m_10, m_11, m_12, m_13]
    
    m_20 = axis[0] * axis[2] * (1.0 - c) - axis[1] * s
    m_21 = axis[1] * axis[2] * (1.0 - c) + axis[0] * s
    m_22 = axis[2] * axis[2] + (1.0 - axis[2] * axis[2] ) * c
    m_23 = 0
    m_2 = [m_20, m_21, m_22, m_23]
    
    m_30 = 0
    m_31 = 0
    m_32 = 0
    m_33 = 1
    m_3 = [m_30, m_31, m_32, m_33]
    
    rot_matrix = np.array([m_0, m_1, m_2, m_3])

    return rot_matrix


def rotate_x(angle):
    return rotate_around_axis(angle, np.array([1.0,0.0,0.0]))


def rotate_y(angle):
    return rotate_around_axis(angle, np.array([0.0,1.0,0.0]))


def rotate_z(angle):
    return rotate_around_axis(angle, np.array([0.0,0.0,1.0]))


def translate(position):
    m_0 = np.array([1.0, 0.0, 0.0, position[0]])
    m_1 = np.array([0.0, 1.0, 0.0, position[1]])
    m_2 = np.array([0.0, 0.0, 1.0, position[2]])
    m_3 = np.array([0.0, 0.0, 0.0, 1.0])
    translation_matrix = np.array([m_0, m_1, m_2, m_3])
    return translation_matrix


def scale(scaling):
    m_0 = np.array([scaling[0], 0.0, 0.0, 0.0])
    m_1 = np.array([0.0, scaling[1], 0.0, 0.0])
    m_2 = np.array([0.0, 0.0, scaling[2], 0.0])
    m_3 = np.array([0.0, 0.0, 0.0, 1])
    scaling_matrix = np.array([m_0, m_1, m_2, m_3])
    return scaling_matrix   


def spherical_direction(sin_theta, cos_theta, phi):
    sin_phi = np.sin(phi)
    cos_phi = np.cos(phi)
    return np.array([sin_theta * cos_phi, sin_theta*sin_phi, cos_theta])    


def rotate_to_normal(normal, v):
    if normal[2] < -0.99999:
        v_n = np.array([-v[1], -v[0], -v[2]])
    else:
        a = 1.0 / (1.0 + normal[2])
        b = - normal[0] * normal[1] * a
        v_0 = np.array([1.0 - normal[0]*normal[0]*a, b, -normal[0]]) * v[0]
        v_1 = np.array([b, 1.0 - normal[1] * normal[1] * a, -normal[1]]) *  v[1]
        v_2 = normal * v[2]
        v_n = v_0 + v_1 + v_2
    return v_n


def sample_cosine_weighted(normal, seed):
    rnd.seed(seed)
    cos_theta = np.sqrt(rnd.random())
    phi = 2.0 * np.pi * rnd.random()
    sin_theta = np.sqrt(1.0 - cos_theta*cos_theta)
    v = spherical_direction(sin_theta, cos_theta, phi)
    rotate_to_normal(normal, v)
    return v, seed + 2


def gamma(n):
    return (n * machine_epsilon) / ( 1 - n * machine_epsilon)
