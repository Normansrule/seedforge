# Host build of the Uno controller core + unit tests (no Arduino needed).
CXX ?= g++
CXXFLAGS ?= -std=c++17 -O1 -g -Wall -Wextra -Werror -Wno-unused-parameter
SRC := ../../firmware/arduino/seedforge_core/src
CORE := $(SRC)/sf_protocol.cpp $(SRC)/sf_motion.cpp $(SRC)/sf_controller.cpp
BUILD := build

all: test

$(BUILD):
	mkdir -p $(BUILD)

$(BUILD)/test_core: test_core.cpp plant.h $(CORE) $(wildcard $(SRC)/*.h) | $(BUILD)
	$(CXX) $(CXXFLAGS) -fsanitize=address,undefined -o $@ test_core.cpp $(CORE)

$(BUILD)/sim_core: sim_core.cpp plant.h $(CORE) $(wildcard $(SRC)/*.h) | $(BUILD)
	$(CXX) $(CXXFLAGS) -o $@ sim_core.cpp $(CORE)

test: $(BUILD)/test_core $(BUILD)/sim_core
	./$(BUILD)/test_core

clean:
	rm -rf $(BUILD)

.PHONY: all test clean
