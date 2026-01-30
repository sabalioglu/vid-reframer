# Modal Backend Debugging Report

## Current Status

The unified pipeline is working end-to-end with the following architecture:
- **Gemini** → Video semantic analysis with millisecond precision
- **YOLOv8** → Object detection verification layer
- **FFmpeg** → Scene detection (optional)
- **SAM2** → Tracking (optional)

## Issue Investigation: "Bowl" Product Detection

### Observed Behavior
- Backend: 103 verified YOLOv8 detections found
- Frontend: Only "bowl" appearing in products identified
- Gemini returned 4 products: Dog Bowl, GOODBOY GRAVIES, Birdie & Louie Premium dry dog food, Cardboard Box

### Potential Causes

1. **Only "bowl" objects in video** (Most likely)
   - YOLOv8 detects objects from the 80-class COCO dataset
   - If the video only contains dog bowl objects, all 103 detections would be "bowl" class
   - This is correct behavior - we verify only what Gemini identified

2. **Keyword matching not working for other products**
   - Keywords extracted: cardboard, box, goodboy, gravies, birdie, louie, premium, food, dog, bowl
   - Matching: `if keyword in class_name or class_name in keyword`
   - Issue: Gemini product names don't match YOLOv8 class names exactly

3. **Frontend filtering issue**
   - Frontend receives `final_output["summary"]["products_in_use"]` from Gemini (all 4)
   - Frontend receives `final_output["yolo_verification"]["class_distribution"]` from YOLOv8 (only detected classes)
   - "Products identified" might be showing only verified detections, not all Gemini products

## Enhanced Logging Added (Deployed to Modal)

The backend now logs:

### In verify_gemini_products():
```
[YOLO Verification] Processing N Gemini products
[YOLO Verification] Product: 'Dog Bowl' (category: 'container') -> keywords: [dog, bowl]
[YOLO Verification] Product: 'GOODBOY GRAVIES' (category: 'container') -> keywords: [goodboy, gravies]
...
[YOLO Verification] Total keywords to match: {dog, bowl, goodboy, gravies, ...}
[YOLO Verification] Frame X: Matched class 'bowl' to keyword 'bowl'
[YOLO Verification] Frame Y: Matched class 'dog' to keyword 'dog'
[YOLO Verification] Complete: N frames with verified detections
[YOLO Verification] Total YOLOv8 detections processed: M
[YOLO Verification] Classes that matched keywords: {bowl, dog, ...}
```

### In analyze_video_gemini_worker():
```
[GeminiWorker] Gemini returned N products:
  1. Name: 'Dog Bowl' | Category: 'container'
  2. Name: 'GOODBOY GRAVIES' | Category: 'container'
...
[GeminiWorker] YOLOv8 Verification complete - Found N verified detections
[GeminiWorker] Frames with verified detections: M
[GeminiWorker] Class distribution: {bowl: 103, ...}
[GeminiWorker] Final output summary:
  - Products in use (from Gemini): [Dog Bowl, GOODBOY GRAVIES, ...]
  - Verified detections (from YOLOv8): 103
  - YOLO class distribution: {bowl: 103, ...}
```

## How to Debug

1. **View Modal Logs**:
   ```bash
   modal logs app_def::analyze_video_gemini_worker --latest
   ```

2. **Test with a video**:
   - Use frontend to upload test video
   - Check Modal logs for detailed keyword extraction and matching
   - Confirm which classes are being detected

3. **Verify Behavior**:
   - If only "bowl" in class_distribution → YOLOv8 only detected bowls (correct)
   - If multiple classes → keyword matching is working (all products verified)
   - If classes missing → check keyword extraction logic

## Next Steps: Frame Visualization

Once product detection is confirmed working:

1. **Extract keyframes** from detected products
   - Use frame indices where detections occur
   - Pick representative frames (middle of scene, highest confidence)

2. **Visualize detections** with bounding boxes
   - Draw YOLO detection boxes on frames
   - Label with class name and confidence

3. **Create timeline view**
   - Show which products appear when
   - Display temporal distribution across video
   - Link to timeline from Gemini analysis

## Implementation Status

- ✅ Comprehensive logging deployed to Modal
- ✅ Backend returning proper final_output format
- ⏳ Next: Frame visualization implementation
- ⏳ Next: Frontend display of detected frames with boxes

## Code References

- Backend worker: `backend/main.py::analyze_video_gemini_worker` (line 411)
- Product verification: `backend/utils/yolo_utils.py::verify_gemini_products` (line 126)
- Detection statistics: `backend/utils/yolo_utils.py::get_detection_statistics` (line 79)
