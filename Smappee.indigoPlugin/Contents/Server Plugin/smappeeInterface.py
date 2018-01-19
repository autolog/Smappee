#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# Smappee - smappeeInterface © Autolog 2018
#

try:
    # noinspection PyUnresolvedReferences
    import indigo
except ImportError, e:
    pass

import datetime
import logging
import Queue
import subprocess
import sys
import threading
import time


# noinspection PyUnresolvedReferences,PyPep8Naming
class ThreadSmappeeInterface(threading.Thread):

    # This class manages the interface to Smappee

    def __init__(self, pluginGlobals, event):

        threading.Thread.__init__(self)

        self.globals = pluginGlobals

        self.smappeeInterfaceLogger = logging.getLogger("Plugin.smappeeInterface")
        self.smappeeInterfaceLogger.setLevel(self.globals['debug']['smappeeInterface'])

        self.methodTracer = logging.getLogger("Plugin.method")
        self.methodTracer.setLevel(self.globals['debug']['methodTrace'])

        self.smappeeInterfaceLogger.debug(u"Debugging Interact With Smappee Thread")

        self.threadStop = event

    def convertUnicode(self, unicodeInput):
        if isinstance(unicodeInput, dict):
            return dict(
                [(self.convertUnicode(key), self.convertUnicode(value)) for key, value in unicodeInput.iteritems()])
        elif isinstance(unicodeInput, list):
            return [self.convertUnicode(element) for element in unicodeInput]
        elif isinstance(unicodeInput, unicode):
            return unicodeInput.encode('utf-8')
        else:
            return unicodeInput

    def run(self):
        self.methodTracer.threaddebug(u"ThreadsmappeeInterfaceRun")

        try:
            self.smappeeInterfaceLogger.debug(u"Smappee Command Thread initialised.")
            keepThreadActive = True
            while keepThreadActive:

                try:
                    commandToSend = self.globals['queues']['sendToSmappee'].get(True, 5)
                    self.smappeeInterfaceLogger.debug(
                            u"Command to send to Smappee [Type=%s]: %s" % (type(commandToSend), commandToSend))

                    smappeeCommand = commandToSend[0]

                    if smappeeCommand == 'ENDTHREAD':
                        keepThreadActive = False


                    self.currentTimeUtc = time.mktime(indigo.server.getTime().timetuple())
                    self.currentTimeDay = int(datetime.datetime.fromtimestamp(self.currentTimeUtc).strftime('%j'))
                    self.smappeeInterfaceLogger.debug(u"%s - self.currentTimeUtc[%s]=[%s], DAY=[%s]" % (
                        smappeeCommand, type(self.currentTimeUtc), self.currentTimeUtc, self.currentTimeDay))

                    self.toTimeUtc = str("%s000" % (int(self.currentTimeUtc + float(3600))))  # Add +1 hour to current time
                    self.smappeeInterfaceLogger.debug(u"%s - self.toTimeUtc=[%s]" % (smappeeCommand, self.toTimeUtc))

                    if smappeeCommand == 'GET_CONSUMPTION' or smappeeCommand == 'RESET_CONSUMPTION':

                        try:
                            self.serviceLocationId = commandToSend[1]
                            self.electricityId = int(
                                self.globals['smappeeServiceLocationIdToDevId'][self.serviceLocationId][
                                    'electricityId'])
                            self.electricityNetId = int(
                                self.globals['smappeeServiceLocationIdToDevId'][self.serviceLocationId][
                                    'electricityNetId'])
                            self.electricitySavedId = int(
                                self.globals['smappeeServiceLocationIdToDevId'][self.serviceLocationId][
                                    'electricitySavedId'])
                            self.solarId = int(
                                self.globals['smappeeServiceLocationIdToDevId'][self.serviceLocationId]['solarId'])
                            self.solarUsedId = int(
                                self.globals['smappeeServiceLocationIdToDevId'][self.serviceLocationId]['solarUsedId'])
                            self.solarExportedId = int(
                                self.globals['smappeeServiceLocationIdToDevId'][self.serviceLocationId][
                                    'solarExportedId'])
                        except Exception, e:
                            self.smappeeInterfaceLogger.error(
                                    u"Debugging Error detected in Smappee Command Thread. Line '%s' has error='%s'" % (
                                        sys.exc_traceback.tb_lineno, e))

                        if self.electricityId == 0 and self.solarId == 0:
                            pass
                            self.smappeeInterfaceLogger.debug(
                                    u"%s - Smappee Base Devices [ELECTRICITY and SOLAR PV] not defined" % smappeeCommand)
                        else:
                            self.smappeeInterfaceLogger.debug(u"%s - GET_CONSUMPTION - smappeeServiceLocationIdToDevId = [%s]" % (
                                smappeeCommand, self.globals['smappeeServiceLocationIdToDevId']))

                            # #TIME# self.currentTimeUtc = time.mktime(indigo.server.getTime().timetuple())
                            # #TIME# self.currentTimeDay = int(datetime.datetime.fromtimestamp(self.currentTimeUtc).strftime('%j'))
                            self.smappeeInterfaceLogger.debug(u"%s - self.currentTimeUtc[%s]=[%s], DAY=[%s]" % (
                                smappeeCommand, type(self.currentTimeUtc), self.currentTimeUtc, self.currentTimeDay))

                            if self.electricityId != 0:
                                devElectricity = indigo.devices[self.electricityId]

                                self.smappeeInterfaceLogger.debug(u"%s - lastReadingElectricityUtc[%s] =[%s]" % (smappeeCommand, type(
                                    self.globals['smappees'][devElectricity.id]['lastReadingElectricityUtc']),
                                                                                                  self.globals[
                                                                                                      'smappees'][
                                                                                                      devElectricity.id][
                                                                                                      'lastReadingElectricityUtc']))
                                self.lastReadingElectricityDay = int(datetime.datetime.fromtimestamp(float(
                                    self.globals['smappees'][devElectricity.id][
                                        'lastReadingElectricityUtc'] / 1000)).strftime('%j'))

                                self.smappeeInterfaceLogger.debug(u"%s - lastReadingElectricityDay=[%s] vs currentTimeDay=[%s]" % (
                                    smappeeCommand, self.lastReadingElectricityDay, self.currentTimeDay))

                                if self.globals['smappees'][devElectricity.id][
                                        'lastReadingElectricityUtc'] > 0 and self.lastReadingElectricityDay == self.currentTimeDay and smappeeCommand != 'RESET_CONSUMPTION':
                                    self.fromTimeElectricityUtc = str(
                                        int(self.globals['smappees'][devElectricity.id]['lastReadingElectricityUtc']))
                                else:
                                    self.fromTimeElectricityUtc = str("%s001" % (int(time.mktime(
                                        datetime.datetime.combine(datetime.date.today(),
                                                                  datetime.time()).timetuple()))))
                                    self.globals['smappees'][devElectricity.id]['lastReadingElectricityUtc'] = float(
                                        float(self.fromTimeElectricityUtc) - 1.0)
                                    if "accumEnergyTotal" in devElectricity.states:
                                        kwh = 0.0
                                        kwhStr = "%0.3f kWh" % kwh
                                        self.smappeeInterfaceLogger.info(u"reset '%s' electricity total to 0.0" % devElectricity.name)
                                        kwhReformatted = float(str("%0.3f" % kwh))
                                        devElectricity.updateStateOnServer("accumEnergyTotal", kwhReformatted,
                                                                           uiValue=kwhStr)

                            if self.electricityNetId != 0:
                                devElectricityNet = indigo.devices[self.electricityNetId]

                                self.smappeeInterfaceLogger.debug(u"%s - lastReadingElectricityNetUtc[%s] =[%s]" % (smappeeCommand,
                                                                                                     type(self.globals[
                                                                                                              'smappees'][
                                                                                                              devElectricityNet.id][
                                                                                                              'lastReadingElectricityNetUtc']),
                                                                                                     self.globals[
                                                                                                         'smappees'][
                                                                                                         devElectricityNet.id][
                                                                                                         'lastReadingElectricityNetUtc']))
                                self.lastReadingElectricityNetDay = int(datetime.datetime.fromtimestamp(float(
                                    self.globals['smappees'][devElectricityNet.id][
                                        'lastReadingElectricityNetUtc'] / 1000)).strftime('%j'))

                                self.smappeeInterfaceLogger.debug(u"%s - lastReadingElectricityNetDay=[%s] vs currentTimeDay=[%s]" % (
                                    smappeeCommand, self.lastReadingElectricityNetDay, self.currentTimeDay))

                                if self.globals['smappees'][devElectricityNet.id][
                                        'lastReadingElectricityNetUtc'] > 0 and self.lastReadingElectricityNetDay == self.currentTimeDay and smappeeCommand != 'RESET_CONSUMPTION':
                                    self.fromTimeElectricityNetUtc = str(int(
                                        self.globals['smappees'][devElectricityNet.id]['lastReadingElectricityNetUtc']))
                                else:
                                    self.fromTimeElectricityNetUtc = str("%s001" % (int(time.mktime(
                                        datetime.datetime.combine(datetime.date.today(),
                                                                  datetime.time()).timetuple()))))
                                    self.globals['smappees'][devElectricityNet.id][
                                        'lastReadingElectricityNetUtc'] = float(
                                        float(self.fromTimeElectricityNetUtc) - 1.0)
                                    if "accumEnergyTotal" in devElectricityNet.states:
                                        kwh = 0.0
                                        kwhStr = str("%0.3f kWh" % kwh)
                                        self.smappeeInterfaceLogger.info(
                                                u"reset '%s' electricity net total to 0.0" % devElectricityNet.name)
                                        kwhReformatted = float(str("%0.3f" % kwh))
                                        devElectricityNet.updateStateOnServer("accumEnergyTotal", kwhReformatted,
                                                                              uiValue=kwhStr)

                            if self.electricitySavedId != 0:
                                devElectricitySaved = indigo.devices[self.electricitySavedId]

                                self.smappeeInterfaceLogger.debug(u"%s - lastReadingElectricitySavedUtc[%s] =[%s]" % (smappeeCommand,
                                                                                                       type(
                                                                                                           self.globals[
                                                                                                               'smappees'][
                                                                                                               devElectricitySaved.id][
                                                                                                               'lastReadingElectricitySavedUtc']),
                                                                                                       self.globals[
                                                                                                           'smappees'][
                                                                                                           devElectricitySaved.id][
                                                                                                           'lastReadingElectricitySavedUtc']))
                                self.lastReadingElectricitySavedDay = int(datetime.datetime.fromtimestamp(float(
                                    self.globals['smappees'][devElectricitySaved.id][
                                        'lastReadingElectricitySavedUtc'] / 1000)).strftime('%j'))

                                self.smappeeInterfaceLogger.debug(
                                        u"%s - lastReadingElectricitySavedDay=[%s] vs currentTimeDay=[%s]" % (
                                            smappeeCommand, self.lastReadingElectricitySavedDay, self.currentTimeDay))

                                if self.globals['smappees'][devElectricitySaved.id][
                                        'lastReadingElectricitySavedUtc'] > 0 and self.lastReadingElectricitySavedDay == self.currentTimeDay and smappeeCommand != 'RESET_CONSUMPTION':
                                    self.fromTimeElectricitySavedUtc = str(int(
                                        self.globals['smappees'][devElectricitySaved.id][
                                            'lastReadingElectricitySavedUtc']))
                                else:
                                    self.fromTimeElectricitySavedUtc = str("%s001" % (int(time.mktime(
                                        datetime.datetime.combine(datetime.date.today(),
                                                                  datetime.time()).timetuple()))))
                                    self.globals['smappees'][devElectricitySaved.id][
                                        'lastReadingElectricitySavedUtc'] = float(
                                        float(self.fromTimeElectricitySavedUtc) - 1.0)
                                    if "accumEnergyTotal" in devElectricitySaved.states:
                                        kwh = 0.0
                                        kwhStr = str("%0.3f kWh" % kwh)
                                        self.smappeeInterfaceLogger.info(
                                                u"reset '%s' electricity Saved total to 0.0" % devElectricitySaved.name)
                                        kwhReformatted = float(str("%0.3f" % kwh))
                                        devElectricitySaved.updateStateOnServer("accumEnergyTotal", kwhReformatted,
                                                                                uiValue=kwhStr)

                            if self.solarId != 0:
                                devSolar = indigo.devices[self.solarId]

                                self.smappeeInterfaceLogger.debug(u"%s - lastReadingSolarUtc[%s] =[%s]" % (
                                    smappeeCommand, type(self.globals['smappees'][devSolar.id]['lastReadingSolarUtc']),
                                    self.globals['smappees'][devSolar.id]['lastReadingSolarUtc']))
                                self.lastReadingSolarDay = int(datetime.datetime.fromtimestamp(float(
                                    self.globals['smappees'][devSolar.id]['lastReadingSolarUtc'] / 1000)).strftime(
                                    '%j'))

                                self.smappeeInterfaceLogger.debug(u"%s - lastReadingSolarDay=[%s] vs currentTimeDay=[%s]" % (
                                    smappeeCommand, self.lastReadingSolarDay, self.currentTimeDay))

                                if self.globals['smappees'][devSolar.id][
                                        'lastReadingSolarUtc'] > 0 and self.lastReadingSolarDay == self.currentTimeDay and smappeeCommand != 'RESET_CONSUMPTION':
                                    self.fromTimeSolarUtc = str(
                                        int(self.globals['smappees'][devSolar.id]['lastReadingSolarUtc']))
                                else:
                                    self.fromTimeSolarUtc = str("%s001" % (int(time.mktime(
                                        datetime.datetime.combine(datetime.date.today(),
                                                                  datetime.time()).timetuple()))))
                                    self.globals['smappees'][devSolar.id]['lastReadingSolarUtc'] = float(
                                        float(self.fromTimeSolarUtc) - 1.0)
                                    if "accumEnergyTotal" in devSolar.states:
                                        kwh = 0.0
                                        kwhStr = str("%0.3f kWh" % kwh)
                                        self.smappeeInterfaceLogger.info(u"reset '%s' solar generation total to 0.0" % devSolar.name)
                                        kwhReformatted = float(str("%0.3f" % kwh))
                                        devSolar.updateStateOnServer("accumEnergyTotal", kwhReformatted, uiValue=kwhStr)

                            if self.solarUsedId != 0:
                                devSolarUsed = indigo.devices[self.solarUsedId]

                                self.smappeeInterfaceLogger.debug(u"%s - lastReadingSolarUsedUtc[%s] =[%s]" % (smappeeCommand, type(
                                    self.globals['smappees'][devSolarUsed.id]['lastReadingSolarUsedUtc']), self.globals[
                                                                                                    'smappees'][
                                                                                                    devSolarUsed.id][
                                                                                                    'lastReadingSolarUsedUtc']))
                                self.lastReadingSolarUsedDay = int(datetime.datetime.fromtimestamp(float(
                                    self.globals['smappees'][devSolarUsed.id][
                                        'lastReadingSolarUsedUtc'] / 1000)).strftime('%j'))

                                self.smappeeInterfaceLogger.debug(u"%s - lastReadingSolarUsedDay=[%s] vs currentTimeDay=[%s]" % (
                                    smappeeCommand, self.lastReadingSolarUsedDay, self.currentTimeDay))

                                if self.globals['smappees'][devSolarUsed.id][
                                        'lastReadingSolarUsedUtc'] > 0 and self.lastReadingSolarUsedDay == self.currentTimeDay and smappeeCommand != 'RESET_CONSUMPTION':
                                    self.fromTimeSolarUsedUtc = str(
                                        int(self.globals['smappees'][devSolarUsed.id]['lastReadingSolarUsedUtc']))
                                else:
                                    self.fromTimeSolarUsedUtc = str("%s001" % (int(time.mktime(
                                        datetime.datetime.combine(datetime.date.today(),
                                                                  datetime.time()).timetuple()))))
                                    self.globals['smappees'][devSolarUsed.id]['lastReadingSolarUsedUtc'] = float(
                                        float(self.fromTimeSolarUtc) - 1.0)
                                    if "accumEnergyTotal" in devSolarUsed.states:
                                        kwh = 0.0
                                        kwhStr = str("%0.3f kWh" % kwh)
                                        self.smappeeInterfaceLogger.info(u"reset '%s' solar used total to 0.0" % devSolarUsed.name)
                                        kwhReformatted = float(str("%0.3f" % kwh))
                                        devSolarUsed.updateStateOnServer("accumEnergyTotal", kwhReformatted,
                                                                         uiValue=kwhStr)

                            if self.solarExportedId != 0:
                                devSolarExported = indigo.devices[self.solarExportedId]

                                self.smappeeInterfaceLogger.debug(u"%s - lastReadingSolarExportedUtc[%s] =[%s]" % (smappeeCommand,
                                                                                                    type(self.globals[
                                                                                                             'smappees'][
                                                                                                             devSolarExported.id][
                                                                                                             'lastReadingSolarExportedUtc']),
                                                                                                    self.globals[
                                                                                                        'smappees'][
                                                                                                        devSolarExported.id][
                                                                                                        'lastReadingSolarExportedUtc']))
                                self.lastReadingSolarExportedDay = int(datetime.datetime.fromtimestamp(float(
                                    self.globals['smappees'][devSolarExported.id][
                                        'lastReadingSolarExportedUtc'] / 1000)).strftime('%j'))

                                self.smappeeInterfaceLogger.debug(u"%s - lastReadingSolarExportedDay=[%s] vs currentTimeDay=[%s]" % (
                                    smappeeCommand, self.lastReadingSolarExportedDay, self.currentTimeDay))

                                if self.globals['smappees'][devSolarExported.id][
                                        'lastReadingSolarExportedUtc'] > 0 and self.lastReadingSolarExportedDay == self.currentTimeDay and smappeeCommand != 'RESET_CONSUMPTION':
                                    self.fromTimeSolarExportedUtc = str(int(
                                        self.globals['smappees'][devSolarExported.id]['lastReadingSolarExportedUtc']))
                                else:
                                    self.fromTimeSolarExportedUtc = str("%s001" % (int(time.mktime(
                                        datetime.datetime.combine(datetime.date.today(),
                                                                  datetime.time()).timetuple()))))
                                    self.globals['smappees'][devSolarExported.id][
                                        'lastReadingSolarExportedUtc'] = float(float(self.fromTimeSolarUtc) - 1.0)
                                    if "accumEnergyTotal" in devSolarExported.states:
                                        kwh = 0.0
                                        kwhStr = str("%0.3f kWh" % kwh)
                                        self.smappeeInterfaceLogger.info(u"reset '%s' solar exported total to 0.0" % devSolarExported.name)
                                        kwhReformatted = float(str("%0.3f" % kwh))
                                        devSolarExported.updateStateOnServer("accumEnergyTotal", kwhReformatted,
                                                                             uiValue=kwhStr)

                            self.fromTimeUtc = 0
                            if self.electricityId != 0:
                                self.fromTimeUtc = self.fromTimeElectricityUtc
                                if self.solarId != 0:
                                    if self.fromTimeSolarUtc < self.fromTimeElectricityUtc:
                                        self.fromTimeUtc = self.fromTimeSolarUtc
                            else:
                                if self.solarId != 0:
                                    self.fromTimeUtc = self.fromTimeSolarUtc

                            self.globals[
                                'consumptionDataReceived'] = True  # Set to True once the self.fromTimeUtc has been determined so getting event data doesn't fail

                            # #TIME# self.toTimeUtc = str(
                            # #TIME#     "%s000" % (int(self.currentTimeUtc + float(3600))))  # Add +1 hour to current time

                            self.smappeeInterfaceLogger.debug(
                                    u"%s - From=[%s], To=[%s]" % (smappeeCommand, self.fromTimeUtc, self.toTimeUtc))

                            self.aggregationType = '1'  # 1 = 5 min values (only available for the last 14 days), 2 = hourly values, 3 = daily values, 4 = monthly values, 5 = yearly values

                            process = subprocess.Popen(
                                ['curl', '-H', 'Authorization: Bearer ' + self.globals['config']['accessToken'],
                                 'https://app1pub.smappee.net/dev/v1/servicelocation/' + self.serviceLocationId + '/consumption?aggregation=' + self.aggregationType + '&from=' + self.fromTimeUtc + '&to=' + self.toTimeUtc,
                                 ''], stdout=subprocess.PIPE)

                            response = ""
                            for line in process.stdout:
                                # self.smappeeInterfaceLogger.debug(u"Response to '%s' = %s" % (smappeeCommand, line))
                                response = response + line.strip()

                            self.smappeeInterfaceLogger.debug(u"MERGED Response to '%s' = %s" % (smappeeCommand, response))

                            self.globals['queues']['process'].put([smappeeCommand, self.serviceLocationId, response])

                    elif smappeeCommand == 'GET_SENSOR_CONSUMPTION' or smappeeCommand == 'RESET_SENSOR_CONSUMPTION':

                        self.serviceLocationId = commandToSend[1]

                        self.sensorFromTimeUtc = 0

                        # #TIME# self.currentTimeDay = int(datetime.datetime.fromtimestamp(self.toTimeUtc).strftime('%j'))

                        for key, value in self.globals['smappeeServiceLocationIdToDevId'][self.serviceLocationId][
                                'sensorIds'].iteritems():
                            # indigo.server.log(u'GET_SENSOR_CONSUMPTION - sensorIds = [Type = %s] %s' % (type(self.globals['smappeeServiceLocationIdToDevId'][self.serviceLocationId]['sensorIds']), self.globals['smappeeServiceLocationIdToDevId'][self.serviceLocationId]['sensorIds']))
                            self.smappeeInterfaceLogger.debug(u'GET_SENSOR_CONSUMPTION = [Key = %s] %s' % (key, value))
                            self.smappeeInterfaceLogger.debug(u'GET_SENSOR_CONSUMPTION = [DevId = %s]' % (str(value['devId'])))

                            if value['devId'] == 0:
                                self.smappeeInterfaceLogger.debug(
                                        u"%s - GET_SENSOR_CONSUMPTION - No Indigo Sensor Device defined for Smappee Sensor %s" % (
                                            smappeeCommand, key))
                                continue

                            # self.smappeeInterfaceLogger.debug(u"%s - GET_SENSOR_CONSUMPTION - smappeeServiceLocationIdToDevId = [%s]" % (smappeeCommand, self.globals['smappeeServiceLocationIdToDevId']))

                            sensorId = value['devId']

                            devSensor = indigo.devices[sensorId]

                            self.smappeeInterfaceLogger.debug(u"GET_SENSOR_CONSUMPTION - %s - lastReadingSensorUtc[%s] =[%s]" % (
                                smappeeCommand, type(self.globals['smappees'][devSensor.id]['lastReadingSensorUtc']),
                                self.globals['smappees'][devSensor.id]['lastReadingSensorUtc']))
                            self.lastReadingSensorDay = int(datetime.datetime.fromtimestamp(
                                float(self.globals['smappees'][devSensor.id]['lastReadingSensorUtc'] / 1000)).strftime(
                                '%j'))

                            self.smappeeInterfaceLogger.debug(
                                    u"GET_SENSOR_CONSUMPTION - %s - lastReadingSensorDay=[%s] vs currentTimeDay=[%s]" % (
                                        smappeeCommand, self.lastReadingSensorDay, self.currentTimeDay))

                            if self.globals['smappees'][devSensor.id][
                                    'lastReadingSensorUtc'] > 0 and self.lastReadingSensorDay == self.currentTimeDay and smappeeCommand != 'RESETSENSORCONSUMPTION':
                                self.fromTimeSensorUtc = str(
                                    int(self.globals['smappees'][devSensor.id]['lastReadingSensorUtc']))
                            else:
                                self.fromTimeSensorUtc = str("%s001" % (int(time.mktime(
                                    datetime.datetime.combine(datetime.date.today(), datetime.time()).timetuple()))))
                                self.globals['smappees'][devSensor.id]['lastReadingSensorUtc'] = float(
                                    float(self.fromTimeSensorUtc) - 1.0)
                                if "accumEnergyTotal" in devSensor.states:
                                    kwh = 0.0
                                    kwhStr = "%0.3f kWh" % kwh
                                    self.smappeeInterfaceLogger.info(u"reset '%s' sensor total to 0.0" % devSensor.name)
                                    kwhReformatted = float(str("%0.3f" % kwh))
                                    devSensor.updateStateOnServer("accumEnergyTotal", kwhReformatted, uiValue=kwhStr)

                            self.sensorFromTimeUtc = self.fromTimeSensorUtc

                            self.sensorToTimeUtc = str(
                                "%s000" % (int(self.currentTimeUtc + float(3600))))  # Add +1 hour to current time

                            self.smappeeInterfaceLogger.debug(u"GET_SENSOR_CONSUMPTION [BC] - %s - SENSOR From=[%s], To=[%s]" % (
                                smappeeCommand, self.sensorFromTimeUtc, self.sensorToTimeUtc))

                            self.aggregationType = '1'  # 1 = 5 min values (only available for the last 14 days), 2 = hourly values, 3 = daily values, 4 = monthly values, 5 = yearly values

                            self.sensorAddress = str(int(str(devSensor.address)[2:4]))
                            self.smappeeInterfaceLogger.debug(u"Sensor Address = '%s'" % self.sensorAddress)

                            process = subprocess.Popen(
                                ['curl', '-H', 'Authorization: Bearer ' + self.globals['config']['accessToken'],
                                 'https://app1pub.smappee.net/dev/v1/servicelocation/' + self.serviceLocationId + '/sensor/' + self.sensorAddress + '/consumption?aggregation=' + self.aggregationType + '&from=' + self.sensorFromTimeUtc + '&to=' + self.sensorToTimeUtc,
                                 ''], stdout=subprocess.PIPE)

                            response = ""
                            for line in process.stdout:
                                # self.smappeeInterfaceLogger.debug(u"Response to '%s' = %s" % (smappeeCommand, line))
                                response = response + line.strip()

                            self.smappeeInterfaceLogger.debug(u"GET_SENSOR_CONSUMPTION [AC] - MERGED Sensor Response to '%s' = %s" % (
                                smappeeCommand, response))

                            # testTimeStamp1 = '1461488100000'  # TEST DATA
                            # testTimeStamp2 = '1461491400000'  # TEST DATA
                            # testTimeStamp3 = '1461494700000'  # TEST DATA

                            # self.globals['testdata']['temperature'].rotate(-1)
                            # temperature = str(self.globals['testdata']['temperature'][0])
                            # self.globals['testdata']['humidity'].rotate(-1)
                            # humidity = str(self.globals['testdata']['humidity'][0])
                            # self.globals['testdata']['batteryLevel'].rotate(-1)
                            # batteryLevel = str(self.globals['testdata']['batteryLevel'][0])
                            # self.globals['testdata']['value1'].rotate(-1)
                            # value1 = str(self.globals['testdata']['value1'][0])
                            # self.globals['testdata']['value2'].rotate(-1)
                            # value2 = str(self.globals['testdata']['value2'][0])

                            # utc = int(time.time())
                            # testTimeStamp1 = str(int(utc-120)*1000)
                            # testTimeStamp2 = str(int(utc-60)*1000)
                            # testTimeStamp3 = str(int(utc)*1000)

                            # ' + temperature + '
                            # ' + humidity + '
                            # ' + batteryLevel + '
                            # ' + value1 + '
                            # ' + value2 + '

                            # response = response[:-3] + '[{"timestamp": ' + testTimeStamp1 + ',"value1": 11.0,"value2": 2.0,"temperature": 226.0,"humidity": 41.0,"battery": 100.0},{"timestamp": ' + testTimeStamp2 + ',"value1": 9.0,"value2": 3.0,"temperature": 220.0,"humidity": 39.0,"battery": 100.0},{"timestamp": ' + testTimeStamp3 + ',"value1": 10.0,"value2": 1.0,"temperature": 202.0,"humidity": 39.0,"battery": 100.0}], "error": "This is a sample error from Smappee","UNKNOWN KEY TEST" : "THIS IS AN ERROR VALUE"}'
                            # response = response[:-3] + '[{"timestamp": ' + testTimeStamp1 + ',"value1": ' + value1 + ',"value2": ' + value2 + ',"temperature": ' + temperature + ',"humidity": ' + humidity + ',"battery": ' + batteryLevel + '},{"timestamp": ' + testTimeStamp2 + ',"value1": ' + value1 + ',"value2": ' + value2 + ',"temperature": ' + temperature + ',"humidity": ' + humidity + ',"battery": ' + batteryLevel + '},{"timestamp": ' + testTimeStamp3 + ',"value1": ' + value1 + ',"value2": ' + value2 + ',"temperature": ' + temperature + ',"humidity": ' + humidity + ',"battery": ' + batteryLevel + '}]}'

                            # self.smappeeInterfaceLogger.debug(u"GET_SENSOR_CONSUMPTION [AC-FIXED] - MERGED Sensor Response to '%s' = %s" % (smappeeCommand, response))

                            self.globals['queues']['process'].put([smappeeCommand, self.serviceLocationId, response])

                    elif smappeeCommand == 'GET_EVENTS' and self.globals['consumptionDataReceived']:
                        self.serviceLocationId = commandToSend[1]

                        self.smappeeInterfaceLogger.debug(u"%s - smappeeServiceLocationIdToDevId = [%s]" % (
                            smappeeCommand, self.globals['smappeeServiceLocationIdToDevId']))
                        if self.globals['smappeeServiceLocationIdToDevId'][self.serviceLocationId][
                                'electricityId'] != 0:
                            dev = indigo.devices[
                                self.globals['smappeeServiceLocationIdToDevId'][self.serviceLocationId][
                                    'electricityId']]

                            # #TIME# self.toTimeUtc = time.mktime(indigo.server.getTime().timetuple())
                            # #TIME# self.smappeeInterfaceLogger.debug(u"%s - self.toTimeUtc[%s] =[%s]" % (
                            # #TIME#     smappeeCommand, type(self.toTimeUtc), self.toTimeUtc))

                            self.smappeeInterfaceLogger.debug(u"%s - lastReadingElectricityUtc[%s] =[%s]" % (
                                smappeeCommand, type(self.globals['smappees'][dev.id]['lastReadingElectricityUtc']),
                                self.globals['smappees'][dev.id]['lastReadingElectricityUtc']))
                            self.lastReadingDay = int(datetime.datetime.fromtimestamp(
                                float(self.globals['smappees'][dev.id]['lastReadingElectricityUtc'] / 1000)).strftime(
                                '%j'))

                            # #TIME# self.currentTimeDay = int(datetime.datetime.fromtimestamp(self.toTimeUtc).strftime('%j'))
                            # #TIME# self.smappeeInterfaceLogger.debug(u"%s - lastReadingDay=[%s] vs currentTimeDay=[%s]" % (
                            # #TIME#     smappeeCommand, self.lastReadingDay, self.currentTimeDay))

                            # #TIME# self.toTimeUtc = str("%s000" % (int(self.toTimeUtc + float(3600))))

                            self.smappeeInterfaceLogger.debug(
                                    u"%s - From=[%s], To=[%s]" % (smappeeCommand, self.fromTimeUtc, self.toTimeUtc))

                            self.appliances = 'applianceId=1&applianceId=2&applianceId=15&applianceId=3&applianceId=34'
                            self.maxNumber = '20'
                            process = subprocess.Popen(
                                ['curl', '-H', 'Authorization: Bearer ' + self.globals['config']['accessToken'],
                                 'https://app1pub.smappee.net/dev/v1/servicelocation/' + self.serviceLocationId + '/events?' + self.appliances + '&maxNumber=' + self.maxNumber + '&from=' + self.fromTimeUtc + '&to=' + self.toTimeUtc,
                                 ''], stdout=subprocess.PIPE)

                            response = ""
                            for line in process.stdout:
                                self.smappeeInterfaceLogger.debug(u"Response to '%s' = %s" % (smappeeCommand, line))
                                response = response + line.strip()

                            self.smappeeInterfaceLogger.debug(u"MERGED Response to '%s' = %s" % (smappeeCommand, response))

                            self.globals['queues']['process'].put([smappeeCommand, self.serviceLocationId, response])
                            
                    elif smappeeCommand == 'INITIALISE':
                        process = subprocess.Popen(['curl', '-XPOST', '-d', 'client_id=' + self.globals['config'][
                            'clientId'] + '&client_secret=' + self.globals['config'][
                                                        'secret'] + '&grant_type=password&username=' +
                                                    self.globals['config']['userName'] + '&password=' +
                                                    self.globals['config']['password'],
                                                    'https://app1pub.smappee.net/dev/v1/oauth2/token', '-d', ''],
                                                   stdout=subprocess.PIPE)

                        response = ""
                        for line in process.stdout:
                            # self.smappeeInterfaceLogger.debug(u"Line Response to '%s' = %s" % (smappeeCommand, line))
                            response = response + line.strip()

                        self.smappeeInterfaceLogger.debug(u"MERGED Response to '%s' = %s" % (smappeeCommand, response))

                        self.globals['queues']['process'].put(['INITIALISE', "", response])

                        continue  # Continue while loop i.e. skip refresh authentication token check at end of this while loop as we have only just authenticated

                    elif smappeeCommand == 'GET_SERVICE_LOCATIONS':
                        process = subprocess.Popen(
                            ['curl', '-H', 'Authorization: Bearer ' + self.globals['config']['accessToken'],
                             'https://app1pub.smappee.net/dev/v1/servicelocation', ''], stdout=subprocess.PIPE)

                        response = ""
                        for line in process.stdout:
                            # self.smappeeInterfaceLogger.debug(u"Response to '%s' = %s" % (smappeeCommand, line))
                            response = response + line.strip()

                        self.smappeeInterfaceLogger.debug(u"MERGED Response to '%s' = %s" % (smappeeCommand, response))

                        self.globals['queues']['process'].put(['GET_SERVICE_LOCATIONS', "", response])

                    elif smappeeCommand == 'GET_SERVICE_LOCATION_INFO':
                        self.serviceLocationId = commandToSend[1]
                        process = subprocess.Popen(
                            ['curl', '-H', 'Authorization: Bearer ' + self.globals['config']['accessToken'],
                             'https://app1pub.smappee.net/dev/v1/servicelocation/' + self.serviceLocationId + '/info',
                             ''], stdout=subprocess.PIPE)

                        response = ""
                        for line in process.stdout:
                            # self.smappeeInterfaceLogger.debug(u"Response to '%s' = %s" % (smappeeCommand, line))
                            response = response + line.strip()

                        # TESTING GAS / WATER [START]
                        # response = response[:-1]
                        # response = response + str(', "sensors": [{"id": 4, "name": "Sensor 4"}, {"id": 5, "name": "Sensor 5"}]}').strip()
                        # TESTING GAS / WATER [END]

                        self.smappeeInterfaceLogger.debug(u"MERGED Response to '%s' = %s" % (smappeeCommand, response))

                        self.globals['queues']['process'].put(['GET_SERVICE_LOCATION_INFO', self.serviceLocationId, response])

                    elif smappeeCommand == 'ON' or smappeeCommand == 'OFF':

                        # Format: 'ON|OFF', ServiceLocationId, ActuatorId 

                        self.serviceLocationId = commandToSend[1]
                        self.actuatorId = commandToSend[2]

                        process = subprocess.Popen(['curl', '-H', 'Content-Type: application/json', '-H',
                                                    'Authorization: Bearer ' + self.globals['config']['accessToken'],
                                                    '-d', '{}',
                                                    'https://app1pub.smappee.net/dev/v1/servicelocation/' + self.serviceLocationId + '/actuator/' + self.actuatorId + '/' + str(
                                                        smappeeCommand).lower(), ''], stdout=subprocess.PIPE)

                        self.smappeeInterfaceLogger.debug(u"DEBUG PROCESS [On/OFF]: [%s]:[%s]" % (type(commandToSend), commandToSend))

                        for line in process.stdout:
                            # self.smappeeInterfaceLogger.debug(u"Response to '%s' = %s" % (smappeeCommand, line))
                            response = response + line.strip()

                        self.smappeeInterfaceLogger.debug(u"MERGED Response to '%s' = %s" % (smappeeCommand, response))

                        # No need to handle reponse

                    # Finally check if authentication token needs refreshing (but only if thread NOT ending)
                    if keepThreadActive:
                        # #TIME# self.currentTimeUtc = time.mktime(indigo.server.getTime().timetuple())
                        if self.currentTimeUtc > self.globals['config']['tokenExpiresDateTimeUtc']:
                            self.smappeeInterfaceLogger.debug(u"Refresh Token Request = %s" % (self.globals['config']['refreshToken']))
                            self.smappeeInterfaceLogger.debug(u"Refresh Token, currentUTC[%s] = %s, expiresUTC[%s] = %s" % (
                                type(self.currentTimeUtc), self.currentTimeUtc,
                                type(self.globals['config']['tokenExpiresDateTimeUtc']),
                                self.globals['config']['tokenExpiresDateTimeUtc']))

                            process = subprocess.Popen(
                                ['curl', '-XPOST', '-H', 'application/x-www-form-urlencoded;charset=UTF-8', '-d',
                                 'grant_type=refresh_token&refresh_token=' + self.globals['config'][
                                     'refreshToken'] + '&client_id=' + self.globals['config'][
                                     'clientId'] + '&client_secret=' + self.globals['config']['secret'],
                                 'https://app1pub.smappee.net/dev/v1/oauth2/token', '-d', ''], stdout=subprocess.PIPE)

                            response = ""
                            for line in process.stdout:
                                # self.smappeeInterfaceLogger.debug(u"Line Response to Refresh Token = %s" % (line))
                                response = response + line.strip()

                            self.smappeeInterfaceLogger.debug(u"MERGED Response to Refresh Token = %s" % response)

                            self.globals['queues']['process'].put(['REFRESH_TOKEN', "", response])

                except Queue.Empty:
                    pass
                except StandardError, e:
                    self.smappeeInterfaceLogger.error(u"StandardError detected communicating with Smappee. Line '%s' has error='%s'" % (
                        sys.exc_traceback.tb_lineno, e))

            if not keepThreadActive:
                self.smappeeInterfaceLogger.debug(u"Command Thread ending.")

        except StandardError, e:
            self.smappeeInterfaceLogger.error(u"StandardError detected in Smappee Command Thread. Line '%s' has error='%s'" % (
                sys.exc_traceback.tb_lineno, e))

        self.smappeeInterfaceLogger.debug(u"Smappee Command Thread ended.")
