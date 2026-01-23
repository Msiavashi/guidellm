# Makefile for building C++ example
# This assumes the C wrapper library is built and installed

CXX = g++
CXXFLAGS = -std=c++11 -Wall -Wextra
INCLUDES = -I../include
LDFLAGS = -L../build -lguidellm_c_wrapper -lpython3.12 -lm

# Adjust Python version and paths as needed
PYTHON_VERSION = $(shell python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
PYTHON_CONFIG = python3-config

# Get Python include and library paths
PYTHON_INCLUDES = $(shell $(PYTHON_CONFIG) --includes)
PYTHON_LDFLAGS = $(shell $(PYTHON_CONFIG) --ldflags)

# For now, we'll link against Python directly since the wrapper uses Python C API
CXXFLAGS += $(PYTHON_INCLUDES)
LDFLAGS += $(PYTHON_LDFLAGS)

TARGET = cpp_example
SOURCE = cpp_example.cpp

all: $(TARGET)

$(TARGET): $(SOURCE)
	$(CXX) $(CXXFLAGS) $(INCLUDES) -o $(TARGET) $(SOURCE) $(LDFLAGS)

clean:
	rm -f $(TARGET)

.PHONY: all clean

