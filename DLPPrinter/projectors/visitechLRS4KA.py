from PySide2.QtCore import Signal, Slot
from PySide2.QtWidgets import QWidget
from PySide2.QtGui import  QPixmap
# from DLPPrinter.external_libraries.kpdlpPyWrapper import KpDLP660Driver, KpMSP430Driver


class VisitechLRS4KA(QWidget):

    print_text_signal = Signal(str)
    connection_status_signal = Signal(bool)
    display_image_signal = Signal(QPixmap)

    def __init__(self):
        QWidget.__init__(self)
        try:
            self.pywrapper = __import__('external_libraries.visitech.kpdlpPyWrapper', fromlist=['KpDLP660Driver', 'KpMSP430Driver'])
        except ImportError:
            return None
        self.kpdlp660 = self.pywrapper.KpDLP660Driver()
        self.kpmsp430 = self.pywrapper.KpMSP430Driver()
        self.LED_time_on = 0.0
        self.is_connected = False

    @Slot()
    def init_projector(self):
        if self.is_connected:
            self.print_text_signal.emit('Projector already ON!')
            return False
        self.print_text_signal.emit('...Starting Projector...')
        result = self.kpmsp430.USB_Open()
        if result == -1 or not self.kpmsp430.USB_IsConnected():
            self.print_text_signal.emit('...Projector initialization failed!')
            self.connection_status_signal.emit(False)
            return False
        result = self.kpdlp660.USB_Open()
        if result == -1 or not self.kpdlp660.USB_IsConnected():
            self.print_text_signal.emit('...Projector initialization failed!')
            self.connection_status_signal.emit(False)
            return False
        result, state = self.kpdlp660.getPowerMode()
        # STATE==2 MEANS PROJECTOR IS READY
        if result == -1 or state != 2:
            self.print_text_signal.emit('...Projector initialization failed!')
            self.connection_status_signal.emit(False)
            return False
        result = self.kpdlp660.changeProjectorMode(self.pywrapper.KpDLP660Driver.Display.HDMI)
        if result == -1:
            self.print_text_signal.emit('...Projector initialization failed! (Unable to set HDMI mode)')
            self.connection_status_signal.emit(False)
            return False
        result, amplitude = self.kpmsp430.getLEDAmplitude()
        if result == -1:
            self.print_text_signal.emit('...Projector initialization failed! (Unable to get LED Driver Amplitude)')
            self.connection_status_signal.emit(False)
            return False
        result = self.kpmsp430.setLEDAmplitude(0)
        self.kpdlp660.LEDWithTimer(True, 0.0)
        self.kpdlp660.LEDWithTimer(False, 0.0)
        if result == -1:
            self.print_text_signal.emit('...Projector initialization failed! (Unable to set LED Driver Amplitude)')
            self.connection_status_signal.emit(False)
            return False
        self.print_text_signal.emit("...Projector READY!")
        self.connection_status_signal.emit(True)
        self.is_connected = True
        return True

    def stop_projector(self):
        self.kpdlp660.LEDWithTimer(False, 0.0)
        self.kpmsp430.setLEDAmplitude(0)
        result = self.kpdlp660.USB_Close()
        if result == -1:
            self.print_text_signal.emit('...Failed to close projector!')
            self.connection_status_signal.emit(True)
            return False
        result = self.kpmsp430.USB_Close()
        if result == -1:
            self.print_text_signal.emit('...Failed to close projector!')
            self.connection_status_signal.emit(True)
            return False
        self.is_connected = False
        self.connection_status_signal.emit(False)

    def set_projector_amplitude(self, amplitude):
        result = self.kpmsp430.setLEDAmplitude(amplitude)
        if amplitude > 0:
            output, self.LED_time_on = self.kpmsp430.getLEDOnTime()
            self.kpdlp660.LEDWithTimer(True, 0.0)
        else:
            self.kpdlp660.LEDWithTimer(False, 0.0)
            output, tmp = self.kpmsp430.getLEDOnTime()
            self.print_text_signal.emit('...LED was on for ' + str(1000*(tmp-self.LED_time_on)) + ' ms!')
        if result == -1:
            self.print_text_signal.emit('...Failed to set projector amplitude!')
            return False
        return True





