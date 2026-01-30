# Frame Visualization Guide

## What's Implemented

### Backend: Frame Extraction with Annotations

The backend now extracts frames from videos with YOLO detection visualizations:

#### 1. Frame Extractor (`backend/utils/frame_extractor.py`)

**Main Function: `extract_frames_with_detections()`**
```python
extract_frames_with_detections(
    video_path: str,
    detections: dict,        # From verify_gemini_products()
    output_dir: str = None,  # Save annotated frames to disk
    max_frames: int = None   # Limit to N frames for preview
) -> dict
```

**What it does:**
1. Opens video file with OpenCV
2. Iterates through frames with detections
3. **Draws bounding boxes** for each detection
4. **Labels boxes** with class name + confidence
5. Optionally **saves frames** to disk as JPEG
6. Returns frame metadata including:
   - Frame number and timestamp
   - Detection count per frame
   - Original YOLO detection data (boxes, classes, confidence)
   - Path to annotated frame file
   - Frame dimensions

**Example Output:**
```json
{
  "status": "success",
  "total_frames_extracted": 5,
  "frames": {
    "0": {
      "frame_number": 0,
      "timestamp_s": 0.0,
      "timestamp_ms": 0,
      "detection_count": 3,
      "detections": [
        {
          "class_id": 44,
          "class_name": "bowl",
          "confidence": 0.95,
          "bbox": {"x1": 100, "y1": 50, "x2": 200, "y2": 150}
        }
      ],
      "frame_path": "/tmp/frame_000000_0.00s.jpg",
      "frame_shape": [1080, 1920, 3]
    }
  },
  "timeline": [
    {
      "frame": 0,
      "timestamp_s": 0.0,
      "detections_summary": {"bowl": 3},
      "total_detections": 3
    }
  ],
  "metadata": {
    "video_fps": 30,
    "video_resolution": "1920x1080",
    "total_video_frames": 150
  }
}
```

#### 2. Keyframe Selection: `get_keyframes()`

Selects representative frames using:
- **"diverse"** - Evenly spaced across video (max 5)
- **"high_confidence"** - Highest average detection confidence

#### 3. Integration in Pipeline

Added to `analyze_video_gemini_worker()`:
- Extracts frames with YOLO detections drawn
- Selects diverse keyframes for display
- Adds frame data to `final_output.frame_visualization`

## Frontend Integration

### Response Structure

```json
{
  "final_output": {
    "frame_visualization": {
      "status": "success",
      "frames_extracted": 5,
      "keyframes": [0, 45, 90, 135, 180],
      "frame_timeline": [...]
    },
    "yolo_verification": {
      "class_distribution": {"bowl": 45, "dog": 8}
    }
  },
  "yolo": {
    "detections": {
      "frame_0": [...],
      "frame_45": [...]
    }
  }
}
```

### Display Components to Build

1. **Keyframes Gallery**
   - Show 5 representative frames
   - Display timestamp and detection count
   - List detected classes

2. **Timeline View**
   - Show detections over time
   - Indicate when products appear/disappear

3. **Detection Summary Table**
   - Class distribution
   - Confidence per class
   - Frames containing each class

## Next Steps

1. **Create UI component** to display keyframes gallery
2. **Parse frame_visualization data** from API response
3. **Show detection details** (classes, confidence, bounding boxes)
4. **Link to Gemini timeline** for context

## Testing

```bash
# View backend logs
modal logs app_def::analyze_video_gemini_worker --latest

# Expected output:
# [FrameExtractor] Extracted 5 annotated frames
# [GeminiWorker] Extracted 5 annotated frames
# [GeminiWorker] Selected 5 keyframes
```

## Code References

- Frame extraction: [backend/utils/frame_extractor.py:15](../backend/utils/frame_extractor.py)
- Pipeline integration: [backend/main.py:456](../backend/main.py)
- Output format: [backend/main.py:487](../backend/main.py)
