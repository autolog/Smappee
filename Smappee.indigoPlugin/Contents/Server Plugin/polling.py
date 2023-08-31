#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# Smappee - Polling © Autolog 2018-2023
#

# noinspection PyUnresolvedReferences
# ============================== Native Imports ===============================
import logging
import sys
import threading
import traceback

# ============================== Custom Imports ===============================
try:
    import indigo  # noqa
except ImportError:
    pass

# ============================== Plugin Imports ===============================
from constants import *


class ThreadPolling(threading.Thread):

    def __init__(self, pluginGlobals, event):

        threading.Thread.__init__(self)

        self.globals = pluginGlobals
        self.pollStop = event

        self.previousPollingSeconds = self.globals[POLLING][SECONDS]

        self.globals[POLLING][THREAD_ACTIVE] = True

        self.pollingLogger = logging.getLogger("Plugin.polling")

        self.pollingLogger.info(f"Initialising to poll at {self.globals[POLLING][SECONDS]} second intervals")

    def exception_handler(self, exception_error_message, log_failing_statement):
        filename, line_number, method, statement = traceback.extract_tb(sys.exc_info()[2])[-1]
        module = filename.split('/')
        log_message = f"'{exception_error_message}' in module '{module[-1]}', method '{method}'"
        if log_failing_statement:
            log_message = log_message + f"\n   Failing statement [line {line_number}]: '{statement}'"
        else:
            log_message = log_message + f" at line {line_number}"
        self.pollingLogger.error(log_message)

    def run(self):
        try:  
            while True:
                self.pollStop.wait(self.globals[POLLING][SECONDS])

                if self.pollStop.isSet():
                    if self.globals[POLLING][FORCE_THREAD_END]:
                        break
                    else:
                        self.pollStop.clear()

                self.pollingLogger.debug(f"Start of While Loop ...")  # Message not quite at start as debug settings need to be checked first and also whether thread is being stopped.

                # Check if polling seconds interval has changed and if so set accordingly
                if self.globals[POLLING][SECONDS] != self.previousPollingSeconds:
                    self.pollingLogger.info(f"Changing to poll at %i second intervals (was %i seconds)" % (self.globals[POLLING][SECONDS], self.previousPollingSeconds))
                    self.previousPollingSeconds = self.globals[POLLING][SECONDS]

                self.pollingLogger.debug(f"Polling at %i second intervals" % (self.globals[POLLING][SECONDS]))

                for serviceLocationId, serviceLocationDetails in self.globals[SMAPPEE_SERVICE_LOCATION_ID_TO_DEV_ID].items():
                    pass
                    self.globals[QUEUES][SEND_TO_SMAPPEE].put([COMMAND_GET_CONSUMPTION, str(serviceLocationId)])
                    self.globals[QUEUES][SEND_TO_SMAPPEE].put([COMMAND_GET_EVENTS, str(serviceLocationId)])
                    self.globals[QUEUES][SEND_TO_SMAPPEE].put([COMMAND_GET_SENSOR_CONSUMPTION, str(serviceLocationId)])

            self.pollingLogger.debug(f"Polling thread ending: pollStop.isSet={self.pollStop.isSet()}, forceThreadEnd={self.globals[POLLING][FORCE_THREAD_END]},"
                                     f" newSeconds={self.globals[POLLING][SECONDS]}, previousSeconds={self.previousPollingSeconds}")

        except Exception as exception_error:
            self.exception_handler(exception_error, True)  # Log error and display failing statement

        self.globals[POLLING][THREAD_ACTIVE] = False
