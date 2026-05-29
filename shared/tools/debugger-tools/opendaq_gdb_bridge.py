import gdb #type: ignore
import re


# 0x831915f2-c42f-5520-a420-56524d2ac552 (little-endian)
_ISERIALIZABLE_INTFID = (
    b'\xf2\x15\x19\x83\x2f\xc4\x20\x55'
    b'\xa4\x20\x56\x52\x4d\x2a\xc5\x52'
)


def _alloc(size=8):
    return int(gdb.parse_and_eval(f"(void*)malloc({size})"))


def _write_null(addr):
    gdb.parse_and_eval(f"*((void**){addr}) = 0")


def _read_ptr(addr):
    return int(gdb.parse_and_eval(f"*((void**){addr})"))


def _write_bytes(addr, data):
    gdb.selected_inferior().write_memory(addr, data)


def _get_string(istring_addr):
    char_pp = _alloc()
    gdb.parse_and_eval(
        f"((daq::IString*){istring_addr})->getCharPtr((const char**){char_pp})"
    )

    char_ptr = gdb.parse_and_eval(f"*((char**){char_pp})")
    return char_ptr.string()


def _borrow_serializable(obj_addr):
    global _intfid_cached_addr
    if _intfid_cached_addr is None:
        _intfid_cached_addr = _alloc(16)
        gdb.selected_inferior().write_memory(_intfid_cached_addr, _ISERIALIZABLE_INTFID)
    intfid_addr = _intfid_cached_addr

    out_pp = _alloc()
    _write_null(out_pp)
    ret = int(gdb.parse_and_eval(
        f"((daq::IBaseObject*){obj_addr})->borrowInterface("
        f"*(const daq::IntfID*){intfid_addr}, (void**){out_pp})"
    ))
    if ret != 0:
        return None
    return _read_ptr(out_pp)


def _create_serializer(pretty=1):
    ser_pp = _alloc()
    _write_null(ser_pp)
    for sym_name in ["createJsonSerializer", "'createJsonSerializer'"]:
        try:
            ret = int(gdb.parse_and_eval(
                f"{sym_name}((daq::ISerializer**){ser_pp}, (daq::Bool){pretty})"
            ))
            if ret == 0:
                return _read_ptr(ser_pp)
            return None
        except gdb.error:
            continue
    try:
        sym = gdb.parse_and_eval("(void*)createJsonSerializer")
        fn_addr = int(sym)
        ret = int(gdb.parse_and_eval(
            f"((int(*)(daq::ISerializer**, int)){fn_addr})"
            f"((daq::ISerializer**){ser_pp}, {pretty})"
        ))
        if ret == 0:
            return _read_ptr(ser_pp)
        return None
    except gdb.error:
        return None


def _serialize_at_address(addr, pretty=1):
    serializable = _borrow_serializable(addr)
    if serializable is None:
        return None
    ser = _create_serializer(pretty)
    if ser is None:
        return None
    ret = int(gdb.parse_and_eval(
        f"((daq::ISerializable*){serializable})->serialize((daq::ISerializer*){ser})"
    ))
    if ret != 0:
        return None
    str_pp = _alloc()
    _write_null(str_pp)
    ret = int(gdb.parse_and_eval(
        f"((daq::ISerializer*){ser})->getOutput((daq::IString**){str_pp})"
    ))
    if ret != 0:
        return None
    return _get_string(_read_ptr(str_pp))


def _resolve_address(expr):
    gdb.execute("set unwind-on-signal on")
    try:
        val = gdb.parse_and_eval(expr)

        t = val.type.strip_typedefs()

        if t.code == gdb.TYPE_CODE_PTR:
            addr = int(val)
            return addr if addr != 0 else None

        try:
            addr = int(val["object"])
            if addr != 0:
                return addr
        except (gdb.error, KeyError, TypeError):
            pass

        try:
            if val.address is not None:
                return int(val.address)
        except gdb.error:
            pass
    except gdb.error:
        pass
    try:
        out = gdb.execute(f"print /x {expr}", to_string=True)
        m = re.search(r'=\s*(0x[0-9a-fA-F]+)', out)
        if m:
            addr = int(m.group(1), 16)
            return addr if addr != 0 else None
    except gdb.error:
        pass

    return None


class OpenDAQSerialize(gdb.Command):
    def __init__(self):
        super().__init__("opendaq-serialize", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        gdb.execute("set unwind-on-signal on")
        args = arg.strip().split()
        if not args:
            print("Usage: opendaq-serialize <address> [pretty=1]")
            return
        addr = int(args[0], 16)
        pretty = int(args[1]) if len(args) > 1 else 1
        json_str = _serialize_at_address(addr, pretty)
        if json_str is None:
            print("ERROR: Serialization failed (object may not implement ISerializable)")
            return
        print(json_str)


OpenDAQSerialize()


_intfid_cached_addr = None 

def _bridge_resolve_impl(raw_ptr_addr):
    try:
        val = gdb.parse_and_eval(f"(daq::IBaseObject*){raw_ptr_addr:#x}")
        dyn = val.dynamic_type
        if dyn.code == gdb.TYPE_CODE_PTR:
            return val.cast(dyn).dereference()
        return val.cast(dyn.pointer()).dereference()
    except Exception:
        pass
    return None


def _bridge_find_field(value, field_name, depth=0):
    if depth > 12:
        return None
    try:
        return value[field_name]
    except Exception:
        pass
    try:
        for f in value.type.strip_typedefs().fields():
            if f.is_base_class:
                r = _bridge_find_field(value[f], field_name, depth + 1)
                if r is not None:
                    return r
    except Exception:
        pass
    return None


def _bridge_extract_ptr(field_val):
    try:
        v = int(field_val["object"])
        return v if v != 0 else None
    except Exception:
        pass
    try:
        if field_val.type.strip_typedefs().code == gdb.TYPE_CODE_PTR:
            v = int(field_val)
            return v if v != 0 else None
    except Exception:
        pass
    return None


def _bridge_list_item(impl, idx):
    list_f = _bridge_find_field(impl, "list")
    if list_f is None:
        return None
    try:
        vis = gdb.default_visualizer(list_f)
        if vis is not None:
            for i, (_, item) in enumerate(vis.children()):
                if i == idx:
                    return _bridge_extract_ptr(item)
    except Exception:
        pass
    try:
        items = list(iter_deque(list_f)) #type: ignore
        if idx < len(items):
            return _bridge_extract_ptr(items[idx])
    except Exception:
        pass
    return None


def _resolve_via_pretty_printer_child(ptr_addr, field_name):

    try:
        base_val = gdb.parse_and_eval(f"(daq::IBaseObject*){ptr_addr:#x}")
    except gdb.error:
        return None

    candidates = [base_val]
    try:
        dyn = base_val.dynamic_type
        if dyn != base_val.type:
            cast_val = (base_val.cast(dyn)
                        if dyn.code == gdb.TYPE_CODE_PTR
                        else base_val.cast(dyn.pointer()))
            candidates.append(cast_val)
    except Exception:
        pass

    for val in candidates:
        try:
            vis = gdb.default_visualizer(val)
            if vis is None:
                continue
            for child_name, child_val in vis.children():
                if child_name.strip('[]') == field_name:
                    result = _bridge_extract_ptr(child_val)
                    if result is not None:
                        return result
        except Exception:
            continue
    return None


def _resolve_via_synthetic_path(expr):
    expr = expr.strip()
    m = re.fullmatch(r'\((.+)\)->([A-Za-z_]\w*)', expr)
    if m:
        inner_expr, field_name = m.group(1).strip(), m.group(2)
        inner_addr = _resolve_combined(inner_expr)
        if inner_addr is None:
            return None
        result = _resolve_via_pretty_printer_child(inner_addr, field_name)
        if result is not None:
            return result
        impl = _bridge_resolve_impl(inner_addr)
        if impl is None:
            return None
        field = _bridge_find_field(impl, field_name)
        if field is not None:
            return _bridge_extract_ptr(field)
        try:
            vis = gdb.default_visualizer(impl)
            if vis is not None:
                for child_name, child_val in vis.children():
                    if child_name.strip('[]') == field_name:
                        result = _bridge_extract_ptr(child_val)
                        if result is not None:
                            return result
        except Exception:
            pass

        return None

    m = re.fullmatch(r'\((.+)\)\.([A-Za-z_]\w*)', expr)
    if m:
        return _resolve_combined(m.group(1).strip())

    m = re.fullmatch(r'\((.+)\)\[(\d+)\]', expr)
    if m:
        inner_expr, idx = m.group(1).strip(), int(m.group(2))
        inner_addr = _resolve_combined(inner_expr)
        if inner_addr is None:
            return None
        impl = _bridge_resolve_impl(inner_addr)
        if impl is None:
            return None
        return _bridge_list_item(impl, idx)

    return None


def _resolve_combined(expr):
    addr = _resolve_address(expr)
    if addr is not None:
        return addr
    return _resolve_via_synthetic_path(expr)


def _resolve_first_instance():
    for expr in ("daqGetFirstInstance()", "(daq::IInstance*)daq::firstInstance"):
        try:
            val = gdb.parse_and_eval(expr)
            addr = int(val)
            if addr != 0:
                return addr
        except gdb.error:
            continue
    return None

def _handle_tree(req):
    if "addr" in req:
        try:
            addr = int(req["addr"], 16)
        except (ValueError, TypeError):
            return {"error": f"Invalid address: {req['addr']}"}
        json_str = _serialize_at_address(addr, pretty=0)
        if json_str is None:
            return {"error": f"Serialization failed for address {req['addr']} (may not implement ISerializable)"}
        return {"json_str": json_str}

    expr = req["expr"]

    addr = _resolve_combined(expr)
    if addr is None:
        return {"error": f"Cannot resolve address for expression: {expr}"}

    json_str = _serialize_at_address(addr, pretty=0)
    if json_str is None:
        return {"error": f"Serialization failed for {expr} (may not implement ISerializable)"}

    return {"json_str": json_str}


def _handle_first_instance(req):
    addr = _resolve_first_instance()
    if addr is None:
        return {"error": "No live openDAQ Instance (daqGetFirstInstance returned null)"}
    json_str = _serialize_at_address(addr, pretty=0)
    if json_str is None:
        return {"error": f"Serialization failed for first instance at {addr:#x}"}
    return {"addr": f"{addr:#x}", "json_str": json_str}


def _handle_diagnose(req):
    expr = req.get("expr", "")
    result = {"expr": expr}
    try:
        val = gdb.parse_and_eval(expr)
        result["type"] = str(val.type)
        result["type_stripped"] = str(val.type.strip_typedefs())
    except gdb.error as e:
        result["eval_error"] = str(e)
        return result

    addr = _resolve_combined(expr)
    result["resolved_address"] = f"{addr:#x}" if addr else None

    if addr:
        json_str = _serialize_at_address(addr)
        if json_str:
            result["serialized_length"] = len(json_str)
            result["serialized_preview"] = json_str[:500]
        else:
            result["serialize_error"] = "Serialization failed"
    return result


def _parse_request(content):
    """Parse simple key=value request format instead of JSON"""
    req = {}
    for line in content.strip().split('\n'):
        if '=' in line:
            key, value = line.split('=', 1)
            req[key.strip()] = value.strip()
    return req


def _format_response(data):
    """Format response as simple text instead of JSON"""
    # Return raw JSON string from serialization directly
    if "json_str" in data and len(data) == 1:
        return data["json_str"]
    elif "addr" in data and "json_str" in data and len(data) == 2:
        return f"addr={data['addr']}\n{data['json_str']}"
    elif "error" in data:
        return f"ERROR: {data['error']}"
    else:
        lines = []
        for key, value in data.items():
            if value is None:
                lines.append(f"{key}=null")
            else:
                lines.append(f"{key}={value}")
        return '\n'.join(lines)


def _daq_bridge_process(tmp_base):
    req_file = tmp_base + ".req.txt"
    res_file = tmp_base + ".res.txt"
    try:
        with open(req_file, "r") as f:
            req = _parse_request(f.read())
        action = req.get("action")
        if action == "tree":
            result = _handle_tree(req)
        elif action == "first_instance":
            result = _handle_first_instance(req)
        elif action == "diagnose":
            result = _handle_diagnose(req)
        else:
            result = {"error": f"Unknown action: {action}"}
    except Exception as e:
        result = {"error": str(e)}
    
    response_text = _format_response(result)
    with open(res_file, "w") as f:
        f.write(response_text)


class _OpenDAQBridgeCmd(gdb.Command):
    """VS Code IPC bridge command. Usage: opendaq-bridge-process <tmp_base>"""
    def __init__(self):
        super().__init__("opendaq-bridge-process", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        tmp_base = arg.strip().strip('"').strip("'")
        if not tmp_base:
            print("Usage: opendaq-bridge-process <tmp_base_path>")
            return
        try:
            _daq_bridge_process(tmp_base)
        except Exception as e:
            print(f"opendaq-bridge-process error: {e}")


_OpenDAQBridgeCmd()


class OpenDAQInspect(gdb.Command):
    def __init__(self):
        super().__init__("opendaq-inspect", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        gdb.execute("set unwind-on-signal on")
        parts = arg.strip().split()
        if not parts:
            print("Usage: opendaq-inspect <expr> [pretty=1]")
            return
        pretty = 1
        if len(parts) > 1 and parts[-1] in ('0', '1'):
            pretty = int(parts[-1])
            expr = ' '.join(parts[:-1])
        else:
            expr = ' '.join(parts)

        print(f"Resolving: {expr}")
        addr = _resolve_combined(expr)
        if addr is None:
            print(f"ERROR: Cannot resolve address for: {expr}")
            return
        print(f"Address: {addr:#x}")

        json_str = _serialize_at_address(addr, pretty)
        if json_str is None:
            print("ERROR: Serialization failed (object may not implement ISerializable)")
            return
        print(json_str)


OpenDAQInspect()


class OpenDAQFirstInstance(gdb.Command):
    def __init__(self):
        super().__init__("opendaq-first-instance", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        gdb.execute("set unwind-on-signal on")
        parts = arg.strip().split()
        pretty = int(parts[0]) if parts and parts[0] in ('0', '1') else 1

        addr = _resolve_first_instance()
        if addr is None:
            print("ERROR: No live openDAQ Instance (daqGetFirstInstance returned null)")
            return
        print(f"First instance address: {addr:#x}")

        json_str = _serialize_at_address(addr, pretty)
        if json_str is None:
            print("ERROR: Serialization failed")
            return
        print(json_str)


OpenDAQFirstInstance()
