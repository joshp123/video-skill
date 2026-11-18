// Written by AI on 2026.11.17 by model claude opus 5.5; desktop Spaces added 18 Nov. Prints every window DaVinci Resolve
// owns as JSON lines: pid, id, layer, onscreen, width, height, title, and spaces: the desktop Spaces the window is on
// (SkyLight's SLSCopySpacesForWindows, a private call; empty for a window that is ordered out, which nobody can see).
// session.py compiles and runs it. Titles need the calling terminal to hold Screen Recording permission.
import CoreGraphics
import Foundation

typealias MainConnection = @convention(c) () -> Int32
typealias CopySpaces = @convention(c) (Int32, Int32, CFArray) -> CFArray?
let skyLight = dlopen("/System/Library/PrivateFrameworks/SkyLight.framework/SkyLight", RTLD_NOW)
let connection = unsafeBitCast(dlsym(skyLight, "SLSMainConnectionID"), to: MainConnection.self)()
let spacesOf = unsafeBitCast(dlsym(skyLight, "SLSCopySpacesForWindows"), to: CopySpaces.self)

let windows = CGWindowListCopyWindowInfo([.optionAll], kCGNullWindowID) as? [[String: Any]] ?? []
for window in windows {
    guard let owner = window[kCGWindowOwnerName as String] as? String, owner.contains("Resolve") else { continue }
    let bounds = window[kCGWindowBounds as String] as? [String: Any] ?? [:]
    let id = window[kCGWindowNumber as String] as? Int ?? 0
    let row: [String: Any] = [
        "pid": window[kCGWindowOwnerPID as String] as? Int ?? 0,
        "id": id,
        "layer": window[kCGWindowLayer as String] as? Int ?? 0,
        "onscreen": window[kCGWindowIsOnscreen as String] as? Bool ?? false,
        "width": Int(bounds["Width"] as? Double ?? 0),
        "height": Int(bounds["Height"] as? Double ?? 0),
        "title": window[kCGWindowName as String] as? String ?? "",
        "spaces": spacesOf(connection, 7, [id] as CFArray) as? [Int] ?? [],
    ]
    let data = try! JSONSerialization.data(withJSONObject: row)
    print(String(data: data, encoding: .utf8)!)
}
