import sys
from PySide2.QtWidgets import QVBoxLayout, QSpinBox, QWidget, QGroupBox, QSlider, QLabel, \
    QGridLayout, QDoubleSpinBox, QCheckBox, QPushButton, QFileDialog, QHBoxLayout, QMessageBox, QComboBox, QSizePolicy
from PySide2.QtCore import Signal, Slot, Qt, QFileInfo
from PySide2.QtGui import QGuiApplication
from MetalPrinter.metalSlicer import MetalSlicer
from PyTracer import pyGeometry


class MetalSlicerGUI(QWidget):

    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        self.main_layout = QHBoxLayout(self)
        # self.main_layout = QVBoxLayout()
        self.widget_width = 500
        self.widget_height = 400

        self.__init_slicer_widget__()
        self.__init_info_widget__()
        self.__init_geometry_options_widget__()
        self.__init_generic_slicer_options_widget__()
        self.__init_slices_display_options_widget()
        self.__init_geometry_specific_slicer_options_widget()
        self.__init_buttons_options_widget()

        self.__info_widget.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        self.__buttons_options_widget.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        self.__geometry_options_widget.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Maximum)
        self.__slicer_options_widget.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Maximum)
        self.__slices_display_options_widget.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Maximum)
        self.__geometry_specific_slicer_options_widget.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Maximum)

        left_widget = QWidget(self)
        # left_layout = QVBoxLayout(left_widget)
        left_layout = QGridLayout(left_widget)
        right_widget = QWidget(self)
        right_layout = QGridLayout(right_widget)
        left_layout.addWidget(self.__slicer_widget, 0, 0, 1, 3)
        left_layout.addWidget(self.__info_widget, 1, 0, 1, 3)
        left_layout.addWidget(self.__buttons_options_widget, 2, 0, 1, 3)
        left_layout.addWidget(self.__geometry_specific_slicer_options_widget, 3, 2, 2, 1)
        left_layout.addWidget(self.__geometry_options_widget, 3, 0, 2, 1)
        left_layout.addWidget(self.__slicer_options_widget, 3, 1, 1, 1)
        left_layout.addWidget(self.__slices_display_options_widget, 4, 1, 1, 1)
        # right_layout.addWidget(self.__geometry_options_widget, 1, 0, 2, 1)
        # right_layout.addWidget(self.__slicer_options_widget, 1, 2, 1, 1)
        # right_layout.addWidget(self.__slices_display_options_widget, 2, 2, 1, 1)
        # right_layout.addWidget(self.__geometry_specific_slicer_options_widget, 1, 1, 2, 1)
        # right_layout.addWidget(self.__buttons_options_widget, 3, 0, 1, 4)
        self.main_layout.addWidget(left_widget)
        self.main_layout.addWidget(right_widget)

    def __init_slicer_widget__(self):
        self.__slicer_widget = MetalSlicer(parent=self)
        self.__slicer_widget.save_default_parameters()
        self.__slicer_widget.setMinimumHeight(self.widget_height)
        # self.__slicer_widget.update_physical_size.connect(self.update_size_label)
        self.__slicer_widget.update_fps.connect(self.update_fps_label)
        self.__slicer_widget.update_slice_counts.connect(self.update_slices_label)

    def __init_options_widget__(self):
        self.__options_widget = QWidget(self)
        self.__init_info_widget__()
        self.__init_geometry_options_widget__()
        self.__init_generic_slicer_options_widget__()
        self.__options_layout = QGridLayout()
        self.__options_layout.addWidget(self.__info_widget, 0, 0, 1, 3)
        self.__options_layout.addWidget(self.__geometry_options_widget, 1, 0, 1, 2)
        self.__options_layout.addWidget(self.__slicer_options_widget, 1, 2)
        self.__options_widget.setLayout(self.__options_layout)
        self.__options_widget.setFixedWidth(self.widget_width, 400)

    def __init_info_widget__(self):
        self.__info_widget = QWidget(self)
        current_geometry_label = QLabel("Selected Geometry:", self.__info_widget)
        self.geometry_list = MyQComboBox(self.__info_widget)
        self.geometry_list.currentIndexChanged.connect(self.update_geometry_transformations)
        self.geometry_list.currentIndexChanged.connect(self.update_slicer_options)
        self.fps_label = QLabel(f'fps: {0:.2f}', self.__info_widget)
        self.physical_size_label = QLabel(f'Width: {0:.2f} \u03BCm, Depth: {0:.2f} \u03BCm, Height: {0:.2f} \u03BCm',
                                          self.__info_widget)
        info_layout = QHBoxLayout()
        info_layout.addWidget(current_geometry_label)
        info_layout.addWidget(self.geometry_list)
        info_layout.addWidget(self.physical_size_label)
        info_layout.addWidget(self.fps_label)
        self.__info_widget.setLayout(info_layout)

    def __init_geometry_options_widget__(self):
        self.__geometry_options_widget = QGroupBox("Geometry", self)
        rotate_x_label = QLabel("Rotate X:", self.__geometry_options_widget)
        self.rotate_x_slider = MyQSlider(axis='X', orientation=Qt.Horizontal, parent=self.__geometry_options_widget)
        self.rotate_x_slider.setTickPosition(QSlider.TicksBothSides)
        self.rotate_x_slider.setTickInterval(45)
        self.rotate_x_slider.setRange(-180, 180)
        self.rotate_x_slider.setValue(0)
        self.rotate_x_spin = MyQSpinBox(axis='X', parent=self.__geometry_options_widget)
        self.rotate_x_spin.setMinimum(-180)
        self.rotate_x_spin.setMaximum(180)
        self.rotate_x_spin.setValue(0)
        self.rotate_x_slider.valueChanged.connect(self.rotate_x_spin.setValue)
        self.rotate_x_slider.myValueChanged.connect(self.rotate_current_geometry)
        self.rotate_x_spin.valueChanged.connect(self.rotate_x_slider.setValue)
        self.rotate_x_spin.myValueChanged.connect(self.rotate_current_geometry)
        rotate_y_label = QLabel("Rotate Y:", self.__geometry_options_widget)
        self.rotate_y_slider = MyQSlider(axis='Y', orientation=Qt.Horizontal, parent=self.__geometry_options_widget)
        self.rotate_y_slider.setTickPosition(QSlider.TicksBothSides)
        self.rotate_y_slider.setTickInterval(45)
        self.rotate_y_slider.setRange(-180, 180)
        self.rotate_y_slider.setValue(0)
        self.rotate_y_spin = MyQSpinBox(axis='Y', parent=self.__geometry_options_widget)
        self.rotate_y_spin.setMinimum(-180)
        self.rotate_y_spin.setMaximum(180)
        self.rotate_y_spin.setValue(0)
        self.rotate_y_slider.valueChanged.connect(self.rotate_y_spin.setValue)
        self.rotate_y_slider.myValueChanged.connect(self.rotate_current_geometry)
        self.rotate_y_spin.valueChanged.connect(self.rotate_y_slider.setValue)
        self.rotate_y_spin.myValueChanged.connect(self.rotate_current_geometry)
        rotate_z_label = QLabel("Rotate Z:", self.__geometry_options_widget)
        self.rotate_z_slider = MyQSlider(axis='Z', orientation=Qt.Horizontal, parent=self.__geometry_options_widget)
        self.rotate_z_slider.setTickPosition(QSlider.TicksBothSides)
        self.rotate_z_slider.setTickInterval(45)
        self.rotate_z_slider.setRange(-180, 180)
        self.rotate_z_slider.setValue(0)
        self.rotate_z_spin = MyQSpinBox(axis='Z', parent=self.__geometry_options_widget)
        self.rotate_z_spin.setMinimum(-180)
        self.rotate_z_spin.setMaximum(180)
        self.rotate_z_spin.setValue(0)
        self.rotate_z_slider.valueChanged.connect(self.rotate_z_spin.setValue)
        self.rotate_z_slider.myValueChanged.connect(self.rotate_current_geometry)
        self.rotate_z_spin.valueChanged.connect(self.rotate_z_slider.setValue)
        self.rotate_z_spin.myValueChanged.connect(self.rotate_current_geometry)
        translate_x_label = QLabel("Translate X:", self.__geometry_options_widget)
        self.translate_x_slider = MyQSlider(axis='X', orientation=Qt.Horizontal, parent=self.__geometry_options_widget)
        self.translate_x_slider.setTickPosition(QSlider.TicksBothSides)
        self.translate_x_slider.setTickInterval(self.__slicer_widget.laser_width_microns)
        self.translate_x_slider.setRange(-self.__slicer_widget.building_area_width_mm * 0.5, self.__slicer_widget.building_area_width_mm * 0.5)
        self.translate_x_slider.setValue(0)
        self.translate_x_spin = MyQDoubleSpinBox(axis='X', parent=self.__geometry_options_widget)
        self.translate_x_spin.setMinimum(-self.__slicer_widget.building_area_width_mm * 0.5)
        self.translate_x_spin.setMaximum(self.__slicer_widget.building_area_width_mm * 0.5)
        self.translate_x_spin.setSingleStep(self.__slicer_widget.laser_width_microns)
        self.translate_x_spin.setValue(0)
        self.translate_x_slider.valueChanged.connect(self.translate_x_spin.setValue)
        self.translate_x_slider.myValueChanged.connect(self.translate_current_geometry)
        self.translate_x_spin.valueChanged.connect(self.translate_x_slider.setValue)
        self.translate_x_spin.myValueChanged.connect(self.translate_current_geometry)
        translate_z_label = QLabel("Translate Z:", self.__geometry_options_widget)
        self.translate_z_slider = MyQSlider(axis='Z', orientation=Qt.Horizontal, parent=self.__geometry_options_widget)
        self.translate_z_slider.setTickPosition(QSlider.TicksBothSides)
        self.translate_z_slider.setTickInterval(self.__slicer_widget.laser_width_microns)
        self.translate_z_slider.setRange(-self.__slicer_widget.building_area_height_mm * 0.5, self.__slicer_widget.building_area_height_mm * 0.5)
        self.translate_z_slider.setValue(0)
        self.translate_z_spin = MyQDoubleSpinBox(axis='Z', parent=self.__geometry_options_widget)
        self.translate_z_spin.setMinimum(-self.__slicer_widget.building_area_height_mm * 0.5)
        self.translate_z_spin.setMaximum(self.__slicer_widget.building_area_height_mm * 0.5)
        self.translate_z_spin.setSingleStep(self.__slicer_widget.laser_width_microns)
        self.translate_z_spin.setValue(0)
        self.translate_z_slider.valueChanged.connect(self.translate_z_spin.setValue)
        self.translate_z_slider.myValueChanged.connect(self.translate_current_geometry)
        self.translate_z_spin.valueChanged.connect(self.translate_z_slider.setValue)
        self.translate_z_spin.myValueChanged.connect(self.translate_current_geometry)
        scale_x_label = QLabel("Scale X:", self.__geometry_options_widget)
        self.scale_x_spin = MyQDoubleSpinBox(axis='X', parent=self.__geometry_options_widget)
        self.scale_x_spin.setMinimum(-1000)
        self.scale_x_spin.setMaximum(1000)
        self.scale_x_spin.setDecimals(3)
        self.scale_x_spin.setValue(1)
        self.scale_x_spin.setSingleStep(0.001)
        self.scale_x_spin.setObjectName("scale_x_spin")
        self.scale_x_spin.myValueChanged.connect(self.scale_current_geometry)
        scale_y_label = QLabel("Scale Y:", self.__geometry_options_widget)
        self.scale_y_spin = MyQDoubleSpinBox(axis='Y', parent=self.__geometry_options_widget)
        self.scale_y_spin.setMinimum(-1000)
        self.scale_y_spin.setMaximum(1000)
        self.scale_y_spin.setDecimals(3)
        self.scale_y_spin.setValue(1)
        self.scale_y_spin.setSingleStep(0.001)
        self.scale_y_spin.setObjectName("scale_y_spin")
        self.scale_y_spin.myValueChanged.connect(self.scale_current_geometry)
        scale_z_label = QLabel("Scale Z:", self.__geometry_options_widget)
        self.scale_z_spin = MyQDoubleSpinBox(axis='Z', parent=self.__geometry_options_widget)
        self.scale_z_spin.setMinimum(-1000)
        self.scale_z_spin.setMaximum(1000)
        self.scale_z_spin.setDecimals(3)
        self.scale_z_spin.setValue(1)
        self.scale_z_spin.setSingleStep(0.001)
        self.scale_z_spin.setObjectName("scale_z_spin")
        self.scale_z_spin.myValueChanged.connect(self.scale_current_geometry)
        self.uniform_scaling = QCheckBox("Uniform Scaling", self.__geometry_options_widget)
        self.uniform_scaling.setChecked(True)
        list_of_measures = ('\u03BCm', 'mm', 'cm', 'dm', 'm')
        self.list_of_measures_coefficients = [0.001, 1, 10, 100, 1000]
        unit_of_measure_label = QLabel("Unit of Measure", self.__geometry_options_widget)
        self.unit_of_measure_combo = QComboBox(self.__geometry_options_widget)
        for measure in list_of_measures:
            self.unit_of_measure_combo.addItem(measure)
        self.unit_of_measure_combo.setCurrentIndex(1)
        self.unit_of_measure_combo.currentIndexChanged.connect(self.update_unit_of_measure)

        rotate_x_row = 0
        rotate_y_row = rotate_x_row + 1
        rotate_z_row = rotate_y_row + 1
        translate_x_row = rotate_z_row + 1
        translate_z_row = translate_x_row + 1
        scale_x_row = translate_z_row + 1
        scale_y_row = scale_x_row + 1
        scale_z_row = scale_y_row + 1
        uniform_scaling_row = scale_x_row
        unit_of_measure_row = scale_y_row
        geometry_layout = QGridLayout()

        geometry_layout.addWidget(rotate_x_label, rotate_x_row, 0)
        geometry_layout.addWidget(self.rotate_x_slider, rotate_x_row, 1, 1, 4)
        geometry_layout.addWidget(self.rotate_x_spin, rotate_x_row, 5)
        geometry_layout.addWidget(rotate_y_label, rotate_y_row, 0)
        geometry_layout.addWidget(self.rotate_y_slider, rotate_y_row, 1, 1, 4)
        geometry_layout.addWidget(self.rotate_y_spin, rotate_y_row, 5)
        geometry_layout.addWidget(rotate_z_label, rotate_z_row, 0)
        geometry_layout.addWidget(self.rotate_z_slider, rotate_z_row, 1, 1, 4)
        geometry_layout.addWidget(self.rotate_z_spin, rotate_z_row, 5)
        geometry_layout.addWidget(translate_x_label, translate_x_row, 0)
        geometry_layout.addWidget(self.translate_x_slider, translate_x_row, 1, 1, 4)
        geometry_layout.addWidget(self.translate_x_spin, translate_x_row, 5)
        geometry_layout.addWidget(translate_z_label, translate_z_row, 0)
        geometry_layout.addWidget(self.translate_z_slider, translate_z_row, 1, 1, 4)
        geometry_layout.addWidget(self.translate_z_spin, translate_z_row, 5)
        geometry_layout.addWidget(scale_x_label, scale_x_row, 0)
        geometry_layout.addWidget(self.scale_x_spin, scale_x_row, 1)
        geometry_layout.addWidget(scale_y_label, scale_y_row, 0)
        geometry_layout.addWidget(self.scale_y_spin, scale_y_row, 1)
        geometry_layout.addWidget(scale_z_label, scale_z_row, 0)
        geometry_layout.addWidget(self.scale_z_spin, scale_z_row, 1)
        geometry_layout.addWidget(self.uniform_scaling, uniform_scaling_row, 3, 1, 2)
        geometry_layout.addWidget(unit_of_measure_label, unit_of_measure_row, 4)
        geometry_layout.addWidget(self.unit_of_measure_combo, unit_of_measure_row, 3)
        self.__geometry_options_widget.setLayout(geometry_layout)

    def __init_generic_slicer_options_widget__(self):
        self.__slicer_options_widget = QGroupBox("Global Options", self)
        thickness_label = QLabel("Layer Thickness", self.__slicer_options_widget)
        thickness_edit = QDoubleSpinBox(self.__slicer_options_widget)
        thickness_edit.setSuffix(str('\u03BCm'))
        thickness_edit.setMaximum(1000000)
        thickness_edit.setMinimum(0)
        thickness_edit.setDecimals(1)
        thickness_edit.setSingleStep(0.1)
        thickness_edit.setValue(self.__slicer_widget.slice_thickness_microns)
        thickness_edit.valueChanged.connect(self.__slicer_widget.set_slice_thickness)
        laser_width_label = QLabel("Laser Width", self.__slicer_options_widget)
        laser_width_edit = QDoubleSpinBox(self.__slicer_options_widget)
        laser_width_edit.setSuffix(str('\u03BCm'))
        laser_width_edit.setMaximum(1000000)
        laser_width_edit.setMinimum(0)
        laser_width_edit.setDecimals(2)
        laser_width_edit.setSingleStep(0.01)
        laser_width_edit.setValue(self.__slicer_widget.laser_width_microns)
        laser_width_edit.valueChanged.connect(self.__slicer_widget.set_laser_width)
        building_area_width_label = QLabel("Building Area Width", self.__slicer_options_widget)
        building_area_edit_x = QSpinBox(self.__slicer_options_widget)
        building_area_edit_x.setSuffix(str(' mm'))
        building_area_edit_x.setMaximum(1000000)
        building_area_edit_x.setMinimum(0)
        building_area_edit_x.setValue(self.__slicer_widget.building_area_width_mm)
        building_area_edit_x.valueChanged.connect(self.__slicer_widget.set_building_area_width)
        building_area_height_label = QLabel("Building Area Height", self.__slicer_options_widget)
        building_area_edit_y = QSpinBox(self.__slicer_options_widget)
        building_area_edit_y.setSuffix(str(' mm'))
        building_area_edit_y.setMaximum(1000000)
        building_area_edit_y.setMinimum(0)
        building_area_edit_y.setValue(self.__slicer_widget.building_area_height_mm)
        building_area_edit_y.valueChanged.connect(self.__slicer_widget.set_building_area_height)
        building_area_width_row = 0
        building_area_height_row = building_area_width_row + 1
        thickness_label_row = 2
        pixel_size_row = thickness_label_row + 1
        contour_strategy_row = 4
        infill_strategy_row = contour_strategy_row + 1
        infill_density_row = infill_strategy_row + 1
        slice_button_row = infill_density_row
        save_job_row = slice_button_row + 1
        slice_layout = QGridLayout()
        slice_layout.addWidget(thickness_label, thickness_label_row, 0)
        slice_layout.addWidget(thickness_edit, thickness_label_row, 1)
        slice_layout.addWidget(laser_width_label, pixel_size_row, 0)
        slice_layout.addWidget(laser_width_edit, pixel_size_row, 1)
        slice_layout.addWidget(building_area_width_label, building_area_width_row, 0)
        slice_layout.addWidget(building_area_edit_x, building_area_width_row, 1)
        slice_layout.addWidget(building_area_height_label, building_area_height_row, 0)
        slice_layout.addWidget(building_area_edit_y, building_area_height_row, 1)
        slice_layout.addWidget(building_area_edit_y, building_area_height_row, 1)
        self.__slicer_options_widget.setLayout(slice_layout)

    def __init_slices_display_options_widget(self):
        self.__slices_display_options_widget = QGroupBox("Slices Display", self)
        display_slices_box = QCheckBox("Display Slices", self.__slices_display_options_widget)
        display_slices_box.setChecked(self.__slicer_widget.show_slices)
        display_slices_box.stateChanged.connect(self.__slicer_widget.set_show_slices)
        self.top_slice_slider = QSlider(orientation=Qt.Horizontal, parent=self.__slices_display_options_widget)
        self.top_slice_slider.setTickPosition(QSlider.TicksBothSides)
        self.top_slice_slider.setTickInterval(5)
        self.top_slice_slider.setRange(0, self.__slicer_widget.top_displayed_slice)
        self.top_slice_slider.setValue(self.__slicer_widget.top_displayed_slice)
        self.top_slice_spin = QSpinBox(self.__slices_display_options_widget)
        self.top_slice_spin.setPrefix("Top Slice: ")
        self.top_slice_spin.setMinimum(0)
        self.top_slice_spin.setMaximum(self.__slicer_widget.top_displayed_slice)
        self.top_slice_spin.setValue(self.__slicer_widget.top_displayed_slice)
        self.top_slice_slider.valueChanged.connect(self.top_slice_spin.setValue)
        self.top_slice_slider.valueChanged.connect(self.__slicer_widget.set_top_displayed_slices)
        self.top_slice_spin.valueChanged.connect(self.top_slice_slider.setValue)
        self.top_slice_spin.valueChanged.connect(self.__slicer_widget.set_top_displayed_slices)
        self.bottom_slice_slider = QSlider(orientation=Qt.Horizontal, parent=self.__slices_display_options_widget)
        self.bottom_slice_slider.setTickPosition(QSlider.TicksBothSides)
        self.bottom_slice_slider.setTickInterval(5)
        self.bottom_slice_slider.setRange(0, self.__slicer_widget.top_displayed_slice)
        self.bottom_slice_slider.setValue(self.__slicer_widget.top_displayed_slice)
        self.bottom_slice_spin = QSpinBox(self.__slices_display_options_widget)
        self.bottom_slice_spin.setPrefix("Bottom Slice: ")
        self.bottom_slice_spin.setMinimum(0)
        self.bottom_slice_spin.setMaximum(self.__slicer_widget.top_displayed_slice)
        self.bottom_slice_spin.setValue(self.__slicer_widget.top_displayed_slice)
        self.bottom_slice_slider.valueChanged.connect(self.bottom_slice_spin.setValue)
        self.bottom_slice_spin.valueChanged.connect(self.bottom_slice_slider.setValue)
        self.bottom_slice_slider.valueChanged.connect(self.__slicer_widget.set_bottom_displayed_slices)
        self.bottom_slice_spin.valueChanged.connect(self.__slicer_widget.set_bottom_displayed_slices)
        self.top_slice_slider.valueChanged.connect(self.bottom_slice_spin.setMaximum)
        self.top_slice_slider.valueChanged.connect(self.bottom_slice_slider.setMaximum)
        self.bottom_slice_spin.valueChanged.connect(self.top_slice_slider.setMinimum)
        self.bottom_slice_spin.valueChanged.connect(self.top_slice_spin.setMinimum)
        show_slices_line_width_spin = QSpinBox(self.__slices_display_options_widget)
        show_slices_line_width_spin.setSuffix(str(' % Width'))
        show_slices_line_width_spin.setMinimum(0)
        show_slices_line_width_spin.setMaximum(100)
        show_slices_line_width_spin.setValue(self.__slicer_widget.slice_planar_thickness_percentage)
        show_slices_line_width_spin.setSingleStep(1)
        show_slices_line_width_spin.valueChanged.connect(self.__slicer_widget.set_slice_planar_thickness_percentage)
        show_slices_line_thickness_spin = QSpinBox(self.__slices_display_options_widget)
        show_slices_line_thickness_spin.setSuffix(str(' % Thickness'))
        show_slices_line_thickness_spin.setMinimum(0)
        show_slices_line_thickness_spin.setMaximum(100)
        show_slices_line_thickness_spin.setValue(self.__slicer_widget.slice_vertical_thickness_percentage)
        show_slices_line_thickness_spin.setSingleStep(1)
        show_slices_line_thickness_spin.valueChanged.connect(self.__slicer_widget.set_slice_vertical_thickness_percentage)

        display_slices_row = 0
        bottom_slices_row = display_slices_row + 1
        top_slices_row = bottom_slices_row + 1
        line_size_row = top_slices_row + 1
        slices_layout = QGridLayout()
        slices_layout.addWidget(display_slices_box, display_slices_row, 0)
        slices_layout.addWidget(self.bottom_slice_spin, bottom_slices_row, 0)
        slices_layout.addWidget(self.bottom_slice_slider, bottom_slices_row, 1)
        slices_layout.addWidget(self.top_slice_spin, top_slices_row, 0)
        slices_layout.addWidget(self.top_slice_slider, top_slices_row, 1)
        slices_layout.addWidget(show_slices_line_width_spin, line_size_row, 0)
        slices_layout.addWidget(show_slices_line_thickness_spin, line_size_row, 1)
        self.__slices_display_options_widget.setLayout(slices_layout)

    def __init_geometry_specific_slicer_options_widget(self):
        self.__geometry_specific_slicer_options_widget = QGroupBox("Slicer Options", self)
        infill_scan_speed_label = QLabel('Infill Scan Speed (mm/s)', self.__geometry_specific_slicer_options_widget)
        self.infill_scan_speed_spin = QDoubleSpinBox(self.__geometry_specific_slicer_options_widget)
        self.infill_scan_speed_spin.setMinimum(0)
        self.infill_scan_speed_spin.setMaximum(10000)
        self.infill_scan_speed_spin.setValue(self.__slicer_widget.default_infill_scan_speed)
        self.infill_scan_speed_spin.valueChanged.connect(self.set_infill_scan_speed)
        infill_power_label = QLabel('Infill Laser Power (W)', self.__geometry_specific_slicer_options_widget)
        self.infill_power_spin = QSpinBox(self.__geometry_specific_slicer_options_widget)
        self.infill_power_spin.setMinimum(0)
        self.infill_power_spin.setMaximum(250)
        self.infill_power_spin.setValue(self.__slicer_widget.default_infill_laser_power)
        self.infill_power_spin.valueChanged.connect(self.set_infill_laser_power)
        infill_duty_cycle_label = QLabel('Infill Duty Cycle (%)', self.__geometry_specific_slicer_options_widget)
        self.infill_duty_cycle_spin = QSpinBox(self.__geometry_specific_slicer_options_widget)
        self.infill_duty_cycle_spin.setMinimum(0)
        self.infill_duty_cycle_spin.setMaximum(100)
        self.infill_duty_cycle_spin.setValue(self.__slicer_widget.default_infill_duty_cycle)
        self.infill_duty_cycle_spin.valueChanged.connect(self.set_infill_duty_cycle)
        infill_frequency_label = QLabel('Infill Frequency (Hz)', self.__geometry_specific_slicer_options_widget)
        self.infill_frequency_spin = QSpinBox(self.__geometry_specific_slicer_options_widget)
        self.infill_frequency_spin.setMinimum(1)
        self.infill_frequency_spin.setMaximum(100000)
        self.infill_frequency_spin.setValue(self.__slicer_widget.default_infill_frequency)
        self.infill_frequency_spin.valueChanged.connect(self.set_infill_frequency)
        contour_scan_speed_label = QLabel('Contour Scan Speed (mm/s)', self.__geometry_specific_slicer_options_widget)
        self.contour_scan_speed_spin = QDoubleSpinBox(self.__geometry_specific_slicer_options_widget)
        self.contour_scan_speed_spin.setMinimum(0)
        self.contour_scan_speed_spin.setMaximum(10000)
        self.contour_scan_speed_spin.setValue(self.__slicer_widget.default_contour_scan_speed)
        self.contour_scan_speed_spin.valueChanged.connect(self.set_contour_scan_speed)
        contour_power_label = QLabel('Contour Laser Power (W)', self.__geometry_specific_slicer_options_widget)
        self.contour_power_spin = QSpinBox(self.__geometry_specific_slicer_options_widget)
        self.contour_power_spin.setMinimum(0)
        self.contour_power_spin.setMaximum(250)
        self.contour_power_spin.setValue(self.__slicer_widget.default_contour_laser_power)
        self.contour_power_spin.valueChanged.connect(self.set_contour_laser_power)
        contoru_duty_cycle_label = QLabel('Contour Duty Cycle (%)', self.__geometry_specific_slicer_options_widget)
        self.contour_duty_cycle_spin = QSpinBox(self.__geometry_specific_slicer_options_widget)
        self.contour_duty_cycle_spin.setMinimum(0)
        self.contour_duty_cycle_spin.setMaximum(100)
        self.contour_duty_cycle_spin.setValue(self.__slicer_widget.default_contour_duty_cycle)
        self.contour_duty_cycle_spin.valueChanged.connect(self.set_contour_duty_cycle)
        contour_frequency_label = QLabel('Contour Frequency (Hz)', self.__geometry_specific_slicer_options_widget)
        self.contour_frequency_spin = QSpinBox(self.__geometry_specific_slicer_options_widget)
        self.contour_frequency_spin.setMinimum(1)
        self.contour_frequency_spin.setMaximum(100000)
        self.contour_frequency_spin.setValue(self.__slicer_widget.default_contour_frequency)
        self.contour_frequency_spin.valueChanged.connect(self.set_contour_frequency)
        contour_label = QLabel("Contour Strategy", self.__geometry_specific_slicer_options_widget)
        self.contour_combo = QComboBox(self.__geometry_specific_slicer_options_widget)
        for strategy in self.__slicer_widget.contour_strategies:
            self.contour_combo.addItem(strategy)
        self.contour_combo.setCurrentIndex(self.__slicer_widget.contour_strategy_idx)
        self.contour_combo.currentIndexChanged.connect(self.set_contour_strategy_idx)
        infill_label = QLabel("Infill Strategy", self.__geometry_specific_slicer_options_widget)
        self.infill_combo = QComboBox(self.__geometry_specific_slicer_options_widget)
        for strategy in self.__slicer_widget.infill_strategies:
            self.infill_combo.addItem(strategy)
        self.infill_combo.setCurrentIndex(self.__slicer_widget.infill_strategy_idx)
        self.infill_combo.currentIndexChanged.connect(self.set_infill_strategy_idx)
        infill_overlap_label = QLabel("Infill Overlap", self.__geometry_specific_slicer_options_widget)
        self.infill_overlap_spin = QSpinBox(self.__geometry_specific_slicer_options_widget)
        self.infill_overlap_spin.setSuffix(str('%'))
        self.infill_overlap_spin.setMinimum(0)
        self.infill_overlap_spin.setMaximum(99)
        self.infill_overlap_spin.setValue(self.__slicer_widget.default_infill_overlap)
        self.infill_overlap_spin.setSingleStep(1)
        self.infill_overlap_spin.valueChanged.connect(self.set_infill_overlap)
        infill_density_label = QLabel("Infill Density", self.__geometry_specific_slicer_options_widget)
        self.infill_density_spin = QSpinBox(self.__geometry_specific_slicer_options_widget)
        self.infill_density_spin.setSuffix(str('%'))
        self.infill_density_spin.setMinimum(0)
        self.infill_density_spin.setMaximum(100)
        self.infill_density_spin.setSingleStep(1)
        self.infill_density_spin.valueChanged.connect(self.set_infill_density)
        self.infill_density_spin.setValue(self.__slicer_widget.default_infill_density)
        infill_rotation_angle_label = QLabel("Infill Rotation", self.__geometry_specific_slicer_options_widget)
        self.infill_rotation_spin = QSpinBox(self.__geometry_specific_slicer_options_widget)
        self.infill_rotation_spin.setSuffix(str('\u00B0'))
        self.infill_rotation_spin.setMinimum(0)
        self.infill_rotation_spin.setMaximum(180)
        self.infill_rotation_spin.setValue(self.__slicer_widget.default_infill_rotation)
        self.infill_rotation_spin.setSingleStep(1)
        self.infill_rotation_spin.valueChanged.connect(self.set_infill_rotation_angle)
        contour_strategy_row = 0
        contour_power_row = contour_strategy_row + 1
        contour_scan_speed_row = contour_power_row + 1
        contour_duty_cycle_row = contour_scan_speed_row + 1
        contour_frequency_row = contour_duty_cycle_row + 1
        infill_strategy_row = contour_frequency_row + 1
        infill_density_row = infill_strategy_row + 1
        infill_overlap_row = infill_density_row + 1
        infill_rotation_row = infill_overlap_row + 1
        infill_power_row = infill_rotation_row + 1
        infill_scan_speed_row = infill_power_row + 1
        infill_duty_cycle_row = infill_scan_speed_row + 1
        infill_frequency_row = infill_duty_cycle_row + 1
        slice_layout = QGridLayout()
        slice_layout.addWidget(contour_label, contour_strategy_row, 0)
        slice_layout.addWidget(self.contour_combo, contour_strategy_row, 1)
        slice_layout.addWidget(contour_power_label, contour_power_row, 0)
        slice_layout.addWidget(self.contour_power_spin, contour_power_row, 1)
        slice_layout.addWidget(contour_scan_speed_label, contour_scan_speed_row, 0)
        slice_layout.addWidget(self.contour_scan_speed_spin, contour_scan_speed_row, 1)
        slice_layout.addWidget(contoru_duty_cycle_label, contour_duty_cycle_row, 0)
        slice_layout.addWidget(self.contour_duty_cycle_spin, contour_duty_cycle_row, 1)
        slice_layout.addWidget(contour_frequency_label, contour_frequency_row, 0)
        slice_layout.addWidget(self.contour_frequency_spin, contour_frequency_row, 1)
        slice_layout.addWidget(infill_power_label, infill_power_row, 0)
        slice_layout.addWidget(self.infill_power_spin, infill_power_row, 1)
        slice_layout.addWidget(infill_scan_speed_label, infill_scan_speed_row, 0)
        slice_layout.addWidget(self.infill_scan_speed_spin, infill_scan_speed_row, 1)
        slice_layout.addWidget(infill_duty_cycle_label, infill_duty_cycle_row, 0)
        slice_layout.addWidget(self.infill_duty_cycle_spin, infill_duty_cycle_row, 1)
        slice_layout.addWidget(infill_frequency_label, infill_frequency_row, 0)
        slice_layout.addWidget(self.infill_frequency_spin, infill_frequency_row, 1)
        slice_layout.addWidget(infill_label, infill_strategy_row, 0)
        slice_layout.addWidget(self.infill_combo, infill_strategy_row, 1)
        slice_layout.addWidget(infill_density_label, infill_density_row, 0)
        slice_layout.addWidget(self.infill_density_spin, infill_density_row, 1)
        slice_layout.addWidget(infill_overlap_label, infill_overlap_row, 0)
        slice_layout.addWidget(self.infill_overlap_spin, infill_overlap_row, 1)
        slice_layout.addWidget(infill_rotation_angle_label, infill_rotation_row, 0)
        slice_layout.addWidget(self.infill_rotation_spin, infill_rotation_row, 1)
        self.__geometry_specific_slicer_options_widget.setLayout(slice_layout)

    def __init_buttons_options_widget(self):
        self.__buttons_options_widget = QWidget(self)
        slice_geometry_button = QPushButton("Slice Geometry", self.__buttons_options_widget)
        slice_geometry_button.clicked.connect(self.start_slicing_process)
        slice_interrupt_button = QPushButton("Stop Slicing", self.__buttons_options_widget)
        slice_interrupt_button.clicked.connect(self.__slicer_widget.interrupt_slicing)
        save_job_button = QPushButton("Save Job", self.__buttons_options_widget)
        save_job_button.clicked.connect(self.save_print_job_to_file)
        load_geometry_button = QPushButton("Load Geometry")
        load_geometry_button.clicked.connect(self.load_geometry)
        remove_geometry_button = QPushButton("Remove Geometry")
        remove_geometry_button.clicked.connect(self.remove_geometry)
        save_scene_button = QPushButton("Save Scene")
        save_scene_button.clicked.connect(self.save_current_scene)
        self.slices_label = QLabel(f'Slicing progress: {0:.0f}/{0:.0f}', self.__buttons_options_widget)
        slice_layout = QHBoxLayout()
        slice_layout.addWidget(load_geometry_button)
        slice_layout.addWidget(remove_geometry_button)
        slice_layout.addWidget(save_scene_button)
        slice_layout.addWidget(slice_geometry_button)
        slice_layout.addWidget(slice_interrupt_button)
        slice_layout.addWidget(save_job_button)
        slice_layout.addWidget(self.slices_label)
        self.__buttons_options_widget.setLayout(slice_layout)

    @Slot()
    def load_geometry(self):
        file_names = QFileDialog.getOpenFileNames(caption='Select Geometry', dir='../',
                                                  filter="Files (*.obj *.stl *.json)", parent=self)
        loading_dialog = QMessageBox()
        loading_dialog.setText("Loading Geometry...")
        loading_dialog.setWindowTitle("AMLab Software")
        loading_dialog.setStandardButtons(QMessageBox.NoButton)
        loading_dialog.open()
        QGuiApplication.processEvents()
        swapyz = True
        for file_name in file_names[0]:
            file_extension = QFileInfo(file_name).suffix()
            if file_extension.lower() == 'json':
                geometries_names = self.__slicer_widget.load_scene(file_name)
                for name in geometries_names:
                    self.geometry_list.addItem(name)
                self.geometry_list.setCurrentIndex(self.geometry_list.count() - 1)
            elif self.__slicer_widget.load_geometry(file_name, swapyz):
                self.geometry_list.addItem(self.__slicer_widget.get_current_geometry().get_geometry_name())

        loading_dialog.close()
        QGuiApplication.processEvents()

    @Slot()
    def remove_geometry(self):
        self.__slicer_widget.remove_geometry()
        self.geometry_list.removeItem(self.geometry_list.currentIndex())
        
    @Slot()
    def save_current_scene(self):
        file_name = QFileDialog.getSaveFileName(caption='Select Scene File Name', dir='../', parent=self, filter="Files (*.json)")
        if len(file_name[0]) > 0:
            self.__slicer_widget.save_current_scene(file_name[0])

    @Slot()
    def start_slicing_process(self):
        self.__slicer_widget.prepare_for_slicing()

    @Slot()
    def save_print_job_to_file(self):
        file_name = QFileDialog.getSaveFileName(caption='Select Job File Name', dir='../', parent=self, filter="Files (*.g)")
        if len(file_name[0]) > 0:
            self.__slicer_widget.write_slice_job_to_file(file_name[0])

    @Slot(float, float, float)
    def update_size_label(self, width, depth, height):
        self.physical_size_label.setText(f'Width: {width:.3f} mm, Depth: {depth:.3f} mm, Height: {height:.3f} mm')

    @Slot(float)
    def update_fps_label(self, fps):
        self.fps_label.setText(f'fps: {fps:.2f}')

    @Slot(float, float)
    def update_slices_label(self, slice, total_slices):
        self.slices_label.setText(f'Slicing progress: {slice:.0f}/{total_slices:.0f}')
        self.top_slice_slider.setMaximum(total_slices)
        self.top_slice_slider.setValue(total_slices)
        self.top_slice_spin.setMaximum(total_slices)
        self.top_slice_spin.setValue(total_slices)
        self.bottom_slice_slider.setMaximum(total_slices)
        self.bottom_slice_slider.setValue(0)
        self.bottom_slice_spin.setMaximum(total_slices)
        self.bottom_slice_spin.setValue(0)

    @Slot(int)
    def update_geometry_transformations(self, index):
        if index >= 0:
            self.__slicer_widget.current_geometry_idx = index
            geometry = self.__slicer_widget.get_current_geometry()
            geometry.update_physical_size.connect(self.update_size_label)
            bbox_width_mm, bbox_depth_mm, bbox_height_mm = geometry.get_bbox_size_mm()
            self.update_size_label(bbox_width_mm, bbox_depth_mm, bbox_height_mm)
            x_rot = geometry.get_x_rot()
            y_rot = geometry.get_y_rot()
            z_rot = geometry.get_z_rot()
            x_scale = geometry.get_x_scale()
            y_scale = geometry.get_y_scale()
            z_scale = geometry.get_z_scale()
            x_pos = geometry.get_x_pos()
            z_pos = geometry.get_z_pos()
            unit_measurement = geometry.get_unit_of_measurement()
            self.__geometry_options_widget.blockSignals(True)
            self.rotate_x_slider.setValue(x_rot)
            self.rotate_x_spin.setValue(x_rot)
            self.rotate_y_slider.setValue(y_rot)
            self.rotate_y_spin.setValue(y_rot)
            self.rotate_z_slider.setValue(z_rot)
            self.rotate_z_spin.setValue(z_rot)
            self.translate_x_slider.setValue(x_pos)
            self.translate_x_spin.setValue(x_pos)
            self.translate_z_slider.setValue(z_pos)
            self.translate_z_spin.setValue(z_pos)
            self.scale_x_spin.setValue(x_scale)
            self.scale_y_spin.setValue(y_scale)
            self.scale_z_spin.setValue(z_scale)
            self.unit_of_measure_combo.setCurrentIndex(self.list_of_measures_coefficients.index(unit_measurement))
            self.__geometry_options_widget.blockSignals(False)

    @Slot(int)
    def update_slicer_options(self, index):
        if index >= 0:
            self.__slicer_widget.current_geometry_idx = index
            parameters = self.__slicer_widget.get_current_parameters()
            contour_scan_speed = parameters.get_contour_scan_speed()
            contour_laser_power = parameters.get_contour_laser_power()
            contour_duty_cycle = parameters.get_contour_duty_cycle()
            contour_frequency = parameters.get_contour_frequency()
            infill_scan_speed = parameters.get_infill_scan_speed()
            infill_laser_power = parameters.get_infill_laser_power()
            infill_duty_cycle = parameters.get_infill_duty_cycle()
            infill_frequency = parameters.get_infill_frequency()
            infill_density = parameters.get_infill_density()
            infill_overlap = parameters.get_infill_overlap()
            infill_idx = parameters.get_infill_strategy_idx()
            contour_idx = parameters.get_contour_strategy_idx()
            infill_rotation_angle = parameters.get_infill_rotation_angle()
            self.__geometry_specific_slicer_options_widget.blockSignals(True)
            self.contour_scan_speed_spin.setValue(contour_scan_speed)
            self.contour_power_spin.setValue(contour_laser_power)
            self.contour_duty_cycle_spin.setValue(contour_duty_cycle)
            self.contour_frequency_spin.setValue(contour_frequency)
            self.infill_scan_speed_spin.setValue(infill_scan_speed)
            self.infill_power_spin.setValue(infill_laser_power)
            self.infill_duty_cycle_spin.setValue(infill_duty_cycle)
            self.infill_frequency_spin.setValue(infill_frequency)
            self.infill_density_spin.setValue(infill_density)
            self.infill_overlap_spin.setValue(infill_overlap)
            self.infill_rotation_spin.setValue(infill_rotation_angle)
            self.infill_combo.setCurrentIndex(infill_idx)
            self.contour_combo.setCurrentIndex(contour_idx)
            self.__geometry_specific_slicer_options_widget.blockSignals(False)

    @Slot(str, int)
    def rotate_current_geometry(self, axis: str, value: int):
        geometry = self.__slicer_widget.get_current_geometry()
        if geometry:
            if axis.lower() == 'x':
                geometry.set_x_rotation(value)
            elif axis.lower() == 'y':
                geometry.set_y_rotation(value)
            elif axis.lower() == 'z':
                geometry.set_z_rotation(value)

    @Slot(str, int)
    def scale_current_geometry(self, axis: str, value: float):
        geometry = self.__slicer_widget.get_current_geometry()
        if geometry:
            if self.uniform_scaling.isChecked():
                geometry.set_x_scale(value)
                geometry.set_y_scale(value)
                geometry.set_z_scale(value)
                self.scale_x_spin.setValue(value)
                self.scale_y_spin.setValue(value)
                self.scale_z_spin.setValue(value)
            elif axis.lower() == 'x':
                geometry.set_x_rotation(value)
            elif axis.lower() == 'y':
                geometry.set_y_rotation(value)
            elif axis.lower() == 'z':
                geometry.set_z_rotation(value)

    @Slot(str, int)
    def translate_current_geometry(self, axis: str, value: float):
        geometry = self.__slicer_widget.get_current_geometry()
        if geometry:
            if axis.lower() == 'x':
                geometry.set_x_pos(value)
            elif axis.lower() == 'y':
                geometry.set_y_pos(value)
            elif axis.lower() == 'z':
                geometry.set_z_pos(value)

    @Slot(int)
    def update_unit_of_measure(self, index):
        geometry = self.__slicer_widget.get_current_geometry()
        if geometry:
            geometry.set_unit_of_measurement(self.list_of_measures_coefficients[index])

    @Slot(float)
    def set_infill_scan_speed(self, value):
        slicing_parameters = self.__slicer_widget.get_current_parameters()
        if slicing_parameters:
            slicing_parameters.set_infill_scan_speed(value)

    @Slot(float)
    def set_infill_laser_power(self, value):
        slicing_parameters = self.__slicer_widget.get_current_parameters()
        if slicing_parameters:
            slicing_parameters.set_infill_laser_power(value)

    @Slot(float)
    def set_infill_duty_cycle(self, value):
        slicing_parameters = self.__slicer_widget.get_current_parameters()
        if slicing_parameters:
            slicing_parameters.set_infill_duty_cycle(value)

    @Slot(float)
    def set_infill_frequency(self, value):
        slicing_parameters = self.__slicer_widget.get_current_parameters()
        if slicing_parameters:
            slicing_parameters.set_infill_frequency(value)

    @Slot(int)
    def set_infill_density(self, value):
        slicing_parameters = self.__slicer_widget.get_current_parameters()
        if slicing_parameters:
            slicing_parameters.set_infill_density(value)
        if value < 100:
            self.infill_overlap_spin.setDisabled(True)
        else:
            self.infill_overlap_spin.setDisabled(False)

    @Slot(float)
    def set_infill_overlap(self, value):
        slicing_parameters = self.__slicer_widget.get_current_parameters()
        if slicing_parameters:
            slicing_parameters.set_infill_overlap(value)

    @Slot(float)
    def set_infill_rotation_angle(self, value):
        slicing_parameters = self.__slicer_widget.get_current_parameters()
        if slicing_parameters:
            slicing_parameters.set_infill_rotation_angle(value)

    @Slot(float)
    def set_contour_scan_speed(self, value):
        slicing_parameters = self.__slicer_widget.get_current_parameters()
        if slicing_parameters:
            slicing_parameters.set_contour_scan_speed(value)

    @Slot(float)
    def set_contour_laser_power(self, value):
        slicing_parameters = self.__slicer_widget.get_current_parameters()
        if slicing_parameters:
            slicing_parameters.set_contour_laser_power(value)

    @Slot(float)
    def set_contour_duty_cycle(self, value):
        slicing_parameters = self.__slicer_widget.get_current_parameters()
        if slicing_parameters:
            slicing_parameters.set_contour_duty_cycle(value)

    @Slot(float)
    def set_contour_frequency(self, value):
        slicing_parameters = self.__slicer_widget.get_current_parameters()
        if slicing_parameters:
            slicing_parameters.set_contour_frequency(value)

    @Slot(int)
    def set_contour_strategy_idx(self, value):
        slicing_parameters = self.__slicer_widget.get_current_parameters()
        if slicing_parameters:
            slicing_parameters.set_contour_strategy_idx(value)

    @Slot(int)
    def set_infill_strategy_idx(self, value):
        slicing_parameters = self.__slicer_widget.get_current_parameters()
        if slicing_parameters:
            slicing_parameters.set_infill_strategy_idx(value)

class MyQComboBox(QComboBox):

    combo_box_clicked = Signal()

    @Slot()
    def showPopup(self):
        self.combo_box_clicked.emit()
        super(MyQComboBox, self).showPopup()


class MyQSlider(QSlider):

    myValueChanged = Signal(str, int)

    def __init__(self, axis='X', orientation=Qt.Vertical, parent=None):
        super().__init__(orientation=orientation, parent=parent)
        self.axis = axis
        self.valueChanged.connect(self.mySetValue)
        # .valueChanged.connect(self.setValue)

    def mySetValue(self, value: int):
        self.myValueChanged.emit(self.axis, value)


class MyQSpinBox(QSpinBox):

    myValueChanged = Signal(str, int)

    def __init__(self, axis='X', parent=None):
        super().__init__(parent=parent)
        self.axis = axis
        self.valueChanged.connect(self.mySetValue)

    def mySetValue(self, value: int):
        self.myValueChanged.emit(self.axis, value)


class MyQDoubleSpinBox(QDoubleSpinBox):

    myValueChanged = Signal(str, float)

    def __init__(self, axis='X', parent=None):
        super().__init__(parent=parent)
        self.axis = axis
        self.valueChanged.connect(self.mySetValue)

    def mySetValue(self, value: float):
        self.myValueChanged.emit(self.axis, value)