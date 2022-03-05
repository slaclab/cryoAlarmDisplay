from dataclasses import dataclass

from cavityWidget import CavityWidget
from epics import PV
from frontEnd_constants import shapeParameterDict
from functools import partial
from pydm import Display
from pydm.widgets.template_repeater import PyDMTemplateRepeater
from typing import Callable, List, Optional

from scLinac import Cavity, Cryomodule, LINACS, Linac

TRANSFER_LINE_ALARM_LIMIT = 8E-5


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
    alarmLimit: float
    updateFunction: Callable

    def __post_init__(self):
        self.pv.add_callback(partial(alarmCallback, self.alarmLimit,
                                     self.updateFunction))


def alarmCallback(alarmLimit, updateFunction, value, **kw):
    isAlarming = value is None or value >= alarmLimit
    updateFunction(isAlarming)


class AlarmLinac(Linac):
    def __init__(self, linacName, cryomoduleStringList):
        super().__init__(linacName, cryomoduleStringList,
                         cryomoduleClass=AlarmCryomodule)

        self.widget: Optional[PyDMTemplateRepeater] = None

        beamLineVacuumPVString = "VGXX:{linac}:0202:COMBO_P".format(linac=linacName)
        self.beamLineVacuumPV = AlarmPV(pv=PV(beamLineVacuumPVString),
                                        alarmLimit=1.5E-8, updateFunction=self.update)

    def update(self, isAlarming):
        if isAlarming:
            self.widget.setStyleSheet("background-color: rgb(150, 0, 0);")

        else:
            self.widget.setStyleSheet("")


class AlarmCryomodule(Cryomodule):
    def __init__(self, cryoName, linacObject: AlarmLinac, cavityClass=Cavity):
        super().__init__(cryoName, linacObject)

        self.widget: Optional[CavityWidget] = None

        couplerVacuumPVString = "VGXX:{linac}:{cryomodule}14:COMBO_P".format(linac=linacObject.name,
                                                                             cryomodule=cryoName)
        self.couplerVacuumPV = AlarmPV(pv=PV(couplerVacuumPVString),
                                       alarmLimit=1E-5,
                                       updateFunction=self.update)

        insulatingVacuumPVString = "VGXX:{linac}:{cryomodule}96:COMBO_P".format(linac=linacObject.name,
                                                                                cryomodule=cryoName)
        self.insulatingCouplerVacuumPV = AlarmPV(pv=PV(insulatingVacuumPVString),
                                                 alarmLimit=8E-5,
                                                 updateFunction=self.update)

        lineBPressurePVString = "CPT:CM{cm}:2602:US:PRESS".format(cm=cryoName)
        self.lineBPressurePV = AlarmPV(pv=PV(lineBPressurePVString),
                                       alarmLimit=2,
                                       updateFunction=self.update)

    def update(self, isAlarming):
        if isAlarming:
            updateWidget(self.widget, 2)

        else:
            updateWidget(self.widget, 0)


ALARM_LINAC_OBJECTS = []
for idx, (name, cryomoduleList) in enumerate(LINACS):
    ALARM_LINAC_OBJECTS.append(AlarmLinac(name, cryomoduleList))


class CryoAlarmDisplay(Display):

    def __init__(self, parent=None, args=None, ui_filename="alarmDisplay.ui"):
        super(CryoAlarmDisplay, self).__init__(parent=parent, args=args,
                                               ui_filename=ui_filename)

        self.transferLineVacuum1 = AlarmPV(pv=PV("CPT:FC01:950:VG:PRESS"),
                                           alarmLimit=TRANSFER_LINE_ALARM_LIMIT,
                                           updateFunction=partial(self.updateVG,
                                                                  self.ui.vg1))

        self.transferLineVacuum2 = AlarmPV(pv=PV("CPT:FC02:953:VG:PRESS"),
                                           alarmLimit=TRANSFER_LINE_ALARM_LIMIT,
                                           updateFunction=partial(self.updateVG,
                                                                  self.ui.vg2))

        self.transferLineVacuum3 = AlarmPV(pv=PV("CPT:FC03:954:VG:PRESS"),
                                           alarmLimit=TRANSFER_LINE_ALARM_LIMIT,
                                           updateFunction=partial(self.updateVG,
                                                                  self.ui.vg3))

        self.transferLineVacuum4 = AlarmPV(pv=PV("CPT:FC04:957:VG:PRESS"),
                                           alarmLimit=TRANSFER_LINE_ALARM_LIMIT,
                                           updateFunction=partial(self.updateVG,
                                                                  self.ui.vg4))

        templateRepeaters: List[PyDMTemplateRepeater] = [self.ui.L0B,
                                                         self.ui.L1B,
                                                         self.ui.L2B,
                                                         self.ui.L3B]

        for linacIdx, templateRepeater in enumerate(templateRepeaters):
            templateRepeater.loadWhenShown = False

            cryomodules: List[CavityWidget] = templateRepeater.findChildren(CavityWidget)
            for cryomoduleDisplayObj in cryomodules:
                cryomoduleName = cryomoduleDisplayObj.cavityText
                linacObject = ALARM_LINAC_OBJECTS[linacIdx]
                linacObject.widget = templateRepeater
                print([linacObject.name, linacObject.widget])
                cryomoduleObject: AlarmCryomodule = linacObject.cryomodules[cryomoduleName]
                cryomoduleObject.widget = cryomoduleDisplayObj

    @staticmethod
    def updateVG(widget, isAlarming):
        if isAlarming:
            updateWidget(widget, 2)

        else:
            updateWidget(widget, 0)
