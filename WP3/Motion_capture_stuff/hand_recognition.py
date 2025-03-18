import cv2
import mediapipe as mp
from pythonosc.udp_client import SimpleUDPClient
import time
from pathlib import Path

pTime = 0
cTime = 0

lmkNames = ["wrist", "thumb_cmc", "thumb_mcp", "thumb_ip", "thumb_tip",
            "index_finger_mcp", "index_finger_pip", "index_finger_dip", "index_finger_tip",
            "middle_finger_mcp", "middle_finger_pip", "middle_finger_dip", "middle_finger_tip",
            "ring_finger_mcp", "ring_finger_pip", "ring_finger_dip", "ring_finger_tip",
            "pinky_mcp", "pinky_pip", "pinky_dip", "pinky_tip"]

lmksToDraw = [0, 4, 8, 12, 16, 20]

# Set the IP and port (MaxMSP listens on port 7400)
ip = "127.0.0.1"
port = 7400

BaseOptions = mp.tasks.BaseOptions
GestureRecognizer = mp.tasks.vision.GestureRecognizer
GestureRecognizerOptions = mp.tasks.vision.GestureRecognizerOptions
GestureRecognizerResult = mp.tasks.vision.GestureRecognizerResult
VisionRunningMode = mp.tasks.vision.RunningMode

# Create a gesture recognizer instance with the video

with open(str(Path("./gesture_recognizer.task").resolve()), 'rb') as file:
    model_data = file.read()

    options = GestureRecognizerOptions(
        base_options=BaseOptions(model_asset_buffer=model_data),
        running_mode=VisionRunningMode.VIDEO,
        num_hands=2)
    with GestureRecognizer.create_from_options(options) as recognizer:

        cap = cv2.VideoCapture(0)

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1024)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 768)

        client = SimpleUDPClient(ip, port) # Create an OSC client

        startTime = time.time()

        while True:
            success, img = cap.read()
            h, w, c = img.shape
            imgRGBified = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=imgRGBified)

            cTime = time.time()
            fps = 1 / (cTime - pTime)
            pTime = cTime

            result = recognizer.recognize_for_video(mp_image, int((cTime - startTime) * 1000))

            # send number of hands
            client.send_message("/numHands", [len(result.hand_world_landmarks)])

            # hand landmarks
            handID = 0
            for hand in result.hand_landmarks:
                id = 0
                for landmark in hand:
                    client.send_message("/" + lmkNames[id] + "_" + str(handID), [int(landmark.x * 1000), int(landmark.y * 1000), int(landmark.z * 1000)])
                    # draw landmarks in video output
                    if id in lmksToDraw:
                        cx, cy = int(landmark.x * w), int(landmark.y * h)
                        cv2.circle(img, (cx, cy), 5, (255, 0, 255), cv2.FILLED)

                    id = id + 1
                handID = handID + 1

            img = cv2.flip(img, 1)

            # gestures
            handID = 0
            for hand in result.gestures:
                client.send_message("/gesture" + "_" + str(handID), [hand[0].category_name])
                cv2.putText(img, hand[0].category_name, (10, (handID + 1) * 80), cv2.FONT_HERSHEY_PLAIN, 3, (255, 0, 255), 3)
                handID = handID + 1

            # handedness
            handID = 0
            for hand in result.handedness:
                #print(hand[0].category_name)
                client.send_message("/handedness" + "_" + str(handID), [hand[0].category_name])
                #cv2.putText(img, hand[0].category_name, (10, (handID + 1) * 80), cv2.FONT_HERSHEY_PLAIN, 3, (255, 0, 255), 3)
                handID = handID + 1

            # show video output
            cv2.putText(img, str(int(fps)), (10, 30), cv2.FONT_HERSHEY_PLAIN, 2, (0, 255, 0), 3)
            cv2.imshow("Image", img)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break

cap.release()
cv2.destroyAllWindows()
