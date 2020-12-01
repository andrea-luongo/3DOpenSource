# -*- coding: utf-8 -*-
"""
Created on Wed Jun 12 14:24:44 2019

@author: aluo
"""
import numpy as np
from PyTracer import pyHelpers as hlp
from functools import reduce
from dataclasses import dataclass, field
from typing import List


@dataclass
class Segment:
    p_0: np.array
    p_1: np.array


class Plane:

    def __init__(self, x_0: np.array, normal: np.array):
        self.x_0 = x_0
        self.normal = hlp.normalize(normal)

    def dist_from_plane(self, x):
        return np.dot(self.normal, x - self.x_0)

    def on_plane(self, x: np.array):
        return np.abs(self.dist_from_plane(x)) < hlp.machine_epsilon

    def plane_segment_intersection(self, p_0: np.array, p_1: np.array):
        d_0 = self.dist_from_plane(p_0)
        d_1 = self.dist_from_plane(p_1)
        if d_0 * d_1 > 0:
            return False, None
        t = d_0 / (d_0 - d_1)
        p = p_0 + t * (p_1 - p_0)
        return True, p

@dataclass
class PlaneIntersectionInfo:
    intersections: List = field(default_factory=list)

class Ray:

    def __init__(self, origin: np.array, direction: np.array, t_min=0, t_max=np.inf, depth=0, seed=0):
        self.origin = origin
        # self.direction = hlp.normalize(direction)
        self.direction = direction
        self.t_min = t_min
        self.t_max = t_max
        self.depth = depth
        self.seed = seed


@dataclass
class RayIntersectionInfo:
    normal: np.array = None
    t_hits: List[float] = field(default_factory=list)


class BBox:

    def __init__(self, m_min=np.array([np.inf, np.inf, np.inf]), m_max=np.array([-np.inf, -np.inf, -np.inf])):
        self.m_min = m_min
        self.m_max = m_max
        # self.diagonal = self.m_max - self.m_min
        # self.maximum_extent = np.argmax(self.diagonal)
        # self.minimum_extent = np.argmin(self.diagonal)
        # d = self.diagonal
        # self.surface_area = 2 * (d[0] * d[1] + d[0] * d[2] + d[1] * d[2])
        # self.volume = d[0] * d[1] * d[2]

    def __getitem__(self, idx):
        if idx == 0:
            return self.m_min
        else:
            return self.m_max

    # @property
    # def m_min(self):
    #     return self.__m_min
    #
    # @property
    # def m_max(self):
    #     return self.__m_max

    @property
    def diagonal(self):
        return self.m_max - self.m_min

    def maximum_extent(self):
        return np.argmax(self.diagonal)

    def minimum_extent(self):
        return np.argmin(self.diagonal)

    def surface_area(self):
        d = self.diagonal
        return 2 * (d[0] * d[1] + d[0] * d[2] + d[1] * d[2])

    def volume(self):
        d = self.diagonal
        return d[0] * d[1] * d[2]

    def offset(self, point):
        o = point - self.m_min
        if self.m_max[0] > self.m_min[0]:
            o[0] /= self.m_max[0] - self.m_min[0]
        if self.m_max[1] > self.m_min[1]:
            o[1] /= self.m_max[1] - self.m_min[1]
        if self.m_max[2] > self.m_min[2]:
            o[2] /= self.m_max[2] - self.m_min[2]
        return o

    @staticmethod
    def union(bbox_0, bbox_1):
        m_min = np.minimum(bbox_0.m_min, bbox_1.m_min)
        m_max = np.maximum(bbox_0.m_max, bbox_1.m_max)
        return BBox(m_min, m_max)

    @staticmethod
    def list_union(box_list):
        # max_array = [box_list[idx].m_max for idx in range(len(box_list))]
        # min_array = [box_list[idx].m_min for idx in range(len(box_list))]
        # m_max = np.max(max_array, axis=0)
        # m_min = np.min(min_array, axis=0)
        m_max = reduce(np.maximum, [box_list[idx].m_max for idx in range(len(box_list))])
        m_min = reduce(np.minimum, [box_list[idx].m_min for idx in range(len(box_list))])
        return BBox(m_min, m_max)

    @staticmethod
    def bbox_point_union(bbox, point):
        m_min = np.minimum(bbox.m_min, point)
        m_max = np.maximum(bbox.m_max, point)
        return BBox(m_min, m_max)
    #
    @staticmethod
    def list_points_union(point_list):
        m_max = reduce(np.maximum, point_list)
        m_min = reduce(np.minimum, point_list)
        return BBox(m_min, m_max)

    def intersect(self, ray: Ray):
        t_0 = 0
        t_1 = ray.t_max
        for idx in range(3):
            inv_ray_dir = np.divide(1.0, ray.direction[idx])
            t_near = (self.m_min[idx] - ray.origin[idx]) * inv_ray_dir
            t_far = (self.m_max[idx] - ray.origin[idx]) * inv_ray_dir
            if t_near > t_far:
                t_near, t_far = t_far, t_near
            t_far *= 1 + 2 * hlp.gamma(3)
            t_0 = t_near if (t_near > t_0) else t_0
            t_1 = t_far if (t_far < t_1) else t_1
            if t_0 > t_1:
                return False, t_0, t_1
        return True, t_0, t_1

    def any_intersect(self, ray: Ray, inv_dir: np.array, dir_is_neg: np.array):
        t_min = (self[dir_is_neg[0]][0] - ray.origin[0]) * inv_dir[0]
        t_max = (self[1 - dir_is_neg[0]][0] - ray.origin[0]) * inv_dir[0]
        ty_min = (self[dir_is_neg[1]][1] - ray.origin[1]) * inv_dir[1]
        ty_max = (self[1 - dir_is_neg[1]][1] - ray.origin[1]) * inv_dir[1]
        t_max *= 1 + 2 * hlp.gamma(3)
        ty_max *= 1 + 2 * hlp.gamma(3)
        if t_min > ty_max or ty_min > t_max:
            return False
        t_min = ty_min if (ty_min > t_min) else t_min
        t_max = ty_max if (ty_max < t_max) else t_max
        tz_min = (self[dir_is_neg[2]][2] - ray.origin[2]) * inv_dir[2]
        tz_max = (self[1 - dir_is_neg[2]][2] - ray.origin[2]) * inv_dir[2]
        tz_max *= 1 + 2 * hlp.gamma(3)
        if t_min > tz_max or tz_min > t_max:
            return False
        t_min = tz_min if (tz_min > t_min) else t_min
        t_max = tz_max if (tz_max < t_max) else t_max
        return t_min < ray.t_max and t_max > 0

    def plane_any_intersect(self, plane: Plane):
        d_0 = plane.dist_from_plane(self.m_min)
        d_1 = plane.dist_from_plane(self.m_max)
        if d_1 * d_0 < 0.0:
            return True
        p_2 = np.array([self.m_min[0], self.m_min[1], self.m_max[2]])
        p_3 = np.array([self.m_max[0], self.m_max[1], self.m_min[2]])
        d_2 = plane.dist_from_plane(p_2)
        d_3 = plane.dist_from_plane(p_3)
        if d_2 * d_3 < 0.0:
            return True
        p_4 = np.array([self.m_min[0], self.m_max[1], self.m_max[2]])
        p_5 = np.array([self.m_max[0], self.m_min[1], self.m_min[2]])
        d_4 = plane.dist_from_plane(p_4)
        d_5 = plane.dist_from_plane(p_5)
        if d_4 * d_5 < 0.0:
            return True
        p_6 = np.array([self.m_min[0], self.m_max[1], self.m_min[2]])
        p_7 = np.array([self.m_max[0], self.m_min[1], self.m_max[2]])
        d_6 = plane.dist_from_plane(p_6)
        d_7 = plane.dist_from_plane(p_7)
        if d_6 * d_7 < 0.0:
            return True
        return False


class Transform:

    def __init__(self, position=np.array([0.0, 0.0, 0.0]), rotation=np.array([0.0, 0.0, 0.0]),
                 scaling=np.array([1.0, 1.0, 1.0])):
        self.__position = position
        self.__rotation = rotation
        self.__scaling = scaling
        self.compute_transform_matrix()

    def compute_transform_matrix(self):
        trans_matrix = hlp.translate(self.__position)
        scale_matrix = hlp.scale(self.__scaling)
        rot_matrix = np.dot(hlp.rotate_z(self.__rotation[2]),
                            np.dot(hlp.rotate_y(self.__rotation[1]), hlp.rotate_x(self.__rotation[0])))
        self.__transformation_matrix = np.dot(trans_matrix, np.dot(rot_matrix, scale_matrix))
        self.__inverse_transformation_matrix = np.linalg.inv(self.__transformation_matrix)
        self.__normal_matrix = self.__transformation_matrix.transpose()

    @property
    def transformation_matrix(self):
        return self.__transformation_matrix

    @property
    def inverse_transformation_matrix(self):
        return self.__inverse_transformation_matrix

    @property
    def normal_matrix(self):
        return self.__normal_matrix

    @property
    def position(self):
        return self.__position

    @position.setter
    def position(self, value):
        self.__position = value
        self.compute_transform_matrix()

    @position.deleter
    def position(self):
        del self.__position

    @property
    def scaling(self):
        return self.__scaling

    @scaling.setter
    def scaling(self, value):
        self.__scaling = value
        self.compute_transform_matrix()

    @scaling.deleter
    def scaling(self):
        del self.__scaling

    @property
    def rotation(self):
        return self.__rotation

    @rotation.setter
    def rotation(self, value):
        self.__rotation = value
        self.compute_transform_matrix()

    @rotation.deleter
    def rotation(self):
        del self.__rotation


class Primitive:

    def __init__(self):
        self.bbox = None
        self.compute_bbox()

    def compute_bbox(self):
        self.bbox = None

    def intersect(self, ray: Ray, info: RayIntersectionInfo):
        return False

    def any_intersect(self, ray: Ray):
        return False

    def all_intersections(self, ray: Ray, info: RayIntersectionInfo):
        return False

    def intersect_plane(self, plane: Plane, info: PlaneIntersectionInfo):
        return []


class Sphere(Primitive):

    def __init__(self, center, radius):
        self.__center = center
        self.__radius = radius
        self.bbox = None
        self.compute_bbox()

    def compute_bbox(self):
        m_min = self.__center - self.__radius
        m_max = self.__center + self.__radius
        self.bbox = BBox(m_min, m_max)

    @property
    def center(self):
        return self.__center

    @center.setter
    def center(self, value):
        self.__center = value
        self.compute_bbox()

    @center.deleter
    def center(self):
        del self.__center

    @property
    def radius(self):
        return self.__radius

    @radius.setter
    def radius(self, value):
        self.__radius = value
        self.compute_bbox()

    @radius.deleter
    def radius(self):
        del self.__radius

    def intersect(self, ray: Ray, info: RayIntersectionInfo):
        O = ray.origin - self.center
        b = np.dot(O, ray.direction)
        c = np.dot(O, O) - self.radius * self.radius
        disc = b * b - c
        if disc > 0.0:
            s_disc = np.sqrt(disc)
            t = -b - s_disc
            if ray.t_min < t < ray.t_max:
                n = (O + t * ray.direction) / self.radius
                ray.t_max = t
                info.normal = n
                if len(info.t_hits) > 0:
                    info.t_hits[0] = t
                else:
                    info.t_hits.append(t)
                return True
            t = -b + s_disc
            if ray.t_min < t < ray.t_max:
                n = (O + t * ray.direction) / self.radius
                ray.t_max = t
                info.normal = hlp.normalize(n)
                if len(info.t_hits) > 0:
                    info.t_hits[0] = t
                else:
                    info.t_hits.append(t)
                return True
        return False

    def any_intersect(self, ray: Ray):
        O = ray.origin - self.center
        b = np.dot(O, ray.direction)
        c = np.dot(O, O) - self.radius * self.radius
        disc = b * b - c
        if disc > 0.0:
            s_disc = np.sqrt(disc)
            t = -b - s_disc
            if ray.t_min < t < ray.t_max:
                return True
            t = -b + s_disc
            if ray.t_min < t < ray.t_max:
                return True
        return False

    def all_intersect(self, ray: Ray, info: RayIntersectionInfo):
        O = ray.origin - self.center
        b = np.dot(O, ray.direction)
        c = np.dot(O, O) - self.radius * self.radius
        disc = b * b - c
        hit = False
        if disc > 0.0:
            s_disc = np.sqrt(disc)
            t = -b - s_disc
            if ray.t_min < t < ray.t_max:
                n = (O + t * ray.direction) / self.radius
                info.t_hits.append(t)
                hit = True
            t = -b + s_disc
            if ray.t_min < t < ray.t_max:
                n = (O + t * ray.direction) / self.radius
                info.t_hits.append(t)
                hit = True
        return hit

    # not supported yet
    def intersect_plane(self, plane: Plane, info: PlaneIntersectionInfo):
        return False


class Triangle(Primitive):

    def __init__(self, v0, v1, v2):
        self.__v0 = v0
        self.__v1 = v1
        self.__v2 = v2
        self.bbox = None
        self.compute_bbox()

    def compute_bbox(self):
        area = np.linalg.norm(np.cross(self.__v1 - self.__v0, self.__v2 - self.__v0))
        if area > 0.0 and np.isfinite(area):
            m_min = np.minimum(np.minimum(self.__v0, self.__v1), self.__v2)
            m_max = np.maximum(np.maximum(self.__v0, self.__v1), self.__v2)
            self.bbox = BBox(m_min, m_max)

    @property
    def v0(self):
        return self.__v0

    @v0.setter
    def v0(self, value):
        self.__v0 = value
        self.compute_bbox()

    @v0.deleter
    def v0(self):
        del self.__v0

    @property
    def v1(self):
        return self.__v1

    @v1.setter
    def v1(self, value):
        self.__v1 = value
        self.compute_bbox()

    @v1.deleter
    def v1(self):
        del self.__v1

    @property
    def v2(self):
        return self.__v2

    @v2.setter
    def v2(self, value):
        self.__v2 = value
        self.compute_bbox()

    @v2.deleter
    def v2(self):
        del self.__v2

    def intersect(self, ray: Ray, info: RayIntersectionInfo):
        e0 = self.__v1 - self.__v0
        e1 = self.__v0 - self.__v2
        n = np.cross(e1, e0)
        e2 = (1.0 / np.dot(n, ray.direction)) * (self.__v0 - ray.origin)
        i = np.cross(ray.direction, e2)
        beta = np.dot(i, e1)
        gamma = np.dot(i, e0)
        t = np.dot(n, e2)
        if ray.t_max > t > ray.t_min and beta > 0.0 and gamma >= 0.0 and beta + gamma <= 1:
            ray.t_max = t
            info.normal = hlp.normalize(n)
            if len(info.t_hits) > 0:
                info.t_hits[0] = t
            else:
                info.t_hits.append(t)
            return True
        return False

    def any_intersect(self, ray: Ray):
        e0 = self.__v1 - self.__v0
        e1 = self.__v0 - self.__v2
        n = np.cross(e1, e0)
        e2 = (1.0 / np.dot(n, ray.direction)) * (self.__v0 - ray.origin)
        i = np.cross(ray.direction, e2)
        beta = np.dot(i, e1)
        gamma = np.dot(i, e0)
        t = np.dot(n, e2)
        if ray.t_max > t > ray.t_min and beta > 0.0 and gamma >= 0.0 and beta + gamma <= 1:
            return True
        return False

    def all_intersect(self, ray: Ray, info: RayIntersectionInfo):
        e0 = self.__v1 - self.__v0
        e1 = self.__v0 - self.__v2
        n = np.cross(e1, e0)
        e2 = np.true_divide(1.0, np.dot(n, ray.direction)) * (self.__v0 - ray.origin)
        i = np.cross(ray.direction, e2)
        beta = np.dot(i, e1)
        gamma = np.dot(i, e0)
        t = np.dot(n, e2)
        if ray.t_max > t > ray.t_min and beta > 0.0 and gamma >= 0.0 and beta + gamma <= 1:
            info.t_hits.append(t)
            return True
        return False

    def intersect_plane(self, plane: Plane, info: PlaneIntersectionInfo):
        hit = False
        intersect, p_0 = plane.plane_segment_intersection(self.v0, self.v1)
        if intersect:
            info.intersections.append(p_0)
            hit = True
        intersect, p_1 = plane.plane_segment_intersection(self.v1, self.v2)
        if intersect:
            info.intersections.append(p_1)
            hit = True
        intersect, p_2 = plane.plane_segment_intersection(self.v2, self.v0)
        if intersect:
            info.intersections.append(p_2)
            hit = True
        return hit
