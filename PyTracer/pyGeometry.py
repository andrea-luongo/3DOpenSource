import numpy as np
from PySide2.QtGui import QVector3D, QMatrix4x4, QVector2D
from PyTracer import pyBVH, pyStructs
from PySide2.QtCore import Signal, Slot, QFileInfo, QObject, QJsonDocument


class PyGeometry(QObject):
    update_physical_size = Signal(float, float, float)

    def __init__(self, filename='', vertices=[], normals=[], bbox_min=QVector3D(), bbox_max=QVector3D(), use_bvh=False):
        QObject.__init__(self)
        self.filename = filename
        self.geometry_name = QFileInfo(filename).baseName()
        self.vertices_list = np.array(vertices, dtype=np.float32).ravel()
        self.normals_list = np.array(normals, dtype=np.float32).ravel()
        self.bbox_min = bbox_min
        self.bbox_max = bbox_max
        self.unit_of_measurement = 1
        self.position = QVector3D()
        self.rotation = QVector3D()
        self.scale = QVector3D(1, 1, 1)
        self.translation_matrix = QMatrix4x4()
        self.rotation_matrix = QMatrix4x4()
        self.scale_matrix = QMatrix4x4()
        self.model_matrix = QMatrix4x4()
        self.bbox_translation_matrix = QMatrix4x4()
        self.transformed_bbox_min = QVector3D()
        self.transformed_bbox_max = QVector3D()
        self.bbox_width_mm = 0
        self.bbox_depth_mm = 0
        self.bbox_height_mm = 0
        self.bvh = None
        if use_bvh and len(self.vertices_list) > 0:
            triangle_primitives = []
            for triangle_idx in range(int(len(vertices) / 9)):
                triangle = vertices[triangle_idx * 9: triangle_idx * 9 + 9]
                triangle_primitives.append(pyStructs.Triangle(triangle[0:3], triangle[3:6], triangle[6:9]))
            self.bvh = pyBVH.BVH(triangle_primitives, 'EqualCounts')
        self.__update_bbox__()
        self.__update_model_matrix__()
        self.is_bbox_refined = True

    def __update_model_matrix__(self):
        self.model_matrix = self.bbox_translation_matrix * self.translation_matrix * self.rotation_matrix * self.scale_matrix
        self.model_matrix_array = np.asarray(self.model_matrix.copyDataTo(), np.float32)

    def __update_bbox__(self):
        model_matrix = self.translation_matrix * self.rotation_matrix * self.scale_matrix
        x_a = (model_matrix.column(0).toVector3D() * self.bbox_min.x()).toTuple()
        y_a = (model_matrix.column(1).toVector3D() * self.bbox_min.y()).toTuple()
        z_a = (model_matrix.column(2).toVector3D() * self.bbox_min.z()).toTuple()
        x_b = (model_matrix.column(0).toVector3D() * self.bbox_max.x()).toTuple()
        y_b = (model_matrix.column(1).toVector3D() * self.bbox_max.y()).toTuple()
        z_b = (model_matrix.column(2).toVector3D() * self.bbox_max.z()).toTuple()
        min_temp = np.minimum(x_a, x_b) + np.minimum(y_a, y_b) + np.minimum(z_a, z_b)
        max_temp = np.maximum(x_a, x_b) + np.maximum(y_a, y_b) + np.maximum(z_a, z_b)
        self.transformed_bbox_min = QVector3D(min_temp[0], min_temp[1], min_temp[2]) + model_matrix.column(3).toVector3D()
        self.transformed_bbox_max = QVector3D(max_temp[0], max_temp[1], max_temp[2]) + model_matrix.column(3).toVector3D()
        self.bbox_translation_matrix = QMatrix4x4()
        self.bbox_translation_matrix.translate(0.0,-self.transformed_bbox_min.y(), 0.0)
        self.bbox_width_mm = (self.transformed_bbox_max.x() - self.transformed_bbox_min.x())
        self.bbox_depth_mm = (self.transformed_bbox_max.z() - self.transformed_bbox_min.z())
        self.bbox_height_mm = (self.transformed_bbox_max.y() - self.transformed_bbox_min.y())
        self.update_physical_size.emit(self.bbox_width_mm, self.bbox_depth_mm, self.bbox_height_mm)

    def refine_bbox(self):
        if self.is_bbox_refined:
            return
        refined_bbox_max = QVector3D(0.0, 0.0, 0.0)
        refined_bbox_min = QVector3D(0.0, 0.0, 0.0)
        model_matrix = self.translation_matrix * self.rotation_matrix * self.scale_matrix
        for idx in range(int(len(self.vertices_list) / 3)):
            qv = model_matrix.map(QVector3D(self.vertices_list[3 * idx], self.vertices_list[3 * idx + 1], self.vertices_list[3 * idx + 2]))
            if idx > 0:
                min_temp = np.minimum(refined_bbox_min.toTuple(), qv.toTuple())
                max_temp = np.maximum(refined_bbox_max.toTuple(), qv.toTuple())
                refined_bbox_min = QVector3D(min_temp[0], min_temp[1], min_temp[2])
                refined_bbox_max = QVector3D(max_temp[0], max_temp[1], max_temp[2])
            else:
                refined_bbox_max = qv
                refined_bbox_min = qv
        self.transformed_bbox_max = refined_bbox_max
        self.transformed_bbox_min = refined_bbox_min
        self.bbox_translation_matrix = QMatrix4x4()
        self.bbox_translation_matrix.translate(0.0, -self.transformed_bbox_min.y(), 0.0)
        self.bbox_width_mm = (self.transformed_bbox_max.x() - self.transformed_bbox_min.x())
        self.bbox_depth_mm = (self.transformed_bbox_max.z() - self.transformed_bbox_min.z())
        self.bbox_height_mm = (self.transformed_bbox_max.y() - self.transformed_bbox_min.y())
        self.update_physical_size.emit(self.bbox_width_mm, self.bbox_depth_mm, self.bbox_height_mm)
        self.is_bbox_refined = True
        self.__update_model_matrix__()

    def set_rotation(self, new_rotation: QVector3D):
        self.rotation = new_rotation
        new_rotation_matrix = QMatrix4x4()
        new_rotation_matrix.rotate(self.rotation.x(), 1.0, 0.0, 0.0)
        new_rotation_matrix.rotate(self.rotation.y(), 0.0, 1.0, 0.0)
        new_rotation_matrix.rotate(self.rotation.z(), 0.0, 0.0, 1.0)
        self.rotation_matrix = new_rotation_matrix
        self.is_bbox_refined = False
        self.__update_bbox__()
        self.__update_model_matrix__()

    @Slot(int)
    def set_x_rotation(self, value):
        self.rotation.setX(value)
        new_rotation_matrix = QMatrix4x4()
        new_rotation_matrix.rotate(self.rotation.x(), 1.0, 0.0, 0.0)
        new_rotation_matrix.rotate(self.rotation.y(), 0.0, 1.0, 0.0)
        new_rotation_matrix.rotate(self.rotation.z(), 0.0, 0.0, 1.0)
        self.rotation_matrix = new_rotation_matrix
        self.is_bbox_refined = False
        self.__update_bbox__()
        self.__update_model_matrix__()

    @Slot(int)
    def set_y_rotation(self, value):
        self.rotation.setY(value)
        new_rotation_matrix = QMatrix4x4()
        new_rotation_matrix.rotate(self.rotation.x(), 1.0, 0.0, 0.0)
        new_rotation_matrix.rotate(self.rotation.y(), 0.0, 1.0, 0.0)
        new_rotation_matrix.rotate(self.rotation.z(), 0.0, 0.0, 1.0)
        self.rotation_matrix = new_rotation_matrix
        self.is_bbox_refined = False
        self.__update_bbox__()
        self.__update_model_matrix__()

    @Slot(int)
    def set_z_rotation(self, value):
        self.rotation.setZ(value)
        new_rotation_matrix = QMatrix4x4()
        new_rotation_matrix.rotate(self.rotation.x(), 1.0, 0.0, 0.0)
        new_rotation_matrix.rotate(self.rotation.y(), 0.0, 1.0, 0.0)
        new_rotation_matrix.rotate(self.rotation.z(), 0.0, 0.0, 1.0)
        self.rotation_matrix = new_rotation_matrix
        self.is_bbox_refined = False
        self.__update_bbox__()
        self.__update_model_matrix__()

    def set_scale(self, new_scale: QVector3D):
        self.scale = new_scale
        new_scale_matrix = QMatrix4x4()
        new_scale_matrix.scale(self.scale)
        new_scale_matrix.scale(self.unit_of_measurement)
        self.scale_matrix = new_scale_matrix
        self.__update_bbox__()
        self.__update_model_matrix__()

    @Slot(float)
    def set_x_scale(self, value):
        self.scale.setX(value)
        new_scale_matrix = QMatrix4x4()
        new_scale_matrix.scale(self.scale)
        new_scale_matrix.scale(self.unit_of_measurement)
        self.scale_matrix = new_scale_matrix
        self.__update_bbox__()
        self.__update_model_matrix__()

    @Slot(float)
    def set_y_scale(self, value):
        self.scale.setY(value)
        new_scale_matrix = QMatrix4x4()
        new_scale_matrix.scale(self.scale)
        new_scale_matrix.scale(self.unit_of_measurement)
        self.scale_matrix = new_scale_matrix
        self.__update_bbox__()
        self.__update_model_matrix__()

    @Slot(float)
    def set_z_scale(self, value):
        self.scale.setZ(value)
        new_scale_matrix = QMatrix4x4()
        new_scale_matrix.scale(self.scale)
        new_scale_matrix.scale(self.unit_of_measurement)
        self.scale_matrix = new_scale_matrix
        self.__update_bbox__()
        self.__update_model_matrix__()

    def set_position(self, new_position: QVector3D):
        self.position = new_position
        new_translation_matrix = QMatrix4x4()
        new_translation_matrix.translate(self.position)
        self.translation_matrix = new_translation_matrix
        self.__update_bbox__()
        self.__update_model_matrix__()

    @Slot(float)
    def set_x_pos(self, value):
        self.position.setX(value)
        new_translation_matrix = QMatrix4x4()
        new_translation_matrix.translate(self.position)
        self.translation_matrix = new_translation_matrix
        self.__update_bbox__()
        self.__update_model_matrix__()

    @Slot(float)
    def set_y_pos(self, value):
        self.position.setY(value)
        new_translation_matrix = QMatrix4x4()
        new_translation_matrix.translate(self.position)
        self.translation_matrix = new_translation_matrix
        self.__update_bbox__()
        self.__update_model_matrix__()

    @Slot(float)
    def set_z_pos(self, value):
        self.position.setZ(value)
        new_translation_matrix = QMatrix4x4()
        new_translation_matrix.translate(self.position)
        self.translation_matrix = new_translation_matrix
        self.__update_bbox__()
        self.__update_model_matrix__()

    @Slot(float)
    def set_unit_of_measurement(self, value):
        self.unit_of_measurement = value
        new_scale_matrix = QMatrix4x4()
        new_scale_matrix.scale(self.scale)
        new_scale_matrix.scale(self.unit_of_measurement)
        self.scale_matrix = new_scale_matrix
        self.is_bbox_refined = False
        self.__update_bbox__()
        self.__update_model_matrix__()

    def get_bbox_size_mm(self):
        return self.bbox_width_mm, self.bbox_depth_mm, self.bbox_height_mm

    def get_x_rot(self):
        return self.rotation.x()

    def get_y_rot(self):
        return self.rotation.y()

    def get_z_rot(self):
        return self.rotation.z()

    def get_x_scale(self):
        return self.scale.x()

    def get_y_scale(self):
        return self.scale.y()

    def get_z_scale(self):
        return self.scale.z()

    def get_x_pos(self):
        return self.position.x()

    def get_y_pos(self):
        return self.position.y()

    def get_z_pos(self):
        return self.position.z()

    def get_unit_of_measurement(self):
        return self.unit_of_measurement

    def get_model_matrix(self):
        return self.model_matrix

    def get_model_matrix_array(self):
        return self.model_matrix_array

    def get_normal_matrix_array(self, matrix=QMatrix4x4()):
        normal_matrix = (matrix * self.model_matrix).normalMatrix()
        return normal_matrix

    def get_normal_matrix_array(self, matrix=QMatrix4x4()):
        normal_matrix = (matrix * self.model_matrix).normalMatrix()
        normal_matrix_array = np.asarray(normal_matrix.data(), np.float32)
        return normal_matrix_array

    def get_vertices_list(self):
        return self.vertices_list

    def get_normals_list(self):
        return self.normals_list

    def get_transformed_min_bbox(self):
        return self.transformed_bbox_min

    def get_transformed_max_bbox(self):
        return self.transformed_bbox_max

    def get_bvh(self):
        return self.bvh

    def get_geometry_name(self):
        return self.geometry_name

    def number_of_triangles(self):
        return int(len(self.vertices_list) / 3)

    def get_parameters_dict(self):
        geometry_data = {}
        geometry_data['filename'] = self.filename
        parameters = {
            'unit_of_measurements': self.unit_of_measurement,
            'position': list(self.position.toTuple()),
            'rotation': list(self.rotation.toTuple()),
            'scale': list(self.scale.toTuple())
        }
        geometry_data['geometry_parameters'] = parameters
        return geometry_data

    def set_parameters_from_dict(self, parameters):
        self.set_unit_of_measurement(parameters['unit_of_measurements'])
        position = QVector3D(parameters['position'][0], parameters['position'][1], parameters['position'][2])
        self.set_position(position)
        rotation = QVector3D(parameters['rotation'][0], parameters['rotation'][1], parameters['rotation'][2])
        self.set_rotation(rotation)
        scale = QVector3D(parameters['scale'][0], parameters['scale'][1], parameters['scale'][2])
        self.set_scale(scale)





