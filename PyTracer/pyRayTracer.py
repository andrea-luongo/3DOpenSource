# -*- coding: utf-8 -*-
"""
Created on Wed Jun 12 14:05:07 2019

@author: aluo
"""

import PyTracer.pyStructs as pst
import PyTracer.pyHelpers as hlp
import numpy as np
import PyTracer.pyScene as psc
import matplotlib.pyplot as plt
import random as rnd
#scene belongs to pyScene.scene
#ray belongs to pyStructs.ray 
def closest_hit(ray, scene):
    t_hit = np.inf
    for i, geometry in enumerate(scene.geometries):
        t, normal = geometry.intersect(ray)
        if t < t_hit:
            t_hit, obj_idx = t, i 
    # Return None if the ray does not intersect any object.
    if t == np.inf:
        return None, None, None, scene.background_color
    
    hit_point = ray.origin + t_hit * ray.direction
    color = scene.geometries[obj_idx].get_shade(ray, hit_point,normal,scene)
    return obj_idx, hit_point, normal, color  

    
    
#scene belongs to pyScene.scene
#ray belongs to pyStructs.ray   
def any_hit(ray, scene):
    t_hit = np.inf
    for i, geometry in enumerate(scene.geometries):
        t, normal = geometry.intersect(ray)
        if t < t_hit:
            t_hit, obj_idx = t, i 
            return t_hit, obj_idx
    
    return 
    
#scene belongs to pyScene.scene
def ray_trace_scene(scene, frames = 1):
    width = scene.camera.width
    height = scene.camera.height
    launch_dim = np.array([width, height])
    origin = scene.camera.eye
    U = scene.camera.U
    V = scene.camera.V
    W = scene.camera.W
    img = np.zeros((height, width, 3))
    rnd.seed(0)
    for f in range(frames):
        for h in range(height):
            if h % 10 == 0:
                print ((h / float(height) * 100 / frames + f / frames * 100), "%")
            for w in range(width):
                
                launch_idx = np.array([w, h])
                jitter = np.array([rnd.random(), rnd.random()])
                ip_coords = (launch_idx + jitter) / (launch_dim) * 2.0 - 1.0;
                direction = hlp.normalize(ip_coords[0]*U + ip_coords[1]*V + W);
                depth = 0
                seed = rnd.random()  
                ray = pst.Ray(origin, direction, 0.0, np.inf, depth, seed)
                obj_idx, hit_point, normal, color = closest_hit(ray, scene)
    #            if not traced:
    #                color = scene.background_color
    #            else:
    #                obj_idx, hit_point, normal, color = traced
                result = img[height - h - 1, w, :] * f
                img[height - h - 1, w, :] = (result + color) / (f + 1)
    
    plt.imsave('fig.png', img)
    



# def slice_geometry(geometry, layer_thickness = 18, pixel_size = 7.5, width = 512, height = 512, antialiasing_level = 1):
#
#     m_min = geometry.obj.bbox.m_min
#     m_max = geometry.obj.bbox.m_max
#     m_max_bottom = np.array([m_max[0], m_min[1], m_max[2]])
#     eye = np.array([(m_max_bottom[0]-m_min[0])/2, m_min[1], (m_max_bottom[2]-m_min[2])/2  ])
#     direction = np.array([0.0, 1.0, 0.0])
#     up = np.array([0.0,0.0,1.0])
#     camera = psc.Camera(eye, direction, up, 45, width, height)
#     launch_dim = np.array([width, height])
#     for h in range(height):
#         if h % 10 == 0:
#             # print ((h / float(height) * 100 / frames + f / frames * 100), "%")
#             for w in range(width):
#
#                 launch_idx = np.array([w, h])
#                 jitter = np.array([rnd.random(), rnd.random()])
#                 d = (launch_idx + jitter) / (launch_dim) * 2.0 - 1.0;
#                 origin = camera.eye + d[0] * camera.U + d[1] * camera.V
#                 depth = 0
#                 seed = rnd.random()
#                 ray = pst.Ray(origin, camera.direction, 0.0, np.inf, depth, seed)
#                 obj_idx, hit_point, normal, color = closest_hit(ray, scene)
#     #            if not traced:
#     #                color = scene.background_color
#     #            else:
#     #                obj_idx, hit_point, normal, color = traced
#                 result = img[height - h - 1, w, :] * f
#                 img[height - h - 1, w, :] = (result + color) / (f + 1)
#