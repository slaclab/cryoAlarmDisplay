from dataclasses import dataclass
from typing import List

from cavityWidget import CavityWidget
from epics import PV
from pydm import Display
from scLinac import Cryomodule, Linac, LINACS, CM_LINAC_MAP
from CavityDisplay import statusCallback, severityCallback, changeShape


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
    def __init__(self, name, cryomoduleStringList):
        super().__init__(name, cryomoduleStringList, cryomoduleClass=AlarmCryomodule)

        beamLineVacuumPVString = "VGXX:{linac}:0202:COMBO_P".format(linac=name)
        self.beamLineVacuumPV = AlarmPV(pv=PV(beamLineVacuumPVString),
                                        lowAlarmLimit=-2,
                                        lowWarningLimit=-1,
                                        highAlarmLimit=2,
                                        highWarningLimit=1)


class AlarmCryomodule(Cryomodule):
    def __init__(self, cryoName, linacObject: AlarmLinac):
        super().__init__(cryoName, linacObject)
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


ALARM_LINAC_OBJECTS = []
for idx, (name, cryomoduleList) in enumerate(LINACS):
    ALARM_LINAC_OBJECTS.append(AlarmLinac(name, cryomoduleList))


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

        cryomodules: List[CavityWidget] = self.ui.cryomodules.findChildren(CavityWidget)
        for cryomoduleDisplayObj in cryomodules:
            cryomoduleName = cryomoduleDisplayObj.cavityText
            linacIdx = CM_LINAC_MAP[cryomoduleName]
            linacObject = ALARM_LINAC_OBJECTS[linacIdx]
            cryomoduleObject = linacObject.cryomodules[cryomoduleName]


def alarmCallback(cryomodule: AlarmCryomodule, cavityWidget: CavityWidget, **kw):
    if cryomodule.isAlarming:
        severityCallback(cavityWidget, 2)

    elif cryomodule.isWarning:
        severityCallback(cavityWidget, 1)

    else:
        severityCallback(cavityWidget, 0)
