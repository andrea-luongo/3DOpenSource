import kpdlpPyWrapper as m
from kpdlpPyWrapper import KpDLP660Driver, KpMSP430Driver

print(dir(m))
print("Testing KpDLP660Driver")
p = KpDLP660Driver()
print("RED", int(KpDLP660Driver.RED))
print("setTPGSelect", p.setTPGSelect(KpDLP660Driver.RED))
print("getTPGSelect", p.getTPGSelect())
print("setImageFreeze", p.setImageFreeze(True))
print("getImageFreeze", p.getImageFreeze())
print("setLongAxisImageFlip", p.setLongAxisImageFlip(True))
print("getLongAxisImageFlip", p.getLongAxisImageFlip())
print("setShortAxisImageFlip", p.setShortAxisImageFlip(True))
print("getShortAxisImageFlip", p.getShortAxisImageFlip())
print("setDLPFunctions", p.setDLPFunctions(True, False, True, False, True, False, True))
print("getDLPFunctions", p.getDLPFunctions())
print("setSolidFieldColor", p.setSolidFieldColor(0, 1, 2))
print("getSolidFieldColor", p.getSolidFieldColor())
print("setGammaTableSelection", p.setGammaTableSelection(1))
print("getGammaTableSelection", p.getGammaTableSelection())
print("setLedCurrents", p.setLedCurrents(10, 50, 20))
print("getLedCurrents",p.getLedCurrents())
print("setLEDMode",p.setLEDMode(True))
print("getLEDMode",p.getLEDMode())
print("LEDWithTimer",p.LEDWithTimer(True, 30.2))
print("changeProjectorMode",p.changeProjectorMode(KpDLP660Driver.HDMI))
print("getProjectorOutputMode",p.getProjectorOutputMode())
print("getFRCParameters",p.getFRCParameters())
print("getSystemStatusWord",p.getSystemStatusWord())
print("getErrorStatusWord",p.getErrorStatusWord())
print("getPowerMode",p.getPowerMode())
print("FPGAVersion",p.FPGAVersion())
print("getVersion",p.getVersion())
print("setXPRmode",p.setXPRmode(3))
print("getXPRmode",p.getXPRmode())
print("setXPR_DAC",p.setXPR_DAC(5))
print("getXPR_DAC",p.getXPR_DAC())
print("setFanPWM",p.setFanPWM(0, 100))
print("getFanPWM",p.getFanPWM(0))
print("USB_Open",p.USB_Open())
print("USB_IsConnected",p.USB_IsConnected())
print("USB_Close",p.USB_Close())
print("USB_Init",p.USB_Init())
print("USB_Exit",p.USB_Exit())

print("Testing KpMSP430Driver")
q = KpMSP430Driver()
print("USB_Open", q.USB_Open())
print("USB_IsConnected", q.USB_IsConnected())
print("USB_Close", q.USB_Close())
print("USB_Init", q.USB_Init())
print("USB_Exit", q.USB_Exit())
print("getLEDAmplitude", q.getLEDAmplitude())
print("setLEDAmplitude", q.setLEDAmplitude(30))
print("getLEDDriveTemp", q.getLEDDriveTemp())
print("getLEDBoardTemp", q.getLEDBoardTemp())
print("getLEDStatus", q.getLEDStatus())
print("getLEDLightFeedback", q.getLEDLightFeedback())
print("getLEDCurrentFeedback", q.getLEDCurrentFeedback())
print("getLEDOnTime", q.getLEDOnTime())
print("getLEDlogEntry", q.getLEDlogEntry(0))
print("getVersion", q.getVersion())
print("setBSLMode", q.setBSLMode())
print("getDLLVersion", q.getDLLVersion())
print("busy", q.busy())











