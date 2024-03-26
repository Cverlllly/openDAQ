//------------------------------------------------------------------------------
// <auto-generated>
//     This code was generated by a tool.
//
//     Changes to this file may cause incorrect behavior and will be lost if
//     the code is regenerated.
//
//     RTGen (PythonGenerator).
// </auto-generated>
//------------------------------------------------------------------------------

/*
 * Copyright 2022-2024 Blueberry d.o.o.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

#include "py_opendaq/py_opendaq.h"
#include "py_core_types/py_converter.h"

PyDaqIntf<daq::ILoggerSink, daq::IBaseObject> declareILoggerSink(pybind11::module_ m)
{
    py::enum_<daq::LogLevel>(m, "LogLevel")
        .value("Trace", daq::LogLevel::Trace)
        .value("Debug", daq::LogLevel::Debug)
        .value("Info", daq::LogLevel::Info)
        .value("Warn", daq::LogLevel::Warn)
        .value("Error", daq::LogLevel::Error)
        .value("Critical", daq::LogLevel::Critical)
        .value("Off", daq::LogLevel::Off)
        .value("Default", daq::LogLevel::Default);

    return wrapInterface<daq::ILoggerSink, daq::IBaseObject>(m, "ILoggerSink");
}

void defineILoggerSink(pybind11::module_ m, PyDaqIntf<daq::ILoggerSink, daq::IBaseObject> cls)
{
    cls.doc() = "Represents the object that actually writes the log messages to the target. Each Logger Sink is responsible for only single target: file, console etc.";

    m.def("StdErrLoggerSink", &daq::StdErrLoggerSink_Create);
    m.def("StdOutLoggerSink", &daq::StdOutLoggerSink_Create);
    m.def("RotatingFileLoggerSink", &daq::RotatingFileLoggerSink_Create);
    m.def("BasicFileLoggerSink", &daq::BasicFileLoggerSink_Create);
#ifdef _WIN32
    m.def("WinDebugLoggerSink", &daq::WinDebugLoggerSink_Create);
#endif
    m.def("LastMessageLoggerSink", &daq::LastMessageLoggerSink_Create);

    cls.def_property("level",
        [](daq::ILoggerSink *object)
        {
            const auto objectPtr = daq::LoggerSinkPtr::Borrow(object);
            return objectPtr.getLevel();
        },
        [](daq::ILoggerSink *object, daq::LogLevel level)
        {
            const auto objectPtr = daq::LoggerSinkPtr::Borrow(object);
            objectPtr.setLevel(level);
        },
        "Gets the minimal severity level of messages to be written to the target. / Sets the minimal severity level of messages to be written to the target.");
    cls.def("should_log",
        [](daq::ILoggerSink *object, daq::LogLevel level)
        {
            const auto objectPtr = daq::LoggerSinkPtr::Borrow(object);
            return objectPtr.shouldLog(level);
        },
        py::arg("level"),
        "Checks whether the messages with given log severity level will be written to the target or not.");
    cls.def_property("pattern",
        nullptr,
        [](daq::ILoggerSink *object, const std::string& pattern)
        {
            const auto objectPtr = daq::LoggerSinkPtr::Borrow(object);
            objectPtr.setPattern(pattern);
        },
        "Sets the custom formatter pattern for the sink.");
    cls.def("flush",
        [](daq::ILoggerSink *object)
        {
            const auto objectPtr = daq::LoggerSinkPtr::Borrow(object);
            objectPtr.flush();
        },
        "Triggers writing out the messages from temporary buffers to the target.");
}
