# 🚗 ParkVision

A computer vision-based smart parking lot monitoring system that detects and tracks parking slot occupancy in real-time using OpenCV.

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![OpenCV](https://img.shields.io/badge/OpenCV-4.x-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## ✨ Features

- **Real-time Parking Detection** - Analyzes video feeds to detect occupied and free parking slots
- **Visual Slot Marker Tool** - Interactive tool to define parking slot boundaries
- **Edge & Pixel Analysis** - Uses Canny edge detection and color variance to determine occupancy
- **REST API** - FastAPI endpoint to query parking status programmatically
- **Live Statistics** - Displays real-time count of free and occupied slots

## 📁 Project Structure

```
ParkVision/
├── parking_analyzer.py    # Main detection script - analyzes video for occupancy
├── slot_marker.py         # Interactive tool to mark parking slot boundaries
├── api.py                 # FastAPI REST endpoint for parking status
├── parking_slots.json     # Stored parking slot coordinates
├── requirements.txt       # Python dependencies
└── README.md
```

## 🚀 Getting Started

### Prerequisites

- Python 3.8 or higher
- A parking lot video file (e.g., `carPark.mp4`)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/MathewX470/ParkVision.git
   cd ParkVision
   ```

2. **Create a virtual environment** (recommended)
   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # Linux/macOS
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

## 📖 Usage

### Step 1: Mark Parking Slots

Before analyzing a video, you need to define the parking slot boundaries:

```bash
python slot_marker.py
```

**Controls:**
| Key | Action |
|-----|--------|
| **Drag** | Draw a rectangle to create a slot |
| **F** | Duplicate the last slot |
| **W/S** | Adjust vertical offset |
| **A/D** | Adjust horizontal offset |
| **U** | Undo last slot |
| **P** | Save and exit |

The slot coordinates are saved to `parking_slots.json`.

### Step 2: Run the Parking Analyzer

Analyze a parking lot video to detect occupancy:

```bash
python parking_analyzer.py
```

- **Green slots** = Free 🟢
- **Red slots** = Occupied 🔴
- Press **ESC** to exit

### Step 3: Query via API (Optional)

Start the FastAPI server to get parking status via REST:

```bash
uvicorn api:app --reload
```

Access the API at: `http://localhost:8000/parking/status`

**Example Response:**
```json
{
  "total_slots": 15,
  "free": 5,
  "occupied": 10
}
```

## ⚙️ How It Works

ParkVision uses a pixel-based analysis approach to determine slot occupancy:

1. **Edge Detection** - Applies Canny edge detection to identify car outlines
2. **Color Variance** - Calculates standard deviation of pixel values
3. **Threshold Comparison** - Empty slots (asphalt) have low edge density and uniform color, while occupied slots (cars) show high edge density and varied colors

```python
# Detection thresholds (adjustable)
edge_threshold = 8      # Edge density percentage
std_threshold = 35      # Color variance threshold
```

## 🎛️ Configuration

You can tune the detection sensitivity by modifying these parameters in `parking_analyzer.py`:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `edge_threshold` | 8 | Minimum edge density % to consider occupied |
| `std_threshold` | 35 | Minimum color std dev to consider occupied |

## 📸 Screenshots

### Interactive Map
![Parking Detection](screenshots/Screenshot_2026-01-31_170504.png)

### Slot Detection View 1
![Slot Detection](screenshots/Screenshot_2026-01-31_170521.png)

### Slot Detection View 2
![Overview](screenshots/image.png)

## 🛠️ Tech Stack

- **OpenCV** - Computer vision and image processing
- **NumPy** - Numerical operations
- **FastAPI** - REST API framework
- **Flask-SocketIO** - Real-time WebSocket support (optional)

## 🤝 Contributing

Contributions are welcome! Feel free to:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.