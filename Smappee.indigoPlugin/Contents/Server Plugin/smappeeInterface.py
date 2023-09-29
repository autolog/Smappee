#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# Smappee - smappeeInterface © Autolog 2018 - 2023
#

# noinspection PyUnresolvedReferences
# ============================== Native Imports ===============================
import datetime
import json
import logging
import queue
import requests
import subprocess
import sys
import threading
import time
import traceback

# ============================== Custom Imports ===============================
try:
    import indigo  # noqa
except ImportError:
    pass

# ============================== Plugin Imports ===============================
from constants import *


# noinspection PyUnresolvedReferences,PyPep8Naming,SpellCheckingInspection
class ThreadSmappeeInterface(threading.Thread):

    # This class manages the interface to Smappee

    def __init__(self, pluginGlobals, event):

        threading.Thread.__init__(self)

        self.globals = pluginGlobals

        self.smappeeInterfaceLogger = logging.getLogger("Plugin.smappeeInterface")
        self.smappeeInterfaceLogger.debug("Debugging Smappee Interface Thread")

        self.previous_status_message = ""

        self.threadStop = event

    def exception_handler(self, exception_error_message, log_failing_statement):
        filename, line_number, method, statement = traceback.extract_tb(sys.exc_info()[2])[-1]
        module = filename.split('/')
        log_message = f"'{exception_error_message}' in module '{module[-1]}', method '{method}'"
        if log_failing_statement:
            log_message = log_message + f"\n   Failing statement [line {line_number}]: '{statement}'"
        else:
            log_message = log_message + f" at line {line_number}"
        self.smappeeInterfaceLogger.error(log_message)

    # def convertUnicode(self, unicodeInput):
    #     if isinstance(unicodeInput, dict):
    #         return dict(
    #             [(self.convertUnicode(key), self.convertUnicode(value)) for key, value in unicodeInput.items()])
    #     elif isinstance(unicodeInput, list):
    #         return [self.convertUnicode(element) for element in unicodeInput]
    #     elif isinstance(unicodeInput, unicode):
    #         return unicodeInput.encode("utf-8")
    #     else:
    #         return unicodeInput

    def run(self):
        try:
            keepThreadActive = True
            while keepThreadActive:

                try:
                    commandToSend = self.globals[QUEUES][SEND_TO_SMAPPEE].get(True, 5)
                    self.smappeeInterfaceLogger.debug(f"Command to send to Smappee [Type={type(commandToSend)}]: {commandToSend}")

                    smappeeCommand = commandToSend[0]
                    service_location_id = commandToSend[1] if len(commandToSend) > 1 else None
                    smappeeParmThree = commandToSend[2] if len(commandToSend) > 2 else None  # TODO Is this only Actuator ID = probably?

                    if smappeeCommand == END_THREAD:
                        keepThreadActive = False
                        continue

                    self.currentTimeUtc = time.mktime(indigo.server.getTime().timetuple())
                    self.currentTimeDay = int(datetime.datetime.fromtimestamp(self.currentTimeUtc).strftime("%j"))
                    self.smappeeInterfaceLogger.debug(f"{smappeeCommand} - self.currentTimeUtc[{type(self.currentTimeUtc)}]=[{self.currentTimeUtc}], DAY=[{self.currentTimeDay}]")

                    current_time_plus_one_hour = int(self.currentTimeUtc + float(3600))  # Add +1 hour to current time
                    self.toTimeUtc = f"{current_time_plus_one_hour}000"
                    self.smappeeInterfaceLogger.debug(f"{smappeeCommand} - self.toTimeUtc=[{self.toTimeUtc}]")

                    if smappeeCommand == COMMAND_GET_CONSUMPTION or smappeeCommand == COMMAND_RESET_CONSUMPTION:
                        self.process_get_reset_consumption(smappeeCommand, service_location_id)
                    elif smappeeCommand == COMMAND_GET_SENSOR_CONSUMPTION or smappeeCommand == COMMAND_RESET_SENSOR_CONSUMPTION:
                        self.process_get_reset_sensor_consumption(smappeeCommand, service_location_id)
                    elif smappeeCommand == COMMAND_GET_EVENTS and self.globals[CONSUMPTION_DATA_RECEIVED]:  # Only if consumption data already present
                        self.process_get_events(smappeeCommand, service_location_id)
                    elif smappeeCommand == COMMAND_INITIALISE:
                        self.process_initialise()
                        continue  # Continue while loop i.e. skip refresh authentication token check at end of this while loop as we have only just authenticated
                    elif smappeeCommand == COMMAND_GET_SERVICE_LOCATIONS:
                        self.process_get_service_locations()
                    elif smappeeCommand == COMMAND_GET_SERVICE_LOCATION_INFO:
                        self.process_get_service_location_info(smappeeCommand, service_location_id)
                    elif smappeeCommand == COMMAND_ON or smappeeCommand == COMMAND_OFF:
                        self.process_on_off(smappeeCommand, service_location_id, smappeeParmThree)

                    # Finally check if authentication token needs refreshing (but only if thread NOT ending)
                    if keepThreadActive:
                        self.process_check_token_refresh()

                except queue.Empty:
                    pass
                except Exception as exception_error:
                    self.exception_handler(exception_error, True)  # Log error and display failing statement

            if not keepThreadActive:
                self.smappeeInterfaceLogger.debug(f"Command Thread ending.")

        except Exception as exception_error:
            self.exception_handler(exception_error, True)  # Log error and display failing statement

        self.smappeeInterfaceLogger.debug(f"Smappee Command Thread ended.")

    def process_get_reset_consumption(self, smappeeCommand, service_location_id):
        try:
            self.serviceLocationId = service_location_id
            self.electricityId = int(self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.serviceLocationId][ELECTRICITY_ID])
            self.electricityNetId = int(self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.serviceLocationId][ELECTRICITY_NET_ID])
            self.electricitySavedId = int(self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.serviceLocationId][ELECTRICITY_SAVED_ID])
            self.solarId = int(self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.serviceLocationId][SOLAR_ID])
            self.solarUsedId = int(self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.serviceLocationId][SOLAR_USED_ID])
            self.solarExportedId = int(self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.serviceLocationId][SOLAR_EXPORTED_ID])

            if self.electricityId == 0 and self.solarId == 0:
                pass
                self.smappeeInterfaceLogger.debug(f"{smappeeCommand} - Smappee Base Devices [ELECTRICITY and SOLAR PV] not defined")
            else:
                self.smappeeInterfaceLogger.debug(f"{smappeeCommand} - GET_CONSUMPTION - smappeeServiceLocationIdToDevId = [{self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID]}]")

                # #TIME# self.currentTimeUtc = time.mktime(indigo.server.getTime().timetuple())
                # #TIME# self.currentTimeDay = int(datetime.datetime.fromtimestamp(self.currentTimeUtc).strftime("%j"))
                self.smappeeInterfaceLogger.debug(f"{smappeeCommand} - self.currentTimeUtc[{type(self.currentTimeUtc)}]=[{self.currentTimeUtc}], DAY=[{self.currentTimeDay}]")

                if self.electricityId != 0:
                    devElectricity = indigo.devices[self.electricityId]

                    self.smappeeInterfaceLogger.debug(f"{smappeeCommand}"
                                                      f" - lastReadingElectricityUtc[{type(self.globals[SMAPPEES][devElectricity.id][LAST_READING_ELECTRICITY_UTC])}]"
                                                      f" = [{self.globals[SMAPPEES][devElectricity.id][LAST_READING_ELECTRICITY_UTC]}]")
                    self.lastReadingElectricityDay = int(datetime.datetime.fromtimestamp(float(self.globals[SMAPPEES][devElectricity.id][LAST_READING_ELECTRICITY_UTC] / 1000)).strftime("%j"))

                    self.smappeeInterfaceLogger.debug(f"{smappeeCommand} - lastReadingElectricityDay=[{self.lastReadingElectricityDay}] vs currentTimeDay=[{self.currentTimeDay}]")

                    if (self.globals[SMAPPEES][devElectricity.id][LAST_READING_ELECTRICITY_UTC] > 0 and
                            self.lastReadingElectricityDay == self.currentTimeDay and smappeeCommand != COMMAND_RESET_CONSUMPTION):
                        self.fromTimeElectricityUtc = str(int(self.globals[SMAPPEES][devElectricity.id][LAST_READING_ELECTRICITY_UTC]))
                    else:
                        from_time_electricity_utc = int(time.mktime(datetime.datetime.combine(datetime.date.today(), datetime.time()).timetuple()))
                        self.fromTimeElectricityUtc = f"{from_time_electricity_utc}001"
                        self.globals[SMAPPEES][devElectricity.id][LAST_READING_ELECTRICITY_UTC] = float(
                            float(self.fromTimeElectricityUtc) - 1.0)
                        if "accumEnergyTotal" in devElectricity.states:
                            kwh = 0.0
                            kwhStr = f"{kwh:0.3f} kWh"
                            self.smappeeInterfaceLogger.info(f"reset '{devElectricity.name}' electricity total to 0.0")
                            kwhReformatted = float(f"{kwh:0.3f}")
                            devElectricity.updateStateOnServer("accumEnergyTotal", kwhReformatted, uiValue=kwhStr)

                if self.electricityNetId != 0:
                    devElectricityNet = indigo.devices[self.electricityNetId]

                    self.smappeeInterfaceLogger.debug(f"{smappeeCommand}"
                                                      f" - lastReadingElectricityNetUtc[{type(self.globals[SMAPPEES][devElectricityNet.id][LAST_READING_ELECTRICITY_NET_UTC])}]"
                                                      f" = [{ self.globals[SMAPPEES][devElectricityNet.id][LAST_READING_ELECTRICITY_NET_UTC]}]")
                    self.lastReadingElectricityNetDay = int(datetime.datetime.fromtimestamp(float(
                        self.globals[SMAPPEES][devElectricityNet.id][LAST_READING_ELECTRICITY_NET_UTC] / 1000)).strftime("%j"))

                    self.smappeeInterfaceLogger.debug(f"{smappeeCommand} - lastReadingElectricityNetDay=[{self.lastReadingElectricityNetDay}] vs currentTimeDay=[{self.currentTimeDay}]")

                    if (self.globals[SMAPPEES][devElectricityNet.id][LAST_READING_ELECTRICITY_NET_UTC] > 0 and
                            self.lastReadingElectricityNetDay == self.currentTimeDay and smappeeCommand != COMMAND_RESET_CONSUMPTION):
                        self.fromTimeElectricityNetUtc = str(int(self.globals[SMAPPEES][devElectricityNet.id][LAST_READING_ELECTRICITY_NET_UTC]))
                    else:
                        from_timeE_eectricity_net_utc = int(time.mktime(datetime.datetime.combine(datetime.date.today(), datetime.time()).timetuple()))
                        self.fromTimeElectricityNetUtc = f"{from_timeE_eectricity_net_utc}001"
                        self.globals[SMAPPEES][devElectricityNet.id][LAST_READING_ELECTRICITY_NET_UTC] = float(float(self.fromTimeElectricityNetUtc) - 1.0)
                        if "accumEnergyTotal" in devElectricityNet.states:
                            kwh = 0.0
                            kwhStr = f"{kwh:0.3f} kWh"
                            self.smappeeInterfaceLogger.info(f"reset '{devElectricityNet.name}' electricity net total to 0.0")
                            kwhReformatted = float(f"{kwh:0.3f}")
                            devElectricityNet.updateStateOnServer("accumEnergyTotal", kwhReformatted, uiValue=kwhStr)

                if self.electricitySavedId != 0:
                    devElectricitySaved = indigo.devices[self.electricitySavedId]

                    self.smappeeInterfaceLogger.debug(f"{smappeeCommand} -"
                                                      f" lastReadingElectricitySavedUtc[{type(self.globals[SMAPPEES][devElectricitySaved.id][LAST_READING_ELECTRICITY_SAVED_UTC])}]"
                                                      f" = [{self.globals[SMAPPEES][devElectricitySaved.id][LAST_READING_ELECTRICITY_SAVED_UTC]}]")
                    self.lastReadingElectricitySavedDay = int(datetime.datetime.fromtimestamp(float(
                        self.globals[SMAPPEES][devElectricitySaved.id][LAST_READING_ELECTRICITY_SAVED_UTC] / 1000)).strftime("%j"))

                    self.smappeeInterfaceLogger.debug(f"{smappeeCommand} - lastReadingElectricitySavedDay=[{self.lastReadingElectricitySavedDay}]"
                                                      f" vs currentTimeDay=[{self.currentTimeDay}]")

                    if (self.globals[SMAPPEES][devElectricitySaved.id][LAST_READING_ELECTRICITY_SAVED_UTC] > 0 and self.lastReadingElectricitySavedDay == self.currentTimeDay
                            and smappeeCommand != COMMAND_RESET_CONSUMPTION):
                        self.fromTimeElectricitySavedUtc = str(int(self.globals[SMAPPEES][devElectricitySaved.id][LAST_READING_ELECTRICITY_SAVED_UTC]))
                    else:
                        from_time_electricity_saved_utc = int(time.mktime(datetime.datetime.combine(datetime.date.today(), datetime.time()).timetuple()))
                        self.fromTimeElectricitySavedUtc = f"{from_time_electricity_saved_utc}001"
                        self.globals[SMAPPEES][devElectricitySaved.id][
                            LAST_READING_ELECTRICITY_SAVED_UTC] = float(
                            float(self.fromTimeElectricitySavedUtc) - 1.0)
                        if "accumEnergyTotal" in devElectricitySaved.states:
                            kwh = 0.0
                            kwhStr = f"{kwh:0.3f} kWh"
                            self.smappeeInterfaceLogger.info(f"reset '{devElectricitySaved.name}' electricity Saved total to 0.0")
                            kwhReformatted = float(f"{kwh:0.3f}")
                            devElectricitySaved.updateStateOnServer("accumEnergyTotal", kwhReformatted, uiValue=kwhStr)

                if self.solarId != 0:
                    devSolar = indigo.devices[self.solarId]

                    self.smappeeInterfaceLogger.debug(f"{smappeeCommand} - lastReadingSolarUtc[{type(self.globals[SMAPPEES][devSolar.id][LAST_READING_SOLAR_UTC])}]"
                                                      f" = [{self.globals[SMAPPEES][devSolar.id][LAST_READING_SOLAR_UTC]}]")
                    self.lastReadingSolarDay = int(datetime.datetime.fromtimestamp(float(self.globals[SMAPPEES][devSolar.id][LAST_READING_SOLAR_UTC] / 1000)).strftime("%j"))

                    self.smappeeInterfaceLogger.debug(f"{smappeeCommand} - lastReadingSolarDay=[{self.lastReadingSolarDay}] vs currentTimeDay=[{self.currentTimeDay}]")

                    if self.globals[SMAPPEES][devSolar.id][LAST_READING_SOLAR_UTC] > 0 and self.lastReadingSolarDay == self.currentTimeDay and smappeeCommand != COMMAND_RESET_CONSUMPTION:
                        self.fromTimeSolarUtc = str(int(self.globals[SMAPPEES][devSolar.id][LAST_READING_SOLAR_UTC]))
                    else:
                        from_time_solar_utc = int(time.mktime(datetime.datetime.combine(datetime.date.today(), datetime.time()).timetuple()))
                        self.fromTimeSolarUtc = f"{from_time_solar_utc}001"
                        self.globals[SMAPPEES][devSolar.id][LAST_READING_SOLAR_UTC] = float(
                            float(self.fromTimeSolarUtc) - 1.0)
                        if "accumEnergyTotal" in devSolar.states:
                            kwh = 0.0
                            kwhStr = f"{kwh:0.3f} kWh"
                            self.smappeeInterfaceLogger.info(f"reset '{devSolar.name}' solar generation total to 0.0")
                            kwhReformatted = float(f"{kwh:0.3f}")
                            devSolar.updateStateOnServer("accumEnergyTotal", kwhReformatted, uiValue=kwhStr)

                if self.solarUsedId != 0:
                    devSolarUsed = indigo.devices[self.solarUsedId]

                    self.smappeeInterfaceLogger.debug(f"{smappeeCommand} - lastReadingSolarUsedUtc[{type(self.globals[SMAPPEES][devSolarUsed.id][LAST_READING_SOLAR_USED_UTC])}]"
                                                      f" = [{self.globals[SMAPPEES][devSolarUsed.id][LAST_READING_SOLAR_USED_UTC]}]")
                    self.lastReadingSolarUsedDay = int(datetime.datetime.fromtimestamp(float(
                        self.globals[SMAPPEES][devSolarUsed.id][
                            LAST_READING_SOLAR_USED_UTC] / 1000)).strftime("%j"))

                    self.smappeeInterfaceLogger.debug(f"{smappeeCommand} - lastReadingSolarUsedDay=[{self.lastReadingSolarUsedDay}] vs currentTimeDay=[{self.currentTimeDay}]")

                    if self.globals[SMAPPEES][devSolarUsed.id][LAST_READING_SOLAR_USED_UTC] > 0 and \
                            self.lastReadingSolarUsedDay == self.currentTimeDay and smappeeCommand != COMMAND_RESET_CONSUMPTION:
                        self.fromTimeSolarUsedUtc = str(int(self.globals[SMAPPEES][devSolarUsed.id][LAST_READING_SOLAR_USED_UTC]))
                    else:
                        from_time_solar_used_utc = int(time.mktime(datetime.datetime.combine(datetime.date.today(), datetime.time()).timetuple()))
                        self.fromTimeSolarUsedUtc = f"{from_time_solar_used_utc}001"
                        self.globals[SMAPPEES][devSolarUsed.id][LAST_READING_SOLAR_USED_UTC] = float(
                            float(self.fromTimeSolarUtc) - 1.0)
                        if "accumEnergyTotal" in devSolarUsed.states:
                            kwh = 0.0
                            kwhStr = f"{kwh:0.3f} kWh"
                            self.smappeeInterfaceLogger.info(f"reset '{devSolarUsed.name}' solar used total to 0.0")
                            kwhReformatted = float(f"{kwh:0.3f}")
                            devSolarUsed.updateStateOnServer("accumEnergyTotal", kwhReformatted, uiValue=kwhStr)

                if self.solarExportedId != 0:
                    devSolarExported = indigo.devices[self.solarExportedId]

                    self.smappeeInterfaceLogger.debug(f"{smappeeCommand} - "
                                                      f"lastReadingSolarExportedUtc[{type(self.globals[SMAPPEES][devSolarExported.id][LAST_READING_SOLAR_EXPORTED_UTC])}]"
                                                      f" = [{self.globals[SMAPPEES][devSolarExported.id][LAST_READING_SOLAR_EXPORTED_UTC]}]")
                    self.lastReadingSolarExportedDay = int(datetime.datetime.fromtimestamp(float(
                        self.globals[SMAPPEES][devSolarExported.id][LAST_READING_SOLAR_EXPORTED_UTC] / 1000)).strftime("%j"))

                    self.smappeeInterfaceLogger.debug(f"{smappeeCommand} - lastReadingSolarExportedDay=[{self.lastReadingSolarExportedDay}] vs currentTimeDay=[{self.currentTimeDay}]")

                    if self.globals[SMAPPEES][devSolarExported.id][LAST_READING_SOLAR_EXPORTED_UTC] > 0 and \
                            self.lastReadingSolarExportedDay == self.currentTimeDay and smappeeCommand != COMMAND_RESET_CONSUMPTION:
                        self.fromTimeSolarExportedUtc = str(int(self.globals[SMAPPEES][devSolarExported.id][LAST_READING_SOLAR_EXPORTED_UTC]))
                    else:
                        from_time_solar_exported_utc = int(time.mktime(datetime.datetime.combine(datetime.date.today(), datetime.time()).timetuple()))
                        self.fromTimeSolarExportedUtc = f"{from_time_solar_exported_utc}001"
                        self.globals[SMAPPEES][devSolarExported.id][
                            LAST_READING_SOLAR_EXPORTED_UTC] = float(float(self.fromTimeSolarUtc) - 1.0)
                        if "accumEnergyTotal" in devSolarExported.states:
                            kwh = 0.0
                            kwhStr = f"{kwh:0.3f} kWh"
                            self.smappeeInterfaceLogger.info(f"reset '{devSolarExported.name}' solar exported total to 0.0")
                            kwhReformatted = float(f"{kwh:0.3f}")
                            devSolarExported.updateStateOnServer("accumEnergyTotal", kwhReformatted, uiValue=kwhStr)

                self.fromTimeUtc = 0
                if self.electricityId != 0:
                    self.fromTimeUtc = self.fromTimeElectricityUtc
                    if self.solarId != 0:
                        if self.fromTimeSolarUtc < self.fromTimeElectricityUtc:
                            self.fromTimeUtc = self.fromTimeSolarUtc
                else:
                    if self.solarId != 0:
                        self.fromTimeUtc = self.fromTimeSolarUtc

                self.globals[CONSUMPTION_DATA_RECEIVED] = True  # Set to True once the self.fromTimeUtc has been determined so getting event data doesn't fail

                # #TIME# to_time_utc = int(self.currentTimeUtc + float(3600))  # Add +1 hour to current time
                # #TIME# self.toTimeUtc = f"{to_time_utc}000"

                self.smappeeInterfaceLogger.debug(f"{smappeeCommand} - From=[{self.fromTimeUtc}], To=[{self.toTimeUtc}]")

                self.aggregationType = "1"  # 1 = 5 min values (only available for the last 14 days), 2 = hourly values, 3 = daily values, 4 = monthly values, 5 = yearly values

                url = f"https://app1pub.smappee.net/dev/v3/servicelocation/{self.serviceLocationId}/consumption?aggregation={self.aggregationType}&from={self.fromTimeUtc}&to={self.toTimeUtc}"

                # Documentation: https://smappee.atlassian.net/wiki/spaces/DEVAPI/pages/526581813/Get+Electricity+Consumption
                result_ok, reply = self.smappee_api_call(SMAPPEE_GET_API_CALL, url)

                if result_ok:
                    self.globals[QUEUES][PROCESS].put([COMMAND_GET_CONSUMPTION, self.serviceLocationId, reply])

                # process = subprocess.Popen(
                #     ['curl', '-H', 'Authorization: Bearer ' + self.globals[CONFIG][ACCESS_TOKEN],
                #      'https://app1pub.smappee.net/dev/v1/servicelocation/' + self.serviceLocationId + '/consumption?aggregation=' + self.aggregationType + '&from=' + self.fromTimeUtc + '&to=' + self.toTimeUtc,
                #      ''], stdout=subprocess.PIPE)
                #
                # response = ""
                # for line in process.stdout:
                #     line_string = line.decode("utf-8")
                #     # self.smappeeInterfaceLogger.debug(f"Response to '{smappeeCommand}' = {line}")
                #     response = response + line_string.strip()
                #
                # self.smappeeInterfaceLogger.debug(f"MERGED Response to '{smappeeCommand}' = {response}")
                #
                # self.globals[QUEUES][PROCESS].put([smappeeCommand, self.serviceLocationId, response])

        except Exception as exception_error:
            self.exception_handler(exception_error, True)  # Log error and display failing statement

    def process_get_reset_sensor_consumption(self, smappeeCommand, service_location_id):
        try:
            self.serviceLocationId = service_location_id

            self.sensorFromTimeUtc = 0

            # #TIME# self.currentTimeDay = int(datetime.datetime.fromtimestamp(self.toTimeUtc).strftime("%j"))

            for key, value in self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.serviceLocationId][SENSOR_IDS].items():
                self.smappeeInterfaceLogger.debug(f"GET_SENSOR_CONSUMPTION - sensorIds = [Type = {type(self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.serviceLocationId][SENSOR_IDS])}]"
                                                  f" {self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.serviceLocationId][SENSOR_IDS]}")
                self.smappeeInterfaceLogger.debug(f"GET_SENSOR_CONSUMPTION = [Key = {key}] {value}")
                self.smappeeInterfaceLogger.debug(f"GET_SENSOR_CONSUMPTION = [DevId = {value[DEV_ID]}]")

                if value[DEV_ID] == 0:
                    self.smappeeInterfaceLogger.debug(f"{smappeeCommand} - GET_SENSOR_CONSUMPTION - No Indigo Sensor Device defined for Smappee Sensor {key}")
                    continue

                # self.smappeeInterfaceLogger.debug(f"{smappeeCommand} - GET_SENSOR_CONSUMPTION - smappeeServiceLocationIdToDevId = [{self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID]}]")

                sensorId = value[DEV_ID]

                devSensor = indigo.devices[sensorId]

                self.smappeeInterfaceLogger.debug(f"GET_SENSOR_CONSUMPTION - {smappeeCommand} -"
                                                  f" lastReadingSensorUtc[{type(self.globals[SMAPPEES][devSensor.id][LAST_READING_SENSOR_UTC])}]"
                                                  f" = [{self.globals[SMAPPEES][devSensor.id][LAST_READING_SENSOR_UTC]}]")
                self.lastReadingSensorDay = int(datetime.datetime.fromtimestamp(float(self.globals[SMAPPEES][devSensor.id][LAST_READING_SENSOR_UTC] / 1000)).strftime("%j"))

                self.smappeeInterfaceLogger.debug(f"GET_SENSOR_CONSUMPTION - {smappeeCommand} -"
                                                  f" lastReadingSensorDay=[{self.lastReadingSensorDay}] vs currentTimeDay=[{self.currentTimeDay}]")

                if self.globals[SMAPPEES][devSensor.id][
                        LAST_READING_SENSOR_UTC] > 0 and self.lastReadingSensorDay == self.currentTimeDay and smappeeCommand != COMMAND_RESET_SENSOR_CONSUMPTION:
                    self.fromTimeSensorUtc = str(
                        int(self.globals[SMAPPEES][devSensor.id][LAST_READING_SENSOR_UTC]))
                else:
                    fromTimeSensorUtc = int(time.mktime(datetime.datetime.combine(datetime.date.today(), datetime.time()).timetuple()))
                    self.fromTimeSensorUtc = f"{fromTimeSensorUtc}001"
                    self.globals[SMAPPEES][devSensor.id][LAST_READING_SENSOR_UTC] = float(
                        float(self.fromTimeSensorUtc) - 1.0)
                    if "accumEnergyTotal" in devSensor.states:
                        kwh = 0.0
                        kwhStr = f"{kwh:0.3f} kWh"
                        self.smappeeInterfaceLogger.info(f"reset '{devSensor.name}' sensor total to 0.0")
                        kwhReformatted = float(f"{kwh:0.3f}")
                        devSensor.updateStateOnServer("accumEnergyTotal", kwhReformatted, uiValue=kwhStr)

                self.sensorFromTimeUtc = self.fromTimeSensorUtc

                sensor_to_time_utc = int(self.currentTimeUtc + float(3600))  # Add +1 hour to current time
                self.sensorToTimeUtc = f"{sensor_to_time_utc}000"

                self.smappeeInterfaceLogger.debug(f"GET_SENSOR_CONSUMPTION [BC] - {smappeeCommand} - SENSOR From=[{self.sensorFromTimeUtc}], To=[{self.sensorToTimeUtc}]")

                self.aggregationType = "1"  # 1 = 5 min values (only available for the last 14 days), 2 = hourly values, 3 = daily values, 4 = monthly values, 5 = yearly values

                self.sensorAddress = str(int(str(devSensor.address)[2:4]))
                self.smappeeInterfaceLogger.debug(f"Sensor Address = '{self.sensorAddress}'")

                url = f"https://app1pub.smappee.net/dev/v3/servicelocation/{self.serviceLocationId}/sensor/{self.sensorAddress}/consumption?aggregation={self.aggregationType}&from={self.sensorFromTimeUtc}&to={self.sensorToTimeUtc}"

                # Documentation: https://smappee.atlassian.net/wiki/spaces/DEVAPI/pages/526581817/Get+Sensor+Consumption
                result_ok, reply = self.smappee_api_call(SMAPPEE_GET_API_CALL, url)

                if result_ok:
                    self.globals[QUEUES][PROCESS].put([COMMAND_GET_SENSOR_CONSUMPTION, self.serviceLocationId, reply])

                # process = subprocess.Popen(
                #     ['curl', '-H', 'Authorization: Bearer ' + self.globals[CONFIG][ACCESS_TOKEN],
                #      'https://app1pub.smappee.net/dev/v1/servicelocation/' + self.serviceLocationId + '/sensor/' + self.sensorAddress + '/consumption?aggregation=' + self.aggregationType + '&from=' + self.sensorFromTimeUtc + '&to=' + self.sensorToTimeUtc,
                #      ''], stdout=subprocess.PIPE)
                #
                # response = ""
                # for line in process.stdout:
                #     line_string = line.decode("utf-8")
                #     # self.smappeeInterfaceLogger.debug(f"Response to '{smappeeCommand}' = {line}")
                #     response = response + line_string.strip()
                #
                # self.smappeeInterfaceLogger.debug(f"GET_SENSOR_CONSUMPTION [AC] - MERGED Sensor Response to '{smappeeCommand}' = {response}")

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

                # self.smappeeInterfaceLogger.debug(f"GET_SENSOR_CONSUMPTION [AC-FIXED] - MERGED Sensor Response to '{smappeeCommand}' = {response}")

                # self.globals[QUEUES][PROCESS].put([smappeeCommand, self.serviceLocationId, response])

        except Exception as exception_error:
            self.exception_handler(exception_error, True)  # Log error and display failing statement

    def process_get_events(self, smappeeCommand, service_location_id):
        try:
            self.serviceLocationId = service_location_id

            self.smappeeInterfaceLogger.debug(f"{smappeeCommand} - smappeeServiceLocationIdToDevId = [{self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID]}]")
            if self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.serviceLocationId][ELECTRICITY_ID] != 0:
                dev = indigo.devices[self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.serviceLocationId][ELECTRICITY_ID]]

                # #TIME# self.toTimeUtc = time.mktime(indigo.server.getTime().timetuple())
                # #TIME# self.smappeeInterfaceLogger.debug(f"{smappeeCommand} - self.toTimeUtc[{type(self.toTimeUtc)}] =[{self.toTimeUtc}]")

                self.smappeeInterfaceLogger.debug(f"{smappeeCommand} - lastReadingElectricityUtc[{type(self.globals[SMAPPEES][dev.id][LAST_READING_ELECTRICITY_UTC])}]"
                                                  f" = [{self.globals[SMAPPEES][dev.id][LAST_READING_ELECTRICITY_UTC]}]")
                self.lastReadingDay = int(datetime.datetime.fromtimestamp(float(self.globals[SMAPPEES][dev.id][LAST_READING_ELECTRICITY_UTC] / 1000)).strftime("%j"))

                # #TIME# self.currentTimeDay = int(datetime.datetime.fromtimestamp(self.toTimeUtc).strftime("%j"))
                # #TIME# self.smappeeInterfaceLogger.debug(f"{smappeeCommand} - lastReadingDay=[{self.lastReadingDay}] vs currentTimeDay=[{self.currentTimeDay}]")

                # to_time_utc_plus_one_hour = int(self.toTimeUtc + float(3600))
                # #TIME# self.toTimeUtc = f"{to_time_utc_plus_one_hour}000"

                self.smappeeInterfaceLogger.debug(f"{smappeeCommand} - From=[{self.fromTimeUtc}], To=[{self.toTimeUtc}]")

                self.appliances = "applianceId=1&applianceId=2&applianceId=15&applianceId=3&applianceId=34"
                self.maxNumber = "20"

                url = f"https://app1pub.smappee.net/dev/v3/servicelocation/{self.serviceLocationId}/events?{self.appliances}&maxNumber={self.maxNumber}&from={self.fromTimeUtc}&to={self.toTimeUtc}"

                # Documentation: https://smappee.atlassian.net/wiki/spaces/DEVAPI/pages/526450713/Get+Events
                result_ok, reply = self.smappee_api_call(SMAPPEE_GET_API_CALL, url)

                if result_ok:
                    self.globals[QUEUES][PROCESS].put([COMMAND_GET_EVENTS, self.serviceLocationId, reply])

                #
                # process = subprocess.Popen(
                #     ['curl', '-H', 'Authorization: Bearer ' + self.globals[CONFIG][ACCESS_TOKEN],
                #      'https://app1pub.smappee.net/dev/v1/servicelocation/' + self.serviceLocationId + '/events?' + self.appliances + '&maxNumber=' + self.maxNumber + '&from=' + self.fromTimeUtc + '&to=' + self.toTimeUtc,
                #      ''], stdout=subprocess.PIPE)
                #
                # response = ""
                # for line in process.stdout:
                #     line_string = line.decode("utf-8")
                #     # self.smappeeInterfaceLogger.debug(f"Response to '{smappeeCommand}' = {line}")
                #     response = response + line_string.strip()
                #
                # self.smappeeInterfaceLogger.debug(f"MERGED Response to '{smappeeCommand}' = {response}")
                #
                # self.globals[QUEUES][PROCESS].put([smappeeCommand, self.serviceLocationId, response])

        except Exception as exception_error:
            self.exception_handler(exception_error, True)  # Log error and display failing statement

    def process_initialise(self):
        try:
            url = "https://app1pub.smappee.net/dev/v3/oauth2/token"

            # Documentation: https://smappee.atlassian.net/wiki/spaces/DEVAPI/pages/8552463/Get+token
            result_ok, reply = self.smappee_api_call(SMAPPEE_POST_API_CALL, url)

            if result_ok:
                self.globals[QUEUES][PROCESS].put([COMMAND_INITIALISE, "", reply])

        except Exception as exception_error:
            self.exception_handler(exception_error, True)  # Log error and display failing statement

    def process_get_service_locations(self):
        try:
            url = "https://app1pub.smappee.net/dev/v3/servicelocation"

            # Documentation: https://smappee.atlassian.net/wiki/spaces/DEVAPI/pages/526483487/Get+Servicelocations
            result_ok, reply = self.smappee_api_call(SMAPPEE_GET_API_CALL, url)

            if result_ok:
                self.globals[QUEUES][PROCESS].put([COMMAND_GET_SERVICE_LOCATIONS, "", reply])

            # process = subprocess.Popen(
            #     ['curl', '-H', 'Authorization: Bearer ' + self.globals[CONFIG][ACCESS_TOKEN],
            #      'https://app1pub.smappee.net/dev/v3/servicelocation', ''], stdout=subprocess.PIPE)
            #
            # response = ""
            # for line in process.stdout:
            #     line_string = line.decode("utf-8")
            #     # self.smappeeInterfaceLogger.debug(f"Response to '{smappeeCommand}' = {line}")
            #     response = response + line_string.strip()
            #
            # self.smappeeInterfaceLogger.debug(f"MERGED Response to '{smappeeCommand}' = {response}")
            #
            # self.globals[QUEUES][PROCESS].put([COMMAND_GET_SERVICE_LOCATIONS, "", response])

        except Exception as exception_error:
            self.exception_handler(exception_error, True)  # Log error and display failing statement

    def process_get_service_location_info(self, smappee_command, service_location_id):
        try:
            url = f"https://app1pub.smappee.net/dev/v3/servicelocation/{service_location_id}/info"

            # Documentation: https://smappee.atlassian.net/wiki/spaces/DEVAPI/pages/526614552/Get+Servicelocation+Info
            result_ok, reply = self.smappee_api_call(SMAPPEE_GET_API_CALL, url)

            if result_ok:
                self.globals[QUEUES][PROCESS].put([COMMAND_GET_SERVICE_LOCATION_INFO, service_location_id, reply])

            # self.serviceLocationId = commandToSend[1]
            # process = subprocess.Popen(
            #     ['curl', '-H', 'Authorization: Bearer ' + self.globals[CONFIG][ACCESS_TOKEN],
            #      'https://app1pub.smappee.net/dev/v1/servicelocation/' + self.serviceLocationId + '/info',
            #      ''], stdout=subprocess.PIPE)
            #
            # response = ""
            # for line in process.stdout:
            #     line_string = line.decode("utf-8")
            #     # self.smappeeInterfaceLogger.debug(f"Response to '{smappeeCommand}' = {line}")
            #     response = response + line_string.strip()
            #
            # # TESTING GAS / WATER [START]
            # # response = response[:-1]
            # # response = response + str(', "sensors": [{"id": 4, "name": "Sensor 4"}, {"id": 5, "name": "Sensor 5"}]}').strip()
            # # TESTING GAS / WATER [END]
            #
            # self.smappeeInterfaceLogger.debug(f"MERGED Response to '{smappeeCommand}' = {response}")
            #
            # self.globals[QUEUES][PROCESS].put([COMMAND_GET_SERVICE_LOCATION_INFO, self.serviceLocationId, response])

        except Exception as exception_error:
            self.exception_handler(exception_error, True)  # Log error and display failing statement

    def process_on_off(self, smappeeCommand, service_location_id, actuator_id):
        try:
            # Format: 'ON|OFF', ServiceLocationId, ActuatorId

            self.serviceLocationId = service_location_id
            self.actuatorId = actuator_id

            process = subprocess.Popen(['curl', '-H', 'Content-Type: application/json', '-H',
                                        'Authorization: Bearer ' + self.globals[CONFIG][ACCESS_TOKEN],
                                        '-d', '{}',
                                        'https://app1pub.smappee.net/dev/v1/servicelocation/' + self.serviceLocationId + '/actuator/' + self.actuatorId + '/'
                                        + str(smappeeCommand).lower(), ''], stdout=subprocess.PIPE)

            response = ""
            for line in process.stdout:
                line_string = line.decode("utf-8")
                # self.smappeeInterfaceLogger.debug(f"Response to '{smappeeCommand}' = {line}")
                response = response + line_string.strip()

            self.smappeeInterfaceLogger.debug(f"MERGED Response to '{smappeeCommand}' = {response}")

            # No need to handle response

        except Exception as exception_error:
            self.exception_handler(exception_error, True)  # Log error and display failing statement

    def process_check_token_refresh(self):
        try:
            # #TIME# self.currentTimeUtc = time.mktime(indigo.server.getTime().timetuple())
            if self.currentTimeUtc > self.globals[CONFIG][TOKEN_EXPIRES_DATETIME_UTC]:
                self.smappeeInterfaceLogger.debug(f"Refresh Token Request = {self.globals[CONFIG][REFRESH_TOKEN]}")
                self.smappeeInterfaceLogger.debug(f"Refresh Token, currentUTC[{type(self.currentTimeUtc)}] = {self.currentTimeUtc},"
                                                  f" expiresUTC[{type(self.globals[CONFIG][TOKEN_EXPIRES_DATETIME_UTC])}] = {self.globals[CONFIG][TOKEN_EXPIRES_DATETIME_UTC]}")

                process = subprocess.Popen(
                    ['curl', '-XPOST', '-H', 'application/x-www-form-urlencoded;charset=UTF-8', '-d',
                     'grant_type=refresh_token&refresh_token='
                     + self.globals[CONFIG][REFRESH_TOKEN]
                     + '&client_id=' + self.globals[CONFIG][CLIENT_ID]
                     + '&client_secret=' + self.globals[CONFIG][SECRET],
                     'https://app1pub.smappee.net/dev/v1/oauth2/token', '-d', ''], stdout=subprocess.PIPE)

                response = ""
                for line in process.stdout:
                    line_string = line.decode("utf-8")
                    # self.smappeeInterfaceLogger.debug(f"Response to '{smappeeCommand}' = {line}")
                    response = response + line_string.strip()

                self.smappeeInterfaceLogger.debug(f"MERGED Response to Refresh Token = {response}")

                self.globals[QUEUES][PROCESS].put([COMMAND_REFRESH_TOKEN, "", response])
        except Exception as exception_error:
            self.exception_handler(exception_error, True)  # Log error and display failing statement

    def smappee_api_call(self, is_post_api_call, api_url):
        try:
            error_code = None
            error_message_ui = ""
            try:
                status_code = -1
                if is_post_api_call:
                    post_data = dict()
                    post_data["grant_type"] = "password"
                    post_data["client_id"] = self.globals[CONFIG][CLIENT_ID]
                    post_data["client_secret"] = self.globals[CONFIG][SECRET]
                    post_data["username"] = self.globals[CONFIG][USER_NAME]
                    post_data["password"] = self.globals[CONFIG][PASSWORD]
                    headers = {"Content-type": "application/x-www-form-urlencoded;charset=UTF-8"}
                    reply = requests.post(api_url, headers=headers, data=post_data)
                else:
                    headers = {"Authorization": f"Bearer {self.globals[CONFIG][ACCESS_TOKEN]}"}
                    reply = requests.get(api_url, headers=headers)
                reply.raise_for_status()  # raise an HTTP error if one coccurred
                status_code = reply.status_code
                # print(f"Reply Status: {reply.status_code}, Text: {reply.text}")
                if status_code == 200:
                    pass
                # elif status_code == 400 or status_code == 401:
                #     error_details = reply.json()
                #     error_code = error_details["code"]
                #     error_message_ui = error_details["message"]
                # elif status_code == 404:
                #     error_code = "Not Found"
                #     error_message_ui = "Starling Hub not found"
                else:
                    error_code = "Unknown Error"
                    error_message_ui = f"unknown connection error: {status_code}"
            except requests.exceptions.HTTPError as error_message:
                error_code = "HTTP Error"
                error_message_ui = f"Access Smappee failed: {error_message}"
                # print(f"HTTP ERROR: {error_message}")
                if error_code != self.previous_status_message:
                    self.smappeeInterfaceLogger.error(error_message_ui)
                return False, [error_code, error_message_ui]
            except requests.exceptions.Timeout as error_message:
                error_code = "Timeout Error"
                error_message_ui = f"Access Smappee failed with a timeout error. Retrying . . ."
                if error_code != self.previous_status_message:
                    self.smappeeInterfaceLogger.error(error_message_ui)
                return False, [error_code, error_message_ui]
            except requests.exceptions.ConnectionError as error_message:
                error_code = "Connection Error"
                error_message_ui = f"Access Smappee failed with a connection error. Retrying . . ."
                if error_code != self.previous_status_message:
                    self.smappeeInterfaceLogger.error(error_message_ui)
                return False, [error_code, error_message_ui]
            except requests.exceptions.RequestException as error_message:
                error_code = "OOps: Unknown error"
                if error_code != self.previous_status_message:
                    error_message_ui = f"Access Smappee failed with an unknown error. Retrying . . ."
                    self.smappeeInterfaceLogger.info(error_message_ui)
                return False, [error_code, error_message_ui]

            if status_code == 200:
                reply = reply.json()  # decode JSON
                # # Check Filter
                # if FILTERS in self.globals:
                #     if len(self.globals[FILTERS]) > 0 and self.globals[FILTERS] != ["-0-"]:
                #         self.nest_filter_log_processing(starling_hub_dev.id, starling_hub_dev.name, control_api, reply)

                return_ok = True
                return return_ok, reply  # noqa [reply might be referenced before assignment]

            else:
                # TODO: Sort this out!
                return_ok = False
                if error_message_ui is "":
                    self.smappeeInterfaceLogger.error(f"Error [{status_code}] accessing Smappee '{starling_hub_dev.name}': {error_code}")
                else:
                    self.smappeeInterfaceLogger.error(f"Error [{status_code}] accessing Smappee '{starling_hub_dev.name}': {error_code} - {error_message_ui}")
                return return_ok, [error_code, error_message_ui]

        except Exception as exception_error:
            self.exception_handler(exception_error, True)  # Log error and display failing statement
            return False, [255, exception_error]
