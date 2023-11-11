import sys
import resource
import logger

# This mini python script is used to determine if a Qt5 GUI application
# can be created without an error.
#
# It is used e.g. for diagnostics output of backintime
# or to check if a system tray icon could be shown...
#
# It is called by "tools.is_Qt5_working()" normally
# but you can also execute it manually via
#     python3 qt5_probing.py

# It works by trying to create a QApplication instance
# Any error indicates that Qt5 is not available or not correctly configured.

# WORK AROUND:
#
# The C++ code of Qt5 ends abruptly with a SIGABRT signal (qFatal macro)
# if a QApplication cannot be instantiated.
# This causes a coredump creation by the python default signal handler
# and the signal handler cannot be disabled since it reacts to a
# non-python low-level signal sent via C/C++.
#
# Even though the coredump message cannot be prevent there is
# workaround to prevent the coredump **file** creation which
# would take too much time just to probe Qt5's availability:
#
#    Use resource.setrlimit() to set resource.RLIMIT_CORE’s soft limit to 0
#
# Note: This does NOT prevent the console output "Aborted (core dumped)"
#       even though no coredump file will be created!
#       You can check that no coredump file was created with the command
#           sudo coredumpctl list -r
#
# More details:
#
# To suppress the creation of coredump file on Linux
# use resource.setrlimit() to set resource.RLIMIT_CORE’s soft limit to 0
# to prevent coredump file creation.
# https://docs.python.org/3.10/library/resource.html#resource.RLIMIT_CORE
# https://docs.python.org/3.10/library/resource.html#resource.setrlimit
# See also the source code of the test.support.SuppressCrashReport() context manager:
#             if self.resource is not None:
#                 try:
#                     self.old_value = self.resource.getrlimit(self.resource.RLIMIT_CORE)
#                     self.resource.setrlimit(self.resource.RLIMIT_CORE,
#                                             (0, self.old_value[1]))
#                 except (ValueError, OSError):
#                     pass
# https://github.com/python/cpython/blob/32718f908cc92c474fd968912368b8a4500bd055/Lib/test/support/__init__.py#L1712-L1718
# and cpython "faulthandler_suppress_crash_report()"
# https://github.com/python/cpython/blob/32718f908cc92c474fd968912368b8a4500bd055/Modules/faulthandler.c#L954
# See "man 2 getrlimit" for more details:
# > RLIMIT_CORE
# >              This  is  the maximum size of a core file (see core(5)) in bytes
# >              that the process may dump.  When 0 no core dump files  are  created
# >              When nonzero, larger dumps are truncated to this size.
# > ...
# > The  soft  limit  is  the value that the kernel enforces for the corresponding resource.
# > The hard limit acts  as  a  ceiling  for  the  soft limit:
# > an  unprivileged process may set only its soft limit to a value
# > in the range from 0 up to the hard limit, and (irreversibly) lower  its
# > hard   limit.    A  privileged  process  (under  Linux:  one  with  the
# > CAP_SYS_RESOURCE capability in the initial user namespace) may make
# > arbitrary changes to either limit value.
#
# Note: The context manager test.support.SuppressCrashReport() is NOT used
#       here since the "test.support" module not public and its API is subject
#        to change without backwards compatibility concerns between releases.

# Work-around to prevent the time-consuming creation of a core dump
old_limits = resource.getrlimit(resource.RLIMIT_CORE)
resource.setrlimit(resource.RLIMIT_CORE, (0, old_limits[1]))

exit_code = 0

try:

    logger.debug(f"{__file__} started... Call args: {str(sys.argv)}")

    from PyQt5 import QtCore
    from PyQt5.QtWidgets import QApplication

    app = QApplication([''])

    exit_code = 1

    # https://doc.qt.io/qt-5/qsystemtrayicon.html#details:
    # > To check whether a system tray is present on the user's desktop,
    # > call the QSystemTrayIcon::isSystemTrayAvailable() static function.
    #
    # This requires a QApplication instance (otherwise Qt5 causes a segfault)
    # which we don't have here so we create it to check if a window manager
    # ("GUI") is active at all (e.g. in headless installations it isn't).
    # See: https://forum.qt.io/topic/3852/issystemtrayavailable-always-crashes-segfault-on-ubuntu-10-10-desktop/6

    from PyQt5.QtWidgets import QSystemTrayIcon
    is_sys_tray_available = QSystemTrayIcon.isSystemTrayAvailable()

    if is_sys_tray_available:
        exit_code = 2

    logger.debug(f"isSystemTrayAvailable for Qt5: {is_sys_tray_available}")

except Exception as e:
    logger.debug(f"Error: {repr(e)}")

logger.debug(f"{__file__} is terminating normally (exit code: {exit_code})")

# Exit codes:
# 0 = no Qt5 GUI available
# 1 = only Qt5 GUI available (no sys tray support)
# 2 = Qt5 GUI and sys tray available
# 134 (-6 as signed byte exit code type!) = SIGABRT caught by python
#     ("interrupted by signal 6: SIGABRT").
#     This is most probably caused by a misconfigured Qt5...
#     So the interpretation is the same as exit code 0.
sys.exit(exit_code)

