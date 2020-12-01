# -*- coding: utf-8 -*-
"""
Created on Mon Jun 17 09:40:05 2019

@author: aluo
"""

import numpy as np
import PyTracer.pyHelpers as hlp
import PyTracer.pyStructs as pst
import PyTracer.pyRayTracer as prt


class DiffuseMaterial():
    
    def __init__(self, diff_color = np.array([0.7,0.2,0.2])):
        self.diff_color = diff_color
        
    def get_shade(self, ray, hit_pos, normal, scene):
        result = np.array( [0.0,0.0,0.0])
        if ray.depth > scene.max_depth:
            return result
        new_dir, ray.seed = hlp.sample_cosine_weighted(normal, ray.seed)
        new_ray = pst.Ray(hit_pos, new_dir, 0, np.inf, ray.depth + 1, ray.seed)
        obj_idx, hit_point, normal, color = prt.closest_hit(new_ray, scene)
        result = result + color * self.diff_color 
        ray.seed = new_ray.seed
        return result
        
        
        
        
        