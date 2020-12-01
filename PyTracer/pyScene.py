# -*- coding: utf-8 -*-
"""
Created on Thu Jun 13 10:41:42 2019

@author: aluo
"""
import numpy as np
import PyTracer.pyHelpers as hlp
import PyTracer.pyStructs as pst
import PyTracer.pyMaterials as pmt

class Camera():
    #fov in degrees
    def __init__(self, eye, lookat, up, fov, width, height):
        self.__eye= eye
        self.__lookat = lookat
        self.__up = up
        self.__fov = fov
        self.__width = width
        self.__height = height
        self.calculate_camera_variables()
        
    def calculate_camera_variables(self):
        W = self.__lookat - self.__eye
        w_len = np.linalg.norm(W)
        U = hlp.normalize(np.cross(W, self.__up))
        V = hlp.normalize(np.cross(U, W))
        v_len = w_len * np.tan(0.5 * self.__fov * np.pi / 180.0)
        V = V * v_len
        aspect_ratio = (1.0 * self.__width) / self.__width
        u_len = v_len * aspect_ratio
        U = U * u_len;
        self.__W = W
        self.__U = U
        self.__V = V

    @property 
    def W(self):
        return self.__W
    @property 
    def U(self):
        return self.__U  
    @property 
    def V(self):
        return self.__V
    @property 
    def eye(self):
        return self.__eye
    @eye.setter
    def eye(self,value):
        self.__eye = value
        self.calculate_camera_variables()
    @eye.deleter
    def eye(self):
        del self.__eye
    @property 
    def lookat(self):
        return self.__lookat
    @lookat.setter
    def lookat(self,value):
        self.__lookat = value
        self.calculate_camera_variables()
    @lookat.deleter
    def lookat(self):
        del self.__lookat        
    @property 
    def up(self):
        return self.__up
    @up.setter
    def up(self,value):
        self.__up = value
        self.calculate_camera_variables()
    @up.deleter
    def up(self):
        del self.__up   
    @property 
    def fov(self):
        return self.__fov
    @fov.setter
    def fov(self,value):
        self.__fov = value
        self.calculate_camera_variables()
    @fov.deleter
    def fov(self):
        del self.__fov 
    @property 
    def width(self):
        return self.__width
    @width.setter
    def width(self,value):
        self.__width = value
        self.calculate_camera_variables()
    @width.deleter
    def width(self):
        del self.__width
    @property 
    def height(self):
        return self.__height
    @height.setter
    def height(self,value):
        self.__height = value
        self.calculate_camera_variables()
    @height.deleter
    def height(self):
        del self.__height

class OrthographicCamera():
    def __init__(self, eye=np.array([0.0,0.0,0.0]), direction=np.array([0.0,0.0,-1.0]), up =np.array([0.0,1.0,0.0]), width=512, height=512):
        self.eye = eye
        self.direction = direction
        self.up = up
        self.width=width
        self.height = height
        self.fov = 45
    
    def calculate_camera_variables(self):
        W = self.__lookat - self.__eye
        w_len = np.linalg.norm(W)
        U = hlp.normalize(np.cross(W, self.__up))
        V = hlp.normalize(np.cross(U, W))
        v_len = w_len * np.tan(0.5 * self.__fov * np.pi / 180.0)
        V = V * v_len
        aspect_ratio = (1.0 * self.__width) / self.__width
        u_len = v_len * aspect_ratio
        U = U * u_len;
        self.__W = W
        self.__U = U
        self.__V = V



class Geometry():
    
    def __init__(self, obj: pst.Primitive, transform = pst.Transform(), material = pmt.DiffuseMaterial()):
        self.obj = obj
        self.material = material
        self.transform = transform
        
    def get_shade(self, ray, hit_pos, normal, scene):
        return self.material.get_shade(ray, hit_pos, normal, scene)
    
    def intersect(self, ray):
        origin_local = np.dot(self.transform.inverse_transformation_matrix, np.append(ray.origin,1.0))[0:-1]
        direction_local = hlp.normalize(np.dot(self.transform.inverse_transformation_matrix, np.append(ray.direction,0.0)))[0:-1]
        local_ray = pst.Ray(origin_local,direction_local, 0, np.inf)
        t_local, normal_local = self.obj.intersect(local_ray)
        hit_point_local = origin_local + t_local * direction_local
        hit_point = np.dot(self.transform.transformation_matrix, np.append(hit_point_local,1.0))[0:-1]
        t_hit = np.linalg.norm(ray.origin - hit_point)
        if t_hit > ray.t_min and t_hit < ray.t_max:
                #found intersection
                ray.t_max = t_hit
                normal = np.dot(self.transform.normal_matrix, np.append(normal_local,0.0))[0:-1]
                return t_hit, hlp.normalize(normal)
        else:
            return np.inf, None
        
        
class Light():
    
    def __init__(self, light_type, light_intensity, transform):
        self.light_type = light_type
        self.light_intensity = light_intensity
        self.transform = transform
        
  
class Scene():
    
    def __init__(self):
        self.__geometries = []
        self.__lights = []
        position = np.array([0.0,0.0,0.0])
        lookat = np.array([0.0,0.0,-1.0])
        up = np.array([0.0,1.0,0.0])
        fov = 45
        width = height = 512
        self.__camera = Camera(position,lookat,up,fov,width,height)
        self.background_color = np.array([1.0,1.0,1.0])
        self.max_depth = 10
    
    def add_geometry(self, g):
        self.__geometries.append(g)
        
    def remove_geometry(self, g):
        self.__geometries.remove(g)
        
    def add_light(self, l):
        self.__lights.append(l)
    def remove_light(self, l):
        self.__lights.remove(l)
        
    @property 
    def geometries(self):
        return self.__geometries   
    @property 
    def lights(self):
        return self.__lights   

    @property 
    def camera(self):
        return self.__camera