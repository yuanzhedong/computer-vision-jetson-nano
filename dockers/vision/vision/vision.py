#!/usr/bin/python3

import jetson.inference
import jetson.utils
import sys
import datetime
import os
import threading
import time
import cv2

try:
    IMAGE_OVERLAY = str(os.environ['IMAGE_OVERLAY'])
except KeyError:
    IMAGE_OVERLAY = "box,labels,conf"
try:
    CAMERA_HEIGHT = int(os.environ['CAMERA_HEIGHT'])
except KeyError:
    CAMERA_HEIGHT = 720
try:
    CAMERA_WIDTH = int(os.environ['CAMERA_WIDTH'])
except KeyError:
    CAMERA_WIDTH = 1280
try:
    CAMERA = str(os.environ['CAMERA'])
except KeyError:
    CAMERA = "/dev/video0"
try:
    CONFIDENCE_TRESHOLD = float(os.environ['CONFIDENCE_TRESHOLD'])
except KeyError:
    CONFIDENCE_TRESHOLD = 0.5
try:
    ALPHA_OVERLAY = int(os.environ['ALPHA_OVERLAY'])
except KeyError:
    ALPHA_OVERLAY = 120
try:
    ENABLE_FLASK = str(os.environ['ENABLE_FLASK']).lower() == 'true'
except KeyError:
    ENABLE_FLASK = True

sys.argv.append('--threshold=' + str(CONFIDENCE_TRESHOLD))
sys.argv.append('--alpha=' + str(ALPHA_OVERLAY))
sys.argv.append('--network=ssd-mobilenet-v2')

mobilenet = jetson.inference.detectNet('ssd-mobilenet-v2', sys.argv)
camera = jetson.utils.gstCamera(CAMERA_WIDTH, CAMERA_HEIGHT, CAMERA)
camera.Open()

outputFrame = None

with open('coco-labels', 'r') as fp:
  classes = [line.rstrip('\n') for line in fp.readlines()]

def object_detections(objects, json):
  json['objects'] = {}
  json['objects_count'] = str(len(objects))
  for i,detection in enumerate(objects):
    detect = {}
    detect['width'] = detection.Width
    detect['height'] = detection.Height
    detect['class'] = classes[detection.ClassID]
    detect['confidence'] = detection.Confidence
    detect['center'] = detection.Center
    json['objects'][i] = detect
  return json

def run():
  global outputFrame

  fps = 0
  while True:
    start_time = time.time()

    # get camera frame
    if (ENABLE_FLASK):
      img, width, height = camera.CaptureRGBA(zeroCopy=1)
    else:
      img, width, height = camera.CaptureRGBA(zeroCopy=0)

    # detect objects
    if (ENABLE_FLASK):
      objects = mobilenet.Detect(img, width, height, IMAGE_OVERLAY)
    else:
      objects = mobilenet.Detect(img, width, height, 'none')

    # json detections
    json = {}
    json['datetime'] = str(datetime.datetime.now())
    json = object_detections(objects, json)
    print(json)

    # serve images
    if (ENABLE_FLASK):
      numpy_img = jetson.utils.cudaToNumpy(img, CAMERA_WIDTH, CAMERA_HEIGHT, 4)
      cv2.putText(numpy_img, str(fps) + ' fps', (20, 40), cv2.FONT_HERSHEY_DUPLEX, 1, (209, 80, 0, 255), 3)
      outputFrame = numpy_img
      fps = round(1.0 / (time.time() - start_time), 2)

  camera.Close()