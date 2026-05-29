import gdb  # type: ignore

class DaqTrackedCount(gdb.Command):
    def __init__(self):
        super().__init__("daq-tracked-count", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        result = gdb.parse_and_eval("(size_t)daqGetTrackedObjectCount()")
        if result is not None:
            print("Tracked objects: {}".format(int(result)))

class DaqIsTracking(gdb.Command):
    def __init__(self):
        super().__init__("daq-is-tracking", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        result = gdb.parse_and_eval("(bool)daqIsTrackingObjects()")
        if result is not None:
            print("Tracking enabled: {}".format(bool(result)))

class DaqPrintTracked(gdb.Command):
    def __init__(self):
        super().__init__("daq-print-tracked", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        result = gdb.parse_and_eval("(void)daqPrintTrackedObjects()")
        if result is not None:
            print("Tracked objects printed.")

DaqTrackedCount()
DaqIsTracking()
DaqPrintTracked()