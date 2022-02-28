from dataclasses import dataclass
from typing import List, Optional

from cavityWidget import CavityWidget
from epics import PV
from pydm import Display
from scLinac import Cryomodule, Linac, LINACS, CM_LINAC_MAP
from pydm.widgets.template_repeater import PyDMTemplateRepeater
from frontEnd_constants import shapeParameterDict


# Change PyDMDrawingPolygon color
def changeShape(cavity_widget, shapeParameterObject):
    cavity_widget.brush.setColor(shapeParameterObject.fillColor)
    cavity_widget.penColor = shapeParameterObject.borderColor
    cavity_widget.numberOfPoints = shapeParameterObject.numPoints
    cavity_widget.rotation = shapeParameterObject.rotation


# Updates shape depending on pv value
def updateWidget(cavity_widget, value):
    changeShape(cavity_widget,
                shapeParameterDict[value] if value in shapeParameterDict
                else shapeParameterDict[3])


@dataclass()
class AlarmPV:
    pv: PV
    lowAlarmLimit: float
    lowWarningLimit: float
    highAlarmLimit: float
    highWarningLimit: float

    @property
    def isWarning(self):
        return (self.lowWarningLimit >= self.pv.value >= self.lowAlarmLimit
                or self.highWarningLimit <= self.pv.value <= self.highAlarmLimit)

    @property
    def isAlarming(self):
        return self.pv.value >= self.highAlarmLimit or self.pv.value <= self.lowAlarmLimit


class AlarmLinac(Linac):
    def __init__(self, linacName, cryomoduleStringList):
        print(cryomoduleStringList)
        super().__init__(linacName, cryomoduleStringList, cryomoduleClass=AlarmCryomodule)

        self.widget: Optional[PyDMTemplateRepeater] = None

        beamLineVacuumPVString = "VGXX:{linac}:0202:COMBO_P".format(linac=linacName)
        self.beamLineVacuumPV = AlarmPV(pv=PV(beamLineVacuumPVString),
                                        lowAlarmLimit=-2,
                                        lowWarningLimit=-1,
                                        highAlarmLimit=2,
                                        highWarningLimit=1)

    @property
    def isAlarming(self):
        return self.beamLineVacuumPV.isAlarming

    @property
    def isWarning(self):
        return self.beamLineVacuumPV.isWarning

    def update(self):
        if self.isAlarming:
            self.widget.setStyleSheet("background-color: rgb(150, 0, 0);")

        elif self.isWarning:
            self.widget.setStyleSheet("background-color: rgb(244,230,67);")

        else:
            self.widget.setStyleSheet("")


class AlarmCryomodule(Cryomodule):
    def __init__(self, cryoName, linacObject: AlarmLinac):
        super().__init__(cryoName, linacObject)

        self.widget: Optional[CavityWidget] = None

        couplerVacuumPVString = "VGXX:{linac}:{cryomodule}14:COMBO_P".format(linac=linacObject.name,
                                                                             cryomodule=cryoName)
        self.couplerVacuumPV = AlarmPV(pv=PV(couplerVacuumPVString),
                                       lowAlarmLimit=-2,
                                       lowWarningLimit=-1,
                                       highAlarmLimit=2,
                                       highWarningLimit=1)

        insulatingVacuumPVString = "VGXX:{linac}:{cryomodule}96:COMBO_P".format(linac=linacObject.name,
                                                                                cryomodule=cryoName)
        self.insulatingCouplerVacuumPV = AlarmPV(pv=PV(insulatingVacuumPVString),
                                                 lowAlarmLimit=-2,
                                                 lowWarningLimit=-1,
                                                 highAlarmLimit=2,
                                                 highWarningLimit=1)

        lineBPressurePVString = "CPT:CM{cm}:2602:US:PRESS".format(cm=cryoName)
        self.lineBPressurePV = AlarmPV(pv=PV(lineBPressurePVString),
                                       lowAlarmLimit=-2,
                                       lowWarningLimit=-1,
                                       highAlarmLimit=2,
                                       highWarningLimit=1)

    @property
    def isWarning(self):
        return (self.lineBPressurePV.isWarning
                or self.insulatingCouplerVacuumPV.isWarning
                or self.couplerVacuumPV.isWarning)

    @property
    def isAlarming(self):
        return (self.lineBPressurePV.isAlarming
                or self.insulatingCouplerVacuumPV.isAlarming
                or self.couplerVacuumPV.isAlarming)

    def update(self):
        if self.isAlarming:
            updateWidget(self.widget, 2)

        elif self.isWarning:
            updateWidget(self.widget, 1)

        else:
            updateWidget(self.widget, 0)


ALARM_LINAC_OBJECTS = []
for idx, (name, cryomoduleList) in enumerate(LINACS):
    ALARM_LINAC_OBJECTS.append(AlarmLinac(name, cryomoduleList))


def run():
    while True:
        for linac in ALARM_LINAC_OBJECTS:
            linac.update()
            for cryomodule in linac.cryomodules:
                cryomodule.update()


class CryoAlarmDisplay(Display):
    # def ui_filename(self):
    #     return "alarmDisplay.ui"

    def __init__(self, parent=None, args=None, ui_filename="alarmDisplay.ui"):
        super(CryoAlarmDisplay, self).__init__(parent=parent, args=args,
                                               ui_filename=ui_filename)
        self.ui.cryomodules.loadWhenShown = False

        self.transferLineVacuum1 = AlarmPV(pv=PV("CPT:FC01:950:VG:PRESS"),
                                           lowAlarmLimit=-2,
                                           lowWarningLimit=-1,
                                           highAlarmLimit=2,
                                           highWarningLimit=1)

        self.transferLineVacuum2 = AlarmPV(pv=PV("CPT:FC02:953:VG:PRESS"),
                                           lowAlarmLimit=-2,
                                           lowWarningLimit=-1,
                                           highAlarmLimit=2,
                                           highWarningLimit=1)

        self.transferLineVacuum3 = AlarmPV(pv=PV("CPT:FC03:954:VG:PRESS"),
                                           lowAlarmLimit=-2,
                                           lowWarningLimit=-1,
                                           highAlarmLimit=2,
                                           highWarningLimit=1)

        self.transferLineVacuum4 = AlarmPV(pv=PV("CPT:FC04:957:VG:PRESS"),
                                           lowAlarmLimit=-2,
                                           lowWarningLimit=-1,
                                           highAlarmLimit=2,
                                           highWarningLimit=1)

        templateRepeaters: List[PyDMTemplateRepeater] = [self.ui.L0B,
                                                         self.ui.L1B,
                                                         self.ui.L2B,
                                                         self.ui.L3B]

        for linacIdx, templateRepeater in enumerate(templateRepeaters):

            cryomodules: List[CavityWidget] = templateRepeater.findChildren(CavityWidget)
            for cryomoduleDisplayObj in cryomodules:
                cryomoduleName = cryomoduleDisplayObj.cavityText
                linacObject = ALARM_LINAC_OBJECTS[linacIdx]
                linacObject.widget = templateRepeater
                cryomoduleObject: AlarmCryomodule = linacObject.cryomodules[cryomoduleName]
                cryomoduleObject.widget = cryomoduleDisplayObj

        run()


def alarmCallback(cryomodule: AlarmCryomodule, cavityWidget: CavityWidget, **kw):
    if cryomodule.isAlarming:
        updateWidget(cavityWidget, 2)

    elif cryomodule.isWarning:
        updateWidget(cavityWidget, 1)

    else:
        updateWidget(cavityWidget, 0)
