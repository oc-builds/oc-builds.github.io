# ============================================================================
# File        : Makefile
# Author      : Sanjay Chauhan
# Date        : 2026-05-31
# Description : CS499 Enhancement Two rebuild of the CS300 ABCU Course Advisor.
#               Builds the advisor binary with C++17 and the full warning
#               set. Use `make` to build; `make clean` to remove artifacts.
# ============================================================================

CXX      := g++
CXXFLAGS := -std=c++17 -Wall -Wextra -Wpedantic -O2
TARGET   := advisor
SOURCES  := $(wildcard *.cpp)

.PHONY: all clean

all: $(TARGET)

$(TARGET): $(SOURCES)
	$(CXX) $(CXXFLAGS) $(SOURCES) -o $(TARGET)

clean:
	rm -f $(TARGET)
