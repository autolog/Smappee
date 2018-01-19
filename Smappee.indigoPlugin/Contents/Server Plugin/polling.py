#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# Smappee - Polling © Autolog 2018
#

try:
    import indigo
except ImportError, e:
    pass

import logging
import sys
import threading
import time


class ThreadPolling(threading.Thread):

    def __init__(self, pluginGlobals, event):

        threading.Thread.__init__(self)

        self.globals = pluginGlobals
        self.pollStop = event

        self.previousPollingSeconds = self.globals['polling']['seconds']

        self.globals['polling']['threadActive'] = True

        self.pollingLogger = logging.getLogger("Plugin.polling")
        self.pollingLogger.setLevel(self.globals['debug']['polling'])

        self.methodTracer = logging.getLogger("Plugin.method")  
        self.methodTracer.setLevel(self.globals['debug']['methodTrace'])

        self.pollingLogger.info(u"Initialising to poll at %i second intervals" % (self.globals['polling']['seconds']))  
        self.pollingLogger.debug(u"debug Polling = %s [%s], debug MethodTrace = %s [%s]" % (self.globals['debug']['polling'], 
                                                                                          type(self.globals['debug']['polling']),
                                                                                          self.globals['debug']['methodTrace'],
                                                                                          type(self.globals['debug']['methodTrace'])))
    def run(self):
        try:  
            self.methodTracer.threaddebug(u"ThreadPolling")
            self.pollingLogger.info(u"Smappee Polling thread now running")
            
            while True:
                self.pollStop.wait(self.globals['polling']['seconds'])

                if self.pollStop.isSet():
                    if self.globals['polling']['forceThreadEnd']:
                        break
                    else:
                        self.pollStop.clear()

                # Check if monitoring / debug options have changed and if so set accordingly
                if self.globals['debug']['previous']['polling'] != self.globals['debug']['polling']:
                    self.globals['debug']['previous']['polling'] = self.globals['debug']['polling']
                    self.pollingLogger.setLevel(self.globals['debug']['polling'])
                if self.globals['debug']['previous']['methodTrace'] != self.globals['debug']['methodTrace']:
                    self.globals['debug']['previous']['methodTrace'] = self.globals['debug']['methodTrace']
                    self.pollingLogger.setLevel(self.globals['debug']['methodTrace'])

                self.pollingLogger.debug(u"Start of While Loop ...")  # Message not quite at start as debug settings need to be checked first and also whether thread is being stopped.

                # Check if polling seconds interval has changed and if so set accordingly
                if self.globals['polling']['seconds'] != self.previousPollingSeconds:
                    self.pollingLogger.info(u"Changing to poll at %i second intervals (was %i seconds)" % (self.globals['polling']['seconds'], self.previousPollingSeconds))  
                    self.previousPollingSeconds = self.globals['polling']['seconds']

                self.pollingLogger.debug(u"Polling at %i second intervals" % (self.globals['polling']['seconds']))

                for serviceLocationId, serviceLocationDetails in self.globals['smappeeServiceLocationIdToDevId'].iteritems():
                    self.globals['queues']['sendToSmappee'].put(["GET_CONSUMPTION", str(serviceLocationId)])
                    self.globals['queues']['sendToSmappee'].put(["GET_EVENTS", str(serviceLocationId)])
                    self.globals['queues']['sendToSmappee'].put(["GET_SENSOR_CONSUMPTION", str(serviceLocationId)])

            self.pollingLogger.debug(u"Polling thread ending: pollStop.isSet={}, forceThreadEnd={}, newSeconds={}, previousSeconds={} ".format(self.pollStop.isSet(), self.globals['polling']['forceThreadEnd'], self.globals['polling']['seconds'], self.previousPollingSeconds))

        except StandardError, e:
            self.pollingLogger.error(u"StandardError detected during Polling. Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))

        self.globals['polling']['threadActive'] = False
