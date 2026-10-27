// Written by AI on 2026-10-26 by Claude Opus 5.5 (hill-climb stream A, the fault instrument).
// Reads every frame of a rendered video with AVFoundation and measures it with Apple Vision.
// One JSON object per frame on stdout: the largest face (box, eye openness, nose and lip boxes,
// median skin colour of the nose and inner cheeks, the patch and method of roles/colour.md), the caption band (text lines, the lit pill's box),
// and on every Nth frame the text lines outside the band. The band is read again only when its white and orange pixels change;
// a frame that reuses the previous reading says band_same_as_previous. Pixel boxes are [x0, y0, x1, y1] from the top left.
// usage: qc_vision VIDEO BAND_TOP BAND_BOTTOM FULL_FRAME_TEXT_EVERY_N
import AVFoundation
import Foundation
import Vision

let arguments = CommandLine.arguments
let videoURL = URL(fileURLWithPath: arguments[1])
let bandTop = Int(arguments[2])!, bandBottom = Int(arguments[3])!
let fullFrameTextEveryN = Int(arguments[4])!

struct BGRAFrame { let width: Int; let height: Int; let bytesPerRow: Int; let bytes: [UInt8] }

func box(_ points: [CGPoint], imageHeight: Int) -> [Int] {
    let xs = points.map { $0.x }, ys = points.map { CGFloat(imageHeight) - $0.y }
    return [Int(xs.min()!), Int(ys.min()!), Int(xs.max()!), Int(ys.max()!)]
}

func eyeOpenness(_ region: VNFaceLandmarkRegion2D?) -> Double {
    guard let region = region, region.pointCount > 2 else { return -1 }
    let xs = region.normalizedPoints.map { Double($0.x) }, ys = region.normalizedPoints.map { Double($0.y) }
    let width = xs.max()! - xs.min()!
    return width > 0 ? (ys.max()! - ys.min()!) / width : -1
}

// The median colour of a patch's skin: pixels between the 20th and 95th percentile of lightness, so beard, glasses and shine drop out.
func skinRGB(_ frame: BGRAFrame, _ rect: [Int]) -> [Double] {
    let x0 = max(0, rect[0]), x1 = min(frame.width, rect[2]), y0 = max(0, rect[1]), y1 = min(frame.height, rect[3])
    guard x1 > x0, y1 - y0 > 10 else { return [] }
    var pixels: [(Int, Int, Int)] = []
    for y in y0..<y1 { for x in x0..<x1 {
        let i = y * frame.bytesPerRow + x * 4
        pixels.append((Int(frame.bytes[i + 2]), Int(frame.bytes[i + 1]), Int(frame.bytes[i])))
    }}
    let lightness = pixels.map { $0.0 + $0.1 + $0.2 }.sorted()
    let low = lightness[Int(0.2 * Double(lightness.count - 1))], high = lightness[Int(0.95 * Double(lightness.count - 1))]
    let kept = pixels.filter { let l = $0.0 + $0.1 + $0.2; return l > low && l < high }
    guard !kept.isEmpty else { return [] }
    func median(_ values: [Int]) -> Double { let sorted = values.sorted(); return Double(sorted[sorted.count / 2]) }
    return [median(kept.map { $0.0 }), median(kept.map { $0.1 }), median(kept.map { $0.2 })]
}

// The look's pill colour is #D9531E; this window holds it through encoding and grading.
func isPillOrange(_ red: Int, _ green: Int, _ blue: Int) -> Bool {
    red > 170 && green > 50 && green < 120 && blue < 80 && red - green > 90
}

func pillOrangeFraction(_ frame: BGRAFrame, _ rect: [Int]) -> Double {
    var orange = 0.0, all = 0.0
    for y in stride(from: max(0, rect[1]), to: min(frame.height, rect[3]), by: 2) { for x in stride(from: max(0, rect[0]), to: min(frame.width, rect[2]), by: 2) {
        let i = y * frame.bytesPerRow + x * 4
        if isPillOrange(Int(frame.bytes[i + 2]), Int(frame.bytes[i + 1]), Int(frame.bytes[i])) { orange += 1 }
        all += 1
    }}
    return all > 0 ? orange / all : 0
}

// White caption letters and the orange pill, sampled sparsely: when this does not change, the caption has not changed.
func captionSignature(_ frame: BGRAFrame) -> [Bool] {
    var signature: [Bool] = []
    for y in stride(from: bandTop, to: min(bandBottom, frame.height), by: 4) { for x in stride(from: 0, to: frame.width, by: 4) {
        let i = y * frame.bytesPerRow + x * 4
        let blue = Int(frame.bytes[i]), green = Int(frame.bytes[i + 1]), red = Int(frame.bytes[i + 2])
        signature.append((red > 215 && green > 215 && blue > 215) || isPillOrange(red, green, blue))
    }}
    return signature
}

func textLines(_ image: CGImage, offsetY: Int, wordBoxes: Bool) -> [[String: Any]] {
    let request = VNRecognizeTextRequest()
    request.recognitionLevel = .accurate
    request.usesLanguageCorrection = false
    try? VNImageRequestHandler(cgImage: image, options: [:]).perform([request])
    let width = Double(image.width), height = Double(image.height)
    func pixels(_ b: CGRect) -> [Int] {
        [Int(b.minX * width), offsetY + Int((1 - b.maxY) * height), Int(b.maxX * width), offsetY + Int((1 - b.minY) * height)]
    }
    var lines: [[String: Any]] = []
    for observation in (request.results ?? []).sorted(by: { $0.boundingBox.maxY > $1.boundingBox.maxY }) {
        guard let candidate = observation.topCandidates(1).first else { continue }
        var line: [String: Any] = ["text": candidate.string, "box": pixels(observation.boundingBox)]
        if wordBoxes {
            var words: [[String: Any]] = []
            let text = candidate.string
            text.enumerateSubstrings(in: text.startIndex..<text.endIndex, options: .byWords) { word, range, _, _ in
                if let word = word, let wordBox = try? candidate.boundingBox(for: range)?.boundingBox {
                    words.append(["text": word, "box": pixels(wordBox)])
                }
            }
            line["words"] = words
        }
        lines.append(line)
    }
    return lines
}

func measure(_ frame: BGRAFrame, _ image: CGImage, index: Int, readCaption: Bool) -> [String: Any] {
    var result: [String: Any] = ["frame": index]
    let faceRequest = VNDetectFaceLandmarksRequest()
    try? VNImageRequestHandler(cgImage: image, options: [:]).perform([faceRequest])
    let imageSize = CGSize(width: frame.width, height: frame.height)
    if let face = (faceRequest.results ?? []).max(by: { $0.boundingBox.width < $1.boundingBox.width }), let landmarks = face.landmarks {
        let b = face.boundingBox
        var faceResult: [String: Any] = [
            "box": [Int(b.minX * Double(frame.width)), Int((1 - b.maxY) * Double(frame.height)),
                    Int(b.maxX * Double(frame.width)), Int((1 - b.minY) * Double(frame.height))],
            "left_eye_openness": eyeOpenness(landmarks.leftEye), "right_eye_openness": eyeOpenness(landmarks.rightEye),
        ]
        if let nose = landmarks.nose { faceResult["nose"] = box(nose.pointsInImage(imageSize: imageSize), imageHeight: frame.height) }
        if let lips = landmarks.outerLips { faceResult["lips"] = box(lips.pointsInImage(imageSize: imageSize), imageHeight: frame.height) }
        if let leftEye = landmarks.leftEye, let rightEye = landmarks.rightEye, let nose = landmarks.nose, let lips = landmarks.outerLips {
            let eyes = box(leftEye.pointsInImage(imageSize: imageSize) + rightEye.pointsInImage(imageSize: imageSize), imageHeight: frame.height)
            let noseBox = box(nose.pointsInImage(imageSize: imageSize), imageHeight: frame.height)
            let lipTop = box(lips.pointsInImage(imageSize: imageSize), imageHeight: frame.height)[1]
            let faceLeft = Double(frame.width) * b.minX, faceWidth = Double(frame.width) * b.width
            let eyeCentreY = Double(eyes[1] + eyes[3]) / 2
            // nose and inner cheeks: the face box's middle half, from a third of the way from the eyes to the lips down to the nose tip
            let skinRect = [Int(faceLeft + 0.25 * faceWidth), Int(eyeCentreY + 0.35 * (Double(lipTop) - eyeCentreY)),
                            Int(faceLeft + 0.75 * faceWidth), noseBox[3]]
            faceResult["skin_rect"] = skinRect
            faceResult["skin_rgb"] = skinRGB(frame, skinRect)
        }
        result["face"] = faceResult
    }
    if readCaption, let band = image.cropping(to: CGRect(x: 0, y: bandTop, width: frame.width, height: bandBottom - bandTop)) {
        var lines = textLines(band, offsetY: bandTop, wordBoxes: true)
        for lineIndex in lines.indices {
            var words = lines[lineIndex]["words"] as! [[String: Any]]
            for wordIndex in words.indices { words[wordIndex]["pill_fraction"] = pillOrangeFraction(frame, words[wordIndex]["box"] as! [Int]) }
            lines[lineIndex]["words"] = words
        }
        result["band_lines"] = lines
    }
    if index % fullFrameTextEveryN == 0 {
        result["frame_lines"] = textLines(image, offsetY: 0, wordBoxes: false).filter {
            let lineBox = $0["box"] as! [Int]; return lineBox[3] < bandTop || lineBox[1] > bandBottom
        }
    }
    return result
}

let asset = AVURLAsset(url: videoURL)
let semaphore = DispatchSemaphore(value: 0)
var videoTrack: AVAssetTrack?
var frameRate: Float = 25
Task {
    videoTrack = try! await asset.loadTracks(withMediaType: .video).first
    frameRate = try! await videoTrack!.load(.nominalFrameRate)
    semaphore.signal()
}
semaphore.wait()
let reader = try! AVAssetReader(asset: asset)
let output = AVAssetReaderTrackOutput(track: videoTrack!, outputSettings: [kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA])
reader.add(output)
reader.startReading()

let workQueue = DispatchQueue(label: "measure", attributes: .concurrent)
let inFlight = DispatchSemaphore(value: ProcessInfo.processInfo.activeProcessorCount)
let group = DispatchGroup()
let resultsLock = NSLock()
var results: [Int: [String: Any]] = [:]
var lastReadSignature: [Bool] = []
while let sample = output.copyNextSampleBuffer(), let pixelBuffer = CMSampleBufferGetImageBuffer(sample) {
    let index = Int((CMSampleBufferGetPresentationTimeStamp(sample).seconds * Double(frameRate)).rounded())
    CVPixelBufferLockBaseAddress(pixelBuffer, .readOnly)
    let width = CVPixelBufferGetWidth(pixelBuffer), height = CVPixelBufferGetHeight(pixelBuffer)
    let bytesPerRow = CVPixelBufferGetBytesPerRow(pixelBuffer)
    let bytes = [UInt8](UnsafeBufferPointer(start: CVPixelBufferGetBaseAddress(pixelBuffer)!.assumingMemoryBound(to: UInt8.self), count: bytesPerRow * height))
    CVPixelBufferUnlockBaseAddress(pixelBuffer, .readOnly)
    let frame = BGRAFrame(width: width, height: height, bytesPerRow: bytesPerRow, bytes: bytes)
    let provider = CGDataProvider(data: Data(bytes) as CFData)!
    let image = CGImage(width: width, height: height, bitsPerComponent: 8, bitsPerPixel: 32, bytesPerRow: bytesPerRow,
                        space: CGColorSpace(name: CGColorSpace.sRGB)!,
                        bitmapInfo: CGBitmapInfo(rawValue: CGImageAlphaInfo.noneSkipFirst.rawValue | CGBitmapInfo.byteOrder32Little.rawValue),
                        provider: provider, decode: nil, shouldInterpolate: false, intent: .defaultIntent)!
    let signature = captionSignature(frame)
    let changed = zip(signature, lastReadSignature).filter { $0 != $1 }.count
    let readCaption = lastReadSignature.isEmpty || changed > signature.count / 400
    if readCaption { lastReadSignature = signature }
    inFlight.wait()
    group.enter()
    workQueue.async {
        var measured = measure(frame, image, index: index, readCaption: readCaption)
        if !readCaption { measured["band_same_as_previous"] = true }
        resultsLock.lock(); results[index] = measured; resultsLock.unlock()
        inFlight.signal(); group.leave()
    }
}
group.wait()
if reader.status == .failed { FileHandle.standardError.write("reading failed: \(String(describing: reader.error))\n".data(using: .utf8)!); exit(1) }
for index in results.keys.sorted() {
    let data = try! JSONSerialization.data(withJSONObject: results[index]!, options: [.sortedKeys])
    FileHandle.standardOutput.write(data); FileHandle.standardOutput.write("\n".data(using: .utf8)!)
}
