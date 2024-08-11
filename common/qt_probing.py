import os
import sys
import resource
import logger

logger.openlog()

# from tools import isRoot

# This mini python script is used to determine if a Qt GUI application
# can be created without an error.
#
# It is used e.g. for diagnostics output of backintime
# or to check if a system tray icon could be shown...
#
# It is called by "tools.is_Qt_working()" normally
# but you can also execute it manually via
#     python3 qt_probing.py

# It works by trying to create a QApplication instance
# Any error indicates that Qt is not available or not correctly configured.

# WORK AROUND:
#
# The C++ code of Qt ends abruptly with a SIGABRT signal (qFatal macro)
# if a QApplication cannot be instantiated.
# This causes a coredump creation by the python default signal handler
# and the signal handler cannot be disabled since it reacts to a
# non-python low-level signal sent via C/C++.
#
# Even though the coredump message cannot be prevented there is
# workaround to prevent the coredump **file** creation which
# would take too much time just to probe Qt's availability:
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

    if "--debug" in sys.argv:  # HACK: Minimal arg parsing to enable debug-level logging
        logger.DEBUG = True

    logger.debug(f"{__file__} started... Call args: {str(sys.argv)}")
    logger.debug(f"Display system: {os.environ.get('XDG_SESSION_TYPE', '($XDG_SESSION_TYPE is not set)')}")
    logger.debug(f"XDG_RUNTIME_DIR={os.environ.get('XDG_RUNTIME_DIR', '($XDG_RUNTIME_DIR is not set)')}")
    logger.debug(f"XAUTHORITY={os.environ.get('XAUTHORITY', '($XAUTHORITY is not set)')}")
    logger.debug(f"QT_QPA_PLATFORM={os.environ.get('QT_QPA_PLATFORM', '($QT_QPA_PLATFORM is not set)')}")

    logger.debug(f"Current euid: {os.geteuid()}")
    # Jan 25, 2024 Not enabled but just documented here since this "fix" is a hack (assumes hard-coded UID 1000 to be always correct). But it works in 99 % of installations
    # if isRoot():
    #     logger.debug("Changing euid from root to user as work-around for #1592 (qt_probing hangs in root cron job)")
    #     # Fix inspired by
    #     # https://stackoverflow.com/questions/71425861/connecting-to-user-dbus-as-root
    #     os.seteuid(1000)
    #     logger.debug(f"New euid: {os.geteuid()}")

    # pylint: disable-next=unused-import
    from PyQt6 import QtCore
    from PyQt6.QtWidgets import QApplication

    app = QApplication([''])

    exit_code = 1

    # https://doc.qt.io/qt-5/qsystemtrayicon.html#details:
    # > To check whether a system tray is present on the user's desktop,
    # > call the QSystemTrayIcon::isSystemTrayAvailable() static function.
    #
    # This requires a QApplication instance (otherwise Qt causes a segfault)
    # which we don't have here so we create it to check if a window manager
    # ("GUI") is active at all (e.g. in headless installations it isn't).
    # See: https://forum.qt.io/topic/3852/issystemtrayavailable-always-crashes-segfault-on-ubuntu-10-10-desktop/6

    from PyQt6.QtWidgets import QSystemTrayIcon
    is_sys_tray_available = QSystemTrayIcon.isSystemTrayAvailable()

    if is_sys_tray_available:
        exit_code = 2

    logger.debug(f"isSystemTrayAvailable for Qt: {is_sys_tray_available}")

except Exception as e:
    logger.debug(f"Error: {repr(e)}")

logger.debug(f"{__file__} is terminating normally (exit code: {exit_code})")

# Exit codes:
# 0 = no Qt GUI available
# 1 = only Qt GUI available (no sys tray support)
# 2 = Qt GUI and sys tray available
# 134 (-6 as signed byte exit code type!) = SIGABRT caught by python
#     ("interrupted by signal 6: SIGABRT").
#     This is most probably caused by a misconfigured Qt...
#     So the interpretation is the same as exit code 0.
sys.exit(exit_code)
