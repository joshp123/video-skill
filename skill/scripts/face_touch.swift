// Flags frames where a hand is on Josh's face, so the cut can avoid them.
// Written by AI on 2026.10.14 by model claude-opus-5.5, from the 14 Oct 2026 session.
// Header commands corrected by AI on 2026-10-22 by Claude Opus 5.5, fault pass after the codex-switch test.
//
// For each JPEG in a folder: does any hand have 3 or more confident points inside the face box
// (enlarged by 15%)? Uses macOS Vision. Many hits are gestures just below the face: look at the
// flagged frames before trusting them. A hand beside or behind the head can show on one camera
// only, so read both cameras' scans together: a touch on either is a touch on both.
//
// SCRATCH is a folder on the SSD under Media/Edits/.cache/. Scan every camera's whole file, from its
// first frame: a scan of part of the take is a hole the editor cannot see. Run it detached (nohup).
// frames: ffmpeg -hwaccel videotoolbox -i CAMERA_FILE -map 0:v:0 -vf "fps=5,scale=640:-2" -q:v 4 "$SCRATCH/frames-CAMERA/%05d.jpg"
// build:  swiftc -O -module-cache-path "$SCRATCH/modulecache" face_touch.swift -o "$SCRATCH/face_touch"
// run:    "$SCRATCH/face_touch" "$SCRATCH/frames-CAMERA" 5 CAMERA_OFFSET_S > CAMERA.csv   (columns: seconds, touching, points)
//         CAMERA_OFFSET_S is that camera's offset_s (0 for the front camera), so the times are front-clock seconds.
import Foundation
import Vision

let args = CommandLine.arguments
let folder = URL(fileURLWithPath: args[1])
let framesPerSecond = Double(args[2])!
let startSeconds = Double(args[3])!
let files = try FileManager.default.contentsOfDirectory(atPath: folder.path).filter { $0.hasSuffix(".jpg") }.sorted()
print("seconds,touching,points")
for (index, name) in files.enumerated() {
    let handler = VNImageRequestHandler(url: folder.appendingPathComponent(name))
    let faces = VNDetectFaceRectanglesRequest()
    let hands = VNDetectHumanHandPoseRequest()
    hands.maximumHandCount = 2
    try? handler.perform([faces, hands])
    var pointsInFace = 0
    if let face = faces.results?.max(by: { $0.boundingBox.width < $1.boundingBox.width })?.boundingBox {
        let box = face.insetBy(dx: -face.width * 0.15, dy: -face.height * 0.15)
        for hand in hands.results ?? [] {
            for (_, point) in (try? hand.recognizedPoints(.all)) ?? [:] where point.confidence > 0.3 && box.contains(point.location) {
                pointsInFace += 1
            }
        }
    }
    print(String(format: "%.2f,%d,%d", startSeconds + Double(index) / framesPerSecond, pointsInFace >= 3 ? 1 : 0, pointsInFace))
}
