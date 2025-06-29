import cv2
from src.monitoring.behavior_monitor import BehaviorMonitor

def alert_callback(alert_type, details=None):
    print(f"[ALERT] {alert_type}: {details if details else ''}")

def main():
    monitor = BehaviorMonitor(alert_callback=alert_callback)
    cap = cv2.VideoCapture(0)
    print("Press 'q' to quit.")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to capture frame from camera.")
            break

        # Run behavior monitoring on the frame
        monitor.process_frame(frame)

        # Show the frame (optional)
        cv2.imshow("Behavior Monitor Test", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()