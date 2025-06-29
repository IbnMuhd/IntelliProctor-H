import cv2

for i in range(5):
    cap = cv2.VideoCapture(i)
    if cap.isOpened():
        print(f"Camera index {i} is available.")
        ret, frame = cap.read()
        if ret:
            print(f"Frame captured from camera {i}.")
            cv2.imshow(f'Camera {i}', frame)
            cv2.waitKey(0)
            cv2.destroyAllWindows()
        cap.release()
    else:
        print(f"Camera index {i} not available.")