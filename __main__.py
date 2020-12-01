# -*- coding: utf-8 -*-
"""
Created on Mon Jun  3 15:20:33 2019

@author: aluo
"""
import mainGUI
from PySide2.QtWidgets import QApplication
from PySide2.QtOpenGL import QGLFormat
import sys


if __name__ == "__main__":
    app = QApplication(sys.argv)
    gl_format = QGLFormat()
    gl_format.setVersion(3, 3)
    gl_format.setProfile(QGLFormat.CoreProfile )
    gl_format.setSampleBuffers(True)
    main_gui = mainGUI.MainGui()
    main_gui.show()
    sys.exit(app.exec_())
