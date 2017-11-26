#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# Smappee Controller © Autolog 2016
# & 
# copyright (c) 2016, Perceptive Automation, LLC. All rights reserved.
# http://www.indigodomo.com
#
import collections  # Used for creating sensor testdata
import datetime
import errno
import inspect
import math
import locale
import logging
from logging.handlers import TimedRotatingFileHandler
import operator
import os
from Queue import Queue as autologQueue
from Queue import Empty as autologQueueEmpty
import select
import signal
import simplejson as json
import sqlite3 as sql3
import subprocess
import sys
import threading
import time
import traceback

pluginGlobal = {}

pluginGlobal['plugin'] = {}  # Info about the plugin filled in by Plugin Start

pluginGlobal['TESTING'] = False

pluginGlobal['SQL']                = {}
pluginGlobal['SQL']['enabled']     = True
pluginGlobal['SQL']['db']          = '/Users/admin/Documents/Autolog/sqlite/smappee.db'
pluginGlobal['SQL']['dbType']      = 'sqlite3'
pluginGlobal['SQL']['connection']  = ''
pluginGlobal['SQL']['cursor']      = ''

pluginGlobal['autologger'] = ''

if pluginGlobal['TESTING'] == True:
    pluginGlobal['testdata'] = {}
    pluginGlobal['testdata']['temperature'] = collections.deque(['255','252','250','249','247','246','220','223','221','198','195','192'])
    pluginGlobal['testdata']['humidity'] = collections.deque(['90','85','80','75','70','65','60','55','50','45','40','35'])
    pluginGlobal['testdata']['batteryLevel'] = collections.deque(['100','99','98','97','95','94','93','92','91','90','89','88'])
    pluginGlobal['testdata']['value1'] = collections.deque(['0','800','400','0','800','800','1200','100','0','0','1000','700'])
    pluginGlobal['testdata']['value2'] = collections.deque(['50','50','0','0','0','0','400','0','0','0','50','70'])


pluginGlobal['unitTable'] = {}

pluginGlobal['unitTable']['default'] = {}
pluginGlobal['unitTable']['default']['measurementTimeMultiplier'] = 12.0  # 'hourly' = 12, '5 minutes' = 1'
pluginGlobal['unitTable']['default']['formatTotaldivisor'] = 1000.0
pluginGlobal['unitTable']['default']['formatCurrent'] = "%d"
pluginGlobal['unitTable']['default']['formatTotal'] = "%3.0f"
pluginGlobal['unitTable']['default']['currentUnits'] = 'watts [E]'                               
pluginGlobal['unitTable']['default']['currentUnitsRate'] = 'watt [E] hours'
pluginGlobal['unitTable']['default']['accumUnits'] = 'kWh [E]'

pluginGlobal['unitTable']['kWh'] = {}
pluginGlobal['unitTable']['kWh']['measurementTimeMultiplier'] = 12.0  # 'hourly' = 12, '5 minutes' = 1'
pluginGlobal['unitTable']['kWh']['formatTotaldivisor'] = 1000.0
pluginGlobal['unitTable']['kWh']['formatCurrentDivisor'] = 1000.0
pluginGlobal['unitTable']['kWh']['formatCurrent'] = "%d"
pluginGlobal['unitTable']['kWh']['formatTotal'] = "%3.0f"
pluginGlobal['unitTable']['kWh']['currentUnits'] = 'watts'                               
pluginGlobal['unitTable']['kWh']['currentUnitsRate'] = 'watt hours'
pluginGlobal['unitTable']['kWh']['accumUnits'] = 'kWh'

pluginGlobal['unitTable']['litres'] = {}
pluginGlobal['unitTable']['litres']['measurementTimeMultiplier'] = 1.0  # 'hourly' = 12, '5 minutes' = 1'
pluginGlobal['unitTable']['litres']['formatTotaldivisor'] = 1.0
pluginGlobal['unitTable']['litres']['formatCurrent'] = "%d"
pluginGlobal['unitTable']['litres']['formatTotal'] = "%d"
pluginGlobal['unitTable']['litres']['currentUnits'] = 'litres'                               
pluginGlobal['unitTable']['litres']['accumUnits'] = 'litres'

pluginGlobal['unitTable']['m3'] = {}
pluginGlobal['unitTable']['m3']['measurementTimeMultiplier'] = 1.0  # 'hourly' = 12, '5 minutes' = 1'
pluginGlobal['unitTable']['m3']['formatTotaldivisor'] = 1.0
pluginGlobal['unitTable']['m3']['formatCurrent'] = "%d"
pluginGlobal['unitTable']['m3']['formatTotal'] = "%d"
pluginGlobal['unitTable']['m3']['currentUnits'] = 'cubic metres'                               
pluginGlobal['unitTable']['m3']['accumUnits'] = 'cubic metres'

pluginGlobal['unitTable']['ft3'] = {}
pluginGlobal['unitTable']['ft3']['measurementTimeMultiplier'] = 1.0  # 'hourly' = 12, '5 minutes' = 1'
pluginGlobal['unitTable']['ft3']['formatTotaldivisor'] = 1.0
pluginGlobal['unitTable']['ft3']['formatCurrent'] = "%d"
pluginGlobal['unitTable']['ft3']['formatTotal'] = "%d"
pluginGlobal['unitTable']['ft3']['currentUnits'] = 'cubic feet'                               
pluginGlobal['unitTable']['ft3']['accumUnits'] = 'cubic feet'

pluginGlobal['unitTable']['gallons'] = {}
pluginGlobal['unitTable']['gallons']['measurementTimeMultiplier'] = 1.0  # 'hourly' = 12, '5 minutes' = 1'
pluginGlobal['unitTable']['gallons']['formatTotaldivisor'] = 1.0
pluginGlobal['unitTable']['gallons']['formatCurrent'] = "%d"
pluginGlobal['unitTable']['gallons']['formatTotal'] = "%d"
pluginGlobal['unitTable']['gallons']['currentUnits'] = 'gallons'                               
pluginGlobal['unitTable']['gallons']['accumUnits'] = 'gallons'                               


pluginGlobal['config'] = {}
pluginGlobal['config']['address'] = ''
pluginGlobal['config']['clientId'] = ''
pluginGlobal['config']['secret'] = ''
pluginGlobal['config']['userName'] = ''
pluginGlobal['config']['password'] = ''

pluginGlobal['config']['appName'] = ''  # Not sure what this is for! Name provided by Get ServiceLocations Smappee call

pluginGlobal['config']['accessToken'] = ''
pluginGlobal['config']['refreshToken'] = ''
pluginGlobal['config']['tokenExpiresIn'] = 0
pluginGlobal['config']['tokenExpiresDateTimeUtc'] = 0


pluginGlobal['config']['supportsElectricity'] = False
pluginGlobal['config']['supportsElectricityNet'] = False
pluginGlobal['config']['supportsElectricitySaved'] = False
pluginGlobal['config']['supportsSolar'] = False
pluginGlobal['config']['supportsSolarUsed'] = False
pluginGlobal['config']['supportsSolarExported'] = False
pluginGlobal['config']['supportsSensor'] = False

# Initialise Global arrays to store internal details about Smappees, Smappee Appliances & Plugs
pluginGlobal['pluginInitialised'] = False
pluginGlobal['consumptionDataReceived'] = False  # Used to signify it is now OK to get Events
pluginGlobal['smappeeServiceLocationIdToDevId'] = {}  # Used to derive Smappee Device Ids from Smappee Service Location Ids
pluginGlobal['smappees'] = {}
pluginGlobal['smappeeAppliances'] = {}
pluginGlobal['smappeePlugs'] = {}

pluginGlobal['deviceFolderId'] = 0
pluginGlobal['variableFolderId'] = 0

pluginGlobal['polling'] = {}
pluginGlobal['polling']['status'] = False
pluginGlobal['polling']['seconds'] = float(300.0)  # 5 minutes
pluginGlobal['polling']['threadEnd'] = False

pluginGlobal['debug'] = {}
pluginGlobal['debug']['initialised']   = False  # Indicates whether the logging has been initialised and logging can be performed
pluginGlobal['debug']['active']        = False  # if False it indicates no debugging is active else it indicates that at least one type of debug is active
pluginGlobal['debug']['detailed']      = False  # For detailed debugging
pluginGlobal['debug']['interface']     = False  # For logging commands sent to and received from the Smappee interface 
pluginGlobal['debug']['polling']       = False  # For polling debugging
pluginGlobal['debug']['deviceFactory'] = False  # For device factory debugging
pluginGlobal['debug']['methodTrace']   = False  # For displaying method invocations i.e. trace method

methodNameForTrace = lambda: inspect.stack()[1][3]


# Logging Types
FACTORY   = 1   # FAC
DETAIL    = 2   # DET
ERROR     = 3   # ERR
INFO      = 4   # INF
POLLING   = 5   # POL
METHOD    = 6   # MET
INTERFACE = 7   # INT 

def autolog(logType, message):
    global pluginGlobal

    if pluginGlobal['debug']['initialised'] == False:
        if logType == INFO: 
            indigo.server.log(message)
        elif logType == ERROR:
            indigo.server.log(message, isError=True)
        return

    if logType == INFO:
        logTime = datetime.datetime.now().strftime("%H:%M:%S")
        pluginGlobal['autologger'].info(str('%s [INF]: %s' %(logTime, message)))
        indigo.server.log(message)
        return
    elif logType == ERROR:
        logTime = datetime.datetime.now().strftime("%H:%M:%S")
        pluginGlobal['autologger'].info(str('%s [ERR]: %s' %(logTime, message)))
        indigo.server.log(message, isError=True)
        return
    else:
        if pluginGlobal['debug']['active']  == False:
            return

    logTime = datetime.datetime.now().strftime("%H:%M:%S")
        
    if logType == DETAIL:
        if pluginGlobal['debug']['detailed']  == True:
            pluginGlobal['autologger'].info(str('%s [DET]: %s' %(logTime, message)))
    elif logType == FACTORY:
        if pluginGlobal['debug']['deviceFactory']  == True:
            pluginGlobal['autologger'].info(str('%s [FAC]: %s' %(logTime, message)))
    elif logType == INTERFACE:
        if pluginGlobal['debug']['interface']  == True:
            pluginGlobal['autologger'].info(str('%s [INT]: %s' %(logTime, message)))
    elif logType == METHOD:
        if pluginGlobal['debug']['methodTrace']  == True:
            pluginGlobal['autologger'].info(str('%s [MTH]: %s' %(logTime, message)))
    elif logType == POLLING:
        if pluginGlobal['debug']['polling']  == True:
            pluginGlobal['autologger'].info(str('%s [POL]: %s' %(logTime, message)))
    else:
        indigo.server.log(u'AUTOLOG LOGGING - INVALID TYPE: %s' % (logType), isError=True)
        indigo.server.log(message, isError=True)



class ThreadPolling(threading.Thread):

    def __init__(self, event, commandToSendqueue):

        threading.Thread.__init__(self)

        global pluginGlobal

        self.pollStop = event
        self.sendQueue = commandToSendqueue

        self.Testing123 = 'ABC'

        autolog(POLLING, u"Initialising Polling thread to poll at %f second intervals" % (pluginGlobal['polling']['seconds']))


    def run(self):
        global pluginGlobal
        autolog(METHOD, u"%s" %  (methodNameForTrace()))  

        try:
            autolog(POLLING, u"Polling thread running")  

            time.sleep(5)  # Wait 5 seconds before commencing polling - gives plugin time to start                        "

            autolog(POLLING, u"smappeeServiceLocationIdToDevId = %s" % (pluginGlobal['smappeeServiceLocationIdToDevId']))
            for serviceLocationId, serviceLocationDetails in pluginGlobal['smappeeServiceLocationIdToDevId'].iteritems():
                self.sendQueue.put(["GET_CONSUMPTION",str(serviceLocationId)])  # 1st time
                self.sendQueue.put(["GET_EVENTS",str(serviceLocationId)])  # 1st time
                self.sendQueue.put(["GET_SENSOR_CONSUMPTION",str(serviceLocationId)])  # 1st time

            while not self.pollStop.wait(pluginGlobal['polling']['seconds']):
                if self.pollStop.isSet():
                    if pluginGlobal['polling']['threadEnd'] == True:
                        break
                    else:
                        self.pollStop.clear()
                autolog(POLLING, u"Now polling at %f second intervals" % (pluginGlobal['polling']['seconds']))

                for serviceLocationId, serviceLocationDetails in pluginGlobal['smappeeServiceLocationIdToDevId'].iteritems():
                    self.sendQueue.put(["GET_CONSUMPTION",str(serviceLocationId)])
                    self.sendQueue.put(["GET_EVENTS",str(serviceLocationId)])
                    self.sendQueue.put(["GET_SENSOR_CONSUMPTION",str(serviceLocationId)])

        except StandardError, e:
            autolog(ERROR, u"StandardError detected in Smappee Polling Thread. Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))   


        autolog(POLLING, u"Polling thread ending")


class ThreadInteractWithSmappee(threading.Thread):

    # This class controls the sending of commands to Smappee and handles its response.
    # It receives high level commands to send to Smappee from a queue which it waits on
    #   and queues replies for handling by the runConcurrent thread

    # It contains the logic for correctly formatting the the high level commands into the specific formats
    #   required by Smappee. This keeps all the Smappee specific logic in one place.

    def __init__(self, commandToSendqueue, responseToReturnQueue):

        threading.Thread.__init__(self)
        self.sendQueue = commandToSendqueue
        self.returnQueue = responseToReturnQueue

        autolog(INTERFACE, u"Initialising Smappee Command thread")  


    def convertUnicode(self, input):
        if isinstance(input, dict):
            return dict([(self.convertUnicode(key), self.convertUnicode(value)) for key, value in input.iteritems()])
        elif isinstance(input, list):
            return [self.convertUnicode(element) for element in input]
        elif isinstance(input, unicode):
            return input.encode('utf-8')
        else:
            return input

  
    def run(self):
        global pluginGlobal
        autolog(METHOD, u"ThreadInteractWithSmappee; %s" %  (methodNameForTrace()))  
 
        try:
            autolog(INTERFACE, u"Smappee Command Thread initialised.")
            keepThreadActive = True    
            while keepThreadActive:

                try:
                    commandToSend = self.sendQueue.get(True,5)
                    autolog(INTERFACE, u"Command to send to Smappee [Type=%s]: %s" % (type(commandToSend),commandToSend))

                    smappeeCommand = commandToSend[0]

                    if smappeeCommand == 'ENDTHREAD':
                        keepThreadActive = False 

                    elif smappeeCommand == 'GET_CONSUMPTION' or smappeeCommand == 'RESET_CONSUMPTION':

                        try:
                            self.serviceLocationId  = commandToSend[1]
                            self.electricityId      = int(pluginGlobal['smappeeServiceLocationIdToDevId'][self.serviceLocationId]['electricityId'])
                            self.electricityNetId   = int(pluginGlobal['smappeeServiceLocationIdToDevId'][self.serviceLocationId]['electricityNetId']) 
                            self.electricitySavedId = int(pluginGlobal['smappeeServiceLocationIdToDevId'][self.serviceLocationId]['electricitySavedId'])
                            self.solarId            = int(pluginGlobal['smappeeServiceLocationIdToDevId'][self.serviceLocationId]['solarId'])
                            self.solarUsedId        = int(pluginGlobal['smappeeServiceLocationIdToDevId'][self.serviceLocationId]['solarUsedId'])
                            self.solarExportedId    = int(pluginGlobal['smappeeServiceLocationIdToDevId'][self.serviceLocationId]['solarExportedId'])
                        except Exception, e:
                            autolog(ERROR, u"Debugging Error detected in Smappee Command Thread. Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))   

                        if self.electricityId == 0 and self.solarId == 0:
                            pass
                            autolog(INTERFACE, u"%s - Smappee Base Devices [ELECTRICITY and SOLAR PV] not defined" % (smappeeCommand))
                        else:
                            autolog(INTERFACE, u"%s - GET_CONSUMPTION - smappeeServiceLocationIdToDevId = [%s]" % (smappeeCommand, pluginGlobal['smappeeServiceLocationIdToDevId']))

                            self.currentTimeUtc = time.mktime(indigo.server.getTime().timetuple())
                            self.currentTimeDay = int(datetime.datetime.fromtimestamp(self.currentTimeUtc).strftime('%j'))
                            autolog(INTERFACE, u"%s - self.currentTimeUtc[%s]=[%s], DAY=[%s]" % (smappeeCommand, type(self.currentTimeUtc), self.currentTimeUtc, self.currentTimeDay))

                            if self.electricityId != 0:
                                devElectricity = indigo.devices[self.electricityId]

                                autolog(INTERFACE, u"%s - lastReadingElectricityUtc[%s] =[%s]" % (smappeeCommand, type(pluginGlobal['smappees'][devElectricity.id]['lastReadingElectricityUtc']), pluginGlobal['smappees'][devElectricity.id]['lastReadingElectricityUtc']))
                                self.lastReadingElectricityDay = int(datetime.datetime.fromtimestamp(float(pluginGlobal['smappees'][devElectricity.id]['lastReadingElectricityUtc']/1000)).strftime('%j'))

                                autolog(INTERFACE, u"%s - lastReadingElectricityDay=[%s] vs currentTimeDay=[%s]" % (smappeeCommand, self.lastReadingElectricityDay, self.currentTimeDay))

                                if pluginGlobal['smappees'][devElectricity.id]['lastReadingElectricityUtc'] > 0 and self.lastReadingElectricityDay == self.currentTimeDay and smappeeCommand != 'RESET_CONSUMPTION':
                                    self.fromTimeElectricityUtc = str(int(pluginGlobal['smappees'][devElectricity.id]['lastReadingElectricityUtc']))
                                else:
                                    self.fromTimeElectricityUtc = str("%s001" % (int(time.mktime(datetime.datetime.combine(datetime.date.today(), datetime.time()).timetuple()))))
                                    pluginGlobal['smappees'][devElectricity.id]['lastReadingElectricityUtc'] = float(float(self.fromTimeElectricityUtc) - 1.0)
                                    if "accumEnergyTotal" in devElectricity.states:
                                        kwh = 0.0
                                        kwhStr = "%0.3f kWh" % (kwh)
                                        autolog(INFO, u"reset '%s' electricity total to 0.0" % (devElectricity.name))
                                        kwhReformatted = float(str("%0.3f" % (kwh)))
                                        devElectricity.updateStateOnServer("accumEnergyTotal", kwhReformatted, uiValue=kwhStr)

                            if self.electricityNetId != 0:
                                devElectricityNet = indigo.devices[self.electricityNetId]

                                autolog(INTERFACE, u"%s - lastReadingElectricityNetUtc[%s] =[%s]" % (smappeeCommand, type(pluginGlobal['smappees'][devElectricityNet.id]['lastReadingElectricityNetUtc']), pluginGlobal['smappees'][devElectricityNet.id]['lastReadingElectricityNetUtc']))
                                self.lastReadingElectricityNetDay = int(datetime.datetime.fromtimestamp(float(pluginGlobal['smappees'][devElectricityNet.id]['lastReadingElectricityNetUtc']/1000)).strftime('%j'))

                                autolog(INTERFACE, u"%s - lastReadingElectricityNetDay=[%s] vs currentTimeDay=[%s]" % (smappeeCommand, self.lastReadingElectricityNetDay, self.currentTimeDay))

                                if pluginGlobal['smappees'][devElectricityNet.id]['lastReadingElectricityNetUtc'] > 0 and self.lastReadingElectricityNetDay == self.currentTimeDay and smappeeCommand != 'RESET_CONSUMPTION':
                                    self.fromTimeElectricityNetUtc = str(int(pluginGlobal['smappees'][devElectricityNet.id]['lastReadingElectricityNetUtc']))
                                else:
                                    self.fromTimeElectricityNetUtc = str("%s001" % (int(time.mktime(datetime.datetime.combine(datetime.date.today(), datetime.time()).timetuple()))))
                                    pluginGlobal['smappees'][devElectricityNet.id]['lastReadingElectricityNetUtc'] = float(float(self.fromTimeElectricityNetUtc) - 1.0)
                                    if "accumEnergyTotal" in devElectricityNet.states:
                                        kwh = 0.0
                                        kwhStr = str("%0.3f kWh" % (kwh))
                                        autolog(INFO, u"reset '%s' electricity net total to 0.0" % (devElectricityNet.name))
                                        kwhReformatted = float(str("%0.3f" % (kwh)))
                                        devElectricityNet.updateStateOnServer("accumEnergyTotal", kwhReformatted, uiValue=kwhStr)

                            if self.electricitySavedId != 0:
                                devElectricitySaved = indigo.devices[self.electricitySavedId]

                                autolog(INTERFACE, u"%s - lastReadingElectricitySavedUtc[%s] =[%s]" % (smappeeCommand, type(pluginGlobal['smappees'][devElectricitySaved.id]['lastReadingElectricitySavedUtc']), pluginGlobal['smappees'][devElectricitySaved.id]['lastReadingElectricitySavedUtc']))
                                self.lastReadingElectricitySavedDay = int(datetime.datetime.fromtimestamp(float(pluginGlobal['smappees'][devElectricitySaved.id]['lastReadingElectricitySavedUtc']/1000)).strftime('%j'))

                                autolog(INTERFACE, u"%s - lastReadingElectricitySavedDay=[%s] vs currentTimeDay=[%s]" % (smappeeCommand, self.lastReadingElectricitySavedDay, self.currentTimeDay))

                                if pluginGlobal['smappees'][devElectricitySaved.id]['lastReadingElectricitySavedUtc'] > 0 and self.lastReadingElectricitySavedDay == self.currentTimeDay and smappeeCommand != 'RESET_CONSUMPTION':
                                    self.fromTimeElectricitySavedUtc = str(int(pluginGlobal['smappees'][devElectricitySaved.id]['lastReadingElectricitySavedUtc']))
                                else:
                                    self.fromTimeElectricitySavedUtc = str("%s001" % (int(time.mktime(datetime.datetime.combine(datetime.date.today(), datetime.time()).timetuple()))))
                                    pluginGlobal['smappees'][devElectricitySaved.id]['lastReadingElectricitySavedUtc'] = float(float(self.fromTimeElectricitySavedUtc) - 1.0)
                                    if "accumEnergyTotal" in devElectricitySaved.states:
                                        kwh = 0.0
                                        kwhStr = str("%0.3f kWh" % (kwh))
                                        autolog(INFO, u"reset '%s' electricity Saved total to 0.0" % (devElectricitySaved.name))
                                        kwhReformatted = float(str("%0.3f" % (kwh)))
                                        devElectricitySaved.updateStateOnServer("accumEnergyTotal", kwhReformatted, uiValue=kwhStr)

                            if self.solarId != 0:
                                devSolar = indigo.devices[self.solarId]

                                autolog(INTERFACE, u"%s - lastReadingSolarUtc[%s] =[%s]" % (smappeeCommand, type(pluginGlobal['smappees'][devSolar.id]['lastReadingSolarUtc']), pluginGlobal['smappees'][devSolar.id]['lastReadingSolarUtc']))
                                self.lastReadingSolarDay = int(datetime.datetime.fromtimestamp(float(pluginGlobal['smappees'][devSolar.id]['lastReadingSolarUtc']/1000)).strftime('%j'))

                                autolog(INTERFACE, u"%s - lastReadingSolarDay=[%s] vs currentTimeDay=[%s]" % (smappeeCommand, self.lastReadingSolarDay, self.currentTimeDay))

                                if pluginGlobal['smappees'][devSolar.id]['lastReadingSolarUtc'] > 0 and self.lastReadingSolarDay == self.currentTimeDay and smappeeCommand != 'RESET_CONSUMPTION':
                                    self.fromTimeSolarUtc = str(int(pluginGlobal['smappees'][devSolar.id]['lastReadingSolarUtc']))
                                else:
                                    self.fromTimeSolarUtc = str("%s001" % (int(time.mktime(datetime.datetime.combine(datetime.date.today(), datetime.time()).timetuple()))))
                                    pluginGlobal['smappees'][devSolar.id]['lastReadingSolarUtc'] = float(float(self.fromTimeSolarUtc) - 1.0)
                                    if "accumEnergyTotal" in devSolar.states:
                                        kwh = 0.0
                                        kwhStr = str("%0.3f kWh" % (kwh))
                                        autolog(INFO, u"reset '%s' solar generation total to 0.0" % (devSolar.name))
                                        kwhReformatted = float(str("%0.3f" % (kwh)))
                                        devSolar.updateStateOnServer("accumEnergyTotal", kwhReformatted, uiValue=kwhStr)

                            if self.solarUsedId != 0:
                                devSolarUsed = indigo.devices[self.solarUsedId]

                                autolog(INTERFACE, u"%s - lastReadingSolarUsedUtc[%s] =[%s]" % (smappeeCommand, type(pluginGlobal['smappees'][devSolarUsed.id]['lastReadingSolarUsedUtc']), pluginGlobal['smappees'][devSolarUsed.id]['lastReadingSolarUsedUtc']))
                                self.lastReadingSolarUsedDay = int(datetime.datetime.fromtimestamp(float(pluginGlobal['smappees'][devSolarUsed.id]['lastReadingSolarUsedUtc']/1000)).strftime('%j'))

                                autolog(INTERFACE, u"%s - lastReadingSolarUsedDay=[%s] vs currentTimeDay=[%s]" % (smappeeCommand, self.lastReadingSolarUsedDay, self.currentTimeDay))

                                if pluginGlobal['smappees'][devSolarUsed.id]['lastReadingSolarUsedUtc'] > 0 and self.lastReadingSolarUsedDay == self.currentTimeDay and smappeeCommand != 'RESET_CONSUMPTION':
                                    self.fromTimeSolarUsedUtc = str(int(pluginGlobal['smappees'][devSolarUsed.id]['lastReadingSolarUsedUtc']))
                                else:
                                    self.fromTimeSolarUsedUtc = str("%s001" % (int(time.mktime(datetime.datetime.combine(datetime.date.today(), datetime.time()).timetuple()))))
                                    pluginGlobal['smappees'][devSolarUsed.id]['lastReadingSolarUsedUtc'] = float(float(self.fromTimeSolarUtc) - 1.0)
                                    if "accumEnergyTotal" in devSolarUsed.states:
                                        kwh = 0.0
                                        kwhStr = str("%0.3f kWh" % (kwh))
                                        autolog(INFO, u"reset '%s' solar used total to 0.0" % (devSolarUsed.name))
                                        kwhReformatted = float(str("%0.3f" % (kwh)))
                                        devSolarUsed.updateStateOnServer("accumEnergyTotal", kwhReformatted, uiValue=kwhStr)

                            if self.solarExportedId != 0:
                                devSolarExported = indigo.devices[self.solarExportedId]

                                autolog(INTERFACE, u"%s - lastReadingSolarExportedUtc[%s] =[%s]" % (smappeeCommand, type(pluginGlobal['smappees'][devSolarExported.id]['lastReadingSolarExportedUtc']), pluginGlobal['smappees'][devSolarExported.id]['lastReadingSolarExportedUtc']))
                                self.lastReadingSolarExportedDay = int(datetime.datetime.fromtimestamp(float(pluginGlobal['smappees'][devSolarExported.id]['lastReadingSolarExportedUtc']/1000)).strftime('%j'))

                                autolog(INTERFACE, u"%s - lastReadingSolarExportedDay=[%s] vs currentTimeDay=[%s]" % (smappeeCommand, self.lastReadingSolarExportedDay, self.currentTimeDay))

                                if pluginGlobal['smappees'][devSolarExported.id]['lastReadingSolarExportedUtc'] > 0 and self.lastReadingSolarExportedDay == self.currentTimeDay and smappeeCommand != 'RESET_CONSUMPTION':
                                    self.fromTimeSolarExportedUtc = str(int(pluginGlobal['smappees'][devSolarExported.id]['lastReadingSolarExportedUtc']))
                                else:
                                    self.fromTimeSolarExportedUtc = str("%s001" % (int(time.mktime(datetime.datetime.combine(datetime.date.today(), datetime.time()).timetuple()))))
                                    pluginGlobal['smappees'][devSolarExported.id]['lastReadingSolarExportedUtc'] = float(float(self.fromTimeSolarUtc) - 1.0)
                                    if "accumEnergyTotal" in devSolarExported.states:
                                        kwh = 0.0
                                        kwhStr = str("%0.3f kWh" % (kwh))
                                        autolog(INFO, u"reset '%s' solar exported total to 0.0" % (devSolarExported.name))
                                        kwhReformatted = float(str("%0.3f" % (kwh)))
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

                            pluginGlobal['consumptionDataReceived'] = True  # Set to True once the self.fromTimeUtc has been determined so getting event data doesn't fail

                            self.toTimeUtc = str("%s000" % (int(self.currentTimeUtc  + float(3600))))  # Add +1 hour to current time

                            autolog(INTERFACE, u"%s - From=[%s], To=[%s]" % (smappeeCommand, self.fromTimeUtc, self.toTimeUtc))

                            self.aggregationType = '1'  # 1 = 5 min values (only available for the last 14 days), 2 = hourly values, 3 = daily values, 4 = monthly values, 5 = yearly values

                            process = subprocess.Popen(['curl', '-H', 'Authorization: Bearer ' + pluginGlobal['config']['accessToken'], 'https://app1pub.smappee.net/dev/v1/servicelocation/' + self.serviceLocationId + '/consumption?aggregation=' + self.aggregationType + '&from=' + self.fromTimeUtc + '&to=' + self.toTimeUtc, ''], stdout=subprocess.PIPE)

                            response = ""
                            for line in process.stdout:
                                # autolog(INTERFACE, u"Response to '%s' = %s" % (smappeeCommand, line))
                                response = response + line.strip()

                            autolog(INTERFACE, u"MERGED Response to '%s' = %s" % (smappeeCommand, response))
                            
                            self.returnQueue.put([smappeeCommand, self.serviceLocationId, response])

                    elif smappeeCommand == 'GET_SENSOR_CONSUMPTION' or smappeeCommand == 'RESET_SENSOR_CONSUMPTION':

                        self.serviceLocationId  = commandToSend[1]

                        self.sensorFromTimeUtc = 0

                        for key, value in pluginGlobal['smappeeServiceLocationIdToDevId'][self.serviceLocationId]['sensorIds'].iteritems():
                            # indigo.server.log(u'GET_SENSOR_CONSUMPTION - sensorIds = [Type = %s] %s' % (type(pluginGlobal['smappeeServiceLocationIdToDevId'][self.serviceLocationId]['sensorIds']), pluginGlobal['smappeeServiceLocationIdToDevId'][self.serviceLocationId]['sensorIds']))
                            autolog(INTERFACE, u'GET_SENSOR_CONSUMPTION = [Key = %s] %s' % (key, value))
                            autolog(INTERFACE, u'GET_SENSOR_CONSUMPTION = [DevId = %s]' % (str(value['devId'])))

                            if value['devId'] == 0 :
                                autolog(INTERFACE, u"%s - GET_SENSOR_CONSUMPTION - No Indigo Sensor Device defined for Smappee Sensor %s" % (smappeeCommand, key))
                                continue

                            # autolog(INTERFACE, u"%s - GET_SENSOR_CONSUMPTION - smappeeServiceLocationIdToDevId = [%s]" % (smappeeCommand, pluginGlobal['smappeeServiceLocationIdToDevId']))

                            sensorId = value['devId']

                            devSensor = indigo.devices[sensorId]

                            autolog(INTERFACE, u"GET_SENSOR_CONSUMPTION - %s - lastReadingSensorUtc[%s] =[%s]" % (smappeeCommand, type(pluginGlobal['smappees'][devSensor.id]['lastReadingSensorUtc']), pluginGlobal['smappees'][devSensor.id]['lastReadingSensorUtc']))
                            self.lastReadingSensorDay = int(datetime.datetime.fromtimestamp(float(pluginGlobal['smappees'][devSensor.id]['lastReadingSensorUtc']/1000)).strftime('%j'))

                            autolog(INTERFACE, u"GET_SENSOR_CONSUMPTION - %s - lastReadingSensorDay=[%s] vs currentTimeDay=[%s]" % (smappeeCommand, self.lastReadingSensorDay, self.currentTimeDay))

                            if pluginGlobal['smappees'][devSensor.id]['lastReadingSensorUtc'] > 0 and self.lastReadingSensorDay == self.currentTimeDay and smappeeCommand != 'RESETSENSORCONSUMPTION':
                                self.fromTimeSensorUtc = str(int(pluginGlobal['smappees'][devSensor.id]['lastReadingSensorUtc']))
                            else:
                                self.fromTimeSensorUtc = str("%s001" % (int(time.mktime(datetime.datetime.combine(datetime.date.today(), datetime.time()).timetuple()))))
                                pluginGlobal['smappees'][devSensor.id]['lastReadingSensorUtc'] = float(float(self.fromTimeSensorUtc) - 1.0)
                                if "accumEnergyTotal" in devSensor.states:
                                    kwh = 0.0
                                    kwhStr = "%0.3f kWh" % (kwh)
                                    autolog(INFO, u"reset '%s' sensor total to 0.0" % (devSensor.name))
                                    kwhReformatted = float(str("%0.3f" % (kwh)))
                                    devSensor.updateStateOnServer("accumEnergyTotal", kwhReformatted, uiValue=kwhStr)

                            self.sensorFromTimeUtc = self.fromTimeSensorUtc

                            self.sensorToTimeUtc = str("%s000" % (int(self.currentTimeUtc  + float(3600))))  # Add +1 hour to current time

                            autolog(INTERFACE, u"GET_SENSOR_CONSUMPTION [BC] - %s - SENSOR From=[%s], To=[%s]" % (smappeeCommand, self.sensorFromTimeUtc, self.sensorToTimeUtc))

                            self.aggregationType = '1'  # 1 = 5 min values (only available for the last 14 days), 2 = hourly values, 3 = daily values, 4 = monthly values, 5 = yearly values


                            self.sensorAddress = str(int(str(devSensor.address)[2:4]))
                            autolog(INTERFACE, u"Sensor Address = '%s'" % (self.sensorAddress))

                            process = subprocess.Popen(['curl', '-H', 'Authorization: Bearer ' + pluginGlobal['config']['accessToken'], 'https://app1pub.smappee.net/dev/v1/servicelocation/' + self.serviceLocationId + '/sensor/'  + self.sensorAddress + '/consumption?aggregation=' + self.aggregationType + '&from=' + self.sensorFromTimeUtc + '&to=' + self.sensorToTimeUtc, ''], stdout=subprocess.PIPE)

                            response = ""
                            for line in process.stdout:
                                # autolog(INTERFACE, u"Response to '%s' = %s" % (smappeeCommand, line))
                                response = response + line.strip()

                            autolog(INTERFACE, u"GET_SENSOR_CONSUMPTION [AC] - MERGED Sensor Response to '%s' = %s" % (smappeeCommand, response))

                            # testTimeStamp1 = '1461488100000'  # TEST DATA
                            # testTimeStamp2 = '1461491400000'  # TEST DATA
                            # testTimeStamp3 = '1461494700000'  # TEST DATA

                            # pluginGlobal['testdata']['temperature'].rotate(-1)
                            # temperature = str(pluginGlobal['testdata']['temperature'][0])
                            # pluginGlobal['testdata']['humidity'].rotate(-1)
                            # humidity = str(pluginGlobal['testdata']['humidity'][0])
                            # pluginGlobal['testdata']['batteryLevel'].rotate(-1)
                            # batteryLevel = str(pluginGlobal['testdata']['batteryLevel'][0])
                            # pluginGlobal['testdata']['value1'].rotate(-1)
                            # value1 = str(pluginGlobal['testdata']['value1'][0])
                            # pluginGlobal['testdata']['value2'].rotate(-1)
                            # value2 = str(pluginGlobal['testdata']['value2'][0])

                            # utc = int(time.time())
                            # testTimeStamp1 = str(int(utc-120)*1000)
                            # testTimeStamp2 = str(int(utc-60)*1000)
                            # testTimeStamp3 = str(int(utc)*1000)


                            # ' + temperature + '
                            # ' + humidity + '
                            # ' + batteryLevel + '
                            # ' + value1 + '
                            # ' + value2 + '

                            #response = response[:-3] + '[{"timestamp": ' + testTimeStamp1 + ',"value1": 11.0,"value2": 2.0,"temperature": 226.0,"humidity": 41.0,"battery": 100.0},{"timestamp": ' + testTimeStamp2 + ',"value1": 9.0,"value2": 3.0,"temperature": 220.0,"humidity": 39.0,"battery": 100.0},{"timestamp": ' + testTimeStamp3 + ',"value1": 10.0,"value2": 1.0,"temperature": 202.0,"humidity": 39.0,"battery": 100.0}], "error": "This is a sample error from Smappee","UNKNOWN KEY TEST" : "THIS IS AN ERROR VALUE"}'
                            #response = response[:-3] + '[{"timestamp": ' + testTimeStamp1 + ',"value1": ' + value1 + ',"value2": ' + value2 + ',"temperature": ' + temperature + ',"humidity": ' + humidity + ',"battery": ' + batteryLevel + '},{"timestamp": ' + testTimeStamp2 + ',"value1": ' + value1 + ',"value2": ' + value2 + ',"temperature": ' + temperature + ',"humidity": ' + humidity + ',"battery": ' + batteryLevel + '},{"timestamp": ' + testTimeStamp3 + ',"value1": ' + value1 + ',"value2": ' + value2 + ',"temperature": ' + temperature + ',"humidity": ' + humidity + ',"battery": ' + batteryLevel + '}]}'

                            # autolog(INTERFACE, u"GET_SENSOR_CONSUMPTION [AC-FIXED] - MERGED Sensor Response to '%s' = %s" % (smappeeCommand, response))
                            
                            self.returnQueue.put([smappeeCommand, self.serviceLocationId, response])



                    elif smappeeCommand == 'GET_EVENTS' and pluginGlobal['consumptionDataReceived'] == True:
                        self.serviceLocationId = commandToSend[1]

                        autolog(INTERFACE, u"%s - smappeeServiceLocationIdToDevId = [%s]" % (smappeeCommand, pluginGlobal['smappeeServiceLocationIdToDevId']))
                        if pluginGlobal['smappeeServiceLocationIdToDevId'][self.serviceLocationId]['electricityId'] != 0:
                            dev = indigo.devices[pluginGlobal['smappeeServiceLocationIdToDevId'][self.serviceLocationId]['electricityId']]

                            self.toTimeUtc = time.mktime(indigo.server.getTime().timetuple())
                            autolog(INTERFACE, u"%s - self.toTimeUtc[%s] =[%s]" % (smappeeCommand, type(self.toTimeUtc), self.toTimeUtc))

                            autolog(INTERFACE, u"%s - lastReadingElectricityUtc[%s] =[%s]" % (smappeeCommand, type(pluginGlobal['smappees'][dev.id]['lastReadingElectricityUtc']), pluginGlobal['smappees'][dev.id]['lastReadingElectricityUtc']))
                            self.lastReadingDay = int(datetime.datetime.fromtimestamp(float(pluginGlobal['smappees'][dev.id]['lastReadingElectricityUtc']/1000)).strftime('%j'))

                            self.currentTimeDay = int(datetime.datetime.fromtimestamp(self.toTimeUtc).strftime('%j'))
                            autolog(INTERFACE, u"%s - lastReadingDay=[%s] vs currentTimeDay=[%s]" % (smappeeCommand, self.lastReadingDay, self.currentTimeDay))

                            self.toTimeUtc = str("%s000" % (int(self.toTimeUtc  + float(3600))))

                            autolog(INTERFACE, u"%s - From=[%s], To=[%s]" % (smappeeCommand, self.fromTimeUtc, self.toTimeUtc))

                            self.appliances = 'applianceId=1&applianceId=2&applianceId=15&applianceId=3&applianceId=34'
                            self.maxNumber = '20'
                            process = subprocess.Popen(['curl', '-H', 'Authorization: Bearer ' + pluginGlobal['config']['accessToken'], 'https://app1pub.smappee.net/dev/v1/servicelocation/' + self.serviceLocationId + '/events?' + self.appliances + '&maxNumber=' + self.maxNumber + '&from=' + self.fromTimeUtc + '&to=' + self.toTimeUtc, ''], stdout=subprocess.PIPE)

                            response = ""
                            for line in process.stdout:
                                autolog(INTERFACE, u"Response to '%s' = %s" % (smappeeCommand, line))
                                response = response + line.strip()

                            autolog(INTERFACE, u"MERGED Response to '%s' = %s" % (smappeeCommand, response))
                            
                            self.returnQueue.put([smappeeCommand, self.serviceLocationId, response])
                    elif smappeeCommand == 'INITIALISE':
                        process = subprocess.Popen(['curl', '-XPOST', '-d', 'client_id=' + pluginGlobal['config']['clientId'] + '&client_secret=' + pluginGlobal['config']['secret'] + '&grant_type=password&username=' + pluginGlobal['config']['userName']  + '&password=' + pluginGlobal['config']['password'], 'https://app1pub.smappee.net/dev/v1/oauth2/token', '-d', ''], stdout=subprocess.PIPE)

                        response = ""
                        for line in process.stdout:
                            # autolog(INTERFACE, u"Line Response to '%s' = %s" % (smappeeCommand, line))
                            response = response + line.strip()

                        autolog(INTERFACE, u"MERGED Response to '%s' = %s" % (smappeeCommand, response))
                        
                        self.returnQueue.put(['INITIALISE', "", response])

                        continue  # Continue while loop i.e. skip refresh authentication token check at end of this while loop as we have only just authenticated

                    elif smappeeCommand == 'GET_SERVICE_LOCATIONS': 
                        process = subprocess.Popen(['curl', '-H', 'Authorization: Bearer ' + pluginGlobal['config']['accessToken'], 'https://app1pub.smappee.net/dev/v1/servicelocation', ''], stdout=subprocess.PIPE)

                        response = ""
                        for line in process.stdout:
                            # autolog(INTERFACE, u"Response to '%s' = %s" % (smappeeCommand, line))
                            response = response + line.strip()

                        autolog(INTERFACE, u"MERGED Response to '%s' = %s" % (smappeeCommand, response))
                        
                        self.returnQueue.put(['GET_SERVICE_LOCATIONS', "", response])



                    elif smappeeCommand == 'GET_SERVICE_LOCATION_INFO':
                        self.serviceLocationId = commandToSend[1] 
                        process = subprocess.Popen(['curl', '-H', 'Authorization: Bearer ' + pluginGlobal['config']['accessToken'], 'https://app1pub.smappee.net/dev/v1/servicelocation/' + self.serviceLocationId + '/info', ''], stdout=subprocess.PIPE)

                        response = ""
                        for line in process.stdout:
                            # autolog(INTERFACE, u"Response to '%s' = %s" % (smappeeCommand, line))
                            response = response + line.strip()

                        # TESTING GAS / WATER [START]
                        # response = response[:-1]
                        # response = response + str(', "sensors": [{"id": 4, "name": "Sensor 4"}, {"id": 5, "name": "Sensor 5"}]}').strip()
                        # TESTING GAS / WATER [END]

                        autolog(INTERFACE, u"MERGED Response to '%s' = %s" % (smappeeCommand, response))
                        
                        self.returnQueue.put(['GET_SERVICE_LOCATION_INFO', self.serviceLocationId, response])

 
                    elif smappeeCommand == 'ON' or smappeeCommand == 'OFF':

                        # Format: 'ON|OFF', ServiceLocationId, ActuatorId 

                        self.serviceLocationId = commandToSend[1]
                        self.actuatorId = commandToSend[2]

                        process = subprocess.Popen(['curl', '-H', 'Content-Type: application/json', '-H', 'Authorization: Bearer ' + pluginGlobal['config']['accessToken'], '-d', '{}', 'https://app1pub.smappee.net/dev/v1/servicelocation/' + self.serviceLocationId + '/actuator/' + self.actuatorId + '/' + str(smappeeCommand).lower(), ''], stdout=subprocess.PIPE)

                        autolog(INTERFACE, u"DEBUG PROCESS [On/OFF]: [%s]:[%s]" % (type(commandToSend),commandToSend))


                        for line in process.stdout:
                            # autolog(INTERFACE, u"Response to '%s' = %s" % (smappeeCommand, line))
                            response = response + line.strip()

                        autolog(INTERFACE, u"MERGED Response to '%s' = %s" % (smappeeCommand, response))
                        
                        # No need to handle reponse

                    # Finally check if authentication token needs refreshing (but only if thread NOT ending)
                    if keepThreadActive == True:
                        self.currentTimeUTC = time.mktime(indigo.server.getTime().timetuple())
                        if self.currentTimeUTC > pluginGlobal['config']['tokenExpiresDateTimeUtc']:
                            autolog(INTERFACE, u"Refresh Token Request = %s" % (pluginGlobal['config']['refreshToken']))
                            autolog(INTERFACE, u"Refresh Token, currentUTC[%s] = %s, expiresUTC[%s] = %s" % (type(self.currentTimeUTC),self.currentTimeUTC,type(pluginGlobal['config']['tokenExpiresDateTimeUtc']),pluginGlobal['config']['tokenExpiresDateTimeUtc']))

                            process = subprocess.Popen(['curl', '-XPOST', '-H', 'application/x-www-form-urlencoded;charset=UTF-8', '-d', 'grant_type=refresh_token&refresh_token=' + pluginGlobal['config']['refreshToken'] + '&client_id=' + pluginGlobal['config']['clientId'] + '&client_secret=' + pluginGlobal['config']['secret'], 'https://app1pub.smappee.net/dev/v1/oauth2/token', '-d', ''], stdout=subprocess.PIPE)

                            response = ""
                            for line in process.stdout:
                                # autolog(INTERFACE, u"Line Response to Refresh Token = %s" % (line))
                                response = response + line.strip()

                            autolog(INTERFACE, u"MERGED Response to Refresh Token = %s" % (response))

                            self.returnQueue.put(['REFRESH_TOKEN', "", response])




                except autologQueueEmpty:
                    pass
                except StandardError, e:
                    autolog(ERROR, u"StandardError detected communicating with Smappee. Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))   

            if smappeeCommand == 'ENDTHREAD':
                autolog(INTERFACE, u"Command Thread ending.")   

        except StandardError, e:
            autolog(ERROR, u"StandardError detected in Smappee Command Thread. Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))   

        autolog(INTERFACE, u"Smappee Command Thread ended.")   
        thread.exit()


class Plugin(indigo.PluginBase):

    def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
        global pluginGlobal

        indigo.PluginBase.__init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs)

        pluginGlobal['plugin']['pluginId'] = pluginId
        pluginGlobal['plugin']['pluginDisplayName'] = pluginDisplayName
        pluginGlobal['plugin']['pluginVersion'] = pluginVersion
        # indigo.server.log(u'ID = %s, NAME = %s, VERSION = %s' % (pluginGlobal['plugin']['pluginId'], pluginGlobal['plugin']['pluginDisplayName'], pluginGlobal['plugin']['pluginVersion']), isError=True)

        self.testThis = 'ABC'
        self.nextTest = 'DEF'

        self.validatePrefsConfigUi(pluginPrefs)  # Validate the Plugin Config before plugin initialisation



    def __del__(self):

        indigo.PluginBase.__del__(self)


    def startup(self):
        global pluginGlobal
        # autolog(METHOD, u"%s" %  (methodNameForTrace()))  

        # Create process queues
        self.sendToSmappeeQueue = autologQueue()  # Used to queue commands to be sent to Smappee
        self.processQueue = autologQueue()        # Used to receive replies from Smappee

        # Initialise debug  
        pluginGlobal['debug']['detailed']      = bool(self.pluginPrefs.get("debugDetailed", False))
        pluginGlobal['debug']['deviceFactory'] = bool(self.pluginPrefs.get("debugDeviceFactory", False))
        pluginGlobal['debug']['interface']     = bool(self.pluginPrefs.get("debugInterface", False))
        pluginGlobal['debug']['methodTrace']   = bool(self.pluginPrefs.get("debugMethodTrace", False))
        pluginGlobal['debug']['polling']       = bool(self.pluginPrefs.get("debugPolling", False))

        pluginGlobal['debug']['active'] = pluginGlobal['debug']['detailed'] or pluginGlobal['debug']['deviceFactory'] or pluginGlobal['debug']['interface'] or pluginGlobal['debug']['methodTrace'] or pluginGlobal['debug']['polling']

        # Initialise validation flags - Used to ensure thread safe processing 
        self.validateDeviceFlag = {}
        self.validateActionFlags = {}

        # Create Smappee folder name in variables (for presets?) and devices (for smappee monitors, appliances and plugs)

        self.variableFolderName = "SMAPPEE"
        if (self.variableFolderName not in indigo.variables.folders):
            self.variableFolder = indigo.variables.folder.create(self.variableFolderName)
        pluginGlobal['variableFolderId'] = indigo.variables.folders.getId(self.variableFolderName)

        self.deviceFolderName = "SMAPPEE"
        if (self.deviceFolderName not in indigo.devices.folders):
            self.deviceFolder = indigo.devices.folder.create(self.deviceFolderName)
        pluginGlobal['deviceFolderId'] = indigo.devices.folders.getId(self.deviceFolderName)

        debugFile = str('%s/%s' %(pluginGlobal['debug']['debugFolder'], 'autolog/smappee/debug/debug.txt'))
        pluginGlobal['autologger'] = logging.getLogger(debugFile)
        pluginGlobal['autologger'].setLevel(logging.INFO)
        handler = TimedRotatingFileHandler(debugFile, when="midnight", interval=10, backupCount=6)
        pluginGlobal['autologger'].addHandler(handler)

        pluginGlobal['debug']['initialised'] = True  # To tell the debug logic it can now write to the debug file

        indigo.devices.subscribeToChanges()

        # define and start thread that will send commands to & receive commands from Smappee
        self.ThreadInteractWithSmappee = ThreadInteractWithSmappee(self.sendToSmappeeQueue, self.processQueue)
        self.ThreadInteractWithSmappee.start()

        # Now send an INITIALISE command (via queue) to Smappee to initialise the plugin
        self.sendToSmappeeQueue.put(['INITIALISE'])

        # Start the Polling thread
        if pluginGlobal['polling']['status'] == True and not hasattr(self, 'pollingThread'):
            pluginGlobal['polling']['threadEnd'] = False  # Just in case!
            self.pollingEvent = threading.Event()
            self.pollingThread = ThreadPolling(self.pollingEvent, self.sendToSmappeeQueue)
            self.pollingThread.start() 

        autolog(INFO, u"Initialisation in progress ...")


    def shutdown(self):
        global pluginGlobal
        autolog(METHOD, u"%s" %  (methodNameForTrace()))  

        autolog(INFO, u"Plugin shutdown requested")

        self.sendToSmappeeQueue.put(['ENDTHREAD'])

        if hasattr(self, 'pollingThread'):
            if pluginGlobal['polling']['status'] == True:
                pluginGlobal['polling']['threadEnd'] = True
                self.pollingEvent.set()  # Stop the Polling Thread

        time.sleep(2)  # Wait 2 seconds before contacting Smappee - gives plugin time to properly shutdown

        autolog(INFO, u"Plugin shutdown complete")


    def getDeviceFactoryUiValues(self, devIdList):
        global pluginGlobal
        autolog(METHOD, u"%s; devIdList = [%s]" %  (methodNameForTrace(), devIdList))  

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

        if len(pluginGlobal['smappeeServiceLocationIdToDevId']) == 1:
            self.smappeeServiceLocationId = pluginGlobal['smappeeServiceLocationIdToDevId'].keys()[0]
            self.smappeeServiceLocationName = pluginGlobal['smappeeServiceLocationIdToDevId'][self.serviceLocationId]['name']
            valuesDict["smappeeLocationValue"] = str("%s: %s" % (self.smappeeServiceLocationId, self.smappeeServiceLocationName))
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

        autolog(METHOD, u" getDeviceFactoryUiValues [END]: EL-Detect=[%s], SO-Detect=[%s],  GW-Detect=[%s], AP-Detect=[%s], AC-Detect=[%s]" % (self.deviceDetectedSmappeeElectricity, self.deviceDetectedSmappeeSolar, self.deviceDetectedSmappeeSensor, self.deviceDetectedSmappeeAppliance , self.deviceDetectedSmappeeActuator))   

        return (valuesDict, errorMsgDict)

    def validateDeviceFactoryUi(self, valuesDict, devIdList):
        global pluginGlobal
        autolog(METHOD, u"%s" %  (methodNameForTrace()))  

        errorsDict = indigo.Dict()
        return (True, valuesDict, errorsDict)

    def closedDeviceFactoryUi(self, valuesDict, userCancelled, devIdList):
        global pluginGlobal
        autolog(METHOD, u"%s" %  (methodNameForTrace()))

        if self.monitorDeviceProcessed == True:
            autolog(INFO, u"Devices changed via 'Define and Sync' - restarting SMAPPEE Plugin . . . . .")

            serverPlugin = indigo.server.getPlugin(self.pluginId)
            serverPlugin.restart(waitUntilDone=False)
            return
  
        if userCancelled == False:
            for sensorId in sorted(pluginGlobal['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['sensorIds']):
                if pluginGlobal['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['sensorIds'][sensorId]['queued-add'] == True:
                    serviceLocationId = self.smappeeServiceLocationId
                    serviceLocationName = pluginGlobal['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['name']
                    address = sensorId
                    name = pluginGlobal['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['sensorIds'][sensorId]['name']
                    deviceType = pluginGlobal['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['sensorIds'][sensorId]['deviceType']

                    self.processQueue.put(['NEW_SENSOR', serviceLocationId, (serviceLocationName, address, name)])

            for applianceId in sorted(pluginGlobal['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['applianceIds']):
                if pluginGlobal['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['applianceIds'][applianceId]['queued-add'] == True:
                    serviceLocationId = self.smappeeServiceLocationId
                    serviceLocationName = pluginGlobal['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['name']
                    address = applianceId
                    name = pluginGlobal['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['applianceIds'][applianceId]['name']

                    self.processQueue.put(["NEW_APPLIANCE", serviceLocationId, (serviceLocationName, address, name)])

            for actuatorId in sorted(pluginGlobal['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['actuatorIds']):
                if pluginGlobal['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['actuatorIds'][actuatorId]['queued-add'] == True:
                    serviceLocationId = self.smappeeServiceLocationId
                    serviceLocationName = pluginGlobal['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['name']
                    address = actuatorId
                    name = pluginGlobal['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['actuatorIds'][actuatorId]['name']

                    self.processQueue.put(["NEW_ACTUATOR", serviceLocationId, (serviceLocationName, address, name)])

        else:
            for sensorId in sorted(pluginGlobal['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['sensorIds']):
                pluginGlobal['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['sensorIds'][sensorId]['queued-add'] == False
                pluginGlobal['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['sensorIds'][sensorId]['queued-remove'] = False          
            for applianceId in sorted(pluginGlobal['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['applianceIds']):
                pluginGlobal['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['applianceIds'][applianceId]['queued-add'] == False
                pluginGlobal['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['applianceIds'][applianceId]['queued-remove'] = False          
            for actuatorId in sorted(pluginGlobal['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['actuatorIds']):
                pluginGlobal['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['actuatorIds'][actuatorId]['queued-add'] == False
                pluginGlobal['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['actuatorIds'][actuatorId]['queued-remove'] == False


        return


        # Not executed - testing example
        plugin = indigo.server.getPlugin("com.autologplugin.indigoplugin.smappeecontroller")
        if plugin.isEnabled():
            plugin.restart()



    def _getSmappeeLocationList(self, filter="", valuesDict=None, typeId="", targetId=0):
        global pluginGlobal
        autolog(METHOD, u"%s" %  (methodNameForTrace()))  

        return self.listItemsSmappeeLocationList


    def _prepareGetSmappeeLocationList(self, valuesDict, devIdList):
        global pluginGlobal
        autolog(METHOD, u"%s" %  (methodNameForTrace()))  

        valuesDict["hideSmappeeLocationValue"] = "true"
        valuesDict["hideSmappeeLocationList"] = "false"

        listToDisplay = []
        self.locationCount = 0
        self.locationAvailableCount = 0
        for self.smappeeServiceLocationId in sorted(pluginGlobal['smappeeServiceLocationIdToDevId']):
            self.serviceLocationName = pluginGlobal['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['name'] 
            self.locationCount += 1
            if pluginGlobal['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['electricityId'] == 0 and pluginGlobal['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['solarId'] == 0:
                listToDisplay.append((self.smappeeServiceLocationId, self.serviceLocationName))
                self.locationAvailableCount +=1
            else:
                self.serviceLocationName = str("Location '%s:%s' assigned to Smappee" % (self.smappeeServiceLocationId, pluginGlobal['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['name']))  
                listToDisplay.append((self.smappeeServiceLocationId, self.serviceLocationName))

        if self.locationCount == 0:
            listToDisplay = []
            listToDisplay.append(("NONE","No Smappee locations found"))
        else:
            if self.locationAvailableCount == 0:
                listToDisplay.insert(0, ("NONE","All location(s) already assigned"))
            else:
                listToDisplay.insert(0, ("NONE","- Select Smappee Location -"))

            if self.locationCount == 1:
                # As only one location, don't display list and skip striaght to displaying value
                valuesDict["hideSmappeeLocationValue"] = "false"
                valuesDict["hideSmappeeLocationList"] = "true"

        self.listItemsSmappeeLocationList = listToDisplay
            
        return valuesDict


    def _smappeeLocationSelected(self, valuesDict, typeId, devIdList):
        global pluginGlobal
        autolog(METHOD, u"%s" %  (methodNameForTrace()))  

        self.deviceDetectedSmappeeElectricity = False
        self.deviceDetectedSmappeeSolar = False
        self.deviceDetectedSmappeeAppliance = False
        self.deviceDetectedSmappeeActuator = False

        if "smappeeLocationList" in valuesDict:
            self.smappeeServiceLocationId = valuesDict["smappeeLocationList"]
            if self.smappeeServiceLocationId != 'NONE':
                if self.smappeeServiceLocationId in pluginGlobal['smappeeServiceLocationIdToDevId']:
                    self.smappeeServiceLocationName = pluginGlobal['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['name']
                    valuesDict["hideSmappeeLocationValue"] = "false"
                    valuesDict["hideSmappeeLocationList"] = "true"

                    valuesDict["smappeeLocationValue"] = str("%s: %s" % (self.smappeeServiceLocationId, self.smappeeServiceLocationName))
                    if pluginGlobal['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['electricityId'] != 0:
                        self.deviceDetectedSmappeeElectricity = True
                    if pluginGlobal['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['solarId'] != 0:
                        self.deviceDetectedSmappeeSolar = True

                    if self.deviceDetectedSmappeeElectricity == True:
                        valuesDict["removeSmappeeElectricityDeviceEnabled"] = 'true'
                    else:   
                        valuesDict["addSmappeeElectricityDeviceEnabled"] = 'true'

                    if self.deviceDetectedSmappeeSolar == True:
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
        global pluginGlobal
        autolog(METHOD, u"%s; LOC=[%s]" %  (methodNameForTrace(), self.smappeeServiceLocationId))  

        return self.listItemsDefinedSmappeeMainList



    def _prepareSmappeeList(self, valuesDict, devIdList):

        global pluginGlobal
        autolog(METHOD, u"%s; LOC=[%s]" %  (methodNameForTrace(), self.smappeeServiceLocationId))  

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
        autolog(FACTORY, u"SMAPPEE [F-0]: _prepareSmappeeList")

        for dev in indigo.devices.iter("self"):
            autolog(FACTORY, u"SMAPPEE [F-1]: %s [devTypeId = %s]" % (dev.name, dev.deviceTypeId))
            if dev.deviceTypeId == "smappeeElectricity" or dev.deviceTypeId == "smappeeElectricityNet" or dev.deviceTypeId == "smappeeElectricitySaved" or dev.deviceTypeId == "smappeeSolar" or dev.deviceTypeId == "smappeeSolarUsed" or dev.deviceTypeId == "smappeeSolarExported":

                autolog(FACTORY, u"SMAPPEE [F-2]: %s [devTypeId = %s]" % (dev.name, dev.deviceTypeId))


                if dev.pluginProps['serviceLocationId'] == self.smappeeServiceLocationId:
                    smappeeMainDeviceDetected = True
                    devName = dev.name
                    listToDisplay.append((dev.id, devName))
                    if dev.deviceTypeId == "smappeeElectricity" :
                        electricityDevId = dev.id
                        valuesDict["addSmappeeElectricityDeviceEnabled"] = 'false'
                        valuesDict["removeSmappeeElectricityDeviceEnabled"] = 'true'
                    elif dev.deviceTypeId == "smappeeElectricityNet" :
                        electricityNetDevId = dev.id
                        valuesDict["addSmappeeElectricityNetDeviceEnabled"] = 'false'
                        valuesDict["removeSmappeeElectricityNetDeviceEnabled"] = 'true'
                    elif dev.deviceTypeId == "smappeeElectricitySaved" :
                        electricitySavedDevId = dev.id
                        valuesDict["addSmappeeElectricitySavedDeviceEnabled"] = 'false'
                        valuesDict["removeSmappeeElectricitySavedDeviceEnabled"] = 'true'
                    elif dev.deviceTypeId == "smappeeSolar" :
                        solarDevId = dev.id
                        valuesDict["addSmappeeSolarDeviceEnabled"] = 'false'
                        valuesDict["removeSmappeeSolarDeviceEnabled"] = 'true'
                    elif dev.deviceTypeId == "smappeeSolarUsed" :
                        solarUsedDevId = dev.id
                        valuesDict["addSmappeeSolarUsedDeviceEnabled"] = 'false'
                        valuesDict["removeSmappeeSolarUsedDeviceEnabled"] = 'true'
                    elif dev.deviceTypeId == "smappeeSolarExported" :
                        solarUsedDevId = dev.id
                        valuesDict["addSmappeeSolarExportedDeviceEnabled"] = 'false'
                        valuesDict["removeSmappeeSolarExportedDeviceEnabled"] = 'true'
                    else:
                        autolog(ERROR, u"SMAPPEE [F-E]: %s [devTypeId = %s] UNKNOWN" % (dev.name, dev.deviceTypeId))

                    autolog(FACTORY, u"SMAPPEE [F-3]: %s [devTypeId = %s]" % (dev.name, dev.deviceTypeId))


        if smappeeMainDeviceDetected == False:
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
                if devIdList[0] != electricityDevId and devIdList[0] != electricityNetDevId and devIdList[0] != electricitySavedDevId and devIdList[0] != solarDevId and devIdList[0] != solarUsedDevId and devIdList[0] != solarExportedDevId:
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

        if (valuesDict["addSmappeeElectricityDeviceEnabled"]          == 'false' and valuesDict["removeSmappeeElectricityDeviceEnabled"]      == 'false' and 
                valuesDict["addSmappeeElectricityNetDeviceEnabled"]   == 'false' and valuesDict["removeSmappeeElectricityNetDeviceEnabled"]   == 'false' and 
                valuesDict["addSmappeeElectricitySavedDeviceEnabled"] == 'false' and valuesDict["removeSmappeeElectricitySavedDeviceEnabled"] == 'false' and 
                valuesDict["addSmappeeSolarDeviceEnabled"]            == 'false' and valuesDict["removeSmappeeSolarDeviceEnabled"]            == 'false' and 
                valuesDict["addSmappeeSolarUsedDeviceEnabled"]        == 'false' and valuesDict["removeSmappeeSolarUsedDeviceEnabled"]        == 'false' and 
                valuesDict["addSmappeeSolarExportedDeviceEnabled"]    == 'false' and valuesDict["removeSmappeeSolarExportedDeviceEnabled"]    == 'false'):
            valuesDict["helpSmappeeElectricitySolarEnabled"] = 'true'
        else:
            valuesDict["helpSmappeeElectricitySolarEnabled"] = 'false'

        if len(listToDisplay) == 0:
            listToDisplay.append((0, "- No Smappee Devices Defined -"))

        self.listItemsDefinedSmappeeMainList = listToDisplay
            
        return valuesDict


    def _addSmappeeElectricityDevice(self, valuesDict, devIdList):
        global pluginGlobal
        autolog(METHOD, u"%s; Location[%s:%s]" %  (methodNameForTrace(), self.smappeeServiceLocationId, self.smappeeServiceLocationName))

        self.monitorDeviceProcessed = True  # Forces Plugin to restart when the Device Factory dialogue is closed or cancelled 

        newdev = indigo.device.create(protocol=indigo.kProtocol.Plugin,
                    address="E000",
                    name="Smappee Electricity V2",
                    description="Smappee", 
                    pluginId="com.autologplugin.indigoplugin.smappeecontroller",
                    deviceTypeId="smappeeElectricity",
                    folder=pluginGlobal['deviceFolderId'],
                    props={"SupportsEnergyMeter":True, 
                           "SupportsEnergyMeterCurPower":True, 
                           "serviceLocationId":self.smappeeServiceLocationId, 
                           "serviceLocationName":self.smappeeServiceLocationName, 
                           "optionsEnergyMeterCurPower":"last", 
                           "hideEnergyMeterCurPower":False, 
                           "hideEnergyMeterAccumPower":False,  
                           "hideAlwaysOnPower":True,
                           "dailyStandingCharge":"0.00",
                           "kwhUnitCost":"0.00"})
        newdev.model = "Smappee"
        newdev.subModel = "Elec."       # Manually need to set the model and subModel names (for UI only)
        newdev.configured = True
        newdev.enabled = True
        newdev.replaceOnServer()

        self.setSmappeeServiceLocationIdToDevId('ADD_UPDATE', 'smappeeElectricity', self.smappeeServiceLocationId, newdev.id, "", "")

        valuesDict["addSmappeeElectricityDeviceEnabled"] = 'false'
        valuesDict["removeSmappeeElectricityDeviceEnabled"] = 'true'

        devIdList.extend([newdev.id])

        valuesDict = self._prepareSmappeeList(valuesDict, devIdList)

        return valuesDict

 
    def _removeSmappeeElectricityDevice(self, valuesDict, devIdList):
        global pluginGlobal
        autolog(METHOD, u"%s" %  (methodNameForTrace()))  

        self.monitorDeviceProcessed = True  # Forces Plugin to restart when the Device Factory dialogue is closed or cancelled 

        for dev in indigo.devices.iter("self"):
            try:
                if dev.deviceTypeId == "smappeeElectricity":
                    serviceLocationId = dev.pluginProps['serviceLocationId']
                    self.setSmappeeServiceLocationIdToDevId('STOP', 'smappeeElectricity', serviceLocationId, dev.id, "", "")

                    if dev.id in pluginGlobal['smappees']:
                        pluginGlobal['smappees'].pop(dev.id, None)
                        autolog(FACTORY, u"_removeSmappeeElectricityDevice = POPPED")

                    indigo.device.delete(dev)

                    pluginGlobal['config']['supportsElectricity'] = False

                    autolog(FACTORY, u"_removeSmappeeElectricityDevice = DELETED")
            except:
                autolog(FACTORY, u"_removeSmappeeElectricityDevice = EXCEPTION")   
                pass    # delete doesn't allow (throws) on root elem

        valuesDict["addSmappeeElectricityDeviceEnabled"] = 'true'
        valuesDict["removeSmappeeElectricityDeviceEnabled"] = 'false'

        valuesDict = self._prepareSmappeeList(valuesDict, devIdList)

        return valuesDict


    def _addSmappeeElectricityNetDevice(self, valuesDict, devIdList):
        global pluginGlobal
        autolog(METHOD, u"%s" %  (methodNameForTrace()))  

        self.monitorDeviceProcessed = True  # Forces Plugin to restart when the Device Factory dialogue is closed or cancelled 

        newdev = indigo.device.create(protocol=indigo.kProtocol.Plugin,
                    address="EN00",
                    name="Smappee Net Electricity V2",
                    description="Smappee", 
                    pluginId="com.autologplugin.indigoplugin.smappeecontroller",
                    deviceTypeId="smappeeElectricityNet",
                    folder=pluginGlobal['deviceFolderId'],
                    props={"SupportsEnergyMeter":True, 
                           "SupportsEnergyMeterCurPower":True, 
                           "serviceLocationId":self.smappeeServiceLocationId, 
                           "serviceLocationName":self.smappeeServiceLocationName, 
                           "optionsEnergyMeterCurPower":"last", 
                           "hideEnergyMeterCurNetPower":False,
                           "hideEnergyMeterCurZeroNetPower":True, 
                           "hideEnergyMeterAccumNetPower":False,
                           "hideNoChangeEnergyMeterAccumNetPower":True})

        newdev.model = "Smappee"
        newdev.subModel = "E-Net"      # Manually need to set the model and subModel names (for UI only)
        newdev.configured = True
        newdev.enabled = True
        newdev.replaceOnServer()

        self.setSmappeeServiceLocationIdToDevId('ADD_UPDATE', 'smappeeElectricityNet', self.smappeeServiceLocationId, newdev.id, "", "")

        valuesDict["addSmappeeElectricityNetDeviceEnabled"] = 'false'
        valuesDict["removeSmappeeElectricityNetDeviceEnabled"] = 'true'

        devIdList.extend([newdev.id])

        valuesDict = self._prepareSmappeeList(valuesDict, devIdList)

        return valuesDict


    def _removeSmappeeElectricityNetDevice(self, valuesDict, devIdList):
        global pluginGlobal
        autolog(METHOD, u"%s" %  (methodNameForTrace()))  

        self.monitorDeviceProcessed = True  # Forces Plugin to restart when the Device Factory dialogue is closed or cancelled 

        for dev in indigo.devices.iter("self"):
            try:
                if dev.deviceTypeId == "smappeeElectricityNet":
                    serviceLocationId = dev.pluginProps['serviceLocationId']
                    
                    self.setSmappeeServiceLocationIdToDevId('STOP', 'smappeeElectricityNet', serviceLocationId, dev.id, "", "")

                    if dev.id in pluginGlobal['smappees']:
                        pluginGlobal['smappees'].pop(dev.id, None)
                        autolog(FACTORY, u"_removeSmappeeElectricityNetDevice = POPPED")   

                    indigo.device.delete(dev)

                    pluginGlobal['config']['supportsElectricityNet'] = False

                    autolog(FACTORY, u"_removeSmappeeElectricityNetDevice = DELETED")
            except:
                autolog(FACTORY, u"_removeSmappeeElectricityNetDevice = EXCEPTION")   
                pass    # delete doesn't allow (throws) on root elem

        valuesDict["addSmappeeElectricityNetDeviceEnabled"] = 'true'
        valuesDict["removeSmappeeElectricityNetDeviceEnabled"] = 'false'

        valuesDict = self._prepareSmappeeList(valuesDict, devIdList)

        return valuesDict


    def _addSmappeeElectricitySavedDevice(self, valuesDict, devIdList):
        global pluginGlobal
        autolog(METHOD, u"%s" %  (methodNameForTrace()))  

        self.monitorDeviceProcessed = True  # Forces Plugin to restart when the Device Factory dialogue is closed or cancelled 

        newdev = indigo.device.create(protocol=indigo.kProtocol.Plugin,
                    address="ES00",
                    name="Smappee Saved Electricity V2",
                    description="Smappee", 
                    pluginId="com.autologplugin.indigoplugin.smappeecontroller",
                    deviceTypeId="smappeeElectricitySaved",
                    folder=pluginGlobal['deviceFolderId'],
                    props={"SupportsEnergyMeter":True, 
                           "SupportsEnergyMeterCurPower":True, 
                           "serviceLocationId":self.smappeeServiceLocationId, 
                           "serviceLocationName":self.smappeeServiceLocationName, 
                           "optionsEnergyMeterCurPower":"last", 
                           "hideEnergyMeterCurSavedPower":False,
                           "hideEnergyMeterCurZeroSavedPower":True, 
                           "hideEnergyMeterAccumSavedPower":False,
                           "hideNoChangeEnergyMeterAccumSavedPower":True})

        newdev.model = "Smappee"
        newdev.subModel = "E-Saved"      # Manually need to set the model and subModel names (for UI only)
        newdev.configured = True
        newdev.enabled = True
        newdev.replaceOnServer()

        self.setSmappeeServiceLocationIdToDevId('ADD_UPDATE', 'smappeeElectricitySaved', self.smappeeServiceLocationId, newdev.id, "", "")

        valuesDict["addSmappeeElectricitySavedDeviceEnabled"] = 'false'
        valuesDict["removeSmappeeElectricitySavedDeviceEnabled"] = 'true'

        devIdList.extend([newdev.id])

        valuesDict = self._prepareSmappeeList(valuesDict, devIdList)

        return valuesDict


    def _removeSmappeeElectricitySavedDevice(self, valuesDict, devIdList):
        global pluginGlobal
        autolog(METHOD, u"%s" %  (methodNameForTrace()))  

        self.monitorDeviceProcessed = True  # Forces Plugin to restart when the Device Factory dialogue is closed or cancelled 

        for dev in indigo.devices.iter("self"):
            try:
                if dev.deviceTypeId == "smappeeElectricitySaved":
                    serviceLocationId = dev.pluginProps['serviceLocationId']
                    
                    self.setSmappeeServiceLocationIdToDevId('STOP', 'smappeeElectricitySaved', serviceLocationId, dev.id, "", "")

                    if dev.id in pluginGlobal['smappees']:
                        pluginGlobal['smappees'].pop(dev.id, None)
                        autolog(FACTORY, u"_removeSmappeeElectricitySavedDevice = POPPED")   

                    indigo.device.delete(dev)

                    pluginGlobal['config']['supportsElectricitySaved'] = False

                    autolog(FACTORY, u"_removeSmappeeElectricitySavedDevice = DELETED")
            except:
                autolog(FACTORY, u"_removeSmappeeElectricitySavedDevice = EXCEPTION")   
                pass    # delete doesn't allow (throws) on root elem

        valuesDict["addSmappeeElectricitySavedDeviceEnabled"] = 'true'
        valuesDict["removeSmappeeElectricitySavedDeviceEnabled"] = 'false'

        valuesDict = self._prepareSmappeeList(valuesDict, devIdList)

        return valuesDict


    def _addSmappeeSolarDevice(self, valuesDict, devIdList):
        global pluginGlobal
        autolog(METHOD, u"%s" %  (methodNameForTrace()))  

        self.monitorDeviceProcessed = True  # Forces Plugin to restart when the Device Factory dialogue is closed or cancelled 

        newdev = indigo.device.create(protocol=indigo.kProtocol.Plugin,
                    address="S000",
                    name="Smappee Solar PV V2",
                    description="Smappee", 
                    pluginId="com.autologplugin.indigoplugin.smappeecontroller",
                    deviceTypeId="smappeeSolar",
                    folder=pluginGlobal['deviceFolderId'],
                    props={"SupportsEnergyMeter":True, 
                           "SupportsEnergyMeterCurPower":True, 
                           "serviceLocationId":self.smappeeServiceLocationId, 
                           "serviceLocationName":self.smappeeServiceLocationName, 
                           "optionsEnergyMeterCurPower":"last", 
                           "hideSolarMeterCurGeneration":False,
                           "hideZeroSolarMeterCurGeneration":True, 
                           "hideSolarMeterAccumGeneration":False,
                           "hideNoChangeInSolarMeterAccumGeneration":True,
                           "generationRate":"0.00",
                           "exportType":"none",
                           "exportPercentage":"0.00",
                           "exportRate":"0.00"})

        newdev.model = "Smappee"
        newdev.subModel = "Solar"      # Manually need to set the model and subModel names (for UI only)
        newdev.configured = True
        newdev.enabled = True
        newdev.replaceOnServer()

        self.setSmappeeServiceLocationIdToDevId('ADD_UPDATE', 'smappeeSolar', self.smappeeServiceLocationId, newdev.id, "", "")

        valuesDict["addSmappeeSolarDeviceEnabled"] = 'false'
        valuesDict["removeSmappeeSolarDeviceEnabled"] = 'true'

        devIdList.extend([newdev.id])

        valuesDict = self._prepareSmappeeList(valuesDict, devIdList)

        return valuesDict


    def _removeSmappeeSolarDevice(self, valuesDict, devIdList):
        global pluginGlobal
        autolog(METHOD, u"%s" %  (methodNameForTrace()))  

        self.monitorDeviceProcessed = True  # Forces Plugin to restart when the Device Factory dialogue is closed or cancelled 

        for dev in indigo.devices.iter("self"):
            try:
                if dev.deviceTypeId == "smappeeSolar":
                    serviceLocationId = dev.pluginProps['serviceLocationId']
                    
                    self.setSmappeeServiceLocationIdToDevId('STOP', 'smappeeSolar', serviceLocationId, dev.id, "", "")

                    if dev.id in pluginGlobal['smappees']:
                        pluginGlobal['smappees'].pop(dev.id, None)
                        autolog(FACTORY, u"_removeSmappeeSolarDevice = POPPED")   

                    indigo.device.delete(dev)

                    pluginGlobal['config']['supportsSolar'] = False

                    autolog(FACTORY, u"_removeSmappeeSolarDevice = DELETED")
            except:
                autolog(FACTORY, u"_removeSmappeeSolarDevice = EXCEPTION")   
                pass    # delete doesn't allow (throws) on root elem

        valuesDict["addSmappeeSolarDeviceEnabled"] = 'true'
        valuesDict["removeSmappeeSolarDeviceEnabled"] = 'false'

        valuesDict = self._prepareSmappeeList(valuesDict, devIdList)

        return valuesDict


    def _addSmappeeSolarUsedDevice(self, valuesDict, devIdList):
        global pluginGlobal
        autolog(METHOD, u"%s" %  (methodNameForTrace()))  

        self.monitorDeviceProcessed = True  # Forces Plugin to restart when the Device Factory dialogue is closed or cancelled 

        newdev = indigo.device.create(protocol=indigo.kProtocol.Plugin,
                    address="SU00",
                    name="Smappee Solar PV Used V2",
                    description="Smappee", 
                    pluginId="com.autologplugin.indigoplugin.smappeecontroller",
                    deviceTypeId="smappeeSolarUsed",
                    folder=pluginGlobal['deviceFolderId'],
                    props={"SupportsEnergyMeter":True, 
                           "SupportsEnergyMeterCurPower":True, 
                           "serviceLocationId":self.smappeeServiceLocationId, 
                           "serviceLocationName":self.smappeeServiceLocationName, 
                           "optionsEnergyMeterCurPower":"last", 
                           "hideSolarUsedMeterCurGeneration":False,
                           "hideZeroSolarUsedMeterCurGeneration":True, 
                           "hideSolarUsedMeterAccumGeneration":False,
                           "hideNoChangeInSolarUsedMeterAccumGeneration":True})

        newdev.model = "Smappee"
        newdev.subModel = "S-Used"      # Manually need to set the model and subModel names (for UI only)
        newdev.configured = True
        newdev.enabled = True
        newdev.replaceOnServer()

        self.setSmappeeServiceLocationIdToDevId('ADD_UPDATE', 'smappeeSolarUsed', self.smappeeServiceLocationId, newdev.id, "", "")

        valuesDict["addSmappeeSolarUsedDeviceEnabled"] = 'false'
        valuesDict["removeSmappeeSolarUsedDeviceEnabled"] = 'true'

        devIdList.extend([newdev.id])

        valuesDict = self._prepareSmappeeList(valuesDict, devIdList)

        return valuesDict


    def _removeSmappeeSolarUsedDevice(self, valuesDict, devIdList):
        global pluginGlobal
        autolog(METHOD, u"%s" %  (methodNameForTrace()))  

        self.monitorDeviceProcessed = True  # Forces Plugin to restart when the Device Factory dialogue is closed or cancelled 

        for dev in indigo.devices.iter("self"):
            try:
                if dev.deviceTypeId == "smappeeSolarUsed":
                    serviceLocationId = dev.pluginProps['serviceLocationId']
                    
                    self.setSmappeeServiceLocationIdToDevId('STOP', 'smappeeSolarUsed', serviceLocationId, dev.id, "", "")

                    if dev.id in pluginGlobal['smappees']:
                        pluginGlobal['smappees'].pop(dev.id, None)
                        autolog(FACTORY, u"_removeSmappeeSolarUsedDevice = POPPED")   

                    indigo.device.delete(dev)

                    pluginGlobal['config']['supportsSolarUsed'] = False

                    autolog(FACTORY, u"_removeSmappeeSolarUsedDevice = DELETED")
            except:
                autolog(FACTORY, u"_removeSmappeeSolarUsedDevice = EXCEPTION")   
                pass    # delete doesn't allow (throws) on root elem

        valuesDict["addSmappeeSolarUsedDeviceEnabled"] = 'true'
        valuesDict["removeSmappeeSolarUsedDeviceEnabled"] = 'false'

        valuesDict = self._prepareSmappeeList(valuesDict, devIdList)

        return valuesDict


    def _addSmappeeSolarExportedDevice(self, valuesDict, devIdList):
        global pluginGlobal
        autolog(METHOD, u"%s" %  (methodNameForTrace()))  

        self.monitorDeviceProcessed = True  # Forces Plugin to restart when the Device Factory dialogue is closed or cancelled 

        newdev = indigo.device.create(protocol=indigo.kProtocol.Plugin,
                    address="SE00",
                    name="Smappee Solar PV Exported V2",
                    description="Smappee", 
                    pluginId="com.autologplugin.indigoplugin.smappeecontroller",
                    deviceTypeId="smappeeSolarExported",
                    folder=pluginGlobal['deviceFolderId'],
                    props={"SupportsEnergyMeter":True, 
                           "SupportsEnergyMeterCurPower":True, 
                           "serviceLocationId":self.smappeeServiceLocationId, 
                           "serviceLocationName":self.smappeeServiceLocationName, 
                           "optionsEnergyMeterCurPower":"last", 
                           "hideSolarExportedMeterCurGeneration":False,
                           "hideZeroSolarExportedMeterCurGeneration":True, 
                           "hideSolarExportedMeterAccumGeneration":False,
                           "hideNoChangeInSolarExportedMeterAccumGeneration":True})

        newdev.model = "Smappee"
        newdev.subModel = "S-Exported"      # Manually need to set the model and subModel names (for UI only)
        newdev.configured = True
        newdev.enabled = True
        newdev.replaceOnServer()

        self.setSmappeeServiceLocationIdToDevId('ADD_UPDATE', 'smappeeSolarExported', self.smappeeServiceLocationId, newdev.id, "", "")

        valuesDict["addSmappeeSolarExportedDeviceEnabled"] = 'false'
        valuesDict["removeSmappeeSolarExportedDeviceEnabled"] = 'true'

        devIdList.extend([newdev.id])

        valuesDict = self._prepareSmappeeList(valuesDict, devIdList)

        return valuesDict


    def _removeSmappeeSolarExportedDevice(self, valuesDict, devIdList):
        global pluginGlobal
        autolog(METHOD, u"%s" %  (methodNameForTrace()))  

        self.monitorDeviceProcessed = True  # Forces Plugin to restart when the Device Factory dialogue is closed or cancelled 

        for dev in indigo.devices.iter("self"):
            try:
                if dev.deviceTypeId == "smappeeSolarExported":
                    serviceLocationId = dev.pluginProps['serviceLocationId']
                    
                    self.setSmappeeServiceLocationIdToDevId('STOP', 'smappeeSolarExported', serviceLocationId, dev.id, "", "")

                    if dev.id in pluginGlobal['smappees']:
                        pluginGlobal['smappees'].pop(dev.id, None)
                        autolog(FACTORY, u"_removeSmappeeSolarExportedDevice = POPPED")   

                    indigo.device.delete(dev)

                    pluginGlobal['config']['supportsSolarExported'] = False

                    autolog(FACTORY, u"_removeSmappeeSolarExportedDevice = DELETED")
            except:
                autolog(FACTORY, u"_removeSmappeeSolarExportedDevice = EXCEPTION")   
                pass    # delete doesn't allow (throws) on root elem

        valuesDict["addSmappeeSolarExportedDeviceEnabled"] = 'true'
        valuesDict["removeSmappeeSolarExportedDeviceEnabled"] = 'false'

        valuesDict = self._prepareSmappeeList(valuesDict, devIdList)

        return valuesDict


    def _getDefinedSmappeeSensorList(self, filter="", valuesDict=None, typeId="", targetId=0):
        global pluginGlobal
        autolog(METHOD, u"%s; LOC=[%s]" %  (methodNameForTrace(), self.smappeeServiceLocationId))  

        return self.listItemsDefinedSmappeeSensorList

    def _prepareGetDefinedSmappeeSensorList(self, valuesDict):
        global pluginGlobal
        autolog(METHOD, u"%s; LOC=[%s]" %  (methodNameForTrace(), self.smappeeServiceLocationId))  

        listToDisplay = []

        if self.smappeeServiceLocationId == '' or self.smappeeServiceLocationId == 'NONE':
            return listToDisplay

        for dev in indigo.devices.iter("self"):
            if dev.deviceTypeId == "smappeeSensor" and dev.pluginProps['serviceLocationId'] == self.smappeeServiceLocationId:
                devName = dev.name
                listToDisplay.append((str(dev.id), devName))

        if listToDisplay == []:
            listToDisplay.append((0, '- No Sensors Defined -'))

        listToDisplay = sorted(listToDisplay,key=lambda x: x[1])

        self.listItemsDefinedSmappeeSensorList = listToDisplay
            
        return valuesDict


    def _getPotentialSmappeeSensorList(self, filter="", valuesDict=None, typeId="", targetId=0):
        global pluginGlobal
        autolog(METHOD, u"%s; LOC=[%s]" %  (methodNameForTrace(), self.smappeeServiceLocationId))  

        return self.listItemsPotentialSmappeeSensorList


    def _prepareGetPotentialSmappeeSensorList(self, valuesDict):
        global pluginGlobal
        autolog(METHOD, u"%s; LOC=[%s]" %  (methodNameForTrace(), self.smappeeServiceLocationId))  

        listToDisplay = []

        if self.smappeeServiceLocationId == '' or self.smappeeServiceLocationId == 'NONE':
            return listToDisplay

        for sensorId in sorted(pluginGlobal['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['sensorIds']):
            sensorName  = pluginGlobal['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['sensorIds'][sensorId]['name']
            sensorDevId = pluginGlobal['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['sensorIds'][sensorId]['devId']
            queuedAdd      = pluginGlobal['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['sensorIds'][sensorId]['queued-add']
            if sensorDevId == 0:
                if queuedAdd == True:
                    sensorName = str("QUEUED: %s" % (sensorName))
                listToDisplay.append((sensorId, sensorName))
                        
        if listToDisplay == []:
            listToDisplay.append((0, '- No Available Sensors Detected -'))
            valuesDict["addSmappeeSensorDeviceEnabled"] = 'false'
        else:
            valuesDict["addSmappeeSensorDeviceEnabled"] = 'true'

        listToDisplay = sorted(listToDisplay)

        self.listItemsPotentialSmappeeSensorList = listToDisplay
            
        return valuesDict


    def _addSmappeeSensorDevice(self, valuesDict, devIdList):
        global pluginGlobal
        autolog(METHOD, u"%s; ValuesDict=[%s]" %  (methodNameForTrace(), valuesDict['potentialSmappeeSensorList']))  

        for potentialSensorAddress in valuesDict['potentialSmappeeSensorList']:
            potentialSensorAddress = str(potentialSensorAddress)
            potentialSensorName = pluginGlobal['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['sensorIds'][potentialSensorAddress]['name'] 
            if pluginGlobal['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['sensorIds'][potentialSensorAddress]['queued-add'] == False:
                self.setSmappeeServiceLocationIdToDevId('QUEUE-ADD', 'smappeeSensor', self.smappeeServiceLocationId, 0, potentialSensorAddress, potentialSensorName)
            else:
                self.setSmappeeServiceLocationIdToDevId('DEQUEUE', 'smappeeSensor', self.smappeeServiceLocationId, 0, potentialSensorAddress, potentialSensorName)

        valuesDict = self._prepareGetDefinedSmappeeSensorList(valuesDict)
        valuesDict = self._prepareGetPotentialSmappeeSensorList(valuesDict)

        return valuesDict


    def _getDefinedSmappeeApplianceList(self, filter="", valuesDict=None, typeId="", targetId=0):
        global pluginGlobal
        autolog(METHOD, u"%s; LOC=[%s]" %  (methodNameForTrace(), self.smappeeServiceLocationId))  

        return self.listItemsDefinedSmappeeApplianceList


    def _prepareGetDefinedSmappeeApplianceList(self, valuesDict):
        global pluginGlobal
        autolog(METHOD, u"%s; LOC=[%s]" %  (methodNameForTrace(), self.smappeeServiceLocationId))  

        listToDisplay = []

        if self.smappeeServiceLocationId == '' or self.smappeeServiceLocationId == 'NONE':
            return listToDisplay

        for dev in indigo.devices.iter("self"):
            if dev.deviceTypeId == "smappeeAppliance" and dev.pluginProps['serviceLocationId'] == self.smappeeServiceLocationId:
                devName = dev.name
                listToDisplay.append((str(dev.id), devName))

        if listToDisplay == []:
            listToDisplay.append((0, '- No Appliances Defined -'))

        listToDisplay = sorted(listToDisplay,key=lambda x: x[1])

        self.listItemsDefinedSmappeeApplianceList = listToDisplay
            
        return valuesDict


    def _getPotentialSmappeeApplianceList(self, filter="", valuesDict=None, typeId="", targetId=0):
        global pluginGlobal
        autolog(METHOD, u"%s; LOC=[%s]" %  (methodNameForTrace(), self.smappeeServiceLocationId))  

        return self.listItemsPotentialSmappeeApplianceList


    def _prepareGetPotentialSmappeeApplianceList(self, valuesDict):
        global pluginGlobal
        autolog(METHOD, u"%s; LOC=[%s]" %  (methodNameForTrace(), self.smappeeServiceLocationId))  

        listToDisplay = []

        if self.smappeeServiceLocationId == '' or self.smappeeServiceLocationId == 'NONE':
            return listToDisplay

        for applianceId in sorted(pluginGlobal['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['applianceIds']):
            applianceName  = pluginGlobal['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['applianceIds'][applianceId]['name']
            applianceDevId = pluginGlobal['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['applianceIds'][applianceId]['devId']
            queuedAdd      = pluginGlobal['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['applianceIds'][applianceId]['queued-add']
            if applianceDevId == 0:
                if queuedAdd == True:
                    applianceName = str("QUEUED: %s" % (applianceName))
                listToDisplay.append((applianceId, applianceName))
                        
        if listToDisplay == []:
            listToDisplay.append((0, '- No Available Appliances Detected -'))
            valuesDict["addSmappeeApplianceDeviceEnabled"] = 'false'
        else:
            valuesDict["addSmappeeApplianceDeviceEnabled"] = 'true'

        listToDisplay = sorted(listToDisplay)

        self.listItemsPotentialSmappeeApplianceList = listToDisplay
            
        return valuesDict


    def _addSmappeeApplianceDevice(self, valuesDict, devIdList):
        global pluginGlobal
        autolog(METHOD, u"%s; ValuesDict=[%s]" %  (methodNameForTrace(), valuesDict['potentialSmappeeApplianceList']))  

        for potentialApplianceAddress in valuesDict['potentialSmappeeApplianceList']:
            potentialApplianceAddress = str(potentialApplianceAddress)
            potentialApplianceName = pluginGlobal['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['applianceIds'][potentialApplianceAddress]['name'] 
            if pluginGlobal['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['applianceIds'][potentialApplianceAddress]['queued-add'] == False:
                self.setSmappeeServiceLocationIdToDevId('QUEUE-ADD', 'smappeeAppliance', self.smappeeServiceLocationId, 0, potentialApplianceAddress, potentialApplianceName)
            else:
                self.setSmappeeServiceLocationIdToDevId('DEQUEUE', 'smappeeAppliance', self.smappeeServiceLocationId, 0, potentialApplianceAddress, potentialApplianceName)

        valuesDict = self._prepareGetDefinedSmappeeApplianceList(valuesDict)
        valuesDict = self._prepareGetPotentialSmappeeApplianceList(valuesDict)

        return valuesDict


    def _getDefinedSmappeeActuatorList(self, filter="", valuesDict=None, typeId="", targetId=0):
        global pluginGlobal
        autolog(METHOD, u"%s; LOC=[%s]" %  (methodNameForTrace(), self.smappeeServiceLocationId))  

        return self.listItemsDefinedSmappeeActuatorList

    def _prepareGetDefinedSmappeeActuatorList(self, valuesDict):
        global pluginGlobal
        autolog(METHOD, u"%s; LOC=[%s]" %  (methodNameForTrace(), self.smappeeServiceLocationId))  

        listToDisplay = []

        if self.smappeeServiceLocationId == '' or self.smappeeServiceLocationId == 'NONE':
            return listToDisplay

        for dev in indigo.devices.iter("self"):
            if dev.deviceTypeId == "smappeeActuator" and dev.pluginProps['serviceLocationId'] == self.smappeeServiceLocationId:
                devName = dev.name
                listToDisplay.append((str(dev.id), devName))
  
        if listToDisplay == []:
            listToDisplay.append((0, '- No Actuators Defined -'))
         
        listToDisplay = sorted(listToDisplay,key=lambda x: x[1])

        self.listItemsDefinedSmappeeActuatorList = listToDisplay
            
        return valuesDict


    def _getPotentialSmappeeActuatorList(self, filter="", valuesDict=None, typeId="", targetId=0):
        global pluginGlobal
        autolog(METHOD, u"%s; LOC=[%s]" %  (methodNameForTrace(), self.smappeeServiceLocationId))  

        return self.listItemsPotentialSmappeeActuatorList


    def _prepareGetPotentialSmappeeActuatorList(self, valuesDict):
        global pluginGlobal
        autolog(METHOD, u"%s; LOC=[%s]" %  (methodNameForTrace(), self.smappeeServiceLocationId))  

        listToDisplay = []

        if self.smappeeServiceLocationId == '' or self.smappeeServiceLocationId == 'NONE':
            return listToDisplay

        for actuatorId in sorted(pluginGlobal['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['actuatorIds']):
            actuatorName   = pluginGlobal['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['actuatorIds'][actuatorId]['name']
            actuatorDevId  = pluginGlobal['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['actuatorIds'][actuatorId]['devId']
            queuedAdd      = pluginGlobal['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['actuatorIds'][actuatorId]['queued-add']
            if actuatorDevId == 0:
                if queuedAdd == True:
                    actuatorName = str("QUEUED: %s" % (actuatorName))
                listToDisplay.append((actuatorId, actuatorName))

        if listToDisplay == []:
            listToDisplay.append((0, '- No Available Actuators Detected -'))
            valuesDict["addSmappeeActuatorDeviceEnabled"] = 'false'
        else:
            valuesDict["addSmappeeActuatorDeviceEnabled"] = 'true'

        listToDisplay = sorted(listToDisplay)

        self.listItemsPotentialSmappeeActuatorList = listToDisplay
            
        return valuesDict


    def _addSmappeeActuatorDevice(self, valuesDict, devIdList):
        global pluginGlobal
        autolog(METHOD, u"%s" %  (methodNameForTrace()))  

        for potentialActuatorAddress in valuesDict['potentialSmappeeActuatorList']:
            potentialActuatorAddress = str(potentialActuatorAddress)
            potentialActuatorName = pluginGlobal['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['actuatorIds'][potentialActuatorAddress]['name']
            if pluginGlobal['smappeeServiceLocationIdToDevId'][self.smappeeServiceLocationId]['actuatorIds'][potentialActuatorAddress]['queued-add'] == False:
                self.setSmappeeServiceLocationIdToDevId('QUEUE-ADD', 'smappeeActuator', self.smappeeServiceLocationId, 0, potentialActuatorAddress, potentialActuatorName)
            else:
                self.setSmappeeServiceLocationIdToDevId('DEQUEUE', 'smappeeActuator', self.smappeeServiceLocationId, 0, potentialActuatorAddress, potentialActuatorName)

        valuesDict = self._prepareGetDefinedSmappeeActuatorList(valuesDict)
        valuesDict = self._prepareGetPotentialSmappeeActuatorList(valuesDict)

        return valuesDict


    def validatePrefsConfigUi(self, valuesDict):
        global pluginGlobal
        autolog(METHOD, u"%s" %  (methodNameForTrace()))  



        ### SMAPPEE CONFIG ###

        if "smappeeAddress" in valuesDict:
            pluginGlobal['config']['address'] = valuesDict["smappeeAddress"]
        else:
            pluginGlobal['config']['address'] = "https://app1pub.smappee.net/dev/v1/servicelocation"

        if "smappeeClientId" in valuesDict:
            pluginGlobal['config']['clientId'] = valuesDict["smappeeClientId"]
        else:
            pluginGlobal['config']['clientId'] = ""

        if "smappeeSecret" in valuesDict:
            pluginGlobal['config']['secret'] = valuesDict["smappeeSecret"]
        else:
            pluginGlobal['config']['secret'] = ""

        if "smappeeUserName" in valuesDict:
            pluginGlobal['config']['userName'] = valuesDict["smappeeUserName"]
        else:
            pluginGlobal['config']['userName'] = ""

        if "smappeePassword" in valuesDict:
            pluginGlobal['config']['password'] = valuesDict["smappeePassword"]
        else:
            pluginGlobal['config']['password'] = ""

        ### POLLING ###

        if "statusPolling" in valuesDict:
            pluginGlobal['polling']['status'] = bool(valuesDict["statusPolling"])
        else:
            pluginGlobal['polling']['status'] = False

        # No need to validate 'pollingSeconds' as value can only be selected from a pull down list
        if "pollingSeconds" in valuesDict:
            pluginGlobal['polling']['seconds'] = float(valuesDict["pollingSeconds"])
        else:
            pluginGlobal['polling']['seconds'] = float(300.0)  # Default to 5 minutes

        ### DEBUG ###

        pluginGlobal['debug']['debugFolder'] = valuesDict.get("debugFolder", "/Library/Application Support")

        if not os.path.exists(pluginGlobal['debug']['debugFolder']):
            errorDict = indigo.Dict()
            errorDict["debugFolder"] = "Folder doesn't exist"
            errorDict["showAlertText"] = "Folder doesn't exist, please specify a valid folder."
            return (False, valuesDict, errorDict)

        try:
            path = str('%s/%s' %(pluginGlobal['debug']['debugFolder'], 'autolog/smappee/debug'))
            os.makedirs(path)
        except OSError, e:
            if e.errno != errno.EEXIST:
                errorDict = indigo.Dict()
                errorDict["debugFolder"] = str("Error creating '%s' folder. Error = %s" % (path, e))
                errorDict["showAlertText"] = "Error creating debug folder - please correct error."
                return (False, valuesDict, errorDict)


        if "debugDetailed" in valuesDict:
            pluginGlobal['debug']['detailed'] = bool(valuesDict["debugDetailed"])
        else:
            pluginGlobal['debug']['detailed'] = False

        if "debugDeviceFactory" in valuesDict:
            pluginGlobal['debug']['deviceFactory'] = bool(valuesDict["debugDeviceFactory"])
        else:
            pluginGlobal['debug']['deviceFactory'] = False

        if "debugInterface" in valuesDict:
            pluginGlobal['debug']['interface'] = bool(valuesDict["debugInterface"])
        else:
            pluginGlobal['debug']['interface'] = False

        if "debugMethodTrace" in valuesDict:
            pluginGlobal['debug']['methodTrace'] = bool(valuesDict["debugMethodTrace"])
        else:
            pluginGlobal['debug']['methodTrace'] = False

        if "debugPolling" in valuesDict:
            pluginGlobal['debug']['polling'] = bool(valuesDict["debugPolling"])
        else:
            pluginGlobal['debug']['polling'] = False

        pluginGlobal['debug']['active'] = pluginGlobal['debug']['detailed'] or pluginGlobal['debug']['deviceFactory'] or pluginGlobal['debug']['interface'] or pluginGlobal['debug']['methodTrace'] or pluginGlobal['debug']['polling']


        if pluginGlobal['debug']['active'] == False:
            autolog(INFO, u"No debug logging requested")
        else:
            debugTypes = []
            if pluginGlobal['debug']['detailed'] == True:
                debugTypes.append('Detailed')
            if pluginGlobal['debug']['deviceFactory'] == True:
                debugTypes.append('Device Factory')
            if pluginGlobal['debug']['interface'] == True:
                debugTypes.append('Interface')
            if pluginGlobal['debug']['methodTrace'] == True:
                debugTypes.append('Method Trace')
            if pluginGlobal['debug']['polling'] == True:
                debugTypes.append('Polling')

            loop = 0
            message = ''
            for debugType in debugTypes:
                if loop == 0:
                    message = message + debugType
                else:
                    message = message + ', ' + debugType
                loop += 1

            autolog(INFO, u"Debug logging active for debug types: %s" % (message))  

        return True


    def closedPrefsConfigUi(self, valuesDict, userCancelled):
        global pluginGlobal
        autolog(METHOD, u"%s" %  (methodNameForTrace()))  


        autolog(POLLING, u"'closePrefsConfigUi' called with userCancelled = %s" % (str(userCancelled)))  

        if userCancelled == True:
            return

        # Following logic checks whether polling is required.
        # If it isn't required, then it checks if a polling thread exists and if it does it ends it
        # If it is required, then it checks if a pollling thread exists and 
        #   if a polling thread doesn't exist it will create one as long as the start logic has completed and created a Smappee Command Queue.
        #   In the case where a Smappee command queue hasn't been created then it means 'Start' is yet to run and so 
        #   'Start' will create the polling thread. So this bit of logic is mainly used where polling has been turned off
        #   after starting and then turned on again
        # If polling is required and a polling thread exists, then the logic 'sets' an event to cause the polling thread to awaken and
        #   update the polling interval

        if pluginGlobal['polling']['status'] == False:
            if hasattr(self, 'pollingThread'):
                pluginGlobal['polling']['threadEnd'] = True
                self.pollingEvent.set()  # Stop the Polling Thread
                self.pollingThread.join(5.0)  # Wait for up tp 5 seconds for it to end
                del self.pollingThread  # Delete thread so that it can be recreated if polling is turned on again
        else:
            if not hasattr(self, 'pollingThread'):
                if hasattr(self, 'sendToSmappeeQueue'):
                    self.pollingEvent = threading.Event()
                    self.pollingThread = ThreadPolling(self.pollingEvent, self.sendToSmappeeQueue)
                    self.pollingThread.start()
            else:
                pluginGlobal['polling']['threadEnd'] = False
                self.pollingEvent.set()  # cause the Polling Thread to update immediately with potentially a new polling seconds value
        return


    def runConcurrentThread(self):
        global pluginGlobal
        autolog(METHOD, u"%s" %  (methodNameForTrace()))  

        # This thread is used to handle responses from Smappee


        try:
            while True:
                try:
                    self.process = self.processQueue.get(True,1)  # Retrieve response from Smappee
                    try:   
                        self.handleSmappeeResponse(self.process[0], self.process[1], self.process[2])  # Handle response from Smappee
                    except StandardError, e:
                        autolog(ERROR, u"StandardError detected for function '%s'. Line '%s' has error='%s'" % (self.process[0], sys.exc_traceback.tb_lineno, e))   
                except autologQueueEmpty:
                    if self.stopThread:
                        raise self.StopThread         # Plugin shutdown request.
        except self.StopThread:
            # Optionally catch the StopThread exception and do any needed cleanup.
            autolog(DETAIL, u"runConcurrentThread being stopped")   


    def deviceUpdated(self, origDev, newDev):
        global pluginGlobal
        # autolog(METHOD, u"%s" %  (methodNameForTrace()))  

        indigo.PluginBase.deviceUpdated(self, origDev, newDev)

        return


    def actionControlDimmerRelay(self, action, dev):
        global pluginGlobal
        autolog(METHOD, u"%s" %  (methodNameForTrace()))  
        ###### TURN ON ######
        if action.deviceAction == indigo.kDimmerRelayAction.TurnOn:
            # Command hardware module (dev) to turn ON here:
            self.processTurnOn(action, dev)
            dev.updateStateOnServer("onOffState", True)
            sendSuccess = True      # Assume succeeded

            if sendSuccess:
                # If success then log that the command was successfully sent.
                autolog(INFO, u"sent \"%s\" %s" % (dev.name, "on"))

                # And then tell the Indigo Server to update the state.
                # dev.updateStateOnServer(key="onOffState", value=True, uiValue="on")  # £££££££££££££££££££££££££££££££££££££££££££££££££££££££££££££££££££££££££

            else:
                # Else log failure but do NOT update state on Indigo Server.
                autolog(ERROR, u"send \"%s\" %s failed" % (dev.name, "on"))

        ###### TURN OFF ######
        elif action.deviceAction == indigo.kDimmerRelayAction.TurnOff:
            # Command hardware module (dev) to turn OFF here:
            self.processTurnOff(action, dev)
            dev.updateStateOnServer("onOffState", False)
            sendSuccess = True      # Assume succeeded

            if sendSuccess:
                # If success then log that the command was successfully sent.
                autolog(INFO, u"sent \"%s\" %s" % (dev.name, "off"))

                # And then tell the Indigo Server to update the state:
                # dev.updateStateOnServer(key="onOffState", value=False, uiValue="off")  # £££££££££££££££££££££££££££££££££££££££££££££££££££££££££££££££££££££££££
            else:
                # Else log failure but do NOT update state on Indigo Server.
                autolog(ERROR, u"send \"%s\" %s failed" % (dev.name, "off"))

        ###### TOGGLE ######
        elif action.deviceAction == indigo.kDimmerRelayAction.Toggle:
            # Command hardware module (dev) to toggle here:
            self.processTurnOnOffToggle(action, dev)
            newOnState = not dev.onState
            sendSuccess = True      # Assume succeeded

            if sendSuccess:
                # If success then log that the command was successfully sent.
                autolog(INFO, u"sent \"%s\" %s" % (dev.name, "toggle"))

                # And then tell the Indigo Server to update the state:
                dev.updateStateOnServer("onOffState", newOnState)
            else:
                # Else log failure but do NOT update state on Indigo Server.
                autolog(ERROR, u"send \"%s\" %s failed" % (dev.name, "toggle"))

    #########################
    # General Action callback
    #########################
    def actionControlGeneral(self, action, dev):
        global pluginGlobal
        autolog(METHOD, u"%s" %  (methodNameForTrace()))  
        ###### BEEP ######
        if action.deviceAction == indigo.kDeviceGeneralAction.Beep:
            # Beep the hardware module (dev) here:
            # ** IMPLEMENT ME **
            autolog(INFO, u"sent \"%s\" %s" % (dev.name, "beep request"))

        ###### ENERGY UPDATE ######
        elif action.deviceAction == indigo.kDeviceGeneralAction.EnergyUpdate:
            # Request hardware module (dev) for its most recent meter data here:
            autolog(INFO, u"sent \"%s\" %s" % (dev.name, "energy update request"))
            self.processUpdate(action, dev)

        ###### ENERGY RESET ######
        elif action.deviceAction == indigo.kDeviceGeneralAction.EnergyReset:
            # Request that the hardware module (dev) reset its accumulative energy usage data here:
            autolog(INFO, u"sent \"%s\" %s" % (dev.name, "energy reset request"))
            self.processReset(action, dev)

        ###### STATUS REQUEST ######
        elif action.deviceAction == indigo.kDeviceGeneralAction.RequestStatus:
            # Query hardware module (dev) for its current status here:
 
            autolog(INFO, u"sent \"%s\" %s" % (dev.name, "status request"))


    def processUpdate(self, pluginAction, dev):  # Dev is a Smappee
        global pluginGlobal
        autolog(METHOD, u"%s" %  (methodNameForTrace()))  

 
        autolog(DETAIL, u"'processUpdate' [%s]" % (str(dev.pluginProps['serviceLocationId']))) 

        self.sendToSmappeeQueue.put(["GET_CONSUMPTION",str(dev.pluginProps['serviceLocationId'])])

        return

    def processReset(self, pluginAction, dev):  # Dev is a Smappee
        global pluginGlobal
        autolog(METHOD, u"%s" %  (methodNameForTrace()))  

 
        autolog(DETAIL, u"'processReset' [%s]" % (str(dev.pluginProps['serviceLocationId']))) 

        if "accumEnergyTotal" in dev.states:
            if float(dev.states.get("accumEnergyTotal", 0)) != 0.0:
                autolog(DETAIL, u"'processReset' accumEnergyTotal=[%f]" % (float(dev.states.get("accumEnergyTotal", 0)))) 
                self.sendToSmappeeQueue.put(["RESET_CONSUMPTION",str(dev.pluginProps['serviceLocationId'])])

        return

    def processTurnOnOffToggle(self, pluginAction, dev):  # Dev is a mappee Appliance
        global pluginGlobal
        autolog(METHOD, u"%s" %  (methodNameForTrace()))  


        autolog(DETAIL, u"'processTurnOnOffToggle' [%s]" % (pluginGlobal['smappeePlugs'][dev.id]['address'])) 

        if dev.onState == True:
            self.processTurnOff(pluginAction, dev) 
        else:
            self.processTurnOn(pluginAction, dev)
        return


    def processTurnOn(self, pluginAction, dev):  # Dev is a Smappee Actuator
        global pluginGlobal
        autolog(METHOD, u"%s" %  (methodNameForTrace()))  



        autolog(DETAIL, u"'processTurnOn' [%s]" % (pluginGlobal['smappeePlugs'][dev.id]['address']))

        #  Convert Address from "P012" to "12" i.e. remove leading P and leading 0's
        actuatorAddress = pluginGlobal['smappeePlugs'][dev.id]['address'][1:].lstrip("0")

        self.sendToSmappeeQueue.put(['ON', str(dev.pluginProps['serviceLocationId']), actuatorAddress])

        return


    def processTurnOff(self, pluginAction, dev):  # Dev is a Smappee Appliance
        global pluginGlobal
        autolog(METHOD, u"%s" %  (methodNameForTrace()))  
 
 
        autolog(DETAIL, u"'processTurnOff' [%s]" % (pluginGlobal['smappeePlugs'][dev.id]['address'])) 

        #  Convert Address from "P012" to "12" i.e. remove leading P and leading 0's
        actuatorAddress = pluginGlobal['smappeePlugs'][dev.id]['address'][1:].lstrip("0")

        self.sendToSmappeeQueue.put(['OFF', str(dev.pluginProps['serviceLocationId']), actuatorAddress])

        return


    def handleCreateNewSensor(self, commandSentToSmappee, responseLocationId, responseFromSmappee):
        global pluginGlobal
        autolog(METHOD, u"%s" %  (methodNameForTrace()))  

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
                folder=pluginGlobal['deviceFolderId'],
                props={"SupportsBatteryLevel":True,
                       "SupportsEnergyMeter":True,
                       "SupportsEnergyMeterCurPower":True,
                       "serviceLocationId":serviceLocationId,
                       "serviceLocationName":serviceLocationName,
                       "optionsEnergyMeterCurPower":"last", 
                       "hideEnergyMeterCurPower":False, 
                       "hideEnergyMeterAccumPower":False,
                       "dailyStandingCharge":"0.00",
                       "units":"kWh",
                       "unitCost":"0.00"})

            self.setSmappeeServiceLocationIdToDevId('DEQUEUE', 'smappeeSensor', serviceLocationId, smappeeSensorDev.id, address, name)

        except StandardError, e:
            autolog(ERROR, u"StandardError detected in 'createNewSensor'. Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))   
            autolog(ERROR, u"Response from Smappee was:'%s'" % (responseFromSmappee))   


    def handleCreateNewAppliance(self, commandSentToSmappee, responseLocationId, responseFromSmappee):
        global pluginGlobal
        autolog(METHOD, u"%s" %  (methodNameForTrace()))  

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
                folder=pluginGlobal['deviceFolderId'],
                props={"SupportsEnergyMeter":True,
                       "SupportsEnergyMeterCurPower":True,
                       "serviceLocationId":serviceLocationId,
                       "serviceLocationName":serviceLocationName,
                       "smappeeApplianceEventLastRecordedTimestamp":0.0,
                       "showApplianceEventStatus":True,
                       "hideApplianceSmappeeEvents":False,
                       "smappeeApplianceEventStatus":"NONE"})

            self.setSmappeeServiceLocationIdToDevId('DEQUEUE', 'smappeeAppliance', serviceLocationId, smappeeApplianceDev.id, address, name)

        except StandardError, e:
            autolog(ERROR, u"StandardError detected in 'createNewAppliance'. Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))   
            autolog(ERROR, u"Response from Smappee was:'%s'" % (responseFromSmappee))


    def handleCreateNewActuator(self, commandSentToSmappee, responseLocationId, responseFromSmappee):
        global pluginGlobal
        autolog(METHOD, u"%s" %  (methodNameForTrace()))  

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
                folder=pluginGlobal['deviceFolderId'],
                props={"SupportsStatusRequest":False,
                       "SupportsAllOff":True,
                       "SupportsEnergyMeter":False,
                       "SupportsEnergyMeterCurPower":False,
                       "serviceLocationId":serviceLocationId,
                       "serviceLocationName":serviceLocationName})

            self.setSmappeeServiceLocationIdToDevId('DEQUEUE', 'smappeeActuator', serviceLocationId, smappeeActuatorDev.id, address, name)

        except StandardError, e:
            autolog(ERROR, u"StandardError detected in 'createNewActuator'. Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))   
            autolog(ERROR, u"Response from Smappee was:'%s'" % (responseFromSmappee))


    def validateSmappeResponse(self, commandSentToSmappee, responseLocationId, responseFromSmappee):
        global pluginGlobal
        autolog(METHOD, u"%s" %  (methodNameForTrace()))  

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

                autolog(ERROR, u"%s" % (message))
                return (False, '')  

            # Ensure that response is enclose in square brackets '[' and ']'
            try:
                if responseFromSmappee[:1] != '[':
                    responseFromSmappee = '[' + responseFromSmappee + ']'
            except StandardError, e:
                autolog(ERROR, u"StandardError detected in 'validateSmappeResponse'. Type=%s, Len=%s" % (type(responseFromSmappee), len(responseFromSmappee)))
                if len(responseFromSmappee) == 3:   
                    autolog(ERROR, u"StandardError detected in 'validateSmappeResponse'. Item[1]=%s" % (responseFromSmappee[0]))
                    autolog(ERROR, u"StandardError detected in 'validateSmappeResponse'. Item[2]=%s" % (responseFromSmappee[1]))
                    autolog(ERROR, u"StandardError detected in 'validateSmappeResponse'. Item[3]=%s" % (responseFromSmappee[2]))

                autolog(ERROR, u"StandardError detected in 'validateSmappeResponse'. Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))   
                autolog(ERROR, u"Response from Smappee was:'%s'" % (str(responseFromSmappee)))

            # Decode response
            decoded = json.loads(responseFromSmappee)

            # Ensure decoded is a list  
            if type(decoded) != 'list':
                decoded = (decoded)

            return (True, decoded)  

        except StandardError, e:
            autolog(ERROR, u"StandardError detected in 'validateSmappeResponse'. Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))   
            autolog(ERROR, u"Response from Smappee was:'%s'" % (str(responseFromSmappee)))
            return (False, '')


    def handleGetEvents(self, responseLocationId, decodedSmappeeResponse):
        global pluginGlobal
        autolog(METHOD, u"%s" %  (methodNameForTrace()))  

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
                applianceId = str("%s%s" % (str(smappeeType), str("00%s" % (applianceId))[-3:]))

                if applianceId in pluginGlobal['smappeeServiceLocationIdToDevId'][responseLocationId]['applianceIds']:
                    if pluginGlobal['smappeeServiceLocationIdToDevId'][responseLocationId]['applianceIds'][applianceId]['devId'] != 0:

                        smappeeApplianceDevId = pluginGlobal['smappeeServiceLocationIdToDevId'][responseLocationId]['applianceIds'][applianceId]['devId']
                        showCurrentPower = smappeeApplianceDev.pluginProps['SupportsEnergyMeterCurPower']
                        if showCurrentPower == True:
                            smappeeApplianceDev.updateStateOnServer("curEnergyLevel", 0.0, uiValue="0 kWh")

                        smappeeApplianceDev = indigo.devices[smappeeApplianceDevId]


                        # Check if timestamp to be processed and if not bale out!
                        if eventTimestamp > float(smappeeApplianceDev.states['smappeeApplianceEventLastRecordedTimestamp']):
                            eventTimestampStr = datetime.datetime.fromtimestamp(int(eventTimestamp/1000)).strftime('%Y-%b-%d %H:%M:%S')
                            smappeeApplianceDev.updateStateOnServer("smappeeApplianceEventLastRecordedTimestamp", float(eventTimestamp), uiValue=eventTimestampStr)
                            showCurrentPower = smappeeApplianceDev.pluginProps['SupportsEnergyMeterCurPower']
                            showOnOffState = smappeeApplianceDev.pluginProps['showApplianceEventStatus']
                            hideEvents = smappeeApplianceDev.pluginProps['hideApplianceSmappeeEvents']

                            activePowerStr = "%d W" % (activePower)

                            if showCurrentPower == True:
                                smappeeApplianceDev.updateStateOnServer("curEnergyLevel", activePower, uiValue=activePowerStr)

                            if showOnOffState == True:
                                if applianceStatus == 'ON':
                                    smappeeApplianceDev.updateStateOnServer("smappeeApplianceEventStatus", "UP", uiValue=activePowerStr)
                                else:
                                    smappeeApplianceDev.updateStateOnServer("smappeeApplianceEventStatus", "DOWN", uiValue=activePowerStr)

                            if hideEvents == False:
                                    eventTimestampStr = datetime.datetime.fromtimestamp(int(eventTimestamp/1000)).strftime('%H:%M:%S')
                                    pass
                                    autolog(INFO, u"recorded Smappee Appliance '%s' event at [%s], reading: %s" % (smappeeApplianceDev.name, eventTimestampStr, activePowerStr))

                            if float(indigo.server.apiVersion) >= 1.18:
                                smappeeApplianceDev.updateStateImageOnServer(indigo.kStateImageSel.EnergyMeterOn)

        except StandardError, e:
            autolog(ERROR, u"StandardError detected in 'handleGetEvents'. Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))   
            autolog(ERROR, u"Decoded response from Smappee was:'%s'" % (decodedSmappeeResponse))


    def handleInitialise(self, commandSentToSmappee, responseLocationId, decodedSmappeeResponse):
        global pluginGlobal
        autolog(METHOD, u"%s" %  (methodNameForTrace()))  

        try:
            for decoding in decodedSmappeeResponse:
                for key, value in decoding.iteritems():

                    if key == 'access_token':
                        pluginGlobal['config']['accessToken'] = value
                        autolog(INFO, u"Authenticated with Smappee but initialisation still in progress ...")
                        # Now request Location info (but only if Initialise i.e. not if Refresh_Token)
                        if commandSentToSmappee == 'INITIALISE':
                            self.sendToSmappeeQueue.put(['GET_SERVICE_LOCATIONS'])
                    elif key == 'expires_in':
                        pluginGlobal['config']['tokenExpiresIn'] = int(value)
                        preAdjustedTokenExpiresDateTimeUtc = time.mktime((indigo.server.getTime() + datetime.timedelta(seconds=pluginGlobal['config']['tokenExpiresIn'])).timetuple())
                        pluginGlobal['config']['tokenExpiresDateTimeUtc'] = preAdjustedTokenExpiresDateTimeUtc - float(pluginGlobal['polling']['seconds'] + 300)  # Adjust token expiry time taking account of polling time + 5 minute safety margin 
                        autolog(DETAIL, u"tokenExpiresDateTimeUtc [T] : Was [%s], is now [%s]" % (preAdjustedTokenExpiresDateTimeUtc, pluginGlobal['config']['tokenExpiresDateTimeUtc']))
                    elif key == 'refresh_token':
                        pluginGlobal['config']['refreshToken'] = value
                    elif key == 'error':
                        autolog(ERROR, u"SMAPPEE ERROR DETECTED [%s]: %s" % (commandSentToSmappee, value))
                    else:
                        pass  # Unknown key/value pair
                        autolog(DETAIL, u"Unhandled key/value pair : K=[%s], V=[%s]" % (key, value))

        except StandardError, e:
            autolog(ERROR, u"StandardError detected in 'handleInitialise'. Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))   
            autolog(ERROR, u"Decoded response from Smappee was:'%s'" % (decodedSmappeeResponse))


    def handleGetServiceLocations(self, responseLocationId, decodedSmappeeResponse):
        global pluginGlobal
        autolog(METHOD, u"%s" %  (methodNameForTrace()))  

        try:
            for decoding in decodedSmappeeResponse:
                for key, value in decoding.iteritems():
                    if key == 'appName':
                        pluginGlobal['config']['appName'] = str(value)
                    elif key == 'serviceLocations':
                        for self.serviceLocationItem in value:
                            self.serviceLocationId = ""
                            self.serviceLocationName = ""
                            for key2, value2 in self.serviceLocationItem.iteritems():
                                autolog(DETAIL, u"handleSmappeeResponse [H][SERVICELOCATION] -  [%s : %s]" % (key2, value2))
                                if key2 == 'serviceLocationId':
                                    self.serviceLocationId = str(value2)
                                elif key2 == 'name':
                                    self.serviceLocationName = str(value2)
                                else:
                                    pass  # Unknown key/value pair
                            if self.serviceLocationId != "":
                                if self.serviceLocationId in pluginGlobal['smappeeServiceLocationIdToDevId']:
                                    pluginGlobal['smappeeServiceLocationIdToDevId'][self.serviceLocationId]['name'] = self.serviceLocationName
                                    if 'electricityId' not in pluginGlobal['smappeeServiceLocationIdToDevId'][self.serviceLocationId]:
                                        pluginGlobal['smappeeServiceLocationIdToDevId'][self.serviceLocationId]['electricityId'] = int(0)
                                    if 'electricityNetId' not in pluginGlobal['smappeeServiceLocationIdToDevId'][self.serviceLocationId]:
                                        pluginGlobal['smappeeServiceLocationIdToDevId'][self.serviceLocationId]['electricityNetId'] = int(0)
                                    if 'electricitySavedId' not in pluginGlobal['smappeeServiceLocationIdToDevId'][self.serviceLocationId]:
                                        pluginGlobal['smappeeServiceLocationIdToDevId'][self.serviceLocationId]['electricitySavedId'] = int(0)
                                    if 'solarId' not in pluginGlobal['smappeeServiceLocationIdToDevId'][self.serviceLocationId]:
                                        pluginGlobal['smappeeServiceLocationIdToDevId'][self.serviceLocationId]['solarId'] = int(0)
                                    if 'solarUsedId' not in pluginGlobal['smappeeServiceLocationIdToDevId'][self.serviceLocationId]:
                                        pluginGlobal['smappeeServiceLocationIdToDevId'][self.serviceLocationId]['solarUsedId'] = int(0)
                                    if 'solarExportedId' not in pluginGlobal['smappeeServiceLocationIdToDevId'][self.serviceLocationId]:
                                        pluginGlobal['smappeeServiceLocationIdToDevId'][self.serviceLocationId]['solarExportedId'] = int(0)
                                    if 'sensorIds' not in pluginGlobal['smappeeServiceLocationIdToDevId'][self.serviceLocationId]:
                                        pluginGlobal['smappeeServiceLocationIdToDevId'][self.serviceLocationId]['sensorIds'] = {}
                                    if 'applianceIds' not in pluginGlobal['smappeeServiceLocationIdToDevId'][self.serviceLocationId]:
                                        pluginGlobal['smappeeServiceLocationIdToDevId'][self.serviceLocationId]['applianceIds'] = {}
                                    if 'actuatorIds' not in pluginGlobal['smappeeServiceLocationIdToDevId'][self.serviceLocationId]:
                                        pluginGlobal['smappeeServiceLocationIdToDevId'][self.serviceLocationId]['actuatorIds'] = {}
                                else:  
                                    pluginGlobal['smappeeServiceLocationIdToDevId'][self.serviceLocationId] = {}
                                    pluginGlobal['smappeeServiceLocationIdToDevId'][self.serviceLocationId]['name'] = self.serviceLocationName  
                                    pluginGlobal['smappeeServiceLocationIdToDevId'][self.serviceLocationId]['electricityId'] = int(0)  
                                    pluginGlobal['smappeeServiceLocationIdToDevId'][self.serviceLocationId]['electricityNetId'] = int(0)
                                    pluginGlobal['smappeeServiceLocationIdToDevId'][self.serviceLocationId]['electricitySavedId'] = int(0)
                                    pluginGlobal['smappeeServiceLocationIdToDevId'][self.serviceLocationId]['solarId'] = int(0)
                                    pluginGlobal['smappeeServiceLocationIdToDevId'][self.serviceLocationId]['solarUsedId'] = int(0)
                                    pluginGlobal['smappeeServiceLocationIdToDevId'][self.serviceLocationId]['solarExportedId'] = int(0)
                                    pluginGlobal['smappeeServiceLocationIdToDevId'][self.serviceLocationId]['sensorIds'] = {}
                                    pluginGlobal['smappeeServiceLocationIdToDevId'][self.serviceLocationId]['applianceIds'] = {}
                                    pluginGlobal['smappeeServiceLocationIdToDevId'][self.serviceLocationId]['actuatorIds'] = {}

                                autolog(DETAIL, u"handleSmappeeResponse [HH][SERVICELOCATION]: %s" % (pluginGlobal['smappeeServiceLocationIdToDevId'][self.serviceLocationId]))

                        for self.serviceLocationId, self.serviceLocationDetails in pluginGlobal['smappeeServiceLocationIdToDevId'].iteritems():

                            for smappeeDev in indigo.devices.iter("self"):

                                if smappeeDev.deviceTypeId == "smappeeElectricity":
                                    autolog(DETAIL, u"handleSmappeeResponse [J] Checking new Smappee Service Location Id: [%s] against known Smappee Electricity Device Id [%s]" % (type(self.serviceLocationId), type(smappeeDev.address)))
                                    if smappeeDev.pluginProps['serviceLocationId'] == self.serviceLocationId:
                                        if self.serviceLocationDetails['electricityId'] == 0:
                                            pluginGlobal['smappeeServiceLocationIdToDevId'][self.serviceLocationId]['electricityId'] = smappeeDev.id
                                        else:
                                            if self.serviceLocationDetails['electricityId'] != smappeeDev.id:
                                                autolog(ERROR, u"DUPLICATE SMAPPEE ELECTRICITY DEVICE / LOCATION. L=[%s], D1=[%s], D2=[%s]" % (self.serviceLocationId, pluginGlobal['smappeeServiceLocationIdToDevId'][self.serviceLocationId]['electricityId'], smappeeDev.id))

                                elif smappeeDev.deviceTypeId == "smappeeElectricityNet":
                                    autolog(DETAIL, u"handleSmappeeResponse [J] Checking new Smappee Service Location Id: [%s] against known Smappee Electricity Net Device Id [%s]" % (type(self.serviceLocationId), type(smappeeDev.address)))
                                    if smappeeDev.pluginProps['serviceLocationId'] == self.serviceLocationId:
                                        if self.serviceLocationDetails['electricityNetId'] == 0:
                                            pluginGlobal['smappeeServiceLocationIdToDevId'][self.serviceLocationId]['electricityNetId'] = smappeeDev.id
                                        else:
                                            if self.serviceLocationDetails['electricityNetId'] != smappeeDev.id:
                                                autolog(ERROR, u"DUPLICATE SMAPPEE ELECTRICITY NET DEVICE / LOCATION. L=[%s], D1=[%s], D2=[%s]" % (self.serviceLocationId, pluginGlobal['smappeeServiceLocationIdToDevId'][self.serviceLocationId]['electricityNetId'], smappeeDev.id))

                                elif smappeeDev.deviceTypeId == "smappeeElectricitySaved":
                                    autolog(DETAIL, u"handleSmappeeResponse [J] Checking new Smappee Service Location Id: [%s] against known Smappee Electricity Saved Device Id [%s]" % (type(self.serviceLocationId), type(smappeeDev.address)))
                                    if smappeeDev.pluginProps['serviceLocationId'] == self.serviceLocationId:
                                        if self.serviceLocationDetails['electricitySavedId'] == 0:
                                            pluginGlobal['smappeeServiceLocationIdToDevId'][self.serviceLocationId]['electricitySavedId'] = smappeeDev.id
                                        else:
                                            if self.serviceLocationDetails['electricitySavedId'] != smappeeDev.id:
                                                autolog(ERROR, u"DUPLICATE SMAPPEE ELECTRICITY SAVED DEVICE / LOCATION. L=[%s], D1=[%s], D2=[%s]" % (self.serviceLocationId, pluginGlobal['smappeeServiceLocationIdToDevId'][self.serviceLocationId]['electricitySavedId'], smappeeDev.id))

                                elif smappeeDev.deviceTypeId == "smappeeSolar":
                                    autolog(DETAIL, u"handleSmappeeResponse [J] Checking new Smappee Service Location Id: [%s] against known Smappee Solar Device Id [%s]" % (type(self.serviceLocationId), type(smappeeDev.address)))
                                    if smappeeDev.pluginProps['serviceLocationId'] == self.serviceLocationId:
                                        if self.serviceLocationDetails['solarId'] == 0:
                                            pluginGlobal['smappeeServiceLocationIdToDevId'][self.serviceLocationId]['solarId'] = smappeeDev.id
                                        else:
                                            if self.serviceLocationDetails['solarId'] != smappeeDev.id:
                                                autolog(ERROR, u"DUPLICATE SMAPPEE SOLAR DEVICE / LOCATION. L=[%s], D1=[%s], D2=[%s]" % (self.serviceLocationId, pluginGlobal['smappeeServiceLocationIdToDevId'][self.serviceLocationId]['solarId'], smappeeDev.id))

                                elif smappeeDev.deviceTypeId == "smappeeSolarUsed":
                                    autolog(DETAIL, u"handleSmappeeResponse [J] Checking new Smappee Service Location Id: [%s] against known Smappee Solar Used Device Id [%s]" % (type(self.serviceLocationId), type(smappeeDev.address)))
                                    if smappeeDev.pluginProps['serviceLocationId'] == self.serviceLocationId:
                                        if self.serviceLocationDetails['solarUsedId'] == 0:
                                            pluginGlobal['smappeeServiceLocationIdToDevId'][self.serviceLocationId]['solarUsedId'] = smappeeDev.id
                                        else:
                                            if self.serviceLocationDetails['solarUsedId'] != smappeeDev.id:
                                                autolog(ERROR, u"DUPLICATE SMAPPEE SOLAR USED DEVICE / LOCATION. L=[%s], D1=[%s], D2=[%s]" % (self.serviceLocationId, pluginGlobal['smappeeServiceLocationIdToDevId'][self.serviceLocationId]['solarUsedId'], smappeeDev.id))

                                elif smappeeDev.deviceTypeId == "smappeeSolarExported":
                                    autolog(DETAIL, u"handleSmappeeResponse [J] Checking new Smappee Service Location Id: [%s] against known Smappee Solar Exported Device Id [%s]" % (type(self.serviceLocationId), type(smappeeDev.address)))
                                    if smappeeDev.pluginProps['serviceLocationId'] == self.serviceLocationId:
                                        if self.serviceLocationDetails['solarExportedId'] == 0:
                                            pluginGlobal['smappeeServiceLocationIdToDevId'][self.serviceLocationId]['solarExportedId'] = smappeeDev.id
                                        else:
                                            if self.serviceLocationDetails['solarExportedId'] != smappeeDev.id:
                                                autolog(ERROR, u"DUPLICATE SMAPPEE SOLAR EXPORTED DEVICE / LOCATION. L=[%s], D1=[%s], D2=[%s]" % (self.serviceLocationId, pluginGlobal['smappeeServiceLocationIdToDevId'][self.serviceLocationId]['solarExportedId'], smappeeDev.id))

                                elif smappeeDev.deviceTypeId == "smappeeSensor":
                                    autolog(DETAIL, u"handleSmappeeResponse [J] Checking new Smappee Service Location Id: [%s] against known Smappee Sensor Device Id [%s]" % (type(self.serviceLocationId), type(smappeeDev.address)))
                                    if smappeeDev.pluginProps['serviceLocationId'] == self.serviceLocationId:
                                        if self.serviceLocationDetails['sensorIds'][smappeeDev.address] == 0:
                                            pluginGlobal['smappeeServiceLocationIdToDevId'][self.serviceLocationId]['sensorIds'][smappeeDev.address] = {'name': smappeeDev.name, 'devId': smappeeDev.id}
                                    #    else:
                                    #        if self.serviceLocationDetails['sensorIds'] != smappeeDev.id:
                                    #           autolog(ERROR, u"DUPLICATE SMAPPEE SENSOR DEVICE / LOCATION. L=[%s], D1=[%s], D2=[%s]" % (self.serviceLocationId, pluginGlobal['smappeeServiceLocationIdToDevId'][self.serviceLocationId]['electricityId'], smappeeDev.id))

                                elif smappeeDev.deviceTypeId == "smappeeAppliance":
                                    autolog(DETAIL, u"handleSmappeeResponse [J] Checking new Smappee Service Location Id: [%s] against known Smappee Appliance Device Id [%s]" % (type(self.serviceLocationId), type(smappeeDev.address)))
                                    if smappeeDev.pluginProps['serviceLocationId'] == self.serviceLocationId:
                                        if self.serviceLocationDetails['applianceIds'][smappeeDev.address] == 0:
                                            pluginGlobal['smappeeServiceLocationIdToDevId'][self.serviceLocationId]['applianceIds'][smappeeDev.address] = {'name': smappeeDev.name, 'devId': smappeeDev.id}
                                    #    else:
                                    #        if self.serviceLocationDetails['electricity'] != smappeeDev.id:
                                    #           autolog(ERROR, u"DUPLICATE SMAPPEE APPLIANCE DEVICE / LOCATION. L=[%s], D1=[%s], D2=[%s]" % (self.serviceLocationId, pluginGlobal['smappeeServiceLocationIdToDevId'][self.serviceLocationId]['electricityId'], smappeeDev.id))

                                elif smappeeDev.deviceTypeId == "smappeeActuator":
                                    autolog(DETAIL, u"handleSmappeeResponse [J] Checking new Smappee Service Location Id: [%s] against known Smappee Actuator Device Id [%s]" % (type(self.serviceLocationId), type(smappeeDev.address)))
                                    if smappeeDev.pluginProps['serviceLocationId'] == self.serviceLocationId:
                                        if self.serviceLocationDetails['actuatorIds'][smappeeDev.address] == 0:
                                            pluginGlobal['smappeeServiceLocationIdToDevId'][self.serviceLocationId]['actuatorIds'][smappeeDev.address] = {'name': smappeeDev.name, 'devId': smappeeDev.id}
                                    #    else:
                                    #        if self.serviceLocationDetails['electricity'] != smappeeDev.id:
                                    #            autolog(ERROR, u"DUPLICATE SMAPPEE ACTUATOR DEVICE / LOCATION. L=[%s], D1=[%s], D2=[%s]" % (self.serviceLocationId, pluginGlobal['smappeeServiceLocationIdToDevId'][self.serviceLocationId]['electricityId'], smappeeDev.id))

                            autolog(DETAIL, u"handleSmappeeResponse [HH][SERVICELOCATION DETAILS]: %s = %s" % (self.serviceLocationId, self.serviceLocationDetails))

                            self.sendToSmappeeQueue.put(['GET_SERVICE_LOCATION_INFO',self.serviceLocationId])

                        if pluginGlobal['pluginInitialised'] == False:
                            autolog(DETAIL, u"handleSmappeeResponse [HH][SERVICELOCATION plugin initialised]: %s " % (pluginGlobal['pluginInitialised']))
                            pluginGlobal['pluginInitialised'] = True
                            autolog(INFO, u"Initialisation completed.")
                        else:
                            pass
                            autolog(DETAIL, u"handleSmappeeResponse [HH][SERVICELOCATION plugin already initialised]: %s " % (pluginGlobal['pluginInitialised']))

                        autolog(DETAIL, u"handleSmappeeResponse [HH][SERVICELOCATION pluginInitialised: FINAL]: %s " % (pluginGlobal['pluginInitialised']))

                    elif key == 'error':
                        autolog(ERROR, u"SMAPPEE ERROR DETECTED [%s]: %s" % (commandSentToSmappee, value))
                    else:
                        pass  # Unknown key/value pair
                        autolog(DETAIL, u"Unhandled key/value pair : K=[%s], V=[%s]" % (key, value))

        except StandardError, e:
            autolog(ERROR, u"StandardError detected in 'handleGetServiceLocations'. Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))   
            autolog(ERROR, u"Decoded response from Smappee was:'%s'" % (decodedSmappeeResponse))


    def handleGetServiceLocationInfo(self, responseLocationId, decodedSmappeeResponse):
        global pluginGlobal
        autolog(METHOD, u"%s" %  (methodNameForTrace()))  

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
                                autolog(DETAIL, u"handleSmappeeResponse [F][SENSOR] -  [%s : %s]" % (key2, value2))
                                if key2 == 'id':
                                    smappeeType = 'GW'  # Sensor for Gas Water
                                    self.sensorId = str("%s%s" % (str(smappeeType), str("00%s" % (value2))[-2:]))
                                elif key2 == 'name':
                                    self.sensorName = str(value2)
                                else:
                                    pass  # Unknown key/value pair
                            autolog(DETAIL, u"handleSmappeeResponse [FF][SENSOR] - [%s]-[%s]" % (self.sensorId, self.sensorName))

                            if self.sensorId != "":
                                # At this point we have detected a Smappee Sensor Device
                                pluginGlobal['config']['supportsSensor'] = True
                                # Two Indigo devices can be created for each Smappee Sensor to represent the two channels (inputs) which could be measuring both Gas and Water
                                # Define a common function (below) to add an Indigo device
                                def createSensor(sensorIdModifier):
                                    if self.sensorName == "":
                                        sensorName = str("[%s-%s] 'Unlabeled'" % (self.sensorId, sensorIdModifier))
                                    else:
                                        sensorName = str("[%s-%s] %s" % (self.sensorId, sensorIdModifier, str(self.sensorName).strip()))

                                    sensorId = self.sensorId + '-' + sensorIdModifier

                                    autolog(DETAIL, u"handleSmappeeResponse [FF-A][SENSOR] - [%s]-[%s]" % (sensorId, sensorName))

                                    if sensorId in pluginGlobal['smappeeServiceLocationIdToDevId'][responseLocationId]['sensorIds']:
                                        autolog(DETAIL, u"handleSmappeeResponse [FF-B][SENSOR] - [%s]-[%s]" % (sensorId, sensorName))
                                        if pluginGlobal['smappeeServiceLocationIdToDevId'][responseLocationId]['sensorIds'][sensorId]['devId'] != 0:
                                            try:
                                                autolog(DETAIL, u"handleSmappeeResponse [FF-C][SENSOR] - [%s]-[%s]" % (sensorId, sensorName))
                                                # Can be either Gas or Water
                                                smappeeSensorDev = indigo.devices[pluginGlobal['smappeeServiceLocationIdToDevId'][responseLocationId]['sensorIds'][sensorId]['devId']]
                                                if smappeeSensorDev.states['smappeeSensorOnline'] == False:
                                                    smappeeSensorDev.updateStateOnServer("smappeeSensorOnline", True, uiValue='online')
                                            except:
                                                pass
                                    else:
                                        # Can be either Gas or Water
                                        self.setSmappeeServiceLocationIdToDevId('ADD_UPDATE', 'smappeeSensor', responseLocationId, 0, sensorId, sensorName)
                                        autolog(DETAIL, u"handleSmappeeResponse [FF-D][SENSOR] - [%s]-[%s]" % (sensorId, sensorName))

                                # Now add the devices
                                createSensor('A')
                                createSensor('B')

                    elif key == 'appliances':
                        for self.applianceItem in value:
                            self.applianceName = ""
                            self.applianceId = ""
                            for key2, value2 in self.applianceItem.iteritems():
                                autolog(DETAIL, u"handleSmappeeResponse [F][APPLIANCE] -  [%s : %s]" % (key2, value2))
                                if key2 == 'id':
                                    smappeeType = 'A'  # Appliance
                                    self.applianceId = str("%s%s" % (str(smappeeType), str("00%s" % (value2))[-3:]))
                                elif key2 == 'name':
                                    self.applianceName = str(value2)
                                elif key2 == 'type':
                                    self.applianceType = value2
                                else:
                                    pass  # Unknown key/value pair
                            autolog(DETAIL, u"handleSmappeeResponse [FF][APPLIANCE] - [%s]-[%s]-[%s]" % (self.applianceId, self.applianceName, self.applianceType))

                            if self.applianceId != "":
                                if self.applianceName == "":
                                    self.applianceName = str("[%s] 'Unlabeled'" % (self.applianceId))
                                else:
                                    self.applianceName = str("[%s] %s" % (self.applianceId, str(self.applianceName).strip()))

                                if self.applianceId in pluginGlobal['smappeeServiceLocationIdToDevId'][responseLocationId]['applianceIds']:
                                    if pluginGlobal['smappeeServiceLocationIdToDevId'][responseLocationId]['applianceIds'][self.applianceId]['devId'] != 0:
                                        try:
                                            smappeeApplianceDev = indigo.devices[pluginGlobal['smappeeServiceLocationIdToDevId'][responseLocationId]['applianceIds'][self.applianceId]['devId']]
                                            if smappeeApplianceDev.states['smappeeApplianceOnline'] == False:
                                                smappeeApplianceDev.updateStateOnServer("smappeeApplianceOnline", True, uiValue='online')
                                        except:
                                            pass
                                else:
                                    self.setSmappeeServiceLocationIdToDevId('ADD_UPDATE', 'smappeeAppliance', responseLocationId, 0, self.applianceId, self.applianceName)

                    elif key == 'actuators':
                        for self.actuatorItem in value:
                            self.actuatorName = ""
                            self.actuatorId = ""
                            for key2, value2 in self.actuatorItem.iteritems():
                                autolog(DETAIL, u"handleSmappeeResponse [F2][ACTUATOR] -  [%s : %s]" % (key2, value2))
                                if key2 == 'id':
                                    smappeeType = 'P'  # Plug
                                    self.actuatorId = str("%s%s" % (str(smappeeType), str("00%s" % (value2))[-3:]))
                                elif key2 == 'name':
                                    self.actuatorName = str(value2)
                                else:
                                    pass  # Unknown key/value pair
                            autolog(DETAIL, u"handleSmappeeResponse [F2F][ACTUATOR] - [%s]-[%s]" % (self.actuatorId, self.actuatorName))

                            if self.actuatorId != "":
                                if self.actuatorName == "":
                                    self.actuatorName = str("[%s] 'Unlabeled'" % (self.actuatorId))
                                else:
                                    self.actuatorName = str("[%s] %s" % (self.actuatorId, str(self.actuatorName).strip()))

                                if self.actuatorId in pluginGlobal['smappeeServiceLocationIdToDevId'][responseLocationId]['actuatorIds']:
                                    if pluginGlobal['smappeeServiceLocationIdToDevId'][responseLocationId]['actuatorIds'][self.actuatorId]['devId'] != 0:
                                        try:
                                            smappeeActuatorDev = indigo.devices[pluginGlobal['smappeeServiceLocationIdToDevId'][responseLocationId]['actuatorIds'][self.actuatorId]['devId']]
                                            if smappeeActuatorDev.states['smappeeActuatorOnline'] == False:
                                                smappeeActuatorDev.updateStateOnServer("smappeeActuatorOnline", True, uiValue='online')
                                            # autolog(DETAIL, u"handleSmappeeResponse [J] Checking new Smappee Appliance Id: [%s] against known Smappee Appliance Id [%s]" % (self.applianceId, smappeeApplianceDev.address))
                                        except:
                                            pass
                                else:
                                    self.setSmappeeServiceLocationIdToDevId('ADD_UPDATE', 'smappeeActuator', responseLocationId, 0, self.actuatorId, self.actuatorName)

                    elif key == 'error':
                        autolog(ERROR, u"SMAPPEE ERROR DETECTED [%s]: %s" % (commandSentToSmappee, value))
                    else:
                        pass  # Unknown key/value pair
                        autolog(DETAIL, u"Unhandled key/value pair : K=[%s], V=[%s]" % (key, value))

        except StandardError, e:
            autolog(ERROR, u"StandardError detected in 'handleGetServiceLocationInfo'. Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))   
            autolog(ERROR, u"Decoded response from Smappee was:'%s'" % (responseFromSmappee))


    def handleGetConsumption(self, commandSentToSmappee, responseLocationId, decodedSmappeeResponse):
        global pluginGlobal
        autolog(METHOD, u"%s" %  (methodNameForTrace()))  

        try:
            for decoding in decodedSmappeeResponse:
                for key, value in decoding.iteritems():


                    if key == 'serviceLocationId':
                        pass
                    elif key == 'consumptions':

                        if pluginGlobal['config']['supportsElectricity'] == True:
                            devElectricity = indigo.devices[pluginGlobal['smappeeServiceLocationIdToDevId'][responseLocationId]['electricityId']]
                            self.lastReadingElectricityUtc = pluginGlobal['smappees'][devElectricity.id]['lastReadingElectricityUtc']
                            autolog(DETAIL, u"handleSmappeeResponse [LRU-ELECTRICITY]: %s" % (self.lastReadingElectricityUtc))

                            if devElectricity.states['smappeeElectricityOnline'] == False:
                                devElectricity.updateStateOnServer("smappeeElectricityOnline", True, uiValue='online')

                        if pluginGlobal['config']['supportsElectricityNet'] == True:
                            devElectricityNet = indigo.devices[pluginGlobal['smappeeServiceLocationIdToDevId'][responseLocationId]['electricityNetId']]
                            self.lastReadingElectricityNetUtc = pluginGlobal['smappees'][devElectricityNet.id]['lastReadingElectricityNetUtc']
                            autolog(DETAIL, u"handleSmappeeResponse [LRU-NET-ELECTRICITY]: %s" % (self.lastReadingElectricityNetUtc))

                            if devElectricityNet.states['smappeeElectricityNetOnline'] == False:
                                devElectricityNet.updateStateOnServer("smappeeElectricityNetOnline", True, uiValue='online')

                        if pluginGlobal['config']['supportsElectricitySaved'] == True:
                            devElectricitySaved = indigo.devices[pluginGlobal['smappeeServiceLocationIdToDevId'][responseLocationId]['electricitySavedId']]
                            self.lastReadingElectricitySavedUtc = pluginGlobal['smappees'][devElectricitySaved.id]['lastReadingElectricitySavedUtc']
                            autolog(DETAIL, u"handleSmappeeResponse [LRU-SAVED-ELECTRICITY]: %s" % (self.lastReadingElectricitySavedUtc))

                            if devElectricitySaved.states['smappeeElectricitySavedOnline'] == False:
                                devElectricitySaved.updateStateOnServer("smappeeElectricitySavedOnline", True, uiValue='online')

                        if pluginGlobal['config']['supportsSolar'] == True:
                            devSolar = indigo.devices[pluginGlobal['smappeeServiceLocationIdToDevId'][responseLocationId]['solarId']]
                            self.lastReadingSolarUtc = pluginGlobal['smappees'][devSolar.id]['lastReadingSolarUtc']
                            autolog(DETAIL, u"handleSmappeeResponse [LRU-SOLAR]: %s" % (self.lastReadingSolarUtc))

                            if devSolar.states['smappeeSolarOnline'] == False:
                                devSolar.updateStateOnServer("smappeeSolarOnline", True, uiValue='online')

                        if pluginGlobal['config']['supportsSolarUsed'] == True:
                            devSolarUsed = indigo.devices[pluginGlobal['smappeeServiceLocationIdToDevId'][responseLocationId]['solarUsedId']]
                            self.lastReadingSolarUsedUtc = pluginGlobal['smappees'][devSolarUsed.id]['lastReadingSolarUsedUtc']
                            autolog(DETAIL, u"handleSmappeeResponse [LRU-SOLAR-USED]: %s" % (self.lastReadingSolarUsedUtc))

                            if devSolarUsed.states['smappeeSolarUsedOnline'] == False:
                                devSolarUsed.updateStateOnServer("smappeeSolarUsedOnline", True, uiValue='online')

                        if pluginGlobal['config']['supportsSolarExported'] == True:
                            devSolarExported = indigo.devices[pluginGlobal['smappeeServiceLocationIdToDevId'][responseLocationId]['solarExportedId']]
                            self.lastReadingSolarExportedUtc = pluginGlobal['smappees'][devSolarExported.id]['lastReadingSolarExportedUtc']
                            autolog(DETAIL, u"handleSmappeeResponse [LRU-SOLAR-EXPORTED]: %s" % (self.lastReadingSolarExportedUtc))

                            if devSolarExported.states['smappeeSolarExportedOnline'] == False:
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

                        if pluginGlobal['SQL']['enabled'] == True:
                            try:
                                pluginGlobal['SQL']['connection'] = sql3.connect(pluginGlobal['SQL']['db'])
                                pluginGlobal['SQL']['cursor'] = pluginGlobal['SQL']['connection'].cursor()
                            except sql3.Error, e:
                                if pluginGlobal['SQL']['connection']:
                                    pluginGlobal['SQL']['connection'].rollback()
                                autolog(ERROR, u"SMAPPEE ERROR DETECTED WITH SQL CONNECTION: %s" % (e.args[0]))

                                pluginGlobal['SQL']['enabled'] = False  # Disable SQL processing

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

                                if self.timestampDetected == True:
                                    ts = datetime.datetime.fromtimestamp(int(int(self.timestampUtc)/1000)).strftime('%Y-%m-%d %H:%M:%S')
                                    autolog(DETAIL, u"ELECTRICITY/SOLAR: DateTime=%s, Electricity=%s, Net=%s, Saved=%s, Solar=%s, Solar Used=%s, Solar Exported=%s" % (ts, self.electricity, self.electricityNet, self.electricitySaved, self.solar, self.solarUsed, self.solarExported))    
                                else:
                                    autolog(DETAIL, u"ELECTRICITY/SOLAR: DateTime=NOT DETECTED, Electricity=%s, Net=%s, Saved=%s, Solar=%s, Solar Used=%s, Solar Exported=%s" % (self.electricity, self.electricityNet, self.electricitySaved, self.solar, self.solarUsed, self.solarExported))    

                            if self.timestampDetected == True:
                                if pluginGlobal['config']['supportsElectricity'] == True:
                                    if self.timestampUtc > self.lastReadingElectricityUtc:
                                        if self.electricityDetected == True:
                                            self.electricityNumberOfValues += 1
                                            self.electricityTotal += self.electricity
                                            if self.electricity < self.electricityMinimum:
                                                self.electricityMinimum = self.electricity
                                            if self.electricity > self.electricityMaximum:
                                                self.electricityMaximum = self.electricity
                                            self.electricityLast = self.electricity
                                    elif self.timestampUtc ==  self.lastReadingElectricityUtc:
                                        self.electricityPrevious = 0.0
                                        if self.electricityDetected == True:
                                            self.electricityPrevious = self.electricity * 12

                                if pluginGlobal['config']['supportsElectricity'] == True and pluginGlobal['config']['supportsElectricityNet'] == True and pluginGlobal['config']['supportsSolar'] == True:
                                    # Net makes no sense if electricity and solar not measured
                                    if self.timestampUtc > self.lastReadingElectricityNetUtc:
                                        if self.electricityNetDetected == True:
                                            self.electricityNetNumberOfValues += 1
                                            self.electricityNetTotal += self.electricityNet
                                            if self.electricityNet < self.electricityNetMinimum:
                                                self.electricityNetMinimum = self.electricityNet
                                            if self.electricityNet > self.electricityNetMaximum:
                                                self.electricityNetMaximum = self.electricityNet
                                            self.electricityNetLast = self.electricityNet
                                    elif self.timestampUtc ==  self.lastReadingElectricityNetUtc:
                                        self.electricityNetPrevious = 0.0
                                        if self.electricityNetDetected == True:
                                            self.electricityNetPrevious = self.electricityNet * 12

                                    autolog(DETAIL, u"handleSmappeeResponse [FF][ELECTRICITY NET] - LRUTC[%s]=[%s], TSUTC[%s]=[%s], Net[%s]=[%s]" % (type(self.lastReadingElectricityNetUtc), self.lastReadingElectricityNetUtc, type(self.timestampUtc), self.timestampUtc, type(self.electricityNet), self.electricityNet))

                                if pluginGlobal['config']['supportsElectricity'] == True and pluginGlobal['config']['supportsElectricitySaved'] == True and pluginGlobal['config']['supportsSolar'] == True:
                                    # Saved makes no sense if electricity and solar not measured
                                    if self.timestampUtc > self.lastReadingElectricitySavedUtc:
                                        if self.electricitySavedDetected == True:
                                            self.electricitySavedNumberOfValues += 1
                                            self.electricitySavedTotal += self.electricitySaved
                                            if self.electricitySaved < self.electricitySavedMinimum:
                                                self.electricitySavedMinimum = self.electricitySaved
                                            if self.electricitySaved > self.electricitySavedMaximum:
                                                self.electricitySavedMaximum = self.electricitySaved
                                            self.electricitySavedLast = self.electricitySaved
                                    elif self.timestampUtc ==  self.lastReadingElectricitySavedUtc:
                                        self.electricitySavedPrevious = 0.0
                                        if self.electricitySavedDetected == True:
                                            self.electricitySavedPrevious = self.electricitySaved * 12

                                    autolog(DETAIL, u"handleSmappeeResponse [FF][ELECTRICITY SAVED] - LRUTC[%s]=[%s], TSUTC[%s]=[%s], Saved[%s]=[%s]" % (type(self.lastReadingElectricitySavedUtc), self.lastReadingElectricitySavedUtc, type(self.timestampUtc), self.timestampUtc, type(self.electricitySaved), self.electricitySaved))

                                if pluginGlobal['config']['supportsSolar'] == True:
                                    if self.timestampUtc > self.lastReadingSolarUtc:
                                        if self.solarDetected == True:
                                            self.solarNumberOfValues += 1
                                            self.solarTotal += self.solar
                                            if self.solar < self.solarMinimum:
                                                self.solarMinimum = self.solar
                                            if self.solar > self.solarMaximum:
                                                self.solarMaximum = self.solar
                                            self.solarLast = self.solar
                                    elif self.timestampUtc ==  self.lastReadingSolarUtc:
                                        self.solarPrevious = 0.0
                                        if self.solarDetected == True:
                                            self.solarPrevious = self.solar * 12
                                    # autolog(DETAIL, u"handleSmappeeResponse [FF][SOLAR] - LRUTC[%s]=[%s], TSUTC[%s]=[%s], S[%s]=[%s]" % (type(self.lastReadingSolarUtc), self.lastReadingSolarUtc, type(self.timestampUtc), self.timestampUtc, type(self.solar), self.solar))

                                if pluginGlobal['config']['supportsElectricity'] == True and pluginGlobal['config']['supportsSolarUsed'] == True:
                                    # Used (Solar) makes no sense if electricity and solar not measured
                                    if self.timestampUtc > self.lastReadingSolarUsedUtc:
                                        if self.solarUsedDetected == True:
                                            self.solarUsedNumberOfValues += 1
                                            self.solarUsedTotal += self.solarUsed
                                            self.solarUsedLast = self.solarUsed
                                    elif self.timestampUtc ==  self.lastReadingSolarUsedUtc:
                                        self.solarUsedPrevious = 0.0
                                        if self.solarUsedDetected == True:
                                            self.solarUsedPrevious = self.solarUsed * 12

                                    autolog(DETAIL, u"handleSmappeeResponse [FF][SOLAR USED] - LRUTC[%s]=[%s], TSUTC[%s]=[%s], Saving[%s]=[%s]" % (type(self.lastReadingSolarUsedUtc), self.lastReadingSolarUsedUtc, type(self.timestampUtc), self.timestampUtc, type(self.solarUsed), self.solarUsed))

                                if pluginGlobal['config']['supportsSolarExported'] == True:
                                    if self.timestampUtc > self.lastReadingSolarExportedUtc:
                                        if self.solarExportedDetected == True:
                                            self.solarExportedNumberOfValues += 1
                                            self.solarExportedTotal += self.solarExported
                                            self.solarExportedLast = self.solarExported
                                    elif self.timestampUtc ==  self.lastReadingSolarExportedUtc:
                                        self.solarExportedPrevious = 0.0
                                        if self.solarExportedDetected == True:
                                            self.solarExportedPrevious = self.solarExported * 12

                                    autolog(DETAIL, u"handleSmappeeResponse [FF][SOLAR EXPORTED] - LRUTC[%s]=[%s], TSUTC[%s]=[%s], Saving[%s]=[%s]" % (type(self.lastReadingSolarExportedUtc), self.lastReadingSolarExportedUtc, type(self.timestampUtc), self.timestampUtc, type(self.solarExported), self.solarExported))

                                if pluginGlobal['SQL']['enabled'] == True:

                                    try:
                                        insertSql = 'NO SQL SET-UP YET'
                                        readingTime = str(int(self.timestampUtc / 1000))  # Remove micro seconds
                                        readingYYYYMMDDHHMMSS = datetime.datetime.fromtimestamp(int(readingTime)).strftime('%Y-%m-%d %H:%M:%S')
                                        readingYYYYMMDD = readingYYYYMMDDHHMMSS[0:10]
                                        readingHHMMSS = readingYYYYMMDDHHMMSS[-8:]
                                        elec          = str(int(self.electricity * 10))
                                        elecNet       = str(int(self.electricityNet * 10))
                                        elecSaved     = str(int(self.electricitySaved * 10))
                                        alwaysOn      = str(int(self.alwaysOn * 10))
                                        solar         = str(int(self.solar * 10))
                                        solarUsed     = str(int(self.solarUsed * 10))
                                        solarExported = str(int(self.solarExported * 10))
                                        insertSql = """
                                            INSERT OR IGNORE INTO readings (reading_time, reading_YYYYMMDD, reading_HHMMSS, elec, elec_net, elec_saved, always_on, solar, solar_used, solar_exported)
                                            VALUES (%s, '%s', '%s', %s, %s, %s, %s, %s, %s, %s);
                                            """ % (readingTime, readingYYYYMMDD, readingHHMMSS, elec, elecNet, elecSaved, alwaysOn, solar, solarUsed, solarExported)
                                        pluginGlobal['SQL']['cursor'].executescript(insertSql)
                                    except sql3.Error, e:
                                        if pluginGlobal['SQL']['connection']:
                                            pluginGlobal['SQL']['connection'].rollback()
                                        autolog(ERROR, u"SMAPPEE ERROR DETECTED WITH SQL INSERT: %s, SQL=[%s]" % (e.args[0], insertSql))
                                        if pluginGlobal['SQL']['connection']:
                                            pluginGlobal['SQL']['connection'].close()  

                                        pluginGlobal['SQL']['enabled'] = False  # Disable SQL processing


                        if pluginGlobal['SQL']['enabled'] == True:
                            try:
                                pluginGlobal['SQL']['connection'].commit()
                            except sql3.Error, e:
                                if pluginGlobal['SQL']['connection']:
                                    pluginGlobal['SQL']['connection'].rollback()
                                autolog(ERROR, u"SMAPPEE ERROR DETECTED WITH SQL COMMIT: %s" % (e.args[0]))

                                pluginGlobal['SQL']['enabled'] = False  # Disable SQL processing
                            finally:
                                if pluginGlobal['SQL']['connection']:
                                    pluginGlobal['SQL']['connection'].close()  


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

                        autolog(DETAIL, u"READINGS - ELECTRICITY: N=[%s], T=[%s], MEAN=[%s], MIN=[%s], MAX=[%s], L=[%s]" \
                            % (self.electricityNumberOfValues, self.electricityTotal, self.electricityMeanAverage, self.electricityMinimum, self.electricityMaximum, self.electricityLast))
                        autolog(DETAIL, u"READINGS - ELECTRICITY NET: N=[%s], T=[%s], MEAN=[%s], MIN=[%s], MAX=[%s], L=[%s]" \
                            % (self.electricityNetNumberOfValues, self.electricityNetTotal, self.electricityNetMeanAverage, self.electricityNetMinimum, self.electricityNetMaximum, self.electricityNetLast))
                        autolog(DETAIL, u"READINGS - ELECTRICITY SAVED: N=[%s], T=[%s], MEAN=[%s], MIN=[%s], MAX=[%s], L=[%s]" \
                            % (self.electricitySavedNumberOfValues, self.electricitySavedTotal, self.electricitySavedMeanAverage, self.electricitySavedMinimum, self.electricitySavedMaximum, self.electricitySavedLast))
                        autolog(DETAIL, u"READINGS - SOLAR: N=[%s], T=[%s], MEAN=[%s], MIN=[%s], MAX=[%s], L=[%s]" \
                            % (self.solarNumberOfValues, self.solarTotal, self.solarMeanAverage, self.solarMinimum, self.solarMaximum, self.solarLast))
                        autolog(DETAIL, u"READINGS - SOLAR USED: N=[%s], T=[%s], MEAN=[%s], MIN=[%s], MAX=[%s], L=[%s]" \
                            % (self.solarUsedNumberOfValues, self.solarUsedTotal, self.solarUsedMeanAverage, self.solarUsedMinimum, self.solarUsedMaximum, self.solarUsedLast))
                        autolog(DETAIL, u"READINGS - SOLAR EXPORTED: N=[%s], T=[%s], MEAN=[%s], MIN=[%s], MAX=[%s], L=[%s]" \
                            % (self.solarExportedNumberOfValues, self.solarExportedTotal, self.solarExportedMeanAverage, self.solarExportedMinimum, self.solarExportedMaximum, self.solarExportedLast))

                        savedElectricityCalculated = False  # Used to determine whether Solar PV FIT + Elec savings can be calculated
                                                            #   Gets set to True if Elec saving calculated so that it can be added to Solar Total Income
                                                            #   to dereive and upadte state: dailyTotalPlusSavedElecIncome

                        if pluginGlobal['config']['supportsElectricity'] == True:

                            if "curEnergyLevel" in devElectricity.states:
                                if commandSentToSmappee == 'RESET_CONSUMPTION':

                                    pluginGlobal['smappees'][devElectricity.id]['curEnergyLevel'] = 0.0
                                    pluginGlobal['smappees'][devElectricity.id]['accumEnergyTotal'] = 0.0
                                    wattStr = "%3.0f Watts" % (pluginGlobal['smappees'][devElectricity.id]['curEnergyLevel'])
                                    devElectricity.updateStateOnServer("curEnergyLevel", pluginGlobal['smappees'][devElectricity.id]['curEnergyLevel'], uiValue=wattStr)
                                    if float(indigo.server.apiVersion) >= 1.18:
                                        devElectricity.updateStateImageOnServer(indigo.kStateImageSel.EnergyMeterOff)

                                self.options = devElectricity.pluginProps['optionsEnergyMeterCurPower']  # mean, minimum, maximum, last

                                if self.options == 'mean':  # mean, minimum, maximum, last
                                    if self.electricityNumberOfValues > 0:
                                        watts = (self.electricityMeanAverage * 60) / 5
                                    else:
                                        autolog(DETAIL, u"ELECTRICITY: CL=[%s], UTCL=[%s], LRUTC=[%s], LRUTC600=[%s]" % (self.electricityLast, self.timestampUtcLast, self.lastReadingElectricityUtc, (self.lastReadingElectricityUtc - 600000)))
                                        if self.electricityLast > 0.0 and self.timestampUtcLast != 0 and self.timestampUtcLast > (self.lastReadingElectricityUtc - 600000):
                                            watts = self.electricityLast * 12
                                        else:
                                            watts = 0.0
                                elif self.options == 'minimum':
                                    if self.electricityNumberOfValues > 0:
                                        watts = self.electricityMinimum * 12
                                    else:
                                        autolog(DETAIL, u"ELECTRICITY: CL=[%s], UTCL=[%s], LRUTC=[%s], LRUTC600=[%s]" % (self.electricityLast, self.timestampUtcLast, self.lastReadingElectricityUtc, (self.lastReadingElectricityUtc - 600000)))
                                        if self.electricityLast > 0.0 and self.timestampUtcLast != 0 and self.timestampUtcLast > (self.lastReadingElectricityUtc - 600000):
                                            watts = self.electricityLast * 12
                                        else:
                                            watts = 0.0
                                elif self.options == 'maximum':
                                    if self.electricityNumberOfValues > 0:
                                        watts = self.electricityMaximum * 12
                                    else:
                                        autolog(DETAIL, u"ELECTRICITY: CL=[%s], UTCL=[%s], LRUTC=[%s], LRUTC600=[%s]" % (self.electricityLast, self.timestampUtcLast, self.lastReadingElectricityUtc, (self.lastReadingElectricityUtc - 600000)))
                                        if self.electricityLast > 0.0 and self.timestampUtcLast != 0 and self.timestampUtcLast > (self.lastReadingElectricityUtc - 600000):
                                            watts = self.electricityLast * 12
                                        else:
                                            watts = 0.0
                                else:  # Assume last
                                    autolog(DETAIL, u"ELECTRICITY: CL=[%s], UTCL=[%s], LRUTC=[%s], LRUTC600=[%s]" % (self.electricityLast, self.timestampUtcLast, self.lastReadingElectricityUtc, (self.lastReadingElectricityUtc - 600000)))
                                    if self.electricityLast > 0.0 and self.timestampUtcLast != 0 and self.timestampUtcLast > (self.lastReadingElectricityUtc - 600000):
                                        watts = self.electricityLast * 12
                                    else:
                                        watts = 0.0

                                if watts == 0.0:
                                    watts = self.electricityPrevious     

                                wattsStr = "%d Watts" % (watts)
                                if not pluginGlobal['smappees'][devElectricity.id]['hideEnergyMeterCurPower']:
                                    autolog(INFO, u"received '%s' power load reading: %s" % (devElectricity.name, wattsStr))

                                devElectricity.updateStateOnServer("curEnergyLevel", watts, uiValue=wattsStr)
                                if float(indigo.server.apiVersion) >= 1.18:
                                    devElectricity.updateStateImageOnServer(indigo.kStateImageSel.EnergyMeterOn)

                            if "accumEnergyTotal" in devElectricity.states:

                                if commandSentToSmappee == 'RESET_CONSUMPTION':
                                    pluginGlobal['smappees'][devElectricity.id]['accumEnergyTotal'] = 0.0
                                    wattStr = "%3.0f Watts" % (pluginGlobal['smappees'][devElectricity.id]['accumEnergyTotal'])
                                    devElectricity.updateStateOnServer("accumEnergyTotal", pluginGlobal['smappees'][devElectricity.id]['accumEnergyTotal'], uiValue=wattStr)

                                kwh = float(devElectricity.states.get("accumEnergyTotal", 0))
                                kwh += float(self.electricityTotal / 1000.0)
                                kwhStr = "%0.3f kWh" % (kwh)
                                kwhUnitCost = pluginGlobal['smappees'][devElectricity.id]['kwhUnitCost']
                                dailyStandingCharge = pluginGlobal['smappees'][devElectricity.id]['dailyStandingCharge']

                                amountGross = 0.00
                                if kwhUnitCost > 0.00:
                                    amountGross = (dailyStandingCharge + (kwh * kwhUnitCost))
                                    amountGrossReformatted = float(str("%0.2f" % (amountGross)))
                                    amountGrossStr = str("%0.2f %s" % (amountGross, pluginGlobal['smappees'][devElectricity.id]['currencyCode']))
                                    devElectricity.updateStateOnServer("dailyTotalCost", amountGrossReformatted, uiValue=amountGrossStr)

                                if not pluginGlobal['smappees'][devElectricity.id]['hideEnergyMeterAccumPower']:
                                    if kwhUnitCost == 0.00 or pluginGlobal['smappees'][devElectricity.id]['hideEnergyMeterAccumPowerCost'] == True:
                                        autolog(INFO, u"received '%s' energy total: %s" % (devElectricity.name, kwhStr))
                                    else:
                                        autolog(INFO, u"received '%s' energy total: %s (Gross %s)" % (devElectricity.name, kwhStr, amountGrossStr))

                                kwhReformatted = float(str("%0.3f" % (kwh)))
                                devElectricity.updateStateOnServer("accumEnergyTotal", kwhReformatted, uiValue=kwhStr)

                            if "alwaysOn" in devElectricity.states:
                                wattsAlwaysOn = self.alwaysOn
                                wattsAlwaysOnStr = "%d Watts" % (wattsAlwaysOn)
                                if not pluginGlobal['smappees'][devElectricity.id]['hideAlwaysOnPower']:
                                    autolog(INFO, u"received '%s' always-on reading: %s" % (devElectricity.name, wattsAlwaysOnStr))
                                devElectricity.updateStateOnServer("alwaysOn", watts, uiValue=wattsAlwaysOnStr)

                            pluginGlobal['smappees'][devElectricity.id]['lastReadingElectricityUtc'] = self.timestampUtc

                        if pluginGlobal['config']['supportsElectricityNet'] == True:

                            if "curEnergyLevel" in devElectricityNet.states:
                                if commandSentToSmappee == 'RESET_CONSUMPTION':

                                    pluginGlobal['smappees'][devElectricityNet.id]['curEnergyLevel'] = 0.0
                                    pluginGlobal['smappees'][devElectricityNet.id]['accumEnergyTotal'] = 0.0
                                    wattStr = "%3.0f Watts" % (pluginGlobal['smappees'][devElectricityNet.id]['curEnergyLevel'])
                                    devElectricityNet.updateStateOnServer("curEnergyLevel", pluginGlobal['smappees'][devElectricityNet.id]['curEnergyLevel'], uiValue=wattStr)
                                    if float(indigo.server.apiVersion) >= 1.18:
                                        devElectricityNet.updateStateImageOnServer(indigo.kStateImageSel.EnergyMeterOff)

                                self.options = devElectricityNet.pluginProps['optionsEnergyMeterCurPower']

                                if self.options == 'mean':  # mean, minimum, maximum, last
                                    if self.electricityNetNumberOfValues > 0:
                                        wattsNet = (self.electricityNetMeanAverage * 60) / 5
                                    else:
                                        autolog(DETAIL, u"ELECTRICITY NET: CL=[%s], UTCL=[%s], LRUTC=[%s], LRUTC600=[%s]" % (self.electricityNetLast, self.timestampUtcLast, self.lastReadingElectricityNetUtc, (self.lastReadingElectricityNetUtc - 600000)))
                                        if self.electricityNetLast > 0.0 and self.timestampUtcLast != 0 and self.timestampUtcLast > (self.lastReadingElectricityNetUtc - 600000):
                                            wattsNet = self.electricityNetLast * 12
                                        else:
                                            wattsNet = 0.0
                                elif self.options == 'minimum':
                                    if self.electricityNetNumberOfValues > 0:
                                        wattsNet = self.electricityNetMinimum * 12
                                    else:
                                        autolog(DETAIL, u"ELECTRICITY NET: CL=[%s], UTCL=[%s], LRUTC=[%s], LRUTC600=[%s]" % (self.electricityNetLast, self.timestampUtcLast, self.lastReadingElectricityNetUtc, (self.lastReadingElectricityNetUtc - 600000)))
                                        if self.electricityNetLast > 0.0 and self.timestampUtcLast != 0 and self.timestampUtcLast > (self.lastReadingElectricityNetUtc - 600000):
                                            wattsNet = self.electricityNetLast * 12
                                        else:
                                            wattsNet = 0.0
                                elif self.options == 'maximum':
                                    if self.electricityNetNumberOfValues > 0:
                                        wattsNet = self.electricityNetMaximum * 12
                                    else:
                                        autolog(DETAIL, u"ELECTRICITY NET: CL=[%s], UTCL=[%s], LRUTC=[%s], LRUTC600=[%s]" % (self.electricityNetLast, self.timestampUtcLast, self.lastReadingElectricityNetUtc, (self.lastReadingElectricityNetUtc - 600000)))
                                        if self.electricityNetLast > 0.0 and self.timestampUtcLast != 0 and self.timestampUtcLast > (self.lastReadingElectricityNetUtc - 600000):
                                            wattsNet = self.electricityNetLast * 12
                                        else:
                                            wattsNet = 0.0
                                else:  # Assume last
                                    autolog(DETAIL, u"ELECTRICITY NET: CL=[%s], UTCL=[%s], LRUTC=[%s], LRUTC600=[%s]" % (self.electricityNetLast, self.timestampUtcLast, self.lastReadingElectricityNetUtc, (self.lastReadingElectricityNetUtc - 600000)))
                                    if self.electricityNetLast > 0.0 and self.timestampUtcLast != 0 and self.timestampUtcLast > (self.lastReadingElectricityNetUtc - 600000):
                                        wattsNet = self.electricityNetLast * 12
                                    else:
                                        wattsNet = 0.0

                                if wattsNet == 0.0:
                                    wattsNet = self.electricityNetPrevious

                                wattsNetStr = "%d Watts" % (wattsNet)
                                if not pluginGlobal['smappees'][devElectricityNet.id]['hideEnergyMeterCurNetPower']:
                                    if wattsNet == 0.0 and pluginGlobal['smappees'][devElectricityNet.id]['hideEnergyMeterCurZeroNetPower']:
                                        pass
                                    else:
                                        autolog(INFO, u"received '%s' electricity net reading: %s" % (devElectricityNet.name, wattsNetStr))
                                devElectricityNet.updateStateOnServer("curEnergyLevel", wattsNet, uiValue=wattsNetStr)
                                if float(indigo.server.apiVersion) >= 1.18:
                                    devElectricityNet.updateStateImageOnServer(indigo.kStateImageSel.EnergyMeterOn)

                                if watts > 0.00:
                                    netPercentage = int(round((wattsNet / watts) * 100))
                                else:
                                    netPercentage = int(0)
                                netPercentageStr = "%d%%" % netPercentage
                                devElectricityNet.updateStateOnServer("kwhCurrentNetPercentage", netPercentage, uiValue=netPercentageStr)

                            if "accumEnergyTotal" in devElectricityNet.states:
                                if commandSentToSmappee == 'RESET_CONSUMPTION':
                                    pluginGlobal['smappees'][devElectricityNet.id]['accumEnergyTotal'] = 0.0
                                    wattNetStr = "%3.0f Watts" % (pluginGlobal['smappees'][devElectricityNet.id]['accumEnergyTotal'])
                                    devElectricityNet.updateStateOnServer("accumEnergyTotal", pluginGlobal['smappees'][devElectricityNet.id]['accumEnergyTotal'], uiValue=wattNetStr)

                                if "accumEnergyTotal" in devElectricity.states:
                                    # Need to check this as the kwh, gross amount, unit cost and currency code is retrieved from the Electricity Device
 
                                    kwhNet = float(devElectricityNet.states.get("accumEnergyTotal", 0))
                                    kwhNet += float(self.electricityNetTotal / 1000.0)
                                    kwhNetStr = str("%0.3f kWh" % (kwhNet))
                                    kwhUnitCost = pluginGlobal['smappees'][devElectricity.id]['kwhUnitCost']
                                    dailyStandingCharge = pluginGlobal['smappees'][devElectricity.id]['dailyStandingCharge']

                                    kwhNetReformatted = float("%0.3f" % (kwhNet))
                                    devElectricityNet.updateStateOnServer("accumEnergyTotal", kwhNetReformatted, uiValue=kwhNetStr)

                                    amountNet = 0.00
                                    if kwhUnitCost > 0.00:
                                        amountNet = dailyStandingCharge + (kwhNet * kwhUnitCost)
                                        amountNetReformatted = float(str("%0.2f" % (amountNet)))
                                        amountNetStr = str("%0.2f %s" % (amountNet, pluginGlobal['smappees'][devElectricity.id]['currencyCode']))
                                        devElectricityNet.updateStateOnServer("dailyNetTotalCost", amountNetReformatted, uiValue=amountNetStr)

                                    if not pluginGlobal['smappees'][devElectricityNet.id]['hideEnergyMeterAccumNetPower']:
                                        if kwhUnitCost == 0.00 or pluginGlobal['smappees'][devElectricityNet.id]['hideEnergyMeterAccumNetPowerCost'] == True:
                                            autolog(INFO, u"received '%s' net energy total: %s" % (devElectricityNet.name, kwhNetStr))
                                        else:
                                            autolog(INFO, u"received '%s' net energy total: %s (Gross %s)" % (devElectricityNet.name, kwhNetStr, amountNetStr))

                                    if kwhNet > 0.00:
                                        netDailyPercentage = int(round((kwhNet / kwh) * 100))
                                    else:
                                        netDailyPercentage = int(0)
                                    netDailyPercentageStr = "%d%%" % netDailyPercentage
                                    devElectricityNet.updateStateOnServer("kwhDailyTotalNetPercentage", netDailyPercentage, uiValue=netDailyPercentageStr)

                            pluginGlobal['smappees'][devElectricityNet.id]['lastReadingElectricityNetUtc'] = self.timestampUtc

                        if pluginGlobal['config']['supportsElectricitySaved'] == True:

                            if "curEnergyLevel" in devElectricitySaved.states:
                                if commandSentToSmappee == 'RESET_CONSUMPTION':

                                    pluginGlobal['smappees'][devElectricitySaved.id]['curEnergyLevel'] = 0.0
                                    pluginGlobal['smappees'][devElectricitySaved.id]['accumEnergyTotal'] = 0.0
                                    wattStr = "%3.0f Watts" % (pluginGlobal['smappees'][devElectricitySaved.id]['curEnergyLevel'])
                                    devElectricitySaved.updateStateOnServer("curEnergyLevel", pluginGlobal['smappees'][devElectricitySaved.id]['curEnergyLevel'], uiValue=wattStr)
                                    if float(indigo.server.apiVersion) >= 1.18:
                                        devElectricitySaved.updateStateImageOnServer(indigo.kStateImageSel.EnergyMeterOff)

                                self.options = devElectricitySaved.pluginProps['optionsEnergyMeterCurPower']

                                if self.options == 'mean':  # mean, minimum, maximum, last
                                    if self.electricitySavedNumberOfValues > 0:
                                        wattsSaved = (self.electricitySavedMeanAverage * 60) / 5
                                    else:
                                        autolog(DETAIL, u"ELECTRICITY SAVED: CL=[%s], UTCL=[%s], LRUTC=[%s], LRUTC600=[%s]" % (self.electricitySavedLast, self.timestampUtcLast, self.lastReadingElectricitySavedUtc, (self.lastReadingElectricitySavedUtc - 600000)))
                                        if self.electricitySavedLast > 0.0 and self.timestampUtcLast != 0 and self.timestampUtcLast > (self.lastReadingElectricitySavedUtc - 600000):
                                            wattsSaved = self.electricitySavedLast * 12
                                        else:
                                            wattsSaved = 0.0
                                elif self.options == 'minimum':
                                    if self.electricitySavedNumberOfValues > 0:
                                        wattsSaved = self.electricitySavedMinimum * 12
                                    else:
                                        autolog(DETAIL, u"ELECTRICITY SAVED: CL=[%s], UTCL=[%s], LRUTC=[%s], LRUTC600=[%s]" % (self.electricitySavedLast, self.timestampUtcLast, self.lastReadingElectricitySavedUtc, (self.lastReadingElectricitySavedUtc - 600000)))
                                        if self.electricitySavedLast > 0.0 and self.timestampUtcLast != 0 and self.timestampUtcLast > (self.lastReadingElectricitySavedUtc - 600000):
                                            wattsSaved = self.electricitySavedLast * 12
                                        else:
                                            wattsSaved = 0.0
                                elif self.options == 'maximum':
                                    if self.electricitySavedNumberOfValues > 0:
                                        wattsSaved = self.electricitySavedMaximum * 12
                                    else:
                                        autolog(DETAIL, u"ELECTRICITY SAVED: CL=[%s], UTCL=[%s], LRUTC=[%s], LRUTC600=[%s]" % (self.electricitySavedLast, self.timestampUtcLast, self.lastReadingElectricitySavedUtc, (self.lastReadingElectricitySavedUtc - 600000)))
                                        if self.electricitySavedLast > 0.0 and self.timestampUtcLast != 0 and self.timestampUtcLast > (self.lastReadingElectricitySavedUtc - 600000):
                                            wattsSaved = self.electricitySavedLast * 12
                                        else:
                                            wattsSaved = 0.0
                                else:  # Assume last
                                    autolog(DETAIL, u"ELECTRICITY SAVED: CL=[%s], UTCL=[%s], LRUTC=[%s], LRUTC600=[%s]" % (self.electricitySavedLast, self.timestampUtcLast, self.lastReadingElectricitySavedUtc, (self.lastReadingElectricitySavedUtc - 600000)))
                                    if self.electricitySavedLast > 0.0 and self.timestampUtcLast != 0 and self.timestampUtcLast > (self.lastReadingElectricitySavedUtc - 600000):
                                        wattsSaved = self.electricitySavedLast * 12
                                    else:
                                        wattsSaved = 0.0

                                if wattsSaved == 0.0:
                                    wattsSaved = self.electricitySavedPrevious

                                wattsSavedStr = "%d Watts" % (wattsSaved)
                                if not pluginGlobal['smappees'][devElectricitySaved.id]['hideEnergyMeterCurSavedPower']:
                                    if wattsSaved == 0.0 and pluginGlobal['smappees'][devElectricitySaved.id]['hideEnergyMeterCurZeroSavedPower']:
                                        pass
                                    else:
                                        autolog(INFO, u"received '%s' electricity saved reading: %s" % (devElectricitySaved.name, wattsSavedStr))
                                devElectricitySaved.updateStateOnServer("curEnergyLevel", wattsSaved, uiValue=wattsSavedStr)
                                if float(indigo.server.apiVersion) >= 1.18:
                                    devElectricitySaved.updateStateImageOnServer(indigo.kStateImageSel.EnergyMeterOn)

                                if watts > 0.00:
                                    savedPercentage = int(round((wattsSaved / watts) * 100))
                                else:
                                    savedPercentage = int(0)
                                savedPercentageStr = "%d%%" % savedPercentage
                                devElectricitySaved.updateStateOnServer("kwhCurrentSavedPercentage", savedPercentage, uiValue=savedPercentageStr)

                            if "accumEnergyTotal" in devElectricitySaved.states:
                                if commandSentToSmappee == 'RESET_CONSUMPTION':
                                    pluginGlobal['smappees'][devElectricitySaved.id]['accumEnergyTotal'] = 0.0
                                    wattSavedStr = "%3.0f Watts" % (pluginGlobal['smappees'][devElectricitySaved.id]['accumEnergyTotal'])
                                    devElectricitySaved.updateStateOnServer("accumEnergyTotal", pluginGlobal['smappees'][devElectricitySaved.id]['accumEnergyTotal'], uiValue=wattSavedStr)

                                if "accumEnergyTotal" in devElectricity.states:
                                    # Need to check this as the gross amount, unit cost and currency code is retrieved from the Electricity Device

                                    kwhSaved = float(devElectricitySaved.states.get("accumEnergyTotal", 0))
                                    kwhSaved += float(self.electricitySavedTotal / 1000.0)
                                    kwhSavedStr = str("%0.3f kWh" % (kwhSaved))
                                    kwhUnitCost = pluginGlobal['smappees'][devElectricity.id]['kwhUnitCost']

                                    amountSaved = 0.00
                                    if kwhUnitCost > 0.00:
                                        amountSaved = (kwhSaved * kwhUnitCost)
                                        amountSavedReformatted = float(str("%0.2f" % (amountSaved)))
                                        amountSavedStr = str("%0.2f %s" % (amountSaved, pluginGlobal['smappees'][devElectricity.id]['currencyCode']))
                                        devElectricitySaved.updateStateOnServer("dailyTotalCostSaving", amountSavedReformatted, uiValue=amountSavedStr)

                                        savedElectricityCalculated = True  # Enables calculation and storing of: dailyTotalPlusSavedElecIncome

                                    if not pluginGlobal['smappees'][devElectricitySaved.id]['hideEnergyMeterAccumSavedPower']:
                                        if kwhUnitCost == 0.00 or pluginGlobal['smappees'][devElectricitySaved.id]['hideEnergyMeterAccumSavedPowerCost'] == True:
                                            autolog(INFO, u"received '%s' saved energy total: %s" % (devElectricitySaved.name, kwhSavedStr))
                                        else:
                                            autolog(INFO, u"received '%s' saved energy total: %s (Saved %s)" % (devElectricitySaved.name, kwhSavedStr, amountSavedStr))

                                    kwhSavedReformatted = float("%0.3f" % (kwhSaved))
                                    devElectricitySaved.updateStateOnServer("accumEnergyTotal", kwhSavedReformatted, uiValue=kwhSavedStr)

                                    if kwhSaved > 0.00:
                                        savedDailyPercentage = int(round((kwhSaved / kwh) * 100))
                                    else:
                                        savedDailyPercentage = int(0)
                                    savedDailyPercentageStr = "%d %%" % savedDailyPercentage
                                    devElectricitySaved.updateStateOnServer("kwhDailyTotalSavedPercentage", savedDailyPercentage, uiValue=savedDailyPercentageStr)

                            pluginGlobal['smappees'][devElectricitySaved.id]['lastReadingElectricitySavedUtc'] = self.timestampUtc

                        if pluginGlobal['config']['supportsSolar'] == True:

                            if "curEnergyLevel" in devSolar.states:
                                if commandSentToSmappee == 'RESET_CONSUMPTION':

                                    pluginGlobal['smappees'][devSolar.id]['curEnergyLevel'] = 0.0
                                    pluginGlobal['smappees'][devSolar.id]['accumEnergyTotal'] = 0.0
                                    wattSolarStr = "%3.0f Watts" % (pluginGlobal['smappees'][devSolar.id]['curEnergyLevel'])
                                    devSolar.updateStateOnServer("curEnergyLevel", pluginGlobal['smappees'][devSolar.id]['curEnergyLevel'], uiValue=wattSolarStr)
                                    if float(indigo.server.apiVersion) >= 1.18:
                                        devSolar.updateStateImageOnServer(indigo.kStateImageSel.EnergyMeterOff)

                                self.optionsEnergyMeterCurPower = devSolar.pluginProps['optionsEnergyMeterCurPower']  # mean, minimum, maximum, last
                                if self.optionsEnergyMeterCurPower == 'mean':
                                    if self.solarNumberOfValues > 0:
                                        wattsSolar = self.solarTotal * (60.0 / float(float(self.solarNumberOfValues) * 5))
                                        autolog(DETAIL, u"watts > 0 =[%s]" % (watts))
                                    else:
                                        autolog(DETAIL, u"SOLAR: CL=[%s], UTCL=[%s], LRUTC=[%s], LRUTC600=[%s]" % (self.solarLast, self.timestampUtcLast, self.lastReadingSolarUtc, (self.lastReadingSolarUtc - 600000)))
                                        if self.solarLast > 0.0 and self.timestampUtcLast != 0 and self.timestampUtcLast > (self.lastReadingSolarUtc - 600000):
                                            wattsSolar = self.solarLast * 12
                                        else:
                                            wattsSolar = 0.0
                                elif self.optionsEnergyMeterCurPower == 'minimum':
                                    if self.solarNumberOfValues > 0:
                                        wattsSolar = self.solarMinimum * 12
                                    else:
                                        autolog(DETAIL, u"SOLAR: CL=[%s], UTCL=[%s], LRUTC=[%s], LRUTC600=[%s]" % (self.solarLast, self.timestampUtcLast, self.lastReadingSolarUtc, (self.lastReadingSolarUtc - 600000)))
                                        if self.solarLast > 0.0 and self.timestampUtcLast != 0 and self.timestampUtcLast > (self.lastReadingSolarUtc - 600000):
                                            wattsSolar = self.solarLast * 12
                                        else:
                                            wattsSolar = 0.0
                                elif self.optionsEnergyMeterCurPower == 'maximum':
                                    if self.solarNumberOfValues > 0:
                                        wattsSolar = self.solarMaximum * 12
                                    else:
                                        autolog(DETAIL, u"SOLAR: CL=[%s], UTCL=[%s], LRUTC=[%s], LRUTC600=[%s]" % (self.solarLast, self.timestampUtcLast, self.lastReadingSolarUtc, (self.lastReadingSolarUtc - 600000)))
                                        if self.solarLast > 0.0 and self.timestampUtcLast != 0 and self.timestampUtcLast > (self.lastReadingSolarUtc - 600000):
                                            wattsSolar = self.solarLast * 12
                                        else:
                                            wattsSolar = 0.0
                                else:  # Assume last
                                    autolog(DETAIL, u"SOLAR: CL=[%s], UTCL=[%s], LRUTC=[%s], LRUTC600=[%s]" % (self.solarLast, self.timestampUtcLast, self.lastReadingSolarUtc, (self.lastReadingSolarUtc - 600000)))
                                    if self.solarLast > 0.0 and self.timestampUtcLast != 0 and self.timestampUtcLast > (self.lastReadingSolarUtc - 600000):
                                        wattsSolar = self.solarLast * 12
                                    else:
                                        wattsSolar = 0.0

                                if wattsSolar == 0.0:
                                    wattsSolar = self.solarPrevious

                                wattsSolarStr = "%d Watts" % (wattsSolar)
                                if not pluginGlobal['smappees'][devSolar.id]['hideSolarMeterCurGeneration']:
                                    if wattsSolar == 0.0 and pluginGlobal['smappees'][devSolar.id]['hideZeroSolarMeterCurGeneration']:
                                        pass
                                    else:
                                        autolog(INFO, u"received '%s' solar generation reading: %s" % (devSolar.name, wattsSolarStr))
                                devSolar.updateStateOnServer("curEnergyLevel", wattsSolar, uiValue=wattsSolarStr)
                                if float(indigo.server.apiVersion) >= 1.18:
                                    devSolar.updateStateImageOnServer(indigo.kStateImageSel.EnergyMeterOn)

                            if "accumEnergyTotal" in devSolar.states:
                                if commandSentToSmappee == 'RESET_CONSUMPTION':
                                    pluginGlobal['smappees'][devSolar.id]['accumEnergyTotal'] = 0.0
                                    wattSolarStr = "%3.0f Watts" % (pluginGlobal['smappees'][devSolar.id]['accumEnergyTotal'])
                                    devSolar.updateStateOnServer("accumEnergyTotal", pluginGlobal['smappees'][devSolar.id]['accumEnergyTotal'], uiValue=wattSolarStr)

                                # To calculate Amounts (financials) all three device types solar, solaUsed and solarExported must be present

                                self.financialsEnabled = True

                                # Calculate Solar Total (Daily)

                                kwhSolar = float(devSolar.states.get("accumEnergyTotal", 0))
                                kwhSolar += float(self.solarTotal / 1000.0)
                                kwhSolarStr = str("%0.3f kWh" % (kwhSolar))

                                generationRate = pluginGlobal['smappees'][devSolar.id]['generationRate']
                                exportRate = pluginGlobal['smappees'][devSolar.id]['exportRate']

                                if pluginGlobal['config']['supportsSolarUsed'] == True and "accumEnergyTotal" in devSolarUsed.states:
                                    # Calculate Solar Used (Daily)
                                    kwhUsed = float(devSolarUsed.states.get("accumEnergyTotal", 0))
                                    kwhUsed += float(self.solarUsedTotal / 1000.0)

                                    if pluginGlobal['config']['supportsSolarExported'] == True and "accumEnergyTotal" in devSolarExported.states:
                                        # Calculate Solar Exported (Daily)
                                        kwhExported = float(devSolarExported.states.get("accumEnergyTotal", 0))
                                        kwhExported += float(self.solarExportedTotal / 1000.0)


                                        amountSolar = 0.00
                                        amountExported = 0.00  # Needed for calculation of total FIT payment
                                        amountGenerated = 0.00

                                        if generationRate > 0.00:
                                            amountGenerated = (kwhSolar * generationRate)
                                        if exportRate > 0.00:
                                            exportType = pluginGlobal['smappees'][devSolar.id]['exportType']
                                            if exportType == 'percentage':
                                                exportPercentage = pluginGlobal['smappees'][devSolar.id]['exportPercentage']
                                            elif exportType == 'actual':
                                                exportPercentage = (kwhExported / kwhSolar) * 100
                                            else:
                                                exportPercentage = 0.00
                                            amountExported = (kwhSolar * exportRate * exportPercentage) / 100

                                        amountSolar = amountGenerated + amountExported

                                        amountGeneratedReformatted = float(str("%0.2f" % (amountGenerated)))
                                        amountGeneratedStr = str("%0.2f %s" % (amountGenerated, pluginGlobal['smappees'][devSolar.id]['currencyCode']))
                                        devSolar.updateStateOnServer("dailyTotalGenOnlyIncome", amountGeneratedReformatted, uiValue=amountGeneratedStr)

                                        amountSolarReformatted = float(str("%0.2f" % (amountSolar)))
                                        amountSolarStr = str("%0.2f %s" % (amountSolarReformatted, pluginGlobal['smappees'][devSolar.id]['currencyCode']))
                                        devSolar.updateStateOnServer("dailyTotalIncome", amountSolarReformatted, uiValue=amountSolarStr)

                                        if savedElectricityCalculated == True:
                                            amountSolarPlusSaving = amountSolar + amountSaved
                                            amountSolarPlusSavingReformatted = float(str("%0.2f" % (amountSolarPlusSaving)))
                                            amountSolarPlusSavingStr = str("%0.2f %s" % (amountSolarPlusSaving, pluginGlobal['smappees'][devSolar.id]['currencyCode']))
                                            devSolar.updateStateOnServer("dailyTotalPlusSavedElecIncome", amountSolarPlusSavingReformatted, uiValue=amountSolarPlusSavingStr)

                                if not pluginGlobal['smappees'][devSolar.id]['hideSolarMeterAccumGeneration']:
                                    if pluginGlobal['smappees'][devSolar.id]['hideSolarMeterAccumGenerationCost']:
                                        if generationRate == 0.00 and pluginGlobal['smappees'][devSolar.id]['hideZeroSolarMeterCurGeneration']:
                                            pass  # Don't output zero solar values
                                        else:
                                            # if 'no change in solar' and pluginGlobal['smappees'][devSolar.id]['hideNoChangeInSolarMeterAccumGeneration']:
                                            #     pass
                                            # else:
                                            # do code below .... (remember to indent it!)
                                            autolog(INFO, u"received '%s' solar generation total: %s" % (devSolar.name, kwhSolarStr))
                                    else:
                                        if generationRate == 0.00 and pluginGlobal['smappees'][devSolar.id]['hideZeroSolarMeterCurGeneration']:
                                            pass  # Don't output zero solar values
                                        else:
                                            # if 'no change in solar' and pluginGlobal['smappees'][devSolar.id]['hideNoChangeInSolarMeterAccumGeneration']:
                                            #     pass
                                            # else:
                                            # do code below .... (remember to indent it!)
                                            autolog(INFO, u"received '%s' solar generation total: %s (%s)" % (devSolar.name, kwhSolarStr, amountSolarStr))
                                      

                                            # pluginGlobal['smappees'][devSolar.id]['hideNoChangeInSolarMeterAccumGeneration'] and kwhReformatted == float(devSolar.states['accumEnergyTotal']) and wattsSolar == 0.0:

                                kwhSolarReformatted = float("%0.3f" % (kwhSolar))
                                devSolar.updateStateOnServer("accumEnergyTotal", kwhSolarReformatted, uiValue=kwhSolarStr)

                            pluginGlobal['smappees'][devSolar.id]['lastReadingSolarUtc'] = self.timestampUtc

                        if pluginGlobal['config']['supportsSolarUsed'] == True:

                            if "curEnergyLevel" in devSolarUsed.states:
                                if commandSentToSmappee == 'RESET_CONSUMPTION':

                                    pluginGlobal['smappees'][devSolarUsed.id]['curEnergyLevel'] = 0.0
                                    pluginGlobal['smappees'][devSolarUsed.id]['accumEnergyTotal'] = 0.0
                                    wattsUsedStr = "%3.0f Watts" % (pluginGlobal['smappees'][devSolarUsed.id]['curEnergyLevel'])
                                    devSolarUsed.updateStateOnServer("curEnergyLevel", pluginGlobal['smappees'][devSolarUsed.id]['curEnergyLevel'], uiValue=wattsUsedStr)
                                    if float(indigo.server.apiVersion) >= 1.18:
                                        devSolarUsed.updateStateImageOnServer(indigo.kStateImageSel.EnergyMeterOff)

                                self.options = devSolarUsed.pluginProps['optionsEnergyMeterCurPower']

                                if self.options == 'mean':  # mean, minimum, maximum, last
                                    if self.solarUsedNumberOfValues > 0:
                                        wattsUsed = (self.solarUsedMeanAverage * 60) / 5
                                    else:
                                        autolog(DETAIL, u"ELECTRICITY NET: CL=[%s], UTCL=[%s], LRUTC=[%s], LRUTC600=[%s]" % (self.solarUsedLast, self.timestampUtcLast, self.lastReadingElectricityNetUtc, (self.lastReadingElectricityNetUtc - 600000)))
                                        if self.solarUsedLast > 0.0 and self.timestampUtcLast != 0 and self.timestampUtcLast > (self.lastReadingElectricityNetUtc - 600000):
                                            wattsUsed = self.solarUsedLast * 12
                                        else:
                                            wattsUsed = 0.0
                                elif self.options == 'minimum':
                                    if self.solarUsedNumberOfValues > 0:
                                        wattsUsed = self.solarUsedMinimum * 12
                                    else:
                                        autolog(DETAIL, u"ELECTRICITY NET: CL=[%s], UTCL=[%s], LRUTC=[%s], LRUTC600=[%s]" % (self.solarUsedLast, self.timestampUtcLast, self.lastReadingElectricityNetUtc, (self.lastReadingElectricityNetUtc - 600000)))
                                        if self.solarUsedLast > 0.0 and self.timestampUtcLast != 0 and self.timestampUtcLast > (self.lastReadingElectricityNetUtc - 600000):
                                            wattsUsed = self.solarUsedLast * 12
                                        else:
                                            wattsUsed = 0.0
                                elif self.options == 'maximum':
                                    if self.solarUsedNumberOfValues > 0:
                                        wattsUsed = self.solarUsedMaximum * 12
                                    else:
                                        autolog(DETAIL, u"ELECTRICITY NET: CL=[%s], UTCL=[%s], LRUTC=[%s], LRUTC600=[%s]" % (self.solarUsedLast, self.timestampUtcLast, self.lastReadingElectricityNetUtc, (self.lastReadingElectricityNetUtc - 600000)))
                                        if self.solarUsedLast > 0.0 and self.timestampUtcLast != 0 and self.timestampUtcLast > (self.lastReadingElectricityNetUtc - 600000):
                                            wattsUsed = self.solarUsedLast * 12
                                        else:
                                            wattsUsed = 0.0
                                else:  # Assume last
                                    autolog(DETAIL, u"SOLAR USED: CL=[%s], UTCL=[%s], LRUTC=[%s], LRUTC600=[%s]" % (self.solarUsedLast, self.timestampUtcLast, self.lastReadingSolarUsedUtc, (self.lastReadingSolarUsedUtc - 600000)))
                                    if self.solarUsedLast > 0.0 and self.timestampUtcLast != 0 and self.timestampUtcLast > (self.lastReadingSolarUsedUtc - 600000):
                                        wattsUsed = self.solarUsedLast * 12
                                    else:
                                        wattsUsed = 0.0

                                if wattsUsed == 0.0:
                                    wattsUsed = self.solarUsedPrevious

                                wattsUsedStr = "%d Watts" % (wattsUsed)
                                if not pluginGlobal['smappees'][devSolarUsed.id]['hideSolarUsedMeterCurGeneration']:
                                    if wattsUsed == 0.0 and pluginGlobal['smappees'][devSolarUsed.id]['hideZeroSolarUsedMeterCurGeneration']:
                                        pass
                                    else:
                                        autolog(INFO, u"received '%s' solar power used reading: %s" % (devSolarUsed.name, wattsUsedStr))
                                devSolarUsed.updateStateOnServer("curEnergyLevel", wattsUsed, uiValue=wattsUsedStr)
                                if float(indigo.server.apiVersion) >= 1.18:
                                    devSolarUsed.updateStateImageOnServer(indigo.kStateImageSel.EnergyMeterOn)

                                if self.solar > 0.00:
                                    usedPercentage = int(round((self.solarUsed / self.solar) * 100))
                                else:
                                    usedPercentage = int(0)
                                usedPercentageStr = "%d %%" % usedPercentage
                                devSolarUsed.updateStateOnServer("kwhCurrentUsedPercentage", usedPercentage, uiValue=usedPercentageStr)

                            if "accumEnergyTotal" in devSolarUsed.states:
                                if commandSentToSmappee == 'RESET_CONSUMPTION':
                                    pluginGlobal['smappees'][devSolarUsed.id]['accumEnergyTotal'] = 0.0
                                    wattStr = "%3.0f Watts" % (pluginGlobal['smappees'][devSolarUsed.id]['accumEnergyTotal'])
                                    devSolarUsed.updateStateOnServer("accumEnergyTotal", pluginGlobal['smappees'][devSolarUsed.id]['accumEnergyTotal'], uiValue=wattStr)

                                # kwhUsed = float(devSolarUsed.states.get("accumEnergyTotal", 0))
                                # kwhUsed += float(self.solarUsedTotal / 1000.0)
                                kwhUsedStr = str("%0.3f kWh" % (kwhUsed))  # Calculated in solar device

                                kwhUsedReformatted = float("%0.3f" % (kwhUsed))

                                if not pluginGlobal['smappees'][devSolarUsed.id]['hideSolarUsedMeterAccumGeneration']:
                                    if pluginGlobal['smappees'][devSolarUsed.id]['hideNoChangeInSolarUsedMeterAccumGeneration'] and kwhUsedReformatted == float(devSolarUsed.states['accumEnergyTotal']) and wattsUsed == 0.0:
                                        pass
                                    else:
                                        autolog(INFO, u"received '%s' solar energy used total: %s" % (devSolarUsed.name, kwhUsedStr))

                                devSolarUsed.updateStateOnServer("accumEnergyTotal", kwhUsedReformatted, uiValue=kwhUsedStr)


                                if "accumEnergyTotal" in devSolar.states:
                                    # Needed to caculate total used percentage - uses 'kwhSolar'

                                    if kwhSolar > 0.00:
                                        usedDailyPercentage = int(round((kwhUsed / kwhSolar) * 100))
                                    else:
                                        usedDailyPercentage = int(0)                                        
                                    usedDailyPercentageStr = "%d %%" % usedDailyPercentage
                                    devSolarUsed.updateStateOnServer("kwhDailyTotalUsedPercentage", usedDailyPercentage, uiValue=usedDailyPercentageStr)

                            pluginGlobal['smappees'][devSolarUsed.id]['lastReadingSolarUsedUtc'] = self.timestampUtc

                        if pluginGlobal['config']['supportsSolarExported'] == True:

                            if "curEnergyLevel" in devSolarExported.states:
                                if commandSentToSmappee == 'RESET_CONSUMPTION':

                                    pluginGlobal['smappees'][devSolarExported.id]['curEnergyLevel'] = 0.0
                                    pluginGlobal['smappees'][devSolarExported.id]['accumEnergyTotal'] = 0.0
                                    wattsExportedStr = "%3.0f Watts" % (pluginGlobal['smappees'][devSolarExported.id]['curEnergyLevel'])
                                    devSolarExported.updateStateOnServer("curEnergyLevel", pluginGlobal['smappees'][devSolarExported.id]['curEnergyLevel'], uiValue=wattsExportedStr)
                                    if float(indigo.server.apiVersion) >= 1.18:
                                        devSolarExported.updateStateImageOnServer(indigo.kStateImageSel.EnergyMeterOff)

                                self.options = devSolarExported.pluginProps['optionsEnergyMeterCurPower']

                                if self.options == 'mean':  # mean, minimum, maximum, last
                                    if self.solarExportedNumberOfValues > 0:
                                        wattsExported = (self.solarExportedMeanAverage * 60) / 5
                                    else:
                                        autolog(DETAIL, u"ELECTRICITY NET: CL=[%s], UTCL=[%s], LRUTC=[%s], LRUTC600=[%s]" % (self.solarExportedLast, self.timestampUtcLast, self.lastReadingElectricityNetUtc, (self.lastReadingElectricityNetUtc - 600000)))
                                        if self.solarExportedLast > 0.0 and self.timestampUtcLast != 0 and self.timestampUtcLast > (self.lastReadingElectricityNetUtc - 600000):
                                            wattsExported = self.solarExportedLast * 12
                                        else:
                                            wattsExported = 0.0
                                elif self.options == 'minimum':
                                    if self.solarExportedNumberOfValues > 0:
                                        wattsExported = self.solarExportedMinimum * 12
                                    else:
                                        autolog(DETAIL, u"ELECTRICITY NET: CL=[%s], UTCL=[%s], LRUTC=[%s], LRUTC600=[%s]" % (self.solarExportedLast, self.timestampUtcLast, self.lastReadingElectricityNetUtc, (self.lastReadingElectricityNetUtc - 600000)))
                                        if self.solarExportedLast > 0.0 and self.timestampUtcLast != 0 and self.timestampUtcLast > (self.lastReadingElectricityNetUtc - 600000):
                                            wattsExported = self.solarExportedLast * 12
                                        else:
                                            wattsExported = 0.0
                                elif self.options == 'maximum':
                                    if self.solarExportedNumberOfValues > 0:
                                        wattsExported = self.solarExportedMaximum * 12
                                    else:
                                        autolog(DETAIL, u"ELECTRICITY NET: CL=[%s], UTCL=[%s], LRUTC=[%s], LRUTC600=[%s]" % (self.solarExportedLast, self.timestampUtcLast, self.lastReadingElectricityNetUtc, (self.lastReadingElectricityNetUtc - 600000)))
                                        if self.solarExportedLast > 0.0 and self.timestampUtcLast != 0 and self.timestampUtcLast > (self.lastReadingElectricityNetUtc - 600000):
                                            wattsExported = self.solarExportedLast * 12
                                        else:
                                            wattsExported = 0.0
                                else:  # Assume last
 

                                    autolog(DETAIL, u"USAGESAVING: CL=[%s], UTCL=[%s], LRUTC=[%s], LRUTC600=[%s]" % (self.solarExportedLast, self.timestampUtcLast, self.lastReadingSolarExportedUtc, (self.lastReadingSolarExportedUtc - 600000)))

                                    if self.solarExportedLast > 0.0 and self.timestampUtcLast != 0 and self.timestampUtcLast > (self.lastReadingSolarExportedUtc - 600000):
                                        wattsExported = self.solarExportedLast * 12
                                    else:
                                        wattsExported = 0.0

                                if wattsExported == 0.0:
                                    wattsExported = self.solarExportedPrevious

                                wattsExportedStr = "%d Watts" % (wattsExported)
                                if not pluginGlobal['smappees'][devSolarExported.id]['hideSolarExportedMeterCurGeneration']:
                                    if wattsExported == 0.0 and pluginGlobal['smappees'][devSolarExported.id]['hideZeroSolarExportedMeterCurGeneration']:
                                        pass
                                    else:
                                        autolog(INFO, u"received '%s' solar energy exported reading: %s" % (devSolarExported.name, wattsExportedStr))
                                devSolarExported.updateStateOnServer("curEnergyLevel", wattsExported, uiValue=wattsExportedStr)
                                if float(indigo.server.apiVersion) >= 1.18:
                                    devSolarExported.updateStateImageOnServer(indigo.kStateImageSel.EnergyMeterOn)

                                if self.solar > 0.00:
                                    exportedPercentage = int(round((self.solarExported / self.solar) * 100))
                                else:
                                    exportedPercentage = int(0)
                                exportedPercentageStr = "%d %%" % exportedPercentage
                                devSolarExported.updateStateOnServer("kwhCurrentExportedPercentage", exportedPercentage, uiValue=exportedPercentageStr)

                            if "accumEnergyTotal" in devSolarExported.states:
                                if commandSentToSmappee == 'RESET_CONSUMPTION':
                                    pluginGlobal['smappees'][devSolarExported.id]['accumEnergyTotal'] = 0.0
                                    kwhExportedStr = "%3.0f kWh" % (pluginGlobal['smappees'][devSolarExported.id]['accumEnergyTotal'])
                                    devSolarExported.updateStateOnServer("accumEnergyTotal", pluginGlobal['smappees'][devSolarExported.id]['accumEnergyTotal'], uiValue=kwhExportedStr)

                                # kwhExported = float(devSolarExported.states.get("accumEnergyTotal", 0))
                                # kwhExported += float(self.solarExportedTotal / 1000.0)
                                kwhExportedStr = str("%0.3f kWh" % (kwhExported))  # Calculated in solar device - 'kwhExported'
                                kwhExportedReformatted = float("%0.3f" % (kwhExported))

                                if not pluginGlobal['smappees'][devSolarExported.id]['hideSolarExportedMeterAccumGeneration']:
                                    if pluginGlobal['smappees'][devSolarExported.id]['hideNoChangeInSolarExportedMeterAccumGeneration'] and kwhExportedReformatted == float(devSolarExported.states['accumEnergyTotal']) and wattsExported == 0.0:
                                        pass
                                    else:
                                        autolog(INFO, u"received '%s' solar energy exported total: %s" % (devSolarExported.name, kwhExportedStr))

                                devSolarExported.updateStateOnServer("accumEnergyTotal", kwhExportedReformatted, uiValue=kwhExportedStr)

                                if "accumEnergyTotal" in devSolar.states:
                                    # Needed to caculate total exported percentage - uses 'kwhSolar'

                                    if kwhSolar > 0.00:
                                        exportedDailyPercentage = int(round((kwhExported / kwhSolar) * 100))
                                    else:
                                        exportedDailyPercentage = int(0)
                                    exportedDailyPercentageStr = "%d %%" % exportedDailyPercentage
                                    devSolarExported.updateStateOnServer("kwhDailyTotalExportedPercentage", exportedDailyPercentage, uiValue=exportedDailyPercentageStr)

                                amountExportedReformatted = float(str("%0.2f" % (amountExported)))
                                amountExportedStr = str("%0.2f %s" % (amountExported, pluginGlobal['smappees'][devSolar.id]['currencyCode']))
                                devSolarExported.updateStateOnServer("dailyTotalExportOnlyIncome", amountExportedReformatted, uiValue=amountExportedStr)

                            pluginGlobal['smappees'][devSolarExported.id]['lastReadingSolarExportedUtc'] = self.timestampUtc

                    elif key == 'error':
                        autolog(ERROR, u"SMAPPEE ERROR DETECTED [%s]: %s" % (commandSentToSmappee, value))
                    else:
                        pass  # Unknown key/value pair
                        autolog(DETAIL, u"Unhandled key/value pair : K=[%s], V=[%s]" % (key, value))

        except StandardError, e:
            autolog(ERROR, u"StandardError detected in 'handleGetConsumption'. Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))   
            autolog(ERROR, u"Decoded response from Smappee was:'%s'" % (decodedSmappeeResponse))


    def handleGetSensorConsumption(self, commandSentToSmappee, responseLocationId, decodedSmappeeResponse):
        global pluginGlobal
        autolog(METHOD, u"%s" %  (methodNameForTrace())) 

        # return  # TEMP FIX

        autolog(DETAIL, u"handleGetSensorConsumption [AC-FIXED] - Decoded Response to '%s' = [%s] %s" % (commandSentToSmappee, responseLocationId, decodedSmappeeResponse))

        try:

            for decoding in decodedSmappeeResponse:

                errorDetected = False
                for key, value in decoding.iteritems():
                    if key == 'serviceLocationId' or key == 'sensorId' or key == 'records' or key == 'error':
                        if key == 'error':
                            autolog(DETAIL, u"SMAPPEE SENSOR handleGetSensorConsumption error detected by Smappee: Error=[%s]" % (value))
                            errorDetected = True
                        # At this point the response (so far) is OK as we know how to process the key
                    else:
                        autolog(DETAIL, u"SMAPPEE SENSOR Unhandled key/value pair : K=[%s], V=[%s]" % (key, value))
                if errorDetected == True:
                    autolog(ERROR, u"SMAPPEE SENSOR handleGetSensorConsumption error - response abandoned!")
                    break

                for key, value in decoding.iteritems():
                    if key == 'serviceLocationId':
                        indigo.server
                        sLoc = str(value)  # Service Location
                        autolog(DETAIL, u"handleGetSensorConsumption [serviceLocationId] - K = [%s], V = %s and sLoc = %s" % (key, value, sLoc))
                        break

                for key, value in decoding.iteritems():
                    if key == 'sensorId':
                        smappeeType = 'GW'  # Sensor for Gas Water
                        sId = str("%s%s" % (str(smappeeType), str("00%s" % (value))[-2:]))
                        autolog(DETAIL, u"handleGetSensorConsumption [sensorId] - sId = [%s]" % (sId))

                        def checkIndigoDev(serviceLocation, address):
                            try:
                                # autolog(DETAIL, u"handleGetSensorConsumption [sensorId-checkIndigoDev] - serviceLocation=[%s] %s, Smappee Address=[%s] %s" % (type(serviceLocation), serviceLocation, type(address), address))
                                returnedDevId = 0
                                # lastReadingSensorUtc = time.mktime(indigo.server.getTime().timetuple())  # Make greater than 'now' so that if no device exists - nothing will be processed
                                lastReadingSensorUtc = 0
                                pulsesPerUnit = 1  # Default
                                measurementTimeMultiplier = 1.0

                                for dev in indigo.devices.iter("self"):
                                    #autolog(DETAIL, u"handleGetSensorConsumption [sensorId-checkIndigoDev] - DN=%s, deviceTypeId=[%s] %s, serviceLocation=[%s] %s, deviceAddress=[%s] %s" % (dev.name, type(dev.deviceTypeId), dev.deviceTypeId, type(dev.pluginProps['serviceLocationId']), dev.pluginProps['serviceLocationId'], type(dev.address), dev.address))
                                    if (dev.deviceTypeId == "smappeeSensor") and (dev.pluginProps['serviceLocationId'] == serviceLocation) and (dev.address == address):
                                        autolog(DETAIL, u"handleGetSensorConsumption [sensorId-checkIndigoDev- FOUND] DN = [%s], TYPEID =  [%s], SL=[%s], A=[%s]" % (dev.name, dev.deviceTypeId, dev.pluginProps['serviceLocationId'], dev.address))
                                        returnedDevId = dev.id
                                        lastReadingSensorUtc = pluginGlobal['smappees'][dev.id]['lastReadingSensorUtc']
                                        pulsesPerUnit = pluginGlobal['smappees'][dev.id]['lastReadingSensorUtc']

                                        unitsKey = pluginGlobal['smappees'][dev.id]['units']
                                        if unitsKey in pluginGlobal['unitTable']:
                                            pass
                                        else:
                                            unitsKey = 'default'
                                        measurementTimeMultiplier = pluginGlobal['unitTable'][unitsKey]['measurementTimeMultiplier']

                                        if dev.states['smappeeSensorOnline'] == False:
                                            dev.updateStateOnServer("smappeeSensorOnline", True, uiValue='online')

                                return returnedDevId, lastReadingSensorUtc, pulsesPerUnit, measurementTimeMultiplier

                            except StandardError, e:
                                autolog(ERROR, u"StandardError detected in 'checkIndigoDev'. Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))   

                                return returnedDevId, lastReadingSensorUtc, pulsesPerUnit, measurementTimeMultiplier

                        sensorAddress = sId + '-A'
                        sensorA_DevId, lastReadingSensorA_Utc, pulsesPerUnitSensorA, measurementTimeMultiplierSensorA = checkIndigoDev(sLoc, sensorAddress)
                        sensorAddress = sId + '-B'
                        sensorB_DevId, lastReadingSensorB_Utc, pulsesPerUnitSensorB, measurementTimeMultiplierSensorB = checkIndigoDev(sLoc, sensorAddress)

                        autolog(DETAIL, u"handleGetSensorConsumption [sensorId-checkIndigoDev] - dev.Id [A] = [%s], dev.Id [B] = [%s]" % (sensorA_DevId, sensorB_DevId))

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

                        if pluginGlobal['SQL']['enabled'] == True:
                            try:
                                pluginGlobal['SQL']['connection'] = sql3.connect(pluginGlobal['SQL']['db'])
                                pluginGlobal['SQL']['cursor'] = pluginGlobal['SQL']['connection'].cursor()
                            except sql3.Error, e:
                                if pluginGlobal['SQL']['connection']:
                                    pluginGlobal['SQL']['connection'].rollback()
                                autolog(ERROR, u"SMAPPEE ERROR DETECTED WITH SQL [SENSOR] CONNECTION: %s" % (e.args[0]))

                                pluginGlobal['SQL']['enabled'] = False  # Disable SQL processing

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

                            autolog(DETAIL, u"handleGetSensorConsumption [Q][SENSOR] -  [START ...]")

                            for readingKey, readingValue in self.sensorReading.iteritems():
                                autolog(DETAIL, u"handleGetSensorConsumption [Q][SENSOR] -  [%s : %s]" % (readingKey, readingValue))
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
                            autolog(DETAIL, u"handleGetSensorConsumption [Q][SENSOR] -  [... END: TS=%s, V1=%s, V2=%s, TEMP=%s, HUM=%s, BAT=%s]" % (timestampUtc, value1, value2, temperature, humidity, batteryLevel))

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
                                        if readingSensorA_Detected == True:
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
                                        if readingSensorB_Detected == True:
                                            sensorB_Previous = value1 * measurementTimeMultiplierSensorB

                                autolog(DETAIL, u"handleGetSensorConsumption [Q][SENSOR] -  [... SQL: TS=%s, V1=%s, V2=%s, TEMP=%s, HUM=%s, BAT=%s]" % (timestampUtc, value1, value2, temperature, humidity, batteryLevel))

                                if pluginGlobal['SQL']['enabled'] == True:

                                    try:
                                        insertSql = 'NO SQL SET-UP YET'
                                        readingTime = str(int(timestampUtc / 1000))  # Remove micro seconds
                                        readingYYYYMMDDHHMMSS = datetime.datetime.fromtimestamp(int(readingTime)).strftime('%Y-%m-%d %H:%M:%S')
                                        readingYYYYMMDD = readingYYYYMMDDHHMMSS[0:10]
                                        readingHHMMSS = readingYYYYMMDDHHMMSS[-8:]
                                        sensor1     = str(int(value1))
                                        sensor2     = str(int(value2))
                                        humidity    = str(int(humidity * 10))
                                        temperature = str(int(temperature * 10))
                                        battery     = str(int(batteryLevel * 10))

                                        autolog(DETAIL, u"handleGetSensorConsumption [Q][SENSOR] -  [... INS: RT=%s, YYYYMMDD=%s, HHMMSS=%s, V1=%s, V2=%s, TEMP=%s, HUM=%s, BAT=%s]" % (readingTime, readingYYYYMMDDHHMMSS, readingHHMMSS, sensor1, sensor2, temperature, humidity, battery))
                                        
                                        insertSql = """
                                            INSERT OR REPLACE INTO sensor_readings (reading_time, reading_YYYYMMDD, reading_HHMMSS, sensor1, sensor2, humidity, temperature, battery)
                                            VALUES (%s, '%s', '%s', %s, %s, %s, %s, %s);
                                            """ % (readingTime, readingYYYYMMDD, readingHHMMSS, sensor1, sensor2, humidity, temperature, battery)
                                        pluginGlobal['SQL']['cursor'].executescript(insertSql)
                                    except sql3.Error, e:
                                        if pluginGlobal['SQL']['connection']:
                                            pluginGlobal['SQL']['connection'].rollback()
                                        autolog(ERROR, u"SMAPPEE ERROR DETECTED WITH SQL [SENSOR] INSERT: %s, SQL=[%s]" % (e.args[0], insertSql))
                                        if pluginGlobal['SQL']['connection']:
                                            pluginGlobal['SQL']['connection'].close()  

                                        pluginGlobal['SQL']['enabled'] = False  # Disable SQL processing


                        if pluginGlobal['SQL']['enabled'] == True:
                            try:
                                pluginGlobal['SQL']['connection'].commit()
                            except sql3.Error, e:
                                if pluginGlobal['SQL']['connection']:
                                    pluginGlobal['SQL']['connection'].rollback()
                                autolog(ERROR, u"SMAPPEE ERROR DETECTED WITH SQL [SENSOR] COMMIT: %s" % (e.args[0]))

                                pluginGlobal['SQL']['enabled'] = False  # Disable SQL processing
                            finally:
                                if pluginGlobal['SQL']['connection']:
                                    pluginGlobal['SQL']['connection'].close()  






                        # reading 'records' entries processing complete 

                        if sensorA_NumberOfValues > 0:
                            sensorA_MeanAverage = sensorA_Total / sensorA_NumberOfValues

                        autolog(DETAIL, u"READINGS - SENSOR [A]: N=[%s], T=[%s], MEAN=[%s], MIN=[%s], MAX=[%s], L=[%s]" \
                            % (sensorA_NumberOfValues, sensorA_Total, sensorA_MeanAverage, sensorA_Minimum, sensorA_Maximum, sensorA_Last))

                        if sensorB_NumberOfValues > 0:
                            sensorB_MeanAverage = sensorB_Total / sensorB_NumberOfValues

                        autolog(DETAIL, u"READINGS - SENSOR [B]: N=[%s], T=[%s], MEAN=[%s], MIN=[%s], MAX=[%s], L=[%s]" \
                            % (sensorB_NumberOfValues, sensorB_Total, sensorB_MeanAverage, sensorB_Minimum, sensorB_Maximum, sensorB_Last))

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

                                autolog(DETAIL, u"UpdateSensor [1 of 2] [%s]: Temp=%s, Humidity=%s, Battery=%s" % (sensorDesc, sensorTemperature, sensorHumidity, sensorBatteryLevel))
                                autolog(DETAIL, u"UpdateSensor [2 of 2] [%s]: Total=%s, NoV=%s, Mean=%s, Min=%s, Max=%s, Prev=%s, Last=%s" % (sensorDesc, str(sensorTotal), str(sensorNumberOfValues), str(sensorMeanAverage), str(sensorMinimum), str(sensorMaximum), str(sensorPrevious), str(sensorLast)))

                                if (sensorNumberOfValues == 0) and ("curEnergyLevel" in sensorDev.states) and (sensorDev.states['curEnergyLevel'] == 0.0):
                                    autolog(DETAIL, u"UpdateSensor [RETURNING, NO UPDATE] [%s]" % (sensorDesc))

                                    return  # Don't update energy totals if no values to process i.e nothing received since last timestamp

                                updateTimeString = datetime.datetime.fromtimestamp(int(timestampUtcLast / 1000)).strftime('%Y-%b-%d %H:%M')

                                if "readingsLastUpdated" in sensorDev.states:
                                    sensorDev.updateStateOnServer("readingsLastUpdated", updateTimeString)

                                if sensorTemperature != pluginGlobal['smappees'][sensorDev.id]['temperature']:
                                    if "temperature" in sensorDev.states:
                                        pluginGlobal['smappees'][sensorDev.id]['temperature'] = float(sensorTemperature)
                                        temperatureStr = "%1.0f deg C" % (float(sensorTemperature)/10)
                                        temperatureReformatted = float("%0.1f" % (float(sensorTemperature)/10))
                                        sensorDev.updateStateOnServer("temperature", temperatureReformatted, uiValue=temperatureStr)

                                        if "temperatureLastUpdated" in sensorDev.states:
                                            sensorDev.updateStateOnServer("temperatureLastUpdated", updateTimeString)

                                if sensorHumidity != pluginGlobal['smappees'][sensorDev.id]['humidity']:
                                    if "humidity" in sensorDev.states:
                                        pluginGlobal['smappees'][sensorDev.id]['humidity'] = float(sensorHumidity)
                                        humidityStr = "%1.0f%%" % (float(sensorHumidity))
                                        humidityReformatted = float("%0.1f" % (float(sensorHumidity)))
                                        sensorDev.updateStateOnServer("humidity", humidityReformatted, uiValue=humidityStr)
 
                                        if "humidityLastUpdated" in sensorDev.states:
                                             sensorDev.updateStateOnServer("humidityLastUpdated", updateTimeString)
 
                                if sensorBatteryLevel != pluginGlobal['smappees'][sensorDev.id]['batteryLevel']:
                                    if "batteryLevel" in sensorDev.states:
                                        pluginGlobal['smappees'][sensorDev.id]['batteryLevel'] = float(sensorBatteryLevel)
                                        batteryLevelStr = "%1.0f%%" % (float(sensorBatteryLevel))
                                        batteryLevelReformatted = float("%0.1f" % (float(sensorBatteryLevel)))
                                        sensorDev.updateStateOnServer("batteryLevel", batteryLevelReformatted, uiValue=batteryLevelStr)
  
                                        if "batteryLevelLastUpdated" in sensorDev.states:
                                            sensorDev.updateStateOnServer("batteryLevelLastUpdated", updateTimeString)

                                unitsKey = pluginGlobal['smappees'][sensorDev.id]['units']
                                if unitsKey in pluginGlobal['unitTable']:
                                    pass
                                else:
                                    unitsKey = 'default'

                                unitsCurrentUnits = pluginGlobal['unitTable'][unitsKey]['currentUnits'] 
                                unitsAccumUnits = pluginGlobal['unitTable'][unitsKey]['accumUnits'] 
                                unitsmeasurementTimeMultiplier = pluginGlobal['unitTable'][unitsKey]['measurementTimeMultiplier']
                                unitsformatTotaldivisor = pluginGlobal['unitTable'][unitsKey]['formatTotaldivisor']
                                unitsformatCurrent = pluginGlobal['unitTable'][unitsKey]['formatCurrent']
                                unitsformatCurrentUi = unitsformatCurrent + u' ' + unitsCurrentUnits
                                unitsformatTotal = pluginGlobal['unitTable'][unitsKey]['formatTotal']
                                unitsformatTotalUi = unitsformatTotal + ' ' + unitsAccumUnits


                                if "curEnergyLevel" in sensorDev.states:
                                    if commandSentToSmappee == 'RESET_SENSOR_CONSUMPTION':
                                        pluginGlobal['smappees'][sensorDev.id]['curEnergyLevel'] = 0.0
                                        dataToUpdateStr = str(unitsformatCurrent + " %s" % (pluginGlobal['smappees'][sensorDev.id]['curEnergyLevel'], unitsCurrentUnits))
                                        sensorDev.updateStateOnServer("curEnergyLevel", pluginGlobal['smappees'][sensorDev.id]['curEnergyLevel'], uiValue=dataToUpdateStr)
                                        if float(indigo.server.apiVersion) >= 1.18:
                                            sensorDev.updateStateImageOnServer(indigo.kStateImageSel.EnergyMeterOff)

                                    readingOption = sensorDev.pluginProps['optionsEnergyMeterCurPower']  # mean, minimum, maximum, last

                                    dataToUpdate = 0.0
                                    if readingOption == 'mean':  # mean, minimum, maximum, last
                                        if sensorNumberOfValues > 0:
                                            dataToUpdate = (sensorMeanAverage * 60) / 5
                                        else:
                                            autolog(DETAIL, u"SENSOR %s: [MEAN] CL=[%s], UTCL=[%s], LRUTC=[%s], LRUTC600=[%s]" % (sensorDesc, sensorLast, timestampUtcLast, lastReadingUtc, (lastReadingUtc - 600000)))
                                            if sensorLast > 0.0 and timestampUtcLast != 0 and timestampUtcLast > (lastReadingUtc - 600000):
                                                dataToUpdate = sensorLast * unitsmeasurementTimeMultiplier
                                    elif readingOption == 'minimum':
                                        if sensorNumberOfValues > 0:
                                            dataToUpdate = sensorMinimum * unitsmeasurementTimeMultiplier
                                        else:
                                            autolog(DETAIL, u"SENSOR %s: [MINIMUM] CL=[%s], UTCL=[%s], LRUTC=[%s], LRUTC600=[%s]" % (sensorDesc, sensorLast, timestampUtcLast, lastReadingUtc, (lastReadingUtc - 600000)))
                                            if sensorLast > 0.0 and timestampUtcLast != 0 and timestampUtcLast > (lastReadingUtc - 600000):
                                                dataToUpdate = sensorLast * unitsmeasurementTimeMultiplier
                                    elif readingOption == 'maximum':
                                        if sensorNumberOfValues > 0:
                                            watts = sensorMaximum * unitsmeasurementTimeMultiplier
                                        else:
                                            autolog(DETAIL, u"SENSOR %s: [MAXIMUM] CL=[%s], UTCL=[%s], LRUTC=[%s], LRUTC600=[%s]" % (sensorDesc, sensorLast, timestampUtcLast, lastReadingUtc, (lastReadingUtc - 600000)))
                                            if sensorLast > 0.0 and timestampUtcLast != 0 and timestampUtcLast > (lastReadingUtc - 600000):
                                                dataToUpdate = sensorLast * unitsmeasurementTimeMultiplier
                                    else:  # Assume last
                                        autolog(DETAIL, u"SENSOR %s: [LAST] CL=[%s], UTCL=[%s], LRUTC=[%s], LRUTC600=[%s]" % (sensorDesc, sensorLast, str(timestampUtcLast), str(lastReadingUtc), (str(lastReadingUtc - 600000))))
                                        if sensorLast > 0.0 and timestampUtcLast != 0 and timestampUtcLast > (lastReadingUtc - 600000):
                                            dataToUpdate = sensorLast * unitsmeasurementTimeMultiplier

                                    currentTimeUtc = int(time.mktime(indigo.server.getTime().timetuple()))
                                    currentTimeMinus6MinsUtc =  int((currentTimeUtc - 360) * 1000)  # Subtract 5 minutes (360 seconds)

                                    autolog(DETAIL, u"SENSOR %s: [TIME CHECK] currentTimeUtc=[%s], currentTimeMinus6MinsUtc=[%s], timestampUtcLast=[%s]" % (sensorDesc, currentTimeUtc, currentTimeMinus6MinsUtc, timestampUtcLast))
                                    if timestampUtcLast < currentTimeMinus6MinsUtc:
                                        dataToUpdate == 0.0

                                    dataToUpdateStr = u"%d %s" % (dataToUpdate, unitsCurrentUnits)
                                    if not pluginGlobal['smappees'][sensorDev.id]['hideEnergyMeterCurPower']:
                                        autolog(INFO, "received '%s' power load reading: %s" % (sensorDev.name, dataToUpdateStr))

                                    sensorDev.updateStateOnServer("curEnergyLevel", dataToUpdate, uiValue=dataToUpdateStr)
                                    if float(indigo.server.apiVersion) >= 1.18:
                                        sensorDev.updateStateImageOnServer(indigo.kStateImageSel.EnergyMeterOn)

                                if sensorNumberOfValues != 0 and "accumEnergyTotal" in sensorDev.states:

                                    if commandSentToSmappee == 'RESET_SENSOR_CONSUMPTION':
                                        pluginGlobal['smappees'][sensorDev.id]['accumEnergyTotal'] = 0.0
                                        dataToUpdateStr = str(unitsformatTotalUi % (pluginGlobal['smappees'][sensorDev.id]['accumEnergyTotal']))
                                        sensorDev.updateStateOnServer("accumEnergyTotal", pluginGlobal['smappees'][sensorDev.id]['accumEnergyTotal'], uiValue=dataToUpdateStr)

                                    dataToUpdate = float(sensorDev.states.get("accumEnergyTotal", 0))
                                    dataToUpdate += float(sensorTotal / unitsformatTotaldivisor)
                                    dataToUpdateStr = str(unitsformatTotalUi % (dataToUpdate))
                                    dataToUpdateReformatted = str(unitsformatTotal % (dataToUpdate))
                                    sensorDev.updateStateOnServer("accumEnergyTotal", dataToUpdateReformatted, uiValue=dataToUpdateStr)

                                    dataUnitCost = pluginGlobal['smappees'][sensorDev.id]['unitCost']
                                    dailyStandingCharge = pluginGlobal['smappees'][sensorDev.id]['dailyStandingCharge']
                                    amountGross = 0.00
                                    if dataUnitCost > 0.00:
                                        amountGross = (dailyStandingCharge + (dataToUpdate * dataUnitCost))
                                        amountGrossReformatted = float(str("%0.2f" % (amountGross)))
                                        amountGrossStr = str("%0.2f %s" % (amountGrossReformatted, pluginGlobal['smappees'][sensorDev.id]['currencyCode']))
                                        sensorDev.updateStateOnServer("dailyTotalCost", amountGrossReformatted, uiValue=amountGrossStr)

                                    if not pluginGlobal['smappees'][sensorDev.id]['hideEnergyMeterAccumPower']:
                                        if dataUnitCost == 0.00 or pluginGlobal['smappees'][sensorDev.id]['hideEnergyMeterAccumPowerCost'] == True:
                                            autolog(INFO, u"received '%s' energy total: %s" % (sensorDev.name, dataToUpdateStr))
                                        else:
                                            autolog(INFO, u"received '%s' energy total: %s (Gross %s)" % (sensorDev.name, dataToUpdateStr, amountGrossStr))



                                pluginGlobal['smappees'][sensorDev.id]['lastReadingSensorUtc'] = timestampUtc

                            except StandardError, e:
                                autolog(ERROR, u"StandardError detected in 'updateSensor'. Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))   

                        if sensorA_DevId != 0:
                            sensorA_Dev = indigo.devices[sensorA_DevId]
                            sensorValues = (timestampUtcLast, lastReadingSensorA_Utc, sensorA_Temperature, sensorA_Humidity, sensorA_BatteryLevel, sensorA_Total, sensorA_NumberOfValues, sensorA_MeanAverage, sensorA_Minimum, sensorA_Maximum, sensorA_Previous, sensorA_Last)
                            updateSensor(sensorA_Dev, 'A', sensorValues)

                        if sensorB_DevId != 0:
                            sensorB_Dev = indigo.devices[sensorB_DevId]
                            sensorValues = (timestampUtcLast, lastReadingSensorB_Utc, sensorB_Temperature, sensorB_Humidity, sensorB_BatteryLevel, sensorB_Total, sensorB_NumberOfValues, sensorB_MeanAverage, sensorB_Minimum, sensorB_Maximum, sensorB_Previous, sensorB_Last)
                            updateSensor(sensorB_Dev, 'B', sensorValues)

                        break

        except StandardError, e:
            autolog(ERROR, u"StandardError detected in 'handleGetSensorConsumption'. Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))   
            autolog(ERROR, u"Decoded response from Smappee was:'%s'" % (decodedSmappeeResponse))


    def handleSmappeeResponse(self, commandSentToSmappee, responseLocationId, responseFromSmappee):
        global pluginGlobal
        autolog(METHOD, u"%s" %  (methodNameForTrace()))  

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

            validSmappeeResponse, decodedSmappeeResponse = self.validateSmappeResponse(commandSentToSmappee, responseLocationId, responseFromSmappee)
            if validSmappeeResponse == False:
                # Response recieved from Smappee is invalid
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
            autolog(ERROR, u"StandardError detected in 'handleSmappeeResponse'. Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))   
            autolog(ERROR, u"Response from Smappee was:'%s'" % (responseFromSmappee))   


    def setSmappeeServiceLocationIdToDevId(self, function, smappeeDeviceTypeId, serviceLocationId, devId, smappeeAddress, devName):

      #  self.setSmappeeServiceLocationIdToDevId('ADD_UPDATE', 'smappeeSensor', responseLocationId, 0, sensorId, sensorName)

        global pluginGlobal
        autolog(METHOD, u"%s" %  (methodNameForTrace()))  

        try:

            if serviceLocationId == "" or serviceLocationId == "NONE":
                return
     
            if serviceLocationId not in pluginGlobal['smappeeServiceLocationIdToDevId']:
                pluginGlobal['smappeeServiceLocationIdToDevId'] = {}
                pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId] = {}
                pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['name'] = "HOME-HOME"
                pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['electricityId'] = 0
                pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['solarId'] = 0
                pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['electricityNetId'] = 0
                pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['electricitySavedId'] = 0
                pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['solarExportedId'] = 0
                pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['sensorIds'] = {}
                pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['applianceIds'] = {}
                pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['actuatorIds'] = {}

            smappeeAddress = str(smappeeAddress)
            if function == 'ADD_UPDATE':
                if smappeeDeviceTypeId == 'smappeeElectricity':
                    pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['electricityId'] = devId
                elif smappeeDeviceTypeId == 'smappeeElectricityNet':
                    pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['electricityNetId'] = devId
                elif smappeeDeviceTypeId == 'smappeeElectricitySaved':
                    pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['electricitySavedId'] = devId
                elif smappeeDeviceTypeId == 'smappeeSolar':
                    pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['solarId'] = devId
                elif smappeeDeviceTypeId == 'smappeeSolarUsed':
                    pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['solarUsedId'] = devId
                elif smappeeDeviceTypeId == 'smappeeSolarExported':
                    pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['solarExportedId'] = devId
                elif smappeeDeviceTypeId == 'smappeeSensor':
                    if smappeeAddress not in pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['sensorIds']:
                        pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['sensorIds'][smappeeAddress] = {}
                        pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['sensorIds'][smappeeAddress]['queued-add'] = False
                        pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['sensorIds'][smappeeAddress]['queued-remove'] = False
                        pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['sensorIds'][smappeeAddress]['devId'] = 0
                    if  pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['sensorIds'][smappeeAddress]['devId'] == 0:
                        pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['sensorIds'][smappeeAddress]['devId'] = devId
                    pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['sensorIds'][smappeeAddress]['name'] = str(devName)
                    autolog(DETAIL, u"setSmappeeServiceLocationIdToDevId [FF-E][SENSOR] - [%s]" % (pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['sensorIds']))
                elif smappeeDeviceTypeId == 'smappeeAppliance':
                    if smappeeAddress not in pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['applianceIds']:
                        pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['applianceIds'][smappeeAddress] = {}
                        pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['applianceIds'][smappeeAddress]['queued-add'] = False
                        pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['applianceIds'][smappeeAddress]['queued-remove'] = False
                    pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['applianceIds'][smappeeAddress]['devId'] = devId
                    pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['applianceIds'][smappeeAddress]['name'] = str(devName)
                elif smappeeDeviceTypeId == 'smappeeActuator':
                    if smappeeAddress not in pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['actuatorIds']:
                        pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['actuatorIds'][smappeeAddress] = {}
                        pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['actuatorIds'][smappeeAddress]['queued-add'] = False
                        pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['actuatorIds'][smappeeAddress]['queued-remove'] = False
                    pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['actuatorIds'][smappeeAddress]['devId'] = devId
                    pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['actuatorIds'][smappeeAddress]['name'] = str(devName)
     
            elif function == 'STOP':
                if smappeeDeviceTypeId == 'smappeeElectricity':
                    pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['electricityId'] = 0
                elif smappeeDeviceTypeId == 'smappeeElectricityNet':
                    pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['electricityNetId'] = 0
                elif smappeeDeviceTypeId == 'smappeeElectricitySaved':
                    pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['electricitySavedId'] = 0
                elif smappeeDeviceTypeId == 'smappeeSolar':
                    pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['solarId'] = 0
                elif smappeeDeviceTypeId == 'smappeeSolarUsed':
                    pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['solarUsedId'] = 0
                elif smappeeDeviceTypeId == 'smappeeSolarExported':
                    pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['solarExportedId'] = 0
                elif smappeeDeviceTypeId == 'smappeeSensor':
                    pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['sensorIds'][smappeeAddress]['queued-add'] = False
                    pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['sensorIds'][smappeeAddress]['queued-remove'] = False
                    pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['sensorIds'][smappeeAddress]['devId'] = 0
                elif smappeeDeviceTypeId == 'smappeeAppliance':
                    pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['applianceIds'][smappeeAddress]['devId'] = 0
                elif smappeeDeviceTypeId == 'smappeeActuator':
                    pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['actuatorIds'][smappeeAddress]['devId'] = 0

            elif function == 'QUEUE-ADD':
                if smappeeDeviceTypeId == 'smappeeSensor':
                    if smappeeAddress not in pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['sensorIds']:
                        pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['applianceIds'][smappeeAddress] = {}
                    pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['sensorIds'][smappeeAddress]['devId'] = 0
                    pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['sensorIds'][smappeeAddress]['name'] = str(devName)
                    pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['sensorIds'][smappeeAddress]['deviceType'] = str(smappeeDeviceTypeId)
                    pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['sensorIds'][smappeeAddress]['queued-add'] = True
                elif smappeeDeviceTypeId == 'smappeeAppliance':
                    if smappeeAddress not in pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['applianceIds']:
                        pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['applianceIds'][smappeeAddress] = {}
                    pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['applianceIds'][smappeeAddress]['devId'] = 0
                    pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['applianceIds'][smappeeAddress]['name'] = str(devName)
                    pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['applianceIds'][smappeeAddress]['queued-add'] = True
                elif smappeeDeviceTypeId == 'smappeeActuator':
                    if smappeeAddress not in pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['actuatorIds']:
                        pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['actuatorIds'][smappeeAddress] = {}
                    pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['actuatorIds'][smappeeAddress]['devId'] = 0
                    pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['actuatorIds'][smappeeAddress]['name'] = str(devName)
                    pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['actuatorIds'][smappeeAddress]['queued-add'] = True

            elif function == 'DEQUEUE':
                if smappeeDeviceTypeId == 'smappeeSensor':
                    if smappeeAddress not in pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['sensorIds']:
                        pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['sensorIds'][smappeeAddress] = {}
                    pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['sensorIds'][smappeeAddress]['devId'] = devId
                    pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['sensorIds'][smappeeAddress]['name'] = str(devName)
                    pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['sensorIds'][smappeeAddress]['queued-add'] = False
                    pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['sensorIds'][smappeeAddress]['queued-remove'] = False
                elif smappeeDeviceTypeId == 'smappeeAppliance':
                    if smappeeAddress not in pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['applianceIds']:
                        pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['applianceIds'][smappeeAddress] = {}
                    pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['applianceIds'][smappeeAddress]['devId'] = devId
                    pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['applianceIds'][smappeeAddress]['name'] = str(devName)
                    pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['applianceIds'][smappeeAddress]['queued-add'] = False
                    pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['applianceIds'][smappeeAddress]['queued-remove'] = False
                elif smappeeDeviceTypeId == 'smappeeActuator':
                    if smappeeAddress not in pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['actuatorIds']:
                        pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['actuatorIds'][smappeeAddress] = {}
                    pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['actuatorIds'][smappeeAddress]['devId'] = devId
                    pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['actuatorIds'][smappeeAddress]['name'] = str(devName)
                    pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['actuatorIds'][smappeeAddress]['queued-add'] = False
                    pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['actuatorIds'][smappeeAddress]['queued-remove'] = False

            elif function == 'QUEUE-REMOVE':
                if smappeeDeviceTypeId == 'smappeeSensor':
                    if smappeeAddress not in pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['sensorIds']:
                        pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['sensorIds'][smappeeAddress] = {}
                    pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['sensorIds'][smappeeAddress]['devId'] = 0
                    pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['sensorIds'][smappeeAddress]['name'] = str(devName)
                    pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['sensorIds'][smappeeAddress]['queued-remove'] = True
                elif smappeeDeviceTypeId == 'smappeeAppliance':
                    if smappeeAddress not in pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['applianceIds']:
                        pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['applianceIds'][smappeeAddress] = {}
                    pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['applianceIds'][smappeeAddress]['devId'] = 0
                    pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['applianceIds'][smappeeAddress]['name'] = str(devName)
                    pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['applianceIds'][smappeeAddress]['queued-remove'] = True
                elif smappeeDeviceTypeId == 'smappeeActuator':
                    if smappeeAddress not in pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['actuatorIds']:
                        pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['actuatorIds'][smappeeAddress] = {}
                    pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['actuatorIds'][smappeeAddress]['devId'] = 0
                    pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['actuatorIds'][smappeeAddress]['name'] = str(devName)
                    pluginGlobal['smappeeServiceLocationIdToDevId'][serviceLocationId]['actuatorIds'][smappeeAddress]['queued-remove'] = True


        except StandardError, e:
            autolog(ERROR, u"StandardError detected in 'setSmappeeServiceLocationIdToDevId'. Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))   
        
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
        global pluginGlobal
        autolog(METHOD, u"%s" %  (methodNameForTrace()))  
 
        if typeId == "smappeeElectricity":
            result = self.validateDeviceConfigUiSmappeeElectricity(valuesDict, typeId, devId)
        elif typeId == "smappeeSolar":
            result = self.validateDeviceConfigUiSmappeeSolar(valuesDict, typeId, devId)
        elif typeId == "smappeeSensor":
            result = self.validateDeviceConfigUiSmappeeSensor(valuesDict, typeId, devId)
        else:
            autolog(ERROR, u"WARNING: validateDeviceConfigUi TYPEID=%s NOT HANDLED" % (typeId))
            result = (True, valuesDict)

        if result[0] == True:
            return (True, result[1])  # True, Valuesdict
        else:
            return (False, result[1], result[2])  # True, Valuesdict, ErrorDict


    def validateDeviceConfigUiSmappeeElectricity(self, valuesDict, typeId, devId):

        validConfig = True  # Assume config is valid

        pluginGlobal['smappees'][devId]['hideEnergyMeterCurPower'] = False
        try:
            if "hideEnergyMeterCurPower" in valuesDict:
                pluginGlobal['smappees'][devId]['hideEnergyMeterCurPower'] = valuesDict["hideEnergyMeterCurPower"]
        except:
            pluginGlobal['smappees'][devId]['hideEnergyMeterCurPower'] = False

        pluginGlobal['smappees'][devId]['hideEnergyMeterAccumPower'] = False
        try:
            if "hideEnergyMeterAccumPower" in valuesDict:
                pluginGlobal['smappees'][devId]['hideEnergyMeterAccumPower'] = valuesDict["hideEnergyMeterAccumPower"]
        except:
            pluginGlobal['smappees'][devId]['hideEnergyMeterAccumPower'] = False

        pluginGlobal['smappees'][devId]['hideAlwaysOnPower'] = False
        try:
            if "hideEnergyMeterAccumPowerCost" in valuesDict:
                pluginGlobal['smappees'][devId]['hideEnergyMeterAccumPowerCost'] = valuesDict["hideEnergyMeterAccumPowerCost"]
        except:
            pluginGlobal['smappees'][devId]['hideEnergyMeterAccumPowerCost'] = False

        pluginGlobal['smappees'][devId]['hideAlwaysOnPower'] = False
        try:
            if "hideAlwaysOnPower" in valuesDict:
                pluginGlobal['smappees'][devId]['hideAlwaysOnPower'] = valuesDict["hideAlwaysOnPower"]
        except:
            pluginGlobal['smappees'][devId]['hideAlwaysOnPower'] = False

        try:
            if "currencyCode" in valuesDict:
                pluginGlobal['smappees'][dev.id]['currencyCode'] = valuesDict['currencyCode']
            else:
                pluginGlobal['smappees'][devId]['currencyCode'] = 'UKP'
        except:
            pluginGlobal['smappees'][devId]['currencyCode'] = 'UKP'

        try:
            if "dailyStandingCharge" in valuesDict:
                if valuesDict['dailyStandingCharge'] == '':
                    pluginGlobal['smappees'][devId]['dailyStandingCharge'] = 0.00
                else:
                    try:
                        pluginGlobal['smappees'][devId]['dailyStandingCharge'] = float(valuesDict['dailyStandingCharge'])
                    except:
                        pluginGlobal['smappees'][devId]['dailyStandingCharge'] = 0.00
                        validConfig = False
            else:
                pluginGlobal['smappees'][devId]['dailyStandingCharge'] = 0.00
        except:
            pluginGlobal['smappees'][devId]['dailyStandingCharge'] = 0.00
            validConfig = False

        if validConfig == False:
            errorDict = indigo.Dict()
            errorDict["dailyStandingCharge"] = "Daily Standing Charge is invalid"
            errorDict["showAlertText"] = "specify a valid financial amount e.g. '0.25'"
            return (False, valuesDict, errorDict)

        try:
            if "kwhUnitCost" in valuesDict:
                if valuesDict['kwhUnitCost'] == '':
                    pluginGlobal['smappees'][devId]['kwhUnitCost'] = 0.00
                else:
                    try:
                        pluginGlobal['smappees'][devId]['kwhUnitCost'] = float(valuesDict['kwhUnitCost'])
                    except:
                        pluginGlobal['smappees'][devId]['kwhUnitCost'] = 0.00
                        validConfig = False
            else:
                pluginGlobal['smappees'][devId]['kwhUnitCost'] = 0.00
        except:
            pluginGlobal['smappees'][devId]['kwhUnitCost'] = 0.00
            validConfig = False

        if validConfig == False:
            errorDict = indigo.Dict()
            errorDict["kwhUnitCost"] = "The kWh Unit Cost is invalid"
            errorDict["showAlertText"] = "specify a valid financial amount e.g. '0.15'"
            return (False, valuesDict, errorDict)

        return (True, valuesDict)


    def validateDeviceConfigUiSmappeeSolar(self, valuesDict, typeId, devId):

        pluginGlobal['smappees'][devId]['hideSolarMeterCurGeneration'] = False
        try:
            if "hideSolarMeterCurGeneration" in valuesDict:
                pluginGlobal['smappees'][devId]['hideSolarMeterCurGeneration'] = valuesDict["hideSolarMeterCurGeneration"]
        except:
            pluginGlobal['smappees'][devId]['hideSolarMeterCurGeneration'] = False

        pluginGlobal['smappees'][devId]['hideSolarMeterAccumGeneration'] = False
        try:
            if "hideSolarMeterAccumGeneration" in valuesDict:
                pluginGlobal['smappees'][devId]['hideSolarMeterAccumGeneration'] = valuesDict["hideSolarMeterAccumGeneration"]
        except:
            pluginGlobal['smappees'][devId]['hideSolarMeterAccumGeneration'] = False

        return (True, valuesDict)



    def validateDeviceConfigUiSmappeeSensor(self, valuesDict, typeId, devId):

        validConfig = True  # Assume config is valid

        pluginGlobal['smappees'][devId]['hideEnergyMeterCurPower'] = False
        try:
            if "hideEnergyMeterCurPower" in valuesDict:
                pluginGlobal['smappees'][devId]['hideEnergyMeterCurPower'] = valuesDict["hideEnergyMeterCurPower"]
        except:
            pluginGlobal['smappees'][devId]['hideEnergyMeterCurPower'] = False

        pluginGlobal['smappees'][devId]['hideEnergyMeterAccumPower'] = False
        try:
            if "hideEnergyMeterAccumPower" in valuesDict:
                pluginGlobal['smappees'][devId]['hideEnergyMeterAccumPower'] = valuesDict["hideEnergyMeterAccumPower"]
        except:
            pluginGlobal['smappees'][devId]['hideEnergyMeterAccumPower'] = False

        pluginGlobal['smappees'][devId]['hideAlwaysOnPower'] = False
        try:
            if "hideEnergyMeterAccumPowerCost" in valuesDict:
                pluginGlobal['smappees'][devId]['hideEnergyMeterAccumPowerCost'] = valuesDict["hideEnergyMeterAccumPowerCost"]
        except:
            pluginGlobal['smappees'][devId]['hideEnergyMeterAccumPowerCost'] = False

        pluginGlobal['smappees'][devId]['hideAlwaysOnPower'] = False
        try:
            if "hideAlwaysOnPower" in valuesDict:
                pluginGlobal['smappees'][devId]['hideAlwaysOnPower'] = valuesDict["hideAlwaysOnPower"]
        except:
            pluginGlobal['smappees'][devId]['hideAlwaysOnPower'] = False

        try:
            if "currencyCode" in valuesDict:
                pluginGlobal['smappees'][dev.id]['currencyCode'] = valuesDict['currencyCode']
            else:
                pluginGlobal['smappees'][devId]['currencyCode'] = 'UKP'
        except:
            pluginGlobal['smappees'][devId]['currencyCode'] = 'UKP'

        try:
            if "dailyStandingCharge" in valuesDict:
                if valuesDict['dailyStandingCharge'] == '':
                    pluginGlobal['smappees'][devId]['dailyStandingCharge'] = 0.00
                else:
                    try:
                        pluginGlobal['smappees'][devId]['dailyStandingCharge'] = float(valuesDict['dailyStandingCharge'])
                    except:
                        pluginGlobal['smappees'][devId]['dailyStandingCharge'] = 0.00
                        validConfig = False
            else:
                pluginGlobal['smappees'][devId]['dailyStandingCharge'] = 0.00
        except:
            pluginGlobal['smappees'][devId]['dailyStandingCharge'] = 0.00
            validConfig = False

        if validConfig == False:
            errorDict = indigo.Dict()
            errorDict["dailyStandingCharge"] = "Daily Standing Charge is invalid"
            errorDict["showAlertText"] = "specify a valid financial amount e.g. '0.25'"
            return (False, valuesDict, errorDict)

        try:
            if "unitCost" in valuesDict:
                if valuesDict['unitCost'] == '':
                    pluginGlobal['smappees'][devId]['unitCost'] = 0.00
                else:
                    try:
                        pluginGlobal['smappees'][devId]['kwhUnitCost'] = float(valuesDict['unitCost'])
                    except:
                        pluginGlobal['smappees'][devId]['kwhUnitCost'] = 0.00
                        validConfig = False
            else:
                pluginGlobal['smappees'][devId]['kwhUnitCost'] = 0.00
        except:
            pluginGlobal['smappees'][devId]['kwhUnitCost'] = 0.00
            validConfig = False

        if validConfig == False:
            errorDict = indigo.Dict()
            errorDict["kwhUnitCost"] = "The Unit Cost is invalid"
            errorDict["showAlertText"] = "specify a valid financial amount e.g. '0.15'"
            return (False, valuesDict, errorDict)

        return (True, valuesDict)




    def deviceStartComm(self, dev):
        global pluginGlobal
        autolog(METHOD, u"%s" %  (methodNameForTrace()))  

        if dev.deviceTypeId == "smappeeElectricity" or dev.deviceTypeId == "smappeeElectricityNet" or dev.deviceTypeId == "smappeeElectricitySaved" or dev.deviceTypeId == "smappeeSolar" or dev.deviceTypeId == "smappeeSolarUsed" or dev.deviceTypeId == "smappeeSolarExported" or dev.deviceTypeId == "smappeeSensor" or dev.deviceTypeId == "smappeeAppliance" or dev.deviceTypeId == "smappeeActuator":
            pass
        else:
            autolog(ERROR, u"Failed to start Smappee Appliance [%s]: Device type [%s] not known by plugin." % (dev.name, dev.deviceTypeId))
            return

        dev.stateListOrDisplayStateIdChanged()  # Ensure latest devices.xml is being used

        try:
            # Initialise internal to plugin smappee electricity states to default values
            if dev.deviceTypeId == "smappeeElectricity":

                autolog(DETAIL, u"SMAPPEE DEV [ELECTRICITY] START smappeeServiceLocationIdToDevId = [%s]" % (pluginGlobal['smappeeServiceLocationIdToDevId']))

                pluginGlobal['config']['supportsElectricity'] = True

                self.serviceLocationId = str(dev.pluginProps['serviceLocationId'])

                autolog(DETAIL, u"SMAPPEE DEV [ELECTRICITY] START self.serviceLocationId = [%s]" % (self.serviceLocationId))

                self.setSmappeeServiceLocationIdToDevId('ADD_UPDATE', 'smappeeElectricity', self.serviceLocationId, dev.id, "", "")

                autolog(DETAIL, u"SMAPPEE DEV [ELECTRICITY] START smappeeServiceLocationIdToDevId [2] = [%s]" % (pluginGlobal['smappeeServiceLocationIdToDevId']))

                pluginGlobal['smappees'][dev.id] = {}
                pluginGlobal['smappees'][dev.id]['serviceLocationId'] = dev.pluginProps['serviceLocationId']
                pluginGlobal['smappees'][dev.id]['serviceLocationName'] = dev.pluginProps['serviceLocationName']
                pluginGlobal['smappees'][dev.id]['name'] = dev.name
                pluginGlobal['smappees'][dev.id]['longditude'] = 0
                pluginGlobal['smappees'][dev.id]['latitude'] = 0
                pluginGlobal['smappees'][dev.id]['electricityCost'] = 0
                pluginGlobal['smappees'][dev.id]['electricityCurrency'] = 0
                pluginGlobal['smappees'][dev.id]['curEnergyLevel'] = 0.0
                pluginGlobal['smappees'][dev.id]['accumEnergyTotal'] = 0.0
                pluginGlobal['smappees'][dev.id]['dailyTotalCost'] = 0.0
                pluginGlobal['smappees'][dev.id]['alwaysOn'] = 0.0
                pluginGlobal['smappees'][dev.id]['lastResetElectricityUtc'] = 0
                pluginGlobal['smappees'][dev.id]['lastReadingElectricityUtc'] = 0
                pluginGlobal['smappees'][dev.id]['lastReadingElectricity'] = 0.0
                try:
                    pluginGlobal['smappees'][dev.id]['hideEnergyMeterCurPower'] = dev.pluginProps['hideEnergyMeterCurPower']
                except:
                    pluginGlobal['smappees'][dev.id]['hideEnergyMeterCurPower'] = False
                try:
                    pluginGlobal['smappees'][dev.id]['hideEnergyMeterAccumPower'] = dev.pluginProps['hideEnergyMeterAccumPower']
                except:
                    pluginGlobal['smappees'][dev.id]['hideEnergyMeterAccumPower'] = False
                try:
                    pluginGlobal['smappees'][dev.id]['hideEnergyMeterAccumPowerCost'] = dev.pluginProps['hideEnergyMeterAccumPowerCost']
                except:
                    pluginGlobal['smappees'][dev.id]['hideEnergyMeterAccumPowerCost'] = False
                try:
                    pluginGlobal['smappees'][dev.id]['hideAlwaysOnPower'] = dev.pluginProps['hideAlwaysOnPower']
                except:
                    pluginGlobal['smappees'][dev.id]['hideAlwaysOnPower'] = False
                try:
                    pluginGlobal['smappees'][dev.id]['currencyCode'] = dev.pluginProps['currencyCode']
                except:
                    pluginGlobal['smappees'][dev.id]['currencyCode'] = 'UKP'
                try:
                    pluginGlobal['smappees'][dev.id]['dailyStandingCharge'] = float(dev.pluginProps['dailyStandingCharge'])
                except:
                    pluginGlobal['smappees'][dev.id]['dailyStandingCharge'] = 8.88  # To make it obvious there is an error
                try:
                    pluginGlobal['smappees'][dev.id]['kwhUnitCost'] = float(dev.pluginProps['kwhUnitCost'])
                except:
                    pluginGlobal['smappees'][dev.id]['kwhUnitCost'] = 9.99  # To make it obvious there is an error

                if "curEnergyLevel" in dev.states:
                    wattStr = "%3.0f Watts" % (pluginGlobal['smappees'][dev.id]['curEnergyLevel'])
                    dev.updateStateOnServer("curEnergyLevel", pluginGlobal['smappees'][dev.id]['curEnergyLevel'], uiValue=wattStr)

                if "accumEnergyTotal" in dev.states:
                    kwhStr = "%3.0f kWh" % (pluginGlobal['smappees'][dev.id]['accumEnergyTotal'])
                    dev.updateStateOnServer("accumEnergyTotal", pluginGlobal['smappees'][dev.id]['accumEnergyTotal'], uiValue=kwhStr)

                if "alwaysOn" in dev.states:
                    wattStr = "%3.0f Watts" % (pluginGlobal['smappees'][dev.id]['alwaysOn'])
                    dev.updateStateOnServer("alwaysOn", pluginGlobal['smappees'][dev.id]['alwaysOn'], uiValue=wattStr)

                if  "dailyTotalCost" in dev.states:
                    costStr = "%3.0f" % (pluginGlobal['smappees'][dev.id]['dailyTotalCost'])
                    dev.updateStateOnServer("dailyTotalCost", pluginGlobal['smappees'][dev.id]['dailyTotalCost'], uiValue=costStr)

                dev.updateStateOnServer("smappeeElectricityOnline", False, uiValue='offline')

                if pluginGlobal['pluginInitialised'] == True and self.serviceLocationId != "":
                    self.sendToSmappeeQueue.put(["GET_CONSUMPTION",str(self.serviceLocationId)])

                autolog(INFO, u"Started '%s' at address [%s]" % (dev.name, dev.address))

            # Initialise internal to plugin smappee electricity net states to default values
            elif dev.deviceTypeId == "smappeeElectricityNet":

                autolog(DETAIL, u"SMAPPEE DEV [ELECTRICITY NET] START smappeeServiceLocationIdToDevId = [%s]" % (pluginGlobal['smappeeServiceLocationIdToDevId']))

                pluginGlobal['config']['supportsElectricityNet'] = True

                self.serviceLocationId = str(dev.pluginProps['serviceLocationId'])

                autolog(DETAIL, u"SMAPPEE DEV [ELECTRICITY NET] START self.serviceLocationId = [%s]" % (self.serviceLocationId))

                self.setSmappeeServiceLocationIdToDevId('ADD_UPDATE', 'smappeeElectricityNet', self.serviceLocationId, dev.id, '0', '0')

                autolog(DETAIL, u"SMAPPEE DEV [ELECTRICITY NET] START smappeeServiceLocationIdToDevId [2] = [%s]" % (pluginGlobal['smappeeServiceLocationIdToDevId']))

                pluginGlobal['smappees'][dev.id] = {}
                pluginGlobal['smappees'][dev.id]['serviceLocationId'] = dev.pluginProps['serviceLocationId']
                pluginGlobal['smappees'][dev.id]['serviceLocationName'] = dev.pluginProps['serviceLocationName']
                pluginGlobal['smappees'][dev.id]['name'] = dev.name
                pluginGlobal['smappees'][dev.id]['electricityCost'] = 0
                pluginGlobal['smappees'][dev.id]['electricityCurrency'] = 0
                pluginGlobal['smappees'][dev.id]['curEnergyLevel'] = 0.0
                pluginGlobal['smappees'][dev.id]['accumEnergyTotal'] = 0.0
                pluginGlobal['smappees'][dev.id]['dailyNetTotalCost'] = 0.0
                pluginGlobal['smappees'][dev.id]['lastResetElectricityNetUtc'] = 0
                pluginGlobal['smappees'][dev.id]['lastReadingElectricityNetUtc'] = 0
                pluginGlobal['smappees'][dev.id]['lastReadingElectricityNet'] = 0.0
                try:
                    pluginGlobal['smappees'][dev.id]['hideEnergyMeterCurNetPower'] = dev.pluginProps['hideEnergyMeterCurNetPower']
                except:
                    pluginGlobal['smappees'][dev.id]['hideEnergyMeterCurNetPower'] = False
                try:
                    pluginGlobal['smappees'][dev.id]['hideEnergyMeterCurZeroNetPower'] = dev.pluginProps['hideEnergyMeterCurZeroNetPower']
                except:
                    pluginGlobal['smappees'][dev.id]['hideEnergyMeterCurZeroNetPower'] = False
                try:
                    pluginGlobal['smappees'][dev.id]['hideEnergyMeterAccumNetPower'] = dev.pluginProps['hideEnergyMeterAccumNetPower']
                except:
                    pluginGlobal['smappees'][dev.id]['hideEnergyMeterAccumNetPower'] = False
                try:
                    pluginGlobal['smappees'][dev.id]['hideEnergyMeterAccumNetPowerCost'] = dev.pluginProps['hideEnergyMeterAccumNetPowerCost']
                except:
                    pluginGlobal['smappees'][dev.id]['hideEnergyMeterAccumNetPowerCost'] = False
                try:
                    pluginGlobal['smappees'][dev.id]['hideNoChangeEnergyMeterAccumNetPower'] = dev.pluginProps['hideNoChangeEnergyMeterAccumNetPower']
                except:
                    pluginGlobal['smappees'][dev.id]['hideNoChangeEnergyMeterAccumNetPower'] = False

                if "curEnergyLevel" in dev.states:
                    wattStr = "%3.0f Watts" % (pluginGlobal['smappees'][dev.id]['curEnergyLevel'])
                    dev.updateStateOnServer("curEnergyLevel", pluginGlobal['smappees'][dev.id]['curEnergyLevel'], uiValue=wattStr)

                if "accumEnergyTotal" in dev.states:
                    kwhStr = "%3.0f kWh" % (pluginGlobal['smappees'][dev.id]['accumEnergyTotal'])
                    dev.updateStateOnServer("accumEnergyTotal", pluginGlobal['smappees'][dev.id]['accumEnergyTotal'], uiValue=kwhStr)

                if  "dailyNetTotalCost" in dev.states:
                    costStr = "%3.0f" % (pluginGlobal['smappees'][dev.id]['dailyNetTotalCost'])
                    dev.updateStateOnServer("dailyNetTotalCost", pluginGlobal['smappees'][dev.id]['dailyNetTotalCost'], uiValue=costStr)

                dev.updateStateOnServer("smappeeElectricityNetOnline", False, uiValue='offline')

                # if pluginGlobal['pluginInitialised'] == True and self.serviceLocationId != "":
                #     self.sendToSmappeeQueue.put(["GET_CONSUMPTION",str(self.serviceLocationId)])

                autolog(INFO, u"Started '%s' at address [%s]" % (dev.name, dev.address))

            # Initialise internal to plugin smappee electricity Saved states to default values
            elif dev.deviceTypeId == "smappeeElectricitySaved":

                autolog(DETAIL, u"SMAPPEE DEV [ELECTRICITY SAVED] START smappeeServiceLocationIdToDevId = [%s]" % (pluginGlobal['smappeeServiceLocationIdToDevId']))

                pluginGlobal['config']['supportsElectricitySaved'] = True

                self.serviceLocationId = str(dev.pluginProps['serviceLocationId'])

                autolog(DETAIL, u"SMAPPEE DEV [ELECTRICITY SAVED] START self.serviceLocationId = [%s]" % (self.serviceLocationId))

                self.setSmappeeServiceLocationIdToDevId('ADD_UPDATE', 'smappeeElectricitySaved', self.serviceLocationId, dev.id, '0', '0')

                autolog(DETAIL, u"SMAPPEE DEV [ELECTRICITY SAVED] START smappeeServiceLocationIdToDevId [2] = [%s]" % (pluginGlobal['smappeeServiceLocationIdToDevId']))

                pluginGlobal['smappees'][dev.id] = {}
                pluginGlobal['smappees'][dev.id]['serviceLocationId'] = dev.pluginProps['serviceLocationId']
                pluginGlobal['smappees'][dev.id]['serviceLocationName'] = dev.pluginProps['serviceLocationName']
                pluginGlobal['smappees'][dev.id]['name'] = dev.name
                pluginGlobal['smappees'][dev.id]['electricityCost'] = 0
                pluginGlobal['smappees'][dev.id]['electricityCurrency'] = 0
                pluginGlobal['smappees'][dev.id]['curEnergyLevel'] = 0.0
                pluginGlobal['smappees'][dev.id]['accumEnergyTotal'] = 0.0
                pluginGlobal['smappees'][dev.id]['dailyTotalCostSaving'] = 0.0
                pluginGlobal['smappees'][dev.id]['lastResetElectricitySavedUtc'] = 0
                pluginGlobal['smappees'][dev.id]['lastReadingElectricitySavedUtc'] = 0
                pluginGlobal['smappees'][dev.id]['lastReadingElectricitySaved'] = 0.0
                try:
                    pluginGlobal['smappees'][dev.id]['hideEnergyMeterCurSavedPower'] = dev.pluginProps['hideEnergyMeterCurSavedPower']
                except:
                    pluginGlobal['smappees'][dev.id]['hideEnergyMeterCurSavedPower'] = False
                try:
                    pluginGlobal['smappees'][dev.id]['hideEnergyMeterCurZeroSavedPower'] = dev.pluginProps['hideEnergyMeterCurZeroSavedPower']
                except:
                    pluginGlobal['smappees'][dev.id]['hideEnergyMeterCurZeroSavedPower'] = False
                try:
                    pluginGlobal['smappees'][dev.id]['hideEnergyMeterAccumSavedPower'] = dev.pluginProps['hideEnergyMeterAccumSavedPower']
                except:
                    pluginGlobal['smappees'][dev.id]['hideEnergyMeterAccumSavedPower'] = False
                try:
                    pluginGlobal['smappees'][dev.id]['hideEnergyMeterAccumSavedPowerCost'] = dev.pluginProps['hideEnergyMeterAccumSavedPowerCost']
                except:
                    pluginGlobal['smappees'][dev.id]['hideEnergyMeterAccumSavedPowerCost'] = False
                try:
                    pluginGlobal['smappees'][dev.id]['hideNoChangeEnergyMeterAccumSavedPower'] = dev.pluginProps['hideNoChangeEnergyMeterAccumSavedPower']
                except:
                    pluginGlobal['smappees'][dev.id]['hideNoChangeEnergyMeterAccumSavedPower'] = False


                if "curEnergyLevel" in dev.states:
                    wattStr = "%3.0f Watts" % (pluginGlobal['smappees'][dev.id]['curEnergyLevel'])
                    dev.updateStateOnServer("curEnergyLevel", pluginGlobal['smappees'][dev.id]['curEnergyLevel'], uiValue=wattStr)

                if "accumEnergyTotal" in dev.states:
                    kwhStr = "%3.0f kWh" % (pluginGlobal['smappees'][dev.id]['accumEnergyTotal'])
                    dev.updateStateOnServer("accumEnergyTotal", pluginGlobal['smappees'][dev.id]['accumEnergyTotal'], uiValue=kwhStr)

                if "dailyTotalCostSaving" in dev.states:
                    costStr = "%3.0f" % (pluginGlobal['smappees'][dev.id]['dailyTotalCostSaving'])
                    dev.updateStateOnServer("dailyTotalCostSaving", pluginGlobal['smappees'][dev.id]['dailyTotalCostSaving'], uiValue=costStr)

                dev.updateStateOnServer("smappeeElectricitySavedOnline", False, uiValue='offline')

                # if pluginGlobal['pluginInitialised'] == True and self.serviceLocationId != "":
                #     self.sendToSmappeeQueue.put(["GET_CONSUMPTION",str(self.serviceLocationId)])

                autolog(INFO, u"Started '%s' at address [%s]" % (dev.name, dev.address))

            # Initialise internal to plugin smappee solar states to default values
            elif dev.deviceTypeId == "smappeeSolar":

                autolog(DETAIL, u"SMAPPEE DEV [SOLAR] START smappeeServiceLocationIdToDevId = [%s]" % (pluginGlobal['smappeeServiceLocationIdToDevId']))

                pluginGlobal['config']['supportsSolar'] = True

                self.serviceLocationId = str(dev.pluginProps['serviceLocationId'])

                autolog(DETAIL, u"SMAPPEE DEV [SOLAR] START self.serviceLocationId = [%s]" % (self.serviceLocationId))

                self.setSmappeeServiceLocationIdToDevId('ADD_UPDATE', 'smappeeSolar', self.serviceLocationId, dev.id, '0', '0')

                autolog(DETAIL, u"SMAPPEE DEV [SOLAR] START smappeeServiceLocationIdToDevId [2] = [%s]" % (pluginGlobal['smappeeServiceLocationIdToDevId']))

                pluginGlobal['smappees'][dev.id] = {}
                pluginGlobal['smappees'][dev.id]['serviceLocationId'] = dev.pluginProps['serviceLocationId']
                pluginGlobal['smappees'][dev.id]['serviceLocationName'] = dev.pluginProps['serviceLocationName']
                pluginGlobal['smappees'][dev.id]['name'] = dev.name
                pluginGlobal['smappees'][dev.id]['electricityCost'] = 0
                pluginGlobal['smappees'][dev.id]['electricityCurrency'] = 0
                pluginGlobal['smappees'][dev.id]['curEnergyLevel'] = 0.0
                pluginGlobal['smappees'][dev.id]['accumEnergyTotal'] = 0.0
                pluginGlobal['smappees'][dev.id]['lastResetSolarUtc'] = 0
                pluginGlobal['smappees'][dev.id]['lastReadingSolarUtc'] = 0
                pluginGlobal['smappees'][dev.id]['lastReadingSolar'] = 0.0
                try:
                    pluginGlobal['smappees'][dev.id]['hideSolarMeterCurGeneration'] = dev.pluginProps['hideSolarMeterCurGeneration']
                except:
                    pluginGlobal['smappees'][dev.id]['hideSolarMeterCurGeneration'] = False
                try:
                    pluginGlobal['smappees'][dev.id]['hideZeroSolarMeterCurGeneration'] = dev.pluginProps['hideZeroSolarMeterCurGeneration']
                except:
                    pluginGlobal['smappees'][dev.id]['hideZeroSolarMeterCurGeneration'] = False
                try:
                    pluginGlobal['smappees'][dev.id]['hideSolarMeterAccumGeneration'] = dev.pluginProps['hideSolarMeterAccumGeneration']
                except:
                    pluginGlobal['smappees'][dev.id]['hideSolarMeterAccumGeneration'] = False
                try:
                    pluginGlobal['smappees'][dev.id]['hideSolarMeterAccumGenerationCost'] = dev.pluginProps['hideSolarMeterAccumGenerationCost']
                except:
                    pluginGlobal['smappees'][dev.id]['hideSolarMeterAccumGenerationCost'] = False
                try:
                    pluginGlobal['smappees'][dev.id]['hideNoChangeInSolarMeterAccumGeneration'] = dev.pluginProps['hideNoChangeInSolarMeterAccumGeneration']
                except:
                    pluginGlobal['smappees'][dev.id]['hideNoChangeInSolarMeterAccumGeneration'] = False
                try:
                    pluginGlobal['smappees'][dev.id]['currencyCode'] = dev.pluginProps['currencyCode']
                except:
                    pluginGlobal['smappees'][dev.id]['currencyCode'] = 'UKP'
                try:
                    pluginGlobal['smappees'][dev.id]['generationRate'] = float(dev.pluginProps['generationRate'])
                except:
                    pluginGlobal['smappees'][dev.id]['generationRate'] = 8.88  # To make it obvious there is an error

                try:
                    pluginGlobal['smappees'][dev.id]['exportType'] = dev.pluginProps['exportType']
                except:
                    pluginGlobal['smappees'][dev.id]['exportType'] = 'percentage'

                try:
                    pluginGlobal['smappees'][dev.id]['exportPercentage'] = float(dev.pluginProps['exportPercentage'])
                except:
                    pluginGlobal['smappees'][dev.id]['exportPercentage'] = 50.0  # To make it obvious there is an error

                try:
                    pluginGlobal['smappees'][dev.id]['exportRate'] = float(dev.pluginProps['exportRate'])
                except:
                    pluginGlobal['smappees'][dev.id]['exportRate'] = 9.99  # To make it obvious there is an error
                if "curEnergyLevel" in dev.states:
                    wattStr = "%3.0f Watts" % (pluginGlobal['smappees'][dev.id]['curEnergyLevel'])
                    dev.updateStateOnServer("curEnergyLevel", pluginGlobal['smappees'][dev.id]['curEnergyLevel'], uiValue=wattStr)

                if "accumEnergyTotal" in dev.states:
                    kwhStr = "%3.0f kWh" % (pluginGlobal['smappees'][dev.id]['accumEnergyTotal'])
                    dev.updateStateOnServer("accumEnergyTotal", pluginGlobal['smappees'][dev.id]['accumEnergyTotal'], uiValue=kwhStr)

                dev.updateStateOnServer("smappeeSolarOnline", False, uiValue='offline')

                if pluginGlobal['pluginInitialised'] == True and self.serviceLocationId != "":
                    self.sendToSmappeeQueue.put(["GET_CONSUMPTION",str(self.serviceLocationId)])

                autolog(INFO, u"Started '%s' at address [%s]" % (dev.name, dev.address))

            # Initialise internal to plugin smappee solar used states to default values
            elif dev.deviceTypeId == "smappeeSolarUsed":

                autolog(DETAIL, u"SMAPPEE DEV [SOLAR USED] START smappeeServiceLocationIdToDevId = [%s]" % (pluginGlobal['smappeeServiceLocationIdToDevId']))

                pluginGlobal['config']['supportsSolarUsed'] = True

                self.serviceLocationId = str(dev.pluginProps['serviceLocationId'])

                autolog(DETAIL, u"SMAPPEE DEV [SOLAR USED] START self.serviceLocationId = [%s]" % (self.serviceLocationId))

                self.setSmappeeServiceLocationIdToDevId('ADD_UPDATE', 'smappeeSolarUsed', self.serviceLocationId, dev.id, '0', '0')

                autolog(DETAIL, u"SMAPPEE DEV [SOLAR USED] START smappeeServiceLocationIdToDevId [2] = [%s]" % (pluginGlobal['smappeeServiceLocationIdToDevId']))

                pluginGlobal['smappees'][dev.id] = {}
                pluginGlobal['smappees'][dev.id]['serviceLocationId'] = dev.pluginProps['serviceLocationId']
                pluginGlobal['smappees'][dev.id]['serviceLocationName'] = dev.pluginProps['serviceLocationName']
                pluginGlobal['smappees'][dev.id]['name'] = dev.name
                pluginGlobal['smappees'][dev.id]['electricityCost'] = 0
                pluginGlobal['smappees'][dev.id]['electricityCurrency'] = 0
                pluginGlobal['smappees'][dev.id]['curEnergyLevel'] = 0.0
                pluginGlobal['smappees'][dev.id]['accumEnergyTotal'] = 0.0
                pluginGlobal['smappees'][dev.id]['lastResetSolarUsedUtc'] = 0
                pluginGlobal['smappees'][dev.id]['lastReadingSolarUsedUtc'] = 0
                pluginGlobal['smappees'][dev.id]['lastReadingSolarUsed'] = 0.0
                pluginGlobal['smappees'][dev.id]['hideSolarUsedMeterCurGeneration'] = dev.pluginProps['hideSolarUsedMeterCurGeneration']
                pluginGlobal['smappees'][dev.id]['hideZeroSolarUsedMeterCurGeneration'] = dev.pluginProps['hideZeroSolarUsedMeterCurGeneration']
                pluginGlobal['smappees'][dev.id]['hideSolarUsedMeterAccumGeneration'] = dev.pluginProps['hideSolarUsedMeterAccumGeneration']
                pluginGlobal['smappees'][dev.id]['hideNoChangeInSolarUsedMeterAccumGeneration'] = dev.pluginProps['hideNoChangeInSolarUsedMeterAccumGeneration']

                if "curEnergyLevel" in dev.states:
                    wattStr = "%3.0f Watts" % (pluginGlobal['smappees'][dev.id]['curEnergyLevel'])
                    dev.updateStateOnServer("curEnergyLevel", pluginGlobal['smappees'][dev.id]['curEnergyLevel'], uiValue=wattStr)

                if "accumEnergyTotal" in dev.states:
                    kwhStr = "%3.0f kWh" % (pluginGlobal['smappees'][dev.id]['accumEnergyTotal'])
                    dev.updateStateOnServer("accumEnergyTotal", pluginGlobal['smappees'][dev.id]['accumEnergyTotal'], uiValue=kwhStr)

                dev.updateStateOnServer("smappeeSolarUsedOnline", False, uiValue='offline')

                # if pluginGlobal['pluginInitialised'] == True and self.serviceLocationId != "":
                #     self.sendToSmappeeQueue.put(["GET_CONSUMPTION",str(self.serviceLocationId)])

                autolog(INFO, u"Started '%s' at address [%s]" % (dev.name, dev.address))

            # Initialise internal to plugin smappee solar exported states to default values
            elif dev.deviceTypeId == "smappeeSolarExported":

                autolog(DETAIL, u"SMAPPEE DEV [SOLAR EXPORTED] START smappeeServiceLocationIdToDevId = [%s]" % (pluginGlobal['smappeeServiceLocationIdToDevId']))

                pluginGlobal['config']['supportsSolarExported'] = True

                self.serviceLocationId = str(dev.pluginProps['serviceLocationId'])

                autolog(DETAIL, u"SMAPPEE DEV [SOLAR EXPORTED] START self.serviceLocationId = [%s]" % (self.serviceLocationId))

                self.setSmappeeServiceLocationIdToDevId('ADD_UPDATE', 'smappeeSolarExported', self.serviceLocationId, dev.id, '0', '0')

                autolog(DETAIL, u"SMAPPEE DEV [SOLAR EXPORTED] START smappeeServiceLocationIdToDevId [2] = [%s]" % (pluginGlobal['smappeeServiceLocationIdToDevId']))

                pluginGlobal['smappees'][dev.id] = {}
                pluginGlobal['smappees'][dev.id]['serviceLocationId'] = dev.pluginProps['serviceLocationId']
                pluginGlobal['smappees'][dev.id]['serviceLocationName'] = dev.pluginProps['serviceLocationName']
                pluginGlobal['smappees'][dev.id]['name'] = dev.name
                pluginGlobal['smappees'][dev.id]['electricityCost'] = 0
                pluginGlobal['smappees'][dev.id]['electricityCurrency'] = 0
                pluginGlobal['smappees'][dev.id]['curEnergyLevel'] = 0.0
                pluginGlobal['smappees'][dev.id]['accumEnergyTotal'] = 0.0
                pluginGlobal['smappees'][dev.id]['lastResetSolarExportedUtc'] = 0
                pluginGlobal['smappees'][dev.id]['lastReadingSolarExportedUtc'] = 0
                pluginGlobal['smappees'][dev.id]['lastReadingSolarExported'] = 0.0
                pluginGlobal['smappees'][dev.id]['hideSolarExportedMeterCurGeneration'] = dev.pluginProps['hideSolarExportedMeterCurGeneration']
                pluginGlobal['smappees'][dev.id]['hideZeroSolarExportedMeterCurGeneration'] = dev.pluginProps['hideZeroSolarExportedMeterCurGeneration']
                pluginGlobal['smappees'][dev.id]['hideSolarExportedMeterAccumGeneration'] = dev.pluginProps['hideSolarExportedMeterAccumGeneration']
                pluginGlobal['smappees'][dev.id]['hideNoChangeInSolarExportedMeterAccumGeneration'] = dev.pluginProps['hideNoChangeInSolarExportedMeterAccumGeneration']

                if "curEnergyLevel" in dev.states:
                    wattStr = "%3.0f Watts" % (pluginGlobal['smappees'][dev.id]['curEnergyLevel'])
                    dev.updateStateOnServer("curEnergyLevel", pluginGlobal['smappees'][dev.id]['curEnergyLevel'], uiValue=wattStr)

                if "accumEnergyTotal" in dev.states:
                    kwhStr = "%3.0f kWh" % (pluginGlobal['smappees'][dev.id]['accumEnergyTotal'])
                    dev.updateStateOnServer("accumEnergyTotal", pluginGlobal['smappees'][dev.id]['accumEnergyTotal'], uiValue=kwhStr)

                dev.updateStateOnServer("smappeeSolarExportedOnline", False, uiValue='offline')

                # if pluginGlobal['pluginInitialised'] == True and self.serviceLocationId != "":
                #     self.sendToSmappeeQueue.put(["GET_CONSUMPTION",str(self.serviceLocationId)])

                autolog(INFO, u"Started '%s' at address [%s]" % (dev.name, dev.address))

            # Initialise internal to plugin smappee sensor states to default values
            elif dev.deviceTypeId == "smappeeSensor":

                autolog(DETAIL, u"SMAPPEE DEV [SENSOR] START-A smappeeServiceLocationIdToDevId = [%s]" % (pluginGlobal['smappeeServiceLocationIdToDevId']))

                self.serviceLocationId = str(dev.pluginProps['serviceLocationId'])

                autolog(DETAIL, u"SMAPPEE DEV [SENSOR] START-B self.serviceLocationId = [%s]" % (self.serviceLocationId))

                self.setSmappeeServiceLocationIdToDevId('ADD_UPDATE', 'smappeeSensor', self.serviceLocationId, dev.id,  dev.address, dev.name)

                autolog(DETAIL, u"SMAPPEE DEV [SENSOR] START-C smappeeServiceLocationIdToDevId [2] = [%s]" % (pluginGlobal['smappeeServiceLocationIdToDevId']))

                pluginGlobal['smappees'][dev.id] = {}
                pluginGlobal['smappees'][dev.id]['serviceLocationId'] = dev.pluginProps['serviceLocationId']
                pluginGlobal['smappees'][dev.id]['serviceLocationName'] = dev.pluginProps['serviceLocationName']
                pluginGlobal['smappees'][dev.id]['name'] = dev.name
                pluginGlobal['smappees'][dev.id]['longditude'] = 0
                pluginGlobal['smappees'][dev.id]['latitude'] = 0
                pluginGlobal['smappees'][dev.id]['smappeeUnitCost'] = 0
                pluginGlobal['smappees'][dev.id]['smappeeUnitCurrency'] = 0
                pluginGlobal['smappees'][dev.id]['curEnergyLevel'] = 0.0
                pluginGlobal['smappees'][dev.id]['accumEnergyTotal'] = 0.0
                pluginGlobal['smappees'][dev.id]['dailyTotalCost'] = 0.0
                pluginGlobal['smappees'][dev.id]['lastResetSensorUtc'] = 0
                pluginGlobal['smappees'][dev.id]['lastReadingSensorUtc'] = 0
                pluginGlobal['smappees'][dev.id]['lastReadingSensor'] = 0.0
                pluginGlobal['smappees'][dev.id]['readingsLastUpdated'] = 'Unknown'
                pluginGlobal['smappees'][dev.id]['hideEnergyMeterCurPower'] = dev.pluginProps['hideEnergyMeterCurPower']
                pluginGlobal['smappees'][dev.id]['hideEnergyMeterAccumPower'] = dev.pluginProps['hideEnergyMeterAccumPower']
                pluginGlobal['smappees'][dev.id]['temperature'] = 0.0
                pluginGlobal['smappees'][dev.id]['humidity'] = 0.0
                pluginGlobal['smappees'][dev.id]['batteryLevel'] = 0.0
                pluginGlobal['smappees'][dev.id]['temperatureLastUpdated'] = 'Unknown'
                pluginGlobal['smappees'][dev.id]['humidityLastUpdated'] = 'Unknown'
                pluginGlobal['smappees'][dev.id]['batteryLevelLastUpdated'] = 'Unknown'

                try:
                    pluginGlobal['smappees'][dev.id]['currencyCode'] = dev.pluginProps['currencyCode']
                except:
                    pluginGlobal['smappees'][dev.id]['currencyCode'] = 'UKP'
                try:
                    pluginGlobal['smappees'][dev.id]['dailyStandingCharge'] = float(dev.pluginProps['dailyStandingCharge'])
                except:
                    pluginGlobal['smappees'][dev.id]['dailyStandingCharge'] = 8.88  # To make it obvious there is an error
                try:
                    pluginGlobal['smappees'][dev.id]['units'] = str(dev.pluginProps['units'])
                except:
                    pluginGlobal['smappees'][dev.id]['units'] = 'kWh'
                try:
                    pluginGlobal['smappees'][dev.id]['pulsesPerUnit'] = str(dev.pluginProps['pulsesPerUnit'])
                except:
                    pluginGlobal['smappees'][dev.id]['pulsesPerUnit'] = int(1.0)
                try:
                    pluginGlobal['smappees'][dev.id]['unitCost'] = float(dev.pluginProps['unitCost'])
                except:
                    pluginGlobal['smappees'][dev.id]['unitCost'] = 9.99  # To make it obvious there is an error

                if "readingsLastUpdated" in dev.states:
                    dev.updateStateOnServer("readingsLastUpdated", pluginGlobal['smappees'][dev.id]['readingsLastUpdated'])

                if "temperature" in dev.states:
                    temperatureStr = "%0.1f deg C" % (pluginGlobal['smappees'][dev.id]['temperature'])
                    temperatureReformatted = float("%0.1f" % (pluginGlobal['smappees'][dev.id]['temperature']))
                    dev.updateStateOnServer("temperature", temperatureReformatted, uiValue=temperatureStr)
 
                if "humidity" in dev.states:
                    humidityStr = "%0.1f%%" % (pluginGlobal['smappees'][dev.id]['humidity'])
                    humidityReformatted = float("%0.1f" % (pluginGlobal['smappees'][dev.id]['humidity']))
                    dev.updateStateOnServer("humidity", humidityReformatted, uiValue=humidityStr)
 
                if "batteryLevel" in dev.states:
                    batteryLevelStr = "%0.1f%%" % (pluginGlobal['smappees'][dev.id]['batteryLevel'])
                    batteryLevelReformatted = float("%0.1f" % (pluginGlobal['smappees'][dev.id]['batteryLevel']))
                    dev.updateStateOnServer("batteryLevel", batteryLevelReformatted, uiValue=batteryLevelStr)

                if "temperatureLastUpdated" in dev.states:
                    dev.updateStateOnServer("temperatureLastUpdated", pluginGlobal['smappees'][dev.id]['temperatureLastUpdated'])
 
                if "humidityLastUpdated" in dev.states:
                    dev.updateStateOnServer("humidityLastUpdated", pluginGlobal['smappees'][dev.id]['humidityLastUpdated'])
 
                if "batteryLevelLastUpdated" in dev.states:
                    dev.updateStateOnServer("batteryLevelLastUpdated", pluginGlobal['smappees'][dev.id]['batteryLevelLastUpdated'])

                unitsKey = pluginGlobal['smappees'][dev.id]['units']
                if unitsKey in pluginGlobal['unitTable']:
                    pass
                else:
                    unitsKey = 'default'

                unitsCurrentUnits              = pluginGlobal['unitTable'][unitsKey]['currentUnits'] 
                unitsAccumUnits                = pluginGlobal['unitTable'][unitsKey]['accumUnits'] 
                unitsmeasurementTimeMultiplier = pluginGlobal['unitTable'][unitsKey]['measurementTimeMultiplier']
                unitsformatTotaldivisor        = pluginGlobal['unitTable'][unitsKey]['formatTotaldivisor']
                unitsformatCurrent             = pluginGlobal['unitTable'][unitsKey]['formatCurrent']
                unitsformatCurrentUi           = unitsformatCurrent + u' ' + unitsCurrentUnits
                unitsformatTotal               = pluginGlobal['unitTable'][unitsKey]['formatTotal']
                unitsformatTotalUi             = unitsformatTotal + ' ' + unitsAccumUnits

                if "curEnergyLevel" in dev.states:
                    dataToUpdateStr = str(unitsformatCurrentUi % (pluginGlobal['smappees'][dev.id]['curEnergyLevel']))
                    dev.updateStateOnServer("curEnergyLevel", pluginGlobal['smappees'][dev.id]['curEnergyLevel'], uiValue=dataToUpdateStr)

                if "accumEnergyTotal" in dev.states:
                    dataToUpdateStr = str(unitsformatTotalUi % (pluginGlobal['smappees'][dev.id]['accumEnergyTotal']))
                    dev.updateStateOnServer("accumEnergyTotal", pluginGlobal['smappees'][dev.id]['accumEnergyTotal'], uiValue=dataToUpdateStr)

                try:
                    pluginGlobal['smappees'][dev.id]['hideEnergyMeterAccumPowerCost'] = dev.pluginProps['hideEnergyMeterAccumPowerCost']
                except:
                    pluginGlobal['smappees'][dev.id]['hideEnergyMeterAccumPowerCost'] = False

                dev.updateStateOnServer("smappeeSensorOnline", False, uiValue='offline')

                if  "dailyTotalCost" in dev.states:
                    costStr = "%3.0f" % (pluginGlobal['smappees'][dev.id]['dailyTotalCost'])
                    dev.updateStateOnServer("dailyTotalCost", pluginGlobal['smappees'][dev.id]['dailyTotalCost'], uiValue=costStr)

                if pluginGlobal['pluginInitialised'] == True and self.serviceLocationId != "":
                    self.sendToSmappeeQueue.put(["GET_SENSOR_CONSUMPTION",str(self.serviceLocationId)])

                autolog(INFO, u"Started '%s' at address [%s]" % (dev.name, dev.address))


            elif dev.deviceTypeId == "smappeeAppliance":

                self.serviceLocationId = str(dev.pluginProps['serviceLocationId'])

                self.setSmappeeServiceLocationIdToDevId('ADD_UPDATE', 'smappeeAppliance', self.serviceLocationId, dev.id, dev.address, dev.name)

                pluginGlobal['smappeeAppliances'][dev.id] = {}
                pluginGlobal['smappeeAppliances'][dev.id]['serviceLocationId'] = dev.pluginProps['serviceLocationId']
                pluginGlobal['smappeeAppliances'][dev.id]["datetimeStarted"] = indigo.server.getTime()
                pluginGlobal['smappeeAppliances'][dev.id]['address'] = dev.address
                pluginGlobal['smappeeAppliances'][dev.id]['onOffState'] = 'off'
                pluginGlobal['smappeeAppliances'][dev.id]['onOffStateBool'] = False
                pluginGlobal['smappeeAppliances'][dev.id]['name'] = dev.name
                pluginGlobal['smappeeAppliances'][dev.id]['curEnergyLevel'] = 0.0
                pluginGlobal['smappeeAppliances'][dev.id]['accumEnergyTotal'] = 0.0
                pluginGlobal['smappeeAppliances'][dev.id]['lastResetApplianceUtc'] = 0
                pluginGlobal['smappeeAppliances'][dev.id]['lastReadingApplianceUtc'] = 0
                pluginGlobal['smappeeAppliances'][dev.id]['lastReadingAppliance'] = 0.0

                if "curEnergyLevel" in dev.states:
                    wattStr = "%3.0f Watts" % (pluginGlobal['smappeeAppliances'][dev.id]['curEnergyLevel'])
                    dev.updateStateOnServer("curEnergyLevel", pluginGlobal['smappeeAppliances'][dev.id]['curEnergyLevel'], uiValue=wattStr)

                if "accumEnergyTotal" in dev.states:
                    kwhStr = "%3.0f kWh" % (pluginGlobal['smappeeAppliances'][dev.id]['accumEnergyTotal'])
                    dev.updateStateOnServer("accumEnergyTotal", pluginGlobal['smappeeAppliances'][dev.id]['accumEnergyTotal'], uiValue=kwhStr)

                dev.updateStateOnServer("smappeeApplianceEventStatus", "NONE", uiValue="No Events")
                if float(indigo.server.apiVersion) >= 1.18:
                    dev.updateStateImageOnServer(indigo.kStateImageSel.EnergyMeterOff)

                autolog(INFO, u"Started '%s' at address [%s]" % (dev.name, pluginGlobal['smappeeAppliances'][dev.id]['address']))


            elif dev.deviceTypeId == "smappeeActuator":

                self.serviceLocationId = str(dev.pluginProps['serviceLocationId'])

                self.setSmappeeServiceLocationIdToDevId('ADD_UPDATE', 'smappeeActuator', self.serviceLocationId, dev.id, dev.address, dev.name)

                pluginGlobal['smappeePlugs'][dev.id] = {}
                pluginGlobal['smappeePlugs'][dev.id]["datetimeStarted"] = indigo.server.getTime()
                pluginGlobal['smappeePlugs'][dev.id]['address'] = dev.address
                pluginGlobal['smappeePlugs'][dev.id]['onOffState'] = 'off'
                pluginGlobal['smappeePlugs'][dev.id]['onOffStateBool'] = False
                pluginGlobal['smappeePlugs'][dev.id]['name'] = dev.name

                dev.updateStateOnServer("onOffState", False, uiValue='off')

                autolog(INFO, u"Started '%s' at address [%s]" % (dev.name, pluginGlobal['smappeePlugs'][dev.id]['address']))

            autolog(DETAIL, u"SMAPPEE DEV [%s] [%s] START smappeeServiceLocationIdToDevId = [%s]" % (dev.name, dev.model, pluginGlobal['smappeeServiceLocationIdToDevId']))


        except StandardError, e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            autolog(ERROR, u"deviceStartComm: StandardError detected for '%s' at line '%s' = %s" % (dev.name, exc_tb.tb_lineno,  e))   

        return


    def deviceStopComm(self, dev):
        global pluginGlobal
        autolog(METHOD, u"%s" %  (methodNameForTrace()))  


        pluginGlobal['smappees'][dev.id] = {}

        if dev.deviceTypeId == "smappeeElectricity":
            dev.updateStateOnServer("smappeeElectricityOnline", False, uiValue='Stopped')
            pluginGlobal['config']['supportsElectricity'] = False

        elif dev.deviceTypeId == "smappeeElectricityNet":
            dev.updateStateOnServer("smappeeElectricityNetOnline", False, uiValue='Stopped')
            pluginGlobal['config']['supportsElectricityNet'] = False

        elif dev.deviceTypeId == "smappeeElectricitySaved":
            dev.updateStateOnServer("smappeeElectricitySavedOnline", False, uiValue='Stopped')
            pluginGlobal['config']['supportsElectricitySaved'] = False

        elif dev.deviceTypeId == "smappeeSolar":
            dev.updateStateOnServer("smappeeSolarOnline", False, uiValue='Stopped')
            pluginGlobal['config']['supportsSolar'] = False

        elif dev.deviceTypeId == "smappeeSolarUsed":
            dev.updateStateOnServer("smappeeSolarUsedOnline", False, uiValue='Stopped')
            pluginGlobal['config']['supportsSolarUsed'] = False

        elif dev.deviceTypeId == "smappeeSolarExported":
            dev.updateStateOnServer("smappeeSolarExportedOnline", False, uiValue='Stopped')
            pluginGlobal['config']['supportsSolarExported'] = False

        elif dev.deviceTypeId == "smappeeSensor":
            dev.updateStateOnServer("smappeeSensorOnline", False, uiValue='Stopped')

        elif dev.deviceTypeId == "smappeeAppliance":
            dev.updateStateOnServer("smappeeApplianceEventStatus", 'Stopped')

        elif dev.deviceTypeId == "smappeeActuator":
            dev.updateStateOnServer("onOffState", False, uiValue='stopped')

        serviceLocationId = dev.pluginProps['serviceLocationId']
        self.setSmappeeServiceLocationIdToDevId('STOP', dev.deviceTypeId, serviceLocationId, dev.id, dev.address, dev.name)


        autolog(INFO, u"Stopping '%s'" % (dev.name))

