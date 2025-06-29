# CPU-Optimized Intelligent Proctoring System

An efficient online exam proctoring system designed to run smoothly on CPU systems. This system provides automated proctoring capabilities through:

## Key Features

1. **Face Detection and Authentication**
   - Real-time face detection
   - Face verification against registered images
   - Multiple face detection prevention

2. **Behavior Monitoring**
   - Head pose estimation
   - Eye tracking and blink detection
   - Phone and object detection
   - Multiple person detection

3. **System Requirements**
   - Python 3.8+
   - Webcam
   - CPU with minimum 4 cores (Intel i5/AMD Ryzen 5 or better recommended)
   - 8GB RAM minimum

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/cpu-proctoring-system.git
cd cpu-proctoring-system
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Project Structure

```
cpu-proctoring-system/
├── src/
│   ├── auth/            # Authentication modules
│   ├── detection/       # Detection algorithms
│   ├── monitoring/      # Behavior monitoring
│   └── utils/          # Utility functions
├── static/             # Static files
├── templates/          # HTML templates
├── tests/             # Unit tests
└── app.py             # Main application
```

## Usage

1. Start the application:
```bash
python app.py
```

2. Open your browser and navigate to `http://localhost:5000`

## Performance Optimizations

This system is specifically optimized for CPU usage through:
- Efficient model selection for face detection and recognition
- Optimized image processing pipeline
- Reduced resolution processing where appropriate
- Batch processing for multiple detections

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 

## Goal
Build a CBT system with integrated AI-based proctoring:
- Face detection and multiple faces alert
- Mobile phone detection
- Noise detection
- Admin dashboard receives real-time alerts
- Frontend connects webcam and SocketIO to backend

# CBT + AI Proctoring System (Flask-based)

Features:
- Face detection for student identity verification
- Live webcam feed using OpenCV
- Audio monitoring for suspicious sound
- Admin receives alerts in real-time
- CBT interface loads MCQ questions
- SocketIO send cheating alerts
