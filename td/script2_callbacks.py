# me - this DAT
# scriptOp - the OP which is cooking

import cv2
import numpy as np
import os
import random

class YOLOVideoDetector:
    def __init__(self, model_type="yolov3", confidence_threshold=0.5, nms_threshold=0.4):
        self.model_path = '/Users/marlen/projects/video_prod_phy/yolo-video-detection/models/'
        self.confidence_threshold = confidence_threshold
        self.nms_threshold = nms_threshold

        # Load YOLO model
        self.net = self.load_model(model_type)

        # Get output layer names
        layer_names = self.net.getLayerNames()
        unconnected_layers = self.net.getUnconnectedOutLayers()
        self.output_layers = [layer_names[i - 1] for i in unconnected_layers]

        # Load class names
        coco_names_path = os.path.join(self.model_path, "coco.names")
        with open(coco_names_path, "r") as f:
            self.classes = [line.strip() for line in f.readlines()]

    def load_model(self, model_type):
        if model_type == "yolov3":
            weights = os.path.join(self.model_path, "yolov3.weights")
            config = os.path.join(self.model_path, "yolov3.cfg")
        elif model_type == "yolov4-tiny":
            weights = os.path.join(self.model_path, "yolov4-tiny.weights")
            config = os.path.join(self.model_path, "yolov4-tiny.cfg")
        else:
            raise ValueError("Unsupported model type. Choose 'yolov3' or 'yolov4-tiny'.")
        return cv2.dnn.readNet(weights, config)

    def process_video(self, scriptOp):
        frame = op('moviefilein1').numpyArray()
        frame = frame[:, :, :3]  # Ensure frame is in RGB format
        frame = (frame * 255).astype(np.uint8)
        processed_frame = self.process_frame(frame)
        # print max and min values of the processed frame
        # print(processed_frame.shape)
        # the range from 0 1 should be 0-255
        frame_contig = np.ascontiguousarray(processed_frame)
        print("Processed frame min:", np.min(frame_contig), "max:", np.max(frame_contig))
        # print(frame_contig.shape)
        scriptOp.copyNumpyArray(frame_contig)

    def process_frame(self, frame_old):
        # copy the frame and resize it
        frame = np.copy(frame_old)
        frame_width = frame.shape[1] // 3
        frame_height = frame.shape[0] // 3
        frame = cv2.resize(frame, (frame_width, frame_height))
        height, width, _ = frame.shape

        # Prepare the frame for YOLO
        blob = cv2.dnn.blobFromImage(frame, 0.00392, (416, 416), (0, 0, 0), True, crop=False)
        self.net.setInput(blob)
        outs = self.net.forward(self.output_layers)

        # Process detections
        class_ids, confidences, boxes = self.get_detections(outs, width, height)

        # Non-max suppression
        indexes = cv2.dnn.NMSBoxes(boxes, confidences, self.confidence_threshold, self.nms_threshold)

        for i in range(len(boxes)):
            if i in indexes:
                x, y, w, h = boxes[i]
                label = str(self.classes[class_ids[i]])

                # Draw a few larger boxes
                num_large_boxes = random.randint(2, 3)
                for lb in range(num_large_boxes):
                    # Large box size and position (vary a bit, allow to go a bit outside)
                    lw = random.randint(int(w * 0.5), int(w * 0.9))
                    lh = random.randint(int(h * 0.5), int(h * 0.9))
                    lx = random.randint(x - int(w * 0.1), x + w - int(lw * 0.9))
                    ly = random.randint(y - int(h * 0.1), y + h - int(lh * 0.9))
                    # color = (
                    #     random.randint(120, 255),
                    #     random.randint(120, 255),
                    #     random.randint(120, 255)
                    # )
                    color = (0, 0, 0)
                    cv2.rectangle(frame, (lx, ly), (lx + lw, ly + lh), color, 2)

                    # Draw smaller, overlapping boxes inside (and a bit outside) the large box
                    num_small_boxes = random.randint(3, 6)
                    for sb in range(num_small_boxes):
                        sw = random.randint(int(lw * 0.2), int(lw * 0.5))
                        sh = random.randint(int(lh * 0.2), int(lh * 0.5))
                        # Allow small boxes to overlap and go a bit outside the large box
                        sx = random.randint(lx - int(sw * 0.2), lx + lw - int(sw * 0.8))
                        sy = random.randint(ly - int(sh * 0.2), ly + lh - int(sh * 0.8))
                        # scolor = (
                        #     min(max(color[0] + random.randint(-40, 40), 0), 255),
                        #     min(max(color[1] + random.randint(-40, 40), 0), 255),
                        #     min(max(color[2] + random.randint(-40, 40), 0), 255)
                        # )
                        scolor = (0, 0, 0)
                        # Flicker effect: show/hide some boxes
                        if random.random() > 0.3:
                            cv2.rectangle(frame, (sx, sy), (sx + sw, sy + sh), scolor, 1)

                # Optionally, still show the label
                cv2.putText(frame, label, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

        return frame

    def get_detections(self, outs, width, height):
        class_ids = []
        confidences = []
        boxes = []

        for out in outs:
            for detection in out:
                scores = detection[5:]
                class_id = np.argmax(scores)
                confidence = scores[class_id]
                if confidence > self.confidence_threshold:
                    center_x = int(detection[0] * width)
                    center_y = int(detection[1] * height)
                    w = int(detection[2] * width)
                    h = int(detection[3] * height)

                    x = int(center_x - w / 2)
                    y = int(center_y - h / 2)

                    boxes.append([x, y, w, h])
                    confidences.append(float(confidence))
                    class_ids.append(class_id)

        return class_ids, confidences, boxes


# me - this DAT
# scriptOp - the OP which is cooking

# press 'Setup Parameters' in the OP to call this function to re-create the parameters.
def onSetupParameters(scriptOp):
	page = scriptOp.appendCustomPage('Custom')
	p = page.appendFloat('Valuea', label='Value A')
	p = page.appendFloat('Valueb', label='Value B')
	return

# called whenever custom pulse parameter is pushed
def onPulse(par):
	return

detector = YOLOVideoDetector(model_type="yolov3")

def onCook(scriptOp):
    detector.process_video(scriptOp)
    return
