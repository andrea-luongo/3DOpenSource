import numpy as np
from PySide2.QtWidgets import QOpenGLWidget
from PySide2.QtCore import Signal, Slot, QTimer, QTime, QFileInfo, QFile, QIODevice, QDate, QJsonArray, QJsonDocument, QRect, QTextStream
from PySide2.QtGui import QVector3D, QOpenGLFunctions, \
    QQuaternion, QOpenGLFramebufferObject, QOpenGLFramebufferObjectFormat, QImage, QMatrix4x4, Qt, QVector2D
from OpenGL import GL
import struct
from pathlib import Path
from helpers import geometry_loader
from helpers import slicer_helpers
from helpers.slicer_helpers import  MetalSlicingParameters
from helpers import my_shaders as ms
from PyTracer import pyBVH, pyStructs, pyGeometry
from itertools import compress


class MetalSlicer(QOpenGLWidget, QOpenGLFunctions):
    # update_physical_size = Signal(float, float, float)
    update_fps = Signal(float)
    update_slice_counts = Signal(float, float)

    def __init__(self, parent=None):
        QOpenGLWidget.__init__(self, parent)

        QOpenGLFunctions.__init__(self)
        self.__default_parameters = {}
        self.__load_default_parameters__()
        # printer variables
        self.laser_width_microns = self.__default_parameters['laser_width (microns)']
        self.building_area_width_mm = self.__default_parameters['building_area_width (mm)']
        self.building_area_height_mm = self.__default_parameters['building_area_height (mm)']
        self.default_infill_density = self.__default_parameters['infill_density']
        self.default_infill_overlap = self.__default_parameters['infill_overlap']
        self.default_infill_rotation = self.__default_parameters['infill_rotation']
        self.default_infill_laser_power = self.__default_parameters['infill_laser_power']
        self.default_infill_scan_speed = self.__default_parameters['infill_scan_speed (mm/min)']
        self.default_infill_duty_cycle = self.__default_parameters['infill_duty_cycle (%)']
        self.default_infill_frequency = self.__default_parameters['infill_frequency (Hz)']
        self.default_contour_laser_power = self.__default_parameters['contour_laser_power']
        self.default_contour_scan_speed = self.__default_parameters['contour_scan_speed (mm/min)']
        self.default_contour_duty_cycle = self.__default_parameters['contour_duty_cycle (%)']
        self.default_contour_frequency = self.__default_parameters['contour_frequency (Hz)']
        self.__number_of_decimals = 4
        # shader variables
        self.program_id = None
        self.slicer_program_id = None
        self.show_slices_program_id = None
        self.initialize_distance_field_program_id = None
        self.distance_field_pass_program_id = None
        self.copy_texture_program_id = None
        self.normalize_distance_field_program_id = None
        self.marching_squares_program_id = None
        self.multisample_fbo = None
        self.multitarget_fbo = None
        self.slicer_fbo = None
        self.distance_field_fbo = None
        self.contour_infill_fbo = None
        self.camera_matrix_location = None
        self.model_matrix_location = None
        self.projection_matrix_location = None
        self.eye_position_location = None
        self.look_at_location = None
        self.light_intensity_location = None
        self.position_location = None
        self.normal_location = None
        self.normal_matrix_location = None
        self.light_location = None
        self.ambient_location = None
        self.diffuse_location = None
        self.slicer_position_location = None
        self.slicer_camera_matrix_location = None
        self.slicer_model_matrix_location = None
        self.slicer_projection_matrix_location = None
        self.slicer_alpha_location = None
        self.show_slices_position_location = None
        self.show_slices_color_location = None
        self.show_slices_camera_matrix_location = None
        self.show_slices_model_matrix_location = None
        self.show_slices_projection_matrix_location = None
        self.show_slices_planar_thickness_location = None
        self.show_slices_vertical_thickness_location = None
        self.show_slices_slice_height_offset_location = None
        self.initialize_distance_field_position_location = None
        self.initialize_distance_field_texcoord_location = None
        self.initialize_distance_field_model_matrix_location = None
        self.initialize_distance_field_texture_location = None
        self.horizontal_lines_buffer = None
        self.vertical_lines_buffer = None
        self.distance_field_lines_position_location = None
        self.distance_field_image_size_location = None
        self.distance_field_read_texture_location = None
        self.distance_field_texture_mask_location = None
        self.copy_texture_position_location = None
        self.copy_texture_read_texture_location = None
        self.normalize_distance_field_position_location = None
        self.normalize_distance_field_texture_location = None
        self.normalize_distance_field_diagonal_location = None
        self.normalize_distance_field_model_matrix_location = None
        self.marching_squares_position_location = None
        self.marching_squares_texcoord_location = None
        self.marching_squares_model_matrix_location = None
        self.marching_squares_texture_location = None
        self.marching_squares_slice_height_location = None
        self.marching_squares_bbox_size_location = None
        self.marching_squares_bbox_origin_location = None
        self.marching_squares_image_size_location = None
        self.marching_squares_viewport_origin_location = None

        # camera variables
        self.w = 1
        self.h = 1
        self.camera_radius = 150
        self.camera_rotation = QQuaternion()
        self.eye = QVector3D(0.0, 1.50, 1.0)
        self.eye = self.camera_radius * self.camera_rotation.rotatedVector(self.eye)
        self.look_at = QVector3D(0.0, 1.0, 0.0)
        self.fov = 45
        self.up = QVector3D(0.0, 1.0, 0.0)
        self.camera_matrix = QMatrix4x4()
        self.camera_matrix.lookAt(self.eye, self.look_at, self.up)
        self.camera_matrix_array = np.asarray(self.camera_matrix.copyDataTo(), np.float32)
        self.perspective_matrix = QMatrix4x4()
        self.perspective_matrix_array = np.asarray(self.perspective_matrix.copyDataTo(), np.float32)

        # slicer variables
        self.slice_height_offset = 0.5
        self.show_slices = False
        self.bottom_displayed_slice = 0
        self.top_displayed_slice = 0
        self.slice_planar_thickness_percentage = 10
        self.slice_vertical_thickness_percentage = 10
        self.slicer_eye = QVector3D(0.0, 0.0, 0.0)
        self.slicer_look_at = QVector3D(0.0, 0.0, 0.0)
        self.slicer_up = QVector3D(0.0, 0.0, 0.0)
        self.slicer_camera_matrix = QMatrix4x4()
        self.slicer_camera_matrix_array = np.asarray(self.slicer_camera_matrix.copyDataTo(), np.float32)
        self.ortho_matrix = QMatrix4x4()
        self.ortho_matrix_array = np.asarray(self.ortho_matrix.copyDataTo(), np.float32)
        self.slice_width = self.building_area_width_mm
        self.slice_height = self.building_area_width_mm
        self.slice_thickness_microns = self.__default_parameters['slice_thickness (microns)']  # microns
        self.contour_strategies = ['Geometric', 'Image-Based', 'None']
        self.contour_strategy_idx = 0
        self.infill_strategies = ['Parallel Lines', 'ZigZag', 'None']
        self.infill_strategy_idx = 0
        self.current_slice = 0
        self.number_of_slices = 0
        self.is_slicing = False
        self.global_bbox_min = QVector3D(0.0, 0.0, 0.0)
        self.global_bbox_max = QVector3D(0.0, 0.0, 0.0)

        # quad plane variables
        self.quad_vertex_buffer = None
        self.quad_normal_buffer = None
        self.quad_texcoords_buffer = None
        self.quad_vertices = None
        self.quad_normals = None
        self.quad_texcoords = None
        self.quad_model_matrix = QMatrix4x4()
        self.quad_normal_matrix = self.quad_model_matrix.normalMatrix()
        self.quad_model_matrix_array = np.asarray(self.quad_model_matrix.copyDataTo(), np.float32)
        self.quad_normal_matrix_array = np.asarray(self.quad_normal_matrix.data(), np.float32)

        # geometry variables
        self.current_geometry_idx = 0
        self.geometries_loaded = 0
        self.geometries_list = []
        self.vertex_buffer_id_list = []
        self.normal_buffer_id_list = []

        # geometry specific slicing variables
        self.slicing_parameters_list = []
        self.contour_buffer_id_list = []
        self.infill_buffer_id_list = []
        self.contour_vertices_list = []
        self.infill_vertices_list = []

        # generic variables
        self.save_directory_name = ''
        self.previous_frame_count = 0
        self.previous_time = 0
        self.current_frame = 0
        self.__timer = None
        self.frameTimer = None
        self.mouse_last_pos = None

        # lighting variables
        self.light_intensity = QVector3D(1.0, 1.0, 1.0)
        self.light_direction = self.look_at - self.eye
        self.ambient_color = QVector3D(0.2, 0.2, 0.2)
        self.diffuse_color = QVector3D(0.7, 0.3, 0.0)
        self.selected_geometry_diffuse_color = QVector3D(1.0, 0.45, 0.45)
        self.quad_ambient_color = QVector3D(0.0, 0.3, 0.7)
        self.quad_diffuse_color = QVector3D(0.0, 0.0, 0.0)

        self.update_quad_scale()
        # self.save_default_parameters()

    def __append_slicing_default_parameters__(self):
        params = MetalSlicingParameters(self.default_infill_laser_power, self.default_infill_scan_speed,
                                        self.default_infill_duty_cycle, self.default_infill_frequency,
                                        self.default_infill_density, self.default_infill_overlap,
                                        self.default_infill_rotation, self.default_contour_laser_power,
                                        self.default_contour_scan_speed, self.default_contour_duty_cycle,
                                        self.default_contour_frequency)
        self.contour_vertices_list.append({'vertices': [], 'vertices_per_layer': [], 'layer_thickness': 0})
        self.infill_vertices_list.append({'vertices': [], 'vertices_per_layer': [], 'layer_thickness': 0})
        self.slicing_parameters_list.append(params)

    @Slot()
    def get_current_geometry(self):
        if self.geometries_loaded > 0:
            return self.geometries_list[self.current_geometry_idx]
        else:
            return None

    @Slot()
    def get_current_parameters(self):
        if self.geometries_loaded > 0:
            return self.slicing_parameters_list[self.current_geometry_idx]
        else:
            return None

    @Slot()
    def get_geometry(self, idx):
        if self.geometries_loaded > 0 and idx >= 0 and idx < self.geometries_loaded:
            return self.geometries_list[idx]
        else:
            return None

    @Slot(bool)
    def set_show_slices(self, value):
        self.show_slices = value

    @Slot(int)
    def set_top_displayed_slices(self, value):
        self.top_displayed_slice = value

    @Slot(int)
    def set_bottom_displayed_slices(self, value):
        self.bottom_displayed_slice = value

    @Slot(float)
    def set_slice_planar_thickness_percentage(self, value):
        self.slice_planar_thickness_percentage = value

    @Slot(float)
    def set_slice_vertical_thickness_percentage(self, value):
        self.slice_vertical_thickness_percentage = value

    @Slot(float)
    def set_laser_width(self, value):
        self.laser_width_microns = value
        self.update_quad_scale()

    @Slot(int)
    def set_building_area_width(self, value):
        self.building_area_width_mm = value
        self.update_quad_scale()

    @Slot(int)
    def set_building_area_height(self, value):
        self.building_area_height_mm = value
        self.update_quad_scale()

    def update_quad_scale(self):
        self.quad_model_matrix = QMatrix4x4()
        self.quad_model_matrix.scale(self.building_area_width_mm * 0.5, 1.0, self.building_area_height_mm * 0.5)
        self.quad_model_matrix_array = np.asarray(self.quad_model_matrix.copyDataTo(), np.float32)
        self.quad_normal_matrix = self.quad_model_matrix.normalMatrix()
        self.quad_normal_matrix_array = np.asarray(self.quad_normal_matrix.data(), np.float32)

    @Slot(float)
    def set_slice_thickness(self, value):
        self.slice_thickness_microns = value

    def __compute_global_bbox__(self):
        is_defined = False
        for idx in range(self.geometries_loaded):
            geometry = self.geometries_list[idx]
            if not is_defined:
                self.global_bbox_min = geometry.get_transformed_min_bbox()
                self.global_bbox_max = geometry.get_transformed_max_bbox()
                is_defined = True
            else:
                min_temp = np.minimum(self.global_bbox_min.toTuple(), geometry.get_transformed_min_bbox().toTuple())
                max_temp = np.maximum(self.global_bbox_max.toTuple(), geometry.get_transformed_max_bbox().toTuple())
                self.global_bbox_min = QVector3D(min_temp[0], min_temp[1], min_temp[2])
                self.global_bbox_max = QVector3D(max_temp[0], max_temp[1], max_temp[2])
        self.global_bbox_width_mm = self.global_bbox_max.x() - self.global_bbox_min.x()
        self.global_bbox_depth_mm = self.global_bbox_max.z() - self.global_bbox_min.z()
        self.global_bbox_height_mm = self.global_bbox_max.y() - self.global_bbox_min.y()

    @Slot()
    def prepare_for_slicing(self, directory='./'):
        if self.geometries_loaded == 0:
            return
        for idx in range(self.geometries_loaded):
            current_geometry = self.geometries_list[idx]
            current_geometry.refine_bbox()
            self.contour_vertices_list[idx] = {'vertices': [], 'vertices_per_layer': [], 'layer_thickness': self.slice_thickness_microns / 1000.0}
            self.infill_vertices_list[idx] = {'vertices': [], 'vertices_per_layer': [], 'layer_thickness': self.slice_thickness_microns / 1000.0}
        self.__compute_global_bbox__()
        self.is_slicing = True
        self.current_slice = 0
        slice_height_offset_mm = self.slice_thickness_microns * self.slice_height_offset / 1000
        self.number_of_slices = int(np.ceil(1000 * (self.global_bbox_height_mm - slice_height_offset_mm) / self.slice_thickness_microns))
        self.slice_width = int(np.ceil(1000 * self.global_bbox_width_mm / self.laser_width_microns))
        self.slice_height = int(np.ceil(1000 * self.global_bbox_depth_mm / self.laser_width_microns))
        self.save_directory_name = directory
        self.__initialize_slicer_opengl__()

    @Slot()
    def interrupt_slicing(self):
        if self.is_slicing:
            self.makeCurrent()
            self.is_slicing = False
            for idx in range(self.geometries_loaded):
                self.contour_vertices_list[idx] = {'vertices': [], 'vertices_per_layer': [], 'layer_thickness': 0}
                self.infill_vertices_list[idx] = {'vertices': [], 'vertices_per_layer': [], 'layer_thickness': 0}
            GL.glDisable(GL.GL_STENCIL_TEST)
            GL.glEnable(GL.GL_DEPTH_TEST)
            GL.glDisable(GL.GL_BLEND)
            self.distance_field_fbo.bindDefault()
            self.glClearColor(0.65, 0.9, 1, 1)
            self.update_slice_counts.emit(self.current_slice, self.number_of_slices)

    def initializeGL(self):
        self.initializeOpenGLFunctions()
        self.glClearColor(0.65, 0.9, 1, 1)
        GL.glEnable(GL.GL_DEPTH_TEST)
        self.load_quad()
        self.__timer = QTimer()
        self.__timer.timeout.connect(self.repaint)  # make it repaint when triggered
        self.__timer.start(0.0)
        self.previous_time = 0
        self.previous_frame_count = 0
        self.current_frame = 0
        self.frameTimer = QTime()
        self.frameTimer.start()
        self.init_shaders()

    def paintGL(self):
        if self.is_slicing:
            self.slice_next_layer()
        else:
            GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT | GL.GL_STENCIL_BUFFER_BIT)
            GL.glUseProgram(self.program_id)
            GL.glUniform3fv(self.light_location, 1, np.asarray(self.light_direction.toTuple(), np.float32))
            GL.glUniform3fv(self.light_intensity_location, 1, np.asarray(self.light_intensity.toTuple(), np.float32))

            GL.glUniformMatrix4fv(self.camera_matrix_location, 1, GL.GL_TRUE, self.camera_matrix_array)
            GL.glUniformMatrix4fv(self.projection_matrix_location, 1, GL.GL_TRUE, self.perspective_matrix_array)
            # DRAW PLANE
            GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.quad_vertex_buffer)
            GL.glEnableVertexAttribArray(self.position_location)
            GL.glVertexAttribPointer(self.position_location, 3, GL.GL_FLOAT, GL.GL_FALSE, 0, None)
            GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.quad_normal_buffer)
            GL.glEnableVertexAttribArray(self.normal_location)
            GL.glVertexAttribPointer(self.normal_location, 3, GL.GL_FLOAT, GL.GL_FALSE, 0, None)
            GL.glUniformMatrix4fv(self.model_matrix_location, 1, GL.GL_TRUE, self.quad_model_matrix_array)
            GL.glUniformMatrix3fv(self.normal_matrix_location, 1, GL.GL_TRUE, self.quad_normal_matrix_array)
            GL.glUniform3fv(self.ambient_location, 1, np.asarray(self.quad_ambient_color.toTuple(), np.float32))
            GL.glUniform3fv(self.diffuse_location, 1, np.asarray(self.quad_diffuse_color.toTuple(), np.float32))
            GL.glDrawArrays(GL.GL_TRIANGLE_FAN, 0, int(len(self.quad_vertices) / 3))
            # DRAW GEOMETRY
            if not self.show_slices:
                GL.glUniform3fv(self.ambient_location, 1, np.asarray(self.ambient_color.toTuple(), np.float32))
                for geometry_idx in range(self.geometries_loaded):
                    if geometry_idx == self.current_geometry_idx:
                        GL.glUniform3fv(self.diffuse_location, 1,
                                        np.asarray(self.selected_geometry_diffuse_color.toTuple(), np.float32))
                    else:
                        GL.glUniform3fv(self.diffuse_location, 1, np.asarray(self.diffuse_color.toTuple(), np.float32))

                    current_geometry = self.geometries_list[geometry_idx]
                    GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.vertex_buffer_id_list[geometry_idx])
                    GL.glEnableVertexAttribArray(self.position_location)
                    GL.glVertexAttribPointer(self.position_location, 3, GL.GL_FLOAT, GL.GL_FALSE, 0, None)
                    GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.normal_buffer_id_list[geometry_idx])
                    GL.glEnableVertexAttribArray(self.normal_location)
                    GL.glVertexAttribPointer(self.normal_location, 3, GL.GL_FLOAT, GL.GL_FALSE, 0, None)
                    GL.glUniformMatrix4fv(self.model_matrix_location, 1, GL.GL_TRUE, current_geometry.get_model_matrix_array())
                    GL.glUniformMatrix3fv(self.normal_matrix_location, 1, GL.GL_FALSE, current_geometry.get_normal_matrix_array(self.camera_matrix))
                    GL.glDrawArrays(GL.GL_TRIANGLES, 0, current_geometry.number_of_triangles())
            else:
                GL.glUseProgram(self.show_slices_program_id)
                GL.glUniformMatrix4fv(self.show_slices_camera_matrix_location, 1, GL.GL_TRUE,
                                      self.camera_matrix_array)
                GL.glUniformMatrix4fv(self.show_slices_projection_matrix_location, 1, GL.GL_TRUE, self.perspective_matrix_array)
                GL.glUniform1fv(self.show_slices_slice_height_offset_location, 1, self.slice_height_offset)
                line_width = self.laser_width_microns / 1000.0 * 0.5 * (self.slice_planar_thickness_percentage / 100.0)
                line_thickness = self.slice_thickness_microns / 1000.0 * (self.slice_vertical_thickness_percentage / 100.0)
                GL.glUniform1fv(self.show_slices_planar_thickness_location, 1, line_width)
                GL.glUniform1fv(self.show_slices_vertical_thickness_location, 1, line_thickness)
                for geometry_idx in range(self.geometries_loaded):
                    current_geometry = self.geometries_list[geometry_idx]
                    current_parameters = self.slicing_parameters_list[geometry_idx]
                    GL.glUniformMatrix4fv(self.show_slices_model_matrix_location, 1, GL.GL_TRUE,
                                          current_geometry.get_model_matrix_array())
                    GL.glUniform3fv(self.show_slices_color_location, 1, np.array([1.0, 0.0, 0.0], np.float32))
                    # DRAW CONTOUR
                    GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.contour_buffer_id_list[geometry_idx])
                    GL.glEnableVertexAttribArray(self.show_slices_position_location)
                    GL.glVertexAttribPointer(self.show_slices_position_location, 3, GL.GL_FLOAT, GL.GL_FALSE, 0, None)
                    try:
                        offset = int(sum(self.contour_vertices_list[geometry_idx]['vertices_per_layer'][0:self.bottom_displayed_slice]) / 3)
                        number_of_points = int(sum(self.contour_vertices_list[geometry_idx]['vertices_per_layer'][self.bottom_displayed_slice:self.top_displayed_slice]) / 3)
                    except:
                        offset = 0
                        number_of_points = 0
                    GL.glDrawArrays(GL.GL_LINES, offset, number_of_points)
                    # DRAW INFILL
                    GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.infill_buffer_id_list[geometry_idx])
                    GL.glUniform3fv(self.show_slices_color_location, 1, np.array([1.0, 1.0, 0.0], np.float32))
                    GL.glEnableVertexAttribArray(self.show_slices_position_location)
                    GL.glVertexAttribPointer(self.show_slices_position_location, 3, GL.GL_FLOAT, GL.GL_FALSE, 0, None)
                    try:
                        offset = int(sum(self.infill_vertices_list[geometry_idx]['vertices_per_layer'][0:self.bottom_displayed_slice]) / 3)
                        number_of_points = int(sum(self.infill_vertices_list[geometry_idx]['vertices_per_layer'][self.bottom_displayed_slice:self.top_displayed_slice]) / 3)
                    except:
                        offset = 0
                        number_of_points = 0
                    GL.glDrawArrays(GL.GL_LINES, offset, number_of_points)
                GL.glDisable(GL.GL_CULL_FACE)

        current_time = self.frameTimer.elapsed()
        dt = current_time - self.previous_time
        if dt > 500:
            fps = 1000.0 * (self.current_frame - self.previous_frame_count) / dt
            self.previous_time = current_time
            self.previous_frame_count = self.current_frame
            self.update_fps.emit(fps)
            if self.is_slicing:
                self.update_slice_counts.emit(self.current_slice, self.number_of_slices)
        self.current_frame += 1

    def resizeGL(self, w, h):
        self.glViewport(0, 0, w, h)
        self.w = w
        self.h = h
        self.perspective_matrix.setToIdentity()
        self.perspective_matrix.perspective(self.fov, w / h, 0.01, 100000.0)
        self.perspective_matrix_array = np.asarray(self.perspective_matrix.copyDataTo(), np.float32)
        self.camera_matrix.setToIdentity()
        self.camera_matrix.lookAt(self.eye, self.look_at, self.up)
        self.camera_matrix_array = np.asarray(self.camera_matrix.copyDataTo(), np.float32)

    def slice_next_layer(self):
        if self.geometries_loaded > 0:
            for geometry_idx in range(self.geometries_loaded):
                        self.__get_slice_contour(geometry_idx)
                        self.__get_slice_infill(geometry_idx)
            self.current_slice += 1
        if self.current_slice == self.number_of_slices:
            self.__load_slices_buffers__()
            self.__reset_default_opengl_buffer__()
            self.is_slicing = False
            self.update_slice_counts.emit(self.current_slice, self.number_of_slices)

    def __get_slice_contour(self, geometry_idx):
        strategy_idx = self.slicing_parameters_list[geometry_idx].get_contour_strategy_idx()
        if self.contour_strategies[strategy_idx] == 'Geometric':
            self.__compute_slice_plane_contour(geometry_idx)
        elif self.contour_strategies[strategy_idx] == 'Image-Based':
            self.__get_image_based_contour(geometry_idx)
        elif self.contour_strategies[strategy_idx] == 'None':
            self.contour_vertices_list[geometry_idx]['vertices'].append(np.array([], dtype=np.float32))
            self.contour_vertices_list[geometry_idx]['vertices_per_layer'].append(0)

    def __get_slice_infill(self, geometry_idx):
        strategy_idx = self.slicing_parameters_list[geometry_idx].get_infill_strategy_idx()
        if self.infill_strategies[strategy_idx] == 'Parallel Lines':
            self.__get_parallel_lines_infill(geometry_idx)
        elif self.infill_strategies[strategy_idx] == 'ZigZag':
            self.__get_zigzag_infill(geometry_idx)
        elif self.infill_strategies[strategy_idx] == 'None':
            self.infill_vertices_list[geometry_idx]['vertices'].append(np.array([], dtype=np.float32))
            self.infill_vertices_list[geometry_idx]['vertices_per_layer'].append(0)

    def __get_image_based_contour(self, geometry_idx):
        self.slicer_fbo.bind()
        GL.glClear(GL.GL_COLOR_BUFFER_BIT)
        GL.glClear(GL.GL_STENCIL_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
        GL.glEnable(GL.GL_STENCIL_TEST)
        GL.glDisable(GL.GL_DEPTH_TEST)
        GL.glUseProgram(self.slicer_program_id)
        self.__set_slicer_uniform_variables__(geometry_idx)
        self.__bind_geometry_buffer__(geometry_idx)
        self.__draw_geometry_slice__(geometry_idx)
        GL.glDisable(GL.GL_STENCIL_TEST)
        self.__extract_image_contour__(geometry_idx)

    def __initialize_slicer_opengl__(self):
        self.makeCurrent()
        self.glClearColor(0, 0, 0, 1)
        fbo_format = QOpenGLFramebufferObjectFormat()
        fbo_format.setAttachment(QOpenGLFramebufferObject.CombinedDepthStencil)
        fbo_format.setInternalTextureFormat(GL.GL_RGBA)
        self.slicer_fbo = QOpenGLFramebufferObject(self.slice_width, self.slice_height, fbo_format)
        self.slicer_textures_id = self.slicer_fbo.textures()
        fbo_format.setInternalTextureFormat(GL.GL_R8)
        print(self.slice_width, self.slice_height)
        self.marching_squares_cell_offset = 1
        self.contour_infill_fbo = QOpenGLFramebufferObject(self.slice_width + self.marching_squares_cell_offset, self.slice_height + self.marching_squares_cell_offset, fbo_format)
        self.contour_infill_fbo.addColorAttachment(self.slice_width+self.marching_squares_cell_offset, self.slice_height+self.marching_squares_cell_offset, GL.GL_RGB8)
        self.contour_infill_fbo.addColorAttachment(self.slice_width+self.marching_squares_cell_offset, self.slice_height+self.marching_squares_cell_offset, GL.GL_RGB32F)
        self.contour_infill_fbo.addColorAttachment(self.slice_width+self.marching_squares_cell_offset, self.slice_height+self.marching_squares_cell_offset, GL.GL_RGB32F)
        self.contour_infill_fbo.addColorAttachment(self.slice_width+self.marching_squares_cell_offset, self.slice_height+self.marching_squares_cell_offset, GL.GL_RGBA32F)
        self.contour_infill_fbo.addColorAttachment(self.slice_width+self.marching_squares_cell_offset, self.slice_height+self.marching_squares_cell_offset, GL.GL_RGBA32F)
        self.contour_infill_textures_id = self.contour_infill_fbo.textures()
        fbo_format.setInternalTextureFormat(GL.GL_RGB16)
        self.distance_field_fbo = QOpenGLFramebufferObject(self.slice_width, self.slice_height, fbo_format)
        self.distance_field_fbo.addColorAttachment(self.slice_width, self.slice_height, GL.GL_RGB16)
        self.distance_field_fbo.addColorAttachment(self.slice_width, self.slice_height, GL.GL_RGB16)
        self.distance_field_textures_id = self.distance_field_fbo.textures()
        self.__load_distance_field_lines__()

    def __set_slicer_uniform_variables__(self, geometry_idx=0):
        self.local_bbox_min = self.geometries_list[geometry_idx].get_transformed_min_bbox()
        self.local_bbox_max = self.geometries_list[geometry_idx].get_transformed_max_bbox()
        slicer_height = self.slice_thickness_microns * (self.current_slice + self.slice_height_offset) / 1000.0
        self.local_bbox_width = self.local_bbox_max.x() - self.local_bbox_min.x()
        self.local_bbox_depth = self.local_bbox_max.z() - self.local_bbox_min.z()
        self.ortho_matrix.setToIdentity()
        self.ortho_matrix.ortho(self.local_bbox_width / 2.0, -self.local_bbox_width / 2.0,
                                -self.local_bbox_depth / 2.0, self.local_bbox_depth / 2.0, 0.0,
                                slicer_height)
        self.ortho_matrix_array = np.asarray(self.ortho_matrix.copyDataTo(), np.float32)
        self.slicer_eye = QVector3D(0.5 * (self.local_bbox_min.x() + self.local_bbox_max.x()), 0, 0.5 * (self.local_bbox_min.z() + self.local_bbox_max.z()))
        self.slicer_look_at = self.slicer_eye + QVector3D(0.0, 1.0, 0.0)
        self.slicer_up = QVector3D(0.0, 0.0, 1.0)
        self.slicer_camera_matrix.setToIdentity()
        self.slicer_camera_matrix.lookAt(self.slicer_eye, self.slicer_look_at, self.slicer_up)
        self.slicer_camera_matrix_array = np.asarray(self.slicer_camera_matrix.copyDataTo(), np.float32)
        self.local_slice_width = int(np.ceil(1000 * self.local_bbox_width / self.laser_width_microns))
        self.local_slice_height = int(np.ceil(1000 * self.local_bbox_depth / self.laser_width_microns))
        self.viewport_origin = np.zeros(2, dtype=np.int32)
        self.viewport_origin[0] = int(np.floor(1000 * (self.global_bbox_max.x() - self.local_bbox_max.x()) / self.laser_width_microns))
        self.viewport_origin[1] = int(np.floor(1000 * (self.global_bbox_max.z() - self.local_bbox_max.z()) / self.laser_width_microns))
        self.glViewport(self.viewport_origin[0], self.viewport_origin[1], self.local_slice_width, self.local_slice_height)
        GL.glUniform3fv(self.slicer_color_location, 1, np.array([1.0, 1.0, 1.0], np.float32))
        GL.glUniformMatrix4fv(self.slicer_camera_matrix_location, 1, GL.GL_TRUE,
                              self.slicer_camera_matrix_array)
        GL.glUniformMatrix4fv(self.slicer_projection_matrix_location, 1, GL.GL_TRUE, self.ortho_matrix_array)
        GL.glUniform1f(self.slicer_alpha_location, 1.0)
        return True

    def __bind_geometry_buffer__(self, geometry_idx):
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.vertex_buffer_id_list[geometry_idx])
        GL.glEnableVertexAttribArray(self.slicer_position_location)
        GL.glVertexAttribPointer(self.slicer_position_location, 3, GL.GL_FLOAT, GL.GL_FALSE, 0, None)
        GL.glUniformMatrix4fv(self.slicer_model_matrix_location, 1, GL.GL_TRUE,
                              self.geometries_list[geometry_idx].get_model_matrix_array())

    def __draw_geometry_slice__(self, geometry_idx):
        # STENCIL SETUP
        GL.glDrawBuffers(1, [GL.GL_COLOR_ATTACHMENT0])
        GL.glStencilMask(0xFF)
        GL.glColorMask(GL.GL_FALSE, GL.GL_FALSE, GL.GL_FALSE, GL.GL_FALSE)
        GL.glStencilFunc(GL.GL_ALWAYS, 1, 0xFF)
        GL.glStencilOpSeparate(GL.GL_FRONT, GL.GL_KEEP, GL.GL_KEEP, GL.GL_DECR_WRAP)
        GL.glStencilOpSeparate(GL.GL_BACK, GL.GL_KEEP, GL.GL_KEEP, GL.GL_INCR_WRAP)
        GL.glDrawArrays(GL.GL_TRIANGLES, 0, self.geometries_list[geometry_idx].number_of_triangles())
        GL.glColorMask(GL.GL_TRUE, GL.GL_TRUE, GL.GL_TRUE, GL.GL_TRUE)
        GL.glStencilOp(GL.GL_KEEP, GL.GL_KEEP, GL.GL_KEEP)
        GL.glStencilFunc(GL.GL_NOTEQUAL, 0, 0xFF)
        GL.glDrawArrays(GL.GL_TRIANGLES, 0, self.geometries_list[geometry_idx].number_of_triangles())

    def __extract_image_contour__(self, geometry_idx):
        time = QTime()
        time.start()
        self.__marching_squares_pass__()
        t = time.elapsed()
        print("marching square pass time:", t)
        self.__marching_squares_meshing__(geometry_idx)
        print("marching square meshing time:", time.elapsed() - t)

    def __marching_squares_pass__(self):
        self.glViewport(self.viewport_origin[0], self.viewport_origin[1], self.local_slice_width + self.marching_squares_cell_offset, self.local_slice_height + self.marching_squares_cell_offset)
        self.contour_infill_fbo.bind()
        GL.glClearColor(0.0, 0.0, 0.0, 1.0)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT)
        GL.glUseProgram(self.marching_squares_program_id)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.quad_vertex_buffer)
        GL.glEnableVertexAttribArray(self.marching_squares_position_location)
        GL.glVertexAttribPointer(self.marching_squares_position_location, 3, GL.GL_FLOAT, GL.GL_FALSE, 0, None)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.quad_texcoords_buffer)
        quad_model_matrix = QMatrix4x4()
        quad_model_matrix.rotate(90, 1, 0, 0)
        quad_model_matrix_array = np.asarray(quad_model_matrix.copyDataTo(), np.float32)
        GL.glUniformMatrix4fv(self.marching_squares_model_matrix_location, 1, GL.GL_TRUE, quad_model_matrix_array)
        GL.glUniform1fv(self.marching_squares_slice_height_location, 1, self.slice_thickness_microns * (self.current_slice + self.slice_height_offset) / 1000.0)
        GL.glUniform2iv(self.marching_squares_image_size_location, 1, np.array([self.local_slice_width+1, self.local_slice_height+1], np.int32))
        GL.glUniform2fv(self.marching_squares_bbox_size_location, 1, np.array([self.local_bbox_width, self.local_bbox_depth], np.float32))
        GL.glUniform2fv(self.marching_squares_bbox_origin_location, 1, np.array([self.local_bbox_max.x(), self.local_bbox_min.z()], np.float32))
        GL.glUniform2iv(self.marching_squares_viewport_origin_location, 1, np.array([self.viewport_origin[0], self.viewport_origin[1]], np.int32))
        GL.glUniform1i(self.marching_squares_texture_location, 0)
        GL.glActiveTexture(GL.GL_TEXTURE0)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.slicer_textures_id[0])
        GL.glDrawBuffers(6, [GL.GL_COLOR_ATTACHMENT0, GL.GL_COLOR_ATTACHMENT1, GL.GL_COLOR_ATTACHMENT2, GL.GL_COLOR_ATTACHMENT3, GL.GL_COLOR_ATTACHMENT4, GL.GL_COLOR_ATTACHMENT5])
        GL.glDrawArrays(GL.GL_TRIANGLE_FAN, 0, int(len(self.quad_vertices) / 3))

    def __marching_squares_meshing__(self, geometry_idx):
        time = QTime()
        time.start()
        GL.glReadBuffer(GL.GL_COLOR_ATTACHMENT1)
        cell_labels = GL.glReadPixels(self.viewport_origin[0], self.viewport_origin[1], self.local_slice_width + self.marching_squares_cell_offset, self.local_slice_height + self.marching_squares_cell_offset, GL.GL_RGB, GL.GL_UNSIGNED_BYTE)
        cell_labels = np.frombuffer(cell_labels, dtype=np.ubyte)
        single_idxs = list(compress(range(len(cell_labels)), cell_labels == 255))
        double_idxs = list(compress(range(len(cell_labels)), cell_labels == 127))
        GL.glReadBuffer(GL.GL_COLOR_ATTACHMENT2)
        first_points = GL.glReadPixels(self.viewport_origin[0], self.viewport_origin[1], self.local_slice_width + self.marching_squares_cell_offset, self.local_slice_height + self.marching_squares_cell_offset, GL.GL_RGB, GL.GL_FLOAT)
        first_points = np.frombuffer(first_points, dtype=np.float32)
        first_points = first_points[single_idxs].reshape((-1, 3))
        GL.glReadBuffer(GL.GL_COLOR_ATTACHMENT3)
        second_points = GL.glReadPixels(self.viewport_origin[0], self.viewport_origin[1], self.local_slice_width + self.marching_squares_cell_offset, self.local_slice_height + self.marching_squares_cell_offset, GL.GL_RGB, GL.GL_FLOAT)
        second_points = np.frombuffer(second_points, dtype=np.float32)
        second_points = second_points[single_idxs].reshape((-1, 3))
        GL.glReadBuffer(GL.GL_COLOR_ATTACHMENT4)
        third_points = GL.glReadPixels(self.viewport_origin[0], self.viewport_origin[1], self.local_slice_width + self.marching_squares_cell_offset, self.local_slice_height + self.marching_squares_cell_offset, GL.GL_RGB, GL.GL_FLOAT)
        third_points = np.frombuffer(third_points, dtype=np.float32)
        third_points = third_points[double_idxs].reshape((-1, 3))
        GL.glReadBuffer(GL.GL_COLOR_ATTACHMENT5)
        fourth_points = GL.glReadPixels(self.viewport_origin[0], self.viewport_origin[1], self.local_slice_width + self.marching_squares_cell_offset, self.local_slice_height + self.marching_squares_cell_offset, GL.GL_RGB, GL.GL_FLOAT)
        fourth_points = np.frombuffer(fourth_points, dtype=np.float32)
        fourth_points = fourth_points[double_idxs].reshape((-1, 3))
        first_segments = np.empty((first_points.shape[0] + second_points.shape[0], 3), dtype=np.float32)
        second_segments = np.empty((third_points.shape[0] + fourth_points.shape[0], 3), dtype=np.float32)
        first_segments[0::2] = first_points
        first_segments[1::2] = second_points
        second_segments[0::2] = third_points
        second_segments[1::2] = fourth_points
        segments = np.concatenate((first_segments, second_segments), axis=0).ravel()
        if len(segments) > 0:
            self.contour_vertices_list[geometry_idx]['vertices'].append(segments)
            self.contour_vertices_list[geometry_idx]['vertices_per_layer'].append(len(segments))
        else:
            self.contour_vertices_list[geometry_idx]['vertices'].append(np.array([], dtype=np.float32))
            self.contour_vertices_list[geometry_idx]['vertices_per_layer'].append(0)

    def __compute_distance_field__(self):
        self.glViewport(0, 0, self.slice_width, self.slice_height)
        self.distance_field_fbo.bind()
        GL.glClearColor(0.0, 0.0, 0.0, 1.0)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT)
        self.__initialize_distance_field_textures__()
        self.__distance_field_horizontal_pass__()
        self.__distance_field_vertical_pass__()
        self.__normalize_distance_field__()

    def __bind_rendering_quad__(self):
        # DRAW PLANE
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.quad_vertex_buffer)
        GL.glEnableVertexAttribArray(self.initialize_distance_field_position_location)
        GL.glVertexAttribPointer(self.initialize_distance_field_position_location, 3, GL.GL_FLOAT, GL.GL_FALSE, 0, None)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.quad_texcoords_buffer)
        GL.glEnableVertexAttribArray(self.initialize_distance_field_texcoord_location)
        GL.glVertexAttribPointer(self.initialize_distance_field_texcoord_location, 2, GL.GL_FLOAT, GL.GL_FALSE, 0, None)
        quad_model_matrix = QMatrix4x4()
        quad_model_matrix.rotate(90, 1, 0, 0)
        quad_model_matrix_array = np.asarray(quad_model_matrix.copyDataTo(), np.float32)
        GL.glUniformMatrix4fv(self.initialize_distance_field_model_matrix_location, 1, GL.GL_TRUE, quad_model_matrix_array)

    def __initialize_distance_field_textures__(self):
        GL.glUseProgram(self.initialize_distance_field_program_id)
        self.__bind_rendering_quad__()
        GL.glUniform1i(self.initialize_distance_field_texture_location, 0)
        GL.glActiveTexture(GL.GL_TEXTURE0)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.slicer_textures_id[0])
        GL.glDrawBuffers(2, [GL.GL_COLOR_ATTACHMENT1, GL.GL_COLOR_ATTACHMENT2])
        GL.glDrawArrays(GL.GL_TRIANGLE_FAN, 0, int(len(self.quad_vertices) / 3))

    def __bind_horizontal_lines__(self):
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.horizontal_lines_buffer)
        GL.glEnableVertexAttribArray(self.distance_field_lines_position_location)
        GL.glVertexAttribPointer(self.distance_field_lines_position_location, 3, GL.GL_FLOAT, GL.GL_FALSE, 0, None)
        GL.glUniform2iv(self.distance_field_image_size_location, 1, np.array([self.slice_width, self.slice_height], dtype=np.int32))
        GL.glEnableVertexAttribArray(self.copy_texture_position_location)
        GL.glVertexAttribPointer(self.copy_texture_position_location, 3, GL.GL_FLOAT, GL.GL_FALSE, 0, None)

    def __bind_vertical_lines__(self):
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.vertical_lines_buffer)
        GL.glEnableVertexAttribArray(self.distance_field_lines_position_location)
        GL.glVertexAttribPointer(self.distance_field_lines_position_location, 3, GL.GL_FLOAT, GL.GL_FALSE, 0, None)
        GL.glUniform2iv(self.distance_field_image_size_location, 1, np.array([self.slice_width, self.slice_height], dtype=np.int32))
        GL.glEnableVertexAttribArray(self.copy_texture_position_location)
        GL.glVertexAttribPointer(self.copy_texture_position_location, 3, GL.GL_FLOAT, GL.GL_FALSE, 0, None)

    def __distance_field_horizontal_pass__(self):
        GL.glUseProgram(self.distance_field_pass_program_id)
        self.__bind_vertical_lines__()
        GL.glUniform1i(self.distance_field_read_texture_location, 1)
        ######################################################
        # left to right pass
        left_to_right_mask = np.array([-1, 1, -1, 0, -1, -1], np.float32)
        GL.glUniformMatrix3x2fv(self.distance_field_texture_mask_location, 1, GL.GL_FALSE, left_to_right_mask)
        GL.glActiveTexture(GL.GL_TEXTURE1)
        for idx in range(1, self.slice_width):
            write_buffer = GL.GL_COLOR_ATTACHMENT1 + (idx + 1) % 2
            read_buffer = self.distance_field_textures_id[(idx) % 2 + 1]
            GL.glBindTexture(GL.GL_TEXTURE_2D, read_buffer)
            GL.glDrawBuffers(1, [write_buffer])
            GL.glDrawArrays(GL.GL_LINES, 0 + idx * 2, 2)
        ######################################################
        # copy line pass
        write_buffer = GL.GL_COLOR_ATTACHMENT1 + (idx) % 2
        read_buffer = self.distance_field_textures_id[(idx + 1) % 2 + 1]
        GL.glUseProgram(self.copy_texture_program_id)
        GL.glUniform1i(self.copy_texture_read_texture_location, 2)
        GL.glActiveTexture(GL.GL_TEXTURE2)
        GL.glBindTexture(GL.GL_TEXTURE_2D, read_buffer)
        GL.glDrawBuffers(1, [write_buffer])
        GL.glDrawArrays(GL.GL_LINES, 0 + idx * 2, 2)
        #######################################################
        # right to left pass
        GL.glUseProgram(self.distance_field_pass_program_id)
        right_to_left_mask = np.array([1, 1, 1, 0, 1, -1], np.float32)
        GL.glUniformMatrix3x2fv(self.distance_field_texture_mask_location, 1, GL.GL_FALSE, right_to_left_mask)
        GL.glActiveTexture(GL.GL_TEXTURE1)
        for idx in range(self.slice_width - 2, -1, -1):
            write_buffer = GL.GL_COLOR_ATTACHMENT1 + (idx) % 2
            read_buffer = self.distance_field_textures_id[(idx + 1) % 2 + 1]
            GL.glBindTexture(GL.GL_TEXTURE_2D, read_buffer)
            GL.glDrawBuffers(1, [write_buffer])
            GL.glDrawArrays(GL.GL_LINES, 0 + idx * 2, 2)
        # ######################################################
        # # merge textures pass
        GL.glUseProgram(self.copy_texture_program_id)
        GL.glUniform1i(self.copy_texture_read_texture_location, 2)
        GL.glActiveTexture(GL.GL_TEXTURE2)
        for idx in range(self.slice_width):
            write_buffer = GL.GL_COLOR_ATTACHMENT1 + (idx + 1) % 2
            read_buffer = self.distance_field_textures_id[(idx) % 2 + 1]
            GL.glBindTexture(GL.GL_TEXTURE_2D, read_buffer)
            GL.glDrawBuffers(1, [write_buffer])
            GL.glDrawArrays(GL.GL_LINES, 0 + idx * 2, 2)

    def __distance_field_vertical_pass__(self):
        ######################################################
        # top to bottom pass
        GL.glUseProgram(self.distance_field_pass_program_id)
        self.__bind_horizontal_lines__()
        GL.glUniform1i(self.distance_field_read_texture_location, 1)
        top_to_bottom_mask = np.array([-1, 1, 0, 1, 1, 1], np.float32)
        GL.glUniformMatrix3x2fv(self.distance_field_texture_mask_location, 1, GL.GL_FALSE, top_to_bottom_mask)
        GL.glActiveTexture(GL.GL_TEXTURE1)
        for idx in range(self.slice_height):
            write_buffer = GL.GL_COLOR_ATTACHMENT1 + (idx + 1) % 2
            read_buffer = self.distance_field_textures_id[(idx) % 2 + 1]
            GL.glBindTexture(GL.GL_TEXTURE_2D, read_buffer)
            GL.glDrawBuffers(1, [write_buffer])
            GL.glDrawArrays(GL.GL_LINES, 0 + idx * 2, 2)
        ######################################################
        # copy line pass
        write_buffer = GL.GL_COLOR_ATTACHMENT1 + (idx) % 2
        read_buffer = self.distance_field_textures_id[(idx + 1) % 2 + 1]
        GL.glUseProgram(self.copy_texture_program_id)
        GL.glUniform1i(self.copy_texture_read_texture_location, 2)
        GL.glActiveTexture(GL.GL_TEXTURE2)
        GL.glBindTexture(GL.GL_TEXTURE_2D, read_buffer)
        GL.glDrawBuffers(1, [write_buffer])
        GL.glDrawArrays(GL.GL_LINES, 0 + idx * 2, 2)
        #######################################################
        # bottom to top pass
        GL.glUseProgram(self.distance_field_pass_program_id)
        bottom_to_top_mask = np.array([-1, -1, 0, -1, 1, -1], np.float32)
        GL.glUniformMatrix3x2fv(self.distance_field_texture_mask_location, 1, GL.GL_FALSE, bottom_to_top_mask)
        GL.glActiveTexture(GL.GL_TEXTURE1)
        for idx in range(self.slice_width - 2, -1, -1):
            write_buffer = GL.GL_COLOR_ATTACHMENT1 + (idx) % 2
            read_buffer = self.distance_field_textures_id[(idx + 1) % 2 + 1]
            GL.glBindTexture(GL.GL_TEXTURE_2D, read_buffer)
            GL.glDrawBuffers(1, [write_buffer])
            GL.glDrawArrays(GL.GL_LINES, 0 + idx * 2, 2)
        # ######################################################
        # # merge textures pass
        GL.glUseProgram(self.copy_texture_program_id)
        GL.glUniform1i(self.copy_texture_read_texture_location, 2)
        GL.glActiveTexture(GL.GL_TEXTURE2)
        for idx in range(self.slice_width):
            write_buffer = GL.GL_COLOR_ATTACHMENT1 + (idx + 1) % 2
            read_buffer = self.distance_field_textures_id[(idx) % 2 + 1]
            GL.glBindTexture(GL.GL_TEXTURE_2D, read_buffer)
            GL.glDrawBuffers(1, [write_buffer])
            GL.glDrawArrays(GL.GL_LINES, 0 + idx * 2, 2)

    def __normalize_distance_field__(self):
        # DRAW PLANE
        GL.glUseProgram(self.normalize_distance_field_program_id)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.quad_vertex_buffer)
        GL.glEnableVertexAttribArray(self.normalize_distance_field_position_location)
        GL.glVertexAttribPointer(self.normalize_distance_field_position_location, 3, GL.GL_FLOAT, GL.GL_FALSE, 0, None)

        quad_model_matrix = QMatrix4x4()
        quad_model_matrix.rotate(90, 1, 0, 0)
        quad_model_matrix_array = np.asarray(quad_model_matrix.copyDataTo(), np.float32)
        GL.glUniformMatrix4fv(self.normalize_distance_field_model_matrix_location, 1, GL.GL_TRUE, quad_model_matrix_array)
        image_diagonal = np.sqrt(self.slice_width**2 + self.slice_height**2)
        GL.glUniform1f(self.normalize_distance_field_diagonal_location, image_diagonal)
        GL.glUniform1i(self.normalize_distance_field_texture_location, 3)
        GL.glActiveTexture(GL.GL_TEXTURE3)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.distance_field_textures_id[1])
        GL.glDrawBuffers(1, [GL.GL_COLOR_ATTACHMENT0])
        GL.glDrawArrays(GL.GL_TRIANGLE_FAN, 0, int(len(self.quad_vertices) / 3))

    def __render_slice_to_screen__(self, fbo, colorAttachmentIdx=0):
        aspect_ratio = self.slice_width / self.slice_height
        rect_height = self.h
        rect_width = rect_height * aspect_ratio
        if rect_width < self.w:
            buffer_rect = QRect(self.w * 0.5 - rect_width * 0.5, 0, rect_width, rect_height)
        else:
            rect_width = self.w
            rect_height = self.w / aspect_ratio
            buffer_rect = QRect(0, self.h * 0.5 - rect_height * 0.5, rect_width, rect_height)
        QOpenGLFramebufferObject.blitFramebuffer(None, buffer_rect, fbo,
                                                 QRect(0, 0, self.slice_width, self.slice_height),
                                                 GL.GL_COLOR_BUFFER_BIT,
                                                 GL.GL_NEAREST, colorAttachmentIdx, 0)

    def __save_slice_to_disk__(self, fbo, colorAttachmentIdx=0, extra_name=''):
        fbo_image = QImage(fbo.toImage(True, colorAttachmentIdx)).convertToFormat(QImage.Format_RGBX64)
        layer_name = self.save_directory_name + '/layer_' + str(self.current_slice) + extra_name + '.png'
        fbo_image.save(layer_name)

    def __reset_default_opengl_buffer__(self):
        GL.glDisable(GL.GL_STENCIL_TEST)
        GL.glEnable(GL.GL_DEPTH_TEST)
        self.distance_field_fbo.bindDefault()
        self.glClearColor(0.65, 0.9, 1, 1)

    def __load_distance_field_lines__(self):
        self.horizontal_lines_buffer = GL.glGenBuffers(1)
        self.vertical_lines_buffer = GL.glGenBuffers(1)
        vertical_lines = []
        horizontal_lines = []
        horizontal_pixel_offset = 2.0 / self.slice_width
        vertical_pixel_offset = 2.0 / self.slice_height
        vertical_offsets = np.linspace(-1 + vertical_pixel_offset, 1, self.slice_height)
        horizontal_offsets = np.linspace(-1 + horizontal_pixel_offset, 1, self.slice_width)
        for idx in range(self.slice_width):
            vertical_lines.append(horizontal_offsets[idx])
            vertical_lines.append(-1)
            vertical_lines.append(0)
            vertical_lines.append(horizontal_offsets[idx])
            vertical_lines.append(1)
            vertical_lines.append(0)
        for idx in range(self.slice_height):
            horizontal_lines.append(-1)
            horizontal_lines.append(vertical_offsets[idx])
            horizontal_lines.append(0)
            horizontal_lines.append(1)
            horizontal_lines.append(vertical_offsets[idx])
            horizontal_lines.append(0)
        vertical_lines = np.array(vertical_lines)
        horizontal_lines = np.array(horizontal_lines)
        vertical_lines = np.array(vertical_lines, dtype=np.float32)
        horizontal_lines = np.array(horizontal_lines, dtype=np.float32)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.horizontal_lines_buffer)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, horizontal_lines.nbytes, horizontal_lines, GL.GL_STATIC_DRAW)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.vertical_lines_buffer)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, vertical_lines.nbytes, vertical_lines, GL.GL_STATIC_DRAW)

    def __compute_slice_plane_contour(self, geometry_idx):
        time = QTime()
        time.start()
        current_geometry = self.geometries_list[geometry_idx]
        slice_height = self.slice_thickness_microns * (self.current_slice + self.slice_height_offset) / 1000.0
        transformation_matrix = current_geometry.get_model_matrix()
        inverse_matrix, _ = transformation_matrix.inverted()
        normal_matrix = np.array(inverse_matrix.normalMatrix().data(), dtype=np.float32).reshape(3, 3).transpose()
        inverse_matrix = np.array(inverse_matrix.data(), dtype=np.float32).reshape(4, 4).transpose()
        transformation_matrix = np.array(transformation_matrix.data(), dtype=np.float32).reshape(4, 4).transpose()
        plane_x0 = inverse_matrix.dot(np.array([0.0, slice_height, 0.0, 1.0], dtype=np.float32))[0:3]
        plane_normal = normal_matrix.dot(np.array([0.0, 1.0, 0.0], dtype=np.float32))
        slice_plane = pyStructs.Plane(plane_x0, plane_normal)
        slice_plane_info = pyStructs.PlaneIntersectionInfo()
        current_geometry.get_bvh().plane_all_intersections(slice_plane, slice_plane_info)
        if len(slice_plane_info.intersections) > 0:
            slice_contour = (np.array(slice_plane_info.intersections, dtype=np.float32).dot(transformation_matrix[:3, :3].transpose())
                             + np.array(transformation_matrix[0:3, 3])).ravel()
            self.contour_vertices_list[geometry_idx]['vertices'].append(slice_contour)
            self.contour_vertices_list[geometry_idx]['vertices_per_layer'].append(len(slice_contour))
        print('plane contour time:', time.elapsed())

    def __sort_slice_contour(self, geometry_idx, use_old_sort=False):
        slices_contour = self.contour_vertices_list[geometry_idx]
        if use_old_sort:
            time = QTime()
            time.start()
            ordered_slices = np.empty(slices_contour['vertices'].size)
            slice_start_idx = 0
            for slice_idx, slice_length in enumerate(slices_contour['vertices_per_layer']):
                slice_contour = slices_contour['vertices'][slice_start_idx : slice_start_idx + slice_length].reshape(-1, 3)
                segments = [[slice_contour[idx * 2], slice_contour[idx * 2 + 1]] for idx in range(int(len(slice_contour) / 2))]
                ordered_slices[slice_start_idx: slice_start_idx + slice_length] = slicer_helpers.sort_segments_list(segments)
                slice_start_idx += slice_length
            print("Old Sort:", time.elapsed())
        else:
            time = QTime()
            time.start()
            ordered_slices = np.empty(slices_contour['vertices'].size)
            slice_start_idx = 0
            for slice_idx, slice_length in enumerate(slices_contour['vertices_per_layer']):
                slice_contour = slices_contour['vertices'][slice_start_idx : slice_start_idx + slice_length].reshape(-1, 3)

                segments = [[slice_contour[idx * 2], slice_contour[idx * 2 + 1]] for idx in range(int(len(slice_contour) / 2))]
                ordered_slices[slice_start_idx: slice_start_idx + slice_length] = slicer_helpers.merge_sort_segments_list(segments)
                slice_start_idx += slice_length
            print("New Sort:", time.elapsed())
        self.contour_vertices_list[geometry_idx]['vertices'] = ordered_slices
        # current_parameters.contour_vertices = (ordered_slices, slices_contour[1], slices_contour[2])

    def __get_parallel_lines_infill(self, geometry_idx):
        current_geometry = self.geometries_list[geometry_idx]
        current_parameters = self.slicing_parameters_list[geometry_idx]
        transformation_matrix = current_geometry.get_model_matrix()
        inverse_matrix, _ = transformation_matrix.inverted()
        inverse_matrix = np.array(inverse_matrix.data(), dtype=np.float32).reshape(4, 4).transpose()
        transformation_matrix = np.array(transformation_matrix.data(), dtype=np.float32).reshape(4, 4).transpose()
        density = current_parameters.get_infill_density() / 100.0
        overlap = current_parameters.get_infill_overlap()  / 100.0
        if density < 1:
            overlap = 0
        bbox_min = current_geometry.get_transformed_min_bbox()
        bbox_max = current_geometry.get_transformed_max_bbox()
        bbox_center = QVector3D(bbox_max.x() + bbox_min.x(), 0, bbox_max.z() + bbox_min.z()) * 0.5
        bbox_diagonal = QVector3D(bbox_max.x() - bbox_min.x(), 0, bbox_max.z() - bbox_min.z()).length()
        rot_angle = current_parameters.get_infill_rotation_angle()  * self.current_slice % 360
        rotation_matrix = QMatrix4x4()
        rotation_matrix.rotate(rot_angle, 0.0, 1.0, 0.0)
        rotation_matrix = np.array(rotation_matrix.data(), dtype=np.float32).reshape(4, 4).transpose()
        number_of_rays = int(np.ceil(bbox_diagonal / (self.laser_width_microns - self.laser_width_microns * overlap)* 1000 * density))
        if number_of_rays == 0:
            intersection_points = np.array([], dtype=np.float32)
            self.infill_vertices_list[geometry_idx]['vertices'].append(intersection_points)
            self.infill_vertices_list[geometry_idx]['vertices_per_layer'].append(len(intersection_points))
            return
        rays_origin_offset = bbox_diagonal / number_of_rays
        ray_origin_x = (- bbox_diagonal * 0.5) + rays_origin_offset * 0.5
        ray_origin_y = self.slice_thickness_microns * (self.current_slice + self.slice_height_offset) / 1000.0
        ray_origin_z = (- bbox_diagonal * 0.5) - 1.0
        rays_origins = [rotation_matrix.dot(np.array([ray_origin_x + rays_origin_offset * idx, ray_origin_y, ray_origin_z, 1.0], dtype=np.float32))
                        + np.array([bbox_center.x(), 0, bbox_center.z(), 0], dtype=np.float32)for idx in range(number_of_rays)]
        rays_origins = [inverse_matrix.dot(rays_origins[idx])[0:3] for idx in range(number_of_rays)]
        ray_direction = inverse_matrix.dot(rotation_matrix.dot(np.array([0.0, 0.0, 1.0, 0.0], dtype=np.float32)))[0:3]
        rays = [pyStructs.Ray(rays_origins[idx], ray_direction) for idx in range(number_of_rays)]
        rays_info = [pyStructs.RayIntersectionInfo() for _ in range(number_of_rays)]
        _ = [current_geometry.get_bvh().all_intersections(rays[idx], rays_info[idx]) for idx in range(number_of_rays)]
        [rays_info[idx].t_hits.sort() for idx in range(number_of_rays)]
        intersection_points = [[rays[ray_idx].origin + t_hit * ray_direction for t_hit in rays_info[ray_idx].t_hits] for ray_idx in range(number_of_rays)]
        try:
            intersection_points = np.vstack([x for x in intersection_points if x])
            intersection_points = (intersection_points.dot(transformation_matrix[:3, :3].transpose()) + np.array(transformation_matrix[0:3, 3])).ravel()
        except:
            intersection_points = np.array([], dtype=np.float32)
        self.infill_vertices_list[geometry_idx]['vertices'].append(intersection_points)
        self.infill_vertices_list[geometry_idx]['vertices_per_layer'].append(len(intersection_points))

    def __get_zigzag_infill(self, geometry_idx):
        current_geometry = self.geometries_list[geometry_idx]
        current_parameters = self.slicing_parameters_list[geometry_idx]
        transformation_matrix = current_geometry.get_model_matrix()
        inverse_matrix, _ = transformation_matrix.inverted()
        inverse_matrix = np.array(inverse_matrix.data(), dtype=np.float32).reshape(4, 4).transpose()
        transformation_matrix = np.array(transformation_matrix.data(), dtype=np.float32).reshape(4, 4).transpose()
        rotation_matrix = QMatrix4x4()
        rotation_matrix.rotate(current_parameters.get_infill_rotation_angle() * self.current_slice  % 360, 0.0, 1.0, 0.0)
        rotation_matrix = np.array(rotation_matrix.data(), dtype=np.float32).reshape(4, 4).transpose()
        density = current_parameters.get_infill_density() / 100.0
        overlap = current_parameters.get_infill_overlap()  / 100.0
        if density < 1:
            overlap = 0
        bbox_min = current_geometry.get_transformed_min_bbox()
        bbox_max = current_geometry.get_transformed_max_bbox()
        bbox_center = QVector3D(bbox_max.x() + bbox_min.x(), 0, bbox_max.z() + bbox_min.z()) * 0.5
        bbox_diagonal = QVector3D(bbox_max.x() - bbox_min.x(), 0, bbox_max.z() - bbox_min.z()).length()
        number_of_rays = int(np.ceil(bbox_diagonal / (self.laser_width_microns - self.laser_width_microns * overlap)* 1000 * density))
        if number_of_rays == 0:
            intersection_points = np.array([], dtype=np.float32)
            self.infill_vertices_list[geometry_idx]['vertices'].append(intersection_points)
            self.infill_vertices_list[geometry_idx]['vertices_per_layer'].append(len(intersection_points))
            return
        rays_origin_offset = bbox_diagonal / number_of_rays
        ray_origin_x = (- bbox_diagonal * 0.5) + rays_origin_offset * 0.5
        ray_origin_y = self.slice_thickness_microns * (self.current_slice + self.slice_height_offset) / 1000.0
        ray_origin_z = (- bbox_diagonal * 0.5) - 1.0
        rays_origins = [rotation_matrix.dot(np.array([ray_origin_x + rays_origin_offset * idx, ray_origin_y, ray_origin_z, 1.0], dtype=np.float32))
                        + np.array([bbox_center.x(), 0, bbox_center.z(), 0], dtype=np.float32)for idx in range(number_of_rays)]
        rays_origins = [inverse_matrix.dot(rays_origins[idx])[0:3] for idx in range(number_of_rays)]
        ray_direction = inverse_matrix.dot(rotation_matrix.dot(np.array([0.0, 0.0, 1.0, 0.0], dtype=np.float32)))[0:3]
        rays = [pyStructs.Ray(rays_origins[idx], ray_direction) for idx in range(number_of_rays)]
        rays_info = [pyStructs.RayIntersectionInfo() for _ in range(number_of_rays)]
        _ = [current_geometry.get_bvh().all_intersections(rays[idx], rays_info[idx]) for idx in range(number_of_rays)]
        [rays_info[idx].t_hits.sort() for idx in range(number_of_rays)]
        intersection_points = [[rays[ray_idx].origin + t_hit * ray_direction for t_hit in rays_info[ray_idx].t_hits] for
                               ray_idx in range(number_of_rays)]
        try:
            for ray_idx in range(number_of_rays - 1):
                if ray_idx % 2 == 0:
                    intersection_points[ray_idx + 1].reverse()
                if intersection_points[ray_idx] and intersection_points[ray_idx + 1]:
                    intersection_points[ray_idx].append(intersection_points[ray_idx][-1])
                    intersection_points[ray_idx].append(intersection_points[ray_idx + 1][0])
            intersection_points = np.vstack([x for x in intersection_points if x])
            intersection_points = (intersection_points.dot(transformation_matrix[:3, :3].transpose()) + np.array(
                transformation_matrix[0:3, 3])).ravel()
        except:
            intersection_points = np.array([], dtype=np.float32)
        self.infill_vertices_list[geometry_idx]['vertices'].append(intersection_points)
        self.infill_vertices_list[geometry_idx]['vertices_per_layer'].append(len(intersection_points))

    def __load_slices_buffers__(self):
        for geometry_idx in range(self.geometries_loaded):
            contour_vertices = self.contour_vertices_list[geometry_idx]['vertices']
            rounded_vertices = np.array([round(x, self.__number_of_decimals) for x in np.hstack(contour_vertices)])
            self.contour_vertices_list[geometry_idx]['vertices'] = rounded_vertices
            GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.contour_buffer_id_list[geometry_idx])
            GL.glBufferData(GL.GL_ARRAY_BUFFER, rounded_vertices.nbytes, rounded_vertices, GL.GL_STATIC_DRAW)

            infill_vertices = self.infill_vertices_list[geometry_idx]['vertices']
            rounded_vertices = np.array([round(x, self.__number_of_decimals) for x in np.hstack(infill_vertices)])
            self.infill_vertices_list[geometry_idx]['vertices'] = rounded_vertices
            GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.infill_buffer_id_list[geometry_idx])
            GL.glBufferData(GL.GL_ARRAY_BUFFER, rounded_vertices.nbytes, rounded_vertices, GL.GL_STATIC_DRAW)

    def write_slice_job_to_file(self, file_name="./job.g"):
        file = QFile(file_name)
        file_info = QFileInfo(file)
        if file.open(QIODevice.WriteOnly | QIODevice.Text):
            sliced_geometry_idxs = []
            for geometry_idx in range(self.geometries_loaded):
                if len(self.contour_vertices_list[geometry_idx]['vertices']) > 0 or len(self.infill_vertices_list[geometry_idx]['vertices']) > 0:
                    sliced_geometry_idxs.append(geometry_idx)

            if len(sliced_geometry_idxs) == 0:
                return
            decimals = "%%.%if" % self.__number_of_decimals
            stream = QTextStream(file)
            contour_vertices_written = []
            infill_vertices_written = []
            layer_thickness = self.contour_vertices_list[sliced_geometry_idxs[0]]['layer_thickness']
            for geometry_idx in sliced_geometry_idxs:
                self.__sort_slice_contour(geometry_idx, use_old_sort=False)
                contour_vertices_written.append(0)
                infill_vertices_written.append(0)
            stream << ";Galvo Scanner System\n"
            stream << ";Gcode altered for SLM\n"
            stream << ";Filename: %s\n" % file_info.fileName()
            stream << ";Laser Spot Size " + decimals % (self.laser_width_microns / 1000) + " mm\n"
            stream << ";Layer Thickness " + decimals % layer_thickness + " mm\n"
            stream << ";Sliced %s\n" % QDate.currentDate().toString("dd.MM.yyyy")
            for geometry_idx in sliced_geometry_idxs:
                current_geometry = self.geometries_list[geometry_idx]
                current_parameters = self.slicing_parameters_list[geometry_idx]
                stream << "\n"
                stream << ";Geometry %i: %s\n" % (geometry_idx, current_geometry.get_geometry_name())
                stream << ";Contour Strategy: %s\n" % self.contour_strategies[current_parameters.get_contour_strategy_idx()]
                stream << ";Contour: Feedrate (mm/s) " + decimals % (current_parameters.get_contour_scan_speed()) + ", Frequency (Hz) %i, Power (W) %i, Duty Cycle (%%) %i\n" % (current_parameters.get_contour_frequency(), current_parameters.get_contour_laser_power(), current_parameters.get_contour_duty_cycle())
                stream << ";Infill Strategy: %s\n" % self.infill_strategies[current_parameters.get_infill_strategy_idx()]
                stream << ";Infill Density: %i\n" % current_parameters.get_infill_density()
                stream << ";Infill Overlap: %i\n" % current_parameters.get_infill_overlap()
                stream << ";Infill Rotation Angle: %i\n" % current_parameters.get_infill_rotation_angle()
                stream << ";Infill: Feedrate (mm/s) " + decimals % (current_parameters.get_infill_scan_speed()) + ", Frequency (Hz) %i, Power (W) %i, Duty Cycle (%%) %i\n" % (current_parameters.get_infill_frequency(), current_parameters.get_infill_laser_power(), current_parameters.get_infill_duty_cycle())
            stream << "\n"
            stream << "G92; Setting Absolute Coordinates\n"
            stream << "\n"
            stream << ";Homing Routine\n"
            stream << "M10\n"
            stream << "C0\n"
            stream << "\n"
            stream << ";Movement Start\n"
            for slice_idx in range(self.number_of_slices):
                stream << ";Slice %i \n" % slice_idx
                stream << ";Recoating routine \n"
                stream << "M10\n"
                stream << "M4 V2 T11000 D683 F490\n"
                stream << "M7 R3\n"
                stream << "C1 R" + decimals % layer_thickness + "\n"
                stream << "C3\n"
                for geometry_idx in sliced_geometry_idxs:
                    current_parameters = self.slicing_parameters_list[geometry_idx]
                    if len(self.infill_vertices_list[geometry_idx]['vertices_per_layer']) > slice_idx:
                        stream << ";Start Infill (Geometry %i)\n" % geometry_idx
                        stream << ";Infill Strategy: %s\n" % self.infill_strategies[
                            current_parameters.get_infill_strategy_idx()]
                        stream << ";Infill Density: %i\n" % current_parameters.get_infill_density()
                        stream << ";Infill Overlap: %i\n" % current_parameters.get_infill_overlap()
                        stream << ";Infill Rotation Angle: %i\n" % (current_parameters.get_infill_rotation_angle() * slice_idx % 360)
                        stream << ";Set Feedrate, Frequency, and Power\n"
                        stream << "G1 F" + decimals % (current_parameters.get_infill_scan_speed()) + " H%i P%i\n" % (current_parameters.get_infill_frequency(), current_parameters.get_infill_laser_power())
                        number_of_infill_vertices_to_write = self.infill_vertices_list[geometry_idx]['vertices_per_layer'][slice_idx]
                        infill_vertices = self.infill_vertices_list[geometry_idx]['vertices'][infill_vertices_written[geometry_idx]:infill_vertices_written[geometry_idx] + number_of_infill_vertices_to_write]
                        infill_segments = int(len(infill_vertices) / 6)
                        last_end_point = None
                        for segment_idx in range(infill_segments):
                            start_point = infill_vertices[segment_idx * 6: segment_idx * 6 + 3]
                            end_point = infill_vertices[segment_idx * 6 + 3: segment_idx * 6 + 6]
                            if (last_end_point == start_point).all():
                                stream << "G1 X" + decimals % end_point[0] + " Y" + decimals % end_point[2] + " D%i\n" % current_parameters.get_infill_duty_cycle()
                            else:
                                stream << "G1 X" + decimals % start_point[0] + " Y" + decimals % start_point[2] + "\n"
                                stream << "G1 X" + decimals % end_point[0] + " Y" + decimals % end_point[2] + " D%i\n" % current_parameters.get_infill_duty_cycle()
                            last_end_point = end_point
                        infill_vertices_written[geometry_idx] += len(infill_vertices)
                    if len(self.contour_vertices_list[geometry_idx]['vertices_per_layer']) > slice_idx:
                        stream << ";Start Contour (Geometry %i)\n" % geometry_idx
                        stream << ";Contour Strategy: %s\n" % self.contour_strategies[current_parameters.get_contour_strategy_idx()]
                        stream << ";Set Feedrate, Frequency, and Power\n"
                        stream << "G1 F" + decimals % (current_parameters.get_contour_scan_speed()) + " H%i P%i\n" % (current_parameters.get_contour_frequency(), current_parameters.get_contour_laser_power())
                        number_of_contour_vertices_to_write = self.contour_vertices_list[geometry_idx]['vertices_per_layer'][slice_idx]
                        contour_vertices = self.contour_vertices_list[geometry_idx]['vertices'][contour_vertices_written[geometry_idx]:contour_vertices_written[geometry_idx] + number_of_contour_vertices_to_write]
                        contour_segments = int(len(contour_vertices) / 6)
                        last_end_point = None
                        for segment_idx in range(contour_segments):
                            start_point = contour_vertices[segment_idx * 6: segment_idx * 6 + 3]
                            end_point = contour_vertices[segment_idx * 6 + 3: segment_idx * 6 + 6]
                            if (last_end_point == start_point).all():
                                stream << "G1 X" + decimals % end_point[0] + " Y" + decimals % end_point[2] + " D%i\n" % current_parameters.get_contour_duty_cycle()
                            else:
                                stream << "G1 X" + decimals % start_point[0] + " Y" + decimals % start_point[2] + "\n"
                                stream << "G1 X" + decimals % end_point[0] + " Y" + decimals % end_point[2] + " D%i\n" % current_parameters.get_contour_duty_cycle()
                            last_end_point = end_point
                        contour_vertices_written[geometry_idx] += len(contour_vertices)
            file.close()
        print(file_name)

    def load_geometry(self, filename, swapyz=True):
        time = QTime()
        time.start()
        is_loaded, vertices_list, normals_list, bbox_min, bbox_max = geometry_loader.load_geometry(filename, swapyz)
        print("Loading time:", time.elapsed())
        if is_loaded:
            geometry_idx = self.geometries_loaded
            self.geometries_loaded += 1
            new_geometry = pyGeometry.PyGeometry(filename=filename, vertices=vertices_list, normals=normals_list,
                                                 bbox_min=bbox_min, bbox_max=bbox_max, use_bvh=True)
            self.geometries_list.append(new_geometry)
            self.__append_slicing_default_parameters__()
            self.write_buffers(geometry_idx)
            self.current_geometry_idx = geometry_idx
            return True
        return False

    def write_buffers(self, geometry_idx=0):
        current_geometry = self.geometries_list[geometry_idx]
        self.vertex_buffer_id_list.append(GL.glGenBuffers(1))
        self.normal_buffer_id_list.append(GL.glGenBuffers(1))
        self.contour_buffer_id_list.append(GL.glGenBuffers(1))
        self.infill_buffer_id_list.append(GL.glGenBuffers(1))
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.vertex_buffer_id_list[geometry_idx])
        GL.glBufferData(GL.GL_ARRAY_BUFFER, current_geometry.get_vertices_list().nbytes, current_geometry.get_vertices_list(),
                        GL.GL_STATIC_DRAW)
        GL.glEnableVertexAttribArray(self.position_location)
        GL.glVertexAttribPointer(self.position_location, 3, GL.GL_FLOAT, GL.GL_FALSE, 0, None)

        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.normal_buffer_id_list[geometry_idx])
        GL.glBufferData(GL.GL_ARRAY_BUFFER, current_geometry.get_normals_list().nbytes, current_geometry.get_normals_list(),
                        GL.GL_STATIC_DRAW)
        GL.glEnableVertexAttribArray(self.normal_location)
        GL.glVertexAttribPointer(self.normal_location, 3, GL.GL_FLOAT, GL.GL_FALSE, 0, None)

    def load_quad(self):
        self.quad_vertex_buffer = GL.glGenBuffers(1)
        self.quad_normal_buffer = GL.glGenBuffers(1)
        self.quad_texcoords_buffer = GL.glGenBuffers(1)
        v0 = QVector3D(1.0, 0.0, 1.0)
        v1 = QVector3D(1.0, 0.0, -1.0)
        v2 = QVector3D(-1.0, 0.0, -1.0)
        v3 = QVector3D(-1.0, 0.0, 1.0)
        n0 = QVector3D(0.0, 1.0, 0.0)
        n1 = QVector3D(0.0, 1.0, 0.0)
        n2 = QVector3D(0.0, 1.0, 0.0)
        n3 = QVector3D(0.0, 1.0, 0.0)
        t0 = QVector2D(1, 0)
        t1 = QVector2D(1, 1)
        t2 = QVector2D(0, 1)
        t3 = QVector2D(0, 0)
        self.quad_vertices = np.asarray(np.concatenate((v0.toTuple(), v1.toTuple(), v2.toTuple(), v3.toTuple())),
                                        np.float32)
        self.quad_normals = np.asarray(np.concatenate((n0.toTuple(), n1.toTuple(), n2.toTuple(), n3.toTuple())),
                                        np.float32)
        self.quad_texcoords = np.array(np.concatenate((t0.toTuple(), t1.toTuple(), t2.toTuple(), t3.toTuple())), np.float32)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.quad_vertex_buffer)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, self.quad_vertices.nbytes, self.quad_vertices, GL.GL_STATIC_DRAW)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.quad_normal_buffer)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, self.quad_normals.nbytes, self.quad_normals, GL.GL_STATIC_DRAW)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.quad_texcoords_buffer)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, self.quad_texcoords.nbytes, self.quad_texcoords, GL.GL_STATIC_DRAW)

    def init_shaders(self):
        # Shaders to visualize loaded geometry
        self.program_id = GL.glCreateProgram()
        vs_id = GL.glCreateShader(GL.GL_VERTEX_SHADER)
        GL.glShaderSource(vs_id, ms.vertex_shader)
        GL.glCompileShader(vs_id)
        frag_id = GL.glCreateShader(GL.GL_FRAGMENT_SHADER)
        GL.glShaderSource(frag_id, ms.fragment_shader)
        GL.glCompileShader(frag_id)
        GL.glAttachShader(self.program_id, vs_id)
        GL.glAttachShader(self.program_id, frag_id)
        GL.glLinkProgram(self.program_id)
        self.position_location = GL.glGetAttribLocation(self.program_id, 'vin_position')
        self.normal_location = GL.glGetAttribLocation(self.program_id, 'vin_normal')
        self.camera_matrix_location = GL.glGetUniformLocation(self.program_id, 'camera_matrix')
        self.model_matrix_location = GL.glGetUniformLocation(self.program_id, 'model_matrix')
        self.projection_matrix_location = GL.glGetUniformLocation(self.program_id, 'projection_matrix')
        self.normal_matrix_location = GL.glGetUniformLocation(self.program_id, 'normal_matrix')
        self.light_location = GL.glGetUniformLocation(self.program_id, 'light_direction')
        self.light_intensity_location = GL.glGetUniformLocation(self.program_id, 'light_intensity')
        self.ambient_location = GL.glGetUniformLocation(self.program_id, 'ambient_color')
        self.diffuse_location = GL.glGetUniformLocation(self.program_id, 'diffuse_color')
        # Shaders to perform image slicing
        self.slicer_program_id = GL.glCreateProgram()
        vs_id = GL.glCreateShader(GL.GL_VERTEX_SHADER)
        GL.glShaderSource(vs_id, ms.slicer_vertex_shader)
        GL.glCompileShader(vs_id)
        frag_id = GL.glCreateShader(GL.GL_FRAGMENT_SHADER)
        GL.glShaderSource(frag_id, ms.slicer_fragment_shader)
        GL.glCompileShader(frag_id)
        GL.glAttachShader(self.slicer_program_id, vs_id)
        GL.glAttachShader(self.slicer_program_id, frag_id)
        GL.glLinkProgram(self.slicer_program_id)
        self.slicer_position_location = GL.glGetAttribLocation(self.slicer_program_id, 'vin_position')
        self.slicer_color_location = GL.glGetUniformLocation(self.slicer_program_id, 'vin_color')
        self.slicer_camera_matrix_location = GL.glGetUniformLocation(self.slicer_program_id, 'camera_matrix')
        self.slicer_model_matrix_location = GL.glGetUniformLocation(self.slicer_program_id, 'model_matrix')
        self.slicer_projection_matrix_location = GL.glGetUniformLocation(self.slicer_program_id, 'projection_matrix')
        self.slicer_alpha_location = GL.glGetUniformLocation(self.slicer_program_id, 'alpha')
        # Shaders to visualize Contours and Infills as Lines
        self.show_slices_program_id = GL.glCreateProgram()
        vs_id = GL.glCreateShader(GL.GL_VERTEX_SHADER)
        GL.glShaderSource(vs_id, ms.show_slices_vertex_shader)
        GL.glCompileShader(vs_id)
        gs_id = GL.glCreateShader(GL.GL_GEOMETRY_SHADER)
        GL.glShaderSource(gs_id, ms.show_slices_geometry_shader)
        GL.glCompileShader(gs_id)
        frag_id = GL.glCreateShader(GL.GL_FRAGMENT_SHADER)
        GL.glShaderSource(frag_id, ms.show_slices_fragment_shader)
        GL.glCompileShader(frag_id)
        GL.glAttachShader(self.show_slices_program_id, vs_id)
        GL.glAttachShader(self.show_slices_program_id, gs_id)
        GL.glAttachShader(self.show_slices_program_id, frag_id)
        GL.glLinkProgram(self.show_slices_program_id)
        self.show_slices_position_location = GL.glGetAttribLocation(self.show_slices_program_id, 'vin_position')
        self.show_slices_color_location = GL.glGetUniformLocation(self.show_slices_program_id, 'vin_color')
        self.show_slices_camera_matrix_location = GL.glGetUniformLocation(self.show_slices_program_id, 'camera_matrix')
        self.show_slices_model_matrix_location = GL.glGetUniformLocation(self.show_slices_program_id, 'model_matrix')
        self.show_slices_projection_matrix_location = GL.glGetUniformLocation(self.show_slices_program_id, 'projection_matrix')
        self.show_slices_planar_thickness_location = GL.glGetUniformLocation(self.show_slices_program_id, 'planar_thickness')
        self.show_slices_vertical_thickness_location = GL.glGetUniformLocation(self.show_slices_program_id, 'vertical_thickness')
        self.show_slices_slice_height_offset_location = GL.glGetUniformLocation(self.show_slices_program_id, 'slice_height_offset')
        # Shaders to initialize distance field computation
        self.initialize_distance_field_program_id = GL.glCreateProgram()
        vs_id = GL.glCreateShader(GL.GL_VERTEX_SHADER)
        GL.glShaderSource(vs_id, ms.initialize_distance_field_vertex_shader)
        GL.glCompileShader(vs_id)
        frag_id = GL.glCreateShader(GL.GL_FRAGMENT_SHADER)
        GL.glShaderSource(frag_id, ms.initialize_distance_field_fragment_shader)
        GL.glCompileShader(frag_id)
        GL.glAttachShader(self.initialize_distance_field_program_id, vs_id)
        GL.glAttachShader(self.initialize_distance_field_program_id, frag_id)
        GL.glLinkProgram(self.initialize_distance_field_program_id)
        self.initialize_distance_field_position_location = GL.glGetAttribLocation(self.initialize_distance_field_program_id, 'vin_position')
        self.initialize_distance_field_texcoord_location = GL.glGetAttribLocation(self.initialize_distance_field_program_id, 'vin_texcoords')
        self.initialize_distance_field_model_matrix_location = GL.glGetUniformLocation(self.initialize_distance_field_program_id, 'model_matrix')
        self.initialize_distance_field_texture_location = GL.glGetUniformLocation(self.initialize_distance_field_program_id, 'sliced_image_texture')
        # Shaders to perform distance field pass
        self.distance_field_pass_program_id = GL.glCreateProgram()
        vs_id = GL.glCreateShader(GL.GL_VERTEX_SHADER)
        GL.glShaderSource(vs_id, ms.distance_field_pass_vertex_shader)
        GL.glCompileShader(vs_id)
        frag_id = GL.glCreateShader(GL.GL_FRAGMENT_SHADER)
        GL.glShaderSource(frag_id, ms.distance_field_pass_fragment_shader)
        GL.glCompileShader(frag_id)
        GL.glAttachShader(self.distance_field_pass_program_id, vs_id)
        GL.glAttachShader(self.distance_field_pass_program_id, frag_id)
        GL.glLinkProgram(self.distance_field_pass_program_id)
        self.distance_field_lines_position_location = GL.glGetAttribLocation(self.distance_field_pass_program_id, 'vin_position')
        self.distance_field_image_size_location = GL.glGetUniformLocation(self.distance_field_pass_program_id, 'image_size')
        self.distance_field_read_texture_location = GL.glGetUniformLocation(self.distance_field_pass_program_id, 'read_texture')
        self.distance_field_texture_mask_location = GL.glGetUniformLocation(self.distance_field_pass_program_id, 'texture_mask')
        # Shader to copy and merge distance field textures
        self.copy_texture_program_id = GL.glCreateProgram()
        vs_id = GL.glCreateShader(GL.GL_VERTEX_SHADER)
        GL.glShaderSource(vs_id, ms.copy_texture_vertex_shader)
        GL.glCompileShader(vs_id)
        frag_id = GL.glCreateShader(GL.GL_FRAGMENT_SHADER)
        GL.glShaderSource(frag_id, ms.copy_texture_fragment_shader)
        GL.glCompileShader(frag_id)
        GL.glAttachShader(self.copy_texture_program_id, vs_id)
        GL.glAttachShader(self.copy_texture_program_id, frag_id)
        GL.glLinkProgram(self.copy_texture_program_id)
        self.copy_texture_position_location = GL.glGetAttribLocation(self.copy_texture_program_id, 'vin_position')
        self.copy_texture_read_texture_location = GL.glGetUniformLocation(self.copy_texture_program_id, 'read_texture')
        # Shader to evaluate and normalize computed distance field
        self.normalize_distance_field_program_id = GL.glCreateProgram()
        vs_id = GL.glCreateShader(GL.GL_VERTEX_SHADER)
        GL.glShaderSource(vs_id, ms.normalize_distance_field_vertex_shader)
        GL.glCompileShader(vs_id)
        frag_id = GL.glCreateShader(GL.GL_FRAGMENT_SHADER)
        GL.glShaderSource(frag_id, ms.normalize_distance_field_fragment_shader)
        GL.glCompileShader(frag_id)
        GL.glAttachShader(self.normalize_distance_field_program_id, vs_id)
        GL.glAttachShader(self.normalize_distance_field_program_id, frag_id)
        GL.glLinkProgram(self.normalize_distance_field_program_id)
        self.normalize_distance_field_position_location = GL.glGetAttribLocation(self.normalize_distance_field_program_id, 'vin_position')
        self.normalize_distance_field_texture_location = GL.glGetUniformLocation(self.normalize_distance_field_program_id, 'distance_field_texture')
        self.normalize_distance_field_model_matrix_location = GL.glGetUniformLocation(self.normalize_distance_field_program_id, 'model_matrix')
        self.normalize_distance_field_diagonal_location = GL.glGetUniformLocation(self.normalize_distance_field_program_id, 'diagonal_length')
        # Shader to perform marching squares and extract contours from sliced images
        self.marching_squares_program_id = GL.glCreateProgram()
        GL.glShaderSource(vs_id, ms.marching_squares_vertex_shader)
        GL.glCompileShader(vs_id)
        frag_id = GL.glCreateShader(GL.GL_FRAGMENT_SHADER)
        GL.glShaderSource(frag_id, ms.marching_squares_fragment_shader)
        GL.glCompileShader(frag_id)
        GL.glAttachShader(self.marching_squares_program_id, vs_id)
        GL.glAttachShader(self.marching_squares_program_id, frag_id)
        GL.glLinkProgram(self.marching_squares_program_id)
        self.marching_squares_position_location = GL.glGetAttribLocation(self.marching_squares_program_id, 'vin_position')
        self.marching_squares_texcoord_location = GL.glGetAttribLocation(self.marching_squares_program_id, 'vin_texcoords')
        self.marching_squares_model_matrix_location = GL.glGetUniformLocation(self.marching_squares_program_id, 'model_matrix')
        self.marching_squares_texture_location = GL.glGetUniformLocation(self.marching_squares_program_id, 'image_texture')
        self.marching_squares_slice_height_location = GL.glGetUniformLocation(self.marching_squares_program_id, 'slice_height')
        self.marching_squares_bbox_size_location = GL.glGetUniformLocation(self.marching_squares_program_id, 'bbox_size')
        self.marching_squares_bbox_origin_location = GL.glGetUniformLocation(self.marching_squares_program_id, 'bbox_origin')
        self.marching_squares_image_size_location = GL.glGetUniformLocation(self.marching_squares_program_id, 'image_size')
        self.marching_squares_viewport_origin_location = GL.glGetUniformLocation(self.marching_squares_program_id, 'viewport_origin')

    def remove_geometry(self):
        if self.geometries_loaded > 0:
            self.geometries_loaded -= 1
            del self.slicing_parameters_list[self.current_geometry_idx]
            GL.glDeleteBuffers(1, [self.contour_buffer_id_list[self.current_geometry_idx]])
            GL.glDeleteBuffers(1, [self.infill_buffer_id_list[self.current_geometry_idx]])
            del self.contour_buffer_id_list[self.current_geometry_idx]
            del self.infill_buffer_id_list[self.current_geometry_idx]
            del self.contour_vertices_list[self.current_geometry_idx]
            del self.infill_vertices_list[self.current_geometry_idx]

            GL.glDeleteBuffers(1, [self.vertex_buffer_id_list[self.current_geometry_idx]])
            GL.glDeleteBuffers(1, [self.normal_buffer_id_list[self.current_geometry_idx]])
            del self.vertex_buffer_id_list[self.current_geometry_idx]
            del self.normal_buffer_id_list[self.current_geometry_idx]
            del self.geometries_list[self.current_geometry_idx]
            self.current_geometry_idx = 0

    def __load_default_parameters__(self):
        self.__default_parameters = {
            'laser_width (microns)': 600,
            'building_area_width (mm)': 100,
            'building_area_height (mm)': 100,
            'slice_thickness (microns)': 10,
            'infill_density': 100,
            'infill_overlap': 0,
            'infill_rotation': 0,
            'infill_duty_cycle (%)': 100,
            'infill_scan_speed (mm/min)': 10,
            'infill_laser_power': 100,
            'infill_frequency (Hz)': 100000,
            'contour_duty_cycle (%)': 100,
            'contour_scan_speed (mm/min)': 10,
            'contour_laser_power': 100,
            'contour_frequency (Hz)': 100000
        }
        base_path = Path(__file__).parent
        settings_path = str((base_path / '../resources/PRINTER_SETTINGS.json').resolve())
        settings_file = QFile(settings_path)
        if settings_file.open(QIODevice.ReadOnly | QIODevice.Text):
            file_data = QJsonDocument.fromJson(settings_file.readAll()).object()
            if "metal_printer_settings" in file_data:
                for key, value in self.__default_parameters.items():
                    if key in file_data["metal_printer_settings"]:
                        new_value = file_data["metal_printer_settings"][key]
                        self.__default_parameters[key] = new_value
            settings_file.close()

    @Slot()
    def save_default_parameters(self):
        base_path = Path(__file__).parent
        settings_path = str((base_path / '../resources/PRINTER_SETTINGS.json').resolve())
        settings_file = QFile(settings_path)
        file_data = {}
        if settings_file.open(QIODevice.ReadOnly | QIODevice.Text):
            file_data = QJsonDocument.fromJson(settings_file.readAll()).object()
            settings_file.close()
        if settings_file.open(QIODevice.ReadWrite | QIODevice.Text | QIODevice.Truncate):
            file_data["printer_type"] = "Metal"
            file_data["metal_printer_settings"] = self.__default_parameters
            settings_file.write(QJsonDocument(file_data).toJson())
            settings_file.close()

    @Slot()
    def save_current_scene(self, scene_path):
        file = QFile(scene_path)
        if file.open(QIODevice.ReadWrite | QIODevice.Text):
            json_array = QJsonArray()
            for geometry_idx in range(self.geometries_loaded):
                current_geometry = self.geometries_list[geometry_idx]
                current_slicing_parameters = self.slicing_parameters_list[geometry_idx]
                geometry_data = current_geometry.get_parameters_dict()
                geometry_data['slicing_parameters'] = current_slicing_parameters.get_parameters_dict()
                json_array.append(geometry_data)
            file.write(QJsonDocument(json_array).toJson())
            file.close()

    @Slot()
    def load_scene(self, scene_path):
        file = QFile(scene_path)
        geometries_names = []
        if file.open(QIODevice.ReadOnly | QIODevice.Text):
            json_document = QJsonDocument.fromJson(file.readAll())
            if json_document.isArray():
                json_array = json_document.array()
                for item_idx in range(json_array.size()):
                    item = json_array.at(item_idx).toObject()
                    if self.load_geometry(item['filename']):
                        current_geometry = self.get_current_geometry()
                        current_slicing_parameters = self.get_current_parameters()
                        geometry_parameters = item['geometry_parameters']
                        slicing_parameters = item['slicing_parameters']
                        current_geometry.set_parameters_from_dict(geometry_parameters)
                        current_slicing_parameters.set_parameters_from_dict(slicing_parameters)
                        geometries_names.append(current_geometry.get_geometry_name())
            file.close()
        return geometries_names

    # Functions to control camera movement
    def mousePressEvent(self, event):
        self.mouse_last_pos = event.pos()

    def mouseMoveEvent(self, event):
        old_pos = self.__normalize_screen_coordinates__(self.mouse_last_pos)
        new_pos = self.__normalize_screen_coordinates__(event.pos())
        if event.buttons() & Qt.LeftButton:
            self.trackball_mapping(old_pos, new_pos, radius=0.8, method='bell')
            self.eye = self.camera_rotation.rotatedVector(self.eye)
            self.up = self.camera_rotation.rotatedVector(self.up)
        if event.buttons() & Qt.MiddleButton:
            zoom_factor = (new_pos.y() - old_pos.y()) * 50
            new_radius = np.fmax(1.0, self.camera_radius + zoom_factor)
            zoom_direction = self.eye - self.look_at
            zoom_direction.normalize()
            self.eye = self.look_at + zoom_direction * new_radius
            self.camera_radius = new_radius
        if event.buttons() & Qt.RightButton:
            x_translation = -(new_pos.x() - old_pos.x()) * 50
            y_translation = (new_pos.y() - old_pos.y()) * 50
            right = QVector3D.crossProduct(self.look_at - self.eye, self.up)
            right.normalize()
            self.eye = self.eye + self.up * y_translation + right * x_translation
            self.look_at = self.look_at + self.up * y_translation + right * x_translation
        self.camera_matrix.setToIdentity()
        self.camera_matrix.lookAt(self.eye, self.look_at, self.up)
        self.camera_matrix_array = np.asarray(self.camera_matrix.copyDataTo(), np.float32)
        self.light_direction = self.look_at - self.eye
        self.mouse_last_pos = event.pos()

    def trackball_mapping(self, point_a, point_c, radius=1, method='bell'):
        if method == 'bell':
            p_a = self.__bell_function__(point_a, radius)
            p_c = self.__bell_function__(point_c, radius)
        elif method == 'shoemake':
            p_a = self.__shoemake_function__(point_a, radius)
            p_c = self.__shoemake_function__(point_c, radius)
        q_a = QQuaternion(0, p_a.normalized())
        q_c = QQuaternion(0, p_c.normalized())
        new_rotation = -q_c * q_a
        self.camera_rotation = new_rotation

    @staticmethod
    def __shoemake_function__(point, radius=1):
        point_3d = QVector3D(-point.x(), point.y(), 0.0)
        sqr_sum = point_3d.x() * point_3d.x() + point_3d.y() * point_3d.y()
        if sqr_sum <= radius * radius:
            result = QVector3D(point_3d.x(), point_3d.y(), np.sqrt(radius * radius - sqr_sum))
        else:
            result = QVector3D(point_3d.x(), point_3d.y(), 0) * radius / (np.sqrt(sqr_sum))
        return result

    @staticmethod
    def __bell_function__(point, radius=1):
        point_3d = QVector3D(-point.x(), point.y(), 0.0)
        sqr_sum = point_3d.x() * point_3d.x() + point_3d.y() * point_3d.y()
        if sqr_sum <= radius * radius / 2:
            result = QVector3D(point_3d.x(), point_3d.y(), np.sqrt(radius * radius - sqr_sum))
        else:
            result = QVector3D(point_3d.x(), point_3d.y(), radius * radius / (2 * np.sqrt(sqr_sum)))
            result = result / np.sqrt(sqr_sum + result.z() * result.z())
        return result

    def __normalize_screen_coordinates__(self, pos):
        new_pos = QVector3D(0, 0, 0)
        new_pos.setX(2.0 * pos.x() / self.w - 1.0)
        if new_pos.x() < -1:
            new_pos.setX(-1)
        elif new_pos.x() > 1:
            new_pos.setX(1)
        new_pos.setY(2.0 * pos.y() / self.h - 1.0)
        if new_pos.y() < -1:
            new_pos.setY(-1)
        elif new_pos.y() > 1:
            new_pos.setY(1)
        return new_pos