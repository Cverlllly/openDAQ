import os
import re
import subprocess
import sys
import tempfile
import traceback
from pathlib import Path

try:
    import pytest  # type: ignore
except ImportError:
    pytest = None

TESTS_DIR = Path(__file__).resolve().parent
PRINTERS_PY = TESTS_DIR.parent / "gdb_printers.py"
REPO_ROOT = TESTS_DIR.parents[3]
TARGET_ENV = "OPENDAQ_GDB_TEST_TARGET"

VARIABLES = [
    "str", "emptyStr", "intVal", "negIntVal", "floatVal",
    "boolTrue", "boolFalse", "ratio", "complexVal", "complexNeg",
    "binData", "nullStr", "rawStr",
    "strList", "intList", "emptyList", "dict", "emptyDict",
    "enumVal", "structVal", "propObj",
]

DEEP_VARIABLES = ["strList", "dict", "structVal", "propObj", "enumVal"]


# MARK: GDB SESSION

def _find_target():
    env = os.environ.get(TARGET_ENV)
    if env:
        return Path(env)
    hits = sorted(Path.cwd().glob("test_gdb_printers_target*"))
    if hits:
        return hits[-1]
    for pattern in ("build/*/bin", "build/*/*/bin",
                    "build/*/*/*/bin", "build/*/*/*/*/bin"):
        hits = sorted(REPO_ROOT.glob(pattern + "/test_gdb_printers_target*"))
        if hits:
            return hits[-1]
    return None


def _gdb_commands():
    lines = [
        "set pagination off",
        "set confirm off",
        "set print pretty on",
        "set print object on",
        "source {}".format(PRINTERS_PY),
        "break breakpoint_here",
        "run",
        "up",
        "set print max-depth 3",
    ]
    for var in VARIABLES:
        lines.append("echo \\n###{}\\n".format(var))
        lines.append("print {}".format(var))
    lines.append("set print max-depth 6")
    for var in DEEP_VARIABLES:
        lines.append("echo \\n###{}_deep\\n".format(var))
        lines.append("print {}".format(var))
    lines.append("echo \\n###END\\n")
    return "\n".join(lines) + "\n"


def _parse_sections(output):
    sections = {}
    current = None
    buf = []
    for line in output.splitlines():
        if line.startswith("###"):
            if current is not None:
                sections[current] = "\n".join(buf)
            current = line[3:].strip()
            buf = []
        elif current is not None:
            buf.append(line)
    if current is not None:
        sections[current] = "\n".join(buf)
    return sections


def _run_gdb(target_bin):
    with tempfile.NamedTemporaryFile("w", suffix=".gdb", delete=False) as f:
        f.write(_gdb_commands())
        cmd_file = f.name
    try:
        res = subprocess.run(
            ["gdb", "-batch", "-nx", "-x", cmd_file, str(target_bin)],
            capture_output=True, text=True, timeout=600)
    finally:
        os.unlink(cmd_file)

    sections = _parse_sections(res.stdout)
    if "END" not in sections:
        raise RuntimeError(
            "gdb run did not finish.\nstdout:\n{}\nstderr:\n{}".format(
                res.stdout[-4000:], res.stderr[-4000:]))
    if "Traceback" in res.stderr:
        raise RuntimeError("python error inside gdb:\n" + res.stderr[-4000:])
    return sections


_sections_cache = None


def _printer_output():
    global _sections_cache
    if _sections_cache is None:
        target = _find_target()
        if target is None or not target.exists():
            msg = ("test target binary not found - configure the build with "
                   "-DOPENDAQ_ENABLE_GDB_PRETTY_PRINTING_TESTS=ON, build the "
                   "test_gdb_printers_target target, or set ${}".format(TARGET_ENV))
            if pytest is not None:
                pytest.skip(msg)
            raise RuntimeError(msg)
        _sections_cache = _run_gdb(target)
    return _sections_cache


if pytest is not None:
    @pytest.fixture(scope="session")
    def printer_output():
        return _printer_output()


# MARK: SCALARS

def test_string(printer_output):
    out = printer_output["str"]
    assert '"hello" [String]' in out
    assert 'Value = "hello"' in out
    assert "Type = String" in out


def test_empty_string(printer_output):
    out = printer_output["emptyStr"]
    assert '"" [String]' in out


def test_int(printer_output):
    out = printer_output["intVal"]
    assert "42 [Int]" in out
    assert "Value = 42" in out


def test_negative_int(printer_output):
    assert "-7 [Int]" in printer_output["negIntVal"]


def test_float(printer_output):
    out = printer_output["floatVal"]
    assert "3.5 [Float]" in out
    assert "Value = 3.5" in out


def test_bool_true(printer_output):
    assert "true [Bool]" in printer_output["boolTrue"]


def test_bool_false(printer_output):
    assert "false [Bool]" in printer_output["boolFalse"]


def test_ratio(printer_output):
    out = printer_output["ratio"]
    assert "1/2 [Ratio]" in out
    assert "Numerator = 1" in out
    assert "Denominator = 2" in out


def test_complex_positive_imag(printer_output):
    assert "3.0 + 4.0i [ComplexNumber]" in printer_output["complexVal"]


def test_complex_negative_imag(printer_output):
    assert "1.5 - 2.5i [ComplexNumber]" in printer_output["complexNeg"]


def test_binary_data(printer_output):
    out = printer_output["binData"]
    assert "16 bytes [BinaryData]" in out
    assert "Size = 16" in out


# MARK: SMART POINTER WRAPPER

def test_smart_pointer_children(printer_output):
    out = printer_output["str"]
    assert "Borrowed = false" in out
    assert "Object =" in out


def test_null_smart_pointer(printer_output):
    out = printer_output["nullStr"]
    assert out.lstrip().startswith("$") and "= null" in out.splitlines()[0]
    assert "Object = 0x0" in out


def test_common_children_present(printer_output):
    out = printer_output["intVal"]
    assert "RefCount = " in out
    assert re.search(r"Address = 0x[0-9a-f]+", out)
    assert "Raw = " in out


def test_hidden_fields_not_shown_at_top_level(printer_output):
    out = printer_output["intVal"]
    top = out.split("Raw =")[0]
    assert "disposeCalled" not in top
    assert "GuidSource" not in top


# MARK: RAW INTERFACE POINTER (NON SMART-POINTER PATH)

def test_raw_interface_pointer(printer_output):
    out = printer_output["rawStr"]
    assert '"hello" [String]' in out
    assert "Borrowed" not in out


# MARK: CONTAINERS

def test_list_of_strings(printer_output):
    out = printer_output["strList"]
    assert "[List<String>]" in out
    assert "Items = {3 items}" in out


def test_list_items_expanded(printer_output):
    out = printer_output["strList_deep"]
    for item in ('"one" [String]', '"two" [String]', '"three" [String]'):
        assert item in out


def test_list_of_ints(printer_output):
    out = printer_output["intList"]
    assert "[List<Int>]" in out
    assert "Items = {2 items}" in out


def test_empty_list(printer_output):
    out = printer_output["emptyList"]
    assert "[List]" in out


def test_dict(printer_output):
    out = printer_output["dict"]
    assert "[Dict<String, Int>]" in out
    assert "Items = {2 items}" in out


def test_dict_entries_expanded(printer_output):
    out = printer_output["dict_deep"]
    assert re.search(r'Key = "a" \[String\]', out)
    assert re.search(r"Value = 1 \[Int\]", out)
    assert re.search(r'Key = "b" \[String\]', out)
    assert re.search(r"Value = 2 \[Int\]", out)


def test_empty_dict(printer_output):
    out = printer_output["emptyDict"]
    assert "[Dict]" in out


# MARK: ENUMERATION

def test_enumeration(printer_output):
    out = printer_output["enumVal"]
    assert '"Green" [Colors]' in out
    assert 'Value = "Green"' in out


# MARK: STRUCT

def test_struct(printer_output):
    out = printer_output["structVal"]
    assert "[MyStruct]" in out
    assert 'Type = "MyStruct" [StructType]' in out
    assert "Fields = {2 items}" in out


def test_struct_fields_expanded(printer_output):
    out = printer_output["structVal_deep"]
    assert re.search(r'FieldA = "abc" \[String\]', out)
    assert re.search(r"FieldB = 7 \[Int\]", out)


# MARK: PROPERTY OBJECT

def test_property_object(printer_output):
    out = printer_output["propObj"]
    assert "[PropertyObject]" in out
    assert "Properties = {3 items}" in out


def test_property_object_refcount_strong_weak(printer_output):
    assert re.search(r"RefCount = \[S:\d+, W:\d+\]", printer_output["propObj"])


def test_property_summaries(printer_output):
    out = printer_output["propObj_deep"]
    assert re.search(r'Frequency = "Frequency" \[Int\]', out)
    assert re.search(r'Label = "Label" \[String\]', out)
    assert re.search(r'Scale = "Scale" \[Float\]', out)


def test_property_default_values(printer_output):
    out = printer_output["propObj_deep"]
    assert "defaultValue" in out or "Frequency" in out


# MARK: STANDALONE RUNNER

def main():
    output = _printer_output()
    passed, failed = 0, 0
    for name, fn in list(globals().items()):
        if not (name.startswith("test_") and callable(fn)):
            continue
        try:
            fn(output)
            passed += 1
            print("PASS  {}".format(name))
        except Exception:
            failed += 1
            print("FAIL  {}".format(name))
            traceback.print_exc(limit=1)
    print("\n{} passed, {} failed".format(passed, failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
