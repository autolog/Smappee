#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# Smappee Controller © Autolog 2018-2023
# 
# Requires Indigo 2022.1+ [Runs under Python 3]

# noinspection PyUnresolvedReferences
# ============================== Native Imports ===============================

import collections  # Used for creating sensor testdata
import datetime
import json
# import logging
import platform
import queue
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
from polling import ThreadPolling
from smappeeInterface import ThreadSmappeeInterface


# noinspection PyPep8Naming,PyUnresolvedReferences,SpellCheckingInspection
class Plugin(indigo.PluginBase):

    def __init__(self, plugin_id, plugin_display_name, plugin_version, plugin_prefs):

        indigo.PluginBase.__init__(self, plugin_id, plugin_display_name, plugin_version, plugin_prefs)

        # Initialise dictionary to store plugin Globals
        self.globals = dict()

        # Initialise Indigo plugin info
        self.globals[PLUGIN_INFO] = dict()
        self.globals[PLUGIN_INFO][PLUGIN_ID] = plugin_id
        self.globals[PLUGIN_INFO][PLUGIN_DISPLAY_NAME] = plugin_display_name
        self.globals[PLUGIN_INFO][PLUGIN_VERSION] = plugin_version
        self.globals[PLUGIN_INFO][PATH] = indigo.server.getInstallFolderPath()
        self.globals[PLUGIN_INFO][API_VERSION] = indigo.server.apiVersion
        self.globals[PLUGIN_INFO][INDIGO_SERVER_ADDRESS] = indigo.server.address

        log_format = logging.Formatter("%(asctime)s.%(msecs)03d\t%(levelname)-12s\t%(name)s.%(funcName)-25s %(msg)s", datefmt="%Y-%m-%d %H:%M:%S")
        self.plugin_file_handler.setFormatter(log_format)
        self.plugin_file_handler.setLevel(LOG_LEVEL_INFO)  # Logging Level for plugin log file
        self.indigo_log_handler.setLevel(LOG_LEVEL_INFO)   # Logging level for Indigo Event Log

        self.logger = logging.getLogger("Plugin.SMAPPEE")

        # Initialise id of folder to hold devices
        self.globals[DEVICES_FOLDER_ID] = 0

        # Initialise dictionary to store message queues
        self.globals[QUEUES] = dict()
        self.globals[QUEUES][INITIALISED] = False

        self.globals[SQL] = dict()
        self.globals[SQL][ENABLED] = False

        self.globals[TESTING] = False  # Set to True to action next section of code
        if self.globals[TESTING]:
            self.globals[TEST_DATA] = dict()
            self.globals[TEST_DATA][TEST_TEMPERATURE] = collections.deque(['255', '252', '250', '249', '247', '246', '220', '223', '221', '198', '195', '192'])
            self.globals[TEST_DATA][TEST_HUMIDITY] = collections.deque(['90', '85', '80', '75', '70', '65', '60', '55', '50', '45', '40', '35'])
            self.globals[TEST_DATA][TEST_BATTERY_LEVEL] = collections.deque(['100', '99', '98', '97', '95', '94', '93', '92', '91', '90', '89', '88'])
            self.globals[TEST_DATA][TEST_VALUE_1] = collections.deque(['0', '800', '400', '0', '800', '800', '1200', '100', '0', '0', '1000', '700'])
            self.globals[TEST_DATA][TEST_VALUE_2] = collections.deque(['50', '50', '0', '0', '0', '0', '400', '0', '0', '0', '50', '70'])

        self.globals[UNIT_TABLE] = dict()

        self.globals[UNIT_TABLE][DEFAULT] = dict()
        self.globals[UNIT_TABLE][DEFAULT][MEASUREMENT_TIME_MULTIPLIER] = 12.0  # 'hourly' = 12, '5 minutes' = 1'
        self.globals[UNIT_TABLE][DEFAULT][FORMAT_TOTAL_DIVISOR] = 1000.0
        self.globals[UNIT_TABLE][DEFAULT][FORMAT_CURRENT] = "%d"
        self.globals[UNIT_TABLE][DEFAULT][FORMAT_TOTAL] = "%3.0f"
        self.globals[UNIT_TABLE][DEFAULT][CURRENT_UNITS] = 'watts [E]'
        self.globals[UNIT_TABLE][DEFAULT][CURRENT_UNITS_RATE] = 'watt [E] hours'
        self.globals[UNIT_TABLE][DEFAULT][ACCUM_UNITS] = 'kWh [E]'

        self.globals[UNIT_TABLE][KWH] = dict()
        self.globals[UNIT_TABLE][KWH][MEASUREMENT_TIME_MULTIPLIER] = 12.0  # 'hourly' = 12, '5 minutes' = 1'
        self.globals[UNIT_TABLE][KWH][FORMAT_TOTAL_DIVISOR] = 1000.0
        self.globals[UNIT_TABLE][KWH][FORMAT_CURRENT_DIVISOR] = 1000.0
        self.globals[UNIT_TABLE][KWH][FORMAT_CURRENT] = "%d"
        self.globals[UNIT_TABLE][KWH][FORMAT_TOTAL] = "%3.0f"
        self.globals[UNIT_TABLE][KWH][CURRENT_UNITS] = 'watts'
        self.globals[UNIT_TABLE][KWH][CURRENT_UNITS_RATE] = 'watt hours'
        self.globals[UNIT_TABLE][KWH][ACCUM_UNITS] = 'kWh'

        self.globals[UNIT_TABLE][LITRES] = dict()
        self.globals[UNIT_TABLE][LITRES][MEASUREMENT_TIME_MULTIPLIER] = 1.0  # 'hourly' = 12, '5 minutes' = 1'
        self.globals[UNIT_TABLE][LITRES][FORMAT_TOTAL_DIVISOR] = 1.0
        self.globals[UNIT_TABLE][LITRES][FORMAT_CURRENT] = "%d"
        self.globals[UNIT_TABLE][LITRES][FORMAT_TOTAL] = "%d"
        self.globals[UNIT_TABLE][LITRES][CURRENT_UNITS] = 'litres'
        self.globals[UNIT_TABLE][LITRES][ACCUM_UNITS] = 'litres'

        self.globals[UNIT_TABLE][M_3] = dict()
        self.globals[UNIT_TABLE][M_3][MEASUREMENT_TIME_MULTIPLIER] = 1.0  # 'hourly' = 12, '5 minutes' = 1'
        self.globals[UNIT_TABLE][M_3][FORMAT_TOTAL_DIVISOR] = 1.0
        self.globals[UNIT_TABLE][M_3][FORMAT_CURRENT] = "%d"
        self.globals[UNIT_TABLE][M_3][FORMAT_TOTAL] = "%d"
        self.globals[UNIT_TABLE][M_3][CURRENT_UNITS] = 'cubic metres'
        self.globals[UNIT_TABLE][M_3][ACCUM_UNITS] = 'cubic metres'

        self.globals[UNIT_TABLE][FT_3] = dict()
        self.globals[UNIT_TABLE][FT_3][MEASUREMENT_TIME_MULTIPLIER] = 1.0  # 'hourly' = 12, '5 minutes' = 1'
        self.globals[UNIT_TABLE][FT_3][FORMAT_TOTAL_DIVISOR] = 1.0
        self.globals[UNIT_TABLE][FT_3][FORMAT_CURRENT] = "%d"
        self.globals[UNIT_TABLE][FT_3][FORMAT_TOTAL] = "%d"
        self.globals[UNIT_TABLE][FT_3][CURRENT_UNITS] = 'cubic feet'
        self.globals[UNIT_TABLE][FT_3][ACCUM_UNITS] = 'cubic feet'

        self.globals[UNIT_TABLE][GALLONS] = dict()
        self.globals[UNIT_TABLE][GALLONS][MEASUREMENT_TIME_MULTIPLIER] = 1.0  # 'hourly' = 12, '5 minutes' = 1'
        self.globals[UNIT_TABLE][GALLONS][FORMAT_TOTAL_DIVISOR] = 1.0
        self.globals[UNIT_TABLE][GALLONS][FORMAT_CURRENT] = "%d"
        self.globals[UNIT_TABLE][GALLONS][FORMAT_TOTAL] = "%d"
        self.globals[UNIT_TABLE][GALLONS][CURRENT_UNITS] = 'gallons'
        self.globals[UNIT_TABLE][GALLONS][ACCUM_UNITS] = 'gallons'

        self.globals[CONFIG] = dict()
        self.globals[CONFIG][ADDRESS] = ""
        self.globals[CONFIG][CLIENT_ID] = ""
        self.globals[CONFIG][SECRET] = ""
        self.globals[CONFIG][USER_NAME] = ""
        self.globals[CONFIG][PASSWORD] = ""

        self.globals[CONFIG][APP_NAME] = ""  # Not sure what this is for! Name provided by Get ServiceLocations Smappee call

        self.globals[CONFIG][ACCESS_TOKEN] = ""
        self.globals[CONFIG][REFRESH_TOKEN] = ""
        self.globals[CONFIG][TOKEN_EXPIRES_IN] = 0
        self.globals[CONFIG][TOKEN_EXPIRES_DATETIME_UTC] = 0

        self.globals[CONFIG][SUPPORTS_ELECTRICITY] = False
        self.globals[CONFIG][SUPPORTS_ELECTRICITY_NET] = False
        self.globals[CONFIG][SUPPORTS_ELECTRICITY_SAVED] = False
        self.globals[CONFIG][SUPPORTS_SOLAR] = False
        self.globals[CONFIG][SUPPORTS_SOLAR_USED] = False
        self.globals[CONFIG][SUPPORTS_SOLAR_EXPORTED] = False
        self.globals[CONFIG][SUPPORTS_SENSOR] = False

        # Initialise Global arrays to store internal details about Smappees, Smappee Appliances & Plugs
        self.globals[PLUGIN_INITIALIZED] = False
        self.globals[CONSUMPTION_DATA_RECEIVED] = False  # Used to signify it is now OK to get Events
        self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID] = dict()  # Used to derive Smappee Device Ids from Smappee Service Location Ids
        self.globals[SMAPPEES] = dict()
        self.globals[SMAPPEE_APPLIANCES] = dict()
        self.globals[SMAPPEE_PLUGS] = dict()

        self.globals[POLLING] = dict()
        self.globals[POLLING][THREAD_ACTIVE] = False        
        self.globals[POLLING][STATUS] = False
        self.globals[POLLING][SECONDS] = float(300.0)  # 5 minutes
        self.globals[POLLING][THREAD_END] = False

        # Set Plugin Config Values
        self.closedPrefsConfigUi(plugin_prefs, False)

    def __del__(self):

        indigo.PluginBase.__del__(self)

    def display_plugin_information(self):
        try:
            def plugin_information_message():
                startup_message_ui = "Plugin Information:\n"
                startup_message_ui += f"{'':={'^'}80}\n"
                startup_message_ui += f"{'Plugin Name:':<30} {self.globals[PLUGIN_INFO][PLUGIN_DISPLAY_NAME]}\n"
                startup_message_ui += f"{'Plugin Version:':<30} {self.globals[PLUGIN_INFO][PLUGIN_VERSION]}\n"
                startup_message_ui += f"{'Plugin ID:':<30} {self.globals[PLUGIN_INFO][PLUGIN_ID]}\n"
                startup_message_ui += f"{'Indigo Version:':<30} {indigo.server.version}\n"
                startup_message_ui += f"{'Indigo License:':<30} {indigo.server.licenseStatus}\n"
                startup_message_ui += f"{'Indigo API Version:':<30} {indigo.server.apiVersion}\n"
                startup_message_ui += f"{'Architecture:':<30} {platform.machine()}\n"
                startup_message_ui += f"{'Python Version:':<30} {sys.version.split(' ')[0]}\n"
                startup_message_ui += f"{'Mac OS Version:':<30} {platform.mac_ver()[0]}\n"
                startup_message_ui += f"{'Plugin Process ID:':<30} {os.getpid()}\n"
                startup_message_ui += f"{'':={'^'}80}\n"
                return startup_message_ui

            self.logger.info(plugin_information_message())

        except Exception as exception_error:
            self.exception_handler(exception_error, True)  # Log error and display failing statement

    def exception_handler(self, exception_error_message, log_failing_statement):
        filename, line_number, method, statement = traceback.extract_tb(sys.exc_info()[2])[-1]
        module = filename.split('/')
        log_message = f"'{exception_error_message}' in module '{module[-1]}', method '{method} [{self.globals[PLUGIN_INFO][PLUGIN_VERSION]}]'"
        if log_failing_statement:
            log_message = log_message + f"\n   Failing statement [line {line_number}]: '{statement}'"
        else:
            log_message = log_message + f" at line {line_number}"
        self.logger.error(log_message)

    def startup(self):

        indigo.devices.subscribeToChanges()

        # Create queues
        self.globals[QUEUES] = dict()
        self.globals[QUEUES][SEND_TO_SMAPPEE] = queue.Queue()  # Used to queue smappee commands
        self.globals[QUEUES][PROCESS] = queue.Queue()  # Used to queue output from smappee
        self.globals[QUEUES][INITIALISED] = True

        self.globals[THREADS] = dict()
        self.globals[THREADS][POLLING] = dict()
        self.globals[THREADS][SMAPPEE_INTERFACE] = dict()

        self.globals[THREADS][SMAPPEE_INTERFACE][EVENT] = threading.Event()
        self.globals[THREADS][SMAPPEE_INTERFACE][THREAD] = ThreadSmappeeInterface(self.globals, self.globals[THREADS][SMAPPEE_INTERFACE][EVENT])
        self.globals[THREADS][SMAPPEE_INTERFACE][THREAD].start()

        # Now send an INITIALISE command (via queue) to Smappee to initialise the plugin
        self.globals[QUEUES][SEND_TO_SMAPPEE].put([COMMAND_INITIALISE])

        # Start the Polling thread
        if self.globals[POLLING][STATUS] and not self.globals[POLLING][THREAD_ACTIVE]:
            self.globals[THREADS][POLLING][EVENT] = threading.Event()
            self.globals[THREADS][POLLING][THREAD] = ThreadPolling(self.globals, self.globals[THREADS][POLLING][EVENT])
            self.globals[THREADS][POLLING][THREAD].start()

        self.logger.info("Initialisation in progress ...")

    def shutdown(self):
        self.logger.info("Plugin shutdown requested")

        self.globals[QUEUES][SEND_TO_SMAPPEE] .put([END_THREAD])

        if hasattr(self, "pollingThread"):  # TODO - CHECK THIS IS CORRECT ?????
            if self.globals[POLLING][STATUS]:
                self.globals[POLLING][THREAD_END] = True
                self.pollingEvent.set()  # Stop the Polling Thread

        # time.sleep(2)  # Wait 2 seconds before contacting Smappee - gives plugin time to properly shutdown

        self.logger.info("Plugin shutdown complete")

    def getPrefsConfigUiValues(self):
        prefsConfigUiValues = self.plugin_prefs
        if "smappeeDeviceFolder" not in prefsConfigUiValues:
            prefsConfigUiValues["smappeeDeviceFolder"] = 'SMAPPEE'

        return prefsConfigUiValues

    def validatePrefsConfigUi(self, valuesDict):

        return True

    def closedPrefsConfigUi(self, valuesDict, userCancelled):
        self.logger.debug(f"'closePrefsConfigUi' called with userCancelled = {userCancelled}")

        try:
            if userCancelled:
                return

            # Get required Event Log and Plugin Log logging levels
            plugin_log_level = int(valuesDict.get("pluginLogLevel", LOG_LEVEL_INFO))
            event_log_level = int(valuesDict.get("eventLogLevel", LOG_LEVEL_INFO))

            # Ensure following logging level messages are output
            self.indigo_log_handler.setLevel(LOG_LEVEL_INFO)
            self.plugin_file_handler.setLevel(LOG_LEVEL_INFO)

            # Output required logging levels and TP Message Monitoring requirement to logs
            self.logger.info(f"Logging to Indigo Event Log at the '{LOG_LEVEL_TRANSLATION[event_log_level]}' level")
            self.logger.info(f"Logging to Plugin Event Log at the '{LOG_LEVEL_TRANSLATION[plugin_log_level]}' level")

            # Now set required logging levels
            self.indigo_log_handler.setLevel(event_log_level)
            self.plugin_file_handler.setLevel(plugin_log_level)

            if "smappeeAddress" in valuesDict:
                self.globals[CONFIG][ADDRESS] = valuesDict["smappeeAddress"]
            else:
                self.globals[CONFIG][ADDRESS] = "https://app1pub.smappee.net/dev/v3/servicelocation"

            if "smappeeClientId" in valuesDict:
                self.globals[CONFIG][CLIENT_ID] = valuesDict["smappeeClientId"]
            else:
                self.globals[CONFIG][CLIENT_ID] = ""

            if "smappeeSecret" in valuesDict:
                self.globals[CONFIG][SECRET] = valuesDict["smappeeSecret"]
            else:
                self.globals[CONFIG][SECRET] = ""

            if "smappeeUserName" in valuesDict:
                self.globals[CONFIG][USER_NAME] = valuesDict["smappeeUserName"]
            else:
                self.globals[CONFIG][USER_NAME] = ""

            if "smappeePassword" in valuesDict:
                self.globals[CONFIG][PASSWORD] = valuesDict["smappeePassword"]
            else:
                self.globals[CONFIG][PASSWORD] = ""

            # ### FOLDER ###
            if "smappeeDeviceFolder" in valuesDict:
                self.globals[CONFIG][SMAPPEE_DEVICE_FOLDER] = valuesDict["smappeeDeviceFolder"]
            else:
                self.globals[CONFIG][SMAPPEE_DEVICE_FOLDER] = "SMAPPEE"

            # Create Smappee folder name (if required) in devices (for smappee monitors, appliances and plugs)
            self.deviceFolderName = self.globals[CONFIG][SMAPPEE_DEVICE_FOLDER]
            if self.deviceFolderName == "":
                self.globals[DEVICES_FOLDER_ID] = None  # noqa - Not required?
            else:
                if self.deviceFolderName not in indigo.devices.folders:
                    self.deviceFolder = indigo.devices.folder.create(self.deviceFolderName)
                self.globals[DEVICES_FOLDER_ID] = indigo.devices.folders.getId(self.deviceFolderName)

            # ### POLLING ###
            self.globals[POLLING][STATUS] = bool(valuesDict.get("statusPolling", False))
            self.globals[POLLING][SECONDS] = float(valuesDict.get("pollingSeconds", float(300.0)))  # Default to 5 minutes

            if not self.globals[POLLING][STATUS]:
                if self.globals[POLLING][THREAD_ACTIVE]:
                    self.globals[POLLING][FORCE_THREAD_END] = True
                    self.globals[THREADS][POLLING][EVENT].set()  # Stop the Polling Thread
                    self.globals[THREADS][POLLING][THREAD].join(5.0)  # Wait for up t0 5 seconds for it to end
                    del self.globals[THREADS][POLLING][THREAD]  # Delete thread so that it can be recreated if polling is turned on again
            else:
                if not self.globals[POLLING][THREAD_ACTIVE]:
                    if self.globals[QUEUES][INITIALISED]:
                        self.globals[POLLING][FORCE_THREAD_END] = False
                        self.globals[THREADS][POLLING][EVENT] = threading.Event()
                        self.globals[THREADS][POLLING][THREAD] = ThreadPolling(self.globals, self.globals[THREADS][POLLING][EVENT])
                        self.globals[THREADS][POLLING][THREAD].start()
                else:
                    self.globals[POLLING][FORCE_THREAD_END] = False
                    self.globals[THREADS][POLLING][EVENT].set()  # cause the Polling Thread to update immediately with potentially new polling seconds value

        except Exception as exception_error:
            self.exception_handler(exception_error, True)  # Log error and display failing statement

    def listActive(self, debugTypes):            
        try:
            loop = 0
            listedTypes = ''
            for debugType in debugTypes:
                if loop == 0:
                    listedTypes = listedTypes + debugType
                else:
                    listedTypes = listedTypes + ', ' + debugType
                loop += 1
            return listedTypes
        
        except Exception as exception_error:
            self.exception_handler(exception_error, True)  # Log error and display failing statement

    def runConcurrentThread(self):

        # This thread is used to handle responses from Smappee
        self.sleep(10)  # Wait before starting to process responses
        try:
            while True:
                try:
                    self.process = self.globals[QUEUES][PROCESS].get(True, 5)  # Retrieve response from Smappee
                    try:
                        self.handleSmappeeResponse(self.process[0], self.process[1], self.process[2])  # Handle response from Smappee
                    except Exception as exception_error:
                        self.exception_handler(exception_error, True)  # Log error and display failing statement
                except queue.Empty:
                    if self.stopThread:
                        raise self.StopThread  # Plugin shutdown request.
        except self.StopThread:
            # Optionally catch the StopThread exception and do any needed cleanup.
            self.logger.debug("runConcurrentThread being stopped")

    def getDeviceFactoryUiValues(self, devIdList):
        try:
            valuesDict = indigo.Dict()
            errorMsgDict = indigo.Dict()
    
            self.listItemsSmappeeLocationList = []
            self.listItemsDefinedSmappeeMainList = []
            self.listItemsDefinedSmappeeSensorList = []
            self.listItemsDefinedSmappeeApplianceList = []
            self.listItemsDefinedSmappeeActuatorList = []
            self.listItemsPotentialSmappeeSensorList = []
            self.listItemsPotentialSmappeeApplianceList = []
            self.listItemsPotentialSmappeeActuatorList = []
    
            self.monitorDeviceProcessed = False  # Used to detect if a major device electricity / electricity net / electricity saved / Solar / solar used / solar generated / gas or water has been added or removed - if so the Plugin will restart when the dialogue is closed/cancelled
    
            valuesDict["smappeeLocationList"] = 'NONE'
            valuesDict["smappeeApplianceList"] = 'NONE'
    
            valuesDict["addSmappeeElectricityDeviceEnabled"] = 'false'
            valuesDict["removeSmappeeElectricityDeviceEnabled"] = 'false'
            valuesDict["addSmappeeElectricityNetDevice"] = 'false'
            valuesDict["removeSmappeeElectricityNetDevice"] = 'false'
            valuesDict["addSmappeeElectricitySavedDevice"] = 'false'
            valuesDict["removeSmappeeElectricitySavedDevice"] = 'false'
    
            valuesDict["addSmappeeSolarDeviceEnabled"] = 'false'
            valuesDict["removeSmappeeSolarDeviceEnabled"] = 'false'
            valuesDict["addSmappeeSolarUsedDevice"] = 'false'
            valuesDict["removeSmappeeSolarUsedDevice"] = 'false'
            valuesDict["addSmappeeSolarExportedDevice"] = 'false'
            valuesDict["removeSmappeeSolarExportedDevice"] = 'false'
    
            valuesDict["addSmappeeSensorDeviceEnabled"] = 'false'
            valuesDict["addSmappeeApplianceDeviceEnabled"] = 'false'
            valuesDict["addSmappeeActuatorDeviceEnabled"] = 'false'
    
            self.deviceDetectedSmappeeElectricity = False
            self.deviceDetectedSmappeeSolar = False
            self.deviceDetectedSmappeeSensor = False
            self.deviceDetectedSmappeeAppliance = False
            self.deviceDetectedSmappeeActuator = False
    
            if len(self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID]) == 1:
                self.smappeeServiceLocationId = list(self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID].keys())[0]
                self.smappeeServiceLocationName = self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.serviceLocationId][NAME]
                valuesDict["smappeeLocationValue"] = f"{self.smappeeServiceLocationId}: {self.smappeeServiceLocationName}"
                valuesDict["hideSmappeeLocationValue"] = "false"  # TODO: Bool ?
                valuesDict["hideSmappeeLocationList"] = "true"    # TODO: Bool ?  
            else:
                self.smappeeServiceLocationId = "NONE"
                self.smappeeServiceLocationName = "Unknown Smappee Location!"
                valuesDict["hideSmappeeLocationValue"] = "true"
                valuesDict["hideSmappeeLocationList"] = "false"
    
            if len(devIdList) == 0:
                valuesDict["smappeeFunction"] = 'New...'
            else:
                valuesDict["smappeeFunction"] = 'Edit...'
    
            valuesDict = self._prepareGetSmappeeLocationList(valuesDict, devIdList)
    
            valuesDict = self._prepareSmappeeList(valuesDict, devIdList)
    
            valuesDict = self._prepareGetDefinedSmappeeSensorList(valuesDict)
            valuesDict = self._prepareGetPotentialSmappeeSensorList(valuesDict)
    
            valuesDict = self._prepareGetDefinedSmappeeApplianceList(valuesDict)
            valuesDict = self._prepareGetPotentialSmappeeApplianceList(valuesDict)
    
            valuesDict = self._prepareGetDefinedSmappeeActuatorList(valuesDict)
            valuesDict = self._prepareGetPotentialSmappeeActuatorList(valuesDict)
    
            self.logger.debug(f"getDeviceFactoryUiValues [END]: EL-Detect=[{self.deviceDetectedSmappeeElectricity}], SO-Detect=[{self.deviceDetectedSmappeeSolar}],"
                              f"  GW-Detect=[{self.deviceDetectedSmappeeSensor}], AP-Detect=[{self.deviceDetectedSmappeeAppliance}], AC-Detect=[{self.deviceDetectedSmappeeActuator}]")
    
            return valuesDict, errorMsgDict
        
        except Exception as exception_error:
            self.exception_handler(exception_error, True)  # Log error and display failing statement

    def validateDeviceFactoryUi(self, valuesDict, devIdList):

        errorsDict = indigo.Dict()
        return True, valuesDict, errorsDict

    def closedDeviceFactoryUi(self, valuesDict, userCancelled, devIdList):
        try:
            if self.monitorDeviceProcessed:
                self.logger.info("Devices changed via 'Define and Sync' - restarting SMAPPEE Plugin . . . . .")
    
                serverPlugin = indigo.server.getPlugin(self.pluginId)
                serverPlugin.restart(waitUntilDone=False)
                return
    
            if not userCancelled:
                for sensorId in sorted(
                        self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.smappeeServiceLocationId][SENSOR_IDS]):
                    if self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.smappeeServiceLocationId][SENSOR_IDS][sensorId][QUEUED_ADD]:
                        serviceLocationId = self.smappeeServiceLocationId
                        serviceLocationName = \
                            self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.smappeeServiceLocationId][NAME]
                        address = sensorId
                        name = self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.smappeeServiceLocationId][SENSOR_IDS][
                            sensorId][NAME]
                        deviceType = \
                            self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.smappeeServiceLocationId][SENSOR_IDS][
                                sensorId][DEVICE_TYPE]
    
                        self.globals[QUEUES][PROCESS].put([NEW_SENSOR, serviceLocationId, (serviceLocationName, address, name)])
    
                for applianceId in sorted(
                        self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.smappeeServiceLocationId][APPLIANCE_IDS]):
                    if self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.smappeeServiceLocationId][APPLIANCE_IDS][
                            applianceId][QUEUED_ADD]:
                        serviceLocationId = self.smappeeServiceLocationId
                        serviceLocationName = \
                            self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.smappeeServiceLocationId][NAME]
                        address = applianceId
                        name = \
                            self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.smappeeServiceLocationId][APPLIANCE_IDS][
                                applianceId][NAME]
    
                        self.globals[QUEUES][PROCESS].put([NEW_APPLIANCE, serviceLocationId, (serviceLocationName, address, name)])
    
                for actuatorId in sorted(
                        self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.smappeeServiceLocationId][ACTUATOR_IDS]):
                    if self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.smappeeServiceLocationId][ACTUATOR_IDS][
                            actuatorId][QUEUED_ADD]:
                        serviceLocationId = self.smappeeServiceLocationId
                        serviceLocationName = \
                            self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.smappeeServiceLocationId][NAME]
                        address = actuatorId
                        name = \
                            self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.smappeeServiceLocationId][ACTUATOR_IDS][
                                actuatorId][NAME]
    
                        self.globals[QUEUES][PROCESS].put([NEW_ACTUATOR, serviceLocationId, (serviceLocationName, address, name)])
    
            else:
                for sensorId in sorted(
                        self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.smappeeServiceLocationId][SENSOR_IDS]):
                    self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.smappeeServiceLocationId][SENSOR_IDS][sensorId][
                        QUEUED_ADD] = False
                    self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.smappeeServiceLocationId][SENSOR_IDS][sensorId][
                        QUEUED_REMOVE] = False
                for applianceId in sorted(
                        self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.smappeeServiceLocationId][APPLIANCE_IDS]):
                    self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.smappeeServiceLocationId][APPLIANCE_IDS][
                        applianceId][QUEUED_ADD] = False
                    self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.smappeeServiceLocationId][APPLIANCE_IDS][
                        applianceId][QUEUED_REMOVE] = False
                for actuatorId in sorted(
                        self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.smappeeServiceLocationId][ACTUATOR_IDS]):
                    self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.smappeeServiceLocationId][ACTUATOR_IDS][
                        actuatorId][QUEUED_ADD] = False
                    self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.smappeeServiceLocationId][ACTUATOR_IDS][
                        actuatorId][QUEUED_REMOVE] = False

        except Exception as exception_error:
            self.exception_handler(exception_error, True)  # Log error and display failing statement

    def _getSmappeeLocationList(self, filter="", valuesDict=None, typeId="", targetId=0):
        try:
            return self.listItemsSmappeeLocationList
    
        except Exception as exception_error:
            self.exception_handler(exception_error, True)  # Log error and display failing statement

    def _prepareGetSmappeeLocationList(self, valuesDict, devIdList):
        try:
            valuesDict["hideSmappeeLocationValue"] = "true"
            valuesDict["hideSmappeeLocationList"] = "false"
    
            listToDisplay = []
            self.locationCount = 0
            self.locationAvailableCount = 0
            for self.smappeeServiceLocationId in sorted(self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID]):
                self.serviceLocationName = self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.smappeeServiceLocationId][NAME]
                self.locationCount += 1
                if self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.smappeeServiceLocationId][ELECTRICITY_ID] == 0 and \
                        self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.smappeeServiceLocationId][SOLAR_ID] == 0:
                    listToDisplay.append((self.smappeeServiceLocationId, self.serviceLocationName))
                    self.locationAvailableCount += 1
                else:
                    self.serviceLocationName = f"Location '{self.smappeeServiceLocationId}:{self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.smappeeServiceLocationId][NAME]}' assigned to Smappee"
    
            if self.locationCount == 0:
                listToDisplay = ["NONE", "No Smappee locations found"]
            else:
                if self.locationAvailableCount == 0:
                    listToDisplay.insert(0, ("NONE", "All location(s) already assigned"))
                else:
                    listToDisplay.insert(0, ("NONE", "- Select Smappee Location -"))
    
                if self.locationCount == 1:
                    # As only one location, don't display list and skip straight to displaying value
                    valuesDict["hideSmappeeLocationValue"] = "false"
                    valuesDict["hideSmappeeLocationList"] = "true"
    
            self.listItemsSmappeeLocationList = listToDisplay
    
            return valuesDict
    
        except Exception as exception_error:
            self.exception_handler(exception_error, True)  # Log error and display failing statement

    def _smappeeLocationSelected(self, valuesDict, typeId, devIdList):
        try:
            self.deviceDetectedSmappeeElectricity = False
            self.deviceDetectedSmappeeSolar = False
            self.deviceDetectedSmappeeAppliance = False
            self.deviceDetectedSmappeeActuator = False
    
            if "smappeeLocationList" in valuesDict:
                self.smappeeServiceLocationId = valuesDict["smappeeLocationList"]
                if self.smappeeServiceLocationId != 'NONE':
                    if self.smappeeServiceLocationId in self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID]:
                        self.smappeeServiceLocationName = \
                            self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.smappeeServiceLocationId][NAME]
                        valuesDict["hideSmappeeLocationValue"] = "false"
                        valuesDict["hideSmappeeLocationList"] = "true"
    
                        valuesDict["smappeeLocationValue"] = f"{self.smappeeServiceLocationId}: {self.smappeeServiceLocationName}"
                        if self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.smappeeServiceLocationId][
                                'electricityId'] != 0:
                            self.deviceDetectedSmappeeElectricity = True
                        if self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.smappeeServiceLocationId][SOLAR_ID] != 0:
                            self.deviceDetectedSmappeeSolar = True
    
                        if self.deviceDetectedSmappeeElectricity:
                            valuesDict["removeSmappeeElectricityDeviceEnabled"] = 'true'
                        else:
                            valuesDict["addSmappeeElectricityDeviceEnabled"] = 'true'
    
                        if self.deviceDetectedSmappeeSolar:
                            valuesDict["removeSmappeeSolarDeviceEnabled"] = 'true'
                        else:
                            valuesDict["addSmappeeSolarDeviceEnabled"] = 'true'
                else:
    
                    valuesDict["hideSmappeeLocationValue"] = "true"
                    valuesDict["hideSmappeeLocationList"] = "false"
    
                    valuesDict["addSmappeeElectricityDeviceEnabled"] = 'false'
                    valuesDict["removeSmappeeElectricityDeviceEnabled"] = 'false'
                    valuesDict["addSmappeeSolarDeviceEnabled"] = 'false'
                    valuesDict["removeSmappeeSolarDeviceEnabled"] = 'false'
                    valuesDict["addSmappeeApplianceDeviceEnabled"] = 'false'
                    valuesDict["addSmappeeActuatorDeviceEnabled"] = 'false'
    
            return valuesDict
        
        except Exception as exception_error:
            self.exception_handler(exception_error, True)  # Log error and display failing statement

    def _getDefinedSmappeeElectricitySolarList(self, filter, valuesDict, devIdList):

        return self.listItemsDefinedSmappeeMainList

    def _prepareSmappeeList(self, valuesDict, devIdList):
        try:
            listToDisplay = []
    
            # Assume no main devices found ...
            valuesDict["addSmappeeElectricityDeviceEnabled"] = 'true'
            valuesDict["removeSmappeeElectricityDeviceEnabled"] = 'false'
            valuesDict["addSmappeeElectricityNetDeviceEnabled"] = 'true'
            valuesDict["removeSmappeeElectricityNetDeviceEnabled"] = 'false'
            valuesDict["addSmappeeElectricitySavedDeviceEnabled"] = 'true'
            valuesDict["removeSmappeeElectricitySavedDeviceEnabled"] = 'false'
            valuesDict["addSmappeeSolarDeviceEnabled"] = 'true'
            valuesDict["removeSmappeeSolarDeviceEnabled"] = 'false'
            valuesDict["addSmappeeSolarUsedDeviceEnabled"] = 'true'
            valuesDict["removeSmappeeSolarUsedDeviceEnabled"] = 'false'
            valuesDict["addSmappeeSolarExportedDeviceEnabled"] = 'true'
            valuesDict["removeSmappeeSolarExportedDeviceEnabled"] = 'false'
    
            smappeeMainDeviceDetected = False
            electricityDevId = 0
            electricityNetDevId = 0
            electricitySavedDevId = 0
            solarDevId = 0
            solarUsedDevId = 0
            solarExportedDevId = 0
            self.logger.debug("SMAPPEE [F-0]: _prepareSmappeeList")
    
            for dev in indigo.devices.iter("self"):
                self.logger.debug(f"SMAPPEE [F-1]: {dev.name} [devTypeId = {dev.deviceTypeId}]")
                if dev.deviceTypeId == ("smappeeElectricity" or dev.deviceTypeId == "smappeeElectricityNet" or dev.deviceTypeId == "smappeeElectricitySaved" or 
                                        dev.deviceTypeId == "smappeeSolar" or dev.deviceTypeId == "smappeeSolarUsed" or dev.deviceTypeId == "smappeeSolarExported"):
    
                    self.logger.debug(f"SMAPPEE [F-2]: {dev.name} [devTypeId = {dev.deviceTypeId}]")
    
                    if dev.pluginProps["serviceLocationId"] == self.smappeeServiceLocationId:
                        smappeeMainDeviceDetected = True
                        devName = dev.name
                        listToDisplay.append((dev.id, devName))
                        if dev.deviceTypeId == "smappeeElectricity":
                            electricityDevId = dev.id
                            valuesDict["addSmappeeElectricityDeviceEnabled"] = 'false'
                            valuesDict["removeSmappeeElectricityDeviceEnabled"] = 'true'
                        elif dev.deviceTypeId == "smappeeElectricityNet":
                            electricityNetDevId = dev.id
                            valuesDict["addSmappeeElectricityNetDeviceEnabled"] = 'false'
                            valuesDict["removeSmappeeElectricityNetDeviceEnabled"] = 'true'
                        elif dev.deviceTypeId == "smappeeElectricitySaved":
                            electricitySavedDevId = dev.id
                            valuesDict["addSmappeeElectricitySavedDeviceEnabled"] = 'false'
                            valuesDict["removeSmappeeElectricitySavedDeviceEnabled"] = 'true'
                        elif dev.deviceTypeId == "smappeeSolar":
                            solarDevId = dev.id
                            valuesDict["addSmappeeSolarDeviceEnabled"] = 'false'
                            valuesDict["removeSmappeeSolarDeviceEnabled"] = 'true'
                        elif dev.deviceTypeId == "smappeeSolarUsed":
                            solarUsedDevId = dev.id
                            valuesDict["addSmappeeSolarUsedDeviceEnabled"] = 'false'
                            valuesDict["removeSmappeeSolarUsedDeviceEnabled"] = 'true'
                        elif dev.deviceTypeId == "smappeeSolarExported":
                            solarUsedDevId = dev.id
                            valuesDict["addSmappeeSolarExportedDeviceEnabled"] = 'false'
                            valuesDict["removeSmappeeSolarExportedDeviceEnabled"] = 'true'
                        else:
                            self.logger.error(f"SMAPPEE [F-E]: {dev.name} [devTypeId = {dev.deviceTypeId}] UNKNOWN")
    
                        self.logger.debug(f"SMAPPEE [F-3]: {dev.name} [devTypeId = {dev.deviceTypeId}]")
    
            if not smappeeMainDeviceDetected:
                if len(devIdList) != 0:
                    valuesDict["addSmappeeElectricityDeviceEnabled"] = 'false'
                    valuesDict["addSmappeeSolarDeviceEnabled"] = 'false'
                    valuesDict["addSmappeeElectricityNetDeviceEnabled"] = 'false'
                    valuesDict["addSmappeeElectricitySavedDeviceEnabled"] = 'false'
                    valuesDict["addSmappeeSolarUsedDeviceEnabled"] = 'false'
                    valuesDict["addSmappeeSolarExportedDeviceEnabled"] = 'false'
            else:
                # smappeeMainDeviceDetected is True
                if len(devIdList) == 0:
                    # Must be New... but main device already exists
                    valuesDict["removeSmappeeElectricityDeviceEnabled"] = 'false'
                    valuesDict["removeSmappeeElectricityNetDeviceEnabled"] = 'false'
                    valuesDict["removeSmappeeElectricitySavedDeviceEnabled"] = 'false'
                    valuesDict["removeSmappeeSolarDeviceEnabled"] = 'false'
                    valuesDict["removeSmappeeSolarUsedDeviceEnabled"] = 'false'
                    valuesDict["removeSmappeeSolarExportedDeviceEnabled"] = 'false'
                    valuesDict["helpSmappeeElectricitySolarEnabled"] = 'true'
                else:
                    # Must be Edit...
                    if devIdList[0] != electricityDevId and devIdList[0] != electricityNetDevId and devIdList[
                        0] != electricitySavedDevId and devIdList[0] != solarDevId and devIdList[0] != solarUsedDevId and \
                            devIdList[0] != solarExportedDevId:
                        # Is Edit... but main device not selected
                        valuesDict["addSmappeeElectricityDeviceEnabled"] = 'false'
                        valuesDict["removeSmappeeElectricityDeviceEnabled"] = 'false'
                        valuesDict["addSmappeeElectricityNetDeviceEnabled"] = 'false'
                        valuesDict["removeSmappeeElectricityNetDeviceEnabled"] = 'false'
                        valuesDict["addSmappeeElectricitySavedDeviceEnabled"] = 'false'
                        valuesDict["removeSmappeeElectricitySavedDeviceEnabled"] = 'false'
                        valuesDict["addSmappeeSolarDeviceEnabled"] = 'false'
                        valuesDict["removeSmappeeSolarDeviceEnabled"] = 'false'
                        valuesDict["addSmappeeSolarUsedDeviceEnabled"] = 'false'
                        valuesDict["removeSmappeeSolarUsedDeviceEnabled"] = 'false'
                        valuesDict["addSmappeeSolarExportedDeviceEnabled"] = 'false'
                        valuesDict["removeSmappeeSolarExportedDeviceEnabled"] = 'false'
    
            if (valuesDict["addSmappeeElectricityDeviceEnabled"] == 'false' and valuesDict["removeSmappeeElectricityDeviceEnabled"] == 'false' and
                    valuesDict["addSmappeeElectricityNetDeviceEnabled"] == 'false' and valuesDict["removeSmappeeElectricityNetDeviceEnabled"] == 'false' and
                    valuesDict["addSmappeeElectricitySavedDeviceEnabled"] == 'false' and valuesDict["removeSmappeeElectricitySavedDeviceEnabled"] == 'false' and
                    valuesDict["addSmappeeSolarDeviceEnabled"] == 'false' and valuesDict["removeSmappeeSolarDeviceEnabled"] == 'false' and
                    valuesDict["addSmappeeSolarUsedDeviceEnabled"] == 'false' and valuesDict["removeSmappeeSolarUsedDeviceEnabled"] == 'false' and
                    valuesDict["addSmappeeSolarExportedDeviceEnabled"] == 'false' and valuesDict["removeSmappeeSolarExportedDeviceEnabled"] == 'false'):
                valuesDict["helpSmappeeElectricitySolarEnabled"] = 'true'
            else:
                valuesDict["helpSmappeeElectricitySolarEnabled"] = 'false'
    
            if len(listToDisplay) == 0:
                listToDisplay.append((0, "- No Smappee Devices Defined -"))
    
            self.listItemsDefinedSmappeeMainList = listToDisplay
    
            return valuesDict
    
        except Exception as exception_error:
            self.exception_handler(exception_error, True)  # Log error and display failing statement

    def _addSmappeeElectricityDevice(self, valuesDict, devIdList):
        try:
            self.monitorDeviceProcessed = True  # Forces Plugin to restart when the Device Factory dialogue is closed or cancelled 
    
            newdev = indigo.device.create(protocol=indigo.kProtocol.Plugin,
                                          address="E000",
                                          name="Smappee Electricity V2",
                                          description="Smappee",
                                          pluginId="com.autologplugin.indigoplugin.smappeecontroller",
                                          deviceTypeId="smappeeElectricity",
                                          folder=self.globals[DEVICES_FOLDER_ID],
                                          props={"SupportsEnergyMeter": True,
                                                 "SupportsEnergyMeterCurPower": True,
                                                 "serviceLocationId": self.smappeeServiceLocationId,
                                                 "serviceLocationName": self.smappeeServiceLocationName,
                                                 "optionsEnergyMeterCurPower": "last",
                                                 "hideEnergyMeterCurPower": False,
                                                 "hideEnergyMeterAccumPower": False,
                                                 "hideAlwaysOnPower": True,
                                                 "dailyStandingCharge": "0.00",
                                                 "kwhUnitCost": "0.00"})
            newdev.model = "Smappee"
            newdev.subModel = "Elec."  # Manually need to set the model and subModel names (for UI only)  # TODO: UPDATE THIS FOR INDIGO 2022.1+
            newdev.configured = True
            newdev.enabled = True
            newdev.replaceOnServer()
    
            self.setSmappeeServiceLocationIdToDevId(FUNCTION_ADD_UPDATE, 'smappeeElectricity', self.smappeeServiceLocationId, newdev.id, "", "")
    
            valuesDict["addSmappeeElectricityDeviceEnabled"] = 'false'
            valuesDict["removeSmappeeElectricityDeviceEnabled"] = 'true'
    
            devIdList.extend([newdev.id])
    
            valuesDict = self._prepareSmappeeList(valuesDict, devIdList)
    
            return valuesDict
        
        except Exception as exception_error:
            self.exception_handler(exception_error, True)  # Log error and display failing statement

    def _removeSmappeeElectricityDevice(self, valuesDict, devIdList):
        try:
            self.monitorDeviceProcessed = True  # Forces Plugin to restart when the Device Factory dialogue is closed or cancelled 
    
            for dev in indigo.devices.iter("self"):
                try:
                    if dev.deviceTypeId == "smappeeElectricity":
                        serviceLocationId = dev.pluginProps["serviceLocationId"]
                        self.setSmappeeServiceLocationIdToDevId(FUNCTION_STOP, 'smappeeElectricity', serviceLocationId, dev.id, "", "")
    
                        if dev.id in self.globals[SMAPPEES]:
                            self.globals[SMAPPEES].pop(dev.id, None)
                            self.logger.debug("_removeSmappeeElectricityDevice = POPPED")
    
                        indigo.device.delete(dev)
    
                        self.globals[CONFIG][SUPPORTS_ELECTRICITY] = False
    
                        self.logger.debug("_removeSmappeeElectricityDevice = DELETED")
                except Exception as exception_error:
                    self.logger.debug("_removeSmappeeElectricityDevice = EXCEPTION")
                    pass  # delete doesn't allow (throws) on root elem
    
            valuesDict["addSmappeeElectricityDeviceEnabled"] = 'true'
            valuesDict["removeSmappeeElectricityDeviceEnabled"] = 'false'
    
            valuesDict = self._prepareSmappeeList(valuesDict, devIdList)
    
            return valuesDict
        
        except Exception as exception_error:
            self.exception_handler(exception_error, True)  # Log error and display failing statement

    def _addSmappeeElectricityNetDevice(self, valuesDict, devIdList):
        try:
            self.monitorDeviceProcessed = True  # Forces Plugin to restart when the Device Factory dialogue is closed or cancelled 
    
            newdev = indigo.device.create(protocol=indigo.kProtocol.Plugin,
                                          address="EN00",
                                          name="Smappee Net Electricity V2",
                                          description="Smappee",
                                          pluginId="com.autologplugin.indigoplugin.smappeecontroller",
                                          deviceTypeId="smappeeElectricityNet",
                                          folder=self.globals[DEVICES_FOLDER_ID],
                                          props={"SupportsEnergyMeter": True,
                                                 "SupportsEnergyMeterCurPower": True,
                                                 "serviceLocationId": self.smappeeServiceLocationId,
                                                 "serviceLocationName": self.smappeeServiceLocationName,
                                                 "optionsEnergyMeterCurPower": "last",
                                                 "hideEnergyMeterCurNetPower": False,
                                                 "hideEnergyMeterCurZeroNetPower": True,
                                                 "hideEnergyMeterAccumNetPower": False,
                                                 "hideNoChangeEnergyMeterAccumNetPower": True})
    
            newdev.model = "Smappee"
            newdev.subModel = "E-Net"  # Manually need to set the model and subModel names (for UI only)
            newdev.configured = True
            newdev.enabled = True
            newdev.replaceOnServer()
    
            self.setSmappeeServiceLocationIdToDevId(FUNCTION_ADD_UPDATE, 'smappeeElectricityNet', self.smappeeServiceLocationId,
                                                    newdev.id, "", "")
    
            valuesDict["addSmappeeElectricityNetDeviceEnabled"] = 'false'
            valuesDict["removeSmappeeElectricityNetDeviceEnabled"] = 'true'
    
            devIdList.extend([newdev.id])
    
            valuesDict = self._prepareSmappeeList(valuesDict, devIdList)
    
            return valuesDict
        
        except Exception as exception_error:
            self.exception_handler(exception_error, True)  # Log error and display failing statement

    def _removeSmappeeElectricityNetDevice(self, valuesDict, devIdList):
        try:
            self.monitorDeviceProcessed = True  # Forces Plugin to restart when the Device Factory dialogue is closed or cancelled 
    
            for dev in indigo.devices.iter("self"):
                try:
                    if dev.deviceTypeId == "smappeeElectricityNet":
                        serviceLocationId = dev.pluginProps["serviceLocationId"]
    
                        self.setSmappeeServiceLocationIdToDevId(FUNCTION_STOP, 'smappeeElectricityNet', serviceLocationId, dev.id, "", "")
    
                        if dev.id in self.globals[SMAPPEES]:
                            self.globals[SMAPPEES].pop(dev.id, None)
                            self.logger.debug("_removeSmappeeElectricityNetDevice = POPPED")
    
                        indigo.device.delete(dev)
    
                        self.globals[CONFIG][SUPPORTS_ELECTRICITY_NET] = False
    
                        self.logger.debug("_removeSmappeeElectricityNetDevice = DELETED")
                except Exception as exception_error:
                    self.logger.debug("_removeSmappeeElectricityNetDevice = EXCEPTION")
                    pass  # delete doesn't allow (throws) on root elem
    
            valuesDict["addSmappeeElectricityNetDeviceEnabled"] = 'true'
            valuesDict["removeSmappeeElectricityNetDeviceEnabled"] = 'false'
    
            valuesDict = self._prepareSmappeeList(valuesDict, devIdList)
    
            return valuesDict
        
        except Exception as exception_error:
            self.exception_handler(exception_error, True)  # Log error and display failing statement

    def _addSmappeeElectricitySavedDevice(self, valuesDict, devIdList):
        try:
            self.monitorDeviceProcessed = True  # Forces Plugin to restart when the Device Factory dialogue is closed or cancelled 
    
            newdev = indigo.device.create(protocol=indigo.kProtocol.Plugin,
                                          address="ES00",
                                          name="Smappee Saved Electricity V2",
                                          description="Smappee",
                                          pluginId="com.autologplugin.indigoplugin.smappeecontroller",
                                          deviceTypeId="smappeeElectricitySaved",
                                          folder=self.globals[DEVICES_FOLDER_ID],
                                          props={"SupportsEnergyMeter": True,
                                                 "SupportsEnergyMeterCurPower": True,
                                                 "serviceLocationId": self.smappeeServiceLocationId,
                                                 "serviceLocationName": self.smappeeServiceLocationName,
                                                 "optionsEnergyMeterCurPower": "last",
                                                 "hideEnergyMeterCurSavedPower": False,
                                                 "hideEnergyMeterCurZeroSavedPower": True,
                                                 "hideEnergyMeterAccumSavedPower": False,
                                                 "hideNoChangeEnergyMeterAccumSavedPower": True})
    
            newdev.model = "Smappee"
            newdev.subModel = "E-Saved"  # Manually need to set the model and subModel names (for UI only)
            newdev.configured = True
            newdev.enabled = True
            newdev.replaceOnServer()
    
            self.setSmappeeServiceLocationIdToDevId(FUNCTION_ADD_UPDATE, 'smappeeElectricitySaved', self.smappeeServiceLocationId, newdev.id, "", "")
    
            valuesDict["addSmappeeElectricitySavedDeviceEnabled"] = 'false'
            valuesDict["removeSmappeeElectricitySavedDeviceEnabled"] = 'true'
    
            devIdList.extend([newdev.id])
    
            valuesDict = self._prepareSmappeeList(valuesDict, devIdList)
    
            return valuesDict
        
        except Exception as exception_error:
            self.exception_handler(exception_error, True)  # Log error and display failing statement

    def _removeSmappeeElectricitySavedDevice(self, valuesDict, devIdList):
        try:
            self.monitorDeviceProcessed = True  # Forces Plugin to restart when the Device Factory dialogue is closed or cancelled 
    
            for dev in indigo.devices.iter("self"):
                try:
                    if dev.deviceTypeId == "smappeeElectricitySaved":
                        serviceLocationId = dev.pluginProps["serviceLocationId"]
    
                        self.setSmappeeServiceLocationIdToDevId(FUNCTION_STOP, 'smappeeElectricitySaved', serviceLocationId, dev.id, "", "")
    
                        if dev.id in self.globals[SMAPPEES]:
                            self.globals[SMAPPEES].pop(dev.id, None)
                            self.logger.debug("_removeSmappeeElectricitySavedDevice = POPPED")
    
                        indigo.device.delete(dev)
    
                        self.globals[CONFIG][SUPPORTS_ELECTRICITY_SAVED] = False
    
                        self.logger.debug("_removeSmappeeElectricitySavedDevice = DELETED")
                except Exception as exception_error:
                    self.logger.debug("_removeSmappeeElectricitySavedDevice = EXCEPTION")
                    pass  # delete doesn't allow (throws) on root elem
    
            valuesDict["addSmappeeElectricitySavedDeviceEnabled"] = 'true'
            valuesDict["removeSmappeeElectricitySavedDeviceEnabled"] = 'false'
    
            valuesDict = self._prepareSmappeeList(valuesDict, devIdList)
    
            return valuesDict
        
        except Exception as exception_error:
            self.exception_handler(exception_error, True)  # Log error and display failing statement

    def _addSmappeeSolarDevice(self, valuesDict, devIdList):
        try:
            self.monitorDeviceProcessed = True  # Forces Plugin to restart when the Device Factory dialogue is closed or cancelled 
    
            newdev = indigo.device.create(protocol=indigo.kProtocol.Plugin,
                                          address="S000",
                                          name="Smappee Solar PV V2",
                                          description="Smappee",
                                          pluginId="com.autologplugin.indigoplugin.smappeecontroller",
                                          deviceTypeId="smappeeSolar",
                                          folder=self.globals[DEVICES_FOLDER_ID],
                                          props={"SupportsEnergyMeter": True,
                                                 "SupportsEnergyMeterCurPower": True,
                                                 "serviceLocationId": self.smappeeServiceLocationId,
                                                 "serviceLocationName": self.smappeeServiceLocationName,
                                                 "optionsEnergyMeterCurPower": "last",
                                                 "hideSolarMeterCurGeneration": False,
                                                 "hideZeroSolarMeterCurGeneration": True,
                                                 "hideSolarMeterAccumGeneration": False,
                                                 "hideNoChangeInSolarMeterAccumGeneration": True,
                                                 "generationRate": "0.00",
                                                 "exportType": "none",
                                                 "exportPercentage": "0.00",
                                                 "exportRate": "0.00"})
    
            newdev.model = "Smappee"
            newdev.subModel = "Solar"  # Manually need to set the model and subModel names (for UI only)
            newdev.configured = True
            newdev.enabled = True
            newdev.replaceOnServer()
    
            self.setSmappeeServiceLocationIdToDevId(FUNCTION_ADD_UPDATE, 'smappeeSolar', self.smappeeServiceLocationId, newdev.id, "", "")
    
            valuesDict["addSmappeeSolarDeviceEnabled"] = 'false'
            valuesDict["removeSmappeeSolarDeviceEnabled"] = 'true'
    
            devIdList.extend([newdev.id])
    
            valuesDict = self._prepareSmappeeList(valuesDict, devIdList)
    
            return valuesDict
        
        except Exception as exception_error:
            self.exception_handler(exception_error, True)  # Log error and display failing statement

    def _removeSmappeeSolarDevice(self, valuesDict, devIdList):
        try:
            self.monitorDeviceProcessed = True  # Forces Plugin to restart when the Device Factory dialogue is closed or cancelled 
    
            for dev in indigo.devices.iter("self"):
                try:
                    if dev.deviceTypeId == "smappeeSolar":
                        serviceLocationId = dev.pluginProps["serviceLocationId"]
    
                        self.setSmappeeServiceLocationIdToDevId(FUNCTION_STOP, 'smappeeSolar', serviceLocationId, dev.id, "", "")
    
                        if dev.id in self.globals[SMAPPEES]:
                            self.globals[SMAPPEES].pop(dev.id, None)
                            self.logger.debug("_removeSmappeeSolarDevice = POPPED")
    
                        indigo.device.delete(dev)
    
                        self.globals[CONFIG][SUPPORTS_SOLAR] = False
    
                        self.logger.debug("_removeSmappeeSolarDevice = DELETED")
                except Exception as exception_error:
                    self.logger.debug("_removeSmappeeSolarDevice = EXCEPTION")
                    pass  # delete doesn't allow (throws) on root elem
    
            valuesDict["addSmappeeSolarDeviceEnabled"] = 'true'
            valuesDict["removeSmappeeSolarDeviceEnabled"] = 'false'
    
            valuesDict = self._prepareSmappeeList(valuesDict, devIdList)
    
            return valuesDict
        
        except Exception as exception_error:
            self.exception_handler(exception_error, True)  # Log error and display failing statement

    def _addSmappeeSolarUsedDevice(self, valuesDict, devIdList):
        try:
            self.monitorDeviceProcessed = True  # Forces Plugin to restart when the Device Factory dialogue is closed or cancelled 
    
            newdev = indigo.device.create(protocol=indigo.kProtocol.Plugin,
                                          address="SU00",
                                          name="Smappee Solar PV Used V2",
                                          description="Smappee",
                                          pluginId="com.autologplugin.indigoplugin.smappeecontroller",
                                          deviceTypeId="smappeeSolarUsed",
                                          folder=self.globals[DEVICES_FOLDER_ID],
                                          props={"SupportsEnergyMeter": True,
                                                 "SupportsEnergyMeterCurPower": True,
                                                 "serviceLocationId": self.smappeeServiceLocationId,
                                                 "serviceLocationName": self.smappeeServiceLocationName,
                                                 "optionsEnergyMeterCurPower": "last",
                                                 "hideSolarUsedMeterCurGeneration": False,
                                                 "hideZeroSolarUsedMeterCurGeneration": True,
                                                 "hideSolarUsedMeterAccumGeneration": False,
                                                 "hideNoChangeInSolarUsedMeterAccumGeneration": True})
    
            newdev.model = "Smappee"
            newdev.subModel = "S-Used"  # Manually need to set the model and subModel names (for UI only)
            newdev.configured = True
            newdev.enabled = True
            newdev.replaceOnServer()
    
            self.setSmappeeServiceLocationIdToDevId(FUNCTION_ADD_UPDATE, 'smappeeSolarUsed', self.smappeeServiceLocationId, newdev.id, "", "")
    
            valuesDict["addSmappeeSolarUsedDeviceEnabled"] = 'false'
            valuesDict["removeSmappeeSolarUsedDeviceEnabled"] = 'true'
    
            devIdList.extend([newdev.id])
    
            valuesDict = self._prepareSmappeeList(valuesDict, devIdList)
    
            return valuesDict
        
        except Exception as exception_error:
            self.exception_handler(exception_error, True)  # Log error and display failing statement

    def _removeSmappeeSolarUsedDevice(self, valuesDict, devIdList):
        try:
            self.monitorDeviceProcessed = True  # Forces Plugin to restart when the Device Factory dialogue is closed or cancelled 
    
            for dev in indigo.devices.iter("self"):
                try:
                    if dev.deviceTypeId == "smappeeSolarUsed":
                        serviceLocationId = dev.pluginProps["serviceLocationId"]
    
                        self.setSmappeeServiceLocationIdToDevId(FUNCTION_STOP, 'smappeeSolarUsed', serviceLocationId, dev.id, "", "")
    
                        if dev.id in self.globals[SMAPPEES]:
                            self.globals[SMAPPEES].pop(dev.id, None)
                            self.logger.debug("_removeSmappeeSolarUsedDevice = POPPED")
    
                        indigo.device.delete(dev)
    
                        self.globals[CONFIG][SUPPORTS_SOLAR_USED] = False
    
                        self.logger.debug("_removeSmappeeSolarUsedDevice = DELETED")
                except Exception as exception_error:
                    self.logger.debug("_removeSmappeeSolarUsedDevice = EXCEPTION")
                    pass  # delete doesn't allow (throws) on root elem
    
            valuesDict["addSmappeeSolarUsedDeviceEnabled"] = 'true'
            valuesDict["removeSmappeeSolarUsedDeviceEnabled"] = 'false'
    
            valuesDict = self._prepareSmappeeList(valuesDict, devIdList)
    
            return valuesDict
        
        except Exception as exception_error:
            self.exception_handler(exception_error, True)  # Log error and display failing statement

    def _addSmappeeSolarExportedDevice(self, valuesDict, devIdList):
        try:
            self.monitorDeviceProcessed = True  # Forces Plugin to restart when the Device Factory dialogue is closed or cancelled 
    
            newdev = indigo.device.create(protocol=indigo.kProtocol.Plugin,
                                          address="SE00",
                                          name="Smappee Solar PV Exported V2",
                                          description="Smappee",
                                          pluginId="com.autologplugin.indigoplugin.smappeecontroller",
                                          deviceTypeId="smappeeSolarExported",
                                          folder=self.globals[DEVICES_FOLDER_ID],
                                          props={"SupportsEnergyMeter": True,
                                                 "SupportsEnergyMeterCurPower": True,
                                                 "serviceLocationId": self.smappeeServiceLocationId,
                                                 "serviceLocationName": self.smappeeServiceLocationName,
                                                 "optionsEnergyMeterCurPower": "last",
                                                 "hideSolarExportedMeterCurGeneration": False,
                                                 "hideZeroSolarExportedMeterCurGeneration": True,
                                                 "hideSolarExportedMeterAccumGeneration": False,
                                                 "hideNoChangeInSolarExportedMeterAccumGeneration": True})
    
            newdev.model = "Smappee"
            newdev.subModel = "S-Exported"  # Manually need to set the model and subModel names (for UI only)
            newdev.configured = True
            newdev.enabled = True
            newdev.replaceOnServer()
    
            self.setSmappeeServiceLocationIdToDevId(FUNCTION_ADD_UPDATE, 'smappeeSolarExported', self.smappeeServiceLocationId, newdev.id, "", "")
    
            valuesDict["addSmappeeSolarExportedDeviceEnabled"] = 'false'
            valuesDict["removeSmappeeSolarExportedDeviceEnabled"] = 'true'
    
            devIdList.extend([newdev.id])
    
            valuesDict = self._prepareSmappeeList(valuesDict, devIdList)
    
            return valuesDict
        
        except Exception as exception_error:
            self.exception_handler(exception_error, True)  # Log error and display failing statement

    def _removeSmappeeSolarExportedDevice(self, valuesDict, devIdList):
        try:
            self.monitorDeviceProcessed = True  # Forces Plugin to restart when the Device Factory dialogue is closed or cancelled 
    
            for dev in indigo.devices.iter("self"):
                try:
                    if dev.deviceTypeId == "smappeeSolarExported":
                        serviceLocationId = dev.pluginProps["serviceLocationId"]
    
                        self.setSmappeeServiceLocationIdToDevId(FUNCTION_STOP, 'smappeeSolarExported', serviceLocationId, dev.id, "", "")
    
                        if dev.id in self.globals[SMAPPEES]:
                            self.globals[SMAPPEES].pop(dev.id, None)
                            self.logger.debug("_removeSmappeeSolarExportedDevice = POPPED")
    
                        indigo.device.delete(dev)
    
                        self.globals[CONFIG][SUPPORTS_SOLAR_EXPORTED] = False
    
                        self.logger.debug("_removeSmappeeSolarExportedDevice = DELETED")
                except Exception as exception_error:
                    self.logger.debug("_removeSmappeeSolarExportedDevice = EXCEPTION")
                    pass  # delete doesn't allow (throws) on root elem
    
            valuesDict["addSmappeeSolarExportedDeviceEnabled"] = 'true'
            valuesDict["removeSmappeeSolarExportedDeviceEnabled"] = 'false'
    
            valuesDict = self._prepareSmappeeList(valuesDict, devIdList)
    
            return valuesDict
        
        except Exception as exception_error:
            self.exception_handler(exception_error, True)  # Log error and display failing statement

    def _getDefinedSmappeeSensorList(self, filter="", valuesDict=None, typeId="", targetId=0):
        try:
            return self.listItemsDefinedSmappeeSensorList
        
        except Exception as exception_error:
            self.exception_handler(exception_error, True)  # Log error and display failing statement

    def _prepareGetDefinedSmappeeSensorList(self, valuesDict):
        try:
            listToDisplay = []
    
            if self.smappeeServiceLocationId == '' or self.smappeeServiceLocationId == 'NONE':
                return listToDisplay
    
            for dev in indigo.devices.iter("self"):
                if dev.deviceTypeId == "smappeeSensor" and dev.pluginProps["serviceLocationId"] == self.smappeeServiceLocationId:
                    devName = dev.name
                    listToDisplay.append((str(dev.id), devName))
    
            if not listToDisplay:
                listToDisplay.append((0, '- No Sensors Defined -'))
    
            listToDisplay = sorted(listToDisplay, key=lambda x: x[1])
    
            self.listItemsDefinedSmappeeSensorList = listToDisplay
    
            return valuesDict
        
        except Exception as exception_error:
            self.exception_handler(exception_error, True)  # Log error and display failing statement

    def _getPotentialSmappeeSensorList(self, filter="", valuesDict=None, typeId="", targetId=0):
        try:
            return self.listItemsPotentialSmappeeSensorList
        
        except Exception as exception_error:
            self.exception_handler(exception_error, True)  # Log error and display failing statement

    def _prepareGetPotentialSmappeeSensorList(self, valuesDict):
        try:
            listToDisplay = []
    
            if self.smappeeServiceLocationId == '' or self.smappeeServiceLocationId == 'NONE':
                return listToDisplay
    
            for sensorId in sorted(
                    self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.smappeeServiceLocationId][SENSOR_IDS]):
                sensorName = self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.smappeeServiceLocationId][SENSOR_IDS][sensorId][NAME]
                sensorDevId = self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.smappeeServiceLocationId][SENSOR_IDS][sensorId][DEV_ID]
                queuedAdd = self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.smappeeServiceLocationId][SENSOR_IDS][sensorId][QUEUED_ADD]
                if sensorDevId == 0:
                    if queuedAdd:
                        sensorName = "QUEUED: {sensorName}"
                    listToDisplay.append((sensorId, sensorName))
    
            if not listToDisplay:
                listToDisplay.append((0, '- No Available Sensors Detected -'))
                valuesDict["addSmappeeSensorDeviceEnabled"] = 'false'
            else:
                valuesDict["addSmappeeSensorDeviceEnabled"] = 'true'
    
            listToDisplay = sorted(listToDisplay)
    
            self.listItemsPotentialSmappeeSensorList = listToDisplay
    
            return valuesDict
        
        except Exception as exception_error:
            self.exception_handler(exception_error, True)  # Log error and display failing statement

    def _addSmappeeSensorDevice(self, valuesDict, devIdList):
        try:
            for potentialSensorAddress in valuesDict["potentialSmappeeSensorList"]:
                potentialSensorAddress = str(potentialSensorAddress)
                potentialSensorName = self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.smappeeServiceLocationId][SENSOR_IDS][potentialSensorAddress][NAME]
                if not self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.smappeeServiceLocationId][SENSOR_IDS][potentialSensorAddress][QUEUED_ADD]:
                    self.setSmappeeServiceLocationIdToDevId(FUNCTION_QUEUE_ADD, 'smappeeSensor', self.smappeeServiceLocationId, 0, potentialSensorAddress, potentialSensorName)
                else:
                    self.setSmappeeServiceLocationIdToDevId(FUNCTION_DEQUEUE, 'smappeeSensor', self.smappeeServiceLocationId, 0, potentialSensorAddress, potentialSensorName)
    
            valuesDict = self._prepareGetDefinedSmappeeSensorList(valuesDict)
            valuesDict = self._prepareGetPotentialSmappeeSensorList(valuesDict)
    
            return valuesDict
        
        except Exception as exception_error:
            self.exception_handler(exception_error, True)  # Log error and display failing statement

    def _getDefinedSmappeeApplianceList(self, filter="", valuesDict=None, typeId="", targetId=0):
        try:
            return self.listItemsDefinedSmappeeApplianceList
        
        except Exception as exception_error:
            self.exception_handler(exception_error, True)  # Log error and display failing statement

    def _prepareGetDefinedSmappeeApplianceList(self, valuesDict):
        try:
            listToDisplay = []

            if self.smappeeServiceLocationId == '' or self.smappeeServiceLocationId == 'NONE':
                return listToDisplay

            for dev in indigo.devices.iter("self"):
                if dev.deviceTypeId == "smappeeAppliance" and dev.pluginProps['serviceLocationId'] == self.smappeeServiceLocationId:
                    devName = dev.name
                    listToDisplay.append((str(dev.id), devName))

            if not listToDisplay:
                listToDisplay.append((0, '- No Appliances Defined -'))

            listToDisplay = sorted(listToDisplay, key=lambda x: x[1])

            self.listItemsDefinedSmappeeApplianceList = listToDisplay

            return valuesDict

        except Exception as exception_error:
            self.exception_handler(exception_error, True)  # Log error and display failing statement

    def _getPotentialSmappeeApplianceList(self, filter="", valuesDict=None, typeId="", targetId=0):
        try:
            return self.listItemsPotentialSmappeeApplianceList

        except Exception as exception_error:
            self.exception_handler(exception_error, True)  # Log error and display failing statement

    def _prepareGetPotentialSmappeeApplianceList(self, valuesDict):
        try:
            listToDisplay = []

            if self.smappeeServiceLocationId == '' or self.smappeeServiceLocationId == 'NONE':
                return listToDisplay

            for applianceId in sorted(self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.smappeeServiceLocationId][APPLIANCE_IDS]):
                applianceName = self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.smappeeServiceLocationId][APPLIANCE_IDS][applianceId][NAME]
                applianceDevId = self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.smappeeServiceLocationId][APPLIANCE_IDS][applianceId][DEV_ID]
                queuedAdd = self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.smappeeServiceLocationId][APPLIANCE_IDS][applianceId][QUEUED_ADD]
                if applianceDevId == 0:
                    if queuedAdd:
                        applianceName = f"QUEUED: {applianceName}"
                    listToDisplay.append((applianceId, applianceName))

            if not listToDisplay:
                listToDisplay.append((0, '- No Available Appliances Detected -'))
                valuesDict["addSmappeeApplianceDeviceEnabled"] = 'false'
            else:
                valuesDict["addSmappeeApplianceDeviceEnabled"] = 'true'

            listToDisplay = sorted(listToDisplay)

            self.listItemsPotentialSmappeeApplianceList = listToDisplay

            return valuesDict

        except Exception as exception_error:
            self.exception_handler(exception_error, True)  # Log error and display failing statement

    def _addSmappeeApplianceDevice(self, valuesDict, devIdList):
        try:
            for potentialApplianceAddress in valuesDict["potentialSmappeeApplianceList"]:
                potentialApplianceAddress = str(potentialApplianceAddress)
                potentialApplianceName = \
                    self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.smappeeServiceLocationId][APPLIANCE_IDS][
                        potentialApplianceAddress][NAME]
                if not self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.smappeeServiceLocationId][APPLIANCE_IDS][
                        potentialApplianceAddress][QUEUED_ADD]:
                    self.setSmappeeServiceLocationIdToDevId(FUNCTION_QUEUE_ADD, 'smappeeAppliance', self.smappeeServiceLocationId, 0, potentialApplianceAddress, potentialApplianceName)
                else:
                    self.setSmappeeServiceLocationIdToDevId(FUNCTION_DEQUEUE, 'smappeeAppliance', self.smappeeServiceLocationId, 0, potentialApplianceAddress, potentialApplianceName)

            valuesDict = self._prepareGetDefinedSmappeeApplianceList(valuesDict)
            valuesDict = self._prepareGetPotentialSmappeeApplianceList(valuesDict)

            return valuesDict

        except Exception as exception_error:
            self.exception_handler(exception_error, True)  # Log error and display failing statement

    def _getDefinedSmappeeActuatorList(self, filter="", valuesDict=None, typeId="", targetId=0):
        try:
            return self.listItemsDefinedSmappeeActuatorList

        except Exception as exception_error:
            self.exception_handler(exception_error, True)  # Log error and display failing statement

    def _prepareGetDefinedSmappeeActuatorList(self, valuesDict):
        try:
            listToDisplay = []

            if self.smappeeServiceLocationId == '' or self.smappeeServiceLocationId == 'NONE':
                return listToDisplay

            for dev in indigo.devices.iter("self"):
                if dev.deviceTypeId == "smappeeActuator" and dev.pluginProps["serviceLocationId"] == self.smappeeServiceLocationId:
                    devName = dev.name
                    listToDisplay.append((str(dev.id), devName))

            if not listToDisplay:
                listToDisplay.append((0, '- No Actuators Defined -'))

            listToDisplay = sorted(listToDisplay, key=lambda x: x[1])

            self.listItemsDefinedSmappeeActuatorList = listToDisplay

            return valuesDict

        except Exception as exception_error:
            self.exception_handler(exception_error, True)  # Log error and display failing statement

    def _getPotentialSmappeeActuatorList(self, filter="", valuesDict=None, typeId="", targetId=0):
        try:
            return self.listItemsPotentialSmappeeActuatorList

        except Exception as exception_error:
            self.exception_handler(exception_error, True)  # Log error and display failing statement

    def _prepareGetPotentialSmappeeActuatorList(self, valuesDict):
        try:
            listToDisplay = []

            if self.smappeeServiceLocationId == '' or self.smappeeServiceLocationId == 'NONE':
                return listToDisplay

            for actuatorId in sorted(self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.smappeeServiceLocationId][ACTUATOR_IDS]):
                actuatorName = self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.smappeeServiceLocationId][ACTUATOR_IDS][actuatorId][NAME]
                actuatorDevId = self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.smappeeServiceLocationId][ACTUATOR_IDS][actuatorId][DEV_ID]
                queuedAdd = self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.smappeeServiceLocationId][ACTUATOR_IDS][actuatorId][QUEUED_ADD]
                if actuatorDevId == 0:
                    if queuedAdd:
                        actuatorName = f"QUEUED: {actuatorName}"
                    listToDisplay.append((actuatorId, actuatorName))

            if not listToDisplay:
                listToDisplay.append((0, '- No Available Actuators Detected -'))
                valuesDict["addSmappeeActuatorDeviceEnabled"] = 'false'
            else:
                valuesDict["addSmappeeActuatorDeviceEnabled"] = 'true'

            listToDisplay = sorted(listToDisplay)

            self.listItemsPotentialSmappeeActuatorList = listToDisplay

            return valuesDict

        except Exception as exception_error:
            self.exception_handler(exception_error, True)  # Log error and display failing statement

    def _addSmappeeActuatorDevice(self, valuesDict, devIdList):
        try:
            for potentialActuatorAddress in valuesDict["potentialSmappeeActuatorList"]:
                potentialActuatorAddress = str(potentialActuatorAddress)
                potentialActuatorName = self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.smappeeServiceLocationId][ACTUATOR_IDS][potentialActuatorAddress][NAME]
                if not self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.smappeeServiceLocationId][ACTUATOR_IDS][potentialActuatorAddress][QUEUED_ADD]:
                    self.setSmappeeServiceLocationIdToDevId(FUNCTION_QUEUE_ADD, 'smappeeActuator', self.smappeeServiceLocationId, 0, potentialActuatorAddress, potentialActuatorName)
                else:
                    self.setSmappeeServiceLocationIdToDevId(FUNCTION_DEQUEUE, 'smappeeActuator', self.smappeeServiceLocationId, 0, potentialActuatorAddress, potentialActuatorName)

            valuesDict = self._prepareGetDefinedSmappeeActuatorList(valuesDict)
            valuesDict = self._prepareGetPotentialSmappeeActuatorList(valuesDict)

            return valuesDict

        except Exception as exception_error:
            self.exception_handler(exception_error, True)  # Log error and display failing statement

    # def deviceUpdated(self, origDev, newDev):
    #     try:
    #         indigo.PluginBase.deviceUpdated(self, origDev, newDev)
    #
    #     except Exception as exception_error:
    #         self.exception_handler(exception_error, True)  # Log error and display failing statement
    #

    def actionControlDimmerRelay(self, action, dev):
        try:
            # ##### TURN ON ######
            if action.deviceAction == indigo.kDimmerRelayAction.TurnOn:
                # Command hardware module (dev) to turn ON here:
                self.processTurnOn(action, dev)
                dev.updateStateOnServer("onOffState", True)
                sendSuccess = True  # Assume succeeded

                if sendSuccess:
                    # If success then log that the command was successfully sent.
                    self.logger.info(f"sent '{dev.name}' 'on'")
                else:
                    # Else log failure but do NOT update state on Indigo Server.
                    self.logger.error(f"send '{dev.name}' 'on' failed")

            # ##### TURN OFF #####
            elif action.deviceAction == indigo.kDimmerRelayAction.TurnOff:
                # Command hardware module (dev) to turn OFF here:
                self.processTurnOff(action, dev)
                dev.updateStateOnServer("onOffState", False)
                sendSuccess = True  # Assume succeeded

                if sendSuccess:
                    # If success then log that the command was successfully sent.
                    self.logger.info(f"sent '{dev.name}' 'off'")

                    # And then tell the Indigo Server to update the state:
                    # dev.updateStateOnServer(key="onOffState", value=False, uiValue="off")  # £££££££££££££££££££££££££££££££££££££££££££££££££££££££££££££££££££££££££
                else:
                    # Else log failure but do NOT update state on Indigo Server.
                    self.logger.error(f"send '{dev.name}' 'off' failed")

            # ##### TOGGLE #####
            elif action.deviceAction == indigo.kDimmerRelayAction.Toggle:
                # Command hardware module (dev) to toggle here:
                self.processTurnOnOffToggle(action, dev)
                newOnState = not dev.onState
                sendSuccess = True  # Assume succeeded

                if sendSuccess:
                    # If success then log that the command was successfully sent.
                    self.logger.info(f"sent '{dev.name}' 'toggle'")

                    # And then tell the Indigo Server to update the state:
                    dev.updateStateOnServer("onOffState", newOnState)
                else:
                    # Else log failure but do NOT update state on Indigo Server.
                    self.logger.error(f"send '{dev.name}' 'toggle' failed")

        except Exception as exception_error:
            self.exception_handler(exception_error, True)  # Log error and display failing statement

    #########################
    # General Action callback
    #########################
    def actionControlGeneral(self, action, dev):
        try:
            # ##### ENERGY UPDATE #####
            if action.deviceAction == indigo.kDeviceGeneralAction.EnergyUpdate:
                # Request hardware module (dev) for its most recent meter data here:
                self.logger.info(f"sent '{dev.name}' energy update request")
                self.processUpdate(action, dev)

            # ##### ENERGY RESET #####
            elif action.deviceAction == indigo.kDeviceGeneralAction.EnergyReset:
                # Request that the hardware module (dev) reset its accumulative energy usage data here:
                self.logger.info(f"sent '{dev.name}' energy reset request")
                self.processReset(action, dev)

            # ##### STATUS REQUEST #####
            elif action.deviceAction == indigo.kDeviceGeneralAction.RequestStatus:
                # Query hardware module (dev) for its current status here:

                self.logger.info(f"sent '{dev.name}' status request")

        except Exception as exception_error:
            self.exception_handler(exception_error, True)  # Log error and display failing statement

    def processUpdate(self, pluginAction, dev):  # Dev is a Smappee
        try:
            self.logger.debug(f"'processUpdate' [{dev.pluginProps['serviceLocationId']}]")
            self.globals[QUEUES][SEND_TO_SMAPPEE].put([COMMAND_GET_CONSUMPTION, str(dev.pluginProps["serviceLocationId"])])

        except Exception as exception_error:
            self.exception_handler(exception_error, True)  # Log error and display failing statement

    def processReset(self, pluginAction, dev):  # Dev is a Smappee
        try:
            self.logger.debug(f"'processReset' [{dev.pluginProps['serviceLocationId']}]")

            if "accumEnergyTotal" in dev.states:
                if float(dev.states.get("accumEnergyTotal", 0)) != 0.0:
                    accum_energy_total = float(dev.states.get("accumEnergyTotal", 0))
                    self.logger.debug(f"'processReset' accumEnergyTotal=[{accum_energy_total}]")
                    self.globals[QUEUES][SEND_TO_SMAPPEE].put([COMMAND_RESET_CONSUMPTION, str(dev.pluginProps["serviceLocationId"])])

        except Exception as exception_error:
            self.exception_handler(exception_error, True)  # Log error and display failing statement

    def processTurnOnOffToggle(self, pluginAction, dev):  # Dev is a mappee Appliance
        try:
            self.logger.debug(f"'processTurnOnOffToggle' [{self.globals[SMAPPEE_PLUGS][dev.id][ADDRESS]}]")

            if dev.onState:
                self.processTurnOff(pluginAction, dev)
            else:
                self.processTurnOn(pluginAction, dev)

        except Exception as exception_error:
            self.exception_handler(exception_error, True)  # Log error and display failing statement

    def processTurnOn(self, pluginAction, dev):  # Dev is a Smappee Actuator
        try:
            self.logger.debug(f"'processTurnOn' [{self.globals[SMAPPEE_PLUGS][dev.id][ADDRESS]}]")

            #  Convert Address from "P012" to "12" i.e. remove leading P and leading 0's
            actuatorAddress = self.globals[SMAPPEE_PLUGS][dev.id][ADDRESS][1:].lstrip("0")

            self.globals[QUEUES][SEND_TO_SMAPPEE].put([COMMAND_ON, str(dev.pluginProps["serviceLocationId"]), actuatorAddress])

        except Exception as exception_error:
            self.exception_handler(exception_error, True)  # Log error and display failing statement

    def processTurnOff(self, pluginAction, dev):  # Dev is a Smappee Appliance
        try:
            self.logger.debug(f"'processTurnOff' [{self.globals[SMAPPEE_PLUGS][dev.id][ADDRESS]}]")

            #  Convert Address from "P012" to "12" i.e. remove leading P and leading 0's
            actuatorAddress = self.globals[SMAPPEE_PLUGS][dev.id][ADDRESS][1:].lstrip("0")

            self.globals[QUEUES][SEND_TO_SMAPPEE].put([COMMAND_OFF, str(dev.pluginProps["serviceLocationId"]), actuatorAddress])

        except Exception as exception_error:
            self.exception_handler(exception_error, True)  # Log error and display failing statement

    def handleCreateNewSensor(self, commandSentToSmappee, responseLocationId, responseFromSmappee):
        try:
            serviceLocationId = responseLocationId
            serviceLocationName, address, name = responseFromSmappee

            name = name + ' V2'

            smappeeSensorDev = indigo.device.create(protocol=indigo.kProtocol.Plugin,
                                                    address=address,
                                                    name=name,
                                                    description="Smappee Sensor",
                                                    pluginId="com.autologplugin.indigoplugin.smappeecontroller",
                                                    deviceTypeId="smappeeSensor",
                                                    folder=self.globals[DEVICES_FOLDER_ID],
                                                    props={"SupportsBatteryLevel": True,
                                                           "SupportsEnergyMeter": True,
                                                           "SupportsEnergyMeterCurPower": True,
                                                           "serviceLocationId": serviceLocationId,
                                                           "serviceLocationName": serviceLocationName,
                                                           "optionsEnergyMeterCurPower": "last",
                                                           "hideEnergyMeterCurPower": False,
                                                           "hideEnergyMeterAccumPower": False,
                                                           "dailyStandingCharge": "0.00",
                                                           "units": "kWh",
                                                           "unitCost": "0.00"})

            self.setSmappeeServiceLocationIdToDevId(FUNCTION_DEQUEUE, 'smappeeSensor', serviceLocationId, smappeeSensorDev.id, address, name)

        except Exception as exception_error:
            self.exception_handler(exception_error, True)  # Log error and display failing statement

    def handleCreateNewAppliance(self, commandSentToSmappee, responseLocationId, responseFromSmappee):
        try:
            serviceLocationId = responseLocationId
            serviceLocationName, address, name = responseFromSmappee

            name = name + ' V2'

            smappeeApplianceDev = indigo.device.create(protocol=indigo.kProtocol.Plugin,
                                                       address=address,
                                                       name=name,
                                                       description="Smappee Appliance",
                                                       pluginId="com.autologplugin.indigoplugin.smappeecontroller",
                                                       deviceTypeId="smappeeAppliance",
                                                       folder=self.globals[DEVICES_FOLDER_ID],
                                                       props={"SupportsEnergyMeter": True,
                                                              "SupportsEnergyMeterCurPower": True,
                                                              "serviceLocationId": serviceLocationId,
                                                              "serviceLocationName": serviceLocationName,
                                                              "smappeeApplianceEventLastRecordedTimestamp": 0.0,
                                                              "showApplianceEventStatus": True,
                                                              "hideApplianceSmappeeEvents": False,
                                                              "smappeeApplianceEventStatus": "NONE"})

            self.setSmappeeServiceLocationIdToDevId(FUNCTION_DEQUEUE, 'smappeeAppliance', serviceLocationId, smappeeApplianceDev.id, address, name)

        except Exception as exception_error:
            self.exception_handler(exception_error, True)  # Log error and display failing statement

    def handleCreateNewActuator(self, commandSentToSmappee, responseLocationId, responseFromSmappee):
        try:
            serviceLocationId = responseLocationId
            serviceLocationName, address, name = responseFromSmappee

            name = name + ' V2'

            smappeeActuatorDev = indigo.device.create(protocol=indigo.kProtocol.Plugin,
                                                      address=address,
                                                      name=name,
                                                      description="Smappee Actuator",
                                                      pluginId="com.autologplugin.indigoplugin.smappeecontroller",
                                                      deviceTypeId="smappeeActuator",
                                                      folder=self.globals[DEVICES_FOLDER_ID],
                                                      props={"SupportsStatusRequest": False,
                                                             "SupportsAllOff": True,
                                                             "SupportsEnergyMeter": False,
                                                             "SupportsEnergyMeterCurPower": False,
                                                             "serviceLocationId": serviceLocationId,
                                                             "serviceLocationName": serviceLocationName})

            self.setSmappeeServiceLocationIdToDevId(FUNCTION_DEQUEUE, 'smappeeActuator', serviceLocationId, smappeeActuatorDev.id, address, name)

        except Exception as exception_error:
            self.exception_handler(exception_error, True)  # Log error and display failing statement

    def validateSmappeResponse(self, commandSentToSmappee, responseLocationId, responseFromSmappee):
        try:  # TODO: METHOD NOW SUPERFLOUS ????
            if responseFromSmappee[0:12] == '<html><head>':
                message = responseFromSmappee.split('<title>')
                if len(message) == 2:
                    message = message[1].split('</title>')
                    if len(message) == 2:
                        message = message[0].replace('\n', '')
                    else:
                        message = 'Unknown Smappee Response [1] = ' + message[0:20] + ' . . .'
                else:
                    message = 'Unknown Smappee Response [2] = ' + message[0:20] + ' . . .'

                self.logger.error(f"{message}")
                return False, ''

                # Ensure that response is enclosed in square brackets '[' and ']'
            try:
                if responseFromSmappee[:1] != '[':
                    responseFromSmappee = '[' + responseFromSmappee + ']'
            except Exception as exception_error:
                self.logger.error(f"Exception detected in 'validateSmappeResponse'. Type={type(responseFromSmappee)}, Len={len(responseFromSmappee)}")
                if len(responseFromSmappee) == 3:
                    self.logger.error(f"Exception detected in 'validateSmappeResponse'. Item[1]={responseFromSmappee[0]}")
                    self.logger.error(f"Exception detected in 'validateSmappeResponse'. Item[2]={responseFromSmappee[1]}")
                    self.logger.error(f"Exception detected in 'validateSmappeResponse'. Item[3]={responseFromSmappee[2]}")
                self.exception_handler(exception_error, True)  # Log error and display failing statement
                return False, ''

            # Decode response
            decoded = json.loads(responseFromSmappee)

            # Ensure decoded is a list  
            if type(decoded) != 'list':
                decoded = decoded

            return True, decoded

        except Exception as exception_error:
            self.exception_handler(exception_error, True)  # Log error and display failing statement
            return False, ''

    def handleGetEvents(self, responseLocationId, smappeeResponse):
        try:
            for smappeeApplianceDev in indigo.devices.iter("self"):
                if smappeeApplianceDev.deviceTypeId == "smappeeAppliance":
                    smappeeApplianceDev.updateStateOnServer("smappeeApplianceEventStatus", "NONE", uiValue="No Events")
                    smappeeApplianceDev.updateStateImageOnServer(indigo.kStateImageSel.EnergyMeterOff)

            for decoding in sorted(smappeeResponse, key=lambda k: k['timestamp']):
                decoding = self.convertUnicode(decoding)
                eventTimestamp = float(decoding['timestamp'])
                activePower = decoding['activePower']
                if activePower > 0.0:
                    applianceStatus = 'ON'
                else:
                    applianceStatus = 'OFF'
                applianceId = decoding['applianceId']
                smappeeType = 'A'
                applianceIdPart = applianceId[-3:]
                applianceId = f"{smappeeType}00{applianceIdPart}"

                if applianceId in self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][responseLocationId][APPLIANCE_IDS]:
                    if self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][responseLocationId][APPLIANCE_IDS][applianceId][DEV_ID] != 0:
                        smappeeApplianceDevId = \
                            self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][responseLocationId][APPLIANCE_IDS][
                                applianceId][DEV_ID]
                        showCurrentPower = smappeeApplianceDev.pluginProps["SupportsEnergyMeterCurPower"]
                        if showCurrentPower:
                            smappeeApplianceDev.updateStateOnServer("curEnergyLevel", 0.0, uiValue="0 kWh")

                        smappeeApplianceDev = indigo.devices[smappeeApplianceDevId]

                        # Check if timestamp to be processed and if not bale out!
                        if eventTimestamp > float(
                                smappeeApplianceDev.states['smappeeApplianceEventLastRecordedTimestamp']):
                            eventTimestampStr = datetime.datetime.fromtimestamp(int(eventTimestamp / 1000)).strftime('%Y-%b-%d %H:%M:%s')
                            smappeeApplianceDev.updateStateOnServer("smappeeApplianceEventLastRecordedTimestamp",
                                                                    float(eventTimestamp), uiValue=eventTimestampStr)
                            showCurrentPower = smappeeApplianceDev.pluginProps["SupportsEnergyMeterCurPower"]
                            showOnOffState = smappeeApplianceDev.pluginProps["showApplianceEventStatus"]
                            hideEvents = smappeeApplianceDev.pluginProps["hideApplianceSmappeeEvents"]

                            activePowerStr = f"{int(activePoweri)} W"

                            if showCurrentPower:
                                smappeeApplianceDev.updateStateOnServer("curEnergyLevel", activePower, uiValue=activePowerStr)

                            if showOnOffState:
                                if applianceStatus == 'ON':
                                    smappeeApplianceDev.updateStateOnServer("smappeeApplianceEventStatus", "UP", uiValue=activePowerStr)
                                else:
                                    smappeeApplianceDev.updateStateOnServer("smappeeApplianceEventStatus", "DOWN", uiValue=activePowerStr)

                            if not hideEvents:
                                eventTimestampStr = datetime.datetime.fromtimestamp(
                                    int(eventTimestamp / 1000)).strftime('%H:%M:%S')
                                self.logger.info(f"recorded Smappee Appliance '{smappeeApplianceDev.name}' event at [{eventTimestampStr}], reading: {activePowerStr}")

                            smappeeApplianceDev.updateStateImageOnServer(indigo.kStateImageSel.EnergyMeterOn)

        except Exception as exception_error:
            self.exception_handler(exception_error, True)  # Log error and display failing statement

    def handleInitialise(self, commandSentToSmappee, responseLocationId, smappeeResponse):
        try:
            for key, value in smappeeResponse.items():
                if key == 'access_token':
                    self.globals[CONFIG][ACCESS_TOKEN] = value
                    self.logger.info("Authenticated with Smappee but initialisation still in progress ...")
                    # Now request Location info (but only if Initialise i.e. not if Refresh_Token)
                    if commandSentToSmappee == COMMAND_INITIALISE:
                        pass
                        self.globals[QUEUES][SEND_TO_SMAPPEE].put([COMMAND_GET_SERVICE_LOCATIONS])
                elif key == 'expires_in':
                    self.globals[CONFIG][TOKEN_EXPIRES_IN] = int(value)
                    preAdjustedTokenExpiresDateTimeUtc = time.mktime((indigo.server.getTime() + datetime.timedelta(seconds=self.globals[CONFIG][TOKEN_EXPIRES_IN])).timetuple())
                    # Adjust token expiry time taking account of polling time + 5 minute safety margin
                    self.globals[CONFIG][TOKEN_EXPIRES_DATETIME_UTC] = preAdjustedTokenExpiresDateTimeUtc - float(self.globals[POLLING][SECONDS] + 300)
                    self.logger.debug(f"tokenExpiresDateTimeUtc [T] : Was [{preAdjustedTokenExpiresDateTimeUtc}], is now [{self.globals[CONFIG][TOKEN_EXPIRES_DATETIME_UTC]}]")
                elif key == 'refresh_token':
                    self.globals[CONFIG][REFRESH_TOKEN] = value
                elif key == 'error':
                    self.logger.error(f"SMAPPEE ERROR DETECTED [{commandSentToSmappee}]: {value}")
                else:
                    pass  # Unknown key/value pair
                    self.logger.debug(f"Unhandled key/value pair : K=[{key}], V=[{value}]")

        except Exception as exception_error:
            self.exception_handler(exception_error, True)  # Log error and display failing statement

    def handleGetServiceLocations(self, responseLocationId, smappeeResponse):
        try:
            for key, value in smappeeResponse.items():
                if key == 'appName':
                    self.globals[CONFIG][APP_NAME] = str(value)
                elif key == 'serviceLocations':
                    for self.serviceLocationItem in value:
                        self.serviceLocationId = ""
                        self.serviceLocationName = ""
                        for key2, value2 in self.serviceLocationItem.items():
                            self.logger.debug(f"handleSmappeeResponse [H][SERVICELOCATION] -  [{key2} : {value2}]")
                            if key2 == 'serviceLocationId':
                                self.serviceLocationId = str(value2)
                            elif key2 == 'name':
                                self.serviceLocationName = str(value2)
                            else:
                                pass  # Unknown key/value pair
                        if self.serviceLocationId != "":
                            if self.serviceLocationId in self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID]:
                                self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.serviceLocationId][
                                    NAME] = self.serviceLocationName
                                if 'electricityId' not in self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.serviceLocationId]:
                                    self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.serviceLocationId][ELECTRICITY_ID] = int(0)
                                if 'electricityNetId' not in self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.serviceLocationId]:
                                    self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.serviceLocationId][ELECTRICITY_NET_ID] = int(0)
                                if 'electricitySavedId' not in self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.serviceLocationId]:
                                    self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.serviceLocationId][ELECTRICITY_SAVED_ID] = int(0)
                                if 'solarId' not in self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.serviceLocationId]:
                                    self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.serviceLocationId][SOLAR_ID] = int(0)
                                if 'solarUsedId' not in self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.serviceLocationId]:
                                    self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.serviceLocationId][SOLAR_USED_ID] = int(0)
                                if 'solarExportedId' not in self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.serviceLocationId]:
                                    self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.serviceLocationId][SOLAR_EXPORTED_ID] = int(0)
                                if 'sensorIds' not in self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.serviceLocationId]:
                                    self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.serviceLocationId][SENSOR_IDS] = dict()
                                if 'applianceIds' not in self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.serviceLocationId]:
                                    self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.serviceLocationId][APPLIANCE_IDS] = dict()
                                if 'actuatorIds' not in self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.serviceLocationId]:
                                    self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.serviceLocationId][ACTUATOR_IDS] = dict()
                            else:
                                self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.serviceLocationId] = dict()
                                self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.serviceLocationId][NAME] = self.serviceLocationName
                                self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.serviceLocationId][ELECTRICITY_ID] = int(0)
                                self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.serviceLocationId][ELECTRICITY_NET_ID] = int(0)
                                self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.serviceLocationId][ELECTRICITY_SAVED_ID] = int(0)
                                self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.serviceLocationId][SOLAR_ID] = int(0)
                                self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.serviceLocationId][SOLAR_USED_ID] = int(0)
                                self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.serviceLocationId][SOLAR_EXPORTED_ID] = int(0)
                                self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.serviceLocationId][SENSOR_IDS] = dict()
                                self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.serviceLocationId][APPLIANCE_IDS] = dict()
                                self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.serviceLocationId][ACTUATOR_IDS] = dict()

                            self.logger.debug(f"handleSmappeeResponse [HH][SERVICELOCATION]: {self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.serviceLocationId]}")

                    for self.serviceLocationId, self.serviceLocationDetails in self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID].items():
                        for smappeeDev in indigo.devices.iter("self"):
                            if smappeeDev.deviceTypeId == "smappeeElectricity":
                                self.logger.debug(f"handleSmappeeResponse [J] Checking new Smappee Service Location Id: [{self.serviceLocationId}]"
                                                  f" against known Smappee Electricity Device with Address [{smappeeDev.address}]")
                                if smappeeDev.pluginProps["serviceLocationId"] == self.serviceLocationId:
                                    if self.serviceLocationDetails[ELECTRICITY_ID] == 0:
                                        self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.serviceLocationId][ELECTRICITY_ID] = smappeeDev.id
                                    else:
                                        if self.serviceLocationDetails[ELECTRICITY_ID] != smappeeDev.id:
                                            self.logger.error(f"DUPLICATE SMAPPEE ELECTRICITY DEVICE / LOCATION. L=[{self.serviceLocationId}],"
                                                              f" D1=[{self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.serviceLocationId][ELECTRICITY_ID]}], D2=[{smappeeDev.id}]")

                            elif smappeeDev.deviceTypeId == "smappeeElectricityNet":
                                self.logger.debug(f"handleSmappeeResponse [J] Checking new Smappee Service Location Id: [{self.serviceLocationId}]"
                                                  f" against known Smappee Electricity Net Device with Address [{smappeeDev.address}]")
                                if smappeeDev.pluginProps["serviceLocationId"] == self.serviceLocationId:
                                    if self.serviceLocationDetails[ELECTRICITY_NET_ID] == 0:
                                        self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.serviceLocationId][ELECTRICITY_NET_ID] = smappeeDev.id
                                    else:
                                        if self.serviceLocationDetails[ELECTRICITY_NET_ID] != smappeeDev.id:
                                            self.logger.error(f"DUPLICATE SMAPPEE ELECTRICITY NET DEVICE / LOCATION. L=[{self.serviceLocationId}],"
                                                              f" D1=[{self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.serviceLocationId][ELECTRICITY_NET_ID]}], D2=[{smappeeDev.id}]")

                            elif smappeeDev.deviceTypeId == "smappeeElectricitySaved":
                                self.logger.debug(f"handleSmappeeResponse [J] Checking new Smappee Service Location Id: [{self.serviceLocationId}]"
                                                  f" against known Smappee Electricity Saved Device with Address [{smappeeDev.address}]")
                                if smappeeDev.pluginProps["serviceLocationId"] == self.serviceLocationId:
                                    if self.serviceLocationDetails[ELECTRICITY_SAVED_ID] == 0:
                                        self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.serviceLocationId][
                                            ELECTRICITY_SAVED_ID] = smappeeDev.id
                                    else:
                                        if self.serviceLocationDetails[ELECTRICITY_SAVED_ID] != smappeeDev.id:
                                            self.logger.error(f"DUPLICATE SMAPPEE ELECTRICITY SAVED DEVICE / LOCATION. L=[{self.serviceLocationId}],"
                                                              f" D1=[{self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.serviceLocationId][ELECTRICITY_SAVED_ID]}], D2=[{smappeeDev.id}]")

                            elif smappeeDev.deviceTypeId == "smappeeSolar":
                                self.logger.debug(f"handleSmappeeResponse [J] Checking new Smappee Service Location Id: [{self.serviceLocationId}]"
                                                  f" against known Smappee Solar Device with Address [{smappeeDev.address}]")
                                if smappeeDev.pluginProps["serviceLocationId"] == self.serviceLocationId:
                                    if self.serviceLocationDetails[SOLAR_ID] == 0:
                                        self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.serviceLocationId][SOLAR_ID] = smappeeDev.id
                                    else:
                                        if self.serviceLocationDetails[SOLAR_ID] != smappeeDev.id:
                                            self.logger.error(f"DUPLICATE SMAPPEE SOLAR DEVICE / LOCATION. L=[{self.serviceLocationId}],"
                                                              f" D1=[{self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.serviceLocationId][SOLAR_ID]}], D2=[{smappeeDev.id}]")

                            elif smappeeDev.deviceTypeId == "smappeeSolarUsed":
                                self.logger.debug(f"handleSmappeeResponse [J] Checking new Smappee Service Location Id: [{self.serviceLocationId}]"
                                                  f" against known Smappee Solar Used Device with Address [{smappeeDev.address}]")
                                if smappeeDev.pluginProps["serviceLocationId"] == self.serviceLocationId:
                                    if self.serviceLocationDetails[SOLAR_USED_ID] == 0:
                                        self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.serviceLocationId][SOLAR_USED_ID] = smappeeDev.id
                                    else:
                                        if self.serviceLocationDetails[SOLAR_USED_ID] != smappeeDev.id:
                                            self.logger.error(
                                                f"DUPLICATE SMAPPEE SOLAR USED DEVICE / LOCATION. L=[{self.serviceLocationId}],"
                                                f" D1=[{self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.serviceLocationId][SOLAR_USED_ID]}], D2=[{smappeeDev.id}]")

                            elif smappeeDev.deviceTypeId == "smappeeSolarExported":
                                self.logger.debug(f"handleSmappeeResponse [J] Checking new Smappee Service Location Id: [{self.serviceLocationId}]"
                                                  f" against known Smappee Solar Exported Device with Address [{smappeeDev.address}]")
                                if smappeeDev.pluginProps["serviceLocationId"] == self.serviceLocationId:
                                    if self.serviceLocationDetails[SOLAR_EXPORTED_ID] == 0:
                                        self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.serviceLocationId][SOLAR_EXPORTED_ID] = smappeeDev.id
                                    else:
                                        if self.serviceLocationDetails[SOLAR_EXPORTED_ID] != smappeeDev.id:
                                            self.logger.error(f"DUPLICATE SMAPPEE SOLAR EXPORTED DEVICE / LOCATION. L=[{self.serviceLocationId}],"
                                                              f" D1=[{self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.serviceLocationId][SOLAR_EXPORTED_ID]}], D2=[{smappeeDev.id}]")

                            elif smappeeDev.deviceTypeId == "smappeeSensor":
                                self.logger.debug(f"handleSmappeeResponse [J] Checking new Smappee Service Location Id: [{self.serviceLocationId}]"
                                                  f" against known Smappee Sensor Device with Address [{smappeeDev.address}]")
                                if smappeeDev.pluginProps["serviceLocationId"] == self.serviceLocationId:
                                    if smappeeDev.address in self.serviceLocationDetails[SENSOR_IDS]:
                                        if self.serviceLocationDetails[SENSOR_IDS][smappeeDev.address] == 0:
                                            self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.serviceLocationId][SENSOR_IDS][smappeeDev.address] = {'name': smappeeDev.name, 'devId': smappeeDev.id}
                                    # else:
                                    #     if self.serviceLocationDetails[SENSOR_IDS] != smappeeDev.id:
                                    #        self.logger.error(f"DUPLICATE SMAPPEE SENSOR DEVICE / LOCATION. L=[{self.serviceLocationId}],"
                                    #                                 f" D1=[{self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.serviceLocationId][ELECTRICITY_ID]}], D2=[{smappeeDev.id}]")
                                
                            elif smappeeDev.deviceTypeId == "smappeeAppliance":
                                self.logger.debug(f"handleSmappeeResponse [J] Checking new Smappee Service Location Id: [{self.serviceLocationId}]"
                                                  f" against known Smappee Appliance Device with Address [{smappeeDev.address}]")
                                if smappeeDev.pluginProps["serviceLocationId"] == self.serviceLocationId:
                                    if self.serviceLocationDetails[APPLIANCE_IDS][smappeeDev.address] == 0:
                                        self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.serviceLocationId][APPLIANCE_IDS][smappeeDev.address] = {'name': smappeeDev.name, 'devId': smappeeDev.id}
                                    # else:
                                    #     if self.serviceLocationDetails['electricity'] != smappeeDev.id:
                                    #        self.logger.error(f"DUPLICATE SMAPPEE APPLIANCE DEVICE / LOCATION. L=[{self.serviceLocationId}],"
                                    #                                 f" D1=[{self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.serviceLocationId][ELECTRICITY_ID]}], D2=[{smappeeDev.id}]")

                            elif smappeeDev.deviceTypeId == "smappeeActuator":
                                self.logger.debug(f"handleSmappeeResponse [J] Checking new Smappee Service Location Id: [{self.serviceLocationId}]"
                                                  f" against known Smappee Actuator Device with Address [{smappeeDev.address}]")
                                if smappeeDev.pluginProps["serviceLocationId"] == self.serviceLocationId:
                                    if self.serviceLocationDetails[ACTUATOR_IDS][smappeeDev.address] == 0:
                                        self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.serviceLocationId][ACTUATOR_IDS][smappeeDev.address] = {'name': smappeeDev.name, 'devId': smappeeDev.id}
                                    # else:
                                    #     if self.serviceLocationDetails['electricity'] != smappeeDev.id:
                                    #         self.logger.error(f"DUPLICATE SMAPPEE ACTUATOR DEVICE / LOCATION. L=[{self.serviceLocationId}],"
                                    #                                  f" D1=[{self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][self.serviceLocationId][ELECTRICITY_ID]}], D2=[{smappeeDev.id}]")

                        self.logger.debug(f"handleSmappeeResponse [HH][SERVICELOCATION DETAILS]: {self.serviceLocationId} = {self.serviceLocationDetails}")

                        self.globals[QUEUES][SEND_TO_SMAPPEE].put([COMMAND_GET_SERVICE_LOCATION_INFO, self.serviceLocationId])

                    if not self.globals[PLUGIN_INITIALIZED]:
                        self.logger.debug(f"handleSmappeeResponse [HH][SERVICELOCATION plugin initialised]: {self.globals[PLUGIN_INITIALIZED]}")
                        self.globals[PLUGIN_INITIALIZED] = True
                        self.logger.info("Initialisation completed.")

                        for serviceLocationId, serviceLocationDetails in self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID].items():
                            self.globals[QUEUES][SEND_TO_SMAPPEE].put([COMMAND_GET_CONSUMPTION, str(serviceLocationId)])
                            self.globals[QUEUES][SEND_TO_SMAPPEE].put([COMMAND_GET_EVENTS, str(serviceLocationId)])
                            self.globals[QUEUES][SEND_TO_SMAPPEE].put([COMMAND_GET_SENSOR_CONSUMPTION, str(serviceLocationId)])

                    else:
                        self.logger.debug(f"handleSmappeeResponse [HH][SERVICELOCATION plugin already initialised]: {self.globals[PLUGIN_INITIALIZED]}")

                    self.logger.debug(f"handleSmappeeResponse [HH][SERVICELOCATION pluginInitialised: FINAL]: {self.globals[PLUGIN_INITIALIZED]}")

                elif key == 'error':
                    self.logger.error(f"SMAPPEE ERROR DETECTED [{decodedSmappeeResponse}]: {value}")
                else:
                    # Unknown key/value pair
                    self.logger.debug(f"Unhandled key/value pair : K=[{key}], V=[{value}]")

        except Exception as exception_error:
            self.exception_handler(exception_error, True)  # Log error and display failing statement

    def handleGetServiceLocationInfo(self, responseLocationId, smappeeResponse):
        try:
            for key, value in smappeeResponse.items():
                if key == 'serviceLocationId':
                    pass
                elif key == 'name':
                    pass
                elif key == 'timezone':
                    pass
                elif key == 'lon':
                    self.longditude = value
                elif key == 'lat':
                    self.lattitude = value
                elif key == 'electricityCost':
                    self.electricityCost = float(value)
                elif key == 'electricityCurrency':
                    self.electricityCurrency = value

                elif key == 'sensors':
                    for self.sensorItem in value:
                        self.sensorName = ""
                        self.sensorId = ""
                        for key2, value2 in self.sensorItem.items():
                            self.logger.debug(f"handleSmappeeResponse [F][SENSOR] -  [{key2} : {value2}]")
                            if key2 == 'id':
                                smappeeType = 'GW'  # Sensor for Gas Water
                                value2_2 = f"0{value2}"[-2:]
                                self.sensorId = f"{smappeeType}{value2_2}"
                            elif key2 == 'name':
                                self.sensorName = value2
                            else:
                                pass  # Unknown key/value pair
                        self.logger.debug(f"handleSmappeeResponse [FF][SENSOR] - [{self.sensorId}]-[{self.sensorName}]")

                        if self.sensorId != "":
                            # At this point we have detected a Smappee Sensor Device
                            self.globals[CONFIG][SUPPORTS_SENSOR] = True

                            # Two Indigo devices can be created for each Smappee Sensor to represent the two channels (inputs) which could be measuring both Gas and Water
                            # Define a common function (below) to add an Indigo device
                            def createSensor(sensorIdModifier):
                                if self.sensorName == "":
                                    sensorName = f"[{self.sensorId}-{sensorIdModifier}] 'Unlabeled'"
                                else:
                                    sensor_name_stripped = self.sensorName.strip()
                                    sensorName = f"[{self.sensorId}-{sensorIdModifier}] {sensor_name_stripped}"

                                sensorId = self.sensorId + '-' + sensorIdModifier

                                self.logger.debug(f"handleSmappeeResponse [FF-A][SENSOR] - [{sensorId}]-[{sensorName}]")

                                if sensorId in self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][responseLocationId][SENSOR_IDS]:
                                    self.logger.debug(f"handleSmappeeResponse [FF-B][SENSOR] - [{sensorId}]-[{sensorName}]")
                                    if self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][responseLocationId]['sensorIds'][sensorId][DEV_ID] != 0:
                                        try:
                                            self.logger.debug(f"handleSmappeeResponse [FF-C][SENSOR] - [{sensorId}]-[{sensorName}]")
                                            # Can be either Gas or Water
                                            smappeeSensorDev = indigo.devices[self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][responseLocationId][SENSOR_IDS][sensorId][DEV_ID]]
                                            if not smappeeSensorDev.states['smappeeSensorOnline']:
                                                smappeeSensorDev.updateStateOnServer("smappeeSensorOnline", True, uiValue='online')
                                        except Exception as exception_error:
                                            pass
                                else:
                                    # Can be either Gas or Water
                                    self.setSmappeeServiceLocationIdToDevId(FUNCTION_ADD_UPDATE, 'smappeeSensor', responseLocationId, 0, sensorId, sensorName)
                                    self.logger.debug(f"handleSmappeeResponse [FF-D][SENSOR] - [{sensorId}]-[{sensorName}]")

                            # Now add the devices
                            createSensor('A')
                            createSensor('B')

                elif key == 'appliances':
                    for self.applianceItem in value:
                        self.applianceName = ""
                        self.applianceId = ""
                        for key2, value2 in self.applianceItem.items():
                            self.logger.debug(f"handleSmappeeResponse [F][APPLIANCE] -  [{key2} : {value2}]")
                            if key2 == 'id':
                                smappeeType = 'A'  # Appliance
                                value_2_3 = f"00{value2}"[-3:]
                                self.applianceId = f"{smappeeType}{value_2_3}"
                            elif key2 == 'name':
                                self.applianceName = str(value2)
                            elif key2 == 'type':
                                self.applianceType = value2
                            else:
                                pass  # Unknown key/value pair
                        self.logger.debug(f"handleSmappeeResponse [FF][APPLIANCE] - [{self.applianceId}]-[{self.applianceName}]-[{self.applianceType}]")

                        if self.applianceId != "":
                            if self.applianceName == "":
                                self.applianceName = f"[{self.applianceId}] 'Unlabeled'"
                            else:
                                appliance_name = self.applianceName.strip()
                                self.applianceName = f"[{self.applianceId}] {appliance_name}"

                            if self.applianceId in \
                                    self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][responseLocationId][APPLIANCE_IDS]:
                                if self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][responseLocationId][APPLIANCE_IDS][self.applianceId][DEV_ID] != 0:
                                    try:
                                        smappeeApplianceDev = indigo.devices[
                                            self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][responseLocationId][APPLIANCE_IDS][self.applianceId][DEV_ID]]
                                        if not smappeeApplianceDev.states['smappeeApplianceOnline']:
                                            smappeeApplianceDev.updateStateOnServer("smappeeApplianceOnline", True, uiValue='online')
                                    except Exception as exception_error:
                                        pass
                            else:
                                self.setSmappeeServiceLocationIdToDevId(FUNCTION_ADD_UPDATE, 'smappeeAppliance', responseLocationId, 0, self.applianceId, self.applianceName)

                elif key == 'actuators':
                    for self.actuatorItem in value:
                        self.actuatorName = ""
                        self.actuatorId = ""
                        for key2, value2 in self.actuatorItem.items():
                            self.logger.debug(f"handleSmappeeResponse [F2][ACTUATOR] -  [{key2} : {value2}]")
                            if key2 == 'id':
                                smappeeType = 'P'  # Plug
                                value_2_3 = ("00" + value2)[-3:]
                                self.actuatorId = f"{smappeeType}{value_2_3}"
                            elif key2 == 'name':
                                self.actuatorName = str(value2)
                            else:
                                pass  # Unknown key/value pair
                        self.logger.debug(f"handleSmappeeResponse [F2F][ACTUATOR] - [{self.actuatorId}]-[{self.actuatorName}]")

                        if self.actuatorId != "":
                            if self.actuatorName == "":
                                self.actuatorName = f"[{self.actuatorId}] 'Unlabeled'"
                            else:
                                actuator_name = self.actuatorName.strip()
                                self.actuatorName = f"[{self.actuatorId}] {actuator_name}"

                            if self.actuatorId in \
                                    self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][responseLocationId][ACTUATOR_IDS]:
                                if \
                                        self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][responseLocationId][ACTUATOR_IDS][self.actuatorId][DEV_ID] != 0:
                                    try:
                                        smappeeActuatorDev = indigo.devices[
                                            self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][responseLocationId][ACTUATOR_IDS][self.actuatorId][DEV_ID]]
                                        if not smappeeActuatorDev.states['smappeeActuatorOnline']:
                                            smappeeActuatorDev.updateStateOnServer("smappeeActuatorOnline", True, uiValue='online')
                                        # self.logger.debug(f"handleSmappeeResponse [J] Checking new Smappee Appliance Id: [{self.applianceId}] against known Smappee Appliance Id [{smappeeApplianceDev.address}]")
                                    except Eception:
                                        pass
                            else:
                                self.setSmappeeServiceLocationIdToDevId(FUNCTION_ADD_UPDATE, 'smappeeActuator', responseLocationId, 0, self.actuatorId, self.actuatorName)

                elif key == 'error':
                    self.logger.error(f"SMAPPEE ERROR DETECTED [{decodedSmappeeResponse}]: {value}")
                else:
                    pass  # Unknown key/value pair
                    self.logger.debug(f"Unhandled key/value pair : K=[{key}], V=[{value}]")

        except Exception as exception_error:
            self.exception_handler(exception_error, True)  # Log error and display failing statement

    def handleGetConsumption(self, commandSentToSmappee, responseLocationId, smappeeResponse):
        try:
            for key, value in smappeeResponse.items():

                if key == 'serviceLocationId':
                    pass
                elif key == 'consumptions':

                    if self.globals[CONFIG][SUPPORTS_ELECTRICITY]:
                        devElectricity = indigo.devices[self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][responseLocationId][ELECTRICITY_ID]]
                        self.lastReadingElectricityUtc = self.globals[SMAPPEES][devElectricity.id][LAST_READING_ELECTRICITY_UTC]
                        utc_ui = datetime.datetime.fromtimestamp(int(int(self.lastReadingElectricityUtc) / 1000)).strftime("%Y-%m-%d %H:%M:%S")
                        self.logger.debug(f"handleSmappeeResponse [LRU-ELECTRICITY]: {utc_ui}")

                        if not devElectricity.states['smappeeElectricityOnline']:
                            devElectricity.updateStateOnServer("smappeeElectricityOnline", True, uiValue='online')

                    if self.globals[CONFIG][SUPPORTS_ELECTRICITY_NET]:
                        devElectricityNet = indigo.devices[self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][responseLocationId][ELECTRICITY_NET_ID]]
                        self.lastReadingElectricityNetUtc = self.globals[SMAPPEES][devElectricityNet.id][LAST_READING_ELECTRICITY_NET_UTC]
                        utc_ui = datetime.datetime.fromtimestamp(int(int(self.lastReadingElectricityNetUtc) / 1000)).strftime("%Y-%m-%d %H:%M:%S")
                        self.logger.debug(f"handleSmappeeResponse [LRU-NET-ELECTRICITY]: {utc_ui}")

                        if not devElectricityNet.states['smappeeElectricityNetOnline']:
                            devElectricityNet.updateStateOnServer("smappeeElectricityNetOnline", True, uiValue='online')

                    if self.globals[CONFIG][SUPPORTS_ELECTRICITY_SAVED]:
                        devElectricitySaved = indigo.devices[self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][responseLocationId][ELECTRICITY_SAVED_ID]]
                        self.lastReadingElectricitySavedUtc = self.globals[SMAPPEES][devElectricitySaved.id][LAST_READING_ELECTRICITY_SAVED_UTC]
                        utc_ui = datetime.datetime.fromtimestamp(int(int(self.lastReadingElectricitySavedUtc) / 1000)).strftime("%Y-%m-%d %H:%M:%S")
                        self.logger.debug(f"handleSmappeeResponse [LRU-SAVED-ELECTRICITY]: {utc_ui}")

                        if not devElectricitySaved.states['smappeeElectricitySavedOnline']:
                            devElectricitySaved.updateStateOnServer("smappeeElectricitySavedOnline", True, uiValue='online')

                    if self.globals[CONFIG][SUPPORTS_SOLAR]:
                        devSolar = indigo.devices[self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][responseLocationId][SOLAR_ID]]
                        self.lastReadingSolarUtc = self.globals[SMAPPEES][devSolar.id][LAST_READING_SOLAR_UTC]
                        utc_ui = datetime.datetime.fromtimestamp(int(int(self.lastReadingSolarUtc) / 1000)).strftime("%Y-%m-%d %H:%M:%S")
                        self.logger.debug(f"handleSmappeeResponse [LRU-SOLAR]: {utc_ui}")

                        if not devSolar.states['smappeeSolarOnline']:
                            devSolar.updateStateOnServer("smappeeSolarOnline", True, uiValue='online')

                    if self.globals[CONFIG][SUPPORTS_SOLAR_USED]:
                        devSolarUsed = indigo.devices[self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][responseLocationId][SOLAR_USED_ID]]
                        self.lastReadingSolarUsedUtc = self.globals[SMAPPEES][devSolarUsed.id][LAST_READING_SOLAR_USED_UTC]
                        utc_ui = datetime.datetime.fromtimestamp(int(int(self.lastReadingSolarUsedUtc) / 1000)).strftime("%Y-%m-%d %H:%M:%S")
                        self.logger.debug(f"handleSmappeeResponse [LRU-SOLAR-USED]: {utc_ui}")

                        if not devSolarUsed.states['smappeeSolarUsedOnline']:
                            devSolarUsed.updateStateOnServer("smappeeSolarUsedOnline", True, uiValue='online')

                    if self.globals[CONFIG][SUPPORTS_SOLAR_EXPORTED]:
                        devSolarExported = indigo.devices[self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][responseLocationId][SOLAR_EXPORTED_ID]]
                        self.lastReadingSolarExportedUtc = self.globals[SMAPPEES][devSolarExported.id][LAST_READING_SOLAR_EXPORTED_UTC]
                        utc_ui = datetime.datetime.fromtimestamp(int(int(self.lastReadingSolarExportedUtc) / 1000)).strftime("%Y-%m-%d %H:%M:%S")
                        self.logger.debug(f"handleSmappeeResponse [LRU-SOLAR-EXPORTED]: {utc_ui}")

                        if not devSolarExported.states['smappeeSolarExportedOnline']:
                            devSolarExported.updateStateOnServer("smappeeSolarExportedOnline", True, uiValue='online')

                    self.timestampUtcLast = 0  # Common to both all

                    self.electricityTotal = 0.0
                    self.electricityMeanAverage = 0.0
                    self.electricityNumberOfValues = 0
                    self.electricityMinimum = 99999999.0
                    self.electricityMaximum = 0.0
                    self.electricityPrevious = 0.0

                    self.electricityNetTotal = 0.0
                    self.electricityNetMeanAverage = 0.0
                    self.electricityNetNumberOfValues = 0
                    self.electricityNetMinimum = 99999999.0
                    self.electricityNetMaximum = 0.0
                    self.electricityNetPrevious = 0.0

                    self.electricitySavedTotal = 0.0
                    self.electricitySavedMeanAverage = 0.0
                    self.electricitySavedNumberOfValues = 0
                    self.electricitySavedMinimum = 99999999.0
                    self.electricitySavedMaximum = 0.0
                    self.electricitySavedPrevious = 0.0

                    self.solarTotal = 0.0
                    self.solarMeanAverage = 0.0
                    self.solarNumberOfValues = 0
                    self.solarMinimum = 99999999.0
                    self.solarMaximum = 0.0
                    self.solarPrevious = 0.0

                    self.solarUsedTotal = 0.0
                    self.solarUsedMeanAverage = 0.0
                    self.solarUsedNumberOfValues = 0
                    self.solarUsedMinimum = 99999999.0
                    self.solarUsedMaximum = 0.0
                    self.solarUsedPrevious = 0.0

                    self.solarExportedTotal = 0.0
                    self.solarExportedMeanAverage = 0.0
                    self.solarExportedNumberOfValues = 0
                    self.solarExportedMinimum = 99999999.0
                    self.solarExportedMaximum = 0.0
                    self.solarExportedPrevious = 0.0

                    if self.globals[SQL][ENABLED]:
                        try:
                            self.globals[SQL][SQL_CONNECTION] = sql3.connect(self.globals[SQL]['db'])
                            self.globals[SQL][SQL_CURSOR] = self.globals[SQL][SQL_CONNECTION].cursor()
                        except sql3.Error as e:
                            if self.globals[SQL][SQL_CONNECTION]:
                                self.globals[SQL][SQL_CONNECTION].rollback()
                            e_args_zero = e.args[0]
                            self.logger.error(f"SMAPPEE ERROR DETECTED WITH SQL CONNECTION: {e_args_zero}")

                            self.globals[SQL][ENABLED] = False  # Disable SQL processing

                    for self.readingItem in value:
                        # process each reading entry

                        self.timestampDetected = False

                        self.electricityDetected = False
                        self.electricityNetDetected = False
                        self.electricitySavedDetected = False
                        self.solarDetected = False
                        self.solarUsedDetected = False
                        self.solarExportedDetected = False

                        self.alwaysOnDetected = False

                        self.timestampUtc = 0

                        self.electricity = 0.0
                        self.electricityNet = 0.0
                        self.electricitySaved = 0.0
                        self.solar = 0.0
                        self.solarUsed = 0.0
                        self.solarExported = 0.0

                        self.alwaysOn = 0.0

                        self.electricityLast = 0.0
                        self.electricityNetLast = 0.0
                        self.electricitySavedLast = 0.0
                        self.solarLast = 0.0
                        self.solarUsedLast = 0.0
                        self.solarExportedLast = 0.0

                        for key2, value2 in self.readingItem.items():
                            if key2 == "timestamp":
                                self.timestampDetected = True
                                self.timestampUtc = value2
                                self.timestampUtcLast = value2
                            elif key2 == "consumption":
                                self.electricityDetected = True
                                self.electricity = value2
                            elif key2 == "solar":
                                self.solarDetected = True
                                self.solar = value2
                            elif key2 == "alwaysOn":
                                self.alwaysOnDetected = True
                                self.alwaysOn = value2
                            else:
                                pass  # Unknown key/value pair

                        if self.electricityDetected and self.solarDetected:
                            self.electricityNetDetected = True
                            self.electricitySavedDetected = True
                            self.solarUsedDetected = True
                            self.solarExportedDetected = True

                            # Calculate:
                            #   Net Electricity used
                            #   Saved Electricity (i.e. because solar being used)
                            #   Solar Used
                            #   Solar Exported

                            if self.electricity > self.solar:
                                self.electricityNet = self.electricity - self.solar
                                self.electricitySaved = self.solar
                            else:
                                self.electricityNet = 0.0
                                self.electricitySaved = self.electricity
                            self.solarUsed = self.electricity - self.electricityNet
                            if self.solar > self.electricity:
                                self.solarExported = self.solar - self.electricity
                            else:
                                self.solarExported = 0.0

                            if self.timestampDetected:
                                ts = datetime.datetime.fromtimestamp(int(int(self.timestampUtc) / 1000)).strftime("%Y-%m-%d %H:%M:%S")
                            else:
                                ts = "NOT DETECTED"
                            self.logger.debug(f"ELECTRICITY/SOLAR: DateTime={ts}, Electricity={self.electricity},"
                                              f" Net={self.electricityNet}, Saved={self.electricitySaved},"
                                              f" Solar={self.solar}, Solar Used={self.solarUsed}, Solar Exported={self.solarExported}")

                        if self.timestampDetected:
                            if self.globals[CONFIG][SUPPORTS_ELECTRICITY]:
                                if self.timestampUtc > self.lastReadingElectricityUtc:
                                    if self.electricityDetected:
                                        self.electricityNumberOfValues += 1
                                        self.electricityTotal += self.electricity
                                        if self.electricity < self.electricityMinimum:
                                            self.electricityMinimum = self.electricity
                                        if self.electricity > self.electricityMaximum:
                                            self.electricityMaximum = self.electricity
                                        self.electricityLast = self.electricity
                                elif self.timestampUtc == self.lastReadingElectricityUtc:
                                    self.electricityPrevious = 0.0
                                    if self.electricityDetected:
                                        self.electricityPrevious = self.electricity * 12

                            if self.globals[CONFIG][SUPPORTS_ELECTRICITY] and self.globals[CONFIG][SUPPORTS_ELECTRICITY_NET] and self.globals[CONFIG][SUPPORTS_SOLAR]:
                                # Net makes no sense if electricity and solar not measured
                                if self.timestampUtc > self.lastReadingElectricityNetUtc:
                                    if self.electricityNetDetected:
                                        self.electricityNetNumberOfValues += 1
                                        self.electricityNetTotal += self.electricityNet
                                        if self.electricityNet < self.electricityNetMinimum:
                                            self.electricityNetMinimum = self.electricityNet
                                        if self.electricityNet > self.electricityNetMaximum:
                                            self.electricityNetMaximum = self.electricityNet
                                        self.electricityNetLast = self.electricityNet
                                elif self.timestampUtc == self.lastReadingElectricityNetUtc:
                                    self.electricityNetPrevious = 0.0
                                    if self.electricityNetDetected:
                                        self.electricityNetPrevious = self.electricityNet * 12

                                lrutc = datetime.datetime.fromtimestamp(int(int(self.lastReadingElectricityNetUtc) / 1000)).strftime("%Y-%m-%d %H:%M:%S")
                                tsutc = datetime.datetime.fromtimestamp(int(int(self.timestampUtc) / 1000)).strftime("%Y-%m-%d %H:%M:%S")
                                self.logger.debug(f"'NET'.            LRUTC: {lrutc}, TSUTC: {tsutc}, Net: {self.electricityNet}")

                            if self.globals[CONFIG][SUPPORTS_ELECTRICITY] and self.globals[CONFIG][SUPPORTS_ELECTRICITY_SAVED] and self.globals[CONFIG][SUPPORTS_SOLAR]:
                                # Saved makes no sense if electricity and solar not measured
                                if self.timestampUtc > self.lastReadingElectricitySavedUtc:
                                    if self.electricitySavedDetected:
                                        self.electricitySavedNumberOfValues += 1
                                        self.electricitySavedTotal += self.electricitySaved
                                        if self.electricitySaved < self.electricitySavedMinimum:
                                            self.electricitySavedMinimum = self.electricitySaved
                                        if self.electricitySaved > self.electricitySavedMaximum:
                                            self.electricitySavedMaximum = self.electricitySaved
                                        self.electricitySavedLast = self.electricitySaved
                                elif self.timestampUtc == self.lastReadingElectricitySavedUtc:
                                    self.electricitySavedPrevious = 0.0
                                    if self.electricitySavedDetected:
                                        self.electricitySavedPrevious = self.electricitySaved * 12

                                lrutc = datetime.datetime.fromtimestamp(int(int(self.lastReadingElectricitySavedUtc) / 1000)).strftime("%Y-%m-%d %H:%M:%S")
                                tsutc = datetime.datetime.fromtimestamp(int(int(self.timestampUtc) / 1000)).strftime("%Y-%m-%d %H:%M:%S")
                                self.logger.debug(f"'SAVED'.          LRUTC: {lrutc}, TSUTC: {tsutc}, Saved: {self.electricitySaved}")

                            if self.globals[CONFIG][SUPPORTS_SOLAR]:
                                if self.timestampUtc > self.lastReadingSolarUtc:
                                    if self.solarDetected:
                                        self.solarNumberOfValues += 1
                                        self.solarTotal += self.solar
                                        if self.solar < self.solarMinimum:
                                            self.solarMinimum = self.solar
                                        if self.solar > self.solarMaximum:
                                            self.solarMaximum = self.solar
                                        self.solarLast = self.solar
                                elif self.timestampUtc == self.lastReadingSolarUtc:
                                    self.solarPrevious = 0.0
                                    if self.solarDetected:
                                        self.solarPrevious = self.solar * 12
                                lrutc = datetime.datetime.fromtimestamp(int(int(self.lastReadingSolarUtc) / 1000)).strftime("%Y-%m-%d %H:%M:%S")
                                tsutc = datetime.datetime.fromtimestamp(int(int(self.timestampUtc) / 1000)).strftime("%Y-%m-%d %H:%M:%S")
                                self.logger.debug(f"'SOLAR'.          LRUTC: {lrutc}, TSUTC: {tsutc}, Solar: {self.solar}")

                            if self.globals[CONFIG][SUPPORTS_ELECTRICITY] and self.globals[CONFIG][SUPPORTS_SOLAR_USED]:
                                # Used (Solar) makes no sense if electricity and solar not measured
                                if self.timestampUtc > self.lastReadingSolarUsedUtc:
                                    if self.solarUsedDetected:
                                        self.solarUsedNumberOfValues += 1
                                        self.solarUsedTotal += self.solarUsed
                                        self.solarUsedLast = self.solarUsed
                                elif self.timestampUtc == self.lastReadingSolarUsedUtc:
                                    self.solarUsedPrevious = 0.0
                                    if self.solarUsedDetected:
                                        self.solarUsedPrevious = self.solarUsed * 12

                                lrutc = datetime.datetime.fromtimestamp(int(int(self.lastReadingSolarUsedUtc) / 1000)).strftime("%Y-%m-%d %H:%M:%S")
                                tsutc = datetime.datetime.fromtimestamp(int(int(self.timestampUtc) / 1000)).strftime("%Y-%m-%d %H:%M:%S")
                                self.logger.debug(f"'SOLAR USED'.     LRUTC: {lrutc}, TSUTC: {tsutc}, Solar Used: {self.solarUsed}")

                            if self.globals[CONFIG][SUPPORTS_SOLAR_EXPORTED]:
                                if self.timestampUtc > self.lastReadingSolarExportedUtc:
                                    if self.solarExportedDetected:
                                        self.solarExportedNumberOfValues += 1
                                        self.solarExportedTotal += self.solarExported
                                        self.solarExportedLast = self.solarExported
                                elif self.timestampUtc == self.lastReadingSolarExportedUtc:
                                    self.solarExportedPrevious = 0.0
                                    if self.solarExportedDetected:
                                        self.solarExportedPrevious = self.solarExported * 12

                                lrutc = datetime.datetime.fromtimestamp(int(int(self.lastReadingSolarExportedUtc) / 1000)).strftime("%Y-%m-%d %H:%M:%S")
                                tsutc = datetime.datetime.fromtimestamp(int(int(self.timestampUtc) / 1000)).strftime("%Y-%m-%d %H:%M:%S")
                                self.logger.debug(f"'SOLAR EXPORTED'. LRUTC: {lrutc}, TSUTC: {tsutc}, Solar Exported: {self.solarExported}")

                            if self.globals[SQL][ENABLED]:
                                insertSql = 'NO SQL SET-UP YET'
                                try:
                                    readingTime = str(int(self.timestampUtc / 1000))  # Remove micro seconds
                                    readingYYYYMMDDHHMMSS = datetime.datetime.fromtimestamp(int(readingTime)).strftime("%Y-%m-%d %H:%M:%S")
                                    readingYYYYMMDD = readingYYYYMMDDHHMMSS[0:10]
                                    readingHHMMSS = readingYYYYMMDDHHMMSS[-8:]
                                    elec = str(int(self.electricity * 10))
                                    elecNet = str(int(self.electricityNet * 10))
                                    elecSaved = str(int(self.electricitySaved * 10))
                                    alwaysOn = str(int(self.alwaysOn * 10))
                                    solar = str(int(self.solar * 10))
                                    solarUsed = str(int(self.solarUsed * 10))
                                    solarExported = str(int(self.solarExported * 10))
                                    insertSql = f"""
                                    INSERT OR IGNORE INTO readings (reading_time, reading_YYYYMMDD, reading_HHMMSS, elec, elec_net, elec_saved, always_on, solar, solar_used, solar_exported)
                                                 VALUES ({readingTime}, '{readingYYYYMMDD}', '{readingHHMMSS}', {elec}, {elecNet}, {elecSaved}, {alwaysOn}, {solar}, {solarUsed}, {solarExported});
                                    """  # noqa
                                    self.globals[SQL][SQL_CURSOR].executescript(insertSql)
                                except sql3.Error as e:
                                    if self.globals[SQL][SQL_CONNECTION]:
                                        self.globals[SQL][SQL_CONNECTION].rollback()
                                    e_args_zero = e.args[0]
                                    self.logger.error(f"SMAPPEE ERROR DETECTED WITH SQL INSERT: {e_args_zero}, SQL=[{insertSql}]")
                                    if self.globals[SQL][SQL_CONNECTION]:
                                        self.globals[SQL][SQL_CONNECTION].close()

                                    self.globals[SQL][ENABLED] = False  # Disable SQL processing

                    if self.globals[SQL][ENABLED]:
                        try:
                            self.globals[SQL][SQL_CONNECTION].commit()
                        except sql3.Error as e:
                            if self.globals[SQL][SQL_CONNECTION]:
                                self.globals[SQL][SQL_CONNECTION].rollback()
                            e_args_zero = e.args[0]
                            self.logger.error(f"SMAPPEE ERROR DETECTED WITH SQL COMMIT: {e_args_zero}")
                            self.globals[SQL][ENABLED] = False  # Disable SQL processing
                        finally:
                            if self.globals[SQL][SQL_CONNECTION]:
                                self.globals[SQL][SQL_CONNECTION].close()

                                # reading entries processing complete

                    if self.electricityNumberOfValues > 0:
                        self.electricityMeanAverage = self.electricityTotal / self.electricityNumberOfValues

                    if self.electricityNetNumberOfValues > 0:
                        self.electricityNetMeanAverage = self.electricityNetTotal / self.electricityNetNumberOfValues

                    if self.electricitySavedNumberOfValues > 0:
                        self.electricitySavedMeanAverage = self.electricitySavedTotal / self.electricitySavedNumberOfValues

                    if self.solarNumberOfValues > 0:
                        self.solarMeanAverage = self.solarTotal / self.solarNumberOfValues

                    if self.solarUsedNumberOfValues > 0:
                        self.solarUsedMeanAverage = self.solarUsedTotal / self.solarUsedNumberOfValues

                    if self.solarExportedNumberOfValues > 0:
                        self.solarExportedMeanAverage = self.solarExportedTotal / self.solarExportedNumberOfValues

                    self.logger.debug(f"READINGS - ELECTRICITY:       Num=[{self.electricityNumberOfValues}], Total=[{self.electricityTotal}],"
                                      f" MEAN=[{self.electricityMeanAverage}], MIN=[{self.electricityMinimum}], MAX=[{self.electricityMaximum}],"
                                      f" Last=[{self.electricityLast}]")
                    self.logger.debug(f"READINGS - ELECTRICITY NET:   Num=[{self.electricityNetNumberOfValues}], Total=[{self.electricityNetTotal}],"
                                      f" MEAN=[{self.electricityNetMeanAverage}], MIN=[{self.electricityNetMinimum}], MAX=[{self.electricityNetMaximum}],"
                                      f" Last=[{self.electricityNetLast}]")
                    self.logger.debug(f"READINGS - ELECTRICITY SAVED: Num=[{self.electricitySavedNumberOfValues}], Total=[{self.electricitySavedTotal}],"
                                      f" MEAN=[{self.electricitySavedMeanAverage}], MIN=[{self.electricitySavedMinimum}], MAX=[{self.electricitySavedMaximum}],"
                                      f" Last=[{self.electricitySavedLast}]")
                    self.logger.debug(f"READINGS - SOLAR:             Num=[{self.solarNumberOfValues}], Total=[{self.solarTotal}],"
                                      f" MEAN=[{self.solarMeanAverage}], MIN=[{self.solarMinimum}], MAX=[{self.solarMaximum}],"
                                      f" Lastt=[{self.solarLast}]")
                    self.logger.debug(f"READINGS - SOLAR USED:        Num=[{self.solarUsedNumberOfValues}], Total=[{self.solarUsedTotal}],"
                                      f" MEAN=[{self.solarUsedMeanAverage}], MIN=[{ self.solarUsedMinimum}], MAX=[{self.solarUsedMaximum}],"
                                      f" Last=[{self.solarUsedLast}]")
                    self.logger.debug(f"READINGS - SOLAR EXPORTED:    Num=[{self.solarExportedNumberOfValues}], Total=[{self.solarExportedTotal}],"
                                      f" MEAN=[{self.solarExportedMeanAverage}], MIN=[{self.solarExportedMinimum}], MAX=[{self.solarExportedMaximum}],"
                                      f" Last=[{self.solarExportedLast}]")

                    savedElectricityCalculated = False  # Used to determine whether Solar PV FIT + Elec savings can be calculated
                    #   Gets set to True if Elec saving calculated so that it can be added to Solar Total Income
                    #   to derive and update state: dailyTotalPlusSavedElecIncome

                    if self.globals[CONFIG][SUPPORTS_ELECTRICITY]:
                        if "curEnergyLevel" in devElectricity.states:
                            if commandSentToSmappee == COMMAND_RESET_CONSUMPTION:

                                self.globals[SMAPPEES][devElectricity.id][CURRENT_ENERGY_LEVEL] = 0.0
                                self.globals[SMAPPEES][devElectricity.id][ACCUMULATED_ENERGY_TOTAL] = 0.0
                                wattStr = f"{self.globals[SMAPPEES][devElectricity.id][CURRENT_ENERGY_LEVEL]:3.0f} Watts"
                                devElectricity.updateStateOnServer("curEnergyLevel", self.globals[SMAPPEES][devElectricity.id][CURRENT_ENERGY_LEVEL], uiValue=wattStr)
                                devElectricity.updateStateImageOnServer(indigo.kStateImageSel.EnergyMeterOff)

                            self.options = devElectricity.pluginProps["optionsEnergyMeterCurPower"]  # mean, minimum, maximum, last

                            if self.options == 'mean':  # mean, minimum, maximum, last
                                if self.electricityNumberOfValues > 0:
                                    watts = (self.electricityMeanAverage * 60) / 5
                                else:
                                    lastReadingElectricityUtc_minus_600000 = self.lastReadingElectricityUtc - 600000
                                    self.logger.debug(f"ELECTRICITY: CL=[{self.electricityLast}], UTCL=[{self.timestampUtcLast}],"
                                                      f" LRUTC=[{self.lastReadingElectricityUtc}], LRUTC600=[{lastReadingElectricityUtc_minus_600000}]")
                                    if self.electricityLast > 0.0 and self.timestampUtcLast != 0 and self.timestampUtcLast > (
                                            self.lastReadingElectricityUtc - 600000):
                                        watts = self.electricityLast * 12
                                    else:
                                        watts = 0.0
                            elif self.options == 'minimum':
                                if self.electricityNumberOfValues > 0:
                                    watts = self.electricityMinimum * 12
                                else:
                                    lastReadingElectricityUtc_minus_600000 = self.lastReadingElectricityUtc - 600000
                                    self.logger.debug(f"ELECTRICITY: CL=[{self.electricityLast}], UTCL=[{self.timestampUtcLast}],"
                                                      f" LRUTC=[{self.lastReadingElectricityUtc}], LRUTC600=[{lastReadingElectricityUtc_minus_600000}]")
                                    if self.electricityLast > 0.0 and self.timestampUtcLast != 0 and self.timestampUtcLast > (self.lastReadingElectricityUtc - 600000):
                                        watts = self.electricityLast * 12
                                    else:
                                        watts = 0.0
                            elif self.options == 'maximum':
                                if self.electricityNumberOfValues > 0:
                                    watts = self.electricityMaximum * 12
                                else:
                                    lastReadingElectricityUtc_minus_600000 = self.lastReadingElectricityUtc - 600000
                                    self.logger.debug(f"ELECTRICITY: CL=[{self.electricityLast}], UTCL=[{self.timestampUtcLast}],"
                                                      f" LRUTC=[{self.lastReadingElectricityUtc}], LRUTC600=[{lastReadingElectricityUtc_minus_600000}]")
                                    if self.electricityLast > 0.0 and self.timestampUtcLast != 0 and self.timestampUtcLast > (self.lastReadingElectricityUtc - 600000):
                                        watts = self.electricityLast * 12
                                    else:
                                        watts = 0.0
                            else:  # Assume last
                                lastReadingElectricityUtc_minus_600000 = self.lastReadingElectricityUtc - 600000
                                self.logger.debug(f"ELECTRICITY: CL=[{self.electricityLast}], UTCL=[{self.timestampUtcLast}],"
                                                  f" LRUTC=[{self.lastReadingElectricityUtc}], LRUTC600=[{lastReadingElectricityUtc_minus_600000}]")
                                if self.electricityLast > 0.0 and self.timestampUtcLast != 0 and self.timestampUtcLast > (self.lastReadingElectricityUtc - 600000):
                                    watts = self.electricityLast * 12
                                else:
                                    watts = 0.0

                            if watts == 0.0:
                                watts = self.electricityPrevious

                            wattsStr = f"{int(watts)} Watts"
                            if not self.globals[SMAPPEES][devElectricity.id][HIDE_ENERGY_METER_CURRENT_POWER]:
                                self.logger.info(f"received '{devElectricity.name}' power load reading: {wattsStr}")

                            devElectricity.updateStateOnServer("curEnergyLevel", watts, uiValue=wattsStr)
                            devElectricity.updateStateImageOnServer(indigo.kStateImageSel.EnergyMeterOn)

                        if "accumEnergyTotal" in devElectricity.states:
                            if commandSentToSmappee == COMMAND_RESET_CONSUMPTION:
                                self.globals[SMAPPEES][devElectricity.id][ACCUMULATED_ENERGY_TOTAL] = 0.0
                                wattStr = f"{self.globals[SMAPPEES][devElectricity.id][ACCUMULATED_ENERGY_TOTAL]:3.0f} Watts"
                                devElectricity.updateStateOnServer("accumEnergyTotal", self.globals[SMAPPEES][devElectricity.id][ACCUMULATED_ENERGY_TOTAL], uiValue=wattStr)

                            kwh = float(devElectricity.states.get("accumEnergyTotal", 0))
                            kwh += float(self.electricityTotal / 1000.0)
                            kwhStr = f"{kwh:0.3f} kWh"
                            kwhUnitCost = self.globals[SMAPPEES][devElectricity.id][KWH_UNIT_COST]
                            dailyStandingCharge = self.globals[SMAPPEES][devElectricity.id][DAILY_STANDING_CHARGE]

                            amountGross = 0.00
                            amountGrossStr = "0.00"
                            if kwhUnitCost > 0.00:
                                amountGross = (dailyStandingCharge + (kwh * kwhUnitCost))
                                amountGrossReformatted = float(str(f"{amountGross:0.2f}"))
                                amountGrossStr = f"{amountGross:0.2f} {self.globals[SMAPPEES][devElectricity.id][CURRENCY_CODE]}"
                                devElectricity.updateStateOnServer("dailyTotalCost", amountGrossReformatted, uiValue=amountGrossStr)

                            if not self.globals[SMAPPEES][devElectricity.id][HIDE_ENERGY_METER_ACCUMULATED_POWER]:
                                if kwhUnitCost == 0.00 or self.globals[SMAPPEES][devElectricity.id][HIDE_ENERGY_METER_ACCUMULATED_POWER_COST]:
                                    self.logger.info(f"received '{devElectricity.name}' energy total: { kwhStr}")
                                else:
                                    self.logger.info(f"received '{devElectricity.name}' energy total: {kwhStr} (Gross {amountGrossStr})")

                            kwhReformatted = float(f"{kwh:0.3f}")
                            devElectricity.updateStateOnServer("accumEnergyTotal", kwhReformatted, uiValue=kwhStr)

                        if "alwaysOn" in devElectricity.states:
                            wattsAlwaysOn = self.alwaysOn
                            wattsAlwaysOnStr = f"{int(wattsAlwaysOn)} Watts"
                            if not self.globals[SMAPPEES][devElectricity.id][HIDE_ALWAYS_ON_POWER]:
                                self.logger.info(f"received '{devElectricity.name}' always-on reading: {wattsAlwaysOnStr}")
                            devElectricity.updateStateOnServer("alwaysOn", wattsAlwaysOn, uiValue=wattsAlwaysOnStr)

                        self.globals[SMAPPEES][devElectricity.id][LAST_READING_ELECTRICITY_UTC] = self.timestampUtc

                    if self.globals[CONFIG][SUPPORTS_ELECTRICITY_NET]:
                        if "curEnergyLevel" in devElectricityNet.states:
                            if commandSentToSmappee == COMMAND_RESET_CONSUMPTION:
                                self.globals[SMAPPEES][devElectricityNet.id][CURRENT_ENERGY_LEVEL] = 0.0
                                self.globals[SMAPPEES][devElectricityNet.id][ACCUMULATED_ENERGY_TOTAL] = 0.0
                                wattStr = f"{self.globals[SMAPPEES][devElectricityNet.id][CURRENT_ENERGY_LEVEL]:3.0f} Watts"
                                devElectricityNet.updateStateOnServer("curEnergyLevel", self.globals[SMAPPEES][devElectricityNet.id][CURRENT_ENERGY_LEVEL], uiValue=wattStr)
                                devElectricityNet.updateStateImageOnServer(indigo.kStateImageSel.EnergyMeterOff)

                            self.options = devElectricityNet.pluginProps["optionsEnergyMeterCurPower"]

                            if self.options == 'mean':  # mean, minimum, maximum, last
                                if self.electricityNetNumberOfValues > 0:
                                    wattsNet = (self.electricityNetMeanAverage * 60) / 5
                                else:
                                    lastReadingElectricityNetUtc_minus_600000 = self.lastReadingElectricityNetUtc - 600000
                                    self.logger.debug(f"ELECTRICITY NET: CL=[{self.electricityNetLast}], UTCL=[{self.timestampUtcLast}],"
                                                      f" LRUTC=[{self.lastReadingElectricityNetUtc}], LRUTC600=[{lastReadingElectricityNetUtc_minus_600000}]")
                                    if self.electricityNetLast > 0.0 and self.timestampUtcLast != 0 and self.timestampUtcLast > (
                                            self.lastReadingElectricityNetUtc - 600000):
                                        wattsNet = self.electricityNetLast * 12
                                    else:
                                        wattsNet = 0.0
                            elif self.options == 'minimum':
                                if self.electricityNetNumberOfValues > 0:
                                    wattsNet = self.electricityNetMinimum * 12
                                else:
                                    lastReadingElectricityNetUtc_minus_600000 = self.lastReadingElectricityNetUtc - 600000
                                    self.logger.debug(f"ELECTRICITY NET: CL=[{self.electricityNetLast}], UTCL=[{self.timestampUtcLast}],"
                                                      f" LRUTC=[{self.lastReadingElectricityNetUtc}], LRUTC600=[{lastReadingElectricityNetUtc_minus_600000}]")
                                    if self.electricityNetLast > 0.0 and self.timestampUtcLast != 0 and self.timestampUtcLast > (
                                            self.lastReadingElectricityNetUtc - 600000):
                                        wattsNet = self.electricityNetLast * 12
                                    else:
                                        wattsNet = 0.0
                            elif self.options == 'maximum':
                                if self.electricityNetNumberOfValues > 0:
                                    wattsNet = self.electricityNetMaximum * 12
                                else:
                                    lastReadingElectricityNetUtc_minus_600000 = self.lastReadingElectricityNetUtc - 600000
                                    self.logger.debug(f"ELECTRICITY NET: CL=[{self.electricityNetLast}], UTCL=[{self.timestampUtcLast}],"
                                                      f" LRUTC=[{self.lastReadingElectricityNetUtc}], LRUTC600=[{lastReadingElectricityNetUtc_minus_600000}]")
                                    if self.electricityNetLast > 0.0 and self.timestampUtcLast != 0 and self.timestampUtcLast > (self.lastReadingElectricityNetUtc - 600000):
                                        wattsNet = self.electricityNetLast * 12
                                    else:
                                        wattsNet = 0.0
                            else:  # Assume last
                                lastReadingElectricityNetUtc_minus_600000 = self.lastReadingElectricityNetUtc - 600000
                                self.logger.debug(f"ELECTRICITY NET: CL=[{self.electricityNetLast}], UTCL=[{self.timestampUtcLast}],"
                                                  f" LRUTC=[{self.lastReadingElectricityNetUtc}], LRUTC600=[{lastReadingElectricityNetUtc_minus_600000}]")
                                if self.electricityNetLast > 0.0 and self.timestampUtcLast != 0 and self.timestampUtcLast > (self.lastReadingElectricityNetUtc - 600000):
                                    wattsNet = self.electricityNetLast * 12
                                else:
                                    wattsNet = 0.0

                            if wattsNet == 0.0:
                                wattsNet = self.electricityNetPrevious

                            wattsNetStr = f"{int(wattsNet)} Watts"
                            if not self.globals[SMAPPEES][devElectricityNet.id][HIDE_ENERGY_METER_CURRENT_NET_POWER]:
                                if wattsNet == 0.0 and self.globals[SMAPPEES][devElectricityNet.id][HIDE_ENERGY_METER_CURRENT_ZERO_NET_POWER]:
                                    pass
                                else:
                                    self.logger.info(f"received '{devElectricityNet.name}' electricity net reading: {wattsNetStr}")
                            devElectricityNet.updateStateOnServer("curEnergyLevel", wattsNet, uiValue=wattsNetStr)
                            devElectricityNet.updateStateImageOnServer(indigo.kStateImageSel.EnergyMeterOn)

                            if watts > 0.00:
                                netPercentage = int(round((wattsNet / watts) * 100))
                            else:
                                netPercentage = int(0)
                            netPercentageStr = f"{int(netPercentage)}%"
                            devElectricityNet.updateStateOnServer("kwhCurrentNetPercentage", netPercentage, uiValue=netPercentageStr)

                        if "accumEnergyTotal" in devElectricityNet.states:
                            if commandSentToSmappee == COMMAND_RESET_CONSUMPTION:
                                self.globals[SMAPPEES][devElectricityNet.id][ACCUMULATED_ENERGY_TOTAL] = 0.0
                                wattNetStr = f"{self.globals[SMAPPEES][devElectricityNet.id][ACCUMULATED_ENERGY_TOTAL]:3.0f} Watts"
                                devElectricityNet.updateStateOnServer("accumEnergyTotal", self.globals[SMAPPEES][devElectricityNet.id][ACCUMULATED_ENERGY_TOTAL], uiValue=wattNetStr)

                            if "accumEnergyTotal" in devElectricity.states:
                                # Need to check this as the kwh, gross amount, unit cost and currency code is retrieved from the Electricity Device

                                kwhNet = float(devElectricityNet.states.get("accumEnergyTotal", 0))
                                kwhNet += float(self.electricityNetTotal / 1000.0)
                                kwhNetStr = f"{kwhNet:0.3f} kWh"
                                kwhUnitCost = self.globals[SMAPPEES][devElectricity.id][KWH_UNIT_COST]
                                dailyStandingCharge = self.globals[SMAPPEES][devElectricity.id][DAILY_STANDING_CHARGE]

                                kwhNetReformatted = float(f"{kwhNet:0.3f}")
                                devElectricityNet.updateStateOnServer("accumEnergyTotal", kwhNetReformatted, uiValue=kwhNetStr)

                                amountNet = 0.00
                                if kwhUnitCost > 0.00:
                                    amountNet = dailyStandingCharge + (kwhNet * kwhUnitCost)
                                    amountNetReformatted = float(str(f"{amountNet:0.2f}"))
                                    amountNetStr = f"{amountNet:0.2f} {self.globals[SMAPPEES][devElectricity.id][CURRENCY_CODE]}"
                                    devElectricityNet.updateStateOnServer("dailyNetTotalCost", amountNetReformatted, uiValue=amountNetStr)

                                if not self.globals[SMAPPEES][devElectricityNet.id][HIDE_ENERGY_METER_ACCUMULATED_NET_POWER]:
                                    if kwhUnitCost == 0.00 or self.globals[SMAPPEES][devElectricityNet.id][HIDE_ENERGY_METER_ACCUMULATED_NET_POWER_COST]:
                                        self.logger.info(f"received '{devElectricityNet.name}' net energy total: {kwhNetStr}")
                                    else:
                                        self.logger.info(f"received '{devElectricityNet.name}' net energy total: {kwhNetStr} (Net {amountNetStr})")

                                if kwhNet > 0.00:
                                    netDailyPercentage = int(round((kwhNet / kwh) * 100))
                                else:
                                    netDailyPercentage = int(0)
                                netDailyPercentageStr = f"{int(netDailyPercentage)}%"
                                devElectricityNet.updateStateOnServer("kwhDailyTotalNetPercentage", netDailyPercentage, uiValue=netDailyPercentageStr)

                        self.globals[SMAPPEES][devElectricityNet.id][LAST_READING_ELECTRICITY_NET_UTC] = self.timestampUtc

                    if self.globals[CONFIG][SUPPORTS_ELECTRICITY_SAVED]:

                        if "curEnergyLevel" in devElectricitySaved.states:
                            if commandSentToSmappee == COMMAND_RESET_CONSUMPTION:
                                self.globals[SMAPPEES][devElectricitySaved.id][CURRENT_ENERGY_LEVEL] = 0.0
                                self.globals[SMAPPEES][devElectricitySaved.id][ACCUMULATED_ENERGY_TOTAL] = 0.0
                                wattStr = f"{self.globals[SMAPPEES][devElectricitySaved.id][CURRENT_ENERGY_LEVEL]:3.0f} Watts"
                                devElectricitySaved.updateStateOnServer("curEnergyLevel", self.globals[SMAPPEES][devElectricitySaved.id][CURRENT_ENERGY_LEVEL], uiValue=wattStr)
                                devElectricitySaved.updateStateImageOnServer(indigo.kStateImageSel.EnergyMeterOff)

                            self.options = devElectricitySaved.pluginProps["optionsEnergyMeterCurPower"]

                            if self.options == 'mean':  # mean, minimum, maximum, last
                                if self.electricitySavedNumberOfValues > 0:
                                    wattsSaved = (self.electricitySavedMeanAverage * 60) / 5
                                else:
                                    lastReadingElectricitySavedUtc_minus_600000 = self.lastReadingElectricitySavedUtc - 600000
                                    self.logger.debug(f"ELECTRICITY SAVED: CL=[{self.electricitySavedLas}], UTCL=[{self.timestampUtcLast}],"
                                                      f" LRUTC=[{self.lastReadingElectricitySavedUtc}], LRUTC600=[{lastReadingElectricitySavedUtc_minus_600000}]")
                                    if self.electricitySavedLast > 0.0 and self.timestampUtcLast != 0 and self.timestampUtcLast > (self.lastReadingElectricitySavedUtc - 600000):
                                        wattsSaved = self.electricitySavedLast * 12
                                    else:
                                        wattsSaved = 0.0
                            elif self.options == 'minimum':
                                if self.electricitySavedNumberOfValues > 0:
                                    wattsSaved = self.electricitySavedMinimum * 12
                                else:
                                    lastReadingElectricitySavedUtc_minus_600000 = self.lastReadingElectricitySavedUtc - 600000
                                    self.logger.debug(f"ELECTRICITY SAVED: CL=[{self.electricitySavedLast}], UTCL=[{self.timestampUtcLast}],"
                                                      f" LRUTC=[{self.lastReadingElectricitySavedUtc}], LRUTC600=[{lastReadingElectricitySavedUtc_minus_600000}]")
                                    if self.electricitySavedLast > 0.0 and self.timestampUtcLast != 0 and self.timestampUtcLast > (self.lastReadingElectricitySavedUtc - 600000):
                                        wattsSaved = self.electricitySavedLast * 12
                                    else:
                                        wattsSaved = 0.0
                            elif self.options == 'maximum':
                                if self.electricitySavedNumberOfValues > 0:
                                    wattsSaved = self.electricitySavedMaximum * 12
                                else:
                                    lastReadingElectricitySavedUtc_minus_600000 = self.lastReadingElectricitySavedUtc - 600000
                                    self.logger.debug(f"ELECTRICITY SAVED: CL=[{self.electricitySavedLast}], UTCL=[{self.timestampUtcLast}],"
                                                      f" LRUTC=[{self.lastReadingElectricitySavedUtc}], LRUTC600=[{lastReadingElectricitySavedUtc_minus_600000}]")
                                    if self.electricitySavedLast > 0.0 and self.timestampUtcLast != 0 and self.timestampUtcLast > (
                                            self.lastReadingElectricitySavedUtc - 600000):
                                        wattsSaved = self.electricitySavedLast * 12
                                    else:
                                        wattsSaved = 0.0
                            else:  # Assume last
                                lastReadingElectricitySavedUtc_minus_600000 = self.lastReadingElectricitySavedUtc - 600000
                                self.logger.debug(f"ELECTRICITY SAVED: CL=[{self.electricitySavedLast}], UTCL=[{self.timestampUtcLast}],"
                                                  f" LRUTC=[{self.lastReadingElectricitySavedUtc}], LRUTC600=[{lastReadingElectricitySavedUtc_minus_600000}]")
                                if self.electricitySavedLast > 0.0 and self.timestampUtcLast != 0 and self.timestampUtcLast > (self.lastReadingElectricitySavedUtc - 600000):
                                    wattsSaved = self.electricitySavedLast * 12
                                else:
                                    wattsSaved = 0.0

                            if wattsSaved == 0.0:
                                wattsSaved = self.electricitySavedPrevious

                            wattsSavedStr = f"{int(wattsSaved)} Watts"
                            if not self.globals[SMAPPEES][devElectricitySaved.id][HIDE_ENERGY_METER_CURRENT_SAVED_POWER]:
                                if wattsSaved == 0.0 and self.globals[SMAPPEES][devElectricitySaved.id][HIDE_ENERGY_METER_CURRENT_ZERO_NET_POWER]:
                                    pass
                                else:
                                    self.logger.info(f"received '{devElectricitySaved.name}' electricity saved reading: {wattsSavedStr}")
                            devElectricitySaved.updateStateOnServer("curEnergyLevel", wattsSaved, uiValue=wattsSavedStr)
                            devElectricitySaved.updateStateImageOnServer(indigo.kStateImageSel.EnergyMeterOn)

                            if watts > 0.00:
                                savedPercentage = int(round((wattsSaved / watts) * 100))
                            else:
                                savedPercentage = int(0)
                            savedPercentageStr = f"{savedPercentage}%"
                            devElectricitySaved.updateStateOnServer("kwhCurrentSavedPercentage", savedPercentage, uiValue=savedPercentageStr)

                        if "accumEnergyTotal" in devElectricitySaved.states:
                            if commandSentToSmappee == COMMAND_RESET_CONSUMPTION:
                                self.globals[SMAPPEES][devElectricitySaved.id][ACCUMULATED_ENERGY_TOTAL] = 0.0
                                wattSavedStr = f"{self.globals[SMAPPEES][devElectricitySaved.id][ACCUMULATED_ENERGY_TOTAL]:3.0f} Watts"
                                devElectricitySaved.updateStateOnServer("accumEnergyTotal", self.globals[SMAPPEES][devElectricitySaved.id][ACCUMULATED_ENERGY_TOTAL], uiValue=wattSavedStr)

                            if "accumEnergyTotal" in devElectricity.states:
                                # Need to check this as the gross amount, unit cost and currency code is retrieved from the Electricity Device

                                kwhSaved = float(devElectricitySaved.states.get("accumEnergyTotal", 0))
                                kwhSaved += float(self.electricitySavedTotal / 1000.0)
                                kwhSavedStr = f"{kwhSaved:0.3f} kWh"
                                kwhUnitCost = self.globals[SMAPPEES][devElectricity.id][KWH_UNIT_COST]

                                amountSaved = 0.00
                                if kwhUnitCost > 0.00:
                                    amountSaved = (kwhSaved * kwhUnitCost)
                                    amountSavedReformatted = float(f"{amountSaved:0.2f}")
                                    amountSavedStr = f"{amountSaved:0.2f} {self.globals[SMAPPEES][devElectricity.id][CURRENCY_CODE]}"
                                    devElectricitySaved.updateStateOnServer("dailyTotalCostSaving", amountSavedReformatted, uiValue=amountSavedStr)

                                    savedElectricityCalculated = True  # Enables calculation and storing of: dailyTotalPlusSavedElecIncome

                                if not self.globals[SMAPPEES][devElectricitySaved.id][HIDE_ENERGY_METER_ACCUMULATED_SAVED_POWER]:
                                    if kwhUnitCost == 0.00 or self.globals[SMAPPEES][devElectricitySaved.id][HIDE_ENERGY_METER_ACCUMULATED_SAVED_POWER_COST]:
                                        self.logger.info(f"received '{devElectricitySaved.name}' saved energy total: {kwhSavedStr}")
                                    else:
                                        self.logger.info(f"received '{devElectricitySaved.name}' saved energy total: {kwhSavedStr} (Saved {amountSavedStr})")

                                kwhSavedReformatted = float(f"{kwhSaved:0.3f}")
                                devElectricitySaved.updateStateOnServer("accumEnergyTotal", kwhSavedReformatted, uiValue=kwhSavedStr)

                                if kwhSaved > 0.00:
                                    savedDailyPercentage = int(round((kwhSaved / kwh) * 100))
                                else:
                                    savedDailyPercentage = int(0)
                                savedDailyPercentageStr = f"{int(savedDailyPercentage)} %"
                                devElectricitySaved.updateStateOnServer("kwhDailyTotalSavedPercentage", savedDailyPercentage, uiValue=savedDailyPercentageStr)

                        self.globals[SMAPPEES][devElectricitySaved.id][LAST_READING_ELECTRICITY_SAVED_UTC] = self.timestampUtc

                    if self.globals[CONFIG][SUPPORTS_SOLAR]:

                        if "curEnergyLevel" in devSolar.states:
                            if commandSentToSmappee == COMMAND_RESET_CONSUMPTION:

                                self.globals[SMAPPEES][devSolar.id][CURRENT_ENERGY_LEVEL] = 0.0
                                self.globals[SMAPPEES][devSolar.id][ACCUMULATED_ENERGY_TOTAL] = 0.0
                                wattSolarStr = f"{self.globals[SMAPPEES][devSolar.id][CURRENT_ENERGY_LEVEL]:3.0f} Watts"
                                devSolar.updateStateOnServer("curEnergyLevel", self.globals[SMAPPEES][devSolar.id][CURRENT_ENERGY_LEVEL], uiValue=wattSolarStr)
                                devSolar.updateStateImageOnServer(indigo.kStateImageSel.EnergyMeterOff)

                            self.optionsEnergyMeterCurPower = devSolar.pluginProps[
                                'optionsEnergyMeterCurPower']  # mean, minimum, maximum, last
                            if self.optionsEnergyMeterCurPower == 'mean':
                                if self.solarNumberOfValues > 0:
                                    wattsSolar = self.solarTotal * (60.0 / float(float(self.solarNumberOfValues) * 5))
                                    self.logger.debug(f"watts > 0 =[{watts}]")
                                else:
                                    lastReadingSolarUtc_minus_600000 = self.lastReadingSolarUtc - 600000
                                    self.logger.debug(f"SOLAR: CL=[{self.solarLast}], UTCL=[{self.timestampUtcLast}],"
                                                      f" LRUTC=[{self.lastReadingSolarUtc}], LRUTC600=[{lastReadingSolarUtc_minus_600000}]")
                                    if self.solarLast > 0.0 and self.timestampUtcLast != 0 and self.timestampUtcLast > (self.lastReadingSolarUtc - 600000):
                                        wattsSolar = self.solarLast * 12
                                    else:
                                        wattsSolar = 0.0
                            elif self.optionsEnergyMeterCurPower == 'minimum':
                                if self.solarNumberOfValues > 0:
                                    wattsSolar = self.solarMinimum * 12
                                else:
                                    lastReadingSolarUtc_minus_600000 = self.lastReadingSolarUtc - 600000
                                    self.logger.debug(f"SOLAR: CL=[{self.solarLast}], UTCL=[{self.timestampUtcLast}],"
                                                      f" LRUTC=[{self.lastReadingSolarUtc}], LRUTC600=[{lastReadingSolarUtc_minus_600000}]")
                                    if self.solarLast > 0.0 and self.timestampUtcLast != 0 and self.timestampUtcLast > (self.lastReadingSolarUtc - 600000):
                                        wattsSolar = self.solarLast * 12
                                    else:
                                        wattsSolar = 0.0
                            elif self.optionsEnergyMeterCurPower == 'maximum':
                                if self.solarNumberOfValues > 0:
                                    wattsSolar = self.solarMaximum * 12
                                else:
                                    lastReadingSolarUtc_minus_600000 = self.lastReadingSolarUtc - 600000
                                    self.logger.debug(f"SOLAR: CL=[{self.solarLast}], UTCL=[{self.timestampUtcLast}],"
                                                      f" LRUTC=[{self.lastReadingSolarUtc}], LRUTC600=[{lastReadingSolarUtc_minus_600000}]")
                                    if self.solarLast > 0.0 and self.timestampUtcLast != 0 and self.timestampUtcLast > (self.lastReadingSolarUtc - 600000):
                                        wattsSolar = self.solarLast * 12
                                    else:
                                        wattsSolar = 0.0
                            else:  # Assume last
                                lastReadingSolarUtc_minus_600000 = self.lastReadingSolarUtc - 600000
                                self.logger.debug(f"SOLAR: CL=[{self.solarLast}], UTCL=[{self.timestampUtcLast}],"
                                                  f" LRUTC=[{self.lastReadingSolarUtc}], LRUTC600=[{lastReadingSolarUtc_minus_600000}]")
                                if self.solarLast > 0.0 and self.timestampUtcLast != 0 and self.timestampUtcLast > (self.lastReadingSolarUtc - 600000):
                                    wattsSolar = self.solarLast * 12
                                else:
                                    wattsSolar = 0.0

                            if wattsSolar == 0.0:
                                wattsSolar = self.solarPrevious

                            wattsSolarStr = f"{int(wattsSolar)} Watts"
                            if not self.globals[SMAPPEES][devSolar.id][HIDE_SOLAR_METER_CURRENT_GENERATION]:
                                if wattsSolar == 0.0 and self.globals[SMAPPEES][devSolar.id][HIDE_ZERO_SOLAR_METER_CURRENT_GENERATION]:
                                    pass
                                else:
                                    self.logger.info(f"received '{devSolar.name}' solar generation reading: {wattsSolarStr}")
                            devSolar.updateStateOnServer("curEnergyLevel", wattsSolar, uiValue=wattsSolarStr)
                            devSolar.updateStateImageOnServer(indigo.kStateImageSel.EnergyMeterOn)

                        if "accumEnergyTotal" in devSolar.states:
                            if commandSentToSmappee == COMMAND_RESET_CONSUMPTION:
                                self.globals[SMAPPEES][devSolar.id][ACCUMULATED_ENERGY_TOTAL] = 0.0
                                wattSolarStr = f"{self.globals[SMAPPEES][devSolar.id][ACCUMULATED_ENERGY_TOTAL]:3.0f} Watts"
                                devSolar.updateStateOnServer("accumEnergyTotal", self.globals[SMAPPEES][devSolar.id][ACCUMULATED_ENERGY_TOTAL], uiValue=wattSolarStr)

                            # To calculate Amounts (financials) all three device types solar, solaUsed and solarExported must be present

                            self.financialsEnabled = True

                            # Calculate Solar Total (Daily)

                            kwhSolar = float(devSolar.states.get("accumEnergyTotal", 0))
                            kwhSolar += float(self.solarTotal / 1000.0)
                            kwhSolarStr = f"{kwhSolar:0.3f} kWh"

                            generationRate = self.globals[SMAPPEES][devSolar.id][GENERATION_RATE]
                            exportRate = self.globals[SMAPPEES][devSolar.id][EXPORT_RATE]

                            if self.globals[CONFIG][SUPPORTS_SOLAR_USED] and "accumEnergyTotal" in devSolarUsed.states:
                                # Calculate Solar Used (Daily)
                                kwhUsed = float(devSolarUsed.states.get("accumEnergyTotal", 0))
                                kwhUsed += float(self.solarUsedTotal / 1000.0)

                                if self.globals[CONFIG][SUPPORTS_SOLAR_EXPORTED] and "accumEnergyTotal" in devSolarExported.states:
                                    # Calculate Solar Exported (Daily)
                                    kwhExported = float(devSolarExported.states.get("accumEnergyTotal", 0))
                                    kwhExported += float(self.solarExportedTotal / 1000.0)

                                    amountSolar = 0.00
                                    amountExported = 0.00  # Needed for calculation of total FIT payment
                                    amountGenerated = 0.00

                                    if generationRate > 0.00:
                                        amountGenerated = (kwhSolar * generationRate)
                                    if exportRate > 0.00:
                                        exportType = self.globals[SMAPPEES][devSolar.id][EXPORT_TYPE]
                                        if exportType == 'percentage':
                                            exportPercentage = self.globals[SMAPPEES][devSolar.id][EXPORT_PERCENTAGE]
                                        elif exportType == 'actual':
                                            exportPercentage = (kwhExported / kwhSolar) * 100
                                        else:
                                            exportPercentage = 0.00
                                        amountExported = (kwhSolar * exportRate * exportPercentage) / 100

                                    amountSolar = amountGenerated + amountExported

                                    amountGeneratedReformatted = float(f"{amountGenerated:0.2f}")
                                    amountGeneratedStr = f"{amountGenerated:0.2f} {self.globals[SMAPPEES][devSolar.id][CURRENCY_CODE]}"
                                    devSolar.updateStateOnServer("dailyTotalGenOnlyIncome", amountGeneratedReformatted, uiValue=amountGeneratedStr)

                                    amountSolarReformatted = float(f"{amountSolar:0.2f}")
                                    amountSolarStr = f"{amountSolarReformatted:0.2f} {self.globals[SMAPPEES][devSolar.id][CURRENCY_CODE]}"
                                    devSolar.updateStateOnServer("dailyTotalIncome", amountSolarReformatted, uiValue=amountSolarStr)

                                    if savedElectricityCalculated:
                                        amountSolarPlusSaving = amountSolar + amountSaved
                                        amountSolarPlusSavingReformatted = float(f"{amountSolarPlusSaving:0.2f}")
                                        amountSolarPlusSavingStr = f"{amountSolarPlusSaving:0.2f} {self.globals[SMAPPEES][devSolar.id][CURRENCY_CODE]}"
                                        devSolar.updateStateOnServer("dailyTotalPlusSavedElecIncome", amountSolarPlusSavingReformatted, uiValue=amountSolarPlusSavingStr)

                            if not self.globals[SMAPPEES][devSolar.id][HIDE_SOLAR_METER_ACCUMULATED_GENERATION]:
                                if self.globals[SMAPPEES][devSolar.id][HIDE_SOLAR_METER_ACCUMULATED_GENERATION_COST]:
                                    if generationRate == 0.00 and self.globals[SMAPPEES][devSolar.id][HIDE_ZERO_SOLAR_METER_CURRENT_GENERATION]:
                                        pass  # Don't output zero solar values
                                    else:
                                        # if 'no change in solar' and self.globals[SMAPPEES][devSolar.id][HIDE_NO_CHANGE_IN_SOLAR_METER_ACCUMULATED_GENERATION]:
                                        #     pass
                                        # else:
                                        # do code below .... (remember to indent it!)
                                        self.logger.info(f"received '{devSolar.name}' solar generation total: {kwhSolarStr}")
                                else:
                                    if generationRate == 0.00 and self.globals[SMAPPEES][devSolar.id][HIDE_ZERO_SOLAR_METER_CURRENT_GENERATION]:
                                        pass  # Don't output zero solar values
                                    else:
                                        # if 'no change in solar' and self.globals[SMAPPEES][devSolar.id][HIDE_NO_CHANGE_IN_SOLAR_METER_ACCUMULATED_GENERATION]:
                                        #     pass
                                        # else:
                                        # do code below .... (remember to indent it!)
                                        self.logger.info(f"received '{devSolar.name}' solar generation total: {kwhSolarStr} ({amountSolarStr})")

                                        # self.globals[SMAPPEES][devSolar.id][HIDE_NO_CHANGE_IN_SOLAR_METER_ACCUMULATED_GENERATION] and kwhReformatted == float(devSolar.states['accumEnergyTotal']) and wattsSolar == 0.0:

                            kwhSolarReformatted = float(f"{kwhSolar:0.3f}")
                            devSolar.updateStateOnServer("accumEnergyTotal", kwhSolarReformatted, uiValue=kwhSolarStr)

                        self.globals[SMAPPEES][devSolar.id][LAST_READING_SOLAR_UTC] = self.timestampUtc

                    if self.globals[CONFIG][SUPPORTS_SOLAR_USED]:
                        if "curEnergyLevel" in devSolarUsed.states:
                            if commandSentToSmappee == COMMAND_RESET_CONSUMPTION:
                                self.globals[SMAPPEES][devSolarUsed.id][CURRENT_ENERGY_LEVEL] = 0.0
                                self.globals[SMAPPEES][devSolarUsed.id][ACCUMULATED_ENERGY_TOTAL] = 0.0
                                wattsUsedStr = f"{self.globals[SMAPPEES][devSolarUsed.id][CURRENT_ENERGY_LEVEL]:3.0f} Watts"
                                devSolarUsed.updateStateOnServer("curEnergyLevel", self.globals[SMAPPEES][devSolarUsed.id][CURRENT_ENERGY_LEVEL], uiValue=wattsUsedStr)
                                devSolarUsed.updateStateImageOnServer(indigo.kStateImageSel.EnergyMeterOff)

                            self.options = devSolarUsed.pluginProps["optionsEnergyMeterCurPower"]

                            if self.options == 'mean':  # mean, minimum, maximum, last
                                if self.solarUsedNumberOfValues > 0:
                                    wattsUsed = (self.solarUsedMeanAverage * 60) / 5
                                else:
                                    lastReadingElectricityNetUtc_minus_600000 = self.lastReadingElectricityNetUtc - 600000
                                    self.logger.debug(f"ELECTRICITY NET: CL=[{self.solarUsedLas}], UTCL=[{self.timestampUtcLast}],"
                                                      f" LRUTC=[{self.lastReadingElectricityNetUtc}], LRUTC600=[{lastReadingElectricityNetUtc_minus_600000}]")
                                    if self.solarUsedLast > 0.0 and self.timestampUtcLast != 0 and self.timestampUtcLast > (self.lastReadingElectricityNetUtc - 600000):
                                        wattsUsed = self.solarUsedLast * 12
                                    else:
                                        wattsUsed = 0.0
                            elif self.options == 'minimum':
                                if self.solarUsedNumberOfValues > 0:
                                    wattsUsed = self.solarUsedMinimum * 12
                                else:
                                    lastReadingElectricityNetUtc_minus_600000 = self.lastReadingElectricityNetUtc - 600000
                                    self.logger.debug(f"ELECTRICITY NET: CL=[{self.solarUsedLast}], UTCL=[{self.timestampUtcLast}],"
                                                      f" LRUTC=[{self.lastReadingElectricityNetUtc}], LRUTC600=[{lastReadingElectricityNetUtc_minus_600000}]")
                                    if self.solarUsedLast > 0.0 and self.timestampUtcLast != 0 and self.timestampUtcLast > (self.lastReadingElectricityNetUtc - 600000):
                                        wattsUsed = self.solarUsedLast * 12
                                    else:
                                        wattsUsed = 0.0
                            elif self.options == 'maximum':
                                if self.solarUsedNumberOfValues > 0:
                                    wattsUsed = self.solarUsedMaximum * 12
                                else:
                                    lastReadingElectricityNetUtc_minus_600000 = self.lastReadingElectricityNetUtc - 600000
                                    self.logger.debug(f"ELECTRICITY NET: CL=[{self.solarUsedLast}], UTCL=[{self.timestampUtcLast}],"
                                                      f" LRUTC=[{self.lastReadingElectricityNetUtc}], LRUTC600=[{lastReadingElectricityNetUtc_minus_600000}]")
                                    if self.solarUsedLast > 0.0 and self.timestampUtcLast != 0 and self.timestampUtcLast > (self.lastReadingElectricityNetUtc - 600000):
                                        wattsUsed = self.solarUsedLast * 12
                                    else:
                                        wattsUsed = 0.0
                            else:  # Assume last
                                lastReadingSolarUsedUtc_minus_600000 = self.lastReadingSolarUsedUtc - 600000
                                self.logger.debug(f"SOLAR USED: CL=[{self.solarUsedLast}], UTCL=[{self.timestampUtcLast}],"
                                                  f" LRUTC=[{self.lastReadingSolarUsedUtc}], LRUTC600=[{lastReadingSolarUsedUtc_minus_600000}]")
                                if self.solarUsedLast > 0.0 and self.timestampUtcLast != 0 and self.timestampUtcLast > (self.lastReadingSolarUsedUtc - 600000):
                                    wattsUsed = self.solarUsedLast * 12
                                else:
                                    wattsUsed = 0.0

                            if wattsUsed == 0.0:
                                wattsUsed = self.solarUsedPrevious

                            wattsUsedStr = f"{int(wattsUsed)} Watts"
                            if not self.globals[SMAPPEES][devSolarUsed.id][HIDE_SOLAR_USED_METER_CURRENT_GENERATION]:
                                if wattsUsed == 0.0 and self.globals[SMAPPEES][devSolarUsed.id][HIDE_SOLAR_USED_METER_CURRENT_GENERATION]:
                                    pass
                                else:
                                    self.logger.info(f"received '{devSolarUsed.name}' solar power used reading: {wattsUsedStr}")
                            devSolarUsed.updateStateOnServer("curEnergyLevel", wattsUsed, uiValue=wattsUsedStr)
                            devSolarUsed.updateStateImageOnServer(indigo.kStateImageSel.EnergyMeterOn)

                            if self.solar > 0.00:
                                usedPercentage = int(round((self.solarUsed / self.solar) * 100))
                            else:
                                usedPercentage = int(0)
                            usedPercentageStr = f"{int(usedPercentage)} %"
                            devSolarUsed.updateStateOnServer("kwhCurrentUsedPercentage", usedPercentage, uiValue=usedPercentageStr)

                        if "accumEnergyTotal" in devSolarUsed.states:
                            if commandSentToSmappee == COMMAND_RESET_CONSUMPTION:
                                self.globals[SMAPPEES][devSolarUsed.id][ACCUMULATED_ENERGY_TOTAL] = 0.0
                                wattStr = f"{self.globals[SMAPPEES][devSolarUsed.id][ACCUMULATED_ENERGY_TOTAL]:3.0f} Watts"
                                devSolarUsed.updateStateOnServer("accumEnergyTotal", self.globals[SMAPPEES][devSolarUsed.id][ACCUMULATED_ENERGY_TOTAL], uiValue=wattStr)

                            # kwhUsed = float(devSolarUsed.states.get("accumEnergyTotal", 0))
                            # kwhUsed += float(self.solarUsedTotal / 1000.0)
                            kwhUsedStr = f"{kwhUsed:0.3f} kWh"  # Calculated in solar device

                            kwhUsedReformatted = float(f"{kwhUsed:0.3f}")

                            # HIDE_NO_CHANGE_IN_SOLAR_EXPORTED_METER_ACCUMULATED_GENERATION

                            if not self.globals[SMAPPEES][devSolarUsed.id][HIDE_SOLAR_USED_METER_ACCUMULATED_GENERATION]:
                                if (self.globals[SMAPPEES][devSolarUsed.id][HIDE_NO_CHANGE_IN_SOLAR_USED_METER_ACCUMULATED_GENERATION] and
                                        kwhUsedReformatted == float(devSolarUsed.states['accumEnergyTotal']) and wattsUsed == 0.0):
                                    pass
                                else:
                                    self.logger.info(f"received '{devSolarUsed.name}' solar energy used total: {kwhUsedStr}")

                            devSolarUsed.updateStateOnServer("accumEnergyTotal", kwhUsedReformatted, uiValue=kwhUsedStr)

                            if "accumEnergyTotal" in devSolar.states:
                                # Needed to caculate total used percentage - uses 'kwhSolar'

                                if kwhSolar > 0.00:
                                    usedDailyPercentage = int(round((kwhUsed / kwhSolar) * 100))
                                else:
                                    usedDailyPercentage = int(0)
                                usedDailyPercentageStr = f"{int(usedDailyPercentage)} %"
                                devSolarUsed.updateStateOnServer("kwhDailyTotalUsedPercentage", usedDailyPercentage, uiValue=usedDailyPercentageStr)

                        self.globals[SMAPPEES][devSolarUsed.id][LAST_READING_SOLAR_USED_UTC] = self.timestampUtc

                    if self.globals[CONFIG][SUPPORTS_SOLAR_EXPORTED]:

                        if "curEnergyLevel" in devSolarExported.states:
                            if commandSentToSmappee == COMMAND_RESET_CONSUMPTION:
                                self.globals[SMAPPEES][devSolarExported.id][CURRENT_ENERGY_LEVEL] = 0.0
                                self.globals[SMAPPEES][devSolarExported.id][ACCUMULATED_ENERGY_TOTAL] = 0.0
                                wattsExportedStr = f"{self.globals[SMAPPEES][devSolarExported.id][CURRENT_ENERGY_LEVEL]:3.0f} Watts"
                                devSolarExported.updateStateOnServer("curEnergyLevel", self.globals[SMAPPEES][devSolarExported.id][CURRENT_ENERGY_LEVEL], uiValue=wattsExportedStr)
                                devSolarExported.updateStateImageOnServer(indigo.kStateImageSel.EnergyMeterOff)

                            self.options = devSolarExported.pluginProps["optionsEnergyMeterCurPower"]

                            if self.options == 'mean':  # mean, minimum, maximum, last
                                if self.solarExportedNumberOfValues > 0:
                                    wattsExported = (self.solarExportedMeanAverage * 60) / 5
                                else:
                                    lastReadingElectricityNetUtc_minus_600000 = self.lastReadingElectricityNetUtc - 600000
                                    self.logger.debug(f"ELECTRICITY NET: CL=[{self.solarExportedLast}], UTCL=[{self.timestampUtcLast}],"
                                                      f" LRUTC=[{self.lastReadingElectricityNetUtc}], LRUTC600=[{lastReadingElectricityNetUtc_minus_600000}]")
                                    if self.solarExportedLast > 0.0 and self.timestampUtcLast != 0 and self.timestampUtcLast > (
                                            self.lastReadingElectricityNetUtc - 600000):
                                        wattsExported = self.solarExportedLast * 12
                                    else:
                                        wattsExported = 0.0
                            elif self.options == 'minimum':
                                if self.solarExportedNumberOfValues > 0:
                                    wattsExported = self.solarExportedMinimum * 12
                                else:
                                    lastReadingElectricityNetUtc_minus_600000 = self.lastReadingElectricityNetUtc - 600000
                                    self.logger.debug(f"ELECTRICITY NET: CL=[{self.solarExportedLast}], UTCL=[{self.timestampUtcLast}],"
                                                      f" LRUTC=[{self.lastReadingElectricityNetUtc}], LRUTC600=[{ lastReadingElectricityNetUtc_minus_600000}]")
                                    if self.solarExportedLast > 0.0 and self.timestampUtcLast != 0 and self.timestampUtcLast > (
                                            self.lastReadingElectricityNetUtc - 600000):
                                        wattsExported = self.solarExportedLast * 12
                                    else:
                                        wattsExported = 0.0
                            elif self.options == 'maximum':
                                if self.solarExportedNumberOfValues > 0:
                                    wattsExported = self.solarExportedMaximum * 12
                                else:
                                    lastReadingElectricityNetUtc_minus_600000 = self.lastReadingElectricityNetUtc - 600000
                                    self.logger.debug(f"ELECTRICITY NET: CL=[{self.solarExportedLast}], UTCL=[{self.timestampUtcLast}],"
                                                      f" LRUTC=[{self.lastReadingElectricityNetUtc}], LRUTC600=[{lastReadingElectricityNetUtc_minus_600000}]")
                                    if self.solarExportedLast > 0.0 and self.timestampUtcLast != 0 and self.timestampUtcLast > (self.lastReadingElectricityNetUtc - 600000):
                                        wattsExported = self.solarExportedLast * 12
                                    else:
                                        wattsExported = 0.0
                            else:  # Assume last
                                lastReadingSolarExportedUtc_minus_600000 = self.lastReadingSolarExportedUtc - 600000
                                self.logger.debug(f"USAGESAVING: CL=[{self.solarExportedLast}], UTCL=[{self.timestampUtcLast}],"
                                                  f" LRUTC=[{self.lastReadingSolarExportedUtc}], LRUTC600=[{lastReadingSolarExportedUtc_minus_600000}]")

                                if self.solarExportedLast > 0.0 and self.timestampUtcLast != 0 and self.timestampUtcLast > (
                                        self.lastReadingSolarExportedUtc - 600000):
                                    wattsExported = self.solarExportedLast * 12
                                else:
                                    wattsExported = 0.0

                            if wattsExported == 0.0:
                                wattsExported = self.solarExportedPrevious

                            wattsExportedStr = f"{int(wattsExported)} Watts"
                            if not self.globals[SMAPPEES][devSolarExported.id][HIDE_SOLAR_EXPORTED_METER_CURRENT_GENERATION]:
                                if wattsExported == 0.0 and self.globals[SMAPPEES][devSolarExported.id][HIDE_SOLAR_EXPORTED_METER_CURRENT_GENERATION]:
                                    pass
                                else:
                                    self.logger.info(f"received '{devSolarExported.name}' solar energy exported reading: {wattsExportedStr}")
                            devSolarExported.updateStateOnServer("curEnergyLevel", wattsExported, uiValue=wattsExportedStr)
                            devSolarExported.updateStateImageOnServer(indigo.kStateImageSel.EnergyMeterOn)

                            if self.solar > 0.00:
                                exportedPercentage = int(round((self.solarExported / self.solar) * 100))
                            else:
                                exportedPercentage = int(0)
                            exportedPercentageStr = f"{int(exportedPercentage)} %"
                            devSolarExported.updateStateOnServer("kwhCurrentExportedPercentage", exportedPercentage, uiValue=exportedPercentageStr)

                        if "accumEnergyTotal" in devSolarExported.states:
                            if commandSentToSmappee == COMMAND_RESET_CONSUMPTION:
                                self.globals[SMAPPEES][devSolarExported.id][ACCUMULATED_ENERGY_TOTAL] = 0.0
                                kwhExportedStr = f"{self.globals[SMAPPEES][devSolarExported.id][ACCUMULATED_ENERGY_TOTAL]:3.0f} kWh"
                                devSolarExported.updateStateOnServer("accumEnergyTotal", self.globals[SMAPPEES][devSolarExported.id][ACCUMULATED_ENERGY_TOTAL], uiValue=kwhExportedStr)

                            # kwhExported = float(devSolarExported.states.get("accumEnergyTotal", 0))
                            # kwhExported += float(self.solarExportedTotal / 1000.0)
                            kwhExportedStr = f"{kwhExported:0.3f} kWh"  # Calculated in solar device - 'kwhExported'
                            kwhExportedReformatted = float(f"{kwhExported:0.3f}")

                            if not self.globals[SMAPPEES][devSolarExported.id][HIDE_SOLAR_EXPORTED_METER_ACCUMULATED_GENERATION]:
                                if self.globals[SMAPPEES][devSolarExported.id][HIDE_NO_CHANGE_IN_SOLAR_EXPORTED_METER_ACCUMULATED_GENERATION] and \
                                        kwhExportedReformatted == float(devSolarExported.states['accumEnergyTotal']) and wattsExported == 0.0:
                                    pass
                                else:
                                    self.logger.info(f"received '{devSolarExported.name}' solar energy exported total: {kwhExportedStr}")

                            devSolarExported.updateStateOnServer("accumEnergyTotal", kwhExportedReformatted,
                                                                 uiValue=kwhExportedStr)

                            if "accumEnergyTotal" in devSolar.states:
                                # Needed to caculate total exported percentage - uses 'kwhSolar'

                                if kwhSolar > 0.00:
                                    exportedDailyPercentage = int(round((kwhExported / kwhSolar) * 100))
                                else:
                                    exportedDailyPercentage = int(0)
                                exportedDailyPercentageStr = f"{int(exportedDailyPercentage)} %"
                                devSolarExported.updateStateOnServer("kwhDailyTotalExportedPercentage", exportedDailyPercentage, uiValue=exportedDailyPercentageStr)

                            amountExportedReformatted = float(f"{amountExported:0.2f}")
                            amountExportedStr = f"{amountExported:0.2f} {self.globals[SMAPPEES][devSolar.id][CURRENCY_CODE]}"
                            devSolarExported.updateStateOnServer("dailyTotalExportOnlyIncome", amountExportedReformatted, uiValue=amountExportedStr)

                        self.globals[SMAPPEES][devSolarExported.id][LAST_READING_SOLAR_EXPORTED_UTC] = self.timestampUtc

                elif key == 'error':
                    self.logger.error(f"SMAPPEE ERROR DETECTED [{commandSentToSmappee}]: {value}")
                else:
                    pass  # Unknown key/value pair
                    self.logger.debug(f"Unhandled key/value pair : K=[{key}], V=[{value}]")

        except Exception as exception_error:
            self.exception_handler(exception_error, True)  # Log error and display failing statement

    def handleGetSensorConsumption(self, commandSentToSmappee, responseLocationId, decodedSmappeeResponse):
        try:
            for decoding in decodedSmappeeResponse:
                errorDetected = False
                for key, value in decoding.items():
                    if key == 'serviceLocationId' or key == 'sensorId' or key == 'records' or key == 'error':
                        if key == 'error':
                            self.logger.debug(f"SMAPPEE SENSOR handleGetSensorConsumption error detected by Smappee: Error=[{value}]")
                            errorDetected = True
                        # At this point the response (so far) is OK as we know how to process the key
                    else:
                        self.logger.debug(f"SMAPPEE SENSOR Unhandled key/value pair : K=[{key}], V=[{value}]")
                if errorDetected:
                    self.logger.error(f"SMAPPEE SENSOR handleGetSensorConsumption error - response abandoned!")
                    break

                sLoc = ""
                for key, value in decoding.items():
                    if key == 'serviceLocationId':
                        sLoc = str(value)  # Service Location
                        self.logger.debug(f"handleGetSensorConsumption [serviceLocationId] - K = [{key}], V = {value} and sLoc = {sLoc}")
                        break

                sensorA_DevId = 0
                sensorB_DevId = 0

                for key, value in decoding.items():
                    if key == 'sensorId':
                        smappeeType = 'GW'  # Sensor for Gas Water
                        value_2 = ("00" + value)[-2:]
                        sId = f"{smappeeType}{value_2}"
                        self.logger.debug(f"handleGetSensorConsumption [sensorId] - sId = [{sId}]")

                        def checkIndigoDev(serviceLocation, address):

                            returnedDevId = 0
                            lastReadingSensorUtc = 0
                            pulsesPerUnit = 1  # Default
                            measurementTimeMultiplier = 1.0

                            try:
                                for dev in indigo.devices.iter("self"):
                                    # self.logger.debug(f"handleGetSensorConsumption [sensorId-checkIndigoDev] - DN={dev.name}, deviceTypeId=[{type(dev.deviceTypeId)}] {dev.deviceTypeId},"
                                    #                          f" serviceLocation=[{type(dev.pluginProps["serviceLocationId"])}] {dev.pluginProps["serviceLocationId"]},"
                                    #                          f" deviceAddress=[{type(dev.address)}] {dev.address}")
                                    if (dev.deviceTypeId == "smappeeSensor") and (dev.pluginProps["serviceLocationId"] == serviceLocation) and (dev.address == address):
                                        self.logger.debug(f"handleGetSensorConsumption [sensorId-checkIndigoDev- FOUND] DN = [{dev.name}], TYPEID =  [{dev.deviceTypeId}],"
                                                          f" SL=[{dev.pluginProps['serviceLocationId']}], A=[{dev.address}]")
                                        returnedDevId = dev.id
                                        lastReadingSensorUtc = self.globals[SMAPPEES][dev.id][LAST_READING_SENSOR_UTC]
                                        pulsesPerUnit = self.globals[SMAPPEES][dev.id][PULSES_PER_UNIT]

                                        unitsKey = self.globals[SMAPPEES][dev.id][UNITS]
                                        if unitsKey in self.globals[UNIT_TABLE]:
                                            pass
                                        else:
                                            unitsKey = 'default'
                                        measurementTimeMultiplier = self.globals[UNIT_TABLE][unitsKey][FUNCTION_QUEUE_REMOVE]

                                        if not dev.states['smappeeSensorOnline']:
                                            dev.updateStateOnServer("smappeeSensorOnline", True, uiValue='online')

                            except Exception as error_message:
                                self.exception_handler(error_message, True)  # Log error and display failing statement
                                
                            finally:
                                return returnedDevId, lastReadingSensorUtc, pulsesPerUnit, measurementTimeMultiplier

                        sensorAddress = sId + '-A'
                        sensorA_DevId, lastReadingSensorA_Utc, pulsesPerUnitSensorA, measurementTimeMultiplierSensorA = checkIndigoDev(sLoc, sensorAddress)
                        sensorAddress = sId + '-B'
                        sensorB_DevId, lastReadingSensorB_Utc, pulsesPerUnitSensorB, measurementTimeMultiplierSensorB = checkIndigoDev(sLoc, sensorAddress)

                        self.logger.debug(f"handleGetSensorConsumption [sensorId-checkIndigoDev] - dev.Id [A] = [{sensorA_DevId}], dev.Id [B] = [{sensorB_DevId}]")

                        break

                for key, value in decoding.items():
                    if key == 'records' and (sensorA_DevId != 0 or sensorB_DevId != 0):

                        timestampUtcLast = 0  # Common to both

                        numberOfValues = 0

                        sensorA_Total = 0.0
                        sensorA_MeanAverage = 0.0
                        sensorA_NumberOfValues = 0
                        sensorA_Minimum = 99999999.0
                        sensorA_Maximum = 0.0
                        sensorA_Previous = 0.0
                        sensorA_Last = 0.0

                        sensorA_Temperature = 0.0
                        sensorA_Humidity = 0.0
                        sensorA_BatteryLevel = 0.0

                        sensorB_Total = 0.0
                        sensorB_MeanAverage = 0.0
                        sensorB_NumberOfValues = 0
                        sensorB_Minimum = 99999999.0
                        sensorB_Maximum = 0.0
                        sensorB_Previous = 0.0
                        sensorB_Last = 0.0

                        sensorB_Temperature = 0.0
                        sensorB_Humidity = 0.0
                        sensorB_BatteryLevel = 0.0

                        if self.globals[SQL][ENABLED]:
                            try:
                                self.globals[SQL][SQL_CONNECTION] = sql3.connect(self.globals[SQL]['db'])
                                self.globals[SQL]['cursor'] = self.globals[SQL][SQL_CONNECTION].cursor()
                            except sql3.Error as e:
                                if self.globals[SQL][SQL_CONNECTION]:
                                    self.globals[SQL][SQL_CONNECTION].rollback()
                                e_args_zero = e.args[0]
                                self.logger.error(f"SMAPPEE ERROR DETECTED WITH SQL [SENSOR] CONNECTION: {e_args_zero}")

                                self.globals[SQL][ENABLED] = False  # Disable SQL processing

                        for self.sensorReading in value:
                            timestampUtc = 0
                            value1 = 0.0
                            value2 = 0.0
                            temperature = 0.0
                            humidity = 0.0
                            batteryLevel = 0.0

                            sensorA_Last = 0.0
                            sensorB_Last = 0.0

                            readingSensorA_Detected = False
                            readingSensorB_Detected = False

                            self.logger.debug("handleGetSensorConsumption [Q][SENSOR] -  [START ...]")

                            for readingKey, readingValue in self.sensorReading.items():
                                self.logger.debug(f"handleGetSensorConsumption [Q][SENSOR] -  [{readingKey} : {readingValue}]")
                                if readingKey == 'timestamp':
                                    timestampUtc = readingValue
                                    timestampUtcLast = readingValue
                                elif readingKey == 'value1':
                                    readingSensorA_Detected = True
                                    value1 = readingValue
                                    # value1 = readingValue / pulsesPerUnitSensorA
                                elif readingKey == 'value2':
                                    readingSensorB_Detected = True
                                    value2 = readingValue
                                    # value2 = readingValue / pulsesPerUnitSensorB
                                elif readingKey == 'temperature':
                                    temperature = readingValue
                                elif readingKey == 'humidity':
                                    humidity = readingValue
                                elif readingKey == 'battery':
                                    batteryLevel = readingValue
                                else:
                                    pass  # Unknown key/value pair
                            self.logger.debug(f"handleGetSensorConsumption [Q][SENSOR] -  [... END: TS={timestampUtc},"
                                              f" V1={value1}, V2={value2}, TEMP={temperature}, HUM={humidity}, BAT={batteryLevel}]")

                            if timestampUtc != 0:
                                if sensorA_DevId != 0:

                                    sensorA_Temperature = temperature
                                    sensorA_Humidity = humidity
                                    sensorA_BatteryLevel = batteryLevel

                                    if timestampUtc > lastReadingSensorA_Utc:
                                        sensorA_NumberOfValues += 1
                                        sensorA_Total += value1
                                        if value1 < sensorA_Minimum:
                                            sensorA_Minimum = value1
                                        if value1 > sensorA_Maximum:
                                            sensorA_Maximum = value1
                                        sensorA_Last = value1

                                    elif timestampUtc == lastReadingSensorA_Utc:
                                        sensorA_Previous = 0.0
                                        if readingSensorA_Detected:
                                            sensorA_Previous = value1 * measurementTimeMultiplierSensorA

                                if sensorB_DevId != 0:
                                    sensorB_Temperature = temperature
                                    sensorB_Humidity = humidity
                                    sensorB_BatteryLevel = batteryLevel

                                    if timestampUtc > lastReadingSensorB_Utc:
                                        sensorB_NumberOfValues += 1
                                        sensorB_Total += value2
                                        if value2 < sensorB_Minimum:
                                            sensorB_Minimum = value2
                                        if value2 > sensorB_Maximum:
                                            sensorB_Maximum = value2
                                        sensorB_Last = value2

                                    elif timestampUtc == lastReadingSensorB_Utc:
                                        sensorB_Previous = 0.0
                                        if readingSensorB_Detected:
                                            sensorB_Previous = value1 * measurementTimeMultiplierSensorB

                                self.logger.debug(f"handleGetSensorConsumption [Q][SENSOR] -  [... SQL: TS={timestampUtc},"
                                                  f" V1={value1}, V2={value2}, TEMP={temperature}, HUM={humidity}, BAT={batteryLevel}]")

                                if self.globals[SQL][ENABLED]:
                                    insertSql = 'NO SQL SET-UP YET'
                                    try:
                                        readingTime = str(int(timestampUtc / 1000))  # Remove micro seconds
                                        readingYYYYMMDDHHMMSS = datetime.datetime.fromtimestamp(int(readingTime)).strftime('%Y-%m-%d %H:%M:%S')
                                        readingYYYYMMDD = readingYYYYMMDDHHMMSS[0:10]
                                        readingHHMMSS = readingYYYYMMDDHHMMSS[-8:]
                                        sensor1 = str(int(value1))
                                        sensor2 = str(int(value2))
                                        humidity = str(int(humidity * 10))
                                        temperature = str(int(temperature * 10))
                                        battery = str(int(batteryLevel * 10))

                                        self.logger.debug(f"handleGetSensorConsumption [Q][SENSOR] -  [... INS: RT={readingTime}, YYYYMMDD={readingYYYYMMDDHHMMSS}, HHMMSS={readingHHMMSS},"
                                                          f" V1={sensor1}, V2={sensor2}, TEMP={temperature}, HUM={humidity}, BAT={battery}]")

                                        insertSql = f"""
                                            INSERT OR REPLACE INTO sensor_readings (reading_time, reading_YYYYMMDD, reading_HHMMSS, sensor1, sensor2, humidity, temperature, battery)
                                            VALUES ({readingTime}, '{readingYYYYMMDD}', '{readingHHMMSS}', {sensor1}, {sensor2}, {humidity}, {temperature}, {battery});
                                            """
                                        self.globals[SQL]['cursor'].executescript(insertSql)
                                    except sql3.Error as e:
                                        if self.globals[SQL][SQL_CONNECTION]:
                                            self.globals[SQL][SQL_CONNECTION].rollback()
                                        e_args_zero = e.args[0]
                                        self.logger.error(f"SMAPPEE ERROR DETECTED WITH SQL [SENSOR] INSERT: {e_args_zero}, SQL=[{insertSql}]")
                                        if self.globals[SQL][SQL_CONNECTION]:
                                            self.globals[SQL][SQL_CONNECTION].close()

                                        self.globals[SQL][ENABLED] = False  # Disable SQL processing

                        if self.globals[SQL][ENABLED]:
                            try:
                                self.globals[SQL][SQL_CONNECTION].commit()
                            except sql3.Error as e:
                                if self.globals[SQL][SQL_CONNECTION]:
                                    self.globals[SQL][SQL_CONNECTION].rollback()
                                e_args_zero = e.args[0]
                                self.logger.error(f"SMAPPEE ERROR DETECTED WITH SQL [SENSOR] COMMIT: {e_args_zero}")

                                self.globals[SQL][ENABLED] = False  # Disable SQL processing
                            finally:
                                if self.globals[SQL][SQL_CONNECTION]:
                                    self.globals[SQL][SQL_CONNECTION].close()

                                    # reading 'records' entries processing complete

                        if sensorA_NumberOfValues > 0:
                            sensorA_MeanAverage = sensorA_Total / sensorA_NumberOfValues

                        self.logger.debug(f"READINGS - SENSOR [A]: N=[{sensorA_NumberOfValues}], T=[{sensorA_Total}], MEAN=[{sensorA_MeanAverage}],"
                                          f" MIN=[{sensorA_Minimum}], MAX=[{sensorA_Maximum}], L=[{sensorA_Last}]")

                        if sensorB_NumberOfValues > 0:
                            sensorB_MeanAverage = sensorB_Total / sensorB_NumberOfValues

                        self.logger.debug(f"READINGS - SENSOR [B]: N=[{sensorB_NumberOfValues}], T=[{sensorB_Total}], MEAN=[{sensorB_MeanAverage}],"
                                          f" MIN=[{sensorB_Minimum}], MAX=[{sensorB_Maximum}], L=[{sensorB_Last}]")

                        def updateSensor(sensorDev, sensorDesc, sensorValues):
                            try:
                                if sensorDev.id == 0:
                                    return

                                # <Option value="kWh">Kilowatt Hours</Option>
                                # <Option value="m3">Cubic Metres</Option>
                                # <Option value="ft3">Cubic Feet</Option>
                                # <Option value="litres">Litres</Option>
                                # <Option value="gallons">Gallons</Option>

                                timestampUtcLast, lastReadingUtc, sensorTemperature, sensorHumidity, sensorBatteryLevel, sensorTotal, sensorNumberOfValues, sensorMeanAverage, sensorMinimum, sensorMaximum, sensorPrevious, sensorLast = sensorValues

                                self.logger.debug(f"UpdateSensor [1 of 2] [{sensorDesc}]: Temp={sensorTemperature}, Humidity={sensorHumidity}, Battery={sensorBatteryLevel}")
                                self.logger.debug(f"UpdateSensor [2 of 2] [{sensorDesc}]: Total={sensorTotal}, NoV={sensorNumberOfValues}, Mean={sensorMeanAverage},"
                                                  f" Min={sensorMinimum}, Max={sensorMaximum}, Prev={sensorPrevious}, Last={sensorLast}")

                                if (sensorNumberOfValues == 0) and ("curEnergyLevel" in sensorDev.states) and (sensorDev.states[CURRENT_ENERGY_LEVEL] == 0.0):
                                    self.logger.debug(f"UpdateSensor [RETURNING, NO UPDATE] [{sensorDesc}]")

                                    return  # Don't update energy totals if no values to process i.e nothing received since last timestamp

                                updateTimeString = datetime.datetime.fromtimestamp(int(timestampUtcLast / 1000)).strftime('%Y-%b-%d %H:%M')

                                if "readingsLastUpdated" in sensorDev.states:
                                    sensorDev.updateStateOnServer("readingsLastUpdated", updateTimeString)

                                if sensorTemperature != self.globals[SMAPPEES][sensorDev.id][TEST_TEMPERATURE]:
                                    if "temperature" in sensorDev.states:
                                        self.globals[SMAPPEES][sensorDev.id][TEST_TEMPERATURE] = float(sensorTemperature)
                                        temperatureStr = f"{float(sensorTemperature) / 10:1.0f} deg C"
                                        temperatureReformatted = float(f"{float(sensorTemperature) / 10:0.1f}")
                                        sensorDev.updateStateOnServer("temperature", temperatureReformatted, uiValue=temperatureStr)

                                        if "temperatureLastUpdated" in sensorDev.states:
                                            sensorDev.updateStateOnServer("temperatureLastUpdated", updateTimeString)

                                if sensorHumidity != self.globals[SMAPPEES][sensorDev.id][TEST_HUMIDITY]:
                                    if "humidity" in sensorDev.states:
                                        self.globals[SMAPPEES][sensorDev.id][TEST_HUMIDITY] = float(sensorHumidity)
                                        humidityStr = f"{float(sensorHumidity):1.0f}%"
                                        humidityReformatted = float(f"{float(sensorHumidity):0.1f}")
                                        sensorDev.updateStateOnServer("humidity", humidityReformatted,
                                                                      uiValue=humidityStr)

                                        if "humidityLastUpdated" in sensorDev.states:
                                            sensorDev.updateStateOnServer("humidityLastUpdated", updateTimeString)

                                if sensorBatteryLevel != self.globals[SMAPPEES][sensorDev.id][TEST_BATTERY_LEVEL]:
                                    if "batteryLevel" in sensorDev.states:
                                        self.globals[SMAPPEES][sensorDev.id][TEST_BATTERY_LEVEL] = float(sensorBatteryLevel)
                                        batteryLevelStr = f"{float(sensorBatteryLevel):1.0f}%"
                                        batteryLevelReformatted = float(f"{float(sensorBatteryLevel):0.1f}")
                                        sensorDev.updateStateOnServer("batteryLevel", batteryLevelReformatted, uiValue=batteryLevelStr)

                                        if "batteryLevelLastUpdated" in sensorDev.states:
                                            sensorDev.updateStateOnServer("batteryLevelLastUpdated", updateTimeString)

                                unitsKey = self.globals[SMAPPEES][sensorDev.id][UNITS]
                                if unitsKey in self.globals[UNIT_TABLE]:
                                    pass
                                else:
                                    unitsKey = 'default'

                                unitsCurrentUnits = self.globals[UNIT_TABLE][unitsKey][CURRENT_UNITS]
                                unitsAccumUnits = self.globals[UNIT_TABLE][unitsKey][ACCUM_UNITS]
                                unitsmeasurementTimeMultiplier = self.globals[UNIT_TABLE][unitsKey][FUNCTION_QUEUE_REMOVE]
                                unitsformatTotaldivisor = self.globals[UNIT_TABLE][unitsKey][FORMAT_TOTAL_DIVISOR]
                                unitsformatCurrent = self.globals[UNIT_TABLE][unitsKey][FORMAT_CURRENT]
                                unitsformatCurrentUi = unitsformatCurrent + " " + unitsCurrentUnits
                                unitsformatTotal = self.globals[UNIT_TABLE][unitsKey][FORMAT_TOTAL]
                                unitsformatTotalUi = unitsformatTotal + ' ' + unitsAccumUnits

                                if "curEnergyLevel" in sensorDev.states:
                                    if commandSentToSmappee == 'RESET_SENSOR_CONSUMPTION':
                                        self.globals[SMAPPEES][sensorDev.id][CURRENT_ENERGY_LEVEL] = 0.0
                                        dataToUpdateStr = f"{unitsformatCurrent} {self.globals[SMAPPEES][sensorDev.id][CURRENT_ENERGY_LEVEL]} {unitsCurrentUnits}"
                                        sensorDev.updateStateOnServer("curEnergyLevel", self.globals[SMAPPEES][sensorDev.id][CURRENT_ENERGY_LEVEL], uiValue=dataToUpdateStr)
                                        sensorDev.updateStateImageOnServer(indigo.kStateImageSel.EnergyMeterOff)

                                    readingOption = sensorDev.pluginProps["optionsEnergyMeterCurPower"]  # mean, minimum, maximum, last

                                    dataToUpdate = 0.0
                                    if readingOption == 'mean':  # mean, minimum, maximum, last
                                        if sensorNumberOfValues > 0:
                                            dataToUpdate = (sensorMeanAverage * 60) / 5
                                        else:
                                            lastReadingUtc_minus_600000 = lastReadingUtc - 600000
                                            self.logger.debug(f"SENSOR {sensorDesc}: [MEAN]"
                                                              f" CL=[{sensorLast}], UTCL=[{timestampUtcLast}],"
                                                              f" LRUTC=[{lastReadingUtc}], LRUTC600=[{lastReadingUtc_minus_600000}]")
                                            if sensorLast > 0.0 and timestampUtcLast != 0 and timestampUtcLast > (lastReadingUtc - 600000):
                                                dataToUpdate = sensorLast * unitsmeasurementTimeMultiplier
                                    elif readingOption == 'minimum':
                                        if sensorNumberOfValues > 0:
                                            dataToUpdate = sensorMinimum * unitsmeasurementTimeMultiplier
                                        else:
                                            lastReadingUtc_minus_600000 = lastReadingUtc - 600000
                                            self.logger.debug(f"SENSOR {sensorDesc}: [MINIMUM]"
                                                              f" CL=[{sensorLast}], UTCL=[{timestampUtcLast}],"
                                                              f" LRUTC=[{lastReadingUtc}], LRUTC600=[{lastReadingUtc_minus_600000}]")
                                            if sensorLast > 0.0 and timestampUtcLast != 0 and timestampUtcLast > (lastReadingUtc - 600000):
                                                dataToUpdate = sensorLast * unitsmeasurementTimeMultiplier
                                    elif readingOption == 'maximum':
                                        if sensorNumberOfValues > 0:
                                            watts = sensorMaximum * unitsmeasurementTimeMultiplier
                                        else:
                                            lastReadingUtc_minus_600000 = lastReadingUtc - 600000
                                            self.logger.debug(f"SENSOR {sensorDesc}: [MAXIMUM]"
                                                              f" CL=[{sensorLast}], UTCL=[{timestampUtcLast}],"
                                                              f" LRUTC=[{lastReadingUtc}], LRUTC600=[{lastReadingUtc_minus_600000}]")
                                            if sensorLast > 0.0 and timestampUtcLast != 0 and timestampUtcLast > (lastReadingUtc - 600000):
                                                dataToUpdate = sensorLast * unitsmeasurementTimeMultiplier
                                    else:  # Assume last
                                        lastReadingUtc_minus_600000 = lastReadingUtc - 600000
                                        self.logger.debug(f"SENSOR {sensorDesc}:"
                                                          f" [LAST] CL=[{sensorLast}], UTCL=[{timestampUtcLast}],"
                                                          f" LRUTC=[{lastReadingUtc}], LRUTC600=[{lastReadingUtc_minus_600000}]")
                                        if sensorLast > 0.0 and timestampUtcLast != 0 and timestampUtcLast > (lastReadingUtc - 600000):
                                            dataToUpdate = sensorLast * unitsmeasurementTimeMultiplier

                                    currentTimeUtc = int(time.mktime(indigo.server.getTime().timetuple()))
                                    currentTimeMinus6MinsUtc = int((currentTimeUtc - 360) * 1000)  # Subtract 5 minutes (360 seconds)

                                    self.logger.debug(f"SENSOR {sensorDesc}: [TIME CHECK] currentTimeUtc=[{currentTimeUtc}], currentTimeMinus6MinsUtc=[{currentTimeMinus6MinsUtc}],"
                                                      f" timestampUtcLast=[{timestampUtcLast}]")
                                    if timestampUtcLast < currentTimeMinus6MinsUtc:
                                        dataToUpdate = 0.0

                                    dataToUpdateStr = f"{dataToUpdate:.2f} {unitsCurrentUnits}"
                                    if not self.globals[SMAPPEES][sensorDev.id][HIDE_ENERGY_METER_CURRENT_POWER]:
                                        self.logger.info(f"received '{sensorDev.name}' power load reading: {dataToUpdateStr}")

                                    sensorDev.updateStateOnServer("curEnergyLevel", dataToUpdate, uiValue=dataToUpdateStr)
                                    sensorDev.updateStateImageOnServer(indigo.kStateImageSel.EnergyMeterOn)

                                if sensorNumberOfValues != 0 and "accumEnergyTotal" in sensorDev.states:

                                    if commandSentToSmappee == COMMAND_RESET_SENSOR_CONSUMPTION:
                                        self.globals[SMAPPEES][sensorDev.id][ACCUMULATED_ENERGY_TOTAL] = 0.0
                                        dataToUpdateStr = str(unitsformatTotalUi % (self.globals[SMAPPEES][sensorDev.id][ACCUMULATED_ENERGY_TOTAL]))
                                        sensorDev.updateStateOnServer("accumEnergyTotal", self.globals[SMAPPEES][sensorDev.id][ACCUMULATED_ENERGY_TOTAL], uiValue=dataToUpdateStr)

                                    dataToUpdate = float(sensorDev.states.get("accumEnergyTotal", 0))
                                    dataToUpdate += float(sensorTotal / unitsformatTotaldivisor)
                                    dataToUpdateStr = str(unitsformatTotalUi % dataToUpdate)
                                    dataToUpdateReformatted = str(unitsformatTotal % dataToUpdate)
                                    sensorDev.updateStateOnServer("accumEnergyTotal", dataToUpdateReformatted, uiValue=dataToUpdateStr)

                                    dataUnitCost = self.globals[SMAPPEES][sensorDev.id][UNIT_COST]
                                    dailyStandingCharge = self.globals[SMAPPEES][sensorDev.id][DAILY_STANDING_CHARGE]
                                    # amountGross = 0.00
                                    amountGrossStr = "0.00"
                                    if dataUnitCost > 0.00:
                                        amountGross = (dailyStandingCharge + (dataToUpdate * dataUnitCost))
                                        amountGrossReformatted = float(f"{amountGross:0.2f}")
                                        amountGrossStr = f"{amountGrossReformatted:.2f} {self.globals[SMAPPEES][sensorDev.id][CURRENCY_CODE]}"
                                        sensorDev.updateStateOnServer("dailyTotalCost", amountGrossReformatted, uiValue=amountGrossStr)

                                    if not self.globals[SMAPPEES][sensorDev.id][HIDE_ENERGY_METER_ACCUMULATED_POWER]:
                                        if dataUnitCost == 0.00 or self.globals[SMAPPEES][sensorDev.id][HIDE_ENERGY_METER_ACCUMULATED_POWER_COST]:
                                            self.logger.info(f"received '{sensorDev.name}' energy total: {dataToUpdateStr}")
                                        else:
                                            self.logger.info(f"received '{sensorDev.name}' energy total: {dataToUpdateStr} (Gross {amountGrossStr})")

                                self.globals[SMAPPEES][sensorDev.id][LAST_READING_SENSOR_UTC] = timestampUtc

                            except Exception as error_message:
                                self.exception_handler(error_message, True)  # Log error and display failing statement

                        if sensorA_DevId != 0:
                            sensorA_Dev = indigo.devices[sensorA_DevId]
                            sensorValues = (
                                timestampUtcLast, lastReadingSensorA_Utc, sensorA_Temperature, sensorA_Humidity,
                                sensorA_BatteryLevel, sensorA_Total, sensorA_NumberOfValues, sensorA_MeanAverage,
                                sensorA_Minimum, sensorA_Maximum, sensorA_Previous, sensorA_Last)
                            updateSensor(sensorA_Dev, 'A', sensorValues)

                        if sensorB_DevId != 0:
                            sensorB_Dev = indigo.devices[sensorB_DevId]
                            sensorValues = (
                                timestampUtcLast, lastReadingSensorB_Utc, sensorB_Temperature, sensorB_Humidity,
                                sensorB_BatteryLevel, sensorB_Total, sensorB_NumberOfValues, sensorB_MeanAverage,
                                sensorB_Minimum, sensorB_Maximum, sensorB_Previous, sensorB_Last)
                            updateSensor(sensorB_Dev, 'B', sensorValues)

                        break

        except Exception as exception_error:
            self.exception_handler(exception_error, True)  # Log error and display failing statement

    def handleSmappeeResponse(self, commandSentToSmappee, responseLocationId, responseFromSmappee):

        # This method handles responses from Smappee to commands sent to Smappee

        self.currentTime = indigo.server.getTime()

        try:
            # First check for internal calls not involving an external communication with the Smappee
            if commandSentToSmappee == COMMAND_NEW_SENSOR:
                # SPECIAL CASE - NOT ACTUALLY A RESPONSE FROM SMAPPEE
                self.handleCreateNewSensor(commandSentToSmappee, responseLocationId, responseFromSmappee)
                return
            if commandSentToSmappee == COMMAND_NEW_APPLIANCE:
                # SPECIAL CASE - NOT ACTUALLY A RESPONSE FROM SMAPPEE
                self.handleCreateNewAppliance(commandSentToSmappee, responseLocationId, responseFromSmappee)
                return
            if commandSentToSmappee == COMMAND_NEW_ACTUATOR:
                # SPECIAL CASE - NOT ACTUALLY A RESPONSE FROM SMAPPEE
                self.handleCreateNewActuator(commandSentToSmappee, responseLocationId, responseFromSmappee)
                return

            # Now do some basic validation on the Smappee response and decode it

            # validSmappeeResponse, decodedSmappeeResponse = self.validateSmappeResponse(commandSentToSmappee,
            #                                                                            responseLocationId,
            #                                                                            responseFromSmappee)
            # if not validSmappeeResponse:
            #     # Response received from Smappee is invalid
            #     return

            # At this point we have a decoded response
            if commandSentToSmappee == COMMAND_GET_EVENTS:
                self.handleGetEvents(responseLocationId, responseFromSmappee)
                return

            if commandSentToSmappee == COMMAND_INITIALISE or commandSentToSmappee == COMMAND_REFRESH_TOKEN:
                self.handleInitialise(commandSentToSmappee, responseLocationId, responseFromSmappee)
                return

            if commandSentToSmappee == COMMAND_GET_SERVICE_LOCATIONS:
                self.handleGetServiceLocations(responseLocationId, responseFromSmappee)
                return

            if commandSentToSmappee == COMMAND_GET_SERVICE_LOCATION_INFO:
                self.handleGetServiceLocationInfo(responseLocationId, responseFromSmappee)
                return

            if commandSentToSmappee == COMMAND_GET_CONSUMPTION or commandSentToSmappee == COMMAND_RESET_CONSUMPTION:
                self.handleGetConsumption(commandSentToSmappee, responseLocationId, responseFromSmappee)
                return

            if commandSentToSmappee == COMMAND_GET_SENSOR_CONSUMPTION or commandSentToSmappee == COMMAND_RESET_SENSOR_CONSUMPTION:
                self.handleGetSensorConsumption(commandSentToSmappee, responseLocationId, responseFromSmappee)
                return

        except Exception as exception_error:
            self.exception_handler(exception_error, True)  # Log error and display failing statement

    def setSmappeeServiceLocationIdToDevId(self, function, smappeeDeviceTypeId, serviceLocationId, devId, smappeeAddress, devName):
        try:

            if serviceLocationId == "" or serviceLocationId == "NONE":
                return

            if serviceLocationId not in self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID]:
                self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID] = dict()
                self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId] = dict()
                self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][NAME] = "HOME-HOME"
                self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][ELECTRICITY_ID] = 0
                self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][SOLAR_ID] = 0
                self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][ELECTRICITY_NET_ID] = 0
                self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][ELECTRICITY_SAVED_ID] = 0
                self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][SOLAR_EXPORTED_ID] = 0
                self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][SENSOR_IDS] = dict()
                self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][APPLIANCE_IDS] = dict()
                self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][ACTUATOR_IDS] = dict()

            smappeeAddress = str(smappeeAddress)
            if function == FUNCTION_ADD_UPDATE:
                if smappeeDeviceTypeId == 'smappeeElectricity':
                    self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][ELECTRICITY_ID] = devId
                elif smappeeDeviceTypeId == 'smappeeElectricityNet':
                    self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][ELECTRICITY_NET_ID] = devId
                elif smappeeDeviceTypeId == 'smappeeElectricitySaved':
                    self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][ELECTRICITY_SAVED_ID] = devId
                elif smappeeDeviceTypeId == 'smappeeSolar':
                    self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][SOLAR_ID] = devId
                elif smappeeDeviceTypeId == 'smappeeSolarUsed':
                    self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][SOLAR_USED_ID] = devId
                elif smappeeDeviceTypeId == 'smappeeSolarExported':
                    self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][SOLAR_EXPORTED_ID] = devId
                elif smappeeDeviceTypeId == 'smappeeSensor':
                    if smappeeAddress not in self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][SENSOR_IDS]:
                        self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][SENSOR_IDS][
                            smappeeAddress] = dict()
                        self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][SENSOR_IDS][smappeeAddress][
                            QUEUED_ADD] = False
                        self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][SENSOR_IDS][smappeeAddress][
                            QUEUED_REMOVE] = False
                        self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][SENSOR_IDS][smappeeAddress][
                            DEV_ID] = 0
                    if self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][SENSOR_IDS][smappeeAddress][
                            DEV_ID] == 0:
                        self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][SENSOR_IDS][smappeeAddress][
                            DEV_ID] = devId
                    self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][SENSOR_IDS][smappeeAddress][
                        NAME] = str(devName)
                    self.logger.debug(f"setSmappeeServiceLocationIdToDevId [FF-E][SENSOR] - [{self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][SENSOR_IDS]}]")
                elif smappeeDeviceTypeId == 'smappeeAppliance':
                    if smappeeAddress not in self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][APPLIANCE_IDS]:
                        self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][APPLIANCE_IDS][
                            smappeeAddress] = dict()
                        self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][APPLIANCE_IDS][
                            smappeeAddress][QUEUED_ADD] = False
                        self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][APPLIANCE_IDS][
                            smappeeAddress][QUEUED_REMOVE] = False
                    self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][APPLIANCE_IDS][smappeeAddress][
                        DEV_ID] = devId
                    self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][APPLIANCE_IDS][smappeeAddress][
                        NAME] = str(devName)
                elif smappeeDeviceTypeId == 'smappeeActuator':
                    if smappeeAddress not in self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][ACTUATOR_IDS]:
                        self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][ACTUATOR_IDS][
                            smappeeAddress] = dict()
                        self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][ACTUATOR_IDS][
                            smappeeAddress][QUEUED_ADD] = False
                        self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][ACTUATOR_IDS][
                            smappeeAddress][QUEUED_REMOVE] = False
                    self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][ACTUATOR_IDS][smappeeAddress][
                        DEV_ID] = devId
                    self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][ACTUATOR_IDS][smappeeAddress][
                        NAME] = str(devName)

            elif function == FUNCTION_STOP:
                if smappeeDeviceTypeId == 'smappeeElectricity':
                    self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][ELECTRICITY_ID] = 0
                elif smappeeDeviceTypeId == 'smappeeElectricityNet':
                    self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][ELECTRICITY_ID] = 0
                elif smappeeDeviceTypeId == 'smappeeElectricitySaved':
                    self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][ELECTRICITY_SAVED_ID] = 0
                elif smappeeDeviceTypeId == 'smappeeSolar':
                    self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][SOLAR_ID] = 0
                elif smappeeDeviceTypeId == 'smappeeSolarUsed':
                    self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][SOLAR_USED_ID] = 0
                elif smappeeDeviceTypeId == 'smappeeSolarExported':
                    self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][SOLAR_EXPORTED_ID] = 0
                elif smappeeDeviceTypeId == 'smappeeSensor':
                    self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][SENSOR_IDS][smappeeAddress][
                        QUEUED_ADD] = False
                    self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][SENSOR_IDS][smappeeAddress][
                        QUEUED_REMOVE] = False
                    self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][SENSOR_IDS][smappeeAddress][
                        DEV_ID] = 0
                elif smappeeDeviceTypeId == 'smappeeAppliance':
                    self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][APPLIANCE_IDS][smappeeAddress][
                        DEV_ID] = 0
                elif smappeeDeviceTypeId == 'smappeeActuator':
                    self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][ACTUATOR_IDS][smappeeAddress][
                        DEV_ID] = 0

            elif function == FUNCTION_QUEUE_ADD:
                if smappeeDeviceTypeId == 'smappeeSensor':
                    if smappeeAddress not in self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][SENSOR_IDS]:
                        self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][APPLIANCE_IDS][
                            smappeeAddress] = dict()
                    self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][SENSOR_IDS][smappeeAddress][
                        DEV_ID] = 0
                    self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][SENSOR_IDS][smappeeAddress][
                        NAME] = str(devName)
                    self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][SENSOR_IDS][smappeeAddress][DEVICE_TYPE] = str(smappeeDeviceTypeId)
                    self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][SENSOR_IDS][smappeeAddress][
                        QUEUED_ADD] = True
                elif smappeeDeviceTypeId == 'smappeeAppliance':
                    if smappeeAddress not in self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][APPLIANCE_IDS]:
                        self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][APPLIANCE_IDS][
                            smappeeAddress] = dict()
                    self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][APPLIANCE_IDS][smappeeAddress][
                        DEV_ID] = 0
                    self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][APPLIANCE_IDS][smappeeAddress][
                        NAME] = str(devName)
                    self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][APPLIANCE_IDS][smappeeAddress][
                        QUEUED_ADD] = True
                elif smappeeDeviceTypeId == 'smappeeActuator':
                    if smappeeAddress not in self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][ACTUATOR_IDS]:
                        self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][ACTUATOR_IDS][
                            smappeeAddress] = dict()
                    self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][ACTUATOR_IDS][smappeeAddress][
                        DEV_ID] = 0
                    self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][ACTUATOR_IDS][smappeeAddress][
                        NAME] = str(devName)
                    self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][ACTUATOR_IDS][smappeeAddress][
                        QUEUED_ADD] = True

            elif function == FUNCTION_DEQUEUE:
                if smappeeDeviceTypeId == 'smappeeSensor':
                    if smappeeAddress not in self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][SENSOR_IDS]:
                        self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][SENSOR_IDS][
                            smappeeAddress] = dict()
                    self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][SENSOR_IDS][smappeeAddress][DEV_ID] = devId
                    self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][SENSOR_IDS][smappeeAddress][NAME] = str(devName)
                    self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][SENSOR_IDS][smappeeAddress][QUEUED_ADD] = False
                    self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][SENSOR_IDS][smappeeAddress][QUEUED_REMOVE] = False
                elif smappeeDeviceTypeId == 'smappeeAppliance':
                    if smappeeAddress not in self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][APPLIANCE_IDS]:
                        self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][APPLIANCE_IDS][
                            smappeeAddress] = dict()
                    self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][APPLIANCE_IDS][smappeeAddress][DEV_ID] = devId
                    self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][APPLIANCE_IDS][smappeeAddress][NAME] = str(devName)
                    self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][APPLIANCE_IDS][smappeeAddress][QUEUED_ADD] = False
                    self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][APPLIANCE_IDS][smappeeAddress][QUEUED_REMOVE] = False
                elif smappeeDeviceTypeId == 'smappeeActuator':
                    if smappeeAddress not in self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][ACTUATOR_IDS]:
                        self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][ACTUATOR_IDS][smappeeAddress] = dict()
                    self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][ACTUATOR_IDS][smappeeAddress][DEV_ID] = devId
                    self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][ACTUATOR_IDS][smappeeAddress][NAME] = str(devName)
                    self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][ACTUATOR_IDS][smappeeAddress][QUEUED_ADD] = False
                    self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][ACTUATOR_IDS][smappeeAddress][QUEUED_REMOVE] = False

            elif function == FUNCTION_QUEUE_REMOVE:
                if smappeeDeviceTypeId == 'smappeeSensor':
                    if smappeeAddress not in self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][SENSOR_IDS]:
                        self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][SENSOR_IDS][smappeeAddress] = dict()
                    self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][SENSOR_IDS][smappeeAddress][DEV_ID] = 0
                    self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][SENSOR_IDS][smappeeAddress][NAME] = str(devName)
                    self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][SENSOR_IDS][smappeeAddress][QUEUED_REMOVE] = True
                elif smappeeDeviceTypeId == 'smappeeAppliance':
                    if smappeeAddress not in self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][APPLIANCE_IDS]:
                        self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][APPLIANCE_IDS][smappeeAddress] = dict()
                    self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][APPLIANCE_IDS][smappeeAddress][DEV_ID] = 0
                    self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][APPLIANCE_IDS][smappeeAddress][NAME] = str(devName)
                    self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][APPLIANCE_IDS][smappeeAddress][QUEUED_REMOVE] = True
                elif smappeeDeviceTypeId == 'smappeeActuator':
                    if smappeeAddress not in self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][ACTUATOR_IDS]:
                        self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][ACTUATOR_IDS][smappeeAddress] = dict()
                    self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][ACTUATOR_IDS][smappeeAddress][DEV_ID] = 0
                    self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][ACTUATOR_IDS][smappeeAddress][NAME] = str(devName)
                    self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID][serviceLocationId][ACTUATOR_IDS][smappeeAddress][QUEUED_REMOVE] = True

        except Exception as exception_error:
            self.exception_handler(exception_error, True)  # Log error and display failing statement

    def convertUnicode(self, input):  # TODO - STILL NEEDED ???
        try:
            if isinstance(input, dict):
                return dict([(self.convertUnicode(key), self.convertUnicode(value)) for key, value in input.items()])
            elif isinstance(input, list):
                return [self.convertUnicode(element) for element in input]
            elif isinstance(input, unicode):
                return input.encode('utf-8')
            else:
                return input

        except Exception as exception_error:
            self.exception_handler(exception_error, True)  # Log error and display failing statement

    def validateDeviceConfigUi(self, valuesDict, typeId, devId):
        try:
            if typeId == "smappeeElectricity":
                result = self.validateDeviceConfigUiSmappeeElectricity(valuesDict, typeId, devId)
            elif typeId == "smappeeSolar":
                result = self.validateDeviceConfigUiSmappeeSolar(valuesDict, typeId, devId)
            elif typeId == "smappeeSensor":
                result = self.validateDeviceConfigUiSmappeeSensor(valuesDict, typeId, devId)
            else:
                self.logger.error(f"WARNING: validateDeviceConfigUi TYPEID={typeId} NOT HANDLED")
                result = (True, valuesDict)

            if result[0]:
                return True, result[1]  # True, Valuesdict
            else:
                return False, result[1], result[2]  # True, Valuesdict, ErrorDict

        except Exception as exception_error:
            self.exception_handler(exception_error, True)  # Log error and display failing statement

    def validateDeviceConfigUiSmappeeElectricity(self, valuesDict, typeId, devId):
        try:
            validConfig = True  # Assume config is valid

            self.globals[SMAPPEES][devId][HIDE_ENERGY_METER_CURRENT_POWER] = False
            try:
                if "hideEnergyMeterCurPower" in valuesDict:
                    self.globals[SMAPPEES][devId][HIDE_ENERGY_METER_CURRENT_POWER] = valuesDict["hideEnergyMeterCurPower"]
            except Exception as exception_error:
                self.globals[SMAPPEES][devId][HIDE_ENERGY_METER_CURRENT_POWER] = False

            self.globals[SMAPPEES][devId][HIDE_ENERGY_METER_ACCUMULATED_POWER] = False
            try:
                if "hideEnergyMeterAccumPower" in valuesDict:
                    self.globals[SMAPPEES][devId][HIDE_ENERGY_METER_ACCUMULATED_POWER] = valuesDict["hideEnergyMeterAccumPower"]
            except Exception as exception_error:
                self.globals[SMAPPEES][devId][HIDE_ENERGY_METER_ACCUMULATED_POWER] = False

            self.globals[SMAPPEES][devId][HIDE_ALWAYS_ON_POWER] = False
            try:
                if "hideEnergyMeterAccumPowerCost" in valuesDict:
                    self.globals[SMAPPEES][devId][HIDE_ENERGY_METER_ACCUMULATED_POWER_COST] = valuesDict["hideEnergyMeterAccumPowerCost"]
            except Exception as exception_error:
                self.globals[SMAPPEES][devId][HIDE_ENERGY_METER_ACCUMULATED_POWER_COST] = False

            self.globals[SMAPPEES][devId][HIDE_ALWAYS_ON_POWER] = False
            try:
                if "hideAlwaysOnPower" in valuesDict:
                    self.globals[SMAPPEES][devId][HIDE_ALWAYS_ON_POWER] = valuesDict["hideAlwaysOnPower"]
            except Exception as exception_error:
                self.globals[SMAPPEES][devId][HIDE_ALWAYS_ON_POWER] = False

            try:
                if "currencyCode" in valuesDict:
                    self.globals[SMAPPEES][dev.id][CURRENCY_CODE] = valuesDict["currencyCode"]
                else:
                    self.globals[SMAPPEES][devId][CURRENCY_CODE] = "UKP"
            except Exception as exception_error:
                self.globals[SMAPPEES][devId][CURRENCY_CODE] = "UKP"

            try:
                if "dailyStandingCharge" in valuesDict:
                    if valuesDict["dailyStandingCharge"] == '':
                        self.globals[SMAPPEES][devId][DAILY_STANDING_CHARGE] = 0.00
                    else:
                        try:
                            self.globals[SMAPPEES][devId][DAILY_STANDING_CHARGE] = float(
                                valuesDict["dailyStandingCharge"])
                        except Exception as exception_error:
                            self.globals[SMAPPEES][devId][DAILY_STANDING_CHARGE] = 0.00
                            validConfig = False
                else:
                    self.globals[SMAPPEES][devId][DAILY_STANDING_CHARGE] = 0.00
            except Exception as exception_error:
                self.globals[SMAPPEES][devId][DAILY_STANDING_CHARGE] = 0.00
                validConfig = False

            if not validConfig:
                errorDict = indigo.Dict()
                errorDict["dailyStandingCharge"] = "Daily Standing Charge is invalid"
                errorDict["showAlertText"] = "specify a valid financial amount e.g. '0.25'"
                return False, valuesDict, errorDict

            try:
                if "kwhUnitCost" in valuesDict:
                    if valuesDict["kwhUnitCost"] == '':
                        self.globals[SMAPPEES][devId][KWH_UNIT_COST] = 0.00
                    else:
                        try:
                            self.globals[SMAPPEES][devId][KWH_UNIT_COST] = float(valuesDict["kwhUnitCost"])
                        except Exception as exception_error:
                            self.globals[SMAPPEES][devId][KWH_UNIT_COST] = 0.00
                            validConfig = False
                else:
                    self.globals[SMAPPEES][devId][KWH_UNIT_COST] = 0.00
            except Exception as exception_error:
                self.globals[SMAPPEES][devId][KWH_UNIT_COST] = 0.00
                validConfig = False

            if not validConfig:
                errorDict = indigo.Dict()
                errorDict["kwhUnitCost"] = "The kWh Unit Cost is invalid"
                errorDict["showAlertText"] = "specify a valid financial amount e.g. '0.15'"
                return False, valuesDict, errorDict

            return True, valuesDict

        except Exception as exception_error:
            self.exception_handler(exception_error, True)  # Log error and display failing statement

    def validateDeviceConfigUiSmappeeSolar(self, valuesDict, typeId, devId):
        try:
            self.globals[SMAPPEES][devId][HIDE_SOLAR_METER_CURRENT_GENERATION] = False
            try:
                if "hideSolarMeterCurGeneration" in valuesDict:
                    self.globals[SMAPPEES][devId][HIDE_SOLAR_METER_CURRENT_GENERATION] = valuesDict["hideSolarMeterCurGeneration"]
            except Exception as exception_error:
                self.globals[SMAPPEES][devId][HIDE_SOLAR_METER_CURRENT_GENERATION] = False

            self.globals[SMAPPEES][devId][HIDE_SOLAR_METER_ACCUMULATED_GENERATION] = False
            try:
                if "hideSolarMeterAccumGeneration" in valuesDict:
                    self.globals[SMAPPEES][devId][HIDE_SOLAR_METER_ACCUMULATED_GENERATION] = valuesDict["hideSolarMeterAccumGeneration"]
            except Exception as exception_error:
                self.globals[SMAPPEES][devId][HIDE_SOLAR_METER_ACCUMULATED_GENERATION] = False

            return True, valuesDict

        except Exception as exception_error:
            self.exception_handler(exception_error, True)  # Log error and display failing statement

    def validateDeviceConfigUiSmappeeSensor(self, valuesDict, typeId, devId):
        try:
            validConfig = True  # Assume config is valid

            self.globals[SMAPPEES][devId][HIDE_ENERGY_METER_CURRENT_POWER] = False
            try:
                if "hideEnergyMeterCurPower" in valuesDict:
                    self.globals[SMAPPEES][devId][HIDE_ENERGY_METER_CURRENT_POWER] = valuesDict["hideEnergyMeterCurPower"]
            except Exception as exception_error:
                self.globals[SMAPPEES][devId][HIDE_ENERGY_METER_CURRENT_POWER] = False

            self.globals[SMAPPEES][devId][HIDE_ENERGY_METER_ACCUMULATED_POWER] = False
            try:
                if "hideEnergyMeterAccumPower" in valuesDict:
                    self.globals[SMAPPEES][devId][HIDE_ENERGY_METER_ACCUMULATED_POWER] = valuesDict["hideEnergyMeterAccumPower"]
            except Exception as exception_error:
                self.globals[SMAPPEES][devId][HIDE_ENERGY_METER_ACCUMULATED_POWER] = False

            self.globals[SMAPPEES][devId][HIDE_ALWAYS_ON_POWER] = False
            try:
                if "hideEnergyMeterAccumPowerCost" in valuesDict:
                    self.globals[SMAPPEES][devId][HIDE_ENERGY_METER_ACCUMULATED_POWER_COST] = valuesDict["hideEnergyMeterAccumPowerCost"]
            except Exception as exception_error:
                self.globals[SMAPPEES][devId][HIDE_ENERGY_METER_ACCUMULATED_POWER_COST] = False

            self.globals[SMAPPEES][devId][HIDE_ALWAYS_ON_POWER] = False
            try:
                if "hideAlwaysOnPower" in valuesDict:
                    self.globals[SMAPPEES][devId][HIDE_ALWAYS_ON_POWER] = valuesDict["hideAlwaysOnPower"]
            except Exception as exception_error:
                self.globals[SMAPPEES][devId][HIDE_ALWAYS_ON_POWER] = False

            try:
                if "currencyCode" in valuesDict:
                    self.globals[SMAPPEES][devId][CURRENCY_CODE] = valuesDict[CURRENCY_CODE]
                else:
                    self.globals[SMAPPEES][devId][CURRENCY_CODE] = 'UKP'
            except Exception as exception_error:
                self.globals[SMAPPEES][devId][CURRENCY_CODE] = 'UKP'

            try:
                if "dailyStandingCharge" in valuesDict:
                    if valuesDict["dailyStandingCharge"] == '':
                        self.globals[SMAPPEES][devId][DAILY_STANDING_CHARGE] = 0.00
                    else:
                        try:
                            self.globals[SMAPPEES][devId][DAILY_STANDING_CHARGE] = float(valuesDict["dailyStandingCharge"])
                        except Exception as exception_error:
                            self.globals[SMAPPEES][devId][DAILY_STANDING_CHARGE] = 0.00
                            validConfig = False
                else:
                    self.globals[SMAPPEES][devId][DAILY_STANDING_CHARGE] = 0.00
            except Exception as exception_error:
                self.globals[SMAPPEES][devId][DAILY_STANDING_CHARGE] = 0.00
                validConfig = False

            if not validConfig:
                errorDict = indigo.Dict()
                errorDict["dailyStandingCharge"] = "Daily Standing Charge is invalid"
                errorDict["showAlertText"] = "specify a valid financial amount e.g. '0.25'"
                return False, valuesDict, errorDict

            try:
                if "unitCost" in valuesDict:
                    if valuesDict["unitCost"] == '':
                        self.globals[SMAPPEES][devId][UNIT_COST] = 0.00
                    else:
                        try:
                            self.globals[SMAPPEES][devId][KWH_UNIT_COST] = float(valuesDict["unitCost"])
                        except Exception as exception_error:
                            self.globals[SMAPPEES][devId][KWH_UNIT_COST] = 0.00
                            validConfig = False
                else:
                    self.globals[SMAPPEES][devId][KWH_UNIT_COST] = 0.00
            except Exception as exception_error:
                self.globals[SMAPPEES][devId][KWH_UNIT_COST] = 0.00
                validConfig = False

            if not validConfig:
                errorDict = indigo.Dict()
                errorDict["kwhUnitCost"] = "The Unit Cost is invalid"
                errorDict["showAlertText"] = "specify a valid financial amount e.g. '0.15'"
                return False, valuesDict, errorDict

            return True, valuesDict

        except Exception as exception_error:
            self.exception_handler(exception_error, True)  # Log error and display failing statement

    def deviceStartComm(self, dev):
        try:
            if dev.deviceTypeId == "smappeeElectricity" or dev.deviceTypeId == "smappeeElectricityNet" or dev.deviceTypeId == "smappeeElectricitySaved" or dev.deviceTypeId == "smappeeSolar" or dev.deviceTypeId == "smappeeSolarUsed" or dev.deviceTypeId == "smappeeSolarExported" or dev.deviceTypeId == "smappeeSensor" or dev.deviceTypeId == "smappeeAppliance" or dev.deviceTypeId == "smappeeActuator":
                pass
            else:
                self.logger.error(f"Failed to start Smappee Appliance [{dev.name}]: Device type [{dev.deviceTypeId}] not known by plugin.")
                return

            dev.stateListOrDisplayStateIdChanged()  # Ensure latest devices.xml is being used

            try:
                # Initialise internal to plugin smappee electricity states to default values
                if dev.deviceTypeId == "smappeeElectricity":

                    self.logger.debug(f"SMAPPEE DEV [ELECTRICITY] START smappeeServiceLocationIdToDevId = [{self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID]}]")

                    self.globals[CONFIG][SUPPORTS_ELECTRICITY] = True

                    self.serviceLocationId = str(dev.pluginProps["serviceLocationId"])

                    self.logger.debug(f"SMAPPEE DEV [ELECTRICITY] START self.serviceLocationId = [{self.serviceLocationId}]")

                    self.setSmappeeServiceLocationIdToDevId(FUNCTION_ADD_UPDATE, 'smappeeElectricity', self.serviceLocationId, dev.id, "", "")

                    self.logger.debug(f"SMAPPEE DEV [ELECTRICITY] START smappeeServiceLocationIdToDevId [2] = [{self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID]}]")

                    self.globals[SMAPPEES][dev.id] = dict()
                    self.globals[SMAPPEES][dev.id][SERVICE_LOCATION_ID] = dev.pluginProps["serviceLocationId"]
                    self.globals[SMAPPEES][dev.id][SERVICE_LOCATION_NAME] = dev.pluginProps["serviceLocationName"]
                    self.globals[SMAPPEES][dev.id][NAME] = dev.name
                    self.globals[SMAPPEES][dev.id][LONGDITUDE] = 0
                    self.globals[SMAPPEES][dev.id][LATITUDE] = 0
                    self.globals[SMAPPEES][dev.id][ELECTRICITY_COST] = 0
                    self.globals[SMAPPEES][dev.id][ELECTRICITY_CURRENCY] = 0
                    self.globals[SMAPPEES][dev.id][CURRENT_ENERGY_LEVEL] = 0.0
                    self.globals[SMAPPEES][dev.id][ACCUMULATED_ENERGY_TOTAL] = 0.0
                    self.globals[SMAPPEES][dev.id][DAILY_TOTAL_COST] = 0.0
                    self.globals[SMAPPEES][dev.id][ALWAYS_ON] = 0.0
                    self.globals[SMAPPEES][dev.id][LAST_RESET_ELECTRICITY_UTC] = 0
                    self.globals[SMAPPEES][dev.id][LAST_READING_ELECTRICITY_UTC] = 0
                    self.globals[SMAPPEES][dev.id][LAST_READING_ELECTRICITY] = 0.0
                    try:
                        self.globals[SMAPPEES][dev.id][HIDE_ENERGY_METER_CURRENT_POWER] = dev.pluginProps["hideEnergyMeterCurPower"]
                    except Exception as exception_error:
                        self.globals[SMAPPEES][dev.id][HIDE_ENERGY_METER_CURRENT_POWER] = False
                    try:
                        self.globals[SMAPPEES][dev.id][HIDE_ENERGY_METER_ACCUMULATED_POWER] = dev.pluginProps["hideEnergyMeterAccumPower"]
                    except Exception as exception_error:
                        self.globals[SMAPPEES][dev.id][HIDE_ENERGY_METER_ACCUMULATED_POWER] = False
                    try:
                        self.globals[SMAPPEES][dev.id][HIDE_ENERGY_METER_ACCUMULATED_POWER_COST] = dev.pluginProps["hideEnergyMeterAccumPowerCost"]
                    except Exception as exception_error:
                        self.globals[SMAPPEES][dev.id][HIDE_ENERGY_METER_ACCUMULATED_POWER_COST] = False
                    try:
                        self.globals[SMAPPEES][dev.id][HIDE_ALWAYS_ON_POWER] = dev.pluginProps["hideAlwaysOnPower"]
                    except Exception as exception_error:
                        self.globals[SMAPPEES][dev.id][HIDE_ALWAYS_ON_POWER] = False
                    try:
                        self.globals[SMAPPEES][dev.id][CURRENCY_CODE] = dev.pluginProps["currencyCode"]
                    except Exception as exception_error:
                        self.globals[SMAPPEES][dev.id][CURRENCY_CODE] = 'UKP'
                    try:
                        self.globals[SMAPPEES][dev.id][DAILY_STANDING_CHARGE] = float(dev.pluginProps["dailyStandingCharge"])
                    except Exception as exception_error:
                        self.globals[SMAPPEES][dev.id][DAILY_STANDING_CHARGE] = 8.88  # To make it obvious there is an error
                    try:
                        self.globals[SMAPPEES][dev.id][KWH_UNIT_COST] = float(dev.pluginProps["kwhUnitCost"])
                    except Exception as exception_error:
                        self.globals[SMAPPEES][dev.id][KWH_UNIT_COST] = 9.99  # To make it obvious there is an error

                    if "curEnergyLevel" in dev.states:
                        wattStr = f"{self.globals[SMAPPEES][dev.id][CURRENT_ENERGY_LEVEL]:3.0f} Watts"
                        dev.updateStateOnServer("curEnergyLevel", self.globals[SMAPPEES][dev.id][CURRENT_ENERGY_LEVEL], uiValue=wattStr)

                    if "accumEnergyTotal" in dev.states:
                        kwhStr = f"{self.globals[SMAPPEES][dev.id][ACCUMULATED_ENERGY_TOTAL]:3.0f} kWh"
                        dev.updateStateOnServer("accumEnergyTotal", self.globals[SMAPPEES][dev.id][ACCUMULATED_ENERGY_TOTAL], uiValue=kwhStr)

                    if "alwaysOn" in dev.states:
                        wattStr = f"{self.globals[SMAPPEES][dev.id][ALWAYS_ON]:3.0f} Watts"
                        dev.updateStateOnServer("alwaysOn", self.globals[SMAPPEES][dev.id][ALWAYS_ON], uiValue=wattStr)

                    if "dailyTotalCost" in dev.states:
                        costStr = f"{self.globals[SMAPPEES][dev.id][DAILY_TOTAL_COST]:3.0f}"
                        dev.updateStateOnServer("dailyTotalCost", self.globals[SMAPPEES][dev.id][DAILY_TOTAL_COST], uiValue=costStr)

                    dev.updateStateOnServer("smappeeElectricityOnline", False, uiValue='offline')

                    if self.globals[PLUGIN_INITIALIZED] and self.serviceLocationId != "":
                        self.globals[QUEUES][SEND_TO_SMAPPEE].put([COMMAND_GET_CONSUMPTION, str(self.serviceLocationId)])

                    self.logger.info(f"Started '{dev.name}' at address [{dev.address}]")

                # Initialise internal to plugin smappee electricity net states to default values
                elif dev.deviceTypeId == "smappeeElectricityNet":

                    self.logger.debug(
                        f"SMAPPEE DEV [ELECTRICITY NET] START smappeeServiceLocationIdToDevId = [{self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID]}]")

                    self.globals[CONFIG][SUPPORTS_ELECTRICITY_NET] = True

                    self.serviceLocationId = str(dev.pluginProps["serviceLocationId"])

                    self.logger.debug(
                        f"SMAPPEE DEV [ELECTRICITY NET] START self.serviceLocationId = [{self.serviceLocationId}]")

                    self.setSmappeeServiceLocationIdToDevId(FUNCTION_ADD_UPDATE, 'smappeeElectricityNet', self.serviceLocationId, dev.id, '0', '0')

                    self.logger.debug(f"SMAPPEE DEV [ELECTRICITY NET] START smappeeServiceLocationIdToDevId [2] = [{self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID]}]")

                    self.globals[SMAPPEES][dev.id] = dict()
                    self.globals[SMAPPEES][dev.id][SERVICE_LOCATION_ID] = dev.pluginProps["serviceLocationId"]
                    self.globals[SMAPPEES][dev.id][SERVICE_LOCATION_NAME] = dev.pluginProps["serviceLocationName"]
                    self.globals[SMAPPEES][dev.id][NAME] = dev.name
                    self.globals[SMAPPEES][dev.id][ELECTRICITY_COST] = 0
                    self.globals[SMAPPEES][dev.id][ELECTRICITY_CURRENCY] = 0
                    self.globals[SMAPPEES][dev.id][CURRENT_ENERGY_LEVEL] = 0.0
                    self.globals[SMAPPEES][dev.id][ACCUMULATED_ENERGY_TOTAL] = 0.0
                    self.globals[SMAPPEES][dev.id][DAILY_NET_TOTAL_COST] = 0.0
                    self.globals[SMAPPEES][dev.id][LAST_RESET_ELECTRICITY_NET_UTC] = 0
                    self.globals[SMAPPEES][dev.id][LAST_READING_ELECTRICITY_NET_UTC] = 0
                    self.globals[SMAPPEES][dev.id][LAST_READING_ELECTRICITY_NET] = 0.0
                    try:
                        self.globals[SMAPPEES][dev.id][HIDE_ENERGY_METER_CURRENT_NET_POWER] = dev.pluginProps["hideEnergyMeterCurNetPower"]
                    except Exception as exception_error:
                        self.globals[SMAPPEES][dev.id][HIDE_ENERGY_METER_CURRENT_NET_POWER] = False
                    try:
                        self.globals[SMAPPEES][dev.id][HIDE_ENERGY_METER_CURRENT_ZERO_NET_POWER] = dev.pluginProps["hideEnergyMeterCurZeroNetPower"]
                    except Exception as exception_error:
                        self.globals[SMAPPEES][dev.id][HIDE_ENERGY_METER_CURRENT_ZERO_NET_POWER] = False
                    try:
                        self.globals[SMAPPEES][dev.id][HIDE_ENERGY_METER_ACCUMULATED_NET_POWER] = dev.pluginProps["hideEnergyMeterAccumNetPower"]
                    except Exception as exception_error:
                        self.globals[SMAPPEES][dev.id][HIDE_ENERGY_METER_ACCUMULATED_NET_POWER] = False
                    try:
                        self.globals[SMAPPEES][dev.id][HIDE_ENERGY_METER_ACCUMULATED_NET_POWER_COST] = dev.pluginProps["hideEnergyMeterAccumNetPowerCost"]
                    except Exception as exception_error:
                        self.globals[SMAPPEES][dev.id][HIDE_ENERGY_METER_ACCUMULATED_NET_POWER_COST] = False
                    try:
                        self.globals[SMAPPEES][dev.id]['hideNoChangeEnergyMeterAccumNetPower'] = dev.pluginProps["hideNoChangeEnergyMeterAccumNetPower"]
                    except Exception as exception_error:
                        self.globals[SMAPPEES][dev.id]['hideNoChangeEnergyMeterAccumNetPower'] = False

                    if "curEnergyLevel" in dev.states:
                        wattStr = f"{self.globals[SMAPPEES][dev.id][CURRENT_ENERGY_LEVEL]:3.0f} Watts"
                        dev.updateStateOnServer("curEnergyLevel", self.globals[SMAPPEES][dev.id][CURRENT_ENERGY_LEVEL], uiValue=wattStr)

                    if "accumEnergyTotal" in dev.states:
                        kwhStr = f"{self.globals[SMAPPEES][dev.id][ACCUMULATED_ENERGY_TOTAL]:3.0f} kWh"
                        dev.updateStateOnServer("accumEnergyTotal", self.globals[SMAPPEES][dev.id][ACCUMULATED_ENERGY_TOTAL], uiValue=kwhStr)

                    if "dailyNetTotalCost" in dev.states:
                        costStr = f"{self.globals[SMAPPEES][dev.id][DAILY_NET_TOTAL_COST]:3.0f}"
                        dev.updateStateOnServer("dailyNetTotalCost", self.globals[SMAPPEES][dev.id][DAILY_NET_TOTAL_COST], uiValue=costStr)

                    dev.updateStateOnServer("smappeeElectricityNetOnline", False, uiValue='offline')

                    # if self.globals[PLUGIN_INITIALIZED] == True and self.serviceLocationId != "":
                    #     self.globals[QUEUES][SEND_TO_SMAPPEE].put([COMMAND_GET_CONSUMPTION,str(self.serviceLocationId)])

                    self.logger.info(f"Started '{dev.name}' at address [{dev.address}]")

                # Initialise internal to plugin smappee electricity Saved states to default values
                elif dev.deviceTypeId == "smappeeElectricitySaved":

                    self.logger.debug(f"SMAPPEE DEV [ELECTRICITY SAVED] START smappeeServiceLocationIdToDevId = [{self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID]}]")

                    self.globals[CONFIG][SUPPORTS_ELECTRICITY_SAVED] = True

                    self.serviceLocationId = str(dev.pluginProps["serviceLocationId"])

                    self.logger.debug(f"SMAPPEE DEV [ELECTRICITY SAVED] START self.serviceLocationId = [{self.serviceLocationId}]")

                    self.setSmappeeServiceLocationIdToDevId(FUNCTION_ADD_UPDATE, 'smappeeElectricitySaved', self.serviceLocationId, dev.id, '0', '0')

                    self.logger.debug(f"SMAPPEE DEV [ELECTRICITY SAVED] START smappeeServiceLocationIdToDevId [2] = [{self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID]}]")

                    self.globals[SMAPPEES][dev.id] = dict()
                    self.globals[SMAPPEES][dev.id][SERVICE_LOCATION_ID] = dev.pluginProps["serviceLocationId"]
                    self.globals[SMAPPEES][dev.id][SERVICE_LOCATION_NAME] = dev.pluginProps["serviceLocationName"]
                    self.globals[SMAPPEES][dev.id][NAME] = dev.name
                    self.globals[SMAPPEES][dev.id][ELECTRICITY_COST] = 0
                    self.globals[SMAPPEES][dev.id][ELECTRICITY_CURRENCY] = 0
                    self.globals[SMAPPEES][dev.id][CURRENT_ENERGY_LEVEL] = 0.0
                    self.globals[SMAPPEES][dev.id][ACCUMULATED_ENERGY_TOTAL] = 0.0
                    self.globals[SMAPPEES][dev.id][DAILY_TOTAL_COST_SAVING] = 0.0
                    self.globals[SMAPPEES][dev.id][LAST_RESET_ELECTRICITY_SAVED_UTC] = 0
                    self.globals[SMAPPEES][dev.id][LAST_READING_ELECTRICITY_SAVED_UTC] = 0
                    self.globals[SMAPPEES][dev.id][LAST_READING_ELECTRICITY_SAVED] = 0.0
                    try:
                        self.globals[SMAPPEES][dev.id][HIDE_ENERGY_METER_CURRENT_SAVED_POWER] = dev.pluginProps["hideEnergyMeterCurSavedPower"]
                    except Exception as exception_error:
                        self.globals[SMAPPEES][dev.id][HIDE_ENERGY_METER_CURRENT_SAVED_POWER] = False
                    try:
                        self.globals[SMAPPEES][dev.id][HIDE_ENERGY_METER_CURRENT_ZERO_NET_POWER] = dev.pluginProps["hideEnergyMeterCurZeroSavedPower"]
                    except Exception as exception_error:
                        self.globals[SMAPPEES][dev.id][HIDE_ENERGY_METER_CURRENT_ZERO_NET_POWER] = False
                    try:
                        self.globals[SMAPPEES][dev.id][HIDE_ENERGY_METER_ACCUMULATED_SAVED_POWER] = dev.pluginProps["hideEnergyMeterAccumSavedPower"]
                    except Exception as exception_error:
                        self.globals[SMAPPEES][dev.id][HIDE_ENERGY_METER_ACCUMULATED_SAVED_POWER] = False
                    try:
                        self.globals[SMAPPEES][dev.id][HIDE_ENERGY_METER_ACCUMULATED_SAVED_POWER_COST] = dev.pluginProps["hideEnergyMeterAccumSavedPowerCost"]
                    except Exception as exception_error:
                        self.globals[SMAPPEES][dev.id][HIDE_ENERGY_METER_ACCUMULATED_SAVED_POWER_COST] = False
                    try:
                        self.globals[SMAPPEES][dev.id][HIDE_NO_CHANGE_ENERGY_METER_ACCUMULATED_SAVED_POWER] = dev.pluginProps["hideNoChangeEnergyMeterAccumSavedPower"]
                    except Exception as exception_error:
                        self.globals[SMAPPEES][dev.id][HIDE_NO_CHANGE_ENERGY_METER_ACCUMULATED_SAVED_POWER] = False

                    if "curEnergyLevel" in dev.states:
                        wattStr = f"{self.globals[SMAPPEES][dev.id][CURRENT_ENERGY_LEVEL]:3.0f} Watts"
                        dev.updateStateOnServer("curEnergyLevel", self.globals[SMAPPEES][dev.id][CURRENT_ENERGY_LEVEL], uiValue=wattStr)

                    if "accumEnergyTotal" in dev.states:
                        kwhStr = f"{self.globals[SMAPPEES][dev.id][ACCUMULATED_ENERGY_TOTAL]:3.0f} kWh"
                        dev.updateStateOnServer("accumEnergyTotal", self.globals[SMAPPEES][dev.id][ACCUMULATED_ENERGY_TOTAL], uiValue=kwhStr)

                    if "dailyTotalCostSaving" in dev.states:
                        costStr = f"{self.globals[SMAPPEES][dev.id][DAILY_TOTAL_COST_SAVING]:3.0f}"
                        dev.updateStateOnServer("dailyTotalCostSaving", self.globals[SMAPPEES][dev.id][DAILY_TOTAL_COST_SAVING], uiValue=costStr)

                    dev.updateStateOnServer("smappeeElectricitySavedOnline", False, uiValue='offline')

                    # if self.globals[PLUGIN_INITIALIZED] == True and self.serviceLocationId != "":
                    #     self.globals[QUEUES][SEND_TO_SMAPPEE].put([COMMAND_GET_CONSUMPTION,str(self.serviceLocationId)])

                    self.logger.info(f"Started '{dev.name}' at address [{dev.address}]")

                # Initialise internal to plugin smappee solar states to default values
                elif dev.deviceTypeId == "smappeeSolar":

                    self.logger.debug(f"SMAPPEE DEV [SOLAR] START smappeeServiceLocationIdToDevId = [{self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID]}]")

                    self.globals[CONFIG][SUPPORTS_SOLAR] = True

                    self.serviceLocationId = str(dev.pluginProps["serviceLocationId"])

                    self.logger.debug(f"SMAPPEE DEV [SOLAR] START self.serviceLocationId = [{self.serviceLocationId}]")

                    self.setSmappeeServiceLocationIdToDevId(FUNCTION_ADD_UPDATE, 'smappeeSolar', self.serviceLocationId, dev.id, '0', '0')

                    self.logger.debug(f"SMAPPEE DEV [SOLAR] START smappeeServiceLocationIdToDevId [2] = [{self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID]}]")

                    self.globals[SMAPPEES][dev.id] = dict()
                    self.globals[SMAPPEES][dev.id][SERVICE_LOCATION_ID] = dev.pluginProps["serviceLocationId"]
                    self.globals[SMAPPEES][dev.id][SERVICE_LOCATION_NAME] = dev.pluginProps["serviceLocationName"]
                    self.globals[SMAPPEES][dev.id][NAME] = dev.name
                    self.globals[SMAPPEES][dev.id][ELECTRICITY_COST] = 0
                    self.globals[SMAPPEES][dev.id][ELECTRICITY_CURRENCY] = 0
                    self.globals[SMAPPEES][dev.id][CURRENT_ENERGY_LEVEL] = 0.0
                    self.globals[SMAPPEES][dev.id][ACCUMULATED_ENERGY_TOTAL] = 0.0
                    self.globals[SMAPPEES][dev.id][LAST_RESET_SOLAR_UTC] = 0
                    self.globals[SMAPPEES][dev.id][LAST_READING_SOLAR_UTC] = 0
                    self.globals[SMAPPEES][dev.id][LAST_READING_SOLAR] = 0.0
                    try:
                        self.globals[SMAPPEES][dev.id][HIDE_SOLAR_METER_CURRENT_GENERATION] = dev.pluginProps["hideSolarMeterCurGeneration"]
                    except Exception as exception_error:
                        self.globals[SMAPPEES][dev.id][HIDE_SOLAR_METER_CURRENT_GENERATION] = False
                    try:
                        self.globals[SMAPPEES][dev.id][HIDE_ZERO_SOLAR_METER_CURRENT_GENERATION] = dev.pluginProps["hideZeroSolarMeterCurGeneration"]
                    except Exception as exception_error:
                        self.globals[SMAPPEES][dev.id][HIDE_ZERO_SOLAR_METER_CURRENT_GENERATION] = False
                    try:
                        self.globals[SMAPPEES][dev.id][HIDE_SOLAR_METER_ACCUMULATED_GENERATION] = dev.pluginProps["hideSolarMeterAccumGeneration"]
                    except Exception as exception_error:
                        self.globals[SMAPPEES][dev.id][HIDE_SOLAR_METER_ACCUMULATED_GENERATION] = False
                    try:
                        self.globals[SMAPPEES][dev.id][HIDE_SOLAR_METER_ACCUMULATED_GENERATION_COST] = dev.pluginProps["hideSolarMeterAccumGenerationCost"]
                    except Exception as exception_error:
                        self.globals[SMAPPEES][dev.id][HIDE_SOLAR_METER_ACCUMULATED_GENERATION_COST] = False
                    try:
                        self.globals[SMAPPEES][dev.id][HIDE_NO_CHANGE_IN_SOLAR_METER_ACCUMULATED_GENERATION] = dev.pluginProps["hideNoChangeInSolarMeterAccumGeneration"]
                    except Exception as exception_error:
                        self.globals[SMAPPEES][dev.id][HIDE_NO_CHANGE_IN_SOLAR_METER_ACCUMULATED_GENERATION] = False
                    try:
                        self.globals[SMAPPEES][dev.id][CURRENCY_CODE] = dev.pluginProps["currencyCode"]
                    except Exception as exception_error:
                        self.globals[SMAPPEES][dev.id][CURRENCY_CODE] = 'UKP'
                    try:
                        self.globals[SMAPPEES][dev.id][GENERATION_RATE] = float(dev.pluginProps["generationRate"])
                    except Exception as exception_error:
                        self.globals[SMAPPEES][dev.id][GENERATION_RATE] = 8.88  # To make it obvious there is an error

                    try:
                        self.globals[SMAPPEES][dev.id][EXPORT_TYPE] = dev.pluginProps["exportType"]
                    except Exception as exception_error:
                        self.globals[SMAPPEES][dev.id][EXPORT_TYPE] = 'percentage'

                    try:
                        self.globals[SMAPPEES][dev.id][EXPORT_PERCENTAGE] = float(dev.pluginProps["exportPercentage"])
                    except Exception as exception_error:
                        self.globals[SMAPPEES][dev.id][EXPORT_PERCENTAGE] = 50.0  # To make it obvious there is an error

                    try:
                        self.globals[SMAPPEES][dev.id][EXPORT_RATE] = float(dev.pluginProps["exportRate"])
                    except Exception as exception_error:
                        self.globals[SMAPPEES][dev.id][EXPORT_RATE] = 9.99  # To make it obvious there is an error
                    if "curEnergyLevel" in dev.states:
                        wattStr = f"{self.globals[SMAPPEES][dev.id][CURRENT_ENERGY_LEVEL]:3.0f} Watts"
                        dev.updateStateOnServer("curEnergyLevel", self.globals[SMAPPEES][dev.id][CURRENT_ENERGY_LEVEL], uiValue=wattStr)

                    if "accumEnergyTotal" in dev.states:
                        kwhStr = f"{self.globals[SMAPPEES][dev.id][ACCUMULATED_ENERGY_TOTAL]:3.0f} kWh"
                        dev.updateStateOnServer("accumEnergyTotal", self.globals[SMAPPEES][dev.id][ACCUMULATED_ENERGY_TOTAL], uiValue=kwhStr)

                    dev.updateStateOnServer("smappeeSolarOnline", False, uiValue='offline')

                    if self.globals[PLUGIN_INITIALIZED] and self.serviceLocationId != "":
                        self.globals[QUEUES][SEND_TO_SMAPPEE].put([COMMAND_GET_CONSUMPTION, str(self.serviceLocationId)])

                    self.logger.info(f"Started '{dev.name}' at address [{dev.address}]")

                # Initialise internal to plugin smappee solar used states to default values
                elif dev.deviceTypeId == "smappeeSolarUsed":

                    self.logger.debug(f"SMAPPEE DEV [SOLAR USED] START smappeeServiceLocationIdToDevId = [{self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID]}]")

                    self.globals[CONFIG][SUPPORTS_SOLAR_USED] = True

                    self.serviceLocationId = dev.pluginProps["serviceLocationId"]

                    self.logger.debug(f"SMAPPEE DEV [SOLAR USED] START self.serviceLocationId = [{self.serviceLocationId}]")

                    self.setSmappeeServiceLocationIdToDevId(FUNCTION_ADD_UPDATE, 'smappeeSolarUsed', self.serviceLocationId, dev.id, '0', '0')

                    self.logger.debug(f"SMAPPEE DEV [SOLAR USED] START smappeeServiceLocationIdToDevId [2] = [{self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID]}]")

                    self.globals[SMAPPEES][dev.id] = dict()
                    self.globals[SMAPPEES][dev.id][SERVICE_LOCATION_ID] = dev.pluginProps["serviceLocationId"]
                    self.globals[SMAPPEES][dev.id][SERVICE_LOCATION_NAME] = dev.pluginProps["serviceLocationName"]
                    self.globals[SMAPPEES][dev.id][NAME] = dev.name
                    self.globals[SMAPPEES][dev.id][ELECTRICITY_COST] = 0
                    self.globals[SMAPPEES][dev.id][ELECTRICITY_CURRENCY] = 0
                    self.globals[SMAPPEES][dev.id][CURRENT_ENERGY_LEVEL] = 0.0
                    self.globals[SMAPPEES][dev.id][ACCUMULATED_ENERGY_TOTAL] = 0.0
                    self.globals[SMAPPEES][dev.id][LAST_RESET_SOLAR_USED_UTC] = 0
                    self.globals[SMAPPEES][dev.id][LAST_READING_SOLAR_USED_UTC] = 0
                    self.globals[SMAPPEES][dev.id][LAST_READING_SOLAR_USED] = 0.0
                    self.globals[SMAPPEES][dev.id][HIDE_SOLAR_USED_METER_CURRENT_GENERATION] = dev.pluginProps["hideSolarUsedMeterCurGeneration"]  # TODO : CHECK UPPER CASE CPNSTANTS are correct
                    self.globals[SMAPPEES][dev.id][HIDE_ZERO_SOLAR_METER_CURRENT_GENERATION] = dev.pluginProps["hideZeroSolarUsedMeterCurGeneration"]
                    self.globals[SMAPPEES][dev.id][HIDE_SOLAR_USED_METER_ACCUMULATED_GENERATION] = dev.pluginProps["hideSolarUsedMeterAccumGeneration"]
                    self.globals[SMAPPEES][dev.id][HIDE_NO_CHANGE_IN_SOLAR_USED_METER_ACCUMULATED_GENERATION] = dev.pluginProps["hideNoChangeInSolarUsedMeterAccumGeneration"]

                    if "curEnergyLevel" in dev.states:
                        wattStr = f"{self.globals[SMAPPEES][dev.id][CURRENT_ENERGY_LEVEL]:3.0f} Watts"
                        dev.updateStateOnServer("curEnergyLevel", self.globals[SMAPPEES][dev.id][CURRENT_ENERGY_LEVEL], uiValue=wattStr)

                    if "accumEnergyTotal" in dev.states:
                        kwhStr = f"{self.globals[SMAPPEES][dev.id][ACCUMULATED_ENERGY_TOTAL]:3.0f} kWh"
                        dev.updateStateOnServer("accumEnergyTotal", self.globals[SMAPPEES][dev.id][ACCUMULATED_ENERGY_TOTAL], uiValue=kwhStr)

                    dev.updateStateOnServer("smappeeSolarUsedOnline", False, uiValue='offline')

                    # if self.globals[PLUGIN_INITIALIZED] == True and self.serviceLocationId != "":
                    #     self.globals[QUEUES][SEND_TO_SMAPPEE].put([COMMAND_GET_CONSUMPTION,str(self.serviceLocationId)])

                    self.logger.info(f"Started '{dev.name}' at address [{dev.address}]")

                # Initialise internal to plugin smappee solar exported states to default values
                elif dev.deviceTypeId == "smappeeSolarExported":
                    self.logger.debug(f"SMAPPEE DEV [SOLAR EXPORTED] START smappeeServiceLocationIdToDevId = [{self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID]}]")

                    self.globals[CONFIG][SUPPORTS_SOLAR_EXPORTED] = True

                    self.serviceLocationId = str(dev.pluginProps["serviceLocationId"])

                    self.logger.debug(f"SMAPPEE DEV [SOLAR EXPORTED] START self.serviceLocationId = [{self.serviceLocationId}]")

                    self.setSmappeeServiceLocationIdToDevId(FUNCTION_ADD_UPDATE, 'smappeeSolarExported', self.serviceLocationId, dev.id, '0', '0')

                    self.logger.debug(f"SMAPPEE DEV [SOLAR EXPORTED] START smappeeServiceLocationIdToDevId [2] = [{self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID]}]")

                    self.globals[SMAPPEES][dev.id] = dict()
                    self.globals[SMAPPEES][dev.id][SERVICE_LOCATION_ID] = dev.pluginProps["serviceLocationId"]
                    self.globals[SMAPPEES][dev.id][SERVICE_LOCATION_NAME] = dev.pluginProps["serviceLocationName"]
                    self.globals[SMAPPEES][dev.id][NAME] = dev.name
                    self.globals[SMAPPEES][dev.id][ELECTRICITY_COST] = 0
                    self.globals[SMAPPEES][dev.id][ELECTRICITY_CURRENCY] = 0
                    self.globals[SMAPPEES][dev.id][CURRENT_ENERGY_LEVEL] = 0.0
                    self.globals[SMAPPEES][dev.id][ACCUMULATED_ENERGY_TOTAL] = 0.0
                    self.globals[SMAPPEES][dev.id][LAST_RESET_SOLAR_EXPORTED_UTC] = 0
                    self.globals[SMAPPEES][dev.id][LAST_READING_SOLAR_EXPORTED_UTC] = 0
                    self.globals[SMAPPEES][dev.id][LAST_READING_SOLAR_EXPORTED] = 0.0
                    self.globals[SMAPPEES][dev.id][HIDE_SOLAR_EXPORTED_METER_CURRENT_GENERATION] = dev.pluginProps["hideSolarExportedMeterCurGeneration"]
                    self.globals[SMAPPEES][dev.id][HIDE_ZERO_SOLAR_METER_CURRENT_GENERATION] = dev.pluginProps["hideZeroSolarExportedMeterCurGeneration"]
                    self.globals[SMAPPEES][dev.id][HIDE_SOLAR_EXPORTED_METER_ACCUMULATED_GENERATION] = dev.pluginProps["hideSolarExportedMeterAccumGeneration"]
                    self.globals[SMAPPEES][dev.id][HIDE_NO_CHANGE_IN_SOLAR_EXPORTED_METER_ACCUMULATED_GENERATION] = dev.pluginProps["hideNoChangeInSolarExportedMeterAccumGeneration"]

                    if "curEnergyLevel" in dev.states:
                        wattStr = f"{self.globals[SMAPPEES][dev.id][CURRENT_ENERGY_LEVEL]:3.0f} Watts"
                        dev.updateStateOnServer("curEnergyLevel", self.globals[SMAPPEES][dev.id][CURRENT_ENERGY_LEVEL], uiValue=wattStr)

                    if "accumEnergyTotal" in dev.states:
                        kwhStr = f"{self.globals[SMAPPEES][dev.id][ACCUMULATED_ENERGY_TOTAL]:3.0f} kWh"
                        dev.updateStateOnServer("accumEnergyTotal", self.globals[SMAPPEES][dev.id][ACCUMULATED_ENERGY_TOTAL], uiValue=kwhStr)

                    dev.updateStateOnServer("smappeeSolarExportedOnline", False, uiValue='offline')

                    # if self.globals[PLUGIN_INITIALIZED] == True and self.serviceLocationId != "":
                    #     self.globals[QUEUES][SEND_TO_SMAPPEE]COMMAND_CONSUMPTION,str(self.serviceLocationId)])

                    self.logger.info(f"Started '{dev.name}' at address [{dev.address}]")

                # Initialise internal to plugin smappee sensor states to default values
                elif dev.deviceTypeId == "smappeeSensor":

                    self.logger.debug(f"SMAPPEE DEV [SENSOR] START-A smappeeServiceLocationIdToDevId = [{self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID]}]")

                    self.serviceLocationId = str(dev.pluginProps["serviceLocationId"])

                    self.logger.debug(f"SMAPPEE DEV [SENSOR] START-B self.serviceLocationId = [{self.serviceLocationId}]")

                    self.setSmappeeServiceLocationIdToDevId(FUNCTION_ADD_UPDATE, 'smappeeSensor', self.serviceLocationId, dev.id, dev.address, dev.name)

                    self.logger.debug(f"SMAPPEE DEV [SENSOR] START-C smappeeServiceLocationIdToDevId [2] = [{self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID]}]")

                    self.globals[SMAPPEES][dev.id] = dict()
                    self.globals[SMAPPEES][dev.id][SERVICE_LOCATION_ID] = dev.pluginProps["serviceLocationId"]
                    self.globals[SMAPPEES][dev.id][SERVICE_LOCATION_NAME] = dev.pluginProps["serviceLocationName"]
                    self.globals[SMAPPEES][dev.id][NAME] = dev.name
                    self.globals[SMAPPEES][dev.id][LONGDITUDE] = 0
                    self.globals[SMAPPEES][dev.id][LATITUDE] = 0
                    self.globals[SMAPPEES][dev.id][SMAPPEE_UNIT_COST] = 0
                    self.globals[SMAPPEES][dev.id][SMAPPEE_UNIT_CURRENCY] = 0
                    self.globals[SMAPPEES][dev.id][CURRENT_ENERGY_LEVEL] = 0.0
                    self.globals[SMAPPEES][dev.id][ACCUMULATED_ENERGY_TOTAL] = 0.0
                    self.globals[SMAPPEES][dev.id][DAILY_TOTAL_COST] = 0.0
                    self.globals[SMAPPEES][dev.id][LAST_RESET_SENSOR_UTC] = 0
                    self.globals[SMAPPEES][dev.id][LAST_READING_SENSOR_UTC] = 0
                    self.globals[SMAPPEES][dev.id][LAST_READING_SENSOR] = 0.0
                    self.globals[SMAPPEES][dev.id][READINGS_LAST_UPDATED] = 'Unknown'
                    self.globals[SMAPPEES][dev.id][HIDE_ENERGY_METER_CURRENT_POWER] = dev.pluginProps["hideEnergyMeterCurPower"]
                    self.globals[SMAPPEES][dev.id][HIDE_ENERGY_METER_ACCUMULATED_POWER] = dev.pluginProps["hideEnergyMeterAccumPower"]
                    self.globals[SMAPPEES][dev.id][TEST_TEMPERATURE] = 0.0
                    self.globals[SMAPPEES][dev.id][TEST_HUMIDITY] = 0.0
                    self.globals[SMAPPEES][dev.id][TEST_BATTERY_LEVEL] = 0.0
                    self.globals[SMAPPEES][dev.id][TEMPERATURE_LAST_UPDATED] = 'Unknown'
                    self.globals[SMAPPEES][dev.id][HUMIDITY_LAST_UPDATED] = 'Unknown'
                    self.globals[SMAPPEES][dev.id][BATTERY_LEVEL_LAST_UPDATED] = 'Unknown'

                    try:
                        self.globals[SMAPPEES][dev.id][CURRENCY_CODE] = dev.pluginProps["currencyCode"]
                    except Exception as exception_error:
                        self.globals[SMAPPEES][dev.id][CURRENCY_CODE] = 'UKP'
                    try:
                        self.globals[SMAPPEES][dev.id][DAILY_STANDING_CHARGE] = float(dev.pluginProps["dailyStandingCharge"])
                    except Exception as exception_error:
                        self.globals[SMAPPEES][dev.id][DAILY_STANDING_CHARGE] = 8.88  # To make it obvious there is an error
                    try:
                        self.globals[SMAPPEES][dev.id][UNITS] = str(dev.pluginProps["units"])
                    except Exception as exception_error:
                        self.globals[SMAPPEES][dev.id][UNITS] = 'kWh'
                    try:
                        self.globals[SMAPPEES][dev.id][PULSES_PER_UNIT] = str(dev.pluginProps["pulsesPerUnit"])
                    except Exception as exception_error:
                        self.globals[SMAPPEES][dev.id][PULSES_PER_UNIT] = int(1.0)
                    try:
                        self.globals[SMAPPEES][dev.id][UNIT_COST] = float(dev.pluginProps["unitCost"])
                    except Exception as exception_error:
                        self.globals[SMAPPEES][dev.id][UNIT_COST] = 9.99  # To make it obvious there is an error

                    if "readingsLastUpdated" in dev.states:
                        dev.updateStateOnServer("readingsLastUpdated", self.globals[SMAPPEES][dev.id][READINGS_LAST_UPDATED])

                    if "temperature" in dev.states:
                        temperatureStr = f"{self.globals[SMAPPEES][dev.id][TEST_TEMPERATURE]:0.1f} deg C"
                        temperatureReformatted = float(f"{self.globals[SMAPPEES][dev.id][TEST_TEMPERATURE]:0.1f}")
                        dev.updateStateOnServer("temperature", temperatureReformatted, uiValue=temperatureStr)

                    if "humidity" in dev.states:
                        humidityStr = f"{self.globals[SMAPPEES][dev.id][TEST_HUMIDITY]:0.1f}%"
                        humidityReformatted = float(f"{self.globals[SMAPPEES][dev.id][TEST_HUMIDITY]:0.1f}")
                        dev.updateStateOnServer("humidity", humidityReformatted, uiValue=humidityStr)

                    if "batteryLevel" in dev.states:
                        batteryLevelStr = f"{self.globals[SMAPPEES][dev.id][TEST_BATTERY_LEVEL]:0.1f}%"
                        batteryLevelReformatted = float(f"{self.globals[SMAPPEES][dev.id][TEST_BATTERY_LEVEL]:0.1f}")
                        dev.updateStateOnServer("batteryLevel", batteryLevelReformatted, uiValue=batteryLevelStr)

                    if "temperatureLastUpdated" in dev.states:
                        dev.updateStateOnServer("temperatureLastUpdated", self.globals[SMAPPEES][dev.id][TEMPERATURE_LAST_UPDATED])

                    if "humidityLastUpdated" in dev.states:
                        dev.updateStateOnServer("humidityLastUpdated", self.globals[SMAPPEES][dev.id][HUMIDITY_LAST_UPDATED])

                    if "batteryLevelLastUpdated" in dev.states:
                        dev.updateStateOnServer("batteryLevelLastUpdated", self.globals[SMAPPEES][dev.id][BATTERY_LEVEL_LAST_UPDATED])

                    unitsKey = self.globals[SMAPPEES][dev.id][UNITS]
                    if unitsKey in self.globals[UNIT_TABLE]:
                        pass
                    else:
                        unitsKey = DEFAULT

                    unitsCurrentUnits = self.globals[UNIT_TABLE][unitsKey][CURRENT_UNITS]
                    unitsAccumUnits = self.globals[UNIT_TABLE][unitsKey][ACCUM_UNITS]
                    unitsmeasurementTimeMultiplier = self.globals[UNIT_TABLE][unitsKey][MEASUREMENT_TIME_MULTIPLIER]
                    unitsformatTotaldivisor = self.globals[UNIT_TABLE][unitsKey][FORMAT_TOTAL_DIVISOR]
                    unitsformatCurrent = self.globals[UNIT_TABLE][unitsKey][FORMAT_CURRENT]
                    unitsformatCurrentUi = unitsformatCurrent + " " + unitsCurrentUnits
                    unitsformatTotal = self.globals[UNIT_TABLE][unitsKey][FORMAT_TOTAL]
                    unitsformatTotalUi = unitsformatTotal + ' ' + unitsAccumUnits

                    if "curEnergyLevel" in dev.states:
                        dataToUpdateStr = str(unitsformatCurrentUi % (self.globals[SMAPPEES][dev.id][CURRENT_ENERGY_LEVEL]))
                        dev.updateStateOnServer("curEnergyLevel", self.globals[SMAPPEES][dev.id][CURRENT_ENERGY_LEVEL], uiValue=dataToUpdateStr)

                    if "accumEnergyTotal" in dev.states:
                        dataToUpdateStr = str(unitsformatTotalUi % (self.globals[SMAPPEES][dev.id][ACCUMULATED_ENERGY_TOTAL]))
                        dev.updateStateOnServer("accumEnergyTotal", self.globals[SMAPPEES][dev.id][ACCUMULATED_ENERGY_TOTAL], uiValue=dataToUpdateStr)

                    try:
                        self.globals[SMAPPEES][dev.id][HIDE_ENERGY_METER_ACCUMULATED_POWER_COST] = dev.pluginProps["hideEnergyMeterAccumPowerCost"]
                    except Exception as exception_error:
                        self.globals[SMAPPEES][dev.id][HIDE_ENERGY_METER_ACCUMULATED_POWER_COST] = False

                    dev.updateStateOnServer("smappeeSensorOnline", False, uiValue='offline')

                    if "dailyTotalCost" in dev.states:
                        costStr = f"{self.globals[SMAPPEES][dev.id][DAILY_TOTAL_COST]:3.0f}"
                        dev.updateStateOnServer("dailyTotalCost", self.globals[SMAPPEES][dev.id][DAILY_TOTAL_COST], uiValue=costStr)

                    if self.globals[PLUGIN_INITIALIZED] and self.serviceLocationId != "":
                        self.globals[QUEUES][SEND_TO_SMAPPEE].put([COMMAND_GET_SENSOR_CONSUMPTION, str(self.serviceLocationId)])

                    self.logger.info(f"Started '{dev.name}' at address [{dev.address}]")

                elif dev.deviceTypeId == "smappeeAppliance":
                    self.serviceLocationId = str(dev.pluginProps["serviceLocationId"])

                    self.setSmappeeServiceLocationIdToDevId(FUNCTION_ADD_UPDATE, 'smappeeAppliance', self.serviceLocationId, dev.id, dev.address, dev.name)

                    self.globals[SMAPPEE_APPLIANCES][dev.id] = dict()
                    self.globals[SMAPPEE_APPLIANCES][dev.id][SERVICE_LOCATION_ID] = dev.pluginProps["serviceLocationId"]
                    self.globals[SMAPPEE_APPLIANCES][dev.id][DATETIME_STARTED] = indigo.server.getTime()
                    self.globals[SMAPPEE_APPLIANCES][dev.id][ADDRESS] = dev.address
                    self.globals[SMAPPEE_APPLIANCES][dev.id][ON_OFF_STATE] = 'off'
                    self.globals[SMAPPEE_APPLIANCES][dev.id][ON_OFF_STATE_BOOL] = False
                    self.globals[SMAPPEE_APPLIANCES][dev.id][NAME] = dev.name
                    self.globals[SMAPPEE_APPLIANCES][dev.id][CURRENT_ENERGY_LEVEL] = 0.0
                    self.globals[SMAPPEE_APPLIANCES][dev.id][ACCUMULATED_ENERGY_TOTAL] = 0.0
                    self.globals[SMAPPEE_APPLIANCES][dev.id][LAST_RESET_APPLIANCE_UTC] = 0
                    self.globals[SMAPPEE_APPLIANCES][dev.id][LAST_READING_APPLIANCE_UTC] = 0
                    self.globals[SMAPPEE_APPLIANCES][dev.id][LAST_READING_APPLIANCE] = 0.0

                    if "curEnergyLevel" in dev.states:
                        wattStr = f"{self.globals[SMAPPEE_APPLIANCES][dev.id][CURRENT_ENERGY_LEVEL]:3.0f} Watts"
                        dev.updateStateOnServer("curEnergyLevel", self.globals[SMAPPEE_APPLIANCES][dev.id][CURRENT_ENERGY_LEVEL], uiValue=wattStr)

                    if "accumEnergyTotal" in dev.states:
                        kwhStr = f"{self.globals[SMAPPEE_APPLIANCES][dev.id][ACCUMULATED_ENERGY_TOTAL]:3.0f} kWh"
                        dev.updateStateOnServer("accumEnergyTotal", self.globals[SMAPPEE_APPLIANCES][dev.id][ACCUMULATED_ENERGY_TOTAL], uiValue=kwhStr)

                    dev.updateStateOnServer("smappeeApplianceEventStatus", "NONE", uiValue="No Events")
                    dev.updateStateImageOnServer(indigo.kStateImageSel.EnergyMeterOff)

                    self.logger.info(f"Started '{dev.name}' at address [{self.globals[SMAPPEE_APPLIANCES][dev.id][ADDRESS]}]")

                elif dev.deviceTypeId == "smappeeActuator":
                    self.serviceLocationId = str(dev.pluginProps["serviceLocationId"])

                    self.setSmappeeServiceLocationIdToDevId(FUNCTION_ADD_UPDATE, 'smappeeActuator', self.serviceLocationId, dev.id, dev.address, dev.name)

                    self.globals[SMAPPEE_PLUGS][dev.id] = dict()
                    self.globals[SMAPPEE_PLUGS][dev.id][DATETIME_STARTED] = indigo.server.getTime()
                    self.globals[SMAPPEE_PLUGS][dev.id][ADDRESS] = dev.address
                    self.globals[SMAPPEE_PLUGS][dev.id][ON_OFF_STATE] = 'off'
                    self.globals[SMAPPEE_PLUGS][dev.id][ON_OFF_STATE_BOOL] = False
                    self.globals[SMAPPEE_PLUGS][dev.id][NAME] = dev.name

                    dev.updateStateOnServer("onOffState", False, uiValue='off')

                    self.logger.info(f"Started '{dev.name}' at address [{self.globals[SMAPPEE_PLUGS][dev.id][ADDRESS]}]")

                self.logger.debug(f"SMAPPEE DEV [{dev.name}] [{dev.model}] START smappeeServiceLocationIdToDevId = [{self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID]}]")

            except Exception as exception_error:
                self.exception_handler(exception_error, True)  # Log error and display failing statement

        except Exception as exception_error:
            self.exception_handler(exception_error, True)  # Log error and display failing statement

    def deviceStopComm(self, dev):
        try:
            self.globals[SMAPPEES][dev.id] = dict()

            if dev.deviceTypeId == "smappeeElectricity":
                dev.updateStateOnServer("smappeeElectricityOnline", False, uiValue='Stopped')
                self.globals[CONFIG][SUPPORTS_ELECTRICITY] = False

            elif dev.deviceTypeId == "smappeeElectricityNet":
                dev.updateStateOnServer("smappeeElectricityNetOnline", False, uiValue='Stopped')
                self.globals[CONFIG][SUPPORTS_ELECTRICITY_NET] = False

            elif dev.deviceTypeId == "smappeeElectricitySaved":
                dev.updateStateOnServer("smappeeElectricitySavedOnline", False, uiValue='Stopped')
                self.globals[CONFIG][SUPPORTS_ELECTRICITY_SAVED] = False

            elif dev.deviceTypeId == "smappeeSolar":
                dev.updateStateOnServer("smappeeSolarOnline", False, uiValue='Stopped')
                self.globals[CONFIG][SUPPORTS_SOLAR] = False

            elif dev.deviceTypeId == "smappeeSolarUsed":
                dev.updateStateOnServer("smappeeSolarUsedOnline", False, uiValue='Stopped')
                self.globals[CONFIG][SUPPORTS_SOLAR_USED] = False

            elif dev.deviceTypeId == "smappeeSolarExported":
                dev.updateStateOnServer("smappeeSolarExportedOnline", False, uiValue='Stopped')
                self.globals[CONFIG][SUPPORTS_SOLAR_EXPORTED] = False

            elif dev.deviceTypeId == "smappeeSensor":
                dev.updateStateOnServer("smappeeSensorOnline", False, uiValue='Stopped')

            elif dev.deviceTypeId == "smappeeAppliance":
                dev.updateStateOnServer("smappeeApplianceEventStatus", 'Stopped')

            elif dev.deviceTypeId == "smappeeActuator":
                dev.updateStateOnServer("onOffState", False, uiValue='stopped')

            serviceLocationId = dev.pluginProps["serviceLocationId"]
            self.setSmappeeServiceLocationIdToDevId(FUNCTION_STOP, dev.deviceTypeId, serviceLocationId, dev.id, dev.address,
                                                    dev.name)

            self.logger.info(f"Stopping '{dev.name}'")

        except Exception as exception_error:
            self.exception_handler(exception_error, True)  # Log error and display failing statement
