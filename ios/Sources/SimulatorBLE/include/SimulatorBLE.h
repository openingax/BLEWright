#import <Foundation/Foundation.h>
/// Install once, before constructing CBCentralManager. Returns NO outside Simulator Debug.
/// Linking with -ObjC also installs automatically when BLEWRIGHT_ENABLE=1 is set.
FOUNDATION_EXPORT BOOL BWSimulatorBLEInstall(void);
