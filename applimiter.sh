#!/bin/bash

# This is a shim script to correctly launch the AppLimiter application,
# handling both regular and sudo execution.

# The absolute path to the AppLimiter installation directory.
INSTALL_DIR="/opt/AppLimiter"

# Set the PYTHONPATH environment variable so that Python knows where to find our package.
# Then, execute the 'applimiter.main' module using python's -m flag.
# "$@" ensures that all arguments passed to this script (e.g., "status", "add --name ...")
# are correctly forwarded to the python command.

export PYTHONPATH="${INSTALL_DIR}"

# Use exec to replace the shell script process with the python process.
# This is slightly more efficient.
exec python3 -m applimiter.main "$@"