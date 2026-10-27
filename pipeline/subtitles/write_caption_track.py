"""Write the look's styled caption track, holding the given captions, into a Resolve timeline file (.drt).

Written by AI on 2026-10-22 by Claude Fable 5.1.

Resolve's scripting API cannot create or edit captions (21.1), but it exports and imports timelines as .drt files,
and a .drt carries the subtitle track: every caption's text, frames and per-word times, and the Fusion template
that styles the track. So the captions are written into the file of an exported timeline, and the file is imported
back as the timeline with captions (pipeline/resolve/add_captions.py does the export and import).

The look's track comes from `looks/<look>/resolve/caption-track.drt`: a timeline exported from Resolve after the
look's subtitle template was dropped on its subtitle track once, in the interface, when the look was made.

Format, verified on Resolve 21.1's export of a 60-caption track (DbPrjVer 17), round-tripped byte for byte:
- A .drt is a zip: project.xml, MediaPool/.../MpFolder.xml and SeqContainer/<id>.xml, the timeline.
- The subtitle track is <SubtitleTrackVec><Element><Sm2TiTrack>: a header, <Items> with one <Sm2TiGenerator>
  per caption, and <FusionCompHolderItems> holding the template as an embedded Fusion composition.
- A caption has <Name> (lines joined by <br>), <Start> and <Duration> in timeline frames, and a <FieldsBlob>:
  a Qt byte array (type tag 2, length, flag 0x80 raw or 0x81 zstd) of a protobuf-style message, field 1 holding
  13: 0; 14: each word's text with its trailing space, or "\\n" where a line breaks, or nothing at the end;
  15: each word's start; 16: each word's end; 21: the caption's start frame. Field 2 is a constant style block.
- Word times are whole timeline frames multiplied by two (Resolve never writes an odd value; an odd value makes
  the template's highlight stick and split words onto a second page: tested 22 Oct).
"""
import argparse
import ctypes
import ctypes.util
import glob
import html
import json
import math
import os
import re
import struct
import uuid
import zipfile

ZSTD_MAGIC = b'\x28\xb5\x2f\xfd'


def load_zstd():
    """libzstd: $ZSTD_LIB, the pipeline devenv's profile, the system, then the Nix store."""
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [os.environ.get("ZSTD_LIB")]
    candidates += glob.glob(os.path.join(here, "..", ".devenv", "profile", "lib", "libzstd*.dylib"))
    candidates += [ctypes.util.find_library("zstd")]
    candidates += sorted(glob.glob("/nix/store/*-zstd-*/lib/libzstd.dylib"))
    for path in candidates:
        if path and os.path.exists(path):
            lib = ctypes.CDLL(path)
            lib.ZSTD_getFrameContentSize.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
            lib.ZSTD_getFrameContentSize.restype = ctypes.c_ulonglong
            lib.ZSTD_decompress.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_size_t]
            lib.ZSTD_decompress.restype = ctypes.c_size_t
            lib.ZSTD_compressBound.argtypes = [ctypes.c_size_t]
            lib.ZSTD_compressBound.restype = ctypes.c_size_t
            lib.ZSTD_compress.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_int]
            lib.ZSTD_compress.restype = ctypes.c_size_t
            return lib
    raise RuntimeError("libzstd not found: set ZSTD_LIB or add pkgs.zstd to the pipeline devenv")


zstd = load_zstd()


def decode_blob(hex_text):
    raw = bytes.fromhex(hex_text)
    assert raw[:4] == b'\x00\x00\x00\x02' and raw[8] in (0x80, 0x81), raw[:12].hex()
    assert struct.unpack('>I', raw[4:8])[0] == len(raw) - 8
    if raw[8] == 0x80:
        return raw[9:]
    compressed = raw[9:]
    assert compressed[:4] == ZSTD_MAGIC
    size = zstd.ZSTD_getFrameContentSize(compressed, len(compressed))
    buffer = ctypes.create_string_buffer(size)
    assert zstd.ZSTD_decompress(buffer, size, compressed, len(compressed)) == size
    return buffer.raw


def encode_blob(payload):
    """Short payloads raw (flag 0x80), longer ones as a zstd frame (flag 0x81), as Resolve writes them."""
    buffer = ctypes.create_string_buffer(zstd.ZSTD_compressBound(len(payload)))
    size = zstd.ZSTD_compress(buffer, len(buffer), payload, len(payload), 3)
    assert 0 < size < len(buffer)
    if size < len(payload):
        return (struct.pack('>I', 2) + struct.pack('>I', size + 1) + b'\x81' + buffer.raw[:size]).hex()
    return (struct.pack('>I', 2) + struct.pack('>I', len(payload) + 1) + b'\x80' + payload).hex()


def read_varint(data, offset):
    value, shift = 0, 0
    while True:
        byte = data[offset]
        offset += 1
        value |= (byte & 127) << shift
        if byte < 128:
            return value, offset
        shift += 7


def write_varint(value):
    out = bytearray()
    while value >= 128:
        out.append((value & 127) | 128)
        value >>= 7
    out.append(value)
    return bytes(out)


def parse_fields(data):
    offset, fields = 0, []
    while offset < len(data):
        tag, offset = read_varint(data, offset)
        number, wire = tag >> 3, tag & 7
        if wire == 0:
            value, offset = read_varint(data, offset)
        elif wire == 2:
            length, offset = read_varint(data, offset)
            value = data[offset:offset + length]
            offset += length
        else:
            raise ValueError((number, wire, offset))
        fields.append((number, wire, value))
    return fields


def build_fields(fields):
    out = bytearray()
    for number, wire, value in fields:
        out += write_varint(number << 3 | wire)
        out += write_varint(value) if wire == 0 else write_varint(len(value)) + value
    return bytes(out)


def parse_caption_blob(hex_text):
    """(word texts, start ticks, end ticks, caption start frame, style block)."""
    outer = parse_fields(decode_blob(hex_text))
    assert [(n, w) for n, w, _ in outer] == [(1, 2), (2, 2)], outer
    inner = parse_fields(outer[0][2])
    words = [v.decode('utf-8') for n, w, v in inner if n == 14]
    starts = [v for n, w, v in inner if n == 15]
    ends = [v for n, w, v in inner if n == 16]
    frame = [v for n, w, v in inner if n == 21]
    assert [(n, w, v) for n, w, v in inner if n not in (14, 15, 16, 21)] == [(13, 0, 0)]
    assert len(words) == len(starts) == len(ends) and len(frame) == 1
    return words, starts, ends, frame[0], outer[1][2]


def caption_blob(words, starts, ends, start_frame, style):
    inner = [(13, 0, 0)] + [(14, 2, w.encode('utf-8')) for w in words]
    inner += [(15, 0, t) for t in starts] + [(16, 0, t) for t in ends] + [(21, 0, start_frame)]
    return encode_blob(build_fields([(1, 2, build_fields(inner)), (2, 2, style)]))


# The constant style block of every caption in the 22 Oct export (a Qt-compressed empty record).
DEFAULT_STYLE = bytes.fromhex('00000024789c6366606420040000b20005')


def word_texts(text, words):
    """Resolve's word texts: a trailing space, or "\\n" where the line breaks, or nothing after the last word."""
    lines = text.split('\n')
    expected = [w for line in lines for w in line.split()]
    given = [w['text'] for w in words]
    assert expected == given, (expected, given)
    out = []
    for line_index, line in enumerate(lines):
        line_words = line.split()
        for i, w in enumerate(line_words):
            last_in_line = i == len(line_words) - 1
            last_line = line_index == len(lines) - 1
            out.append(w + ('' if last_in_line and last_line else '\n' if last_in_line else ' '))
    return out


def xml_escape(text):
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


CAPTION_XML = """     <Element>
      <Sm2TiGenerator DbId="{db_id}">
       <FieldsBlob>{blob}</FieldsBlob>
       <PrettyType>Subtitle</PrettyType>
       <Name>{name}</Name>
       <Start>{start}</Start>
       <Duration>{duration}</Duration>
       <LinkedItemSync/>
       <WasDisbanded>false</WasDisbanded>
       <MarkersBA/>
       <UiMemento>0</UiMemento>
       <Flags>0</Flags>
       <PriorityIndex>0</PriorityIndex>
       <EffectFiltersBA/>
       <ImportExportMetadataBA/>
       <RenderTextEnabled>true</RenderTextEnabled>
       <RenderTextGanged>true</RenderTextGanged>
       <RenderTextPrefixed>true</RenderTextPrefixed>
       <In/>
      </Sm2TiGenerator>
     </Element>
"""


def caption_frames(caption, fps, timeline_start):
    """A caption's frames and its words' ticks, in whole frames, each word at least a frame, in order, inside the caption."""
    start_frame = timeline_start + math.floor(caption['start'] * fps + 1e-6)
    end_frame = timeline_start + math.ceil(caption['end'] * fps - 1e-6)
    if end_frame <= start_frame:
        raise ValueError(f"caption has no length: {caption['text']!r}")
    frames = []
    for w in caption['words']:
        a = min(max(round(timeline_start + w['start'] * fps), start_frame), end_frame)
        b = min(max(round(timeline_start + w['end'] * fps), start_frame), end_frame)
        frames.append([a, b])
    for i, (a, b) in enumerate(frames):
        if i:
            frames[i][0] = a = max(a, frames[i - 1][1])
        if b <= a:
            frames[i][1] = b = a + 1
    if frames[-1][1] > end_frame:
        raise ValueError(f"the words of {caption['text']!r} need more frames than the caption has")
    return start_frame, end_frame, [2 * a for a, _ in frames], [2 * b for _, b in frames]


def caption_items_xml(captions, fps, timeline_start, style=DEFAULT_STYLE):
    blocks = []
    for c in captions:
        words = word_texts(c['text'], c['words'])
        start_frame, end_frame, starts, ends = caption_frames(c, fps, timeline_start)
        blocks.append(CAPTION_XML.format(db_id=str(uuid.uuid4()), blob=caption_blob(words, starts, ends, start_frame, style),
                                         name=xml_escape(c['text']).replace('\n', '&lt;br&gt;'),
                                         start=start_frame, duration=end_frame - start_frame))
    return ''.join(blocks)


def sequence_xml(drt_path):
    """The timeline's own sequence in a .drt. A timeline holding other timelines as clips (the native graphics)
    carries their sequences too; its own is the one no clip refers to (fault 85 of the 22 Oct run, from the
    finishing editor's own_sequence.py). A multicam's sequence is left out the same way (26 Oct, Claude Opus 5.5,
    stream I of the hill-climb)."""
    with zipfile.ZipFile(drt_path) as z:
        sequences = {n: z.read(n).decode('utf-8') for n in z.namelist() if n.startswith('SeqContainer/')}
        pool = ''.join(z.read(n).decode('utf-8') for n in z.namelist() if n.startswith('MediaPool/'))
    if len(sequences) == 1:
        return next(iter(sequences.items()))
    used_as_clips = set(re.findall(r'<MediaRef>([0-9a-f-]+)</MediaRef>', ''.join(sequences.values())))
    nested = {sequence for clip, sequence in re.findall(
        r'<MpTimelineClip>([0-9a-f-]+)</MpTimelineClip>\s*<Sequence>\s*<Sm2Sequence DbId="([0-9a-f-]+)"', pool) if clip in used_as_clips}
    nested |= {sequence for clip, sequence in re.findall(
        r'<Sm2MpMulticamClip DbId="([0-9a-f-]+)">.*?<Sm2Sequence DbId="([0-9a-f-]+)"', pool, re.S) if clip in used_as_clips}
    own = [n for n, xml in sequences.items() if not any(f'<Sequence>{s}</Sequence>' in xml for s in nested)]
    if len(own) != 1:
        raise ValueError(f"cannot tell which sequence in {drt_path} is the timeline's own: {own}")
    return own[0], sequences[own[0]]


def read_captions(drt_path):
    """The captions in a .drt: text (lines joined by \\n), start and end frames, word texts and ticks."""
    _, seq = sequence_xml(drt_path)
    m = re.search(r'<SubtitleTrackVec>.*?</SubtitleTrackVec>', seq, re.S)
    out = []
    for block in re.findall(r'<Sm2TiGenerator\b.*?</Sm2TiGenerator>', m.group(0) if m else '', re.S):
        name = re.search(r'<Name>(.*?)</Name>', block, re.S).group(1)
        text = html.unescape(name.replace('&lt;br&gt;', '\n'))  # Resolve writes &quot; and &apos; too (26 Oct)
        start = int(re.search(r'<Start>(\d+)</Start>', block).group(1))
        duration = int(re.search(r'<Duration>(\d+)</Duration>', block).group(1))
        words, starts, ends, frame, _ = parse_caption_blob(re.search(r'<FieldsBlob>([0-9a-f]+)</FieldsBlob>', block).group(1))
        assert frame == start
        out.append({"text": text, "start": start, "end": start + duration, "words": words, "word_starts": starts, "word_ends": ends})
    return out


def write_caption_track(timeline_drt, look_track_drt, captions, fps, timeline_start, output):
    """The exported timeline with the look's subtitle track, holding the captions, in place of its own."""
    _, look_seq = sequence_xml(look_track_drt)
    track_vec = re.search(r'<SubtitleTrackVec>.*?</SubtitleTrackVec>', look_seq, re.S)
    assert track_vec and 'FusionCompHolderItems>' in track_vec.group(0), "the look's file carries no styled subtitle track"
    track_vec = track_vec.group(0)
    items = re.search(r'<Items>.*?</Items>|<Items\s*/>', track_vec, re.S)
    track_vec = track_vec[:items.start()] + '<Items>\n' + caption_items_xml(captions, fps, timeline_start) + '    </Items>' + track_vec[items.end():]
    seq_name, seq = sequence_xml(timeline_drt)
    sequence_id = re.search(r'<Sm2TiTrack\b.*?<Sequence>([0-9a-f-]+)</Sequence>', seq, re.S).group(1)
    track_vec = re.sub(r'<Sequence>[0-9a-f-]+</Sequence>', f'<Sequence>{sequence_id}</Sequence>', track_vec)
    track_vec = re.sub(r'<Sm2TiVideoClip DbId="[0-9a-f-]+">', lambda _: f'<Sm2TiVideoClip DbId="{uuid.uuid4()}">', track_vec)
    existing = re.search(r'<SubtitleTrackVec>.*?</SubtitleTrackVec>|<SubtitleTrackVec\s*/>', seq, re.S)
    assert existing, 'no SubtitleTrackVec in the exported timeline'
    seq = seq[:existing.start()] + track_vec + seq[existing.end():]
    with zipfile.ZipFile(timeline_drt) as z:
        entries = {i.filename: z.read(i) for i in z.infolist()}
    entries[seq_name] = seq.encode('utf-8')
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED) as out:
        for name, data in entries.items():
            out.writestr(name, data)
    written = read_captions(output)
    assert len(written) == len(captions)
    return {"captions": len(written), "first": written[0]["text"] if written else None, "output": str(output)}


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description="Write the look's caption track with the given captions into an exported timeline file.")
    ap.add_argument('timeline_drt', help='a .drt exported from the timeline (Timeline.Export with EXPORT_DRT)')
    ap.add_argument('look_track_drt', help="the look's caption-track.drt")
    ap.add_argument('captions_json', help='build/captions.json from build_captions.py')
    ap.add_argument('output')
    ap.add_argument('--start-frame', type=int, required=True, help="the timeline's first frame (Timeline.GetStartFrame)")
    args = ap.parse_args()
    spec = json.load(open(args.captions_json, encoding='utf-8'))
    print(json.dumps(write_caption_track(args.timeline_drt, args.look_track_drt, spec['captions'], spec['fps'], args.start_frame, args.output)))
