#!/bin/bash
# Build script for GuideLLM C/C++ API

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Building GuideLLM C/C++ API..."

# Get Python configuration
PYTHON_CONFIG=$(which python3-config 2>/dev/null || echo "python3-config")
if ! command -v $PYTHON_CONFIG &> /dev/null; then
    echo "Error: python3-config not found. Please install Python development headers."
    exit 1
fi

# Get Python version for library name
PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PYTHON_LIB_NAME="python${PYTHON_VERSION}"

# Create build directory
mkdir -p build
cd build

echo "Compiling C wrapper library..."

# Compile the C wrapper as a shared library
gcc -shared -fPIC \
    -I"$SCRIPT_DIR/include" \
    $($PYTHON_CONFIG --includes) \
    -o libguidellm_c_wrapper.so \
    "$SCRIPT_DIR/src/guidellm/c_api/guidellm_c_wrapper.c" \
    $($PYTHON_CONFIG --ldflags) \
    -l$PYTHON_LIB_NAME

if [ $? -eq 0 ]; then
    echo "Successfully built libguidellm_c_wrapper.so"
    echo "Library location: $SCRIPT_DIR/build/libguidellm_c_wrapper.so"
    echo ""
    echo "To use the library, add to your compile command:"
    echo "  -L$SCRIPT_DIR/build -lguidellm_c_wrapper"
    echo "  -I$SCRIPT_DIR/include"
else
    echo "Error: Failed to build C wrapper library"
    exit 1
fi

echo ""
echo "Note: The Python C extension (guidellm_c_api) is built automatically"
echo "      when you install the package with: pip install -e ."

