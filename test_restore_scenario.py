#!/usr/bin/env python3
"""
Test script to simulate the exact restore scenario that was failing.
"""
import sys
import os

# Add the common directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'common'))

class MockConfig:
    """Mock config object to simulate the restore dialog scenario."""
    def __init__(self, xWindowId):
        self.xWindowId = xWindowId
        self.inhibitCookie = None

def test_restore_scenario():
    """Test the exact scenario from restoredialog.py line 82."""
    try:
        import tools
        
        # Simulate the problematic config with the X Window ID from the error
        config = MockConfig(xWindowId=527453920)
        
        print(f"Simulating restore dialog with X Window ID: {config.xWindowId}")
        
        # This is the exact line that was failing in restoredialog.py:82
        config.inhibitCookie = tools.inhibitSuspend(
            toplevel_xid=config.xWindowId, 
            reason='restoring'
        )
        
        if config.inhibitCookie:
            print("✓ Restore dialog inhibitSuspend call succeeded!")
            cookie, bus, dbus_props = config.inhibitCookie
            print(f"  Cookie: {cookie}")
            
            # Clean up
            tools.unInhibitSuspend(cookie, bus, dbus_props)
            print("✓ Cleanup successful!")
        else:
            print("⚠ inhibitSuspend returned None (expected if no dbus available)")
            
        print("\n✓ Restore scenario test completed successfully!")
        return True
        
    except Exception as e:
        print(f"✗ Restore scenario test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_restore_scenario()
    sys.exit(0 if success else 1)
