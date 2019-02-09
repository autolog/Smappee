#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# Smappee Controller © Autolog 2018
# 

try:
    import indigo
except ImportError, e:
    pass

import collections  # Used for creating sensor testdata
import datetime
import simplejson as json
import logging
import Queue
# import sqlite3 as sql3
import sys
import threading
import time

from polling import ThreadPolling
from smappeeInterface import ThreadSmappeeInterface


# noinspection PyPep8Naming,PyUnresolvedReferences
class Plugin(indigo.PluginBase):

    def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):

        indigo.PluginBase.__init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs)

        # Initialise dictionary to store plugin Globals
        self.globals = dict()

        # Initialise Indigo plugin info
        self.globals['plugin'] = dict()  # Info about the plugin filled in by Plugin Start
        self.globals['plugin']['pluginId'] = pluginId
        self.globals['plugin']['pluginDisplayName'] = pluginDisplayName
        self.globals['plugin']['pluginVersion'] = pluginVersion

        # Initialise dictionary for debug in plugin Globals
        self.globals['debug'] = dict()
        self.globals['debug']['debugEnabled'] = False  # if False it indicates no debugging is active else it indicates that at least one type of debug is active
        self.globals['debug']['active'] = False  # if False it indicates no debugging is active else it indicates that at least one type of debug is active

        self.globals['debug']['general'] = False  # For general debugging
        self.globals['debug']['deviceFactory'] = False  # For device factory debugging
        self.globals['debug']['smappeeInterface'] = False  # For Smappee interface debugging
        self.globals['debug']['polling'] = False  # For polling debugging
        self.globals['debug']['methodTrace'] = False  # For displaying method invocations i.e. trace method

        self.globals['debug']['previous'] = dict()
        self.globals['debug']['previous']['general'] = False  # For general debugging
        self.globals['debug']['previous']['deviceFactory'] = False  # For device factory debugging
        self.globals['debug']['previous']['smappeeInterface'] = False  # For logging commands sent to and received from the Smappee interface
        self.globals['debug']['previous']['polling'] = False  # For polling debugging
        self.globals['debug']['previous']['methodTrace'] = False  # For displaying method invocations i.e. trace method

        # Setup Logging
        logformat = logging.Formatter('%(asctime)s.%(msecs)03d\t%(levelname)-12s\t%(name)s.%(funcName)-25s %(msg)s',
                                      datefmt='%Y-%m-%d %H:%M:%S')
        self.plugin_file_handler.setFormatter(logformat)
        self.plugin_file_handler.setLevel(logging.INFO)  # Master Logging Level for Plugin Log file
        self.indigo_log_handler.setLevel(logging.INFO)  # Logging level for Indigo Event Log
        self.generalLogger = logging.getLogger("Plugin.general")
        self.generalLogger.setLevel(self.globals['debug']['general'])
        self.deviceFactoryLogger = logging.getLogger("Plugin.deviceFactory")
        self.deviceFactoryLogger.setLevel(self.globals['debug']['deviceFactory'])
        self.methodTracer = logging.getLogger("Plugin.method")
        self.methodTracer.setLevel(self.globals['debug']['methodTrace'])

        # Now logging is set-up, output Initialising Message
        self.generalLogger.info(u"'Smappee V3' plugin initializing . . .")

        # Initialise id of folder to hold devices
        self.globals['devicesFolderId'] = 0

        # Initialise dictionary to store message queues
        self.globals['queues'] = dict()
        self.globals['queues']['initialised'] = False

        self.globals['SQL'] = dict()
        self.globals['SQL']['enabled'] = False
        # self.globals['SQL']['db'] = '/Users/admin/Documents/Autolog/sqlite/smappee.db'
        # self.globals['SQL']['dbType'] = 'sqlite3'
        # self.globals['SQL']['connection'] = ''
        # self.globals['SQL']['cursor'] = ''

        self.globals['TESTING'] = False  # Set to True to action next section of code
        if self.globals['TESTING']:
            self.globals['testdata'] = dict()
            self.globals['testdata']['temperature'] = collections.deque(
                ['255', '252', '250', '249', '247', '246', '220', '223', '221', '198', '195', '192'])
            self.globals['testdata']['humidity'] = collections.deque(
                ['90', '85', '80', '75', '70', '65', '60', '55', '50', '45', '40', '35'])
            self.globals['testdata']['batteryLevel'] = collections.deque(
                ['100', '99', '98', '97', '95', '94', '93', '92', '91', '90', '89', '88'])
            self.globals['testdata']['value1'] = collections.deque(
                ['0', '800', '400', '0', '800', '800', '1200', '100', '0', '0', '1000', '700'])
            self.globals['testdata']['value2'] = collections.deque(
                ['50', '50', '0', '0', '0', '0', '400', '0', '0', '0', '50', '70'])

        self.globals['unitTable'] = dict()

        self.globals['unitTable']['default'] = dict()
        self.globals['unitTable']['default']['measurementTimeMultiplier'] = 12.0  # 'hourly' = 12, '5 minutes' = 1'
        self.globals['unitTable']['default']['formatTotaldivisor'] = 1000.0
        self.globals['unitTable']['default']['formatCurrent'] = "%d"
        self.globals['unitTable']['default']['formatTotal'] = "%3.0f"
        self.globals['unitTable']['default']['currentUnits'] = 'watts [E]'
        self.globals['unitTable']['default']['currentUnitsRate'] = 'watt [E] hours'
        self.globals['unitTable']['default']['accumUnits'] = 'kWh [E]'

        self.globals['unitTable']['kWh'] = dict()
        self.globals['unitTable']['kWh']['measurementTimeMultiplier'] = 12.0  # 'hourly' = 12, '5 minutes' = 1'
        self.globals['unitTable']['kWh']['formatTotaldivisor'] = 1000.0
        self.globals['unitTable']['kWh']['formatCurrentDivisor'] = 1000.0
        self.globals['unitTable']['kWh']['formatCurrent'] = "%d"
        self.globals['unitTable']['kWh']['formatTotal'] = "%3.0f"
        self.globals['unitTable']['kWh']['currentUnits'] = 'watts'
        self.globals['unitTable']['kWh']['currentUnitsRate'] = 'watt hours'
        self.globals['unitTable']['kWh']['accumUnits'] = 'kWh'

        self.globals['unitTable']['litres'] = dict()
        self.globals['unitTable']['litres']['measurementTimeMultiplier'] = 1.0  # 'hourly' = 12, '5 minutes' = 1'
        self.globals['unitTable']['litres']['formatTotaldivisor'] = 1.0
        self.globals['unitTable']['litres']['formatCurrent'] = "%d"
        self.globals['unitTable']['litres']['formatTotal'] = "%d"
        self.globals['unitTable']['litres']['currentUnits'] = 'litres'
        self.globals['unitTable']['litres']['accumUnits'] = 'litres'

        self.globals['unitTable']['m3'] = dict()
        self.globals['unitTable']['m3']['measurementTimeMultiplier'] = 1.0  # 'hourly' = 12, '5 minutes' = 1'
        self.globals['unitTable']['m3']['formatTotaldivisor'] = 1.0
        self.globals['unitTable']['m3']['formatCurrent'] = "%d"
        self.globals['unitTable']['m3']['formatTotal'] = "%d"
        self.globals['unitTable']['m3']['currentUnits'] = 'cubic metres'
        self.globals['unitTable']['m3']['accumUnits'] = 'cubic metres'

        self.globals['unitTable']['ft3'] = dict()
        self.globals['unitTable']['ft3']['measurementTimeMultiplier'] = 1.0  # 'hourly' = 12, '5 minutes' = 1'
        self.globals['unitTable']['ft3']['formatTotaldivisor'] = 1.0
        self.globals['unitTable']['ft3']['formatCurrent'] = "%d"
        self.globals['unitTable']['ft3']['formatTotal'] = "%d"
        self.globals['unitTable']['ft3']['currentUnits'] = 'cubic feet'
        self.globals['unitTable']['ft3']['accumUnits'] = 'cubic feet'

        self.globals['unitTable']['gallons'] = dict()
        self.globals['unitTable']['gallons']['measurementTimeMultiplier'] = 1.0  # 'hourly' = 12, '5 minutes' = 1'
        self.globals['unitTable']['gallons']['formatTotaldivisor'] = 1.0
        self.globals['unitTable']['gallons']['formatCurrent'] = "%d"
        self.globals['unitTable']['gallons']['formatTotal'] = "%d"
        self.globals['unitTable']['gallons']['currentUnits'] = 'gallons'
        self.globals['unitTable']['gallons']['accumUnits'] = 'gallons'

        self.globals['config'] = dict()
        self.globals['config']['address'] = ''
        self.globals['config']['clientId'] = ''
        self.globals['config']['secret'] = ''
        self.globals['config']['userName'] = ''
        self.globals['config']['password'] = ''

        self.globals['config'][
            'appName'] = ''  # Not sure what this is for! Name provided by Get ServiceLocations Smappee call

        self.globals['config']['accessToken'] = ''
        self.globals['config']['refreshToken'] = ''
        self.globals['config']['tokenExpiresIn'] = 0
        self.globals['config']['tokenExpiresDateTimeUtc'] = 0

        self.globals['config']['supportsElectricity'] = False
        self.globals['config']['supportsElectricityNet'] = False
        self.globals['config']['supportsElectricitySaved'] = False
        self.globals['config']['supportsSolar'] = False
        self.globals['config']['supportsSolarUsed'] = False
        self.globals['config']['supportsSolarExported'] = False
        self.globals['config']['supportsSensor'] = False

        # Initialise Global arrays to store internal details about Smappees, Smappee Appliances & Plugs
        self.globals['pluginInitialised'] = False
        self.globals['consumptionDataReceived'] = False  # Used to signify it is now OK to get Events
        self.globals[
            'smappeeServiceLocationIdToDevId'] = {}  # Used to derive Smappee Device Ids from Smappee Service Location Ids
        self.globals['smappees'] = {}
        self.globals['smappeeAppliances'] = {}
        self.globals['smappeePlugs'] = dict()

        self.globals['polling'] = dict()
        self.globals['polling']['threadActive'] = False        
        self.globals['polling']['status'] = False
        self.globals['polling']['seconds'] = float(300.0)  # 5 minutes
        self.globals['polling']['threadEnd'] = False

        # Set Plugin Config Values
        self.closedPrefsConfigUi(pluginPrefs, False)

    def __del__(self):

        indigo.PluginBase.__del__(self)

    def startup(self):
        self.methodTracer.threaddebug(u"CLASS: Plugin")

        # Initialise debug  
        self.globals['debug']['general'] = bool(self.pluginPrefs.get("debugGeneral", False))
        self.globals['debug']['deviceFactory'] = bool(self.pluginPrefs.get("debugDeviceFactory", False))
        self.globals['debug']['smappeInterface'] = bool(self.pluginPrefs.get("debugSmappeeInterface", False))
        self.globals['debug']['methodTrace'] = bool(self.pluginPrefs.get("debugMethodTrace", False))
        self.globals['debug']['polling'] = bool(self.pluginPrefs.get("debugPolling", False))

        self.globals['debug']['active'] = self.globals['debug']['general'] or self.globals['debug']['deviceFactory'] or \
                                          self.globals['debug']['smappeInterface'] or self.globals['debug']['methodTrace'] or \
                                          self.globals['debug']['polling']

        indigo.devices.subscribeToChanges()

        # Create queues
        self.globals['queues'] = dict()
        self.globals['queues']['sendToSmappee'] = Queue.Queue()  # Used to queue smappee commands
        self.globals['queues']['process'] = Queue.Queue()  # Used to queue output from smappee
        self.globals['queues']['initialised'] = True

        self.globals['threads'] = dict()
        self.globals['threads']['polling'] = dict()
        self.globals['threads']['smappeeInterface'] = dict()

        self.globals['threads']['smappeeInterface']['event'] = threading.Event()
        self.globals['threads']['smappeeInterface']['thread'] = ThreadSmappeeInterface(self.globals,
                                                                                             self.globals['threads'][
                                                                                                 'smappeeInterface'][
                                                                                                 'event'])
        self.globals['threads']['smappeeInterface']['thread'].start()

        # Now send an INITIALISE command (via queue) to Smappee to initialise the plugin
        self.globals['queues']['sendToSmappee'].put(['INITIALISE'])

        # Start the Polling thread
        if self.globals['polling']['status'] and not self.globals['polling']['threadActive']:
            self.globals['threads']['polling']['event'] = threading.Event()
            self.globals['threads']['polling']['thread'] = ThreadPolling(self.globals,
                                                                         self.globals['threads']['polling']['event'])
            self.globals['threads']['polling']['thread'].start()

        self.generalLogger.info(u"Initialisation in progress ...")

    def shutdown(self):
        self.methodTracer.threaddebug(u"CLASS: Plugin")

        self.generalLogger.info(u"Plugin shutdown requested")

        self.globals['queues']['sendToSmappee'] .put(['ENDTHREAD'])

        if hasattr(self, 'pollingThread'):
            if self.globals['polling']['status']:
                self.globals['polling']['threadEnd'] = True
                self.pollingEvent.set()  # Stop the Polling Thread

        # time.sleep(2)  # Wait 2 seconds before contacting Smappee - gives plugin time to properly shutdown

        self.generalLogger.info(u"Plugin shutdown complete")

    def getPrefsConfigUiValues(self):
        self.methodTracer.threaddebug(u"CLASS: getPrefsConfigUiValues")

        prefsConfigUiValues = self.pluginPrefs
        if "smappeeDeviceFolder" not in prefsConfigUiValues:
            prefsConfigUiValues["smappeeDeviceFolder"] = 'SMAPPEE'

        return prefsConfigUiValues

    def validatePrefsConfigUi(self, valuesDict):
        self.methodTracer.threaddebug(u"CLASS: Plugin")

        return True

    def closedPrefsConfigUi(self, valuesDict, userCancelled):
        self.methodTracer.threaddebug(u"CLASS: closedPrefsConfigUi")
        self.generalLogger.debug(u"'closePrefsConfigUi' called with userCancelled = %s" % str(userCancelled))

        try:
            if userCancelled:
                return

            if "smappeeAddress" in valuesDict:
                self.globals['config']['address'] = valuesDict["smappeeAddress"]
            else:
                self.globals['config']['address'] = "https://app1pub.smappee.net/dev/v1/servicelocation"

            if "smappeeClientId" in valuesDict:
                self.globals['config']['clientId'] = valuesDict["smappeeClientId"]
            else:
                self.globals['config']['clientId'] = ""

            if "smappeeSecret" in valuesDict:
                self.globals['config']['secret'] = valuesDict["smappeeSecret"]
            else:
                self.globals['config']['secret'] = ""

            if "smappeeUserName" in valuesDict:
                self.globals['config']['userName'] = valuesDict["smappeeUserName"]
            else:
                self.globals['config']['userName'] = ""

            if "smappeePassword" in valuesDict:
                self.globals['config']['password'] = valuesDict["smappeePassword"]
            else:
                self.globals['config']['password'] = ""

            # ### FOLDER ###
            if "smappeeDeviceFolder" in valuesDict:
                self.globals['config']['smappeeDeviceFolder'] = valuesDict["smappeeDeviceFolder"]
            else:
                self.globals['config']['smappeeDeviceFolder'] = "SMAPPEE"

            # Create Smappee folder name (if required) in devices (for smappee monitors, appliances and plugs)
            self.deviceFolderName = self.globals['config']['smappeeDeviceFolder']
            if self.deviceFolderName == '':
                self.globals['devicesFolderId'] = None  # Not required
            else:
                if self.deviceFolderName not in indigo.devices.folders:
                    self.deviceFolder = indigo.devices.folder.create(self.deviceFolderName)
                self.globals['devicesFolderId'] = indigo.devices.folders.getId(self.deviceFolderName)

            # ### POLLING ###
            self.globals['polling']['status'] = bool(valuesDict.get("statusPolling", False))
            self.globals['polling']['seconds'] = float(valuesDict.get("pollingSeconds", float(300.0)))  # Default to 5 minutes

            # Check monitoring / debug / filered IP address options  
            self.setDebuggingLevels(valuesDict)

            # Following logic checks whether polling is required.
            #
            # If it isn't required, then it checks if a polling thread exists and if it does it ends it
            # If it is required, then it checks if a pollling thread exists and 
            #   if a polling thread doesn't exist it will create one as long as the start logic has completed and created a Smappee Command Queue.
            #   In the case where a Smappee command queue hasn't been created then it means 'Start' is yet to run and so 
            #   'Start' will create the polling thread. So this bit of logic is mainly used where polling has been turned off
            #   after starting and then turned on again
            # If polling is required and a polling thread exists, then the logic 'sets' an event to cause the polling thread to awaken and
            #   update the polling interval

            if not self.globals['polling']['status']:
                if self.globals['polling']['threadActive']:
                    self.globals['polling']['forceThreadEnd'] = True
                    self.globals['threads']['polling']['event'].set()  # Stop the Polling Thread
                    self.globals['threads']['polling']['thread'].join(5.0)  # Wait for up t0 5 seconds for it to end
                    del self.globals['threads']['polling']['thread']  # Delete thread so that it can be recreated if polling is turned on again
            else:
                if not self.globals['polling']['threadActive']:
                    if self.globals['queues']['initialised']:
                        self.globals['polling']['forceThreadEnd'] = False
                        self.globals['threads']['polling']['event'] = threading.Event()
                        self.globals['threads']['polling']['thread'] = ThreadPolling(self.globals, self.globals['threads']['polling']['event'])
                        self.globals['threads']['polling']['thread'].start()
                else:
                    self.globals['polling']['forceThreadEnd'] = False
                    self.globals['threads']['polling']['event'].set()  # cause the Polling Thread to update immediately with potentially new polling seconds value

        except StandardError, e:
            self.generalLogger.error(u"closedPrefsConfigUi error detected. Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))   
            return True

    def setDebuggingLevels(self, valuesDict):
        self.methodTracer.threaddebug(u"CLASS: Plugin")

        self.globals['debug']['debugEnabled'] = bool(valuesDict.get("debugEnabled", False))

        self.globals['debug']['general'] = logging.INFO  # For general debugging of the main thread
        self.globals['debug']['deviceFactory'] = logging.INFO  # For logging messages 
        self.globals['debug']['smappeeInterface'] = logging.INFO  # For debugging messages
        self.globals['debug']['methodTrace'] = logging.INFO  # For displaying method invocations i.e. trace method
        self.globals['debug']['polling'] = logging.INFO  # For polling debugging

        if not self.globals['debug']['debugEnabled']:
            self.plugin_file_handler.setLevel(logging.INFO)
        else:
            self.plugin_file_handler.setLevel(logging.THREADDEBUG)

        debugGeneral = bool(valuesDict.get("debugGeneral", False))
        debugDeviceFactory = bool(valuesDict.get("debugDeviceFactory", False))
        debugSmappeeInterface = bool(valuesDict.get("debugSmappeeInterface", False))
        debugMethodTrace = bool(valuesDict.get("debugMethodTrace", False))
        debugPolling = bool(valuesDict.get("debugPolling", False))

        if debugGeneral:
            self.globals['debug']['general'] = logging.DEBUG  # For general debugging of the main thread
            self.generalLogger.setLevel(self.globals['debug']['general'])
        if debugDeviceFactory:
            self.globals['debug']['deviceFactory'] = logging.DEBUG  # For logging device factory processing 
        if debugSmappeeInterface:
            self.globals['debug']['smappeeInterface'] = logging.DEBUG  # For debugging interaction with Smappee
        if debugMethodTrace:
            self.globals['debug']['methodTrace'] = logging.THREADDEBUG  # For displaying method invocations i.e. trace method
        if debugPolling:
            self.globals['debug']['polling'] = logging.DEBUG  # For polling debugging

        self.globals['debug']['debugActive'] = debugGeneral or debugDeviceFactory or debugSmappeeInterface or debugMethodTrace or debugPolling

        if not self.globals['debug']['debugEnabled']:
            self.generalLogger.info(u"No debugging requested")
        else:
            debugTypes = []
            if debugGeneral:
                debugTypes.append('General')
            if debugDeviceFactory:
                debugTypes.append('Device Factory')
            if debugSmappeeInterface:
                debugTypes.append('Smappee Interface')
            if debugMethodTrace:
                debugTypes.append('Method Trace')
            if debugPolling:
                debugTypes.append('Polling')
            message = self.listActive(debugTypes)   
            self.generalLogger.warning(u"Debugging enabled for Smappee: %s" % message)

    def listActive(self, debugTypes):            
        self.methodTracer.threaddebug(u"CLASS: Plugin")

        loop = 0
        listedTypes = ''
        for debugType in debugTypes:
            if loop == 0:
                listedTypes = listedTypes + debugType
            else:
                listedTypes = listedTypes + ', ' + debugType
            loop += 1
        return listedTypes

    def runConcurrentThread(self):
        self.methodTracer.threaddebug(u"CLASS: Plugin")

        # This thread is used to handle responses from Smappee
        self.sleep(10)
        try:
            while True:
                try:
                    self.process = self.globals['queues']['process'].get(True, 5)  # Retrieve response from Smappee
                    try:
                        self.handleSmappeeResponse(self.process[0], self.process[1],
                                                   self.process[2])  # Handle response from Smappee
                    except StandardError, e:
                        self.generalLogger.error(
                            u"StandardError detected for function '%s'. Line '%s' has error='%s'" % (
                                self.process[0], sys.exc_traceback.tb_lineno, e))
                except Queue.Empty:
                    if self.stopThread:
                        raise self.StopThread  # Plugin shutdown request.
        except self.StopThread:
            # Optionally catch the StopThread exception and do any needed cleanup.
            self.generalLogger.debug(u"runConcurrentThread being stopped")

    def getDeviceFactoryUiValues(self, devIdList):
        self.methodTracer.threaddebug(u"getDeviceFactoryUiValues: devIdList = [%s]" % devIdList)

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

        self.monitorDeviceProcessed = False  # Used to detect if a major device electricity / electricity net / electricity saved / Solar / solar used / solar generated / gas or water has beed added or removed - if so the Plugin will restart when the dialogue is closed/cancelled

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

        if len(self.globals['smappeeServiceLocationIdToDevId']) == 1:
            self.smappeeServiceLocationId = self.globals['smappeeServiceLocationIdToDevId'].keys()[0]
            self.smappeeServiceLocationName = self.globals['smappeeServiceLocationIdToDevId'][self.serviceLocationId][
                'name']
            valuesDict["smappeeLocationValue"] = str(
                "%s: %s" % (self.smappeeServiceLocationId, self.smappeeServiceLocationName))
            valuesDict["hideSmappeeLocationValue"] = "false"
            valuesDict["hideSmappeeLocationList"] = "true"
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

        self.generalLogger.info(
            u"getDeviceFactoryUiValues [END]: EL-Detect=[%s], SO-Detect=[%s],  GW-Detect=[%s], AP-Detect=[%s], AC-Detect=[%s]" % (
                self.deviceDetectedSmappeeElectricity, self.deviceDetectedSmappeeSolar,
                self.deviceDetectedSmappeeSensor,
                self.deviceDetectedSmappeeAppliance, self.deviceDetectedSmappeeActuator))

        return valuesDict, errorMsgDict

    def validateDeviceFactoryUi(self, valuesDict, devIdList):
        self.methodTracer.threaddebug(u"CLASS: Plugin")

        errorsDict = indigo.Dict()
        return True, valuesDict, errorsDict

    def closedDeviceFactoryUi(self, valuesDict, userCancelled, devIdList):
        self.methodTracer.threaddebug(u"CLASS: Plugin")

        if self.monitorDeviceProcessed:
            self.generalLogger.info(u"Devices changed via 'Define and Sync' - restarting SMAPPEE Plugin . . . . .")

            serverPlugin = indigo.server.getPlugin(self.pluginId)
            serverPlugin.restart(waitUntilDone=False)
            return

        if not userCancelled:
            for sensorId in sorted(
                    self.globals['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['sensorIds']):
                if \
                        self.globals['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['sensorIds'][
                            sensorId][
                            'queued-add']:
                    serviceLocationId = self.smappeeServiceLocationId
                    serviceLocationName = \
                        self.globals['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['name']
                    address = sensorId
                    name = self.globals['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['sensorIds'][
                        sensorId]['name']
                    deviceType = \
                        self.globals['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['sensorIds'][
                            sensorId]['deviceType']

                    self.globals['queues']['process'].put(['NEW_SENSOR', serviceLocationId, (serviceLocationName, address, name)])

            for applianceId in sorted(
                    self.globals['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['applianceIds']):
                if self.globals['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['applianceIds'][
                        applianceId]['queued-add']:
                    serviceLocationId = self.smappeeServiceLocationId
                    serviceLocationName = \
                        self.globals['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['name']
                    address = applianceId
                    name = \
                        self.globals['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['applianceIds'][
                            applianceId]['name']

                    self.globals['queues']['process'].put(["NEW_APPLIANCE", serviceLocationId, (serviceLocationName, address, name)])

            for actuatorId in sorted(
                    self.globals['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['actuatorIds']):
                if self.globals['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['actuatorIds'][
                        actuatorId]['queued-add']:
                    serviceLocationId = self.smappeeServiceLocationId
                    serviceLocationName = \
                        self.globals['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['name']
                    address = actuatorId
                    name = \
                        self.globals['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['actuatorIds'][
                            actuatorId]['name']

                    self.globals['queues']['process'].put(["NEW_ACTUATOR", serviceLocationId, (serviceLocationName, address, name)])

        else:
            for sensorId in sorted(
                    self.globals['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['sensorIds']):
                self.globals['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['sensorIds'][sensorId][
                    'queued-add'] = False
                self.globals['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['sensorIds'][sensorId][
                    'queued-remove'] = False
            for applianceId in sorted(
                    self.globals['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['applianceIds']):
                self.globals['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['applianceIds'][
                    applianceId]['queued-add'] = False
                self.globals['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['applianceIds'][
                    applianceId]['queued-remove'] = False
            for actuatorId in sorted(
                    self.globals['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['actuatorIds']):
                self.globals['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['actuatorIds'][
                    actuatorId]['queued-add'] = False
                self.globals['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['actuatorIds'][
                    actuatorId]['queued-remove'] = False

        return

    def _getSmappeeLocationList(self, filter="", valuesDict=None, typeId="", targetId=0):
        self.methodTracer.threaddebug(u"CLASS: _getSmappeeLocationList")

        return self.listItemsSmappeeLocationList

    def _prepareGetSmappeeLocationList(self, valuesDict, devIdList):
        self.methodTracer.threaddebug(u"CLASS: _prepareGetSmappeeLocationList")

        valuesDict["hideSmappeeLocationValue"] = "true"
        valuesDict["hideSmappeeLocationList"] = "false"

        listToDisplay = []
        self.locationCount = 0
        self.locationAvailableCount = 0
        for self.smappeeServiceLocationId in sorted(self.globals['smappeeServiceLocationIdToDevId']):
            self.serviceLocationName = self.globals['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId][
                'name']
            self.locationCount += 1
            if self.globals['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['electricityId'] == 0 and \
                    self.globals['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['solarId'] == 0:
                listToDisplay.append((self.smappeeServiceLocationId, self.serviceLocationName))
                self.locationAvailableCount += 1
            else:
                self.serviceLocationName = str("Location '%s:%s' assigned to Smappee" % (self.smappeeServiceLocationId,
                                                                                         self.globals[
                                                                                             'smappeeServiceLocationIdToDevId'][
                                                                                             self.smappeeServiceLocationId][
                                                                                             'name']))
                listToDisplay.append((self.smappeeServiceLocationId, self.serviceLocationName))

        if self.locationCount == 0:
            listToDisplay = ["NONE", "No Smappee locations found"]
        else:
            if self.locationAvailableCount == 0:
                listToDisplay.insert(0, ("NONE", "All location(s) already assigned"))
            else:
                listToDisplay.insert(0, ("NONE", "- Select Smappee Location -"))

            if self.locationCount == 1:
                # As only one location, don't display list and skip striaght to displaying value
                valuesDict["hideSmappeeLocationValue"] = "false"
                valuesDict["hideSmappeeLocationList"] = "true"

        self.listItemsSmappeeLocationList = listToDisplay

        return valuesDict

    def _smappeeLocationSelected(self, valuesDict, typeId, devIdList):
        self.methodTracer.threaddebug(u"CLASS: _smappeeLocationSelected")

        self.deviceDetectedSmappeeElectricity = False
        self.deviceDetectedSmappeeSolar = False
        self.deviceDetectedSmappeeAppliance = False
        self.deviceDetectedSmappeeActuator = False

        if "smappeeLocationList" in valuesDict:
            self.smappeeServiceLocationId = valuesDict["smappeeLocationList"]
            if self.smappeeServiceLocationId != 'NONE':
                if self.smappeeServiceLocationId in self.globals['smappeeServiceLocationIdToDevId']:
                    self.smappeeServiceLocationName = \
                        self.globals['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['name']
                    valuesDict["hideSmappeeLocationValue"] = "false"
                    valuesDict["hideSmappeeLocationList"] = "true"

                    valuesDict["smappeeLocationValue"] = str(
                        "%s: %s" % (self.smappeeServiceLocationId, self.smappeeServiceLocationName))
                    if self.globals['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId][
                            'electricityId'] != 0:
                        self.deviceDetectedSmappeeElectricity = True
                    if self.globals['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['solarId'] != 0:
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

    def _getDefinedSmappeeElectricitySolarList(self, filter, valuesDict, devIdList):
        self.methodTracer.threaddebug(
            u"CLASS: _getDefinedSmappeeElectricitySolarList; LOC=[%s]" % self.smappeeServiceLocationId)

        return self.listItemsDefinedSmappeeMainList

    def _prepareSmappeeList(self, valuesDict, devIdList):

        self.methodTracer.threaddebug(u"CLASS: _prepareSmappeeList; LOC=[%s]" % self.smappeeServiceLocationId)

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
        self.deviceFactoryLogger.debug(u"SMAPPEE [F-0]: _prepareSmappeeList")

        for dev in indigo.devices.iter("self"):
            self.deviceFactoryLogger.debug(u"SMAPPEE [F-1]: %s [devTypeId = %s]" % (dev.name, dev.deviceTypeId))
            if dev.deviceTypeId == "smappeeElectricity" or dev.deviceTypeId == "smappeeElectricityNet" or dev.deviceTypeId == "smappeeElectricitySaved" or dev.deviceTypeId == "smappeeSolar" or dev.deviceTypeId == "smappeeSolarUsed" or dev.deviceTypeId == "smappeeSolarExported":

                self.deviceFactoryLogger.debug(u"SMAPPEE [F-2]: %s [devTypeId = %s]" % (dev.name, dev.deviceTypeId))

                if dev.pluginProps['serviceLocationId'] == self.smappeeServiceLocationId:
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
                        self.generalLogger.error(
                            u"SMAPPEE [F-E]: %s [devTypeId = %s] UNKNOWN" % (dev.name, dev.deviceTypeId))

                    self.deviceFactoryLogger.debug(u"SMAPPEE [F-3]: %s [devTypeId = %s]" % (dev.name, dev.deviceTypeId))

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

        if (valuesDict["addSmappeeElectricityDeviceEnabled"] == 'false' and valuesDict[
            "removeSmappeeElectricityDeviceEnabled"] == 'false' and
                valuesDict["addSmappeeElectricityNetDeviceEnabled"] == 'false' and valuesDict[
                    "removeSmappeeElectricityNetDeviceEnabled"] == 'false' and
                valuesDict["addSmappeeElectricitySavedDeviceEnabled"] == 'false' and valuesDict[
                    "removeSmappeeElectricitySavedDeviceEnabled"] == 'false' and
                valuesDict["addSmappeeSolarDeviceEnabled"] == 'false' and valuesDict[
                    "removeSmappeeSolarDeviceEnabled"] == 'false' and
                valuesDict["addSmappeeSolarUsedDeviceEnabled"] == 'false' and valuesDict[
                    "removeSmappeeSolarUsedDeviceEnabled"] == 'false' and
                valuesDict["addSmappeeSolarExportedDeviceEnabled"] == 'false' and valuesDict[
                    "removeSmappeeSolarExportedDeviceEnabled"] == 'false'):
            valuesDict["helpSmappeeElectricitySolarEnabled"] = 'true'
        else:
            valuesDict["helpSmappeeElectricitySolarEnabled"] = 'false'

        if len(listToDisplay) == 0:
            listToDisplay.append((0, "- No Smappee Devices Defined -"))

        self.listItemsDefinedSmappeeMainList = listToDisplay

        return valuesDict

    def _addSmappeeElectricityDevice(self, valuesDict, devIdList):
        self.methodTracer.threaddebug(u"CLASS: _addSmappeeElectricityDevice; Location[%s:%s]" % (
            self.smappeeServiceLocationId, self.smappeeServiceLocationName))

        self.monitorDeviceProcessed = True  # Forces Plugin to restart when the Device Factory dialogue is closed or cancelled 

        newdev = indigo.device.create(protocol=indigo.kProtocol.Plugin,
                                      address="E000",
                                      name="Smappee Electricity V2",
                                      description="Smappee",
                                      pluginId="com.autologplugin.indigoplugin.smappeecontroller",
                                      deviceTypeId="smappeeElectricity",
                                      folder=self.globals['devicesFolderId'],
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
        newdev.subModel = "Elec."  # Manually need to set the model and subModel names (for UI only)
        newdev.configured = True
        newdev.enabled = True
        newdev.replaceOnServer()

        self.setSmappeeServiceLocationIdToDevId('ADD_UPDATE', 'smappeeElectricity', self.smappeeServiceLocationId,
                                                newdev.id, "", "")

        valuesDict["addSmappeeElectricityDeviceEnabled"] = 'false'
        valuesDict["removeSmappeeElectricityDeviceEnabled"] = 'true'

        devIdList.extend([newdev.id])

        valuesDict = self._prepareSmappeeList(valuesDict, devIdList)

        return valuesDict

    def _removeSmappeeElectricityDevice(self, valuesDict, devIdList):
        self.methodTracer.threaddebug(u"CLASS: _removeSmappeeElectricityDevice")

        self.monitorDeviceProcessed = True  # Forces Plugin to restart when the Device Factory dialogue is closed or cancelled 

        for dev in indigo.devices.iter("self"):
            try:
                if dev.deviceTypeId == "smappeeElectricity":
                    serviceLocationId = dev.pluginProps['serviceLocationId']
                    self.setSmappeeServiceLocationIdToDevId('STOP', 'smappeeElectricity', serviceLocationId, dev.id, "",
                                                            "")

                    if dev.id in self.globals['smappees']:
                        self.globals['smappees'].pop(dev.id, None)
                        self.deviceFactoryLogger.debug(u"_removeSmappeeElectricityDevice = POPPED")

                    indigo.device.delete(dev)

                    self.globals['config']['supportsElectricity'] = False

                    self.deviceFactoryLogger.debug(u"_removeSmappeeElectricityDevice = DELETED")
            except:
                self.deviceFactoryLogger.debug(u"_removeSmappeeElectricityDevice = EXCEPTION")
                pass  # delete doesn't allow (throws) on root elem

        valuesDict["addSmappeeElectricityDeviceEnabled"] = 'true'
        valuesDict["removeSmappeeElectricityDeviceEnabled"] = 'false'

        valuesDict = self._prepareSmappeeList(valuesDict, devIdList)

        return valuesDict

    def _addSmappeeElectricityNetDevice(self, valuesDict, devIdList):
        self.methodTracer.threaddebug(u"CLASS: _addSmappeeElectricityNetDevice")

        self.monitorDeviceProcessed = True  # Forces Plugin to restart when the Device Factory dialogue is closed or cancelled 

        newdev = indigo.device.create(protocol=indigo.kProtocol.Plugin,
                                      address="EN00",
                                      name="Smappee Net Electricity V2",
                                      description="Smappee",
                                      pluginId="com.autologplugin.indigoplugin.smappeecontroller",
                                      deviceTypeId="smappeeElectricityNet",
                                      folder=self.globals['devicesFolderId'],
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

        self.setSmappeeServiceLocationIdToDevId('ADD_UPDATE', 'smappeeElectricityNet', self.smappeeServiceLocationId,
                                                newdev.id, "", "")

        valuesDict["addSmappeeElectricityNetDeviceEnabled"] = 'false'
        valuesDict["removeSmappeeElectricityNetDeviceEnabled"] = 'true'

        devIdList.extend([newdev.id])

        valuesDict = self._prepareSmappeeList(valuesDict, devIdList)

        return valuesDict

    def _removeSmappeeElectricityNetDevice(self, valuesDict, devIdList):
        self.methodTracer.threaddebug(u"CLASS: _removeSmappeeElectricityNetDevice")

        self.monitorDeviceProcessed = True  # Forces Plugin to restart when the Device Factory dialogue is closed or cancelled 

        for dev in indigo.devices.iter("self"):
            try:
                if dev.deviceTypeId == "smappeeElectricityNet":
                    serviceLocationId = dev.pluginProps['serviceLocationId']

                    self.setSmappeeServiceLocationIdToDevId('STOP', 'smappeeElectricityNet', serviceLocationId, dev.id,
                                                            "", "")

                    if dev.id in self.globals['smappees']:
                        self.globals['smappees'].pop(dev.id, None)
                        self.deviceFactoryLogger.debug(u"_removeSmappeeElectricityNetDevice = POPPED")

                    indigo.device.delete(dev)

                    self.globals['config']['supportsElectricityNet'] = False

                    self.deviceFactoryLogger.debug(u"_removeSmappeeElectricityNetDevice = DELETED")
            except:
                self.deviceFactoryLogger.debug(u"_removeSmappeeElectricityNetDevice = EXCEPTION")
                pass  # delete doesn't allow (throws) on root elem

        valuesDict["addSmappeeElectricityNetDeviceEnabled"] = 'true'
        valuesDict["removeSmappeeElectricityNetDeviceEnabled"] = 'false'

        valuesDict = self._prepareSmappeeList(valuesDict, devIdList)

        return valuesDict

    def _addSmappeeElectricitySavedDevice(self, valuesDict, devIdList):
        self.methodTracer.threaddebug(u"CLASS: _addSmappeeElectricitySavedDevice")

        self.monitorDeviceProcessed = True  # Forces Plugin to restart when the Device Factory dialogue is closed or cancelled 

        newdev = indigo.device.create(protocol=indigo.kProtocol.Plugin,
                                      address="ES00",
                                      name="Smappee Saved Electricity V2",
                                      description="Smappee",
                                      pluginId="com.autologplugin.indigoplugin.smappeecontroller",
                                      deviceTypeId="smappeeElectricitySaved",
                                      folder=self.globals['devicesFolderId'],
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

        self.setSmappeeServiceLocationIdToDevId('ADD_UPDATE', 'smappeeElectricitySaved', self.smappeeServiceLocationId,
                                                newdev.id, "", "")

        valuesDict["addSmappeeElectricitySavedDeviceEnabled"] = 'false'
        valuesDict["removeSmappeeElectricitySavedDeviceEnabled"] = 'true'

        devIdList.extend([newdev.id])

        valuesDict = self._prepareSmappeeList(valuesDict, devIdList)

        return valuesDict

    def _removeSmappeeElectricitySavedDevice(self, valuesDict, devIdList):
        self.methodTracer.threaddebug(u"CLASS: _removeSmappeeElectricitySavedDevice")

        self.monitorDeviceProcessed = True  # Forces Plugin to restart when the Device Factory dialogue is closed or cancelled 

        for dev in indigo.devices.iter("self"):
            try:
                if dev.deviceTypeId == "smappeeElectricitySaved":
                    serviceLocationId = dev.pluginProps['serviceLocationId']

                    self.setSmappeeServiceLocationIdToDevId('STOP', 'smappeeElectricitySaved', serviceLocationId,
                                                            dev.id, "", "")

                    if dev.id in self.globals['smappees']:
                        self.globals['smappees'].pop(dev.id, None)
                        self.deviceFactoryLogger.debug(u"_removeSmappeeElectricitySavedDevice = POPPED")

                    indigo.device.delete(dev)

                    self.globals['config']['supportsElectricitySaved'] = False

                    self.deviceFactoryLogger.debug(u"_removeSmappeeElectricitySavedDevice = DELETED")
            except:
                self.deviceFactoryLogger.debug(u"_removeSmappeeElectricitySavedDevice = EXCEPTION")
                pass  # delete doesn't allow (throws) on root elem

        valuesDict["addSmappeeElectricitySavedDeviceEnabled"] = 'true'
        valuesDict["removeSmappeeElectricitySavedDeviceEnabled"] = 'false'

        valuesDict = self._prepareSmappeeList(valuesDict, devIdList)

        return valuesDict

    def _addSmappeeSolarDevice(self, valuesDict, devIdList):
        self.methodTracer.threaddebug(u"CLASS: _addSmappeeSolarDevice")

        self.monitorDeviceProcessed = True  # Forces Plugin to restart when the Device Factory dialogue is closed or cancelled 

        newdev = indigo.device.create(protocol=indigo.kProtocol.Plugin,
                                      address="S000",
                                      name="Smappee Solar PV V2",
                                      description="Smappee",
                                      pluginId="com.autologplugin.indigoplugin.smappeecontroller",
                                      deviceTypeId="smappeeSolar",
                                      folder=self.globals['devicesFolderId'],
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

        self.setSmappeeServiceLocationIdToDevId('ADD_UPDATE', 'smappeeSolar', self.smappeeServiceLocationId, newdev.id,
                                                "", "")

        valuesDict["addSmappeeSolarDeviceEnabled"] = 'false'
        valuesDict["removeSmappeeSolarDeviceEnabled"] = 'true'

        devIdList.extend([newdev.id])

        valuesDict = self._prepareSmappeeList(valuesDict, devIdList)

        return valuesDict

    def _removeSmappeeSolarDevice(self, valuesDict, devIdList):
        self.methodTracer.threaddebug(u"CLASS: _removeSmappeeSolarDevice")

        self.monitorDeviceProcessed = True  # Forces Plugin to restart when the Device Factory dialogue is closed or cancelled 

        for dev in indigo.devices.iter("self"):
            try:
                if dev.deviceTypeId == "smappeeSolar":
                    serviceLocationId = dev.pluginProps['serviceLocationId']

                    self.setSmappeeServiceLocationIdToDevId('STOP', 'smappeeSolar', serviceLocationId, dev.id, "", "")

                    if dev.id in self.globals['smappees']:
                        self.globals['smappees'].pop(dev.id, None)
                        self.deviceFactoryLogger.debug(u"_removeSmappeeSolarDevice = POPPED")

                    indigo.device.delete(dev)

                    self.globals['config']['supportsSolar'] = False

                    self.deviceFactoryLogger.debug(u"_removeSmappeeSolarDevice = DELETED")
            except:
                self.deviceFactoryLogger.debug(u"_removeSmappeeSolarDevice = EXCEPTION")
                pass  # delete doesn't allow (throws) on root elem

        valuesDict["addSmappeeSolarDeviceEnabled"] = 'true'
        valuesDict["removeSmappeeSolarDeviceEnabled"] = 'false'

        valuesDict = self._prepareSmappeeList(valuesDict, devIdList)

        return valuesDict

    def _addSmappeeSolarUsedDevice(self, valuesDict, devIdList):
        self.methodTracer.threaddebug(u"CLASS: _addSmappeeSolarUsedDevice")

        self.monitorDeviceProcessed = True  # Forces Plugin to restart when the Device Factory dialogue is closed or cancelled 

        newdev = indigo.device.create(protocol=indigo.kProtocol.Plugin,
                                      address="SU00",
                                      name="Smappee Solar PV Used V2",
                                      description="Smappee",
                                      pluginId="com.autologplugin.indigoplugin.smappeecontroller",
                                      deviceTypeId="smappeeSolarUsed",
                                      folder=self.globals['devicesFolderId'],
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

        self.setSmappeeServiceLocationIdToDevId('ADD_UPDATE', 'smappeeSolarUsed', self.smappeeServiceLocationId,
                                                newdev.id, "", "")

        valuesDict["addSmappeeSolarUsedDeviceEnabled"] = 'false'
        valuesDict["removeSmappeeSolarUsedDeviceEnabled"] = 'true'

        devIdList.extend([newdev.id])

        valuesDict = self._prepareSmappeeList(valuesDict, devIdList)

        return valuesDict

    def _removeSmappeeSolarUsedDevice(self, valuesDict, devIdList):
        self.methodTracer.threaddebug(u"CLASS: _removeSmappeeSolarUsedDevice")

        self.monitorDeviceProcessed = True  # Forces Plugin to restart when the Device Factory dialogue is closed or cancelled 

        for dev in indigo.devices.iter("self"):
            try:
                if dev.deviceTypeId == "smappeeSolarUsed":
                    serviceLocationId = dev.pluginProps['serviceLocationId']

                    self.setSmappeeServiceLocationIdToDevId('STOP', 'smappeeSolarUsed', serviceLocationId, dev.id, "",
                                                            "")

                    if dev.id in self.globals['smappees']:
                        self.globals['smappees'].pop(dev.id, None)
                        self.deviceFactoryLogger.debug(u"_removeSmappeeSolarUsedDevice = POPPED")

                    indigo.device.delete(dev)

                    self.globals['config']['supportsSolarUsed'] = False

                    self.deviceFactoryLogger.debug(u"_removeSmappeeSolarUsedDevice = DELETED")
            except:
                self.deviceFactoryLogger.debug(u"_removeSmappeeSolarUsedDevice = EXCEPTION")
                pass  # delete doesn't allow (throws) on root elem

        valuesDict["addSmappeeSolarUsedDeviceEnabled"] = 'true'
        valuesDict["removeSmappeeSolarUsedDeviceEnabled"] = 'false'

        valuesDict = self._prepareSmappeeList(valuesDict, devIdList)

        return valuesDict

    def _addSmappeeSolarExportedDevice(self, valuesDict, devIdList):
        self.methodTracer.threaddebug(u"CLASS: _addSmappeeSolarExportedDevice")

        self.monitorDeviceProcessed = True  # Forces Plugin to restart when the Device Factory dialogue is closed or cancelled 

        newdev = indigo.device.create(protocol=indigo.kProtocol.Plugin,
                                      address="SE00",
                                      name="Smappee Solar PV Exported V2",
                                      description="Smappee",
                                      pluginId="com.autologplugin.indigoplugin.smappeecontroller",
                                      deviceTypeId="smappeeSolarExported",
                                      folder=self.globals['devicesFolderId'],
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

        self.setSmappeeServiceLocationIdToDevId('ADD_UPDATE', 'smappeeSolarExported', self.smappeeServiceLocationId,
                                                newdev.id, "", "")

        valuesDict["addSmappeeSolarExportedDeviceEnabled"] = 'false'
        valuesDict["removeSmappeeSolarExportedDeviceEnabled"] = 'true'

        devIdList.extend([newdev.id])

        valuesDict = self._prepareSmappeeList(valuesDict, devIdList)

        return valuesDict

    def _removeSmappeeSolarExportedDevice(self, valuesDict, devIdList):
        self.methodTracer.threaddebug(u"CLASS: _removeSmappeeSolarExportedDevice")

        self.monitorDeviceProcessed = True  # Forces Plugin to restart when the Device Factory dialogue is closed or cancelled 

        for dev in indigo.devices.iter("self"):
            try:
                if dev.deviceTypeId == "smappeeSolarExported":
                    serviceLocationId = dev.pluginProps['serviceLocationId']

                    self.setSmappeeServiceLocationIdToDevId('STOP', 'smappeeSolarExported', serviceLocationId, dev.id,
                                                            "", "")

                    if dev.id in self.globals['smappees']:
                        self.globals['smappees'].pop(dev.id, None)
                        self.deviceFactoryLogger.debug(u"_removeSmappeeSolarExportedDevice = POPPED")

                    indigo.device.delete(dev)

                    self.globals['config']['supportsSolarExported'] = False

                    self.deviceFactoryLogger.debug(u"_removeSmappeeSolarExportedDevice = DELETED")
            except:
                self.deviceFactoryLogger.debug(u"_removeSmappeeSolarExportedDevice = EXCEPTION")
                pass  # delete doesn't allow (throws) on root elem

        valuesDict["addSmappeeSolarExportedDeviceEnabled"] = 'true'
        valuesDict["removeSmappeeSolarExportedDeviceEnabled"] = 'false'

        valuesDict = self._prepareSmappeeList(valuesDict, devIdList)

        return valuesDict

    def _getDefinedSmappeeSensorList(self, filter="", valuesDict=None, typeId="", targetId=0):
        self.methodTracer.threaddebug(u"CLASS: _getDefinedSmappeeSensorList; LOC=[%s]" % self.smappeeServiceLocationId)

        return self.listItemsDefinedSmappeeSensorList

    def _prepareGetDefinedSmappeeSensorList(self, valuesDict):
        self.methodTracer.threaddebug(
            u"CLASS: _prepareGetDefinedSmappeeSensorList; LOC=[%s]" % self.smappeeServiceLocationId)

        listToDisplay = []

        if self.smappeeServiceLocationId == '' or self.smappeeServiceLocationId == 'NONE':
            return listToDisplay

        for dev in indigo.devices.iter("self"):
            if dev.deviceTypeId == "smappeeSensor" and dev.pluginProps[
                    'serviceLocationId'] == self.smappeeServiceLocationId:
                devName = dev.name
                listToDisplay.append((str(dev.id), devName))

        if not listToDisplay:
            listToDisplay.append((0, '- No Sensors Defined -'))

        listToDisplay = sorted(listToDisplay, key=lambda x: x[1])

        self.listItemsDefinedSmappeeSensorList = listToDisplay

        return valuesDict

    def _getPotentialSmappeeSensorList(self, filter="", valuesDict=None, typeId="", targetId=0):
        self.methodTracer.threaddebug(
            u"CLASS: _getPotentialSmappeeSensorList; LOC=[%s]" % self.smappeeServiceLocationId)

        return self.listItemsPotentialSmappeeSensorList

    def _prepareGetPotentialSmappeeSensorList(self, valuesDict):
        self.methodTracer.threaddebug(
            u"CLASS: _prepareGetPotentialSmappeeSensorList; LOC=[%s]" % self.smappeeServiceLocationId)

        listToDisplay = []

        if self.smappeeServiceLocationId == '' or self.smappeeServiceLocationId == 'NONE':
            return listToDisplay

        for sensorId in sorted(
                self.globals['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['sensorIds']):
            sensorName = \
                self.globals['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['sensorIds'][sensorId][
                    'name']
            sensorDevId = \
                self.globals['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['sensorIds'][sensorId][
                    'devId']
            queuedAdd = \
                self.globals['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['sensorIds'][sensorId][
                    'queued-add']
            if sensorDevId == 0:
                if queuedAdd:
                    sensorName = str("QUEUED: %s" % sensorName)
                listToDisplay.append((sensorId, sensorName))

        if not listToDisplay:
            listToDisplay.append((0, '- No Available Sensors Detected -'))
            valuesDict["addSmappeeSensorDeviceEnabled"] = 'false'
        else:
            valuesDict["addSmappeeSensorDeviceEnabled"] = 'true'

        listToDisplay = sorted(listToDisplay)

        self.listItemsPotentialSmappeeSensorList = listToDisplay

        return valuesDict

    def _addSmappeeSensorDevice(self, valuesDict, devIdList):
        self.methodTracer.threaddebug(
            u"CLASS: _addSmappeeSensorDevice; ValuesDict=[%s]" % valuesDict['potentialSmappeeSensorList'])

        for potentialSensorAddress in valuesDict['potentialSmappeeSensorList']:
            potentialSensorAddress = str(potentialSensorAddress)
            potentialSensorName = \
                self.globals['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['sensorIds'][
                    potentialSensorAddress]['name']
            if not self.globals['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['sensorIds'][
                    potentialSensorAddress]['queued-add']:
                self.setSmappeeServiceLocationIdToDevId('QUEUE-ADD', 'smappeeSensor', self.smappeeServiceLocationId, 0,
                                                        potentialSensorAddress, potentialSensorName)
            else:
                self.setSmappeeServiceLocationIdToDevId('DEQUEUE', 'smappeeSensor', self.smappeeServiceLocationId, 0,
                                                        potentialSensorAddress, potentialSensorName)

        valuesDict = self._prepareGetDefinedSmappeeSensorList(valuesDict)
        valuesDict = self._prepareGetPotentialSmappeeSensorList(valuesDict)

        return valuesDict

    def _getDefinedSmappeeApplianceList(self, filter="", valuesDict=None, typeId="", targetId=0):
        self.methodTracer.threaddebug(
            u"CLASS: _getDefinedSmappeeApplianceList; LOC=[%s]" % self.smappeeServiceLocationId)

        return self.listItemsDefinedSmappeeApplianceList

    def _prepareGetDefinedSmappeeApplianceList(self, valuesDict):
        self.methodTracer.threaddebug(
            u"CLASS: _prepareGetDefinedSmappeeApplianceList; LOC=[%s]" % self.smappeeServiceLocationId)

        listToDisplay = []

        if self.smappeeServiceLocationId == '' or self.smappeeServiceLocationId == 'NONE':
            return listToDisplay

        for dev in indigo.devices.iter("self"):
            if dev.deviceTypeId == "smappeeAppliance" and dev.pluginProps[
                    'serviceLocationId'] == self.smappeeServiceLocationId:
                devName = dev.name
                listToDisplay.append((str(dev.id), devName))

        if not listToDisplay:
            listToDisplay.append((0, '- No Appliances Defined -'))

        listToDisplay = sorted(listToDisplay, key=lambda x: x[1])

        self.listItemsDefinedSmappeeApplianceList = listToDisplay

        return valuesDict

    def _getPotentialSmappeeApplianceList(self, filter="", valuesDict=None, typeId="", targetId=0):
        self.methodTracer.threaddebug(
            u"CLASS: _getPotentialSmappeeApplianceList; LOC=[%s]" % self.smappeeServiceLocationId)

        return self.listItemsPotentialSmappeeApplianceList

    def _prepareGetPotentialSmappeeApplianceList(self, valuesDict):
        self.methodTracer.threaddebug(
            u"CLASS: _prepareGetPotentialSmappeeApplianceList; LOC=[%s]" % self.smappeeServiceLocationId)

        listToDisplay = []

        if self.smappeeServiceLocationId == '' or self.smappeeServiceLocationId == 'NONE':
            return listToDisplay

        for applianceId in sorted(
                self.globals['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['applianceIds']):
            applianceName = \
                self.globals['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['applianceIds'][
                    applianceId][
                    'name']
            applianceDevId = \
                self.globals['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['applianceIds'][
                    applianceId][
                    'devId']
            queuedAdd = \
                self.globals['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['applianceIds'][
                    applianceId][
                    'queued-add']
            if applianceDevId == 0:
                if queuedAdd:
                    applianceName = str("QUEUED: %s" % applianceName)
                listToDisplay.append((applianceId, applianceName))

        if not listToDisplay:
            listToDisplay.append((0, '- No Available Appliances Detected -'))
            valuesDict["addSmappeeApplianceDeviceEnabled"] = 'false'
        else:
            valuesDict["addSmappeeApplianceDeviceEnabled"] = 'true'

        listToDisplay = sorted(listToDisplay)

        self.listItemsPotentialSmappeeApplianceList = listToDisplay

        return valuesDict

    def _addSmappeeApplianceDevice(self, valuesDict, devIdList):
        self.methodTracer.threaddebug(
            u"CLASS: _addSmappeeApplianceDevice; ValuesDict=[%s]" % valuesDict['potentialSmappeeApplianceList'])

        for potentialApplianceAddress in valuesDict['potentialSmappeeApplianceList']:
            potentialApplianceAddress = str(potentialApplianceAddress)
            potentialApplianceName = \
                self.globals['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['applianceIds'][
                    potentialApplianceAddress]['name']
            if not self.globals['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['applianceIds'][
                    potentialApplianceAddress]['queued-add']:
                self.setSmappeeServiceLocationIdToDevId('QUEUE-ADD', 'smappeeAppliance', self.smappeeServiceLocationId,
                                                        0, potentialApplianceAddress, potentialApplianceName)
            else:
                self.setSmappeeServiceLocationIdToDevId('DEQUEUE', 'smappeeAppliance', self.smappeeServiceLocationId, 0,
                                                        potentialApplianceAddress, potentialApplianceName)

        valuesDict = self._prepareGetDefinedSmappeeApplianceList(valuesDict)
        valuesDict = self._prepareGetPotentialSmappeeApplianceList(valuesDict)

        return valuesDict

    def _getDefinedSmappeeActuatorList(self, filter="", valuesDict=None, typeId="", targetId=0):
        self.methodTracer.threaddebug(
            u"CLASS: _getDefinedSmappeeActuatorList; LOC=[%s]" % self.smappeeServiceLocationId)

        return self.listItemsDefinedSmappeeActuatorList

    def _prepareGetDefinedSmappeeActuatorList(self, valuesDict):
        self.methodTracer.threaddebug(
            u"CLASS: _prepareGetDefinedSmappeeActuatorList; LOC=[%s]" % self.smappeeServiceLocationId)

        listToDisplay = []

        if self.smappeeServiceLocationId == '' or self.smappeeServiceLocationId == 'NONE':
            return listToDisplay

        for dev in indigo.devices.iter("self"):
            if dev.deviceTypeId == "smappeeActuator" and dev.pluginProps[
                    'serviceLocationId'] == self.smappeeServiceLocationId:
                devName = dev.name
                listToDisplay.append((str(dev.id), devName))

        if not listToDisplay:
            listToDisplay.append((0, '- No Actuators Defined -'))

        listToDisplay = sorted(listToDisplay, key=lambda x: x[1])

        self.listItemsDefinedSmappeeActuatorList = listToDisplay

        return valuesDict

    def _getPotentialSmappeeActuatorList(self, filter="", valuesDict=None, typeId="", targetId=0):
        self.methodTracer.threaddebug(
            u"CLASS: _getPotentialSmappeeActuatorList; LOC=[%s]" % self.smappeeServiceLocationId)

        return self.listItemsPotentialSmappeeActuatorList

    def _prepareGetPotentialSmappeeActuatorList(self, valuesDict):
        self.methodTracer.threaddebug(
            u"CLASS: _prepareGetPotentialSmappeeActuatorList; LOC=[%s]" % self.smappeeServiceLocationId)

        listToDisplay = []

        if self.smappeeServiceLocationId == '' or self.smappeeServiceLocationId == 'NONE':
            return listToDisplay

        for actuatorId in sorted(
                self.globals['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['actuatorIds']):
            actuatorName = \
                self.globals['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['actuatorIds'][
                    actuatorId][
                    'name']
            actuatorDevId = \
                self.globals['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['actuatorIds'][
                    actuatorId][
                    'devId']
            queuedAdd = \
                self.globals['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['actuatorIds'][
                    actuatorId][
                    'queued-add']
            if actuatorDevId == 0:
                if queuedAdd:
                    actuatorName = str("QUEUED: %s" % actuatorName)
                listToDisplay.append((actuatorId, actuatorName))

        if not listToDisplay:
            listToDisplay.append((0, '- No Available Actuators Detected -'))
            valuesDict["addSmappeeActuatorDeviceEnabled"] = 'false'
        else:
            valuesDict["addSmappeeActuatorDeviceEnabled"] = 'true'

        listToDisplay = sorted(listToDisplay)

        self.listItemsPotentialSmappeeActuatorList = listToDisplay

        return valuesDict

    def _addSmappeeActuatorDevice(self, valuesDict, devIdList):
        self.methodTracer.threaddebug(u"CLASS: _addSmappeeActuatorDevice")

        for potentialActuatorAddress in valuesDict['potentialSmappeeActuatorList']:
            potentialActuatorAddress = str(potentialActuatorAddress)
            potentialActuatorName = \
                self.globals['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['actuatorIds'][
                    potentialActuatorAddress]['name']
            if not self.globals['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['actuatorIds'][
                    potentialActuatorAddress]['queued-add']:
                self.setSmappeeServiceLocationIdToDevId('QUEUE-ADD', 'smappeeActuator', self.smappeeServiceLocationId,
                                                        0, potentialActuatorAddress, potentialActuatorName)
            else:
                self.setSmappeeServiceLocationIdToDevId('DEQUEUE', 'smappeeActuator', self.smappeeServiceLocationId, 0,
                                                        potentialActuatorAddress, potentialActuatorName)

        valuesDict = self._prepareGetDefinedSmappeeActuatorList(valuesDict)
        valuesDict = self._prepareGetPotentialSmappeeActuatorList(valuesDict)

        return valuesDict

    def deviceUpdated(self, origDev, newDev):
        indigo.PluginBase.deviceUpdated(self, origDev, newDev)

        return

    def actionControlDimmerRelay(self, action, dev):
        self.methodTracer.threaddebug(u"CLASS: actionControlDimmerRelay")

        # ##### TURN ON ######
        if action.deviceAction == indigo.kDimmerRelayAction.TurnOn:
            # Command hardware module (dev) to turn ON here:
            self.processTurnOn(action, dev)
            dev.updateStateOnServer("onOffState", True)
            sendSuccess = True  # Assume succeeded

            if sendSuccess:
                # If success then log that the command was successfully sent.
                self.generalLogger.info(u"sent \"%s\" %s" % (dev.name, "on"))

                # And then tell the Indigo Server to update the state.
                # dev.updateStateOnServer(key="onOffState", value=True, uiValue="on")  # £££££££££££££££££££££££££££££££££££££££££££££££££££££££££££££££££££££££££

            else:
                # Else log failure but do NOT update state on Indigo Server.
                self.generalLogger.error(u"send \"%s\" %s failed" % (dev.name, "on"))

        # ##### TURN OFF #####
        elif action.deviceAction == indigo.kDimmerRelayAction.TurnOff:
            # Command hardware module (dev) to turn OFF here:
            self.processTurnOff(action, dev)
            dev.updateStateOnServer("onOffState", False)
            sendSuccess = True  # Assume succeeded

            if sendSuccess:
                # If success then log that the command was successfully sent.
                self.generalLogger.info(u"sent \"%s\" %s" % (dev.name, "off"))

                # And then tell the Indigo Server to update the state:
                # dev.updateStateOnServer(key="onOffState", value=False, uiValue="off")  # £££££££££££££££££££££££££££££££££££££££££££££££££££££££££££££££££££££££££
            else:
                # Else log failure but do NOT update state on Indigo Server.
                self.generalLogger.error(u"send \"%s\" %s failed" % (dev.name, "off"))

        # ##### TOGGLE #####
        elif action.deviceAction == indigo.kDimmerRelayAction.Toggle:
            # Command hardware module (dev) to toggle here:
            self.processTurnOnOffToggle(action, dev)
            newOnState = not dev.onState
            sendSuccess = True  # Assume succeeded

            if sendSuccess:
                # If success then log that the command was successfully sent.
                self.generalLogger.info(u"sent \"%s\" %s" % (dev.name, "toggle"))

                # And then tell the Indigo Server to update the state:
                dev.updateStateOnServer("onOffState", newOnState)
            else:
                # Else log failure but do NOT update state on Indigo Server.
                self.generalLogger.error(u"send \"%s\" %s failed" % (dev.name, "toggle"))

    #########################
    # General Action callback
    #########################
    def actionControlGeneral(self, action, dev):
        self.methodTracer.threaddebug(u"CLASS: actionControlGeneral")

        # ##### ENERGY UPDATE #####
        if action.deviceAction == indigo.kDeviceGeneralAction.EnergyUpdate:
            # Request hardware module (dev) for its most recent meter data here:
            self.generalLogger.info(u"sent \"%s\" %s" % (dev.name, "energy update request"))
            self.processUpdate(action, dev)

        # ##### ENERGY RESET #####
        elif action.deviceAction == indigo.kDeviceGeneralAction.EnergyReset:
            # Request that the hardware module (dev) reset its accumulative energy usage data here:
            self.generalLogger.info(u"sent \"%s\" %s" % (dev.name, "energy reset request"))
            self.processReset(action, dev)

        # ##### STATUS REQUEST #####
        elif action.deviceAction == indigo.kDeviceGeneralAction.RequestStatus:
            # Query hardware module (dev) for its current status here:

            self.generalLogger.info(u"sent \"%s\" %s" % (dev.name, "status request"))

    def processUpdate(self, pluginAction, dev):  # Dev is a Smappee
        self.methodTracer.threaddebug(u"CLASS: processUpdate")

        self.generalLogger.debug(u"'processUpdate' [%s]" % (str(dev.pluginProps['serviceLocationId'])))

        self.globals['queues']['sendToSmappee'].put(["GET_CONSUMPTION", str(dev.pluginProps['serviceLocationId'])])

        return

    def processReset(self, pluginAction, dev):  # Dev is a Smappee
        self.methodTracer.threaddebug(u"CLASS: processReset")

        self.generalLogger.debug(u"'processReset' [%s]" % (str(dev.pluginProps['serviceLocationId'])))

        if "accumEnergyTotal" in dev.states:
            if float(dev.states.get("accumEnergyTotal", 0)) != 0.0:
                self.generalLogger.debug(
                    u"'processReset' accumEnergyTotal=[%f]" % (float(dev.states.get("accumEnergyTotal", 0))))
                self.globals['queues']['sendToSmappee'].put(["RESET_CONSUMPTION", str(dev.pluginProps['serviceLocationId'])])

        return

    def processTurnOnOffToggle(self, pluginAction, dev):  # Dev is a mappee Appliance
        self.methodTracer.threaddebug(u"CLASS: processTurnOnOffToggle")

        self.generalLogger.debug(u"'processTurnOnOffToggle' [%s]" % (self.globals['smappeePlugs'][dev.id]['address']))

        if dev.onState:
            self.processTurnOff(pluginAction, dev)
        else:
            self.processTurnOn(pluginAction, dev)
        return

    def processTurnOn(self, pluginAction, dev):  # Dev is a Smappee Actuator
        self.methodTracer.threaddebug(u"CLASS: processTurnOn")

        self.generalLogger.debug(u"'processTurnOn' [%s]" % (self.globals['smappeePlugs'][dev.id]['address']))

        #  Convert Address from "P012" to "12" i.e. remove leading P and leading 0's
        actuatorAddress = self.globals['smappeePlugs'][dev.id]['address'][1:].lstrip("0")

        self.globals['queues']['sendToSmappee'].put(['ON', str(dev.pluginProps['serviceLocationId']), actuatorAddress])

        return

    def processTurnOff(self, pluginAction, dev):  # Dev is a Smappee Appliance
        self.methodTracer.threaddebug(u"CLASS: processTurnOff")

        self.generalLogger.debug(u"'processTurnOff' [%s]" % (self.globals['smappeePlugs'][dev.id]['address']))

        #  Convert Address from "P012" to "12" i.e. remove leading P and leading 0's
        actuatorAddress = self.globals['smappeePlugs'][dev.id]['address'][1:].lstrip("0")

        self.globals['queues']['sendToSmappee'].put(['OFF', str(dev.pluginProps['serviceLocationId']), actuatorAddress])

        return

    def handleCreateNewSensor(self, commandSentToSmappee, responseLocationId, responseFromSmappee):
        self.methodTracer.threaddebug(u"CLASS: handleCreateNewSensor")

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
                                                    folder=self.globals['devicesFolderId'],
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

            self.setSmappeeServiceLocationIdToDevId('DEQUEUE', 'smappeeSensor', serviceLocationId, smappeeSensorDev.id,
                                                    address, name)

        except StandardError, e:
            self.generalLogger.error(u"StandardError detected in 'createNewSensor'. Line '%s' has error='%s'" % (
                sys.exc_traceback.tb_lineno, e))
            self.generalLogger.error(u"Response from Smappee was:'%s'" % responseFromSmappee)

    def handleCreateNewAppliance(self, commandSentToSmappee, responseLocationId, responseFromSmappee):
        self.methodTracer.threaddebug(u"CLASS: handleCreateNewAppliance")

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
                                                       folder=self.globals['devicesFolderId'],
                                                       props={"SupportsEnergyMeter": True,
                                                              "SupportsEnergyMeterCurPower": True,
                                                              "serviceLocationId": serviceLocationId,
                                                              "serviceLocationName": serviceLocationName,
                                                              "smappeeApplianceEventLastRecordedTimestamp": 0.0,
                                                              "showApplianceEventStatus": True,
                                                              "hideApplianceSmappeeEvents": False,
                                                              "smappeeApplianceEventStatus": "NONE"})

            self.setSmappeeServiceLocationIdToDevId('DEQUEUE', 'smappeeAppliance', serviceLocationId,
                                                    smappeeApplianceDev.id, address, name)

        except StandardError, e:
            self.generalLogger.error(u"StandardError detected in 'createNewAppliance'. Line '%s' has error='%s'" % (
                sys.exc_traceback.tb_lineno, e))
            self.generalLogger.error(u"Response from Smappee was:'%s'" % responseFromSmappee)

    def handleCreateNewActuator(self, commandSentToSmappee, responseLocationId, responseFromSmappee):
        self.methodTracer.threaddebug(u"CLASS: handleCreateNewActuator")

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
                                                      folder=self.globals['devicesFolderId'],
                                                      props={"SupportsStatusRequest": False,
                                                             "SupportsAllOff": True,
                                                             "SupportsEnergyMeter": False,
                                                             "SupportsEnergyMeterCurPower": False,
                                                             "serviceLocationId": serviceLocationId,
                                                             "serviceLocationName": serviceLocationName})

            self.setSmappeeServiceLocationIdToDevId('DEQUEUE', 'smappeeActuator', serviceLocationId,
                                                    smappeeActuatorDev.id, address, name)

        except StandardError, e:
            self.generalLogger.error(u"StandardError detected in 'createNewActuator'. Line '%s' has error='%s'" % (
                sys.exc_traceback.tb_lineno, e))
            self.generalLogger.error(u"Response from Smappee was:'%s'" % responseFromSmappee)

    def validateSmappeResponse(self, commandSentToSmappee, responseLocationId, responseFromSmappee):
        self.methodTracer.threaddebug(u"CLASS: validateSmappeResponse")

        try:
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

                self.generalLogger.error(u"%s" % message)
                return False, ''

                # Ensure that response is enclose in square brackets '[' and ']'
            try:
                if responseFromSmappee[:1] != '[':
                    responseFromSmappee = '[' + responseFromSmappee + ']'
            except StandardError, e:
                self.generalLogger.error(u"StandardError detected in 'validateSmappeResponse'. Type=%s, Len=%s" % (
                    type(responseFromSmappee), len(responseFromSmappee)))
                if len(responseFromSmappee) == 3:
                    self.generalLogger.error(
                        u"StandardError detected in 'validateSmappeResponse'. Item[1]=%s" % (responseFromSmappee[0]))
                    self.generalLogger.error(
                        u"StandardError detected in 'validateSmappeResponse'. Item[2]=%s" % (responseFromSmappee[1]))
                    self.generalLogger.error(
                        u"StandardError detected in 'validateSmappeResponse'. Item[3]=%s" % (responseFromSmappee[2]))

                self.generalLogger.error(
                    u"StandardError detected in 'validateSmappeResponse'. Line '%s' has error='%s'" % (
                        sys.exc_traceback.tb_lineno, e))
                self.generalLogger.error(u"Response from Smappee was:'%s'" % (str(responseFromSmappee)))

            # Decode response
            decoded = json.loads(responseFromSmappee)

            # Ensure decoded is a list  
            if type(decoded) != 'list':
                decoded = decoded

            return True, decoded

        except StandardError, e:
            self.generalLogger.error(u"StandardError detected in 'validateSmappeResponse'. Line '%s' has error='%s'" % (
                sys.exc_traceback.tb_lineno, e))
            self.generalLogger.error(u"Response from Smappee was:'%s'" % (str(responseFromSmappee)))
            return False, ''

    def handleGetEvents(self, responseLocationId, decodedSmappeeResponse):
        self.methodTracer.threaddebug(u"CLASS: handleGetEvents")

        try:
            for smappeeApplianceDev in indigo.devices.iter("self"):
                if smappeeApplianceDev.deviceTypeId == "smappeeAppliance":
                    smappeeApplianceDev.updateStateOnServer("smappeeApplianceEventStatus", "NONE", uiValue="No Events")
                    if float(indigo.server.apiVersion) >= 1.18:
                        smappeeApplianceDev.updateStateImageOnServer(indigo.kStateImageSel.EnergyMeterOff)

            for decoding in sorted(decodedSmappeeResponse, key=lambda k: k['timestamp']):
                decoding = self.convertUnicode(decoding)
                eventTimestamp = float(decoding['timestamp'])
                activePower = decoding['activePower']
                if activePower > 0.0:
                    applianceStatus = 'ON'
                else:
                    applianceStatus = 'OFF'
                applianceId = decoding['applianceId']
                smappeeType = 'A'
                applianceId = str("%s%s" % (str(smappeeType), str("00%s" % applianceId)[-3:]))

                if applianceId in self.globals['smappeeServiceLocationIdToDevId'][responseLocationId]['applianceIds']:
                    if self.globals['smappeeServiceLocationIdToDevId'][responseLocationId]['applianceIds'][applianceId][
                            'devId'] != 0:

                        smappeeApplianceDevId = \
                            self.globals['smappeeServiceLocationIdToDevId'][responseLocationId]['applianceIds'][
                                applianceId]['devId']
                        showCurrentPower = smappeeApplianceDev.pluginProps['SupportsEnergyMeterCurPower']
                        if showCurrentPower:
                            smappeeApplianceDev.updateStateOnServer("curEnergyLevel", 0.0, uiValue="0 kWh")

                        smappeeApplianceDev = indigo.devices[smappeeApplianceDevId]

                        # Check if timestamp to be processed and if not bale out!
                        if eventTimestamp > float(
                                smappeeApplianceDev.states['smappeeApplianceEventLastRecordedTimestamp']):
                            eventTimestampStr = datetime.datetime.fromtimestamp(int(eventTimestamp / 1000)).strftime(
                                '%Y-%b-%d %H:%M:%S')
                            smappeeApplianceDev.updateStateOnServer("smappeeApplianceEventLastRecordedTimestamp",
                                                                    float(eventTimestamp), uiValue=eventTimestampStr)
                            showCurrentPower = smappeeApplianceDev.pluginProps['SupportsEnergyMeterCurPower']
                            showOnOffState = smappeeApplianceDev.pluginProps['showApplianceEventStatus']
                            hideEvents = smappeeApplianceDev.pluginProps['hideApplianceSmappeeEvents']

                            activePowerStr = "%d W" % activePower

                            if showCurrentPower:
                                smappeeApplianceDev.updateStateOnServer("curEnergyLevel", activePower,
                                                                        uiValue=activePowerStr)

                            if showOnOffState:
                                if applianceStatus == 'ON':
                                    smappeeApplianceDev.updateStateOnServer("smappeeApplianceEventStatus", "UP",
                                                                            uiValue=activePowerStr)
                                else:
                                    smappeeApplianceDev.updateStateOnServer("smappeeApplianceEventStatus", "DOWN",
                                                                            uiValue=activePowerStr)

                            if not hideEvents:
                                eventTimestampStr = datetime.datetime.fromtimestamp(
                                    int(eventTimestamp / 1000)).strftime('%H:%M:%S')
                                self.generalLogger.info(
                                    u"recorded Smappee Appliance '%s' event at [%s], reading: %s" % (
                                        smappeeApplianceDev.name, eventTimestampStr, activePowerStr))

                            if float(indigo.server.apiVersion) >= 1.18:
                                smappeeApplianceDev.updateStateImageOnServer(indigo.kStateImageSel.EnergyMeterOn)

        except StandardError, e:
            self.generalLogger.error(u"StandardError detected in 'handleGetEvents'. Line '%s' has error='%s'" % (
                sys.exc_traceback.tb_lineno, e))
            self.generalLogger.error(u"Decoded response from Smappee was:'%s'" % decodedSmappeeResponse)

    def handleInitialise(self, commandSentToSmappee, responseLocationId, decodedSmappeeResponse):
        self.methodTracer.threaddebug(u"CLASS: handleInitialise")

        try:
            for decoding in decodedSmappeeResponse:
                for key, value in decoding.iteritems():

                    if key == 'access_token':
                        self.globals['config']['accessToken'] = value
                        self.generalLogger.info(u"Authenticated with Smappee but initialisation still in progress ...")
                        # Now request Location info (but only if Initialise i.e. not if Refresh_Token)
                        if commandSentToSmappee == 'INITIALISE':
                            self.globals['queues']['sendToSmappee'].put(['GET_SERVICE_LOCATIONS'])
                    elif key == 'expires_in':
                        self.globals['config']['tokenExpiresIn'] = int(value)
                        preAdjustedTokenExpiresDateTimeUtc = time.mktime((indigo.server.getTime() + datetime.timedelta(seconds=self.globals['config']['tokenExpiresIn'])).timetuple())
                        self.globals['config']['tokenExpiresDateTimeUtc'] = preAdjustedTokenExpiresDateTimeUtc - float(
                            self.globals['polling'][
                                'seconds'] + 300)  # Adjust token expiry time taking account of polling time + 5 minute safety margin
                        self.generalLogger.debug(u"tokenExpiresDateTimeUtc [T] : Was [%s], is now [%s]" % (
                            preAdjustedTokenExpiresDateTimeUtc, self.globals['config']['tokenExpiresDateTimeUtc']))
                    elif key == 'refresh_token':
                        self.globals['config']['refreshToken'] = value
                    elif key == 'error':
                        self.generalLogger.error(u"SMAPPEE ERROR DETECTED [%s]: %s" % (commandSentToSmappee, value))
                    else:
                        pass  # Unknown key/value pair
                        self.generalLogger.debug(u"Unhandled key/value pair : K=[%s], V=[%s]" % (key, value))

        except StandardError, e:
            self.generalLogger.error(u"StandardError detected in 'handleInitialise'. Line '%s' has error='%s'" % (
                sys.exc_traceback.tb_lineno, e))
            self.generalLogger.error(u"Decoded response from Smappee was:'%s'" % decodedSmappeeResponse)

    def handleGetServiceLocations(self, responseLocationId, decodedSmappeeResponse):
        self.methodTracer.threaddebug(u"CLASS: handleGetServiceLocations")

        try:
            for decoding in decodedSmappeeResponse:
                for key, value in decoding.iteritems():
                    if key == 'appName':
                        self.globals['config']['appName'] = str(value)
                    elif key == 'serviceLocations':
                        for self.serviceLocationItem in value:
                            self.serviceLocationId = ""
                            self.serviceLocationName = ""
                            for key2, value2 in self.serviceLocationItem.iteritems():
                                self.generalLogger.debug(
                                    u"handleSmappeeResponse [H][SERVICELOCATION] -  [%s : %s]" % (key2, value2))
                                if key2 == 'serviceLocationId':
                                    self.serviceLocationId = str(value2)
                                elif key2 == 'name':
                                    self.serviceLocationName = str(value2)
                                else:
                                    pass  # Unknown key/value pair
                            if self.serviceLocationId != "":
                                if self.serviceLocationId in self.globals['smappeeServiceLocationIdToDevId']:
                                    self.globals['smappeeServiceLocationIdToDevId'][self.serviceLocationId][
                                        'name'] = self.serviceLocationName
                                    if 'electricityId' not in self.globals['smappeeServiceLocationIdToDevId'][
                                            self.serviceLocationId]:
                                        self.globals['smappeeServiceLocationIdToDevId'][self.serviceLocationId][
                                            'electricityId'] = int(0)
                                    if 'electricityNetId' not in self.globals['smappeeServiceLocationIdToDevId'][
                                            self.serviceLocationId]:
                                        self.globals['smappeeServiceLocationIdToDevId'][self.serviceLocationId][
                                            'electricityNetId'] = int(0)
                                    if 'electricitySavedId' not in self.globals['smappeeServiceLocationIdToDevId'][
                                            self.serviceLocationId]:
                                        self.globals['smappeeServiceLocationIdToDevId'][self.serviceLocationId][
                                            'electricitySavedId'] = int(0)
                                    if 'solarId' not in self.globals['smappeeServiceLocationIdToDevId'][
                                            self.serviceLocationId]:
                                        self.globals['smappeeServiceLocationIdToDevId'][self.serviceLocationId][
                                            'solarId'] = int(0)
                                    if 'solarUsedId' not in self.globals['smappeeServiceLocationIdToDevId'][
                                            self.serviceLocationId]:
                                        self.globals['smappeeServiceLocationIdToDevId'][self.serviceLocationId][
                                            'solarUsedId'] = int(0)
                                    if 'solarExportedId' not in self.globals['smappeeServiceLocationIdToDevId'][
                                            self.serviceLocationId]:
                                        self.globals['smappeeServiceLocationIdToDevId'][self.serviceLocationId][
                                            'solarExportedId'] = int(0)
                                    if 'sensorIds' not in self.globals['smappeeServiceLocationIdToDevId'][
                                            self.serviceLocationId]:
                                        self.globals['smappeeServiceLocationIdToDevId'][self.serviceLocationId][
                                            'sensorIds'] = {}
                                    if 'applianceIds' not in self.globals['smappeeServiceLocationIdToDevId'][
                                            self.serviceLocationId]:
                                        self.globals['smappeeServiceLocationIdToDevId'][self.serviceLocationId][
                                            'applianceIds'] = {}
                                    if 'actuatorIds' not in self.globals['smappeeServiceLocationIdToDevId'][
                                            self.serviceLocationId]:
                                        self.globals['smappeeServiceLocationIdToDevId'][self.serviceLocationId][
                                            'actuatorIds'] = {}
                                else:
                                    self.globals['smappeeServiceLocationIdToDevId'][self.serviceLocationId] = {}
                                    self.globals['smappeeServiceLocationIdToDevId'][self.serviceLocationId][
                                        'name'] = self.serviceLocationName
                                    self.globals['smappeeServiceLocationIdToDevId'][self.serviceLocationId][
                                        'electricityId'] = int(0)
                                    self.globals['smappeeServiceLocationIdToDevId'][self.serviceLocationId][
                                        'electricityNetId'] = int(0)
                                    self.globals['smappeeServiceLocationIdToDevId'][self.serviceLocationId][
                                        'electricitySavedId'] = int(0)
                                    self.globals['smappeeServiceLocationIdToDevId'][self.serviceLocationId][
                                        'solarId'] = int(0)
                                    self.globals['smappeeServiceLocationIdToDevId'][self.serviceLocationId][
                                        'solarUsedId'] = int(0)
                                    self.globals['smappeeServiceLocationIdToDevId'][self.serviceLocationId][
                                        'solarExportedId'] = int(0)
                                    self.globals['smappeeServiceLocationIdToDevId'][self.serviceLocationId][
                                        'sensorIds'] = {}
                                    self.globals['smappeeServiceLocationIdToDevId'][self.serviceLocationId][
                                        'applianceIds'] = {}
                                    self.globals['smappeeServiceLocationIdToDevId'][self.serviceLocationId][
                                        'actuatorIds'] = {}

                                self.generalLogger.debug(u"handleSmappeeResponse [HH][SERVICELOCATION]: %s" % (
                                    self.globals['smappeeServiceLocationIdToDevId'][self.serviceLocationId]))

                        for self.serviceLocationId, self.serviceLocationDetails in self.globals[
                                'smappeeServiceLocationIdToDevId'].iteritems():

                            for smappeeDev in indigo.devices.iter("self"):

                                if smappeeDev.deviceTypeId == "smappeeElectricity":
                                    self.generalLogger.debug(
                                        u"handleSmappeeResponse [J] Checking new Smappee Service Location Id: [%s] against known Smappee Electricity Device Id [%s]" % (
                                            type(self.serviceLocationId), type(smappeeDev.address)))
                                    if smappeeDev.pluginProps['serviceLocationId'] == self.serviceLocationId:
                                        if self.serviceLocationDetails['electricityId'] == 0:
                                            self.globals['smappeeServiceLocationIdToDevId'][self.serviceLocationId][
                                                'electricityId'] = smappeeDev.id
                                        else:
                                            if self.serviceLocationDetails['electricityId'] != smappeeDev.id:
                                                self.generalLogger.error(
                                                    u"DUPLICATE SMAPPEE ELECTRICITY DEVICE / LOCATION. L=[%s], D1=[%s], D2=[%s]" % (
                                                        self.serviceLocationId,
                                                        self.globals['smappeeServiceLocationIdToDevId'][
                                                            self.serviceLocationId]['electricityId'], smappeeDev.id))

                                elif smappeeDev.deviceTypeId == "smappeeElectricityNet":
                                    self.generalLogger.debug(
                                        u"handleSmappeeResponse [J] Checking new Smappee Service Location Id: [%s] against known Smappee Electricity Net Device Id [%s]" % (
                                            type(self.serviceLocationId), type(smappeeDev.address)))
                                    if smappeeDev.pluginProps['serviceLocationId'] == self.serviceLocationId:
                                        if self.serviceLocationDetails['electricityNetId'] == 0:
                                            self.globals['smappeeServiceLocationIdToDevId'][self.serviceLocationId][
                                                'electricityNetId'] = smappeeDev.id
                                        else:
                                            if self.serviceLocationDetails['electricityNetId'] != smappeeDev.id:
                                                self.generalLogger.error(
                                                    u"DUPLICATE SMAPPEE ELECTRICITY NET DEVICE / LOCATION. L=[%s], D1=[%s], D2=[%s]" % (
                                                        self.serviceLocationId,
                                                        self.globals['smappeeServiceLocationIdToDevId'][
                                                            self.serviceLocationId]['electricityNetId'], smappeeDev.id))

                                elif smappeeDev.deviceTypeId == "smappeeElectricitySaved":
                                    self.generalLogger.debug(
                                        u"handleSmappeeResponse [J] Checking new Smappee Service Location Id: [%s] against known Smappee Electricity Saved Device Id [%s]" % (
                                            type(self.serviceLocationId), type(smappeeDev.address)))
                                    if smappeeDev.pluginProps['serviceLocationId'] == self.serviceLocationId:
                                        if self.serviceLocationDetails['electricitySavedId'] == 0:
                                            self.globals['smappeeServiceLocationIdToDevId'][self.serviceLocationId][
                                                'electricitySavedId'] = smappeeDev.id
                                        else:
                                            if self.serviceLocationDetails['electricitySavedId'] != smappeeDev.id:
                                                self.generalLogger.error(
                                                    u"DUPLICATE SMAPPEE ELECTRICITY SAVED DEVICE / LOCATION. L=[%s], D1=[%s], D2=[%s]" % (
                                                        self.serviceLocationId,
                                                        self.globals['smappeeServiceLocationIdToDevId'][
                                                            self.serviceLocationId]['electricitySavedId'],
                                                        smappeeDev.id))

                                elif smappeeDev.deviceTypeId == "smappeeSolar":
                                    self.generalLogger.debug(
                                        u"handleSmappeeResponse [J] Checking new Smappee Service Location Id: [%s] against known Smappee Solar Device Id [%s]" % (
                                            type(self.serviceLocationId), type(smappeeDev.address)))
                                    if smappeeDev.pluginProps['serviceLocationId'] == self.serviceLocationId:
                                        if self.serviceLocationDetails['solarId'] == 0:
                                            self.globals['smappeeServiceLocationIdToDevId'][self.serviceLocationId][
                                                'solarId'] = smappeeDev.id
                                        else:
                                            if self.serviceLocationDetails['solarId'] != smappeeDev.id:
                                                self.generalLogger.error(
                                                    u"DUPLICATE SMAPPEE SOLAR DEVICE / LOCATION. L=[%s], D1=[%s], D2=[%s]" % (
                                                        self.serviceLocationId,
                                                        self.globals['smappeeServiceLocationIdToDevId'][
                                                            self.serviceLocationId]['solarId'], smappeeDev.id))

                                elif smappeeDev.deviceTypeId == "smappeeSolarUsed":
                                    self.generalLogger.debug(
                                        u"handleSmappeeResponse [J] Checking new Smappee Service Location Id: [%s] against known Smappee Solar Used Device Id [%s]" % (
                                            type(self.serviceLocationId), type(smappeeDev.address)))
                                    if smappeeDev.pluginProps['serviceLocationId'] == self.serviceLocationId:
                                        if self.serviceLocationDetails['solarUsedId'] == 0:
                                            self.globals['smappeeServiceLocationIdToDevId'][self.serviceLocationId][
                                                'solarUsedId'] = smappeeDev.id
                                        else:
                                            if self.serviceLocationDetails['solarUsedId'] != smappeeDev.id:
                                                self.generalLogger.error(
                                                    u"DUPLICATE SMAPPEE SOLAR USED DEVICE / LOCATION. L=[%s], D1=[%s], D2=[%s]" % (
                                                        self.serviceLocationId,
                                                        self.globals['smappeeServiceLocationIdToDevId'][
                                                            self.serviceLocationId]['solarUsedId'], smappeeDev.id))

                                elif smappeeDev.deviceTypeId == "smappeeSolarExported":
                                    self.generalLogger.debug(
                                        u"handleSmappeeResponse [J] Checking new Smappee Service Location Id: [%s] against known Smappee Solar Exported Device Id [%s]" % (
                                            type(self.serviceLocationId), type(smappeeDev.address)))
                                    if smappeeDev.pluginProps['serviceLocationId'] == self.serviceLocationId:
                                        if self.serviceLocationDetails['solarExportedId'] == 0:
                                            self.globals['smappeeServiceLocationIdToDevId'][self.serviceLocationId][
                                                'solarExportedId'] = smappeeDev.id
                                        else:
                                            if self.serviceLocationDetails['solarExportedId'] != smappeeDev.id:
                                                self.generalLogger.error(
                                                    u"DUPLICATE SMAPPEE SOLAR EXPORTED DEVICE / LOCATION. L=[%s], D1=[%s], D2=[%s]" % (
                                                        self.serviceLocationId,
                                                        self.globals['smappeeServiceLocationIdToDevId'][
                                                            self.serviceLocationId]['solarExportedId'], smappeeDev.id))

                                elif smappeeDev.deviceTypeId == "smappeeSensor":
                                    self.generalLogger.debug(
                                        u"handleSmappeeResponse [J] Checking new Smappee Service Location Id: [%s] against known Smappee Sensor Device Id [%s]" % (
                                            type(self.serviceLocationId), type(smappeeDev.address)))
                                    if smappeeDev.pluginProps['serviceLocationId'] == self.serviceLocationId:
                                        if self.serviceLocationDetails['sensorIds'][smappeeDev.address] == 0:
                                            self.globals['smappeeServiceLocationIdToDevId'][self.serviceLocationId][
                                                'sensorIds'][smappeeDev.address] = {'name': smappeeDev.name,
                                                                                    'devId': smappeeDev.id}
                                    #    else:
                                    #        if self.serviceLocationDetails['sensorIds'] != smappeeDev.id:
                                    #           self.generalLogger.error(u"DUPLICATE SMAPPEE SENSOR DEVICE / LOCATION. L=[%s], D1=[%s], D2=[%s]" % (self.serviceLocationId, self.globals['smappeeServiceLocationIdToDevId'][self.serviceLocationId]['electricityId'], smappeeDev.id))

                                elif smappeeDev.deviceTypeId == "smappeeAppliance":
                                    self.generalLogger.debug(
                                        u"handleSmappeeResponse [J] Checking new Smappee Service Location Id: [%s] against known Smappee Appliance Device Id [%s]" % (
                                            type(self.serviceLocationId), type(smappeeDev.address)))
                                    if smappeeDev.pluginProps['serviceLocationId'] == self.serviceLocationId:
                                        if self.serviceLocationDetails['applianceIds'][smappeeDev.address] == 0:
                                            self.globals['smappeeServiceLocationIdToDevId'][self.serviceLocationId][
                                                'applianceIds'][smappeeDev.address] = {'name': smappeeDev.name,
                                                                                       'devId': smappeeDev.id}
                                    #    else:
                                    #        if self.serviceLocationDetails['electricity'] != smappeeDev.id:
                                    #           self.generalLogger.error(u"DUPLICATE SMAPPEE APPLIANCE DEVICE / LOCATION. L=[%s], D1=[%s], D2=[%s]" % (self.serviceLocationId, self.globals['smappeeServiceLocationIdToDevId'][self.serviceLocationId]['electricityId'], smappeeDev.id))

                                elif smappeeDev.deviceTypeId == "smappeeActuator":
                                    self.generalLogger.debug(
                                        u"handleSmappeeResponse [J] Checking new Smappee Service Location Id: [%s] against known Smappee Actuator Device Id [%s]" % (
                                            type(self.serviceLocationId), type(smappeeDev.address)))
                                    if smappeeDev.pluginProps['serviceLocationId'] == self.serviceLocationId:
                                        if self.serviceLocationDetails['actuatorIds'][smappeeDev.address] == 0:
                                            self.globals['smappeeServiceLocationIdToDevId'][self.serviceLocationId][
                                                'actuatorIds'][smappeeDev.address] = {'name': smappeeDev.name,
                                                                                      'devId': smappeeDev.id}
                                    #    else:
                                    #        if self.serviceLocationDetails['electricity'] != smappeeDev.id:
                                    #            self.generalLogger.error(u"DUPLICATE SMAPPEE ACTUATOR DEVICE / LOCATION. L=[%s], D1=[%s], D2=[%s]" % (self.serviceLocationId, self.globals['smappeeServiceLocationIdToDevId'][self.serviceLocationId]['electricityId'], smappeeDev.id))

                            self.generalLogger.debug(u"handleSmappeeResponse [HH][SERVICELOCATION DETAILS]: %s = %s" % (
                                self.serviceLocationId, self.serviceLocationDetails))

                            self.globals['queues']['sendToSmappee'].put(['GET_SERVICE_LOCATION_INFO', self.serviceLocationId])

                        if not self.globals['pluginInitialised']:
                            self.generalLogger.debug(
                                u"handleSmappeeResponse [HH][SERVICELOCATION plugin initialised]: %s " % (
                                    self.globals['pluginInitialised']))
                            self.globals['pluginInitialised'] = True
                            self.generalLogger.info(u"Initialisation completed.")

                            for serviceLocationId, serviceLocationDetails in self.globals['smappeeServiceLocationIdToDevId'].iteritems():
                                self.globals['queues']['sendToSmappee'].put(["GET_CONSUMPTION", str(serviceLocationId)])
                                self.globals['queues']['sendToSmappee'].put(["GET_EVENTS", str(serviceLocationId)])
                                self.globals['queues']['sendToSmappee'].put(["GET_SENSOR_CONSUMPTION", str(serviceLocationId)])

                        else:
                            self.generalLogger.debug(
                                u"handleSmappeeResponse [HH][SERVICELOCATION plugin already initialised]: %s " % (
                                    self.globals['pluginInitialised']))

                        self.generalLogger.debug(
                            u"handleSmappeeResponse [HH][SERVICELOCATION pluginInitialised: FINAL]: %s " % (
                                self.globals['pluginInitialised']))

                    elif key == 'error':
                        self.generalLogger.error(u"SMAPPEE ERROR DETECTED [%s]: %s" % (decodedSmappeeResponse, value))
                    else:
                        # Unknown key/value pair
                        self.generalLogger.debug(u"Unhandled key/value pair : K=[%s], V=[%s]" % (key, value))

        except StandardError, e:
            self.generalLogger.error(
                u"StandardError detected in 'handleGetServiceLocations'. Line '%s' has error='%s'" % (
                    sys.exc_traceback.tb_lineno, e))
            self.generalLogger.error(u"Decoded response from Smappee was:'%s'" % decodedSmappeeResponse)

    def handleGetServiceLocationInfo(self, responseLocationId, decodedSmappeeResponse):
        self.methodTracer.threaddebug(u"CLASS: handleGetServiceLocationInfo")

        try:
            for decoding in decodedSmappeeResponse:
                for key, value in decoding.iteritems():
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
                            for key2, value2 in self.sensorItem.iteritems():
                                self.generalLogger.debug(
                                    u"handleSmappeeResponse [F][SENSOR] -  [%s : %s]" % (key2, value2))
                                if key2 == 'id':
                                    smappeeType = 'GW'  # Sensor for Gas Water
                                    self.sensorId = str("%s%s" % (str(smappeeType), str("00%s" % value2)[-2:]))
                                elif key2 == 'name':
                                    self.sensorName = str(value2)
                                else:
                                    pass  # Unknown key/value pair
                            self.generalLogger.debug(
                                u"handleSmappeeResponse [FF][SENSOR] - [%s]-[%s]" % (self.sensorId, self.sensorName))

                            if self.sensorId != "":
                                # At this point we have detected a Smappee Sensor Device
                                self.globals['config']['supportsSensor'] = True

                                # Two Indigo devices can be created for each Smappee Sensor to represent the two channels (inputs) which could be measuring both Gas and Water
                                # Define a common function (below) to add an Indigo device
                                def createSensor(sensorIdModifier):
                                    if self.sensorName == "":
                                        sensorName = str("[%s-%s] 'Unlabeled'" % (self.sensorId, sensorIdModifier))
                                    else:
                                        sensorName = str("[%s-%s] %s" % (
                                            self.sensorId, sensorIdModifier, str(self.sensorName).strip()))

                                    sensorId = self.sensorId + '-' + sensorIdModifier

                                    self.generalLogger.debug(
                                        u"handleSmappeeResponse [FF-A][SENSOR] - [%s]-[%s]" % (sensorId, sensorName))

                                    if sensorId in self.globals['smappeeServiceLocationIdToDevId'][responseLocationId][
                                            'sensorIds']:
                                        self.generalLogger.debug(u"handleSmappeeResponse [FF-B][SENSOR] - [%s]-[%s]" % (
                                            sensorId, sensorName))
                                        if self.globals['smappeeServiceLocationIdToDevId'][responseLocationId][
                                                'sensorIds'][sensorId]['devId'] != 0:
                                            try:
                                                self.generalLogger.debug(
                                                    u"handleSmappeeResponse [FF-C][SENSOR] - [%s]-[%s]" % (
                                                        sensorId, sensorName))
                                                #  Can be either Gas or Water
                                                smappeeSensorDev = indigo.devices[
                                                    self.globals['smappeeServiceLocationIdToDevId'][responseLocationId][
                                                        'sensorIds'][sensorId]['devId']]
                                                if not smappeeSensorDev.states['smappeeSensorOnline']:
                                                    smappeeSensorDev.updateStateOnServer("smappeeSensorOnline", True,
                                                                                         uiValue='online')
                                            except:
                                                pass
                                    else:
                                        #  Can be either Gas or Water
                                        self.setSmappeeServiceLocationIdToDevId('ADD_UPDATE', 'smappeeSensor',
                                                                                responseLocationId, 0, sensorId,
                                                                                sensorName)
                                        self.generalLogger.debug(u"handleSmappeeResponse [FF-D][SENSOR] - [%s]-[%s]" % (
                                            sensorId, sensorName))

                                # Now add the devices
                                createSensor('A')
                                createSensor('B')

                    elif key == 'appliances':
                        for self.applianceItem in value:
                            self.applianceName = ""
                            self.applianceId = ""
                            for key2, value2 in self.applianceItem.iteritems():
                                self.generalLogger.debug(
                                    u"handleSmappeeResponse [F][APPLIANCE] -  [%s : %s]" % (key2, value2))
                                if key2 == 'id':
                                    smappeeType = 'A'  # Appliance
                                    self.applianceId = str("%s%s" % (str(smappeeType), str("00%s" % value2)[-3:]))
                                elif key2 == 'name':
                                    self.applianceName = str(value2)
                                elif key2 == 'type':
                                    self.applianceType = value2
                                else:
                                    pass  # Unknown key/value pair
                            self.generalLogger.debug(u"handleSmappeeResponse [FF][APPLIANCE] - [%s]-[%s]-[%s]" % (
                                self.applianceId, self.applianceName, self.applianceType))

                            if self.applianceId != "":
                                if self.applianceName == "":
                                    self.applianceName = str("[%s] 'Unlabeled'" % self.applianceId)
                                else:
                                    self.applianceName = str(
                                        "[%s] %s" % (self.applianceId, str(self.applianceName).strip()))

                                if self.applianceId in \
                                        self.globals['smappeeServiceLocationIdToDevId'][responseLocationId][
                                            'applianceIds']:
                                    if \
                                            self.globals['smappeeServiceLocationIdToDevId'][responseLocationId][
                                                'applianceIds'][
                                                self.applianceId]['devId'] != 0:
                                        try:
                                            smappeeApplianceDev = indigo.devices[
                                                self.globals['smappeeServiceLocationIdToDevId'][responseLocationId][
                                                    'applianceIds'][self.applianceId]['devId']]
                                            if not smappeeApplianceDev.states['smappeeApplianceOnline']:
                                                smappeeApplianceDev.updateStateOnServer("smappeeApplianceOnline", True,
                                                                                        uiValue='online')
                                        except:
                                            pass
                                else:
                                    self.setSmappeeServiceLocationIdToDevId('ADD_UPDATE', 'smappeeAppliance',
                                                                            responseLocationId, 0, self.applianceId,
                                                                            self.applianceName)

                    elif key == 'actuators':
                        for self.actuatorItem in value:
                            self.actuatorName = ""
                            self.actuatorId = ""
                            for key2, value2 in self.actuatorItem.iteritems():
                                self.generalLogger.debug(
                                    u"handleSmappeeResponse [F2][ACTUATOR] -  [%s : %s]" % (key2, value2))
                                if key2 == 'id':
                                    smappeeType = 'P'  # Plug
                                    self.actuatorId = str("%s%s" % (str(smappeeType), str("00%s" % value2)[-3:]))
                                elif key2 == 'name':
                                    self.actuatorName = str(value2)
                                else:
                                    pass  # Unknown key/value pair
                            self.generalLogger.debug(u"handleSmappeeResponse [F2F][ACTUATOR] - [%s]-[%s]" % (
                                self.actuatorId, self.actuatorName))

                            if self.actuatorId != "":
                                if self.actuatorName == "":
                                    self.actuatorName = str("[%s] 'Unlabeled'" % self.actuatorId)
                                else:
                                    self.actuatorName = str(
                                        "[%s] %s" % (self.actuatorId, str(self.actuatorName).strip()))

                                if self.actuatorId in \
                                        self.globals['smappeeServiceLocationIdToDevId'][responseLocationId][
                                            'actuatorIds']:
                                    if \
                                            self.globals['smappeeServiceLocationIdToDevId'][responseLocationId][
                                                'actuatorIds'][
                                                self.actuatorId]['devId'] != 0:
                                        try:
                                            smappeeActuatorDev = indigo.devices[
                                                self.globals['smappeeServiceLocationIdToDevId'][responseLocationId][
                                                    'actuatorIds'][self.actuatorId]['devId']]
                                            if not smappeeActuatorDev.states['smappeeActuatorOnline']:
                                                smappeeActuatorDev.updateStateOnServer("smappeeActuatorOnline", True,
                                                                                       uiValue='online')
                                            # self.generalLogger.debug(u"handleSmappeeResponse [J] Checking new Smappee Appliance Id: [%s] against known Smappee Appliance Id [%s]" % (self.applianceId, smappeeApplianceDev.address))
                                        except:
                                            pass
                                else:
                                    self.setSmappeeServiceLocationIdToDevId('ADD_UPDATE', 'smappeeActuator',
                                                                            responseLocationId, 0, self.actuatorId,
                                                                            self.actuatorName)

                    elif key == 'error':
                        self.generalLogger.error(u"SMAPPEE ERROR DETECTED [%s]: %s" % (decodedSmappeeResponse, value))
                    else:
                        pass  # Unknown key/value pair
                        self.generalLogger.debug(u"Unhandled key/value pair : K=[%s], V=[%s]" % (key, value))

        except StandardError, e:
            self.generalLogger.error(
                u"StandardError detected in 'handleGetServiceLocationInfo'. Line '%s' has error='%s'" % (
                    sys.exc_traceback.tb_lineno, e))
            self.generalLogger.error(u"Decoded response from Smappee was:'%s'" % decodedSmappeeResponse)

    def handleGetConsumption(self, commandSentToSmappee, responseLocationId, decodedSmappeeResponse):
        self.methodTracer.threaddebug(u"CLASS: handleGetConsumption")

        try:
            for decoding in decodedSmappeeResponse:
                for key, value in decoding.iteritems():

                    if key == 'serviceLocationId':
                        pass
                    elif key == 'consumptions':

                        if self.globals['config']['supportsElectricity']:
                            devElectricity = indigo.devices[
                                self.globals['smappeeServiceLocationIdToDevId'][responseLocationId]['electricityId']]
                            self.lastReadingElectricityUtc = self.globals['smappees'][devElectricity.id][
                                'lastReadingElectricityUtc']
                            self.generalLogger.debug(
                                u"handleSmappeeResponse [LRU-ELECTRICITY]: %s" % self.lastReadingElectricityUtc)

                            if not devElectricity.states['smappeeElectricityOnline']:
                                devElectricity.updateStateOnServer("smappeeElectricityOnline", True, uiValue='online')

                        if self.globals['config']['supportsElectricityNet']:
                            devElectricityNet = indigo.devices[
                                self.globals['smappeeServiceLocationIdToDevId'][responseLocationId]['electricityNetId']]
                            self.lastReadingElectricityNetUtc = self.globals['smappees'][devElectricityNet.id][
                                'lastReadingElectricityNetUtc']
                            self.generalLogger.debug(u"handleSmappeeResponse [LRU-NET-ELECTRICITY]: %s" % (
                                self.lastReadingElectricityNetUtc))

                            if not devElectricityNet.states['smappeeElectricityNetOnline']:
                                devElectricityNet.updateStateOnServer("smappeeElectricityNetOnline", True,
                                                                      uiValue='online')

                        if self.globals['config']['supportsElectricitySaved']:
                            devElectricitySaved = indigo.devices[
                                self.globals['smappeeServiceLocationIdToDevId'][responseLocationId][
                                    'electricitySavedId']]
                            self.lastReadingElectricitySavedUtc = self.globals['smappees'][devElectricitySaved.id][
                                'lastReadingElectricitySavedUtc']
                            self.generalLogger.debug(u"handleSmappeeResponse [LRU-SAVED-ELECTRICITY]: %s" % (
                                self.lastReadingElectricitySavedUtc))

                            if not devElectricitySaved.states['smappeeElectricitySavedOnline']:
                                devElectricitySaved.updateStateOnServer("smappeeElectricitySavedOnline", True,
                                                                        uiValue='online')

                        if self.globals['config']['supportsSolar']:
                            devSolar = indigo.devices[
                                self.globals['smappeeServiceLocationIdToDevId'][responseLocationId]['solarId']]
                            self.lastReadingSolarUtc = self.globals['smappees'][devSolar.id]['lastReadingSolarUtc']
                            self.generalLogger.debug(
                                u"handleSmappeeResponse [LRU-SOLAR]: %s" % self.lastReadingSolarUtc)

                            if not devSolar.states['smappeeSolarOnline']:
                                devSolar.updateStateOnServer("smappeeSolarOnline", True, uiValue='online')

                        if self.globals['config']['supportsSolarUsed']:
                            devSolarUsed = indigo.devices[
                                self.globals['smappeeServiceLocationIdToDevId'][responseLocationId]['solarUsedId']]
                            self.lastReadingSolarUsedUtc = self.globals['smappees'][devSolarUsed.id][
                                'lastReadingSolarUsedUtc']
                            self.generalLogger.debug(
                                u"handleSmappeeResponse [LRU-SOLAR-USED]: %s" % self.lastReadingSolarUsedUtc)

                            if not devSolarUsed.states['smappeeSolarUsedOnline']:
                                devSolarUsed.updateStateOnServer("smappeeSolarUsedOnline", True, uiValue='online')

                        if self.globals['config']['supportsSolarExported']:
                            devSolarExported = indigo.devices[
                                self.globals['smappeeServiceLocationIdToDevId'][responseLocationId]['solarExportedId']]
                            self.lastReadingSolarExportedUtc = self.globals['smappees'][devSolarExported.id][
                                'lastReadingSolarExportedUtc']
                            self.generalLogger.debug(
                                u"handleSmappeeResponse [LRU-SOLAR-EXPORTED]: %s" % self.lastReadingSolarExportedUtc)

                            if not devSolarExported.states['smappeeSolarExportedOnline']:
                                devSolarExported.updateStateOnServer("smappeeSolarExportedOnline", True,
                                                                     uiValue='online')

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

                        if self.globals['SQL']['enabled']:
                            try:
                                self.globals['SQL']['connection'] = sql3.connect(self.globals['SQL']['db'])
                                self.globals['SQL']['cursor'] = self.globals['SQL']['connection'].cursor()
                            except sql3.Error, e:
                                if self.globals['SQL']['connection']:
                                    self.globals['SQL']['connection'].rollback()
                                self.generalLogger.error(
                                    u"SMAPPEE ERROR DETECTED WITH SQL CONNECTION: %s" % (e.args[0]))

                                self.globals['SQL']['enabled'] = False  # Disable SQL processing

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

                            for key2, value2 in self.readingItem.iteritems():
                                if key2 == 'timestamp':
                                    self.timestampDetected = True
                                    self.timestampUtc = value2
                                    self.timestampUtcLast = value2
                                elif key2 == 'consumption':
                                    self.electricityDetected = True
                                    self.electricity = value2
                                elif key2 == 'solar':
                                    self.solarDetected = True
                                    self.solar = value2
                                elif key2 == 'alwaysOn':
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
                                    ts = datetime.datetime.fromtimestamp(int(int(self.timestampUtc) / 1000)).strftime(
                                        '%Y-%m-%d %H:%M:%S')
                                    self.generalLogger.debug(
                                        u"ELECTRICITY/SOLAR: DateTime=%s, Electricity=%s, Net=%s, Saved=%s, Solar=%s, Solar Used=%s, Solar Exported=%s" % (
                                            ts, self.electricity, self.electricityNet, self.electricitySaved,
                                            self.solar,
                                            self.solarUsed, self.solarExported))
                                else:
                                    self.generalLogger.debug(
                                        u"ELECTRICITY/SOLAR: DateTime=NOT DETECTED, Electricity=%s, Net=%s, Saved=%s, Solar=%s, Solar Used=%s, Solar Exported=%s" % (
                                            self.electricity, self.electricityNet, self.electricitySaved, self.solar,
                                            self.solarUsed, self.solarExported))

                            if self.timestampDetected:
                                if self.globals['config']['supportsElectricity']:
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

                                if self.globals['config']['supportsElectricity'] and self.globals['config'][
                                        'supportsElectricityNet'] and self.globals['config']['supportsSolar']:
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

                                    self.generalLogger.debug(
                                        u"handleSmappeeResponse [FF][ELECTRICITY NET] - LRUTC[%s]=[%s], TSUTC[%s]=[%s], Net[%s]=[%s]" % (
                                            type(self.lastReadingElectricityNetUtc), self.lastReadingElectricityNetUtc,
                                            type(self.timestampUtc), self.timestampUtc, type(self.electricityNet),
                                            self.electricityNet))

                                if self.globals['config']['supportsElectricity'] and self.globals['config'][
                                        'supportsElectricitySaved'] and self.globals['config']['supportsSolar']:
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

                                    self.generalLogger.debug(
                                        u"handleSmappeeResponse [FF][ELECTRICITY SAVED] - LRUTC[%s]=[%s], TSUTC[%s]=[%s], Saved[%s]=[%s]" % (
                                            type(self.lastReadingElectricitySavedUtc),
                                            self.lastReadingElectricitySavedUtc,
                                            type(self.timestampUtc), self.timestampUtc, type(self.electricitySaved),
                                            self.electricitySaved))

                                if self.globals['config']['supportsSolar']:
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
                                    # self.generalLogger.debug(u"handleSmappeeResponse [FF][SOLAR] - LRUTC[%s]=[%s], TSUTC[%s]=[%s], S[%s]=[%s]" % (type(self.lastReadingSolarUtc), self.lastReadingSolarUtc, type(self.timestampUtc), self.timestampUtc, type(self.solar), self.solar))

                                if self.globals['config']['supportsElectricity'] and self.globals['config'][
                                        'supportsSolarUsed']:
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

                                    self.generalLogger.debug(
                                        u"handleSmappeeResponse [FF][SOLAR USED] - LRUTC[%s]=[%s], TSUTC[%s]=[%s], Saving[%s]=[%s]" % (
                                            type(self.lastReadingSolarUsedUtc), self.lastReadingSolarUsedUtc,
                                            type(self.timestampUtc), self.timestampUtc, type(self.solarUsed),
                                            self.solarUsed))

                                if self.globals['config']['supportsSolarExported']:
                                    if self.timestampUtc > self.lastReadingSolarExportedUtc:
                                        if self.solarExportedDetected:
                                            self.solarExportedNumberOfValues += 1
                                            self.solarExportedTotal += self.solarExported
                                            self.solarExportedLast = self.solarExported
                                    elif self.timestampUtc == self.lastReadingSolarExportedUtc:
                                        self.solarExportedPrevious = 0.0
                                        if self.solarExportedDetected:
                                            self.solarExportedPrevious = self.solarExported * 12

                                    self.generalLogger.debug(
                                        u"handleSmappeeResponse [FF][SOLAR EXPORTED] - LRUTC[%s]=[%s], TSUTC[%s]=[%s], Saving[%s]=[%s]" % (
                                            type(self.lastReadingSolarExportedUtc), self.lastReadingSolarExportedUtc,
                                            type(self.timestampUtc), self.timestampUtc, type(self.solarExported),
                                            self.solarExported))

                                if self.globals['SQL']['enabled']:

                                    try:
                                        insertSql = 'NO SQL SET-UP YET'
                                        readingTime = str(int(self.timestampUtc / 1000))  # Remove micro seconds
                                        readingYYYYMMDDHHMMSS = datetime.datetime.fromtimestamp(
                                            int(readingTime)).strftime('%Y-%m-%d %H:%M:%S')
                                        readingYYYYMMDD = readingYYYYMMDDHHMMSS[0:10]
                                        readingHHMMSS = readingYYYYMMDDHHMMSS[-8:]
                                        elec = str(int(self.electricity * 10))
                                        elecNet = str(int(self.electricityNet * 10))
                                        elecSaved = str(int(self.electricitySaved * 10))
                                        alwaysOn = str(int(self.alwaysOn * 10))
                                        solar = str(int(self.solar * 10))
                                        solarUsed = str(int(self.solarUsed * 10))
                                        solarExported = str(int(self.solarExported * 10))
                                        insertSql = """
                                            INSERT OR IGNORE INTO readings (reading_time, reading_YYYYMMDD, reading_HHMMSS, elec, elec_net, elec_saved, always_on, solar, solar_used, solar_exported)
                                            VALUES (%s, '%s', '%s', %s, %s, %s, %s, %s, %s, %s);
                                            """ % (
                                            readingTime, readingYYYYMMDD, readingHHMMSS, elec, elecNet, elecSaved,
                                            alwaysOn,
                                            solar, solarUsed, solarExported)
                                        self.globals['SQL']['cursor'].executescript(insertSql)
                                    except sql3.Error, e:
                                        if self.globals['SQL']['connection']:
                                            self.globals['SQL']['connection'].rollback()
                                        self.generalLogger.error(
                                            u"SMAPPEE ERROR DETECTED WITH SQL INSERT: %s, SQL=[%s]" % (
                                                e.args[0], insertSql))
                                        if self.globals['SQL']['connection']:
                                            self.globals['SQL']['connection'].close()

                                        self.globals['SQL']['enabled'] = False  # Disable SQL processing

                        if self.globals['SQL']['enabled']:
                            try:
                                self.globals['SQL']['connection'].commit()
                            except sql3.Error, e:
                                if self.globals['SQL']['connection']:
                                    self.globals['SQL']['connection'].rollback()
                                self.generalLogger.error(u"SMAPPEE ERROR DETECTED WITH SQL COMMIT: %s" % (e.args[0]))

                                self.globals['SQL']['enabled'] = False  # Disable SQL processing
                            finally:
                                if self.globals['SQL']['connection']:
                                    self.globals['SQL']['connection'].close()

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

                        if self.solarNumberOfValues > 0:
                            self.solarExportedMeanAverage = self.solarExportedTotal / self.solarNumberOfValues

                        self.generalLogger.debug(
                            u"READINGS - ELECTRICITY: N=[%s], T=[%s], MEAN=[%s], MIN=[%s], MAX=[%s], L=[%s]"
                            % (self.electricityNumberOfValues, self.electricityTotal, self.electricityMeanAverage,
                               self.electricityMinimum, self.electricityMaximum, self.electricityLast))
                        self.generalLogger.debug(
                            u"READINGS - ELECTRICITY NET: N=[%s], T=[%s], MEAN=[%s], MIN=[%s], MAX=[%s], L=[%s]"
                            % (
                                self.electricityNetNumberOfValues, self.electricityNetTotal,
                                self.electricityNetMeanAverage,
                                self.electricityNetMinimum, self.electricityNetMaximum, self.electricityNetLast))
                        self.generalLogger.debug(
                            u"READINGS - ELECTRICITY SAVED: N=[%s], T=[%s], MEAN=[%s], MIN=[%s], MAX=[%s], L=[%s]"
                            % (self.electricitySavedNumberOfValues, self.electricitySavedTotal,
                               self.electricitySavedMeanAverage, self.electricitySavedMinimum,
                               self.electricitySavedMaximum, self.electricitySavedLast))
                        self.generalLogger.debug(
                            u"READINGS - SOLAR: N=[%s], T=[%s], MEAN=[%s], MIN=[%s], MAX=[%s], L=[%s]"
                            % (self.solarNumberOfValues, self.solarTotal, self.solarMeanAverage, self.solarMinimum,
                               self.solarMaximum, self.solarLast))
                        self.generalLogger.debug(
                            u"READINGS - SOLAR USED: N=[%s], T=[%s], MEAN=[%s], MIN=[%s], MAX=[%s], L=[%s]"
                            % (self.solarUsedNumberOfValues, self.solarUsedTotal, self.solarUsedMeanAverage,
                               self.solarUsedMinimum, self.solarUsedMaximum, self.solarUsedLast))
                        self.generalLogger.debug(
                            u"READINGS - SOLAR EXPORTED: N=[%s], T=[%s], MEAN=[%s], MIN=[%s], MAX=[%s], L=[%s]"
                            % (self.solarExportedNumberOfValues, self.solarExportedTotal, self.solarExportedMeanAverage,
                               self.solarExportedMinimum, self.solarExportedMaximum, self.solarExportedLast))

                        savedElectricityCalculated = False  # Used to determine whether Solar PV FIT + Elec savings can be calculated
                        #   Gets set to True if Elec saving calculated so that it can be added to Solar Total Income
                        #   to dereive and upadte state: dailyTotalPlusSavedElecIncome

                        if self.globals['config']['supportsElectricity']:

                            if "curEnergyLevel" in devElectricity.states:
                                if commandSentToSmappee == 'RESET_CONSUMPTION':

                                    self.globals['smappees'][devElectricity.id]['curEnergyLevel'] = 0.0
                                    self.globals['smappees'][devElectricity.id]['accumEnergyTotal'] = 0.0
                                    wattStr = "%3.0f Watts" % (
                                        self.globals['smappees'][devElectricity.id]['curEnergyLevel'])
                                    devElectricity.updateStateOnServer("curEnergyLevel",
                                                                       self.globals['smappees'][devElectricity.id][
                                                                           'curEnergyLevel'], uiValue=wattStr)
                                    if float(indigo.server.apiVersion) >= 1.18:
                                        devElectricity.updateStateImageOnServer(indigo.kStateImageSel.EnergyMeterOff)

                                self.options = devElectricity.pluginProps[
                                    'optionsEnergyMeterCurPower']  # mean, minimum, maximum, last

                                if self.options == 'mean':  # mean, minimum, maximum, last
                                    if self.electricityNumberOfValues > 0:
                                        watts = (self.electricityMeanAverage * 60) / 5
                                    else:
                                        self.generalLogger.debug(
                                            u"ELECTRICITY: CL=[%s], UTCL=[%s], LRUTC=[%s], LRUTC600=[%s]" % (
                                                self.electricityLast, self.timestampUtcLast,
                                                self.lastReadingElectricityUtc,
                                                (self.lastReadingElectricityUtc - 600000)))
                                        if self.electricityLast > 0.0 and self.timestampUtcLast != 0 and self.timestampUtcLast > (
                                                self.lastReadingElectricityUtc - 600000):
                                            watts = self.electricityLast * 12
                                        else:
                                            watts = 0.0
                                elif self.options == 'minimum':
                                    if self.electricityNumberOfValues > 0:
                                        watts = self.electricityMinimum * 12
                                    else:
                                        self.generalLogger.debug(
                                            u"ELECTRICITY: CL=[%s], UTCL=[%s], LRUTC=[%s], LRUTC600=[%s]" % (
                                                self.electricityLast, self.timestampUtcLast,
                                                self.lastReadingElectricityUtc,
                                                (self.lastReadingElectricityUtc - 600000)))
                                        if self.electricityLast > 0.0 and self.timestampUtcLast != 0 and self.timestampUtcLast > (
                                                self.lastReadingElectricityUtc - 600000):
                                            watts = self.electricityLast * 12
                                        else:
                                            watts = 0.0
                                elif self.options == 'maximum':
                                    if self.electricityNumberOfValues > 0:
                                        watts = self.electricityMaximum * 12
                                    else:
                                        self.generalLogger.debug(
                                            u"ELECTRICITY: CL=[%s], UTCL=[%s], LRUTC=[%s], LRUTC600=[%s]" % (
                                                self.electricityLast, self.timestampUtcLast,
                                                self.lastReadingElectricityUtc,
                                                (self.lastReadingElectricityUtc - 600000)))
                                        if self.electricityLast > 0.0 and self.timestampUtcLast != 0 and self.timestampUtcLast > (
                                                self.lastReadingElectricityUtc - 600000):
                                            watts = self.electricityLast * 12
                                        else:
                                            watts = 0.0
                                else:  # Assume last
                                    self.generalLogger.debug(
                                        u"ELECTRICITY: CL=[%s], UTCL=[%s], LRUTC=[%s], LRUTC600=[%s]" % (
                                            self.electricityLast, self.timestampUtcLast, self.lastReadingElectricityUtc,
                                            (self.lastReadingElectricityUtc - 600000)))
                                    if self.electricityLast > 0.0 and self.timestampUtcLast != 0 and self.timestampUtcLast > (
                                            self.lastReadingElectricityUtc - 600000):
                                        watts = self.electricityLast * 12
                                    else:
                                        watts = 0.0

                                if watts == 0.0:
                                    watts = self.electricityPrevious

                                wattsStr = "%d Watts" % watts
                                if not self.globals['smappees'][devElectricity.id]['hideEnergyMeterCurPower']:
                                    self.generalLogger.info(
                                        u"received '%s' power load reading: %s" % (devElectricity.name, wattsStr))

                                devElectricity.updateStateOnServer("curEnergyLevel", watts, uiValue=wattsStr)
                                if float(indigo.server.apiVersion) >= 1.18:
                                    devElectricity.updateStateImageOnServer(indigo.kStateImageSel.EnergyMeterOn)

                            if "accumEnergyTotal" in devElectricity.states:

                                if commandSentToSmappee == 'RESET_CONSUMPTION':
                                    self.globals['smappees'][devElectricity.id]['accumEnergyTotal'] = 0.0
                                    wattStr = "%3.0f Watts" % (
                                        self.globals['smappees'][devElectricity.id]['accumEnergyTotal'])
                                    devElectricity.updateStateOnServer("accumEnergyTotal",
                                                                       self.globals['smappees'][devElectricity.id][
                                                                           'accumEnergyTotal'], uiValue=wattStr)

                                kwh = float(devElectricity.states.get("accumEnergyTotal", 0))
                                kwh += float(self.electricityTotal / 1000.0)
                                kwhStr = "%0.3f kWh" % kwh
                                kwhUnitCost = self.globals['smappees'][devElectricity.id]['kwhUnitCost']
                                dailyStandingCharge = self.globals['smappees'][devElectricity.id]['dailyStandingCharge']

                                amountGross = 0.00
                                if kwhUnitCost > 0.00:
                                    amountGross = (dailyStandingCharge + (kwh * kwhUnitCost))
                                    amountGrossReformatted = float(str("%0.2f" % amountGross))
                                    amountGrossStr = str("%0.2f %s" % (
                                        amountGross, self.globals['smappees'][devElectricity.id]['currencyCode']))
                                    devElectricity.updateStateOnServer("dailyTotalCost", amountGrossReformatted,
                                                                       uiValue=amountGrossStr)

                                if not self.globals['smappees'][devElectricity.id]['hideEnergyMeterAccumPower']:
                                    if kwhUnitCost == 0.00 or self.globals['smappees'][devElectricity.id][
                                            'hideEnergyMeterAccumPowerCost']:
                                        self.generalLogger.info(
                                            u"received '%s' energy total: %s" % (devElectricity.name, kwhStr))
                                    else:
                                        self.generalLogger.info(u"received '%s' energy total: %s (Gross %s)" % (
                                            devElectricity.name, kwhStr, amountGrossStr))

                                kwhReformatted = float(str("%0.3f" % kwh))
                                devElectricity.updateStateOnServer("accumEnergyTotal", kwhReformatted, uiValue=kwhStr)

                            if "alwaysOn" in devElectricity.states:
                                wattsAlwaysOn = self.alwaysOn
                                wattsAlwaysOnStr = "%d Watts" % wattsAlwaysOn
                                if not self.globals['smappees'][devElectricity.id]['hideAlwaysOnPower']:
                                    self.generalLogger.info(u"received '%s' always-on reading: %s" % (
                                        devElectricity.name, wattsAlwaysOnStr))
                                devElectricity.updateStateOnServer("alwaysOn", watts, uiValue=wattsAlwaysOnStr)

                            self.globals['smappees'][devElectricity.id]['lastReadingElectricityUtc'] = self.timestampUtc

                        if self.globals['config']['supportsElectricityNet']:

                            if "curEnergyLevel" in devElectricityNet.states:
                                if commandSentToSmappee == 'RESET_CONSUMPTION':

                                    self.globals['smappees'][devElectricityNet.id]['curEnergyLevel'] = 0.0
                                    self.globals['smappees'][devElectricityNet.id]['accumEnergyTotal'] = 0.0
                                    wattStr = "%3.0f Watts" % (
                                        self.globals['smappees'][devElectricityNet.id]['curEnergyLevel'])
                                    devElectricityNet.updateStateOnServer("curEnergyLevel", self.globals['smappees'][
                                        devElectricityNet.id]['curEnergyLevel'], uiValue=wattStr)
                                    if float(indigo.server.apiVersion) >= 1.18:
                                        devElectricityNet.updateStateImageOnServer(indigo.kStateImageSel.EnergyMeterOff)

                                self.options = devElectricityNet.pluginProps['optionsEnergyMeterCurPower']

                                if self.options == 'mean':  # mean, minimum, maximum, last
                                    if self.electricityNetNumberOfValues > 0:
                                        wattsNet = (self.electricityNetMeanAverage * 60) / 5
                                    else:
                                        self.generalLogger.debug(
                                            u"ELECTRICITY NET: CL=[%s], UTCL=[%s], LRUTC=[%s], LRUTC600=[%s]" % (
                                                self.electricityNetLast, self.timestampUtcLast,
                                                self.lastReadingElectricityNetUtc,
                                                (self.lastReadingElectricityNetUtc - 600000)))
                                        if self.electricityNetLast > 0.0 and self.timestampUtcLast != 0 and self.timestampUtcLast > (
                                                self.lastReadingElectricityNetUtc - 600000):
                                            wattsNet = self.electricityNetLast * 12
                                        else:
                                            wattsNet = 0.0
                                elif self.options == 'minimum':
                                    if self.electricityNetNumberOfValues > 0:
                                        wattsNet = self.electricityNetMinimum * 12
                                    else:
                                        self.generalLogger.debug(
                                            u"ELECTRICITY NET: CL=[%s], UTCL=[%s], LRUTC=[%s], LRUTC600=[%s]" % (
                                                self.electricityNetLast, self.timestampUtcLast,
                                                self.lastReadingElectricityNetUtc,
                                                (self.lastReadingElectricityNetUtc - 600000)))
                                        if self.electricityNetLast > 0.0 and self.timestampUtcLast != 0 and self.timestampUtcLast > (
                                                self.lastReadingElectricityNetUtc - 600000):
                                            wattsNet = self.electricityNetLast * 12
                                        else:
                                            wattsNet = 0.0
                                elif self.options == 'maximum':
                                    if self.electricityNetNumberOfValues > 0:
                                        wattsNet = self.electricityNetMaximum * 12
                                    else:
                                        self.generalLogger.debug(
                                            u"ELECTRICITY NET: CL=[%s], UTCL=[%s], LRUTC=[%s], LRUTC600=[%s]" % (
                                                self.electricityNetLast, self.timestampUtcLast,
                                                self.lastReadingElectricityNetUtc,
                                                (self.lastReadingElectricityNetUtc - 600000)))
                                        if self.electricityNetLast > 0.0 and self.timestampUtcLast != 0 and self.timestampUtcLast > (
                                                self.lastReadingElectricityNetUtc - 600000):
                                            wattsNet = self.electricityNetLast * 12
                                        else:
                                            wattsNet = 0.0
                                else:  # Assume last
                                    self.generalLogger.debug(
                                        u"ELECTRICITY NET: CL=[%s], UTCL=[%s], LRUTC=[%s], LRUTC600=[%s]" % (
                                            self.electricityNetLast, self.timestampUtcLast,
                                            self.lastReadingElectricityNetUtc,
                                            (self.lastReadingElectricityNetUtc - 600000)))
                                    if self.electricityNetLast > 0.0 and self.timestampUtcLast != 0 and self.timestampUtcLast > (
                                            self.lastReadingElectricityNetUtc - 600000):
                                        wattsNet = self.electricityNetLast * 12
                                    else:
                                        wattsNet = 0.0

                                if wattsNet == 0.0:
                                    wattsNet = self.electricityNetPrevious

                                wattsNetStr = "%d Watts" % wattsNet
                                if not self.globals['smappees'][devElectricityNet.id]['hideEnergyMeterCurNetPower']:
                                    if wattsNet == 0.0 and self.globals['smappees'][devElectricityNet.id][
                                            'hideEnergyMeterCurZeroNetPower']:
                                        pass
                                    else:
                                        self.generalLogger.info(u"received '%s' electricity net reading: %s" % (
                                            devElectricityNet.name, wattsNetStr))
                                devElectricityNet.updateStateOnServer("curEnergyLevel", wattsNet, uiValue=wattsNetStr)
                                if float(indigo.server.apiVersion) >= 1.18:
                                    devElectricityNet.updateStateImageOnServer(indigo.kStateImageSel.EnergyMeterOn)

                                if watts > 0.00:
                                    netPercentage = int(round((wattsNet / watts) * 100))
                                else:
                                    netPercentage = int(0)
                                netPercentageStr = "%d%%" % netPercentage
                                devElectricityNet.updateStateOnServer("kwhCurrentNetPercentage", netPercentage,
                                                                      uiValue=netPercentageStr)

                            if "accumEnergyTotal" in devElectricityNet.states:
                                if commandSentToSmappee == 'RESET_CONSUMPTION':
                                    self.globals['smappees'][devElectricityNet.id]['accumEnergyTotal'] = 0.0
                                    wattNetStr = "%3.0f Watts" % (
                                        self.globals['smappees'][devElectricityNet.id]['accumEnergyTotal'])
                                    devElectricityNet.updateStateOnServer("accumEnergyTotal", self.globals['smappees'][
                                        devElectricityNet.id]['accumEnergyTotal'], uiValue=wattNetStr)

                                if "accumEnergyTotal" in devElectricity.states:
                                    # Need to check this as the kwh, gross amount, unit cost and currency code is retrieved from the Electricity Device

                                    kwhNet = float(devElectricityNet.states.get("accumEnergyTotal", 0))
                                    kwhNet += float(self.electricityNetTotal / 1000.0)
                                    kwhNetStr = str("%0.3f kWh" % kwhNet)
                                    kwhUnitCost = self.globals['smappees'][devElectricity.id]['kwhUnitCost']
                                    dailyStandingCharge = self.globals['smappees'][devElectricity.id][
                                        'dailyStandingCharge']

                                    kwhNetReformatted = float("%0.3f" % kwhNet)
                                    devElectricityNet.updateStateOnServer("accumEnergyTotal", kwhNetReformatted,
                                                                          uiValue=kwhNetStr)

                                    amountNet = 0.00
                                    if kwhUnitCost > 0.00:
                                        amountNet = dailyStandingCharge + (kwhNet * kwhUnitCost)
                                        amountNetReformatted = float(str("%0.2f" % amountNet))
                                        amountNetStr = str("%0.2f %s" % (
                                            amountNet, self.globals['smappees'][devElectricity.id]['currencyCode']))
                                        devElectricityNet.updateStateOnServer("dailyNetTotalCost", amountNetReformatted,
                                                                              uiValue=amountNetStr)

                                    if not self.globals['smappees'][devElectricityNet.id][
                                            'hideEnergyMeterAccumNetPower']:
                                        if kwhUnitCost == 0.00 or self.globals['smappees'][devElectricityNet.id][
                                                'hideEnergyMeterAccumNetPowerCost']:
                                            self.generalLogger.info(u"received '%s' net energy total: %s" % (
                                                devElectricityNet.name, kwhNetStr))
                                        else:
                                            self.generalLogger.info(u"received '%s' net energy total: %s (Gross %s)" % (
                                                devElectricityNet.name, kwhNetStr, amountNetStr))

                                    if kwhNet > 0.00:
                                        netDailyPercentage = int(round((kwhNet / kwh) * 100))
                                    else:
                                        netDailyPercentage = int(0)
                                    netDailyPercentageStr = "%d%%" % netDailyPercentage
                                    devElectricityNet.updateStateOnServer("kwhDailyTotalNetPercentage",
                                                                          netDailyPercentage,
                                                                          uiValue=netDailyPercentageStr)

                            self.globals['smappees'][devElectricityNet.id][
                                'lastReadingElectricityNetUtc'] = self.timestampUtc

                        if self.globals['config']['supportsElectricitySaved']:

                            if "curEnergyLevel" in devElectricitySaved.states:
                                if commandSentToSmappee == 'RESET_CONSUMPTION':

                                    self.globals['smappees'][devElectricitySaved.id]['curEnergyLevel'] = 0.0
                                    self.globals['smappees'][devElectricitySaved.id]['accumEnergyTotal'] = 0.0
                                    wattStr = "%3.0f Watts" % (
                                        self.globals['smappees'][devElectricitySaved.id]['curEnergyLevel'])
                                    devElectricitySaved.updateStateOnServer("curEnergyLevel", self.globals['smappees'][
                                        devElectricitySaved.id]['curEnergyLevel'], uiValue=wattStr)
                                    if float(indigo.server.apiVersion) >= 1.18:
                                        devElectricitySaved.updateStateImageOnServer(
                                            indigo.kStateImageSel.EnergyMeterOff)

                                self.options = devElectricitySaved.pluginProps['optionsEnergyMeterCurPower']

                                if self.options == 'mean':  # mean, minimum, maximum, last
                                    if self.electricitySavedNumberOfValues > 0:
                                        wattsSaved = (self.electricitySavedMeanAverage * 60) / 5
                                    else:
                                        self.generalLogger.debug(
                                            u"ELECTRICITY SAVED: CL=[%s], UTCL=[%s], LRUTC=[%s], LRUTC600=[%s]" % (
                                                self.electricitySavedLast, self.timestampUtcLast,
                                                self.lastReadingElectricitySavedUtc,
                                                (self.lastReadingElectricitySavedUtc - 600000)))
                                        if self.electricitySavedLast > 0.0 and self.timestampUtcLast != 0 and self.timestampUtcLast > (
                                                self.lastReadingElectricitySavedUtc - 600000):
                                            wattsSaved = self.electricitySavedLast * 12
                                        else:
                                            wattsSaved = 0.0
                                elif self.options == 'minimum':
                                    if self.electricitySavedNumberOfValues > 0:
                                        wattsSaved = self.electricitySavedMinimum * 12
                                    else:
                                        self.generalLogger.debug(
                                            u"ELECTRICITY SAVED: CL=[%s], UTCL=[%s], LRUTC=[%s], LRUTC600=[%s]" % (
                                                self.electricitySavedLast, self.timestampUtcLast,
                                                self.lastReadingElectricitySavedUtc,
                                                (self.lastReadingElectricitySavedUtc - 600000)))
                                        if self.electricitySavedLast > 0.0 and self.timestampUtcLast != 0 and self.timestampUtcLast > (
                                                self.lastReadingElectricitySavedUtc - 600000):
                                            wattsSaved = self.electricitySavedLast * 12
                                        else:
                                            wattsSaved = 0.0
                                elif self.options == 'maximum':
                                    if self.electricitySavedNumberOfValues > 0:
                                        wattsSaved = self.electricitySavedMaximum * 12
                                    else:
                                        self.generalLogger.debug(
                                            u"ELECTRICITY SAVED: CL=[%s], UTCL=[%s], LRUTC=[%s], LRUTC600=[%s]" % (
                                                self.electricitySavedLast, self.timestampUtcLast,
                                                self.lastReadingElectricitySavedUtc,
                                                (self.lastReadingElectricitySavedUtc - 600000)))
                                        if self.electricitySavedLast > 0.0 and self.timestampUtcLast != 0 and self.timestampUtcLast > (
                                                self.lastReadingElectricitySavedUtc - 600000):
                                            wattsSaved = self.electricitySavedLast * 12
                                        else:
                                            wattsSaved = 0.0
                                else:  # Assume last
                                    self.generalLogger.debug(
                                        u"ELECTRICITY SAVED: CL=[%s], UTCL=[%s], LRUTC=[%s], LRUTC600=[%s]" % (
                                            self.electricitySavedLast, self.timestampUtcLast,
                                            self.lastReadingElectricitySavedUtc,
                                            (self.lastReadingElectricitySavedUtc - 600000)))
                                    if self.electricitySavedLast > 0.0 and self.timestampUtcLast != 0 and self.timestampUtcLast > (
                                            self.lastReadingElectricitySavedUtc - 600000):
                                        wattsSaved = self.electricitySavedLast * 12
                                    else:
                                        wattsSaved = 0.0

                                if wattsSaved == 0.0:
                                    wattsSaved = self.electricitySavedPrevious

                                wattsSavedStr = "%d Watts" % wattsSaved
                                if not self.globals['smappees'][devElectricitySaved.id]['hideEnergyMeterCurSavedPower']:
                                    if wattsSaved == 0.0 and self.globals['smappees'][devElectricitySaved.id][
                                            'hideEnergyMeterCurZeroSavedPower']:
                                        pass
                                    else:
                                        self.generalLogger.info(u"received '%s' electricity saved reading: %s" % (
                                            devElectricitySaved.name, wattsSavedStr))
                                devElectricitySaved.updateStateOnServer("curEnergyLevel", wattsSaved,
                                                                        uiValue=wattsSavedStr)
                                if float(indigo.server.apiVersion) >= 1.18:
                                    devElectricitySaved.updateStateImageOnServer(indigo.kStateImageSel.EnergyMeterOn)

                                if watts > 0.00:
                                    savedPercentage = int(round((wattsSaved / watts) * 100))
                                else:
                                    savedPercentage = int(0)
                                savedPercentageStr = "%d%%" % savedPercentage
                                devElectricitySaved.updateStateOnServer("kwhCurrentSavedPercentage", savedPercentage,
                                                                        uiValue=savedPercentageStr)

                            if "accumEnergyTotal" in devElectricitySaved.states:
                                if commandSentToSmappee == 'RESET_CONSUMPTION':
                                    self.globals['smappees'][devElectricitySaved.id]['accumEnergyTotal'] = 0.0
                                    wattSavedStr = "%3.0f Watts" % (
                                        self.globals['smappees'][devElectricitySaved.id]['accumEnergyTotal'])
                                    devElectricitySaved.updateStateOnServer("accumEnergyTotal",
                                                                            self.globals['smappees'][
                                                                                devElectricitySaved.id][
                                                                                'accumEnergyTotal'],
                                                                            uiValue=wattSavedStr)

                                if "accumEnergyTotal" in devElectricity.states:
                                    # Need to check this as the gross amount, unit cost and currency code is retrieved from the Electricity Device

                                    kwhSaved = float(devElectricitySaved.states.get("accumEnergyTotal", 0))
                                    kwhSaved += float(self.electricitySavedTotal / 1000.0)
                                    kwhSavedStr = str("%0.3f kWh" % kwhSaved)
                                    kwhUnitCost = self.globals['smappees'][devElectricity.id]['kwhUnitCost']

                                    amountSaved = 0.00
                                    if kwhUnitCost > 0.00:
                                        amountSaved = (kwhSaved * kwhUnitCost)
                                        amountSavedReformatted = float(str("%0.2f" % amountSaved))
                                        amountSavedStr = str("%0.2f %s" % (
                                            amountSaved, self.globals['smappees'][devElectricity.id]['currencyCode']))
                                        devElectricitySaved.updateStateOnServer("dailyTotalCostSaving",
                                                                                amountSavedReformatted,
                                                                                uiValue=amountSavedStr)

                                        savedElectricityCalculated = True  # Enables calculation and storing of: dailyTotalPlusSavedElecIncome

                                    if not self.globals['smappees'][devElectricitySaved.id][
                                            'hideEnergyMeterAccumSavedPower']:
                                        if kwhUnitCost == 0.00 or self.globals['smappees'][devElectricitySaved.id][
                                                'hideEnergyMeterAccumSavedPowerCost']:
                                            self.generalLogger.info(u"received '%s' saved energy total: %s" % (
                                                devElectricitySaved.name, kwhSavedStr))
                                        else:
                                            self.generalLogger.info(
                                                u"received '%s' saved energy total: %s (Saved %s)" % (
                                                    devElectricitySaved.name, kwhSavedStr, amountSavedStr))

                                    kwhSavedReformatted = float("%0.3f" % kwhSaved)
                                    devElectricitySaved.updateStateOnServer("accumEnergyTotal", kwhSavedReformatted,
                                                                            uiValue=kwhSavedStr)

                                    if kwhSaved > 0.00:
                                        savedDailyPercentage = int(round((kwhSaved / kwh) * 100))
                                    else:
                                        savedDailyPercentage = int(0)
                                    savedDailyPercentageStr = "%d %%" % savedDailyPercentage
                                    devElectricitySaved.updateStateOnServer("kwhDailyTotalSavedPercentage",
                                                                            savedDailyPercentage,
                                                                            uiValue=savedDailyPercentageStr)

                            self.globals['smappees'][devElectricitySaved.id][
                                'lastReadingElectricitySavedUtc'] = self.timestampUtc

                        if self.globals['config']['supportsSolar']:

                            if "curEnergyLevel" in devSolar.states:
                                if commandSentToSmappee == 'RESET_CONSUMPTION':

                                    self.globals['smappees'][devSolar.id]['curEnergyLevel'] = 0.0
                                    self.globals['smappees'][devSolar.id]['accumEnergyTotal'] = 0.0
                                    wattSolarStr = "%3.0f Watts" % (
                                        self.globals['smappees'][devSolar.id]['curEnergyLevel'])
                                    devSolar.updateStateOnServer("curEnergyLevel",
                                                                 self.globals['smappees'][devSolar.id][
                                                                     'curEnergyLevel'], uiValue=wattSolarStr)
                                    if float(indigo.server.apiVersion) >= 1.18:
                                        devSolar.updateStateImageOnServer(indigo.kStateImageSel.EnergyMeterOff)

                                self.optionsEnergyMeterCurPower = devSolar.pluginProps[
                                    'optionsEnergyMeterCurPower']  # mean, minimum, maximum, last
                                if self.optionsEnergyMeterCurPower == 'mean':
                                    if self.solarNumberOfValues > 0:
                                        wattsSolar = self.solarTotal * (
                                                60.0 / float(float(self.solarNumberOfValues) * 5))
                                        self.generalLogger.debug(u"watts > 0 =[%s]" % watts)
                                    else:
                                        self.generalLogger.debug(
                                            u"SOLAR: CL=[%s], UTCL=[%s], LRUTC=[%s], LRUTC600=[%s]" % (
                                                self.solarLast, self.timestampUtcLast, self.lastReadingSolarUtc,
                                                (self.lastReadingSolarUtc - 600000)))
                                        if self.solarLast > 0.0 and self.timestampUtcLast != 0 and self.timestampUtcLast > (
                                                self.lastReadingSolarUtc - 600000):
                                            wattsSolar = self.solarLast * 12
                                        else:
                                            wattsSolar = 0.0
                                elif self.optionsEnergyMeterCurPower == 'minimum':
                                    if self.solarNumberOfValues > 0:
                                        wattsSolar = self.solarMinimum * 12
                                    else:
                                        self.generalLogger.debug(
                                            u"SOLAR: CL=[%s], UTCL=[%s], LRUTC=[%s], LRUTC600=[%s]" % (
                                                self.solarLast, self.timestampUtcLast, self.lastReadingSolarUtc,
                                                (self.lastReadingSolarUtc - 600000)))
                                        if self.solarLast > 0.0 and self.timestampUtcLast != 0 and self.timestampUtcLast > (
                                                self.lastReadingSolarUtc - 600000):
                                            wattsSolar = self.solarLast * 12
                                        else:
                                            wattsSolar = 0.0
                                elif self.optionsEnergyMeterCurPower == 'maximum':
                                    if self.solarNumberOfValues > 0:
                                        wattsSolar = self.solarMaximum * 12
                                    else:
                                        self.generalLogger.debug(
                                            u"SOLAR: CL=[%s], UTCL=[%s], LRUTC=[%s], LRUTC600=[%s]" % (
                                                self.solarLast, self.timestampUtcLast, self.lastReadingSolarUtc,
                                                (self.lastReadingSolarUtc - 600000)))
                                        if self.solarLast > 0.0 and self.timestampUtcLast != 0 and self.timestampUtcLast > (
                                                self.lastReadingSolarUtc - 600000):
                                            wattsSolar = self.solarLast * 12
                                        else:
                                            wattsSolar = 0.0
                                else:  # Assume last
                                    self.generalLogger.debug(u"SOLAR: CL=[%s], UTCL=[%s], LRUTC=[%s], LRUTC600=[%s]" % (
                                        self.solarLast, self.timestampUtcLast, self.lastReadingSolarUtc,
                                        (self.lastReadingSolarUtc - 600000)))
                                    if self.solarLast > 0.0 and self.timestampUtcLast != 0 and self.timestampUtcLast > (
                                            self.lastReadingSolarUtc - 600000):
                                        wattsSolar = self.solarLast * 12
                                    else:
                                        wattsSolar = 0.0

                                if wattsSolar == 0.0:
                                    wattsSolar = self.solarPrevious

                                wattsSolarStr = "%d Watts" % wattsSolar
                                if not self.globals['smappees'][devSolar.id]['hideSolarMeterCurGeneration']:
                                    if wattsSolar == 0.0 and self.globals['smappees'][devSolar.id][
                                            'hideZeroSolarMeterCurGeneration']:
                                        pass
                                    else:
                                        self.generalLogger.info(u"received '%s' solar generation reading: %s" % (
                                            devSolar.name, wattsSolarStr))
                                devSolar.updateStateOnServer("curEnergyLevel", wattsSolar, uiValue=wattsSolarStr)
                                if float(indigo.server.apiVersion) >= 1.18:
                                    devSolar.updateStateImageOnServer(indigo.kStateImageSel.EnergyMeterOn)

                            if "accumEnergyTotal" in devSolar.states:
                                if commandSentToSmappee == 'RESET_CONSUMPTION':
                                    self.globals['smappees'][devSolar.id]['accumEnergyTotal'] = 0.0
                                    wattSolarStr = "%3.0f Watts" % (
                                        self.globals['smappees'][devSolar.id]['accumEnergyTotal'])
                                    devSolar.updateStateOnServer("accumEnergyTotal",
                                                                 self.globals['smappees'][devSolar.id][
                                                                     'accumEnergyTotal'], uiValue=wattSolarStr)

                                # To calculate Amounts (financials) all three device types solar, solaUsed and solarExported must be present

                                self.financialsEnabled = True

                                # Calculate Solar Total (Daily)

                                kwhSolar = float(devSolar.states.get("accumEnergyTotal", 0))
                                kwhSolar += float(self.solarTotal / 1000.0)
                                kwhSolarStr = str("%0.3f kWh" % kwhSolar)

                                generationRate = self.globals['smappees'][devSolar.id]['generationRate']
                                exportRate = self.globals['smappees'][devSolar.id]['exportRate']

                                if self.globals['config'][
                                        'supportsSolarUsed'] and "accumEnergyTotal" in devSolarUsed.states:
                                    # Calculate Solar Used (Daily)
                                    kwhUsed = float(devSolarUsed.states.get("accumEnergyTotal", 0))
                                    kwhUsed += float(self.solarUsedTotal / 1000.0)

                                    if self.globals['config'][
                                            'supportsSolarExported'] and "accumEnergyTotal" in devSolarExported.states:
                                        # Calculate Solar Exported (Daily)
                                        kwhExported = float(devSolarExported.states.get("accumEnergyTotal", 0))
                                        kwhExported += float(self.solarExportedTotal / 1000.0)

                                        amountSolar = 0.00
                                        amountExported = 0.00  # Needed for calculation of total FIT payment
                                        amountGenerated = 0.00

                                        if generationRate > 0.00:
                                            amountGenerated = (kwhSolar * generationRate)
                                        if exportRate > 0.00:
                                            exportType = self.globals['smappees'][devSolar.id]['exportType']
                                            if exportType == 'percentage':
                                                exportPercentage = self.globals['smappees'][devSolar.id][
                                                    'exportPercentage']
                                            elif exportType == 'actual':
                                                exportPercentage = (kwhExported / kwhSolar) * 100
                                            else:
                                                exportPercentage = 0.00
                                            amountExported = (kwhSolar * exportRate * exportPercentage) / 100

                                        amountSolar = amountGenerated + amountExported

                                        amountGeneratedReformatted = float(str("%0.2f" % amountGenerated))
                                        amountGeneratedStr = str("%0.2f %s" % (
                                            amountGenerated, self.globals['smappees'][devSolar.id]['currencyCode']))
                                        devSolar.updateStateOnServer("dailyTotalGenOnlyIncome",
                                                                     amountGeneratedReformatted,
                                                                     uiValue=amountGeneratedStr)

                                        amountSolarReformatted = float(str("%0.2f" % amountSolar))
                                        amountSolarStr = str("%0.2f %s" % (
                                            amountSolarReformatted,
                                            self.globals['smappees'][devSolar.id]['currencyCode']))
                                        devSolar.updateStateOnServer("dailyTotalIncome", amountSolarReformatted,
                                                                     uiValue=amountSolarStr)

                                        if savedElectricityCalculated:
                                            amountSolarPlusSaving = amountSolar + amountSaved
                                            amountSolarPlusSavingReformatted = float(
                                                str("%0.2f" % amountSolarPlusSaving))
                                            amountSolarPlusSavingStr = str("%0.2f %s" % (amountSolarPlusSaving,
                                                                                         self.globals['smappees'][
                                                                                             devSolar.id][
                                                                                             'currencyCode']))
                                            devSolar.updateStateOnServer("dailyTotalPlusSavedElecIncome",
                                                                         amountSolarPlusSavingReformatted,
                                                                         uiValue=amountSolarPlusSavingStr)

                                if not self.globals['smappees'][devSolar.id]['hideSolarMeterAccumGeneration']:
                                    if self.globals['smappees'][devSolar.id]['hideSolarMeterAccumGenerationCost']:
                                        if generationRate == 0.00 and self.globals['smappees'][devSolar.id][
                                                'hideZeroSolarMeterCurGeneration']:
                                            pass  # Don't output zero solar values
                                        else:
                                            # if 'no change in solar' and self.globals['smappees'][devSolar.id]['hideNoChangeInSolarMeterAccumGeneration']:
                                            #     pass
                                            # else:
                                            # do code below .... (remember to indent it!)
                                            self.generalLogger.info(u"received '%s' solar generation total: %s" % (
                                                devSolar.name, kwhSolarStr))
                                    else:
                                        if generationRate == 0.00 and self.globals['smappees'][devSolar.id][
                                                'hideZeroSolarMeterCurGeneration']:
                                            pass  # Don't output zero solar values
                                        else:
                                            # if 'no change in solar' and self.globals['smappees'][devSolar.id]['hideNoChangeInSolarMeterAccumGeneration']:
                                            #     pass
                                            # else:
                                            # do code below .... (remember to indent it!)
                                            self.generalLogger.info(u"received '%s' solar generation total: %s (%s)" % (
                                                devSolar.name, kwhSolarStr, amountSolarStr))

                                            # self.globals['smappees'][devSolar.id]['hideNoChangeInSolarMeterAccumGeneration'] and kwhReformatted == float(devSolar.states['accumEnergyTotal']) and wattsSolar == 0.0:

                                kwhSolarReformatted = float("%0.3f" % kwhSolar)
                                devSolar.updateStateOnServer("accumEnergyTotal", kwhSolarReformatted,
                                                             uiValue=kwhSolarStr)

                            self.globals['smappees'][devSolar.id]['lastReadingSolarUtc'] = self.timestampUtc

                        if self.globals['config']['supportsSolarUsed']:

                            if "curEnergyLevel" in devSolarUsed.states:
                                if commandSentToSmappee == 'RESET_CONSUMPTION':

                                    self.globals['smappees'][devSolarUsed.id]['curEnergyLevel'] = 0.0
                                    self.globals['smappees'][devSolarUsed.id]['accumEnergyTotal'] = 0.0
                                    wattsUsedStr = "%3.0f Watts" % (
                                        self.globals['smappees'][devSolarUsed.id]['curEnergyLevel'])
                                    devSolarUsed.updateStateOnServer("curEnergyLevel",
                                                                     self.globals['smappees'][devSolarUsed.id][
                                                                         'curEnergyLevel'], uiValue=wattsUsedStr)
                                    if float(indigo.server.apiVersion) >= 1.18:
                                        devSolarUsed.updateStateImageOnServer(indigo.kStateImageSel.EnergyMeterOff)

                                self.options = devSolarUsed.pluginProps['optionsEnergyMeterCurPower']

                                if self.options == 'mean':  # mean, minimum, maximum, last
                                    if self.solarUsedNumberOfValues > 0:
                                        wattsUsed = (self.solarUsedMeanAverage * 60) / 5
                                    else:
                                        self.generalLogger.debug(
                                            u"ELECTRICITY NET: CL=[%s], UTCL=[%s], LRUTC=[%s], LRUTC600=[%s]" % (
                                                self.solarUsedLast, self.timestampUtcLast,
                                                self.lastReadingElectricityNetUtc,
                                                (self.lastReadingElectricityNetUtc - 600000)))
                                        if self.solarUsedLast > 0.0 and self.timestampUtcLast != 0 and self.timestampUtcLast > (
                                                self.lastReadingElectricityNetUtc - 600000):
                                            wattsUsed = self.solarUsedLast * 12
                                        else:
                                            wattsUsed = 0.0
                                elif self.options == 'minimum':
                                    if self.solarUsedNumberOfValues > 0:
                                        wattsUsed = self.solarUsedMinimum * 12
                                    else:
                                        self.generalLogger.debug(
                                            u"ELECTRICITY NET: CL=[%s], UTCL=[%s], LRUTC=[%s], LRUTC600=[%s]" % (
                                                self.solarUsedLast, self.timestampUtcLast,
                                                self.lastReadingElectricityNetUtc,
                                                (self.lastReadingElectricityNetUtc - 600000)))
                                        if self.solarUsedLast > 0.0 and self.timestampUtcLast != 0 and self.timestampUtcLast > (
                                                self.lastReadingElectricityNetUtc - 600000):
                                            wattsUsed = self.solarUsedLast * 12
                                        else:
                                            wattsUsed = 0.0
                                elif self.options == 'maximum':
                                    if self.solarUsedNumberOfValues > 0:
                                        wattsUsed = self.solarUsedMaximum * 12
                                    else:
                                        self.generalLogger.debug(
                                            u"ELECTRICITY NET: CL=[%s], UTCL=[%s], LRUTC=[%s], LRUTC600=[%s]" % (
                                                self.solarUsedLast, self.timestampUtcLast,
                                                self.lastReadingElectricityNetUtc,
                                                (self.lastReadingElectricityNetUtc - 600000)))
                                        if self.solarUsedLast > 0.0 and self.timestampUtcLast != 0 and self.timestampUtcLast > (
                                                self.lastReadingElectricityNetUtc - 600000):
                                            wattsUsed = self.solarUsedLast * 12
                                        else:
                                            wattsUsed = 0.0
                                else:  # Assume last
                                    self.generalLogger.debug(
                                        u"SOLAR USED: CL=[%s], UTCL=[%s], LRUTC=[%s], LRUTC600=[%s]" % (
                                            self.solarUsedLast, self.timestampUtcLast, self.lastReadingSolarUsedUtc,
                                            (self.lastReadingSolarUsedUtc - 600000)))
                                    if self.solarUsedLast > 0.0 and self.timestampUtcLast != 0 and self.timestampUtcLast > (
                                            self.lastReadingSolarUsedUtc - 600000):
                                        wattsUsed = self.solarUsedLast * 12
                                    else:
                                        wattsUsed = 0.0

                                if wattsUsed == 0.0:
                                    wattsUsed = self.solarUsedPrevious

                                wattsUsedStr = "%d Watts" % wattsUsed
                                if not self.globals['smappees'][devSolarUsed.id]['hideSolarUsedMeterCurGeneration']:
                                    if wattsUsed == 0.0 and self.globals['smappees'][devSolarUsed.id][
                                            'hideZeroSolarUsedMeterCurGeneration']:
                                        pass
                                    else:
                                        self.generalLogger.info(u"received '%s' solar power used reading: %s" % (
                                            devSolarUsed.name, wattsUsedStr))
                                devSolarUsed.updateStateOnServer("curEnergyLevel", wattsUsed, uiValue=wattsUsedStr)
                                if float(indigo.server.apiVersion) >= 1.18:
                                    devSolarUsed.updateStateImageOnServer(indigo.kStateImageSel.EnergyMeterOn)

                                if self.solar > 0.00:
                                    usedPercentage = int(round((self.solarUsed / self.solar) * 100))
                                else:
                                    usedPercentage = int(0)
                                usedPercentageStr = "%d %%" % usedPercentage
                                devSolarUsed.updateStateOnServer("kwhCurrentUsedPercentage", usedPercentage,
                                                                 uiValue=usedPercentageStr)

                            if "accumEnergyTotal" in devSolarUsed.states:
                                if commandSentToSmappee == 'RESET_CONSUMPTION':
                                    self.globals['smappees'][devSolarUsed.id]['accumEnergyTotal'] = 0.0
                                    wattStr = "%3.0f Watts" % (
                                        self.globals['smappees'][devSolarUsed.id]['accumEnergyTotal'])
                                    devSolarUsed.updateStateOnServer("accumEnergyTotal",
                                                                     self.globals['smappees'][devSolarUsed.id][
                                                                         'accumEnergyTotal'], uiValue=wattStr)

                                # kwhUsed = float(devSolarUsed.states.get("accumEnergyTotal", 0))
                                # kwhUsed += float(self.solarUsedTotal / 1000.0)
                                kwhUsedStr = str("%0.3f kWh" % kwhUsed)  # Calculated in solar device

                                kwhUsedReformatted = float("%0.3f" % kwhUsed)

                                if not self.globals['smappees'][devSolarUsed.id]['hideSolarUsedMeterAccumGeneration']:
                                    if self.globals['smappees'][devSolarUsed.id][
                                            'hideNoChangeInSolarUsedMeterAccumGeneration'] and kwhUsedReformatted == float(
                                            devSolarUsed.states['accumEnergyTotal']) and wattsUsed == 0.0:
                                        pass
                                    else:
                                        self.generalLogger.info(u"received '%s' solar energy used total: %s" % (
                                            devSolarUsed.name, kwhUsedStr))

                                devSolarUsed.updateStateOnServer("accumEnergyTotal", kwhUsedReformatted,
                                                                 uiValue=kwhUsedStr)

                                if "accumEnergyTotal" in devSolar.states:
                                    # Needed to caculate total used percentage - uses 'kwhSolar'

                                    if kwhSolar > 0.00:
                                        usedDailyPercentage = int(round((kwhUsed / kwhSolar) * 100))
                                    else:
                                        usedDailyPercentage = int(0)
                                    usedDailyPercentageStr = "%d %%" % usedDailyPercentage
                                    devSolarUsed.updateStateOnServer("kwhDailyTotalUsedPercentage", usedDailyPercentage,
                                                                     uiValue=usedDailyPercentageStr)

                            self.globals['smappees'][devSolarUsed.id]['lastReadingSolarUsedUtc'] = self.timestampUtc

                        if self.globals['config']['supportsSolarExported']:

                            if "curEnergyLevel" in devSolarExported.states:
                                if commandSentToSmappee == 'RESET_CONSUMPTION':

                                    self.globals['smappees'][devSolarExported.id]['curEnergyLevel'] = 0.0
                                    self.globals['smappees'][devSolarExported.id]['accumEnergyTotal'] = 0.0
                                    wattsExportedStr = "%3.0f Watts" % (
                                        self.globals['smappees'][devSolarExported.id]['curEnergyLevel'])
                                    devSolarExported.updateStateOnServer("curEnergyLevel",
                                                                         self.globals['smappees'][devSolarExported.id][
                                                                             'curEnergyLevel'],
                                                                         uiValue=wattsExportedStr)
                                    if float(indigo.server.apiVersion) >= 1.18:
                                        devSolarExported.updateStateImageOnServer(indigo.kStateImageSel.EnergyMeterOff)

                                self.options = devSolarExported.pluginProps['optionsEnergyMeterCurPower']

                                if self.options == 'mean':  # mean, minimum, maximum, last
                                    if self.solarExportedNumberOfValues > 0:
                                        wattsExported = (self.solarExportedMeanAverage * 60) / 5
                                    else:
                                        self.generalLogger.debug(
                                            u"ELECTRICITY NET: CL=[%s], UTCL=[%s], LRUTC=[%s], LRUTC600=[%s]" % (
                                                self.solarExportedLast, self.timestampUtcLast,
                                                self.lastReadingElectricityNetUtc,
                                                (self.lastReadingElectricityNetUtc - 600000)))
                                        if self.solarExportedLast > 0.0 and self.timestampUtcLast != 0 and self.timestampUtcLast > (
                                                self.lastReadingElectricityNetUtc - 600000):
                                            wattsExported = self.solarExportedLast * 12
                                        else:
                                            wattsExported = 0.0
                                elif self.options == 'minimum':
                                    if self.solarExportedNumberOfValues > 0:
                                        wattsExported = self.solarExportedMinimum * 12
                                    else:
                                        self.generalLogger.debug(
                                            u"ELECTRICITY NET: CL=[%s], UTCL=[%s], LRUTC=[%s], LRUTC600=[%s]" % (
                                                self.solarExportedLast, self.timestampUtcLast,
                                                self.lastReadingElectricityNetUtc,
                                                (self.lastReadingElectricityNetUtc - 600000)))
                                        if self.solarExportedLast > 0.0 and self.timestampUtcLast != 0 and self.timestampUtcLast > (
                                                self.lastReadingElectricityNetUtc - 600000):
                                            wattsExported = self.solarExportedLast * 12
                                        else:
                                            wattsExported = 0.0
                                elif self.options == 'maximum':
                                    if self.solarExportedNumberOfValues > 0:
                                        wattsExported = self.solarExportedMaximum * 12
                                    else:
                                        self.generalLogger.debug(
                                            u"ELECTRICITY NET: CL=[%s], UTCL=[%s], LRUTC=[%s], LRUTC600=[%s]" % (
                                                self.solarExportedLast, self.timestampUtcLast,
                                                self.lastReadingElectricityNetUtc,
                                                (self.lastReadingElectricityNetUtc - 600000)))
                                        if self.solarExportedLast > 0.0 and self.timestampUtcLast != 0 and self.timestampUtcLast > (
                                                self.lastReadingElectricityNetUtc - 600000):
                                            wattsExported = self.solarExportedLast * 12
                                        else:
                                            wattsExported = 0.0
                                else:  # Assume last

                                    self.generalLogger.debug(
                                        u"USAGESAVING: CL=[%s], UTCL=[%s], LRUTC=[%s], LRUTC600=[%s]" % (
                                            self.solarExportedLast, self.timestampUtcLast,
                                            self.lastReadingSolarExportedUtc,
                                            (self.lastReadingSolarExportedUtc - 600000)))

                                    if self.solarExportedLast > 0.0 and self.timestampUtcLast != 0 and self.timestampUtcLast > (
                                            self.lastReadingSolarExportedUtc - 600000):
                                        wattsExported = self.solarExportedLast * 12
                                    else:
                                        wattsExported = 0.0

                                if wattsExported == 0.0:
                                    wattsExported = self.solarExportedPrevious

                                wattsExportedStr = "%d Watts" % wattsExported
                                if not self.globals['smappees'][devSolarExported.id][
                                        'hideSolarExportedMeterCurGeneration']:
                                    if wattsExported == 0.0 and self.globals['smappees'][devSolarExported.id][
                                            'hideZeroSolarExportedMeterCurGeneration']:
                                        pass
                                    else:
                                        self.generalLogger.info(u"received '%s' solar energy exported reading: %s" % (
                                            devSolarExported.name, wattsExportedStr))
                                devSolarExported.updateStateOnServer("curEnergyLevel", wattsExported,
                                                                     uiValue=wattsExportedStr)
                                if float(indigo.server.apiVersion) >= 1.18:
                                    devSolarExported.updateStateImageOnServer(indigo.kStateImageSel.EnergyMeterOn)

                                if self.solar > 0.00:
                                    exportedPercentage = int(round((self.solarExported / self.solar) * 100))
                                else:
                                    exportedPercentage = int(0)
                                exportedPercentageStr = "%d %%" % exportedPercentage
                                devSolarExported.updateStateOnServer("kwhCurrentExportedPercentage", exportedPercentage,
                                                                     uiValue=exportedPercentageStr)

                            if "accumEnergyTotal" in devSolarExported.states:
                                if commandSentToSmappee == 'RESET_CONSUMPTION':
                                    self.globals['smappees'][devSolarExported.id]['accumEnergyTotal'] = 0.0
                                    kwhExportedStr = "%3.0f kWh" % (
                                        self.globals['smappees'][devSolarExported.id]['accumEnergyTotal'])
                                    devSolarExported.updateStateOnServer("accumEnergyTotal",
                                                                         self.globals['smappees'][devSolarExported.id][
                                                                             'accumEnergyTotal'],
                                                                         uiValue=kwhExportedStr)

                                # kwhExported = float(devSolarExported.states.get("accumEnergyTotal", 0))
                                # kwhExported += float(self.solarExportedTotal / 1000.0)
                                kwhExportedStr = str(
                                    "%0.3f kWh" % kwhExported)  # Calculated in solar device - 'kwhExported'
                                kwhExportedReformatted = float("%0.3f" % kwhExported)

                                if not self.globals['smappees'][devSolarExported.id][
                                        'hideSolarExportedMeterAccumGeneration']:
                                    if self.globals['smappees'][devSolarExported.id][
                                            'hideNoChangeInSolarExportedMeterAccumGeneration'] and kwhExportedReformatted == float(
                                            devSolarExported.states['accumEnergyTotal']) and wattsExported == 0.0:
                                        pass
                                    else:
                                        self.generalLogger.info(u"received '%s' solar energy exported total: %s" % (
                                            devSolarExported.name, kwhExportedStr))

                                devSolarExported.updateStateOnServer("accumEnergyTotal", kwhExportedReformatted,
                                                                     uiValue=kwhExportedStr)

                                if "accumEnergyTotal" in devSolar.states:
                                    # Needed to caculate total exported percentage - uses 'kwhSolar'

                                    if kwhSolar > 0.00:
                                        exportedDailyPercentage = int(round((kwhExported / kwhSolar) * 100))
                                    else:
                                        exportedDailyPercentage = int(0)
                                    exportedDailyPercentageStr = "%d %%" % exportedDailyPercentage
                                    devSolarExported.updateStateOnServer("kwhDailyTotalExportedPercentage",
                                                                         exportedDailyPercentage,
                                                                         uiValue=exportedDailyPercentageStr)

                                amountExportedReformatted = float(str("%0.2f" % amountExported))
                                amountExportedStr = str("%0.2f %s" % (
                                    amountExported, self.globals['smappees'][devSolar.id]['currencyCode']))
                                devSolarExported.updateStateOnServer("dailyTotalExportOnlyIncome",
                                                                     amountExportedReformatted,
                                                                     uiValue=amountExportedStr)

                            self.globals['smappees'][devSolarExported.id][
                                'lastReadingSolarExportedUtc'] = self.timestampUtc

                    elif key == 'error':
                        self.generalLogger.error(u"SMAPPEE ERROR DETECTED [%s]: %s" % (commandSentToSmappee, value))
                    else:
                        pass  # Unknown key/value pair
                        self.generalLogger.debug(u"Unhandled key/value pair : K=[%s], V=[%s]" % (key, value))

        except StandardError, e:
            self.generalLogger.error(u"StandardError detected in 'handleGetConsumption'. Line '%s' has error='%s'" % (
                sys.exc_traceback.tb_lineno, e))
            self.generalLogger.error(u"Decoded response from Smappee was:'%s'" % decodedSmappeeResponse)

    def handleGetSensorConsumption(self, commandSentToSmappee, responseLocationId, decodedSmappeeResponse):
        self.methodTracer.threaddebug(u"CLASS: Plugin")

        # return  # TEMP FIX

        self.generalLogger.debug(u"handleGetSensorConsumption [AC-FIXED] - Decoded Response to '%s' = [%s] %s" % (
            commandSentToSmappee, responseLocationId, decodedSmappeeResponse))

        try:

            for decoding in decodedSmappeeResponse:

                errorDetected = False
                for key, value in decoding.iteritems():
                    if key == 'serviceLocationId' or key == 'sensorId' or key == 'records' or key == 'error':
                        if key == 'error':
                            self.generalLogger.debug(
                                u"SMAPPEE SENSOR handleGetSensorConsumption error detected by Smappee: Error=[%s]" % (
                                    value))
                            errorDetected = True
                        # At this point the response (so far) is OK as we know how to process the key
                    else:
                        self.generalLogger.debug(
                            u"SMAPPEE SENSOR Unhandled key/value pair : K=[%s], V=[%s]" % (key, value))
                if errorDetected:
                    self.generalLogger.error(u"SMAPPEE SENSOR handleGetSensorConsumption error - response abandoned!")
                    break

                for key, value in decoding.iteritems():
                    if key == 'serviceLocationId':
                        sLoc = str(value)  # Service Location
                        self.generalLogger.debug(
                            u"handleGetSensorConsumption [serviceLocationId] - K = [%s], V = %s and sLoc = %s" % (
                                key, value, sLoc))
                        break

                for key, value in decoding.iteritems():
                    if key == 'sensorId':
                        smappeeType = 'GW'  # Sensor for Gas Water
                        sId = str("%s%s" % (str(smappeeType), str("00%s" % value)[-2:]))
                        self.generalLogger.debug(u"handleGetSensorConsumption [sensorId] - sId = [%s]" % sId)

                        def checkIndigoDev(serviceLocation, address):
                            try:
                                # self.generalLogger.debug(u"handleGetSensorConsumption [sensorId-checkIndigoDev] - serviceLocation=[%s] %s, Smappee Address=[%s] %s" % (type(serviceLocation), serviceLocation, type(address), address))
                                returnedDevId = 0
                                # lastReadingSensorUtc = time.mktime(indigo.server.getTime().timetuple())  # Make greater than 'now' so that if no device exists - nothing will be processed
                                lastReadingSensorUtc = 0
                                pulsesPerUnit = 1  # Default
                                measurementTimeMultiplier = 1.0

                                for dev in indigo.devices.iter("self"):
                                    # self.generalLogger.debug(u"handleGetSensorConsumption [sensorId-checkIndigoDev] - DN=%s, deviceTypeId=[%s] %s, serviceLocation=[%s] %s, deviceAddress=[%s] %s" % (dev.name, type(dev.deviceTypeId), dev.deviceTypeId, type(dev.pluginProps['serviceLocationId']), dev.pluginProps['serviceLocationId'], type(dev.address), dev.address))
                                    if (dev.deviceTypeId == "smappeeSensor") and (
                                            dev.pluginProps['serviceLocationId'] == serviceLocation) and (
                                            dev.address == address):
                                        self.generalLogger.debug(
                                            u"handleGetSensorConsumption [sensorId-checkIndigoDev- FOUND] DN = [%s], TYPEID =  [%s], SL=[%s], A=[%s]" % (
                                                dev.name, dev.deviceTypeId, dev.pluginProps['serviceLocationId'],
                                                dev.address))
                                        returnedDevId = dev.id
                                        lastReadingSensorUtc = self.globals['smappees'][dev.id]['lastReadingSensorUtc']
                                        pulsesPerUnit = self.globals['smappees'][dev.id]['lastReadingSensorUtc']

                                        unitsKey = self.globals['smappees'][dev.id]['units']
                                        if unitsKey in self.globals['unitTable']:
                                            pass
                                        else:
                                            unitsKey = 'default'
                                        measurementTimeMultiplier = self.globals['unitTable'][unitsKey][
                                            'measurementTimeMultiplier']

                                        if not dev.states['smappeeSensorOnline']:
                                            dev.updateStateOnServer("smappeeSensorOnline", True, uiValue='online')

                                return returnedDevId, lastReadingSensorUtc, pulsesPerUnit, measurementTimeMultiplier

                            except StandardError, e:
                                self.generalLogger.error(
                                    u"StandardError detected in 'checkIndigoDev'. Line '%s' has error='%s'" % (
                                        sys.exc_traceback.tb_lineno, e))

                                return returnedDevId, lastReadingSensorUtc, pulsesPerUnit, measurementTimeMultiplier

                        sensorAddress = sId + '-A'
                        sensorA_DevId, lastReadingSensorA_Utc, pulsesPerUnitSensorA, measurementTimeMultiplierSensorA = checkIndigoDev(
                            sLoc, sensorAddress)
                        sensorAddress = sId + '-B'
                        sensorB_DevId, lastReadingSensorB_Utc, pulsesPerUnitSensorB, measurementTimeMultiplierSensorB = checkIndigoDev(
                            sLoc, sensorAddress)

                        self.generalLogger.debug(
                            u"handleGetSensorConsumption [sensorId-checkIndigoDev] - dev.Id [A] = [%s], dev.Id [B] = [%s]" % (
                                sensorA_DevId, sensorB_DevId))

                        break

                for key, value in decoding.iteritems():
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

                        if self.globals['SQL']['enabled']:
                            try:
                                self.globals['SQL']['connection'] = sql3.connect(self.globals['SQL']['db'])
                                self.globals['SQL']['cursor'] = self.globals['SQL']['connection'].cursor()
                            except sql3.Error, e:
                                if self.globals['SQL']['connection']:
                                    self.globals['SQL']['connection'].rollback()
                                self.generalLogger.error(
                                    u"SMAPPEE ERROR DETECTED WITH SQL [SENSOR] CONNECTION: %s" % (e.args[0]))

                                self.globals['SQL']['enabled'] = False  # Disable SQL processing

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

                            self.generalLogger.debug(u"handleGetSensorConsumption [Q][SENSOR] -  [START ...]")

                            for readingKey, readingValue in self.sensorReading.iteritems():
                                self.generalLogger.debug(
                                    u"handleGetSensorConsumption [Q][SENSOR] -  [%s : %s]" % (readingKey, readingValue))
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
                            self.generalLogger.debug(
                                u"handleGetSensorConsumption [Q][SENSOR] -  [... END: TS=%s, V1=%s, V2=%s, TEMP=%s, HUM=%s, BAT=%s]" % (
                                    timestampUtc, value1, value2, temperature, humidity, batteryLevel))

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

                                self.generalLogger.debug(
                                    u"handleGetSensorConsumption [Q][SENSOR] -  [... SQL: TS=%s, V1=%s, V2=%s, TEMP=%s, HUM=%s, BAT=%s]" % (
                                        timestampUtc, value1, value2, temperature, humidity, batteryLevel))

                                if self.globals['SQL']['enabled']:

                                    try:
                                        insertSql = 'NO SQL SET-UP YET'
                                        readingTime = str(int(timestampUtc / 1000))  # Remove micro seconds
                                        readingYYYYMMDDHHMMSS = datetime.datetime.fromtimestamp(
                                            int(readingTime)).strftime('%Y-%m-%d %H:%M:%S')
                                        readingYYYYMMDD = readingYYYYMMDDHHMMSS[0:10]
                                        readingHHMMSS = readingYYYYMMDDHHMMSS[-8:]
                                        sensor1 = str(int(value1))
                                        sensor2 = str(int(value2))
                                        humidity = str(int(humidity * 10))
                                        temperature = str(int(temperature * 10))
                                        battery = str(int(batteryLevel * 10))

                                        self.generalLogger.debug(
                                            u"handleGetSensorConsumption [Q][SENSOR] -  [... INS: RT=%s, YYYYMMDD=%s, HHMMSS=%s, V1=%s, V2=%s, TEMP=%s, HUM=%s, BAT=%s]" % (
                                                readingTime, readingYYYYMMDDHHMMSS, readingHHMMSS, sensor1, sensor2,
                                                temperature, humidity, battery))

                                        insertSql = """
                                            INSERT OR REPLACE INTO sensor_readings (reading_time, reading_YYYYMMDD, reading_HHMMSS, sensor1, sensor2, humidity, temperature, battery)
                                            VALUES (%s, '%s', '%s', %s, %s, %s, %s, %s);
                                            """ % (
                                            readingTime, readingYYYYMMDD, readingHHMMSS, sensor1, sensor2, humidity,
                                            temperature, battery)
                                        self.globals['SQL']['cursor'].executescript(insertSql)
                                    except sql3.Error, e:
                                        if self.globals['SQL']['connection']:
                                            self.globals['SQL']['connection'].rollback()
                                        self.generalLogger.error(
                                            u"SMAPPEE ERROR DETECTED WITH SQL [SENSOR] INSERT: %s, SQL=[%s]" % (
                                                e.args[0], insertSql))
                                        if self.globals['SQL']['connection']:
                                            self.globals['SQL']['connection'].close()

                                        self.globals['SQL']['enabled'] = False  # Disable SQL processing

                        if self.globals['SQL']['enabled']:
                            try:
                                self.globals['SQL']['connection'].commit()
                            except sql3.Error, e:
                                if self.globals['SQL']['connection']:
                                    self.globals['SQL']['connection'].rollback()
                                self.generalLogger.error(
                                    u"SMAPPEE ERROR DETECTED WITH SQL [SENSOR] COMMIT: %s" % (e.args[0]))

                                self.globals['SQL']['enabled'] = False  # Disable SQL processing
                            finally:
                                if self.globals['SQL']['connection']:
                                    self.globals['SQL']['connection'].close()

                                    # reading 'records' entries processing complete

                        if sensorA_NumberOfValues > 0:
                            sensorA_MeanAverage = sensorA_Total / sensorA_NumberOfValues

                        self.generalLogger.debug(
                            u"READINGS - SENSOR [A]: N=[%s], T=[%s], MEAN=[%s], MIN=[%s], MAX=[%s], L=[%s]"
                            % (sensorA_NumberOfValues, sensorA_Total, sensorA_MeanAverage, sensorA_Minimum,
                               sensorA_Maximum, sensorA_Last))

                        if sensorB_NumberOfValues > 0:
                            sensorB_MeanAverage = sensorB_Total / sensorB_NumberOfValues

                        self.generalLogger.debug(
                            u"READINGS - SENSOR [B]: N=[%s], T=[%s], MEAN=[%s], MIN=[%s], MAX=[%s], L=[%s]"
                            % (sensorB_NumberOfValues, sensorB_Total, sensorB_MeanAverage, sensorB_Minimum,
                               sensorB_Maximum, sensorB_Last))

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

                                self.generalLogger.debug(
                                    u"UpdateSensor [1 of 2] [%s]: Temp=%s, Humidity=%s, Battery=%s" % (
                                        sensorDesc, sensorTemperature, sensorHumidity, sensorBatteryLevel))
                                self.generalLogger.debug(
                                    u"UpdateSensor [2 of 2] [%s]: Total=%s, NoV=%s, Mean=%s, Min=%s, Max=%s, Prev=%s, Last=%s" % (
                                        sensorDesc, str(sensorTotal), str(sensorNumberOfValues), str(sensorMeanAverage),
                                        str(sensorMinimum), str(sensorMaximum), str(sensorPrevious), str(sensorLast)))

                                if (sensorNumberOfValues == 0) and ("curEnergyLevel" in sensorDev.states) and (
                                        sensorDev.states['curEnergyLevel'] == 0.0):
                                    self.generalLogger.debug(u"UpdateSensor [RETURNING, NO UPDATE] [%s]" % sensorDesc)

                                    return  # Don't update energy totals if no values to process i.e nothing received since last timestamp

                                updateTimeString = datetime.datetime.fromtimestamp(
                                    int(timestampUtcLast / 1000)).strftime('%Y-%b-%d %H:%M')

                                if "readingsLastUpdated" in sensorDev.states:
                                    sensorDev.updateStateOnServer("readingsLastUpdated", updateTimeString)

                                if sensorTemperature != self.globals['smappees'][sensorDev.id]['temperature']:
                                    if "temperature" in sensorDev.states:
                                        self.globals['smappees'][sensorDev.id]['temperature'] = float(sensorTemperature)
                                        temperatureStr = "%1.0f deg C" % (float(sensorTemperature) / 10)
                                        temperatureReformatted = float("%0.1f" % (float(sensorTemperature) / 10))
                                        sensorDev.updateStateOnServer("temperature", temperatureReformatted,
                                                                      uiValue=temperatureStr)

                                        if "temperatureLastUpdated" in sensorDev.states:
                                            sensorDev.updateStateOnServer("temperatureLastUpdated", updateTimeString)

                                if sensorHumidity != self.globals['smappees'][sensorDev.id]['humidity']:
                                    if "humidity" in sensorDev.states:
                                        self.globals['smappees'][sensorDev.id]['humidity'] = float(sensorHumidity)
                                        humidityStr = "%1.0f%%" % (float(sensorHumidity))
                                        humidityReformatted = float("%0.1f" % (float(sensorHumidity)))
                                        sensorDev.updateStateOnServer("humidity", humidityReformatted,
                                                                      uiValue=humidityStr)

                                        if "humidityLastUpdated" in sensorDev.states:
                                            sensorDev.updateStateOnServer("humidityLastUpdated", updateTimeString)

                                if sensorBatteryLevel != self.globals['smappees'][sensorDev.id]['batteryLevel']:
                                    if "batteryLevel" in sensorDev.states:
                                        self.globals['smappees'][sensorDev.id]['batteryLevel'] = float(
                                            sensorBatteryLevel)
                                        batteryLevelStr = "%1.0f%%" % (float(sensorBatteryLevel))
                                        batteryLevelReformatted = float("%0.1f" % (float(sensorBatteryLevel)))
                                        sensorDev.updateStateOnServer("batteryLevel", batteryLevelReformatted,
                                                                      uiValue=batteryLevelStr)

                                        if "batteryLevelLastUpdated" in sensorDev.states:
                                            sensorDev.updateStateOnServer("batteryLevelLastUpdated", updateTimeString)

                                unitsKey = self.globals['smappees'][sensorDev.id]['units']
                                if unitsKey in self.globals['unitTable']:
                                    pass
                                else:
                                    unitsKey = 'default'

                                unitsCurrentUnits = self.globals['unitTable'][unitsKey]['currentUnits']
                                unitsAccumUnits = self.globals['unitTable'][unitsKey]['accumUnits']
                                unitsmeasurementTimeMultiplier = self.globals['unitTable'][unitsKey][
                                    'measurementTimeMultiplier']
                                unitsformatTotaldivisor = self.globals['unitTable'][unitsKey]['formatTotaldivisor']
                                unitsformatCurrent = self.globals['unitTable'][unitsKey]['formatCurrent']
                                unitsformatCurrentUi = unitsformatCurrent + u' ' + unitsCurrentUnits
                                unitsformatTotal = self.globals['unitTable'][unitsKey]['formatTotal']
                                unitsformatTotalUi = unitsformatTotal + ' ' + unitsAccumUnits

                                if "curEnergyLevel" in sensorDev.states:
                                    if commandSentToSmappee == 'RESET_SENSOR_CONSUMPTION':
                                        self.globals['smappees'][sensorDev.id]['curEnergyLevel'] = 0.0
                                        dataToUpdateStr = str(unitsformatCurrent + " %s %s" % (
                                            self.globals['smappees'][sensorDev.id]['curEnergyLevel'],
                                            unitsCurrentUnits))
                                        sensorDev.updateStateOnServer("curEnergyLevel",
                                                                      self.globals['smappees'][sensorDev.id][
                                                                          'curEnergyLevel'], uiValue=dataToUpdateStr)
                                        if float(indigo.server.apiVersion) >= 1.18:
                                            sensorDev.updateStateImageOnServer(indigo.kStateImageSel.EnergyMeterOff)

                                    readingOption = sensorDev.pluginProps[
                                        'optionsEnergyMeterCurPower']  # mean, minimum, maximum, last

                                    dataToUpdate = 0.0
                                    if readingOption == 'mean':  # mean, minimum, maximum, last
                                        if sensorNumberOfValues > 0:
                                            dataToUpdate = (sensorMeanAverage * 60) / 5
                                        else:
                                            self.generalLogger.debug(
                                                u"SENSOR %s: [MEAN] CL=[%s], UTCL=[%s], LRUTC=[%s], LRUTC600=[%s]" % (
                                                    sensorDesc, sensorLast, timestampUtcLast, lastReadingUtc,
                                                    (lastReadingUtc - 600000)))
                                            if sensorLast > 0.0 and timestampUtcLast != 0 and timestampUtcLast > (
                                                    lastReadingUtc - 600000):
                                                dataToUpdate = sensorLast * unitsmeasurementTimeMultiplier
                                    elif readingOption == 'minimum':
                                        if sensorNumberOfValues > 0:
                                            dataToUpdate = sensorMinimum * unitsmeasurementTimeMultiplier
                                        else:
                                            self.generalLogger.debug(
                                                u"SENSOR %s: [MINIMUM] CL=[%s], UTCL=[%s], LRUTC=[%s], LRUTC600=[%s]" % (
                                                    sensorDesc, sensorLast, timestampUtcLast, lastReadingUtc,
                                                    (lastReadingUtc - 600000)))
                                            if sensorLast > 0.0 and timestampUtcLast != 0 and timestampUtcLast > (
                                                    lastReadingUtc - 600000):
                                                dataToUpdate = sensorLast * unitsmeasurementTimeMultiplier
                                    elif readingOption == 'maximum':
                                        if sensorNumberOfValues > 0:
                                            watts = sensorMaximum * unitsmeasurementTimeMultiplier
                                        else:
                                            self.generalLogger.debug(
                                                u"SENSOR %s: [MAXIMUM] CL=[%s], UTCL=[%s], LRUTC=[%s], LRUTC600=[%s]" % (
                                                    sensorDesc, sensorLast, timestampUtcLast, lastReadingUtc,
                                                    (lastReadingUtc - 600000)))
                                            if sensorLast > 0.0 and timestampUtcLast != 0 and timestampUtcLast > (
                                                    lastReadingUtc - 600000):
                                                dataToUpdate = sensorLast * unitsmeasurementTimeMultiplier
                                    else:  # Assume last
                                        self.generalLogger.debug(
                                            u"SENSOR %s: [LAST] CL=[%s], UTCL=[%s], LRUTC=[%s], LRUTC600=[%s]" % (
                                                sensorDesc, sensorLast, str(timestampUtcLast), str(lastReadingUtc),
                                                (str(lastReadingUtc - 600000))))
                                        if sensorLast > 0.0 and timestampUtcLast != 0 and timestampUtcLast > (
                                                lastReadingUtc - 600000):
                                            dataToUpdate = sensorLast * unitsmeasurementTimeMultiplier

                                    currentTimeUtc = int(time.mktime(indigo.server.getTime().timetuple()))
                                    currentTimeMinus6MinsUtc = int(
                                        (currentTimeUtc - 360) * 1000)  # Subtract 5 minutes (360 seconds)

                                    self.generalLogger.debug(
                                        u"SENSOR %s: [TIME CHECK] currentTimeUtc=[%s], currentTimeMinus6MinsUtc=[%s], timestampUtcLast=[%s]" % (
                                            sensorDesc, currentTimeUtc, currentTimeMinus6MinsUtc, timestampUtcLast))
                                    if timestampUtcLast < currentTimeMinus6MinsUtc:
                                        dataToUpdate = 0.0

                                    dataToUpdateStr = u"%d %s" % (dataToUpdate, unitsCurrentUnits)
                                    if not self.globals['smappees'][sensorDev.id]['hideEnergyMeterCurPower']:
                                        self.generalLogger.info(
                                            u"received '%s' power load reading: %s" % (sensorDev.name, dataToUpdateStr))

                                    sensorDev.updateStateOnServer("curEnergyLevel", dataToUpdate,
                                                                  uiValue=dataToUpdateStr)
                                    if float(indigo.server.apiVersion) >= 1.18:
                                        sensorDev.updateStateImageOnServer(indigo.kStateImageSel.EnergyMeterOn)

                                if sensorNumberOfValues != 0 and "accumEnergyTotal" in sensorDev.states:

                                    if commandSentToSmappee == 'RESET_SENSOR_CONSUMPTION':
                                        self.globals['smappees'][sensorDev.id]['accumEnergyTotal'] = 0.0
                                        dataToUpdateStr = str(unitsformatTotalUi % (
                                            self.globals['smappees'][sensorDev.id]['accumEnergyTotal']))
                                        sensorDev.updateStateOnServer("accumEnergyTotal",
                                                                      self.globals['smappees'][sensorDev.id][
                                                                          'accumEnergyTotal'], uiValue=dataToUpdateStr)

                                    dataToUpdate = float(sensorDev.states.get("accumEnergyTotal", 0))
                                    dataToUpdate += float(sensorTotal / unitsformatTotaldivisor)
                                    dataToUpdateStr = str(unitsformatTotalUi % dataToUpdate)
                                    dataToUpdateReformatted = str(unitsformatTotal % dataToUpdate)
                                    sensorDev.updateStateOnServer("accumEnergyTotal", dataToUpdateReformatted,
                                                                  uiValue=dataToUpdateStr)

                                    dataUnitCost = self.globals['smappees'][sensorDev.id]['unitCost']
                                    dailyStandingCharge = self.globals['smappees'][sensorDev.id]['dailyStandingCharge']
                                    amountGross = 0.00
                                    if dataUnitCost > 0.00:
                                        amountGross = (dailyStandingCharge + (dataToUpdate * dataUnitCost))
                                        amountGrossReformatted = float(str("%0.2f" % amountGross))
                                        amountGrossStr = str("%0.2f %s" % (
                                            amountGrossReformatted,
                                            self.globals['smappees'][sensorDev.id]['currencyCode']))
                                        sensorDev.updateStateOnServer("dailyTotalCost", amountGrossReformatted,
                                                                      uiValue=amountGrossStr)

                                    if not self.globals['smappees'][sensorDev.id]['hideEnergyMeterAccumPower']:
                                        if dataUnitCost == 0.00 or self.globals['smappees'][sensorDev.id][
                                                'hideEnergyMeterAccumPowerCost']:
                                            self.generalLogger.info(
                                                u"received '%s' energy total: %s" % (sensorDev.name, dataToUpdateStr))
                                        else:
                                            self.generalLogger.info(u"received '%s' energy total: %s (Gross %s)" % (
                                                sensorDev.name, dataToUpdateStr, amountGrossStr))

                                self.globals['smappees'][sensorDev.id]['lastReadingSensorUtc'] = timestampUtc

                            except StandardError, e:
                                self.generalLogger.error(
                                    u"StandardError detected in 'updateSensor'. Line '%s' has error='%s'" % (
                                        sys.exc_traceback.tb_lineno, e))

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

        except StandardError, e:
            self.generalLogger.error(
                u"StandardError detected in 'handleGetSensorConsumption'. Line '%s' has error='%s'" % (
                    sys.exc_traceback.tb_lineno, e))
            self.generalLogger.error(u"Decoded response from Smappee was:'%s'" % decodedSmappeeResponse)

    def handleSmappeeResponse(self, commandSentToSmappee, responseLocationId, responseFromSmappee):
        self.methodTracer.threaddebug(u"CLASS: Plugin")

        # This thread handles responses from Smappee to commands sent to Smappee

        self.currentTime = indigo.server.getTime()

        try:
            # First check for internal calls not involving an external communication with the Smappee
            if commandSentToSmappee == 'NEW_SENSOR':
                # SPECIAL CASE - NOT ACTUALLY A RESPONSE FROM SMAPPEE
                self.handleCreateNewSensor(commandSentToSmappee, responseLocationId, responseFromSmappee)
                return
            if commandSentToSmappee == 'NEW_APPLIANCE':
                # SPECIAL CASE - NOT ACTUALLY A RESPONSE FROM SMAPPEE
                self.handleCreateNewAppliance(commandSentToSmappee, responseLocationId, responseFromSmappee)
                return
            if commandSentToSmappee == 'NEW_ACTUATOR':
                # SPECIAL CASE - NOT ACTUALLY A RESPONSE FROM SMAPPEE
                self.handleCreateNewActuator(commandSentToSmappee, responseLocationId, responseFromSmappee)
                return

            # Now do some basic validation on the Smappee response and decode it

            validSmappeeResponse, decodedSmappeeResponse = self.validateSmappeResponse(commandSentToSmappee,
                                                                                       responseLocationId,
                                                                                       responseFromSmappee)
            if not validSmappeeResponse:
                # Response received from Smappee is invalid
                return

            # At this point we have a decoded response
            if commandSentToSmappee == 'GET_EVENTS':
                self.handleGetEvents(responseLocationId, decodedSmappeeResponse)
                return

            if commandSentToSmappee == 'INITIALISE' or commandSentToSmappee == 'REFRESH_TOKEN':
                self.handleInitialise(commandSentToSmappee, responseLocationId, decodedSmappeeResponse)
                return

            if commandSentToSmappee == 'GET_SERVICE_LOCATIONS':
                self.handleGetServiceLocations(responseLocationId, decodedSmappeeResponse)
                return

            if commandSentToSmappee == 'GET_SERVICE_LOCATION_INFO':
                self.handleGetServiceLocationInfo(responseLocationId, decodedSmappeeResponse)
                return

            if commandSentToSmappee == 'GET_CONSUMPTION' or commandSentToSmappee == 'RESET_CONSUMPTION':
                self.handleGetConsumption(commandSentToSmappee, responseLocationId, decodedSmappeeResponse)
                return

            if commandSentToSmappee == 'GET_SENSOR_CONSUMPTION' or commandSentToSmappee == 'RESET_SENSOR_CONSUMPTION':
                self.handleGetSensorConsumption(commandSentToSmappee, responseLocationId, decodedSmappeeResponse)
                return

        except StandardError, e:
            self.generalLogger.error(u"StandardError detected in 'handleSmappeeResponse'. Line '%s' has error='%s'" % (
                sys.exc_traceback.tb_lineno, e))
            self.generalLogger.error(u"Response from Smappee was:'%s'" % responseFromSmappee)

    def setSmappeeServiceLocationIdToDevId(self, function, smappeeDeviceTypeId, serviceLocationId, devId,
                                           smappeeAddress, devName):

        # self.setSmappeeServiceLocationIdToDevId('ADD_UPDATE', 'smappeeSensor', responseLocationId, 0, sensorId, sensorName)

        self.methodTracer.threaddebug(u"CLASS: Plugin")

        try:

            if serviceLocationId == "" or serviceLocationId == "NONE":
                return

            if serviceLocationId not in self.globals['smappeeServiceLocationIdToDevId']:
                self.globals['smappeeServiceLocationIdToDevId'] = {}
                self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId] = {}
                self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId]['name'] = "HOME-HOME"
                self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId]['electricityId'] = 0
                self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId]['solarId'] = 0
                self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId]['electricityNetId'] = 0
                self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId]['electricitySavedId'] = 0
                self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId]['solarExportedId'] = 0
                self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId]['sensorIds'] = {}
                self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId]['applianceIds'] = {}
                self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId]['actuatorIds'] = {}

            smappeeAddress = str(smappeeAddress)
            if function == 'ADD_UPDATE':
                if smappeeDeviceTypeId == 'smappeeElectricity':
                    self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId]['electricityId'] = devId
                elif smappeeDeviceTypeId == 'smappeeElectricityNet':
                    self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId]['electricityNetId'] = devId
                elif smappeeDeviceTypeId == 'smappeeElectricitySaved':
                    self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId]['electricitySavedId'] = devId
                elif smappeeDeviceTypeId == 'smappeeSolar':
                    self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId]['solarId'] = devId
                elif smappeeDeviceTypeId == 'smappeeSolarUsed':
                    self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId]['solarUsedId'] = devId
                elif smappeeDeviceTypeId == 'smappeeSolarExported':
                    self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId]['solarExportedId'] = devId
                elif smappeeDeviceTypeId == 'smappeeSensor':
                    if smappeeAddress not in self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId][
                            'sensorIds']:
                        self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId]['sensorIds'][
                            smappeeAddress] = {}
                        self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId]['sensorIds'][smappeeAddress][
                            'queued-add'] = False
                        self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId]['sensorIds'][smappeeAddress][
                            'queued-remove'] = False
                        self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId]['sensorIds'][smappeeAddress][
                            'devId'] = 0
                    if self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId]['sensorIds'][smappeeAddress][
                            'devId'] == 0:
                        self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId]['sensorIds'][smappeeAddress][
                            'devId'] = devId
                    self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId]['sensorIds'][smappeeAddress][
                        'name'] = str(devName)
                    self.generalLogger.debug(u"setSmappeeServiceLocationIdToDevId [FF-E][SENSOR] - [%s]" % (
                        self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId]['sensorIds']))
                elif smappeeDeviceTypeId == 'smappeeAppliance':
                    if smappeeAddress not in self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId][
                            'applianceIds']:
                        self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId]['applianceIds'][
                            smappeeAddress] = {}
                        self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId]['applianceIds'][
                            smappeeAddress]['queued-add'] = False
                        self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId]['applianceIds'][
                            smappeeAddress]['queued-remove'] = False
                    self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId]['applianceIds'][smappeeAddress][
                        'devId'] = devId
                    self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId]['applianceIds'][smappeeAddress][
                        'name'] = str(devName)
                elif smappeeDeviceTypeId == 'smappeeActuator':
                    if smappeeAddress not in self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId][
                            'actuatorIds']:
                        self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId]['actuatorIds'][
                            smappeeAddress] = {}
                        self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId]['actuatorIds'][
                            smappeeAddress]['queued-add'] = False
                        self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId]['actuatorIds'][
                            smappeeAddress]['queued-remove'] = False
                    self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId]['actuatorIds'][smappeeAddress][
                        'devId'] = devId
                    self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId]['actuatorIds'][smappeeAddress][
                        'name'] = str(devName)

            elif function == 'STOP':
                if smappeeDeviceTypeId == 'smappeeElectricity':
                    self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId]['electricityId'] = 0
                elif smappeeDeviceTypeId == 'smappeeElectricityNet':
                    self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId]['electricityNetId'] = 0
                elif smappeeDeviceTypeId == 'smappeeElectricitySaved':
                    self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId]['electricitySavedId'] = 0
                elif smappeeDeviceTypeId == 'smappeeSolar':
                    self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId]['solarId'] = 0
                elif smappeeDeviceTypeId == 'smappeeSolarUsed':
                    self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId]['solarUsedId'] = 0
                elif smappeeDeviceTypeId == 'smappeeSolarExported':
                    self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId]['solarExportedId'] = 0
                elif smappeeDeviceTypeId == 'smappeeSensor':
                    self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId]['sensorIds'][smappeeAddress][
                        'queued-add'] = False
                    self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId]['sensorIds'][smappeeAddress][
                        'queued-remove'] = False
                    self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId]['sensorIds'][smappeeAddress][
                        'devId'] = 0
                elif smappeeDeviceTypeId == 'smappeeAppliance':
                    self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId]['applianceIds'][smappeeAddress][
                        'devId'] = 0
                elif smappeeDeviceTypeId == 'smappeeActuator':
                    self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId]['actuatorIds'][smappeeAddress][
                        'devId'] = 0

            elif function == 'QUEUE-ADD':
                if smappeeDeviceTypeId == 'smappeeSensor':
                    if smappeeAddress not in self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId][
                            'sensorIds']:
                        self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId]['applianceIds'][
                            smappeeAddress] = {}
                    self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId]['sensorIds'][smappeeAddress][
                        'devId'] = 0
                    self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId]['sensorIds'][smappeeAddress][
                        'name'] = str(devName)
                    self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId]['sensorIds'][smappeeAddress][
                        'deviceType'] = str(smappeeDeviceTypeId)
                    self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId]['sensorIds'][smappeeAddress][
                        'queued-add'] = True
                elif smappeeDeviceTypeId == 'smappeeAppliance':
                    if smappeeAddress not in self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId][
                            'applianceIds']:
                        self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId]['applianceIds'][
                            smappeeAddress] = {}
                    self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId]['applianceIds'][smappeeAddress][
                        'devId'] = 0
                    self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId]['applianceIds'][smappeeAddress][
                        'name'] = str(devName)
                    self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId]['applianceIds'][smappeeAddress][
                        'queued-add'] = True
                elif smappeeDeviceTypeId == 'smappeeActuator':
                    if smappeeAddress not in self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId][
                            'actuatorIds']:
                        self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId]['actuatorIds'][
                            smappeeAddress] = {}
                    self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId]['actuatorIds'][smappeeAddress][
                        'devId'] = 0
                    self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId]['actuatorIds'][smappeeAddress][
                        'name'] = str(devName)
                    self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId]['actuatorIds'][smappeeAddress][
                        'queued-add'] = True

            elif function == 'DEQUEUE':
                if smappeeDeviceTypeId == 'smappeeSensor':
                    if smappeeAddress not in self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId][
                            'sensorIds']:
                        self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId]['sensorIds'][
                            smappeeAddress] = {}
                    self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId]['sensorIds'][smappeeAddress][
                        'devId'] = devId
                    self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId]['sensorIds'][smappeeAddress][
                        'name'] = str(devName)
                    self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId]['sensorIds'][smappeeAddress][
                        'queued-add'] = False
                    self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId]['sensorIds'][smappeeAddress][
                        'queued-remove'] = False
                elif smappeeDeviceTypeId == 'smappeeAppliance':
                    if smappeeAddress not in self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId][
                            'applianceIds']:
                        self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId]['applianceIds'][
                            smappeeAddress] = {}
                    self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId]['applianceIds'][smappeeAddress][
                        'devId'] = devId
                    self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId]['applianceIds'][smappeeAddress][
                        'name'] = str(devName)
                    self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId]['applianceIds'][smappeeAddress][
                        'queued-add'] = False
                    self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId]['applianceIds'][smappeeAddress][
                        'queued-remove'] = False
                elif smappeeDeviceTypeId == 'smappeeActuator':
                    if smappeeAddress not in self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId][
                            'actuatorIds']:
                        self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId]['actuatorIds'][
                            smappeeAddress] = {}
                    self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId]['actuatorIds'][smappeeAddress][
                        'devId'] = devId
                    self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId]['actuatorIds'][smappeeAddress][
                        'name'] = str(devName)
                    self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId]['actuatorIds'][smappeeAddress][
                        'queued-add'] = False
                    self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId]['actuatorIds'][smappeeAddress][
                        'queued-remove'] = False

            elif function == 'QUEUE-REMOVE':
                if smappeeDeviceTypeId == 'smappeeSensor':
                    if smappeeAddress not in self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId][
                            'sensorIds']:
                        self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId]['sensorIds'][
                            smappeeAddress] = {}
                    self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId]['sensorIds'][smappeeAddress][
                        'devId'] = 0
                    self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId]['sensorIds'][smappeeAddress][
                        'name'] = str(devName)
                    self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId]['sensorIds'][smappeeAddress][
                        'queued-remove'] = True
                elif smappeeDeviceTypeId == 'smappeeAppliance':
                    if smappeeAddress not in self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId][
                            'applianceIds']:
                        self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId]['applianceIds'][
                            smappeeAddress] = {}
                    self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId]['applianceIds'][smappeeAddress][
                        'devId'] = 0
                    self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId]['applianceIds'][smappeeAddress][
                        'name'] = str(devName)
                    self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId]['applianceIds'][smappeeAddress][
                        'queued-remove'] = True
                elif smappeeDeviceTypeId == 'smappeeActuator':
                    if smappeeAddress not in self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId][
                            'actuatorIds']:
                        self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId]['actuatorIds'][
                            smappeeAddress] = {}
                    self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId]['actuatorIds'][smappeeAddress][
                        'devId'] = 0
                    self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId]['actuatorIds'][smappeeAddress][
                        'name'] = str(devName)
                    self.globals['smappeeServiceLocationIdToDevId'][serviceLocationId]['actuatorIds'][smappeeAddress][
                        'queued-remove'] = True

        except StandardError, e:
            self.generalLogger.error(
                u"StandardError detected in 'setSmappeeServiceLocationIdToDevId'. Line '%s' has error='%s'" % (
                    sys.exc_traceback.tb_lineno, e))

        return

    def convertUnicode(self, input):
        if isinstance(input, dict):
            return dict([(self.convertUnicode(key), self.convertUnicode(value)) for key, value in input.iteritems()])
        elif isinstance(input, list):
            return [self.convertUnicode(element) for element in input]
        elif isinstance(input, unicode):
            return input.encode('utf-8')
        else:
            return input

    def validateDeviceConfigUi(self, valuesDict, typeId, devId):
        self.methodTracer.threaddebug(u"CLASS: Plugin")

        if typeId == "smappeeElectricity":
            result = self.validateDeviceConfigUiSmappeeElectricity(valuesDict, typeId, devId)
        elif typeId == "smappeeSolar":
            result = self.validateDeviceConfigUiSmappeeSolar(valuesDict, typeId, devId)
        elif typeId == "smappeeSensor":
            result = self.validateDeviceConfigUiSmappeeSensor(valuesDict, typeId, devId)
        else:
            self.generalLogger.error(u"WARNING: validateDeviceConfigUi TYPEID=%s NOT HANDLED" % typeId)
            result = (True, valuesDict)

        if result[0]:
            return True, result[1]  # True, Valuesdict
        else:
            return False, result[1], result[2]  # True, Valuesdict, ErrorDict

    def validateDeviceConfigUiSmappeeElectricity(self, valuesDict, typeId, devId):

        validConfig = True  # Assume config is valid

        self.globals['smappees'][devId]['hideEnergyMeterCurPower'] = False
        try:
            if "hideEnergyMeterCurPower" in valuesDict:
                self.globals['smappees'][devId]['hideEnergyMeterCurPower'] = valuesDict["hideEnergyMeterCurPower"]
        except:
            self.globals['smappees'][devId]['hideEnergyMeterCurPower'] = False

        self.globals['smappees'][devId]['hideEnergyMeterAccumPower'] = False
        try:
            if "hideEnergyMeterAccumPower" in valuesDict:
                self.globals['smappees'][devId]['hideEnergyMeterAccumPower'] = valuesDict["hideEnergyMeterAccumPower"]
        except:
            self.globals['smappees'][devId]['hideEnergyMeterAccumPower'] = False

        self.globals['smappees'][devId]['hideAlwaysOnPower'] = False
        try:
            if "hideEnergyMeterAccumPowerCost" in valuesDict:
                self.globals['smappees'][devId]['hideEnergyMeterAccumPowerCost'] = valuesDict[
                    "hideEnergyMeterAccumPowerCost"]
        except:
            self.globals['smappees'][devId]['hideEnergyMeterAccumPowerCost'] = False

        self.globals['smappees'][devId]['hideAlwaysOnPower'] = False
        try:
            if "hideAlwaysOnPower" in valuesDict:
                self.globals['smappees'][devId]['hideAlwaysOnPower'] = valuesDict["hideAlwaysOnPower"]
        except:
            self.globals['smappees'][devId]['hideAlwaysOnPower'] = False

        try:
            if "currencyCode" in valuesDict:
                self.globals['smappees'][dev.id]['currencyCode'] = valuesDict['currencyCode']
            else:
                self.globals['smappees'][devId]['currencyCode'] = 'UKP'
        except:
            self.globals['smappees'][devId]['currencyCode'] = 'UKP'

        try:
            if "dailyStandingCharge" in valuesDict:
                if valuesDict['dailyStandingCharge'] == '':
                    self.globals['smappees'][devId]['dailyStandingCharge'] = 0.00
                else:
                    try:
                        self.globals['smappees'][devId]['dailyStandingCharge'] = float(
                            valuesDict['dailyStandingCharge'])
                    except:
                        self.globals['smappees'][devId]['dailyStandingCharge'] = 0.00
                        validConfig = False
            else:
                self.globals['smappees'][devId]['dailyStandingCharge'] = 0.00
        except:
            self.globals['smappees'][devId]['dailyStandingCharge'] = 0.00
            validConfig = False

        if not validConfig:
            errorDict = indigo.Dict()
            errorDict["dailyStandingCharge"] = "Daily Standing Charge is invalid"
            errorDict["showAlertText"] = "specify a valid financial amount e.g. '0.25'"
            return False, valuesDict, errorDict

        try:
            if "kwhUnitCost" in valuesDict:
                if valuesDict['kwhUnitCost'] == '':
                    self.globals['smappees'][devId]['kwhUnitCost'] = 0.00
                else:
                    try:
                        self.globals['smappees'][devId]['kwhUnitCost'] = float(valuesDict['kwhUnitCost'])
                    except:
                        self.globals['smappees'][devId]['kwhUnitCost'] = 0.00
                        validConfig = False
            else:
                self.globals['smappees'][devId]['kwhUnitCost'] = 0.00
        except:
            self.globals['smappees'][devId]['kwhUnitCost'] = 0.00
            validConfig = False

        if not validConfig:
            errorDict = indigo.Dict()
            errorDict["kwhUnitCost"] = "The kWh Unit Cost is invalid"
            errorDict["showAlertText"] = "specify a valid financial amount e.g. '0.15'"
            return False, valuesDict, errorDict

        return True, valuesDict

    def validateDeviceConfigUiSmappeeSolar(self, valuesDict, typeId, devId):

        self.globals['smappees'][devId]['hideSolarMeterCurGeneration'] = False
        try:
            if "hideSolarMeterCurGeneration" in valuesDict:
                self.globals['smappees'][devId]['hideSolarMeterCurGeneration'] = valuesDict[
                    "hideSolarMeterCurGeneration"]
        except:
            self.globals['smappees'][devId]['hideSolarMeterCurGeneration'] = False

        self.globals['smappees'][devId]['hideSolarMeterAccumGeneration'] = False
        try:
            if "hideSolarMeterAccumGeneration" in valuesDict:
                self.globals['smappees'][devId]['hideSolarMeterAccumGeneration'] = valuesDict[
                    "hideSolarMeterAccumGeneration"]
        except:
            self.globals['smappees'][devId]['hideSolarMeterAccumGeneration'] = False

        return True, valuesDict

    def validateDeviceConfigUiSmappeeSensor(self, valuesDict, typeId, devId):

        validConfig = True  # Assume config is valid

        self.globals['smappees'][devId]['hideEnergyMeterCurPower'] = False
        try:
            if "hideEnergyMeterCurPower" in valuesDict:
                self.globals['smappees'][devId]['hideEnergyMeterCurPower'] = valuesDict["hideEnergyMeterCurPower"]
        except:
            self.globals['smappees'][devId]['hideEnergyMeterCurPower'] = False

        self.globals['smappees'][devId]['hideEnergyMeterAccumPower'] = False
        try:
            if "hideEnergyMeterAccumPower" in valuesDict:
                self.globals['smappees'][devId]['hideEnergyMeterAccumPower'] = valuesDict["hideEnergyMeterAccumPower"]
        except:
            self.globals['smappees'][devId]['hideEnergyMeterAccumPower'] = False

        self.globals['smappees'][devId]['hideAlwaysOnPower'] = False
        try:
            if "hideEnergyMeterAccumPowerCost" in valuesDict:
                self.globals['smappees'][devId]['hideEnergyMeterAccumPowerCost'] = valuesDict[
                    "hideEnergyMeterAccumPowerCost"]
        except:
            self.globals['smappees'][devId]['hideEnergyMeterAccumPowerCost'] = False

        self.globals['smappees'][devId]['hideAlwaysOnPower'] = False
        try:
            if "hideAlwaysOnPower" in valuesDict:
                self.globals['smappees'][devId]['hideAlwaysOnPower'] = valuesDict["hideAlwaysOnPower"]
        except:
            self.globals['smappees'][devId]['hideAlwaysOnPower'] = False

        try:
            if "currencyCode" in valuesDict:
                self.globals['smappees'][devId]['currencyCode'] = valuesDict['currencyCode']
            else:
                self.globals['smappees'][devId]['currencyCode'] = 'UKP'
        except:
            self.globals['smappees'][devId]['currencyCode'] = 'UKP'

        try:
            if "dailyStandingCharge" in valuesDict:
                if valuesDict['dailyStandingCharge'] == '':
                    self.globals['smappees'][devId]['dailyStandingCharge'] = 0.00
                else:
                    try:
                        self.globals['smappees'][devId]['dailyStandingCharge'] = float(
                            valuesDict['dailyStandingCharge'])
                    except:
                        self.globals['smappees'][devId]['dailyStandingCharge'] = 0.00
                        validConfig = False
            else:
                self.globals['smappees'][devId]['dailyStandingCharge'] = 0.00
        except:
            self.globals['smappees'][devId]['dailyStandingCharge'] = 0.00
            validConfig = False

        if not validConfig:
            errorDict = indigo.Dict()
            errorDict["dailyStandingCharge"] = "Daily Standing Charge is invalid"
            errorDict["showAlertText"] = "specify a valid financial amount e.g. '0.25'"
            return False, valuesDict, errorDict

        try:
            if "unitCost" in valuesDict:
                if valuesDict['unitCost'] == '':
                    self.globals['smappees'][devId]['unitCost'] = 0.00
                else:
                    try:
                        self.globals['smappees'][devId]['kwhUnitCost'] = float(valuesDict['unitCost'])
                    except:
                        self.globals['smappees'][devId]['kwhUnitCost'] = 0.00
                        validConfig = False
            else:
                self.globals['smappees'][devId]['kwhUnitCost'] = 0.00
        except:
            self.globals['smappees'][devId]['kwhUnitCost'] = 0.00
            validConfig = False

        if not validConfig:
            errorDict = indigo.Dict()
            errorDict["kwhUnitCost"] = "The Unit Cost is invalid"
            errorDict["showAlertText"] = "specify a valid financial amount e.g. '0.15'"
            return False, valuesDict, errorDict

        return True, valuesDict

    def deviceStartComm(self, dev):
        self.methodTracer.threaddebug(u"CLASS: Plugin")

        if dev.deviceTypeId == "smappeeElectricity" or dev.deviceTypeId == "smappeeElectricityNet" or dev.deviceTypeId == "smappeeElectricitySaved" or dev.deviceTypeId == "smappeeSolar" or dev.deviceTypeId == "smappeeSolarUsed" or dev.deviceTypeId == "smappeeSolarExported" or dev.deviceTypeId == "smappeeSensor" or dev.deviceTypeId == "smappeeAppliance" or dev.deviceTypeId == "smappeeActuator":
            pass
        else:
            self.generalLogger.error(
                u"Failed to start Smappee Appliance [%s]: Device type [%s] not known by plugin." % (
                    dev.name, dev.deviceTypeId))
            return

        dev.stateListOrDisplayStateIdChanged()  # Ensure latest devices.xml is being used

        try:
            # Initialise internal to plugin smappee electricity states to default values
            if dev.deviceTypeId == "smappeeElectricity":

                self.generalLogger.debug(u"SMAPPEE DEV [ELECTRICITY] START smappeeServiceLocationIdToDevId = [%s]" % (
                    self.globals['smappeeServiceLocationIdToDevId']))

                self.globals['config']['supportsElectricity'] = True

                self.serviceLocationId = str(dev.pluginProps['serviceLocationId'])

                self.generalLogger.debug(
                    u"SMAPPEE DEV [ELECTRICITY] START self.serviceLocationId = [%s]" % self.serviceLocationId)

                self.setSmappeeServiceLocationIdToDevId('ADD_UPDATE', 'smappeeElectricity', self.serviceLocationId,
                                                        dev.id, "", "")

                self.generalLogger.debug(
                    u"SMAPPEE DEV [ELECTRICITY] START smappeeServiceLocationIdToDevId [2] = [%s]" % (
                        self.globals['smappeeServiceLocationIdToDevId']))

                self.globals['smappees'][dev.id] = {}
                self.globals['smappees'][dev.id]['serviceLocationId'] = dev.pluginProps['serviceLocationId']
                self.globals['smappees'][dev.id]['serviceLocationName'] = dev.pluginProps['serviceLocationName']
                self.globals['smappees'][dev.id]['name'] = dev.name
                self.globals['smappees'][dev.id]['longditude'] = 0
                self.globals['smappees'][dev.id]['latitude'] = 0
                self.globals['smappees'][dev.id]['electricityCost'] = 0
                self.globals['smappees'][dev.id]['electricityCurrency'] = 0
                self.globals['smappees'][dev.id]['curEnergyLevel'] = 0.0
                self.globals['smappees'][dev.id]['accumEnergyTotal'] = 0.0
                self.globals['smappees'][dev.id]['dailyTotalCost'] = 0.0
                self.globals['smappees'][dev.id]['alwaysOn'] = 0.0
                self.globals['smappees'][dev.id]['lastResetElectricityUtc'] = 0
                self.globals['smappees'][dev.id]['lastReadingElectricityUtc'] = 0
                self.globals['smappees'][dev.id]['lastReadingElectricity'] = 0.0
                try:
                    self.globals['smappees'][dev.id]['hideEnergyMeterCurPower'] = dev.pluginProps[
                        'hideEnergyMeterCurPower']
                except:
                    self.globals['smappees'][dev.id]['hideEnergyMeterCurPower'] = False
                try:
                    self.globals['smappees'][dev.id]['hideEnergyMeterAccumPower'] = dev.pluginProps[
                        'hideEnergyMeterAccumPower']
                except:
                    self.globals['smappees'][dev.id]['hideEnergyMeterAccumPower'] = False
                try:
                    self.globals['smappees'][dev.id]['hideEnergyMeterAccumPowerCost'] = dev.pluginProps[
                        'hideEnergyMeterAccumPowerCost']
                except:
                    self.globals['smappees'][dev.id]['hideEnergyMeterAccumPowerCost'] = False
                try:
                    self.globals['smappees'][dev.id]['hideAlwaysOnPower'] = dev.pluginProps['hideAlwaysOnPower']
                except:
                    self.globals['smappees'][dev.id]['hideAlwaysOnPower'] = False
                try:
                    self.globals['smappees'][dev.id]['currencyCode'] = dev.pluginProps['currencyCode']
                except:
                    self.globals['smappees'][dev.id]['currencyCode'] = 'UKP'
                try:
                    self.globals['smappees'][dev.id]['dailyStandingCharge'] = float(
                        dev.pluginProps['dailyStandingCharge'])
                except:
                    self.globals['smappees'][dev.id][
                        'dailyStandingCharge'] = 8.88  # To make it obvious there is an error
                try:
                    self.globals['smappees'][dev.id]['kwhUnitCost'] = float(dev.pluginProps['kwhUnitCost'])
                except:
                    self.globals['smappees'][dev.id]['kwhUnitCost'] = 9.99  # To make it obvious there is an error

                if "curEnergyLevel" in dev.states:
                    wattStr = "%3.0f Watts" % (self.globals['smappees'][dev.id]['curEnergyLevel'])
                    dev.updateStateOnServer("curEnergyLevel", self.globals['smappees'][dev.id]['curEnergyLevel'],
                                            uiValue=wattStr)

                if "accumEnergyTotal" in dev.states:
                    kwhStr = "%3.0f kWh" % (self.globals['smappees'][dev.id]['accumEnergyTotal'])
                    dev.updateStateOnServer("accumEnergyTotal", self.globals['smappees'][dev.id]['accumEnergyTotal'],
                                            uiValue=kwhStr)

                if "alwaysOn" in dev.states:
                    wattStr = "%3.0f Watts" % (self.globals['smappees'][dev.id]['alwaysOn'])
                    dev.updateStateOnServer("alwaysOn", self.globals['smappees'][dev.id]['alwaysOn'], uiValue=wattStr)

                if "dailyTotalCost" in dev.states:
                    costStr = "%3.0f" % (self.globals['smappees'][dev.id]['dailyTotalCost'])
                    dev.updateStateOnServer("dailyTotalCost", self.globals['smappees'][dev.id]['dailyTotalCost'],
                                            uiValue=costStr)

                dev.updateStateOnServer("smappeeElectricityOnline", False, uiValue='offline')

                if self.globals['pluginInitialised'] and self.serviceLocationId != "":
                    self.globals['queues']['sendToSmappee'].put(["GET_CONSUMPTION", str(self.serviceLocationId)])

                self.generalLogger.info(u"Started '%s' at address [%s]" % (dev.name, dev.address))

            # Initialise internal to plugin smappee electricity net states to default values
            elif dev.deviceTypeId == "smappeeElectricityNet":

                self.generalLogger.debug(
                    u"SMAPPEE DEV [ELECTRICITY NET] START smappeeServiceLocationIdToDevId = [%s]" % (
                        self.globals['smappeeServiceLocationIdToDevId']))

                self.globals['config']['supportsElectricityNet'] = True

                self.serviceLocationId = str(dev.pluginProps['serviceLocationId'])

                self.generalLogger.debug(
                    u"SMAPPEE DEV [ELECTRICITY NET] START self.serviceLocationId = [%s]" % self.serviceLocationId)

                self.setSmappeeServiceLocationIdToDevId('ADD_UPDATE', 'smappeeElectricityNet', self.serviceLocationId,
                                                        dev.id, '0', '0')

                self.generalLogger.debug(
                    u"SMAPPEE DEV [ELECTRICITY NET] START smappeeServiceLocationIdToDevId [2] = [%s]" % (
                        self.globals['smappeeServiceLocationIdToDevId']))

                self.globals['smappees'][dev.id] = {}
                self.globals['smappees'][dev.id]['serviceLocationId'] = dev.pluginProps['serviceLocationId']
                self.globals['smappees'][dev.id]['serviceLocationName'] = dev.pluginProps['serviceLocationName']
                self.globals['smappees'][dev.id]['name'] = dev.name
                self.globals['smappees'][dev.id]['electricityCost'] = 0
                self.globals['smappees'][dev.id]['electricityCurrency'] = 0
                self.globals['smappees'][dev.id]['curEnergyLevel'] = 0.0
                self.globals['smappees'][dev.id]['accumEnergyTotal'] = 0.0
                self.globals['smappees'][dev.id]['dailyNetTotalCost'] = 0.0
                self.globals['smappees'][dev.id]['lastResetElectricityNetUtc'] = 0
                self.globals['smappees'][dev.id]['lastReadingElectricityNetUtc'] = 0
                self.globals['smappees'][dev.id]['lastReadingElectricityNet'] = 0.0
                try:
                    self.globals['smappees'][dev.id]['hideEnergyMeterCurNetPower'] = dev.pluginProps[
                        'hideEnergyMeterCurNetPower']
                except:
                    self.globals['smappees'][dev.id]['hideEnergyMeterCurNetPower'] = False
                try:
                    self.globals['smappees'][dev.id]['hideEnergyMeterCurZeroNetPower'] = dev.pluginProps[
                        'hideEnergyMeterCurZeroNetPower']
                except:
                    self.globals['smappees'][dev.id]['hideEnergyMeterCurZeroNetPower'] = False
                try:
                    self.globals['smappees'][dev.id]['hideEnergyMeterAccumNetPower'] = dev.pluginProps[
                        'hideEnergyMeterAccumNetPower']
                except:
                    self.globals['smappees'][dev.id]['hideEnergyMeterAccumNetPower'] = False
                try:
                    self.globals['smappees'][dev.id]['hideEnergyMeterAccumNetPowerCost'] = dev.pluginProps[
                        'hideEnergyMeterAccumNetPowerCost']
                except:
                    self.globals['smappees'][dev.id]['hideEnergyMeterAccumNetPowerCost'] = False
                try:
                    self.globals['smappees'][dev.id]['hideNoChangeEnergyMeterAccumNetPower'] = dev.pluginProps[
                        'hideNoChangeEnergyMeterAccumNetPower']
                except:
                    self.globals['smappees'][dev.id]['hideNoChangeEnergyMeterAccumNetPower'] = False

                if "curEnergyLevel" in dev.states:
                    wattStr = "%3.0f Watts" % (self.globals['smappees'][dev.id]['curEnergyLevel'])
                    dev.updateStateOnServer("curEnergyLevel", self.globals['smappees'][dev.id]['curEnergyLevel'],
                                            uiValue=wattStr)

                if "accumEnergyTotal" in dev.states:
                    kwhStr = "%3.0f kWh" % (self.globals['smappees'][dev.id]['accumEnergyTotal'])
                    dev.updateStateOnServer("accumEnergyTotal", self.globals['smappees'][dev.id]['accumEnergyTotal'],
                                            uiValue=kwhStr)

                if "dailyNetTotalCost" in dev.states:
                    costStr = "%3.0f" % (self.globals['smappees'][dev.id]['dailyNetTotalCost'])
                    dev.updateStateOnServer("dailyNetTotalCost", self.globals['smappees'][dev.id]['dailyNetTotalCost'],
                                            uiValue=costStr)

                dev.updateStateOnServer("smappeeElectricityNetOnline", False, uiValue='offline')

                # if self.globals['pluginInitialised'] == True and self.serviceLocationId != "":
                #     self.globals['queues']['sendToSmappee'].put(["GET_CONSUMPTION",str(self.serviceLocationId)])

                self.generalLogger.info(u"Started '%s' at address [%s]" % (dev.name, dev.address))

            # Initialise internal to plugin smappee electricity Saved states to default values
            elif dev.deviceTypeId == "smappeeElectricitySaved":

                self.generalLogger.debug(
                    u"SMAPPEE DEV [ELECTRICITY SAVED] START smappeeServiceLocationIdToDevId = [%s]" % (
                        self.globals['smappeeServiceLocationIdToDevId']))

                self.globals['config']['supportsElectricitySaved'] = True

                self.serviceLocationId = str(dev.pluginProps['serviceLocationId'])

                self.generalLogger.debug(
                    u"SMAPPEE DEV [ELECTRICITY SAVED] START self.serviceLocationId = [%s]" % self.serviceLocationId)

                self.setSmappeeServiceLocationIdToDevId('ADD_UPDATE', 'smappeeElectricitySaved', self.serviceLocationId,
                                                        dev.id, '0', '0')

                self.generalLogger.debug(
                    u"SMAPPEE DEV [ELECTRICITY SAVED] START smappeeServiceLocationIdToDevId [2] = [%s]" % (
                        self.globals['smappeeServiceLocationIdToDevId']))

                self.globals['smappees'][dev.id] = {}
                self.globals['smappees'][dev.id]['serviceLocationId'] = dev.pluginProps['serviceLocationId']
                self.globals['smappees'][dev.id]['serviceLocationName'] = dev.pluginProps['serviceLocationName']
                self.globals['smappees'][dev.id]['name'] = dev.name
                self.globals['smappees'][dev.id]['electricityCost'] = 0
                self.globals['smappees'][dev.id]['electricityCurrency'] = 0
                self.globals['smappees'][dev.id]['curEnergyLevel'] = 0.0
                self.globals['smappees'][dev.id]['accumEnergyTotal'] = 0.0
                self.globals['smappees'][dev.id]['dailyTotalCostSaving'] = 0.0
                self.globals['smappees'][dev.id]['lastResetElectricitySavedUtc'] = 0
                self.globals['smappees'][dev.id]['lastReadingElectricitySavedUtc'] = 0
                self.globals['smappees'][dev.id]['lastReadingElectricitySaved'] = 0.0
                try:
                    self.globals['smappees'][dev.id]['hideEnergyMeterCurSavedPower'] = dev.pluginProps[
                        'hideEnergyMeterCurSavedPower']
                except:
                    self.globals['smappees'][dev.id]['hideEnergyMeterCurSavedPower'] = False
                try:
                    self.globals['smappees'][dev.id]['hideEnergyMeterCurZeroSavedPower'] = dev.pluginProps[
                        'hideEnergyMeterCurZeroSavedPower']
                except:
                    self.globals['smappees'][dev.id]['hideEnergyMeterCurZeroSavedPower'] = False
                try:
                    self.globals['smappees'][dev.id]['hideEnergyMeterAccumSavedPower'] = dev.pluginProps[
                        'hideEnergyMeterAccumSavedPower']
                except:
                    self.globals['smappees'][dev.id]['hideEnergyMeterAccumSavedPower'] = False
                try:
                    self.globals['smappees'][dev.id]['hideEnergyMeterAccumSavedPowerCost'] = dev.pluginProps[
                        'hideEnergyMeterAccumSavedPowerCost']
                except:
                    self.globals['smappees'][dev.id]['hideEnergyMeterAccumSavedPowerCost'] = False
                try:
                    self.globals['smappees'][dev.id]['hideNoChangeEnergyMeterAccumSavedPower'] = dev.pluginProps[
                        'hideNoChangeEnergyMeterAccumSavedPower']
                except:
                    self.globals['smappees'][dev.id]['hideNoChangeEnergyMeterAccumSavedPower'] = False

                if "curEnergyLevel" in dev.states:
                    wattStr = "%3.0f Watts" % (self.globals['smappees'][dev.id]['curEnergyLevel'])
                    dev.updateStateOnServer("curEnergyLevel", self.globals['smappees'][dev.id]['curEnergyLevel'],
                                            uiValue=wattStr)

                if "accumEnergyTotal" in dev.states:
                    kwhStr = "%3.0f kWh" % (self.globals['smappees'][dev.id]['accumEnergyTotal'])
                    dev.updateStateOnServer("accumEnergyTotal", self.globals['smappees'][dev.id]['accumEnergyTotal'],
                                            uiValue=kwhStr)

                if "dailyTotalCostSaving" in dev.states:
                    costStr = "%3.0f" % (self.globals['smappees'][dev.id]['dailyTotalCostSaving'])
                    dev.updateStateOnServer("dailyTotalCostSaving",
                                            self.globals['smappees'][dev.id]['dailyTotalCostSaving'], uiValue=costStr)

                dev.updateStateOnServer("smappeeElectricitySavedOnline", False, uiValue='offline')

                # if self.globals['pluginInitialised'] == True and self.serviceLocationId != "":
                #     self.globals['queues']['sendToSmappee'].put(["GET_CONSUMPTION",str(self.serviceLocationId)])

                self.generalLogger.info(u"Started '%s' at address [%s]" % (dev.name, dev.address))

            # Initialise internal to plugin smappee solar states to default values
            elif dev.deviceTypeId == "smappeeSolar":

                self.generalLogger.debug(u"SMAPPEE DEV [SOLAR] START smappeeServiceLocationIdToDevId = [%s]" % (
                    self.globals['smappeeServiceLocationIdToDevId']))

                self.globals['config']['supportsSolar'] = True

                self.serviceLocationId = str(dev.pluginProps['serviceLocationId'])

                self.generalLogger.debug(
                    u"SMAPPEE DEV [SOLAR] START self.serviceLocationId = [%s]" % self.serviceLocationId)

                self.setSmappeeServiceLocationIdToDevId('ADD_UPDATE', 'smappeeSolar', self.serviceLocationId, dev.id,
                                                        '0', '0')

                self.generalLogger.debug(u"SMAPPEE DEV [SOLAR] START smappeeServiceLocationIdToDevId [2] = [%s]" % (
                    self.globals['smappeeServiceLocationIdToDevId']))

                self.globals['smappees'][dev.id] = {}
                self.globals['smappees'][dev.id]['serviceLocationId'] = dev.pluginProps['serviceLocationId']
                self.globals['smappees'][dev.id]['serviceLocationName'] = dev.pluginProps['serviceLocationName']
                self.globals['smappees'][dev.id]['name'] = dev.name
                self.globals['smappees'][dev.id]['electricityCost'] = 0
                self.globals['smappees'][dev.id]['electricityCurrency'] = 0
                self.globals['smappees'][dev.id]['curEnergyLevel'] = 0.0
                self.globals['smappees'][dev.id]['accumEnergyTotal'] = 0.0
                self.globals['smappees'][dev.id]['lastResetSolarUtc'] = 0
                self.globals['smappees'][dev.id]['lastReadingSolarUtc'] = 0
                self.globals['smappees'][dev.id]['lastReadingSolar'] = 0.0
                try:
                    self.globals['smappees'][dev.id]['hideSolarMeterCurGeneration'] = dev.pluginProps[
                        'hideSolarMeterCurGeneration']
                except:
                    self.globals['smappees'][dev.id]['hideSolarMeterCurGeneration'] = False
                try:
                    self.globals['smappees'][dev.id]['hideZeroSolarMeterCurGeneration'] = dev.pluginProps[
                        'hideZeroSolarMeterCurGeneration']
                except:
                    self.globals['smappees'][dev.id]['hideZeroSolarMeterCurGeneration'] = False
                try:
                    self.globals['smappees'][dev.id]['hideSolarMeterAccumGeneration'] = dev.pluginProps[
                        'hideSolarMeterAccumGeneration']
                except:
                    self.globals['smappees'][dev.id]['hideSolarMeterAccumGeneration'] = False
                try:
                    self.globals['smappees'][dev.id]['hideSolarMeterAccumGenerationCost'] = dev.pluginProps[
                        'hideSolarMeterAccumGenerationCost']
                except:
                    self.globals['smappees'][dev.id]['hideSolarMeterAccumGenerationCost'] = False
                try:
                    self.globals['smappees'][dev.id]['hideNoChangeInSolarMeterAccumGeneration'] = dev.pluginProps[
                        'hideNoChangeInSolarMeterAccumGeneration']
                except:
                    self.globals['smappees'][dev.id]['hideNoChangeInSolarMeterAccumGeneration'] = False
                try:
                    self.globals['smappees'][dev.id]['currencyCode'] = dev.pluginProps['currencyCode']
                except:
                    self.globals['smappees'][dev.id]['currencyCode'] = 'UKP'
                try:
                    self.globals['smappees'][dev.id]['generationRate'] = float(dev.pluginProps['generationRate'])
                except:
                    self.globals['smappees'][dev.id]['generationRate'] = 8.88  # To make it obvious there is an error

                try:
                    self.globals['smappees'][dev.id]['exportType'] = dev.pluginProps['exportType']
                except:
                    self.globals['smappees'][dev.id]['exportType'] = 'percentage'

                try:
                    self.globals['smappees'][dev.id]['exportPercentage'] = float(dev.pluginProps['exportPercentage'])
                except:
                    self.globals['smappees'][dev.id]['exportPercentage'] = 50.0  # To make it obvious there is an error

                try:
                    self.globals['smappees'][dev.id]['exportRate'] = float(dev.pluginProps['exportRate'])
                except:
                    self.globals['smappees'][dev.id]['exportRate'] = 9.99  # To make it obvious there is an error
                if "curEnergyLevel" in dev.states:
                    wattStr = "%3.0f Watts" % (self.globals['smappees'][dev.id]['curEnergyLevel'])
                    dev.updateStateOnServer("curEnergyLevel", self.globals['smappees'][dev.id]['curEnergyLevel'],
                                            uiValue=wattStr)

                if "accumEnergyTotal" in dev.states:
                    kwhStr = "%3.0f kWh" % (self.globals['smappees'][dev.id]['accumEnergyTotal'])
                    dev.updateStateOnServer("accumEnergyTotal", self.globals['smappees'][dev.id]['accumEnergyTotal'],
                                            uiValue=kwhStr)

                dev.updateStateOnServer("smappeeSolarOnline", False, uiValue='offline')

                if self.globals['pluginInitialised'] and self.serviceLocationId != "":
                    self.globals['queues']['sendToSmappee'].put(["GET_CONSUMPTION", str(self.serviceLocationId)])

                self.generalLogger.info(u"Started '%s' at address [%s]" % (dev.name, dev.address))

            # Initialise internal to plugin smappee solar used states to default values
            elif dev.deviceTypeId == "smappeeSolarUsed":

                self.generalLogger.debug(u"SMAPPEE DEV [SOLAR USED] START smappeeServiceLocationIdToDevId = [%s]" % (
                    self.globals['smappeeServiceLocationIdToDevId']))

                self.globals['config']['supportsSolarUsed'] = True

                self.serviceLocationId = str(dev.pluginProps['serviceLocationId'])

                self.generalLogger.debug(
                    u"SMAPPEE DEV [SOLAR USED] START self.serviceLocationId = [%s]" % self.serviceLocationId)

                self.setSmappeeServiceLocationIdToDevId('ADD_UPDATE', 'smappeeSolarUsed', self.serviceLocationId,
                                                        dev.id, '0', '0')

                self.generalLogger.debug(
                    u"SMAPPEE DEV [SOLAR USED] START smappeeServiceLocationIdToDevId [2] = [%s]" % (
                        self.globals['smappeeServiceLocationIdToDevId']))

                self.globals['smappees'][dev.id] = {}
                self.globals['smappees'][dev.id]['serviceLocationId'] = dev.pluginProps['serviceLocationId']
                self.globals['smappees'][dev.id]['serviceLocationName'] = dev.pluginProps['serviceLocationName']
                self.globals['smappees'][dev.id]['name'] = dev.name
                self.globals['smappees'][dev.id]['electricityCost'] = 0
                self.globals['smappees'][dev.id]['electricityCurrency'] = 0
                self.globals['smappees'][dev.id]['curEnergyLevel'] = 0.0
                self.globals['smappees'][dev.id]['accumEnergyTotal'] = 0.0
                self.globals['smappees'][dev.id]['lastResetSolarUsedUtc'] = 0
                self.globals['smappees'][dev.id]['lastReadingSolarUsedUtc'] = 0
                self.globals['smappees'][dev.id]['lastReadingSolarUsed'] = 0.0
                self.globals['smappees'][dev.id]['hideSolarUsedMeterCurGeneration'] = dev.pluginProps[
                    'hideSolarUsedMeterCurGeneration']
                self.globals['smappees'][dev.id]['hideZeroSolarUsedMeterCurGeneration'] = dev.pluginProps[
                    'hideZeroSolarUsedMeterCurGeneration']
                self.globals['smappees'][dev.id]['hideSolarUsedMeterAccumGeneration'] = dev.pluginProps[
                    'hideSolarUsedMeterAccumGeneration']
                self.globals['smappees'][dev.id]['hideNoChangeInSolarUsedMeterAccumGeneration'] = dev.pluginProps[
                    'hideNoChangeInSolarUsedMeterAccumGeneration']

                if "curEnergyLevel" in dev.states:
                    wattStr = "%3.0f Watts" % (self.globals['smappees'][dev.id]['curEnergyLevel'])
                    dev.updateStateOnServer("curEnergyLevel", self.globals['smappees'][dev.id]['curEnergyLevel'],
                                            uiValue=wattStr)

                if "accumEnergyTotal" in dev.states:
                    kwhStr = "%3.0f kWh" % (self.globals['smappees'][dev.id]['accumEnergyTotal'])
                    dev.updateStateOnServer("accumEnergyTotal", self.globals['smappees'][dev.id]['accumEnergyTotal'],
                                            uiValue=kwhStr)

                dev.updateStateOnServer("smappeeSolarUsedOnline", False, uiValue='offline')

                # if self.globals['pluginInitialised'] == True and self.serviceLocationId != "":
                #     self.globals['queues']['sendToSmappee'].put(["GET_CONSUMPTION",str(self.serviceLocationId)])

                self.generalLogger.info(u"Started '%s' at address [%s]" % (dev.name, dev.address))

            # Initialise internal to plugin smappee solar exported states to default values
            elif dev.deviceTypeId == "smappeeSolarExported":

                self.generalLogger.debug(
                    u"SMAPPEE DEV [SOLAR EXPORTED] START smappeeServiceLocationIdToDevId = [%s]" % (
                        self.globals['smappeeServiceLocationIdToDevId']))

                self.globals['config']['supportsSolarExported'] = True

                self.serviceLocationId = str(dev.pluginProps['serviceLocationId'])

                self.generalLogger.debug(
                    u"SMAPPEE DEV [SOLAR EXPORTED] START self.serviceLocationId = [%s]" % self.serviceLocationId)

                self.setSmappeeServiceLocationIdToDevId('ADD_UPDATE', 'smappeeSolarExported', self.serviceLocationId,
                                                        dev.id, '0', '0')

                self.generalLogger.debug(
                    u"SMAPPEE DEV [SOLAR EXPORTED] START smappeeServiceLocationIdToDevId [2] = [%s]" % (
                        self.globals['smappeeServiceLocationIdToDevId']))

                self.globals['smappees'][dev.id] = {}
                self.globals['smappees'][dev.id]['serviceLocationId'] = dev.pluginProps['serviceLocationId']
                self.globals['smappees'][dev.id]['serviceLocationName'] = dev.pluginProps['serviceLocationName']
                self.globals['smappees'][dev.id]['name'] = dev.name
                self.globals['smappees'][dev.id]['electricityCost'] = 0
                self.globals['smappees'][dev.id]['electricityCurrency'] = 0
                self.globals['smappees'][dev.id]['curEnergyLevel'] = 0.0
                self.globals['smappees'][dev.id]['accumEnergyTotal'] = 0.0
                self.globals['smappees'][dev.id]['lastResetSolarExportedUtc'] = 0
                self.globals['smappees'][dev.id]['lastReadingSolarExportedUtc'] = 0
                self.globals['smappees'][dev.id]['lastReadingSolarExported'] = 0.0
                self.globals['smappees'][dev.id]['hideSolarExportedMeterCurGeneration'] = dev.pluginProps[
                    'hideSolarExportedMeterCurGeneration']
                self.globals['smappees'][dev.id]['hideZeroSolarExportedMeterCurGeneration'] = dev.pluginProps[
                    'hideZeroSolarExportedMeterCurGeneration']
                self.globals['smappees'][dev.id]['hideSolarExportedMeterAccumGeneration'] = dev.pluginProps[
                    'hideSolarExportedMeterAccumGeneration']
                self.globals['smappees'][dev.id]['hideNoChangeInSolarExportedMeterAccumGeneration'] = dev.pluginProps[
                    'hideNoChangeInSolarExportedMeterAccumGeneration']

                if "curEnergyLevel" in dev.states:
                    wattStr = "%3.0f Watts" % (self.globals['smappees'][dev.id]['curEnergyLevel'])
                    dev.updateStateOnServer("curEnergyLevel", self.globals['smappees'][dev.id]['curEnergyLevel'],
                                            uiValue=wattStr)

                if "accumEnergyTotal" in dev.states:
                    kwhStr = "%3.0f kWh" % (self.globals['smappees'][dev.id]['accumEnergyTotal'])
                    dev.updateStateOnServer("accumEnergyTotal", self.globals['smappees'][dev.id]['accumEnergyTotal'],
                                            uiValue=kwhStr)

                dev.updateStateOnServer("smappeeSolarExportedOnline", False, uiValue='offline')

                # if self.globals['pluginInitialised'] == True and self.serviceLocationId != "":
                #     self.globals['queues']['sendToSmappee'].put(["GET_CONSUMPTION",str(self.serviceLocationId)])

                self.generalLogger.info(u"Started '%s' at address [%s]" % (dev.name, dev.address))

            # Initialise internal to plugin smappee sensor states to default values
            elif dev.deviceTypeId == "smappeeSensor":

                self.generalLogger.debug(u"SMAPPEE DEV [SENSOR] START-A smappeeServiceLocationIdToDevId = [%s]" % (
                    self.globals['smappeeServiceLocationIdToDevId']))

                self.serviceLocationId = str(dev.pluginProps['serviceLocationId'])

                self.generalLogger.debug(
                    u"SMAPPEE DEV [SENSOR] START-B self.serviceLocationId = [%s]" % self.serviceLocationId)

                self.setSmappeeServiceLocationIdToDevId('ADD_UPDATE', 'smappeeSensor', self.serviceLocationId, dev.id,
                                                        dev.address, dev.name)

                self.generalLogger.debug(u"SMAPPEE DEV [SENSOR] START-C smappeeServiceLocationIdToDevId [2] = [%s]" % (
                    self.globals['smappeeServiceLocationIdToDevId']))

                self.globals['smappees'][dev.id] = {}
                self.globals['smappees'][dev.id]['serviceLocationId'] = dev.pluginProps['serviceLocationId']
                self.globals['smappees'][dev.id]['serviceLocationName'] = dev.pluginProps['serviceLocationName']
                self.globals['smappees'][dev.id]['name'] = dev.name
                self.globals['smappees'][dev.id]['longditude'] = 0
                self.globals['smappees'][dev.id]['latitude'] = 0
                self.globals['smappees'][dev.id]['smappeeUnitCost'] = 0
                self.globals['smappees'][dev.id]['smappeeUnitCurrency'] = 0
                self.globals['smappees'][dev.id]['curEnergyLevel'] = 0.0
                self.globals['smappees'][dev.id]['accumEnergyTotal'] = 0.0
                self.globals['smappees'][dev.id]['dailyTotalCost'] = 0.0
                self.globals['smappees'][dev.id]['lastResetSensorUtc'] = 0
                self.globals['smappees'][dev.id]['lastReadingSensorUtc'] = 0
                self.globals['smappees'][dev.id]['lastReadingSensor'] = 0.0
                self.globals['smappees'][dev.id]['readingsLastUpdated'] = 'Unknown'
                self.globals['smappees'][dev.id]['hideEnergyMeterCurPower'] = dev.pluginProps['hideEnergyMeterCurPower']
                self.globals['smappees'][dev.id]['hideEnergyMeterAccumPower'] = dev.pluginProps[
                    'hideEnergyMeterAccumPower']
                self.globals['smappees'][dev.id]['temperature'] = 0.0
                self.globals['smappees'][dev.id]['humidity'] = 0.0
                self.globals['smappees'][dev.id]['batteryLevel'] = 0.0
                self.globals['smappees'][dev.id]['temperatureLastUpdated'] = 'Unknown'
                self.globals['smappees'][dev.id]['humidityLastUpdated'] = 'Unknown'
                self.globals['smappees'][dev.id]['batteryLevelLastUpdated'] = 'Unknown'

                try:
                    self.globals['smappees'][dev.id]['currencyCode'] = dev.pluginProps['currencyCode']
                except:
                    self.globals['smappees'][dev.id]['currencyCode'] = 'UKP'
                try:
                    self.globals['smappees'][dev.id]['dailyStandingCharge'] = float(
                        dev.pluginProps['dailyStandingCharge'])
                except:
                    self.globals['smappees'][dev.id][
                        'dailyStandingCharge'] = 8.88  # To make it obvious there is an error
                try:
                    self.globals['smappees'][dev.id]['units'] = str(dev.pluginProps['units'])
                except:
                    self.globals['smappees'][dev.id]['units'] = 'kWh'
                try:
                    self.globals['smappees'][dev.id]['pulsesPerUnit'] = str(dev.pluginProps['pulsesPerUnit'])
                except:
                    self.globals['smappees'][dev.id]['pulsesPerUnit'] = int(1.0)
                try:
                    self.globals['smappees'][dev.id]['unitCost'] = float(dev.pluginProps['unitCost'])
                except:
                    self.globals['smappees'][dev.id]['unitCost'] = 9.99  # To make it obvious there is an error

                if "readingsLastUpdated" in dev.states:
                    dev.updateStateOnServer("readingsLastUpdated",
                                            self.globals['smappees'][dev.id]['readingsLastUpdated'])

                if "temperature" in dev.states:
                    temperatureStr = "%0.1f deg C" % (self.globals['smappees'][dev.id]['temperature'])
                    temperatureReformatted = float("%0.1f" % (self.globals['smappees'][dev.id]['temperature']))
                    dev.updateStateOnServer("temperature", temperatureReformatted, uiValue=temperatureStr)

                if "humidity" in dev.states:
                    humidityStr = "%0.1f%%" % (self.globals['smappees'][dev.id]['humidity'])
                    humidityReformatted = float("%0.1f" % (self.globals['smappees'][dev.id]['humidity']))
                    dev.updateStateOnServer("humidity", humidityReformatted, uiValue=humidityStr)

                if "batteryLevel" in dev.states:
                    batteryLevelStr = "%0.1f%%" % (self.globals['smappees'][dev.id]['batteryLevel'])
                    batteryLevelReformatted = float("%0.1f" % (self.globals['smappees'][dev.id]['batteryLevel']))
                    dev.updateStateOnServer("batteryLevel", batteryLevelReformatted, uiValue=batteryLevelStr)

                if "temperatureLastUpdated" in dev.states:
                    dev.updateStateOnServer("temperatureLastUpdated",
                                            self.globals['smappees'][dev.id]['temperatureLastUpdated'])

                if "humidityLastUpdated" in dev.states:
                    dev.updateStateOnServer("humidityLastUpdated",
                                            self.globals['smappees'][dev.id]['humidityLastUpdated'])

                if "batteryLevelLastUpdated" in dev.states:
                    dev.updateStateOnServer("batteryLevelLastUpdated",
                                            self.globals['smappees'][dev.id]['batteryLevelLastUpdated'])

                unitsKey = self.globals['smappees'][dev.id]['units']
                if unitsKey in self.globals['unitTable']:
                    pass
                else:
                    unitsKey = 'default'

                unitsCurrentUnits = self.globals['unitTable'][unitsKey]['currentUnits']
                unitsAccumUnits = self.globals['unitTable'][unitsKey]['accumUnits']
                unitsmeasurementTimeMultiplier = self.globals['unitTable'][unitsKey]['measurementTimeMultiplier']
                unitsformatTotaldivisor = self.globals['unitTable'][unitsKey]['formatTotaldivisor']
                unitsformatCurrent = self.globals['unitTable'][unitsKey]['formatCurrent']
                unitsformatCurrentUi = unitsformatCurrent + u' ' + unitsCurrentUnits
                unitsformatTotal = self.globals['unitTable'][unitsKey]['formatTotal']
                unitsformatTotalUi = unitsformatTotal + ' ' + unitsAccumUnits

                if "curEnergyLevel" in dev.states:
                    dataToUpdateStr = str(unitsformatCurrentUi % (self.globals['smappees'][dev.id]['curEnergyLevel']))
                    dev.updateStateOnServer("curEnergyLevel", self.globals['smappees'][dev.id]['curEnergyLevel'],
                                            uiValue=dataToUpdateStr)

                if "accumEnergyTotal" in dev.states:
                    dataToUpdateStr = str(unitsformatTotalUi % (self.globals['smappees'][dev.id]['accumEnergyTotal']))
                    dev.updateStateOnServer("accumEnergyTotal", self.globals['smappees'][dev.id]['accumEnergyTotal'],
                                            uiValue=dataToUpdateStr)

                try:
                    self.globals['smappees'][dev.id]['hideEnergyMeterAccumPowerCost'] = dev.pluginProps[
                        'hideEnergyMeterAccumPowerCost']
                except:
                    self.globals['smappees'][dev.id]['hideEnergyMeterAccumPowerCost'] = False

                dev.updateStateOnServer("smappeeSensorOnline", False, uiValue='offline')

                if "dailyTotalCost" in dev.states:
                    costStr = "%3.0f" % (self.globals['smappees'][dev.id]['dailyTotalCost'])
                    dev.updateStateOnServer("dailyTotalCost", self.globals['smappees'][dev.id]['dailyTotalCost'],
                                            uiValue=costStr)

                if self.globals['pluginInitialised'] and self.serviceLocationId != "":
                    self.globals['queues']['sendToSmappee'].put(["GET_SENSOR_CONSUMPTION", str(self.serviceLocationId)])

                self.generalLogger.info(u"Started '%s' at address [%s]" % (dev.name, dev.address))

            elif dev.deviceTypeId == "smappeeAppliance":

                self.serviceLocationId = str(dev.pluginProps['serviceLocationId'])

                self.setSmappeeServiceLocationIdToDevId('ADD_UPDATE', 'smappeeAppliance', self.serviceLocationId,
                                                        dev.id, dev.address, dev.name)

                self.globals['smappeeAppliances'][dev.id] = {}
                self.globals['smappeeAppliances'][dev.id]['serviceLocationId'] = dev.pluginProps['serviceLocationId']
                self.globals['smappeeAppliances'][dev.id]["datetimeStarted"] = indigo.server.getTime()
                self.globals['smappeeAppliances'][dev.id]['address'] = dev.address
                self.globals['smappeeAppliances'][dev.id]['onOffState'] = 'off'
                self.globals['smappeeAppliances'][dev.id]['onOffStateBool'] = False
                self.globals['smappeeAppliances'][dev.id]['name'] = dev.name
                self.globals['smappeeAppliances'][dev.id]['curEnergyLevel'] = 0.0
                self.globals['smappeeAppliances'][dev.id]['accumEnergyTotal'] = 0.0
                self.globals['smappeeAppliances'][dev.id]['lastResetApplianceUtc'] = 0
                self.globals['smappeeAppliances'][dev.id]['lastReadingApplianceUtc'] = 0
                self.globals['smappeeAppliances'][dev.id]['lastReadingAppliance'] = 0.0

                if "curEnergyLevel" in dev.states:
                    wattStr = "%3.0f Watts" % (self.globals['smappeeAppliances'][dev.id]['curEnergyLevel'])
                    dev.updateStateOnServer("curEnergyLevel",
                                            self.globals['smappeeAppliances'][dev.id]['curEnergyLevel'],
                                            uiValue=wattStr)

                if "accumEnergyTotal" in dev.states:
                    kwhStr = "%3.0f kWh" % (self.globals['smappeeAppliances'][dev.id]['accumEnergyTotal'])
                    dev.updateStateOnServer("accumEnergyTotal",
                                            self.globals['smappeeAppliances'][dev.id]['accumEnergyTotal'],
                                            uiValue=kwhStr)

                dev.updateStateOnServer("smappeeApplianceEventStatus", "NONE", uiValue="No Events")
                if float(indigo.server.apiVersion) >= 1.18:
                    dev.updateStateImageOnServer(indigo.kStateImageSel.EnergyMeterOff)

                self.generalLogger.info(
                    u"Started '%s' at address [%s]" % (dev.name, self.globals['smappeeAppliances'][dev.id]['address']))

            elif dev.deviceTypeId == "smappeeActuator":

                self.serviceLocationId = str(dev.pluginProps['serviceLocationId'])

                self.setSmappeeServiceLocationIdToDevId('ADD_UPDATE', 'smappeeActuator', self.serviceLocationId, dev.id,
                                                        dev.address, dev.name)

                self.globals['smappeePlugs'][dev.id] = {}
                self.globals['smappeePlugs'][dev.id]["datetimeStarted"] = indigo.server.getTime()
                self.globals['smappeePlugs'][dev.id]['address'] = dev.address
                self.globals['smappeePlugs'][dev.id]['onOffState'] = 'off'
                self.globals['smappeePlugs'][dev.id]['onOffStateBool'] = False
                self.globals['smappeePlugs'][dev.id]['name'] = dev.name

                dev.updateStateOnServer("onOffState", False, uiValue='off')

                self.generalLogger.info(
                    u"Started '%s' at address [%s]" % (dev.name, self.globals['smappeePlugs'][dev.id]['address']))

            self.generalLogger.debug(u"SMAPPEE DEV [%s] [%s] START smappeeServiceLocationIdToDevId = [%s]" % (
                dev.name, dev.model, self.globals['smappeeServiceLocationIdToDevId']))

        except StandardError, e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            self.generalLogger.error(
                u"deviceStartComm: StandardError detected for '%s' at line '%s' = %s" % (dev.name, exc_tb.tb_lineno, e))

        return

    def deviceStopComm(self, dev):
        self.methodTracer.threaddebug(u"CLASS: Plugin")

        self.globals['smappees'][dev.id] = {}

        if dev.deviceTypeId == "smappeeElectricity":
            dev.updateStateOnServer("smappeeElectricityOnline", False, uiValue='Stopped')
            self.globals['config']['supportsElectricity'] = False

        elif dev.deviceTypeId == "smappeeElectricityNet":
            dev.updateStateOnServer("smappeeElectricityNetOnline", False, uiValue='Stopped')
            self.globals['config']['supportsElectricityNet'] = False

        elif dev.deviceTypeId == "smappeeElectricitySaved":
            dev.updateStateOnServer("smappeeElectricitySavedOnline", False, uiValue='Stopped')
            self.globals['config']['supportsElectricitySaved'] = False

        elif dev.deviceTypeId == "smappeeSolar":
            dev.updateStateOnServer("smappeeSolarOnline", False, uiValue='Stopped')
            self.globals['config']['supportsSolar'] = False

        elif dev.deviceTypeId == "smappeeSolarUsed":
            dev.updateStateOnServer("smappeeSolarUsedOnline", False, uiValue='Stopped')
            self.globals['config']['supportsSolarUsed'] = False

        elif dev.deviceTypeId == "smappeeSolarExported":
            dev.updateStateOnServer("smappeeSolarExportedOnline", False, uiValue='Stopped')
            self.globals['config']['supportsSolarExported'] = False

        elif dev.deviceTypeId == "smappeeSensor":
            dev.updateStateOnServer("smappeeSensorOnline", False, uiValue='Stopped')

        elif dev.deviceTypeId == "smappeeAppliance":
            dev.updateStateOnServer("smappeeApplianceEventStatus", 'Stopped')

        elif dev.deviceTypeId == "smappeeActuator":
            dev.updateStateOnServer("onOffState", False, uiValue='stopped')

        serviceLocationId = dev.pluginProps['serviceLocationId']
        self.setSmappeeServiceLocationIdToDevId('STOP', dev.deviceTypeId, serviceLocationId, dev.id, dev.address,
                                                dev.name)

        self.generalLogger.info(u"Stopping '%s'" % dev.name)
