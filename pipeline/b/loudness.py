"""Write and import an Optimize to Standard BS.1770-4 render preset; print its name.
Written by AI on 2026-10-25 by GPT-6.1 Sol.
Usage: loudness.py --preset-dir DIR --target LUFS --ceiling DBTP
Targets are whole numbers, as stored by Resolve. Uses route 3's exported Audio
Only donor and Qt blob codec, unchanged. The imported preset is audio-only;
LoadRenderPreset(name) before render_timeline.py sets the phone/post format.
Optimize is measured to undershoot its target; measure the actual delivery.
"""
import argparse, os, re, sys, uuid
from pathlib import Path

import struct


def _string(data, i):
    n = struct.unpack(">I", data[i:i + 4])[0]
    if n == 0xFFFFFFFF:
        return None, i + 4
    return data[i + 4:i + 4 + n].decode("utf-16-be"), i + 4 + n


def _variant(data, i):
    kind = struct.unpack(">I", data[i:i + 4])[0]
    i += 5                                          # type, then the null flag
    if kind == 1:
        return ("bool", bool(data[i])), i + 1
    if kind in (2, 3):
        return (("int", "uint")[kind - 2], struct.unpack(">i" if kind == 2 else ">I", data[i:i + 4])[0]), i + 4
    if kind in (4, 5):
        return (("long", "ulong")[kind - 4], struct.unpack(">q" if kind == 4 else ">Q", data[i:i + 8])[0]), i + 8
    if kind == 6:
        return ("double", struct.unpack(">d", data[i:i + 8])[0]), i + 8
    if kind == 10:
        s, i = _string(data, i)
        return ("string", s), i
    if kind == 12:
        n = struct.unpack(">I", data[i:i + 4])[0]
        return ("bytes", data[i + 4:i + 4 + n].hex()), i + 4 + n
    if kind == 8:
        m, i = _map(data, i)
        return ("map", m), i
    if kind == 9:
        n = struct.unpack(">I", data[i:i + 4])[0]
        i += 4
        items = []
        for _ in range(n):
            v, i = _variant(data, i)
            items.append(v)
        return ("list", items), i
    raise ValueError(f"QVariant type {kind} at {i - 5}")


def _map(data, i):
    n = struct.unpack(">I", data[i:i + 4])[0]
    i += 4
    out = []
    for _ in range(n):
        k, i = _string(data, i)
        v, i = _variant(data, i)
        out.append((k, v))
    return out, i


def decode(hex_text):
    data = bytes.fromhex(hex_text)
    assert data[:4] == b"\x00\x00\x00\x01", data[:8].hex()
    m, i = _map(data, 4)
    assert i == len(data), (i, len(data))
    return m


def _encode_string(s):
    raw = s.encode("utf-16-be")
    return struct.pack(">I", len(raw)) + raw


def _encode_variant(v):
    kind, value = v
    if kind == "bool":
        return struct.pack(">IB", 1, 0) + bytes([1 if value else 0])
    if kind == "int":
        return struct.pack(">IBi", 2, 0, value)
    if kind == "uint":
        return struct.pack(">IBI", 3, 0, value)
    if kind == "long":
        return struct.pack(">IBq", 4, 0, value)
    if kind == "double":
        return struct.pack(">IBd", 6, 0, value)
    if kind == "string":
        return struct.pack(">IB", 10, 0) + _encode_string(value)
    if kind == "bytes":
        raw = bytes.fromhex(value)
        return struct.pack(">IBI", 12, 0, len(raw)) + raw
    if kind == "map":
        return struct.pack(">IB", 8, 0) + _encode_map(value)
    if kind == "list":
        return struct.pack(">IBI", 9, 0, len(value)) + b"".join(_encode_variant(x) for x in value)
    raise ValueError(kind)


def _encode_map(m):
    return struct.pack(">I", len(m)) + b"".join(_encode_string(k) + _encode_variant(v) for k, v in m)


def encode(m):
    return (b"\x00\x00\x00\x01" + _encode_map(m)).hex()



def run(resolve, directory, target, ceiling):
    project = resolve.GetProjectManager().GetCurrentProject()
    donor = Path(__file__).resolve().parents[2]/'.cache/audio-route-test-2/drt/r2-audio-base.xml/r2 audio base.xml'
    base = donor.read_text()
    blob = re.search(r'<FieldsBlob>([0-9a-f]+)</FieldsBlob>',base)[1]
    values = dict(RecordNormalizeAudio=('bool',True), RecordAudioNormalizationMethod=('int',1),
        RecordAudioNormalizationMode=('int',3), RecordAudioNormalizationTargetLoudness=('int',target),
        RecordAudioNormalizationTargetLevel=('int',ceiling),
        RecordAudioNormalizationOutputTracksEnableState=('bytes','0000000100000001000000020030000000020000000001'))
    fields = [(k,v) for k,v in decode(blob) if k not in values]+list(values.items())
    name = f'B loudness {target} LUFS {ceiling} dBTP {uuid.uuid4().hex[:8]}'
    text = re.sub(r'<SyRecordInfo DbId="[0-9a-f-]+">',f'<SyRecordInfo DbId="{uuid.uuid4()}">',base.replace(blob,encode(fields)),count=1)
    directory.mkdir(parents=True,exist_ok=True)
    path = directory/(name+'.xml'); path.write_text(text)
    if not resolve.ImportRenderPreset(str(path)) or name not in project.GetRenderPresetList():
        raise RuntimeError(f'ImportRenderPreset failed: {path}')
    print(name)
    return name


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preset-dir',type=Path,required=True)
    parser.add_argument('--target',type=int,required=True); parser.add_argument('--ceiling',type=int,required=True)
    args = parser.parse_args()
    import DaVinciResolveScript
    try: run(DaVinciResolveScript.scriptapp('Resolve'),args.preset_dir.resolve(),args.target,args.ceiling)
    except Exception as error:
        print(str(error),file=sys.stderr); sys.stdout.flush(); os._exit(1)
    sys.stdout.flush(); os._exit(0)
