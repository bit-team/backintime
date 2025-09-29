#!/usr/bin/env python3
"""
Test script to verify the UInt32 overflow fix in inhibitSuspend function.
"""
import sys
import os

# Add the common directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'common'))

try:
    import tools
    
    # Test with the problematic value from the error report
    problematic_xid = 527453920
    print(f"Testing with X Window ID: {problematic_xid}")
    
    # This should not crash anymore
    result = tools.inhibitSuspend(
        app_id='test_backintime',
        toplevel_xid=problematic_xid,
        reason='testing fix'
    )
    
    if result:
        print("✓ inhibitSuspend succeeded!")
        cookie, bus, dbus_props = result
        print(f"  Cookie: {cookie}")
        
        # Clean up
        tools.unInhibitSuspend(cookie, bus, dbus_props)
        print("✓ unInhibitSuspend succeeded!")
    else:
        print("⚠ inhibitSuspend returned None (expected if no dbus available)")
        
    # Test with an even larger value that definitely exceeds UInt32
    large_xid = 5000000000  # > 4294967295
    print(f"\nTesting with large X Window ID: {large_xid}")
    
    result = tools.inhibitSuspend(
        app_id='test_backintime',
        toplevel_xid=large_xid,
        reason='testing large value'
    )
    
    if result:
        print("✓ inhibitSuspend with large value succeeded!")
        cookie, bus, dbus_props = result
        tools.unInhibitSuspend(cookie, bus, dbus_props)
    else:
        print("⚠ inhibitSuspend with large value returned None")
        
    print("\n✓ All tests completed without crashes!")
    
except Exception as e:
    print(f"✗ Test failed with error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
