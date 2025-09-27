# Queue Manager JavaScript 500 Error Fix

## Problem
The Queue Manager was returning a 500 Internal Server Error when trying to load `queue_manager.js`.

## Root Cause
The HTML file (`web/index.html`) was using relative paths to load JavaScript and CSS files:
```html
<script src="queue_manager.js"></script>
<link rel="stylesheet" href="styles.css">
```

However, the web server routes were set up to serve files through the `/extensions/comfyui-queue-manager/` path.

## Solution
Updated the HTML file to use absolute paths that match the server route configuration:

### Before:
```html
<link rel="stylesheet" href="styles.css">
<script src="queue_manager.js"></script>
```

### After:
```html
<link rel="stylesheet" href="/extensions/comfyui-queue-manager/styles.css">
<script src="/extensions/comfyui-queue-manager/queue_manager.js"></script>
```

## Additional Improvements Made

1. **Enhanced Error Handling**: Added better error handling in the web route server to catch and log different types of errors:
   - Unicode decode errors
   - File size limits (10MB max)
   - OS errors
   - Unexpected errors

2. **Debug Logging**: Added debug logging to track file serving requests:
   - File path resolution
   - File existence checks
   - File size information

3. **Route Registration**: Improved the route registration process to handle cases where ComfyUI isn't fully initialized yet.

## Files Modified

1. `web/index.html` - Fixed resource paths
2. `__init__.py` - Enhanced error handling and logging
3. `web/test.html` - Created test file with correct paths
4. `web/queue_manager_simple.js` - Created simplified version for testing

## Testing

The fix can be tested by:
1. Loading the Queue Manager through ComfyUI's menu
2. Checking browser developer tools for successful resource loading
3. Verifying no 500 errors in the network tab

## Prevention

To prevent similar issues in the future:
- Always use absolute paths for resources in web extensions
- Test resource loading in the actual ComfyUI environment
- Use the `/extensions/{extension-name}/` path pattern for all resources