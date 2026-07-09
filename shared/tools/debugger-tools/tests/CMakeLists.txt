opendaq_set_cmake_folder_context(TARGET_FOLDER_NAME)
set(MODULE_NAME gdb_printers)
set(TEST_APP test_${MODULE_NAME})


set(TARGET_APP ${TEST_APP}_target)

add_executable(${TARGET_APP} test_target.cpp)
target_compile_definitions(${TARGET_APP} PRIVATE ${OPENDAQ_TEST_COMPILE_DEFINES})
set_target_properties(${TARGET_APP} PROPERTIES DEBUG_POSTFIX _debug)

target_link_libraries(${TARGET_APP} PRIVATE ${SDK_TARGET_NAMESPACE}::opendaq)

target_compile_options(${TARGET_APP} PRIVATE -g -O0)

if (Python_EXECUTABLE)
    set(GDB_PRINTERS_PYTHON ${Python_EXECUTABLE})
else ()
    find_package(Python3 COMPONENTS Interpreter)
    set(GDB_PRINTERS_PYTHON ${Python3_EXECUTABLE})
endif ()
find_program(GDB_EXECUTABLE gdb)

if (GDB_PRINTERS_PYTHON AND GDB_EXECUTABLE)
    add_test(NAME ${TEST_APP}
        COMMAND ${GDB_PRINTERS_PYTHON} ${CMAKE_CURRENT_SOURCE_DIR}/test_printers.py
        WORKING_DIRECTORY $<TARGET_FILE_DIR:${TARGET_APP}>
    )
    set_tests_properties(${TEST_APP} PROPERTIES LABELS "gdb_printers")
else ()
    message(STATUS "gdb printer tests not registered (python3 or gdb not found)")
endif ()
