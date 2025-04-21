import sys
import cv2
import serial
import mediapipe as mp
import numpy as np
from PyQt6.QtWidgets import QApplication, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QSlider, QFrame, QComboBox
from PyQt6.QtGui import QImage, QPixmap, QIcon
from PyQt6.QtCore import Qt, QTimer
import os
import ctypes
from ctypes import (
    c_int, c_uint, c_void_p, c_char, c_char_p,
    POINTER, Structure, byref, cast, create_string_buffer, c_ubyte
)
import time
from deepface import DeepFace


os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'

# Load DLL
try:
    dpfpdd = ctypes.WinDLL('dpfpdd.dll')
    dpfj = ctypes.CDLL("dpfj.dll")
except OSError:
    print("[ERROR] Tidak dapat memuat dpfpdd.dll. Pastikan DLL tersedia.")
    exit(1)

# Inisialisasi MediaPipe
mp_holistic = mp.solutions.holistic
mp_hands = mp.solutions.hands
# mp_face_mesh = mp.solutions.face_mesh
mp_drawing = mp.solutions.drawing_utils
mp_face = mp.solutions.face_detection

# Initialize MediaPipe Holistic
mp_holistic = mp.solutions.holistic
holistic = mp_holistic.Holistic(min_detection_confidence=0.5, min_tracking_confidence=0.5, enable_segmentation=False, refine_face_landmarks=False)
# MediaPipe Hands dan Face Mesh
hands = mp_hands.Hands(min_detection_confidence=0.5, min_tracking_confidence=0.5)
# face_mesh = mp_face_mesh.FaceMesh(min_detection_confidence=0.5, min_tracking_confidence=0.5)
mp_pose = mp.solutions.pose
pose = mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)
face_detection = mp_face.FaceDetection(min_detection_confidence=0.5)

# Initialize Optical Flow parameters
feature_params = dict(maxCorners=100, qualityLevel=0.3, minDistance=7, blockSize=7)
lk_params = dict(winSize=(15, 15), maxLevel=2, criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03))
prev_gray = None
prev_points = None

# # Status motor
# motor_state = "STOP"

# Define constants and data types from the header files
DPFPDD_QUALITY_GOOD = 0
DPFPDD_SUCCESS = 0
DPFPDD_IMG_FMT_ANSI381 = 0x001B0401
MAX_FMD_SIZE = 1024 * 10  # Adjust size if necessary

# =============================================
# 1. Definisi Semua Struktur dari Header C
# =============================================
class DPFPDD_VER_INFO(Structure):
    _fields_ = [
        ("major", c_int),
        ("minor", c_int),
        ("maintenance", c_int)
    ]

class DPFPDD_VERSION(Structure):
    _fields_ = [
        ("size", c_uint),
        ("lib_ver", DPFPDD_VER_INFO),
        ("api_ver", DPFPDD_VER_INFO)
    ]

class DPFPDD_HW_DESCR(Structure):
    _fields_ = [
        ("vendor_name", c_char * 128),
        ("product_name", c_char * 128),
        ("serial_num", c_char * 128)
    ]

class DPFPDD_HW_ID(Structure):
    _fields_ = [
        ("vendor_id", c_uint),
        ("product_id", c_uint)
    ]

class DPFPDD_HW_VERSION(Structure):
    _fields_ = [
        ("hw_ver", DPFPDD_VER_INFO),
        ("fw_ver", DPFPDD_VER_INFO),
        ("bcd_rev", c_uint)
    ]

class DPFPDD_DEV_INFO(Structure):
    _fields_ = [
        ("size", c_uint),
        ("name", c_char * 1024),
        ("descr", DPFPDD_HW_DESCR),
        ("id", DPFPDD_HW_ID),
        ("ver", DPFPDD_HW_VERSION),
        ("modality", c_uint),
        ("technology", c_uint)
    ]

class DPFPDD_DEV(Structure):
    pass

class DPFPDD_CAPTURE_PARAM(Structure):
    _fields_ = [
        ("size", c_uint),
        ("image_fmt", c_uint),
        ("image_proc", c_uint),
        ("image_res", c_uint)
    ]

class DPFPDD_IMAGE_INFO(Structure):
    _fields_ = [
        ("size", c_uint),
        ("width", c_uint),
        ("height", c_uint),
        ("res", c_uint),
        ("bpp", c_uint)
    ]

class DPFPDD_CAPTURE_RESULT(Structure):
    _fields_ = [
        ("size", c_uint),
        ("success", c_int),
        ("quality", c_uint),
        ("score", c_uint),
        ("info", DPFPDD_IMAGE_INFO)
    ]

class DPFPDD_DEV_CAPS(Structure):
    _fields_ = [
        ("size", c_uint),
        ("can_capture_image", c_int),
        ("can_stream_image", c_int),
        ("can_extract_features", c_int),
        ("can_match", c_int),
        ("can_identify", c_int),
        ("has_fp_storage", c_int),
        ("indicator_type", c_uint),
        ("has_pwr_mgmt", c_int),
        ("has_calibration", c_int),
        ("piv_compliant", c_int),
        ("resolution_cnt", c_uint),
        ("resolutions", c_uint * 1)  # Array of resolutions
    ]

# =============================================
# 2. Inisialisasi Fungsi DLL
# =============================================
dpfpdd.dpfpdd_version.argtypes = [POINTER(DPFPDD_VERSION)]
dpfpdd.dpfpdd_version.restype = c_int

dpfpdd.dpfpdd_init.restype = c_int
dpfpdd.dpfpdd_exit.restype = c_int

dpfpdd.dpfpdd_query_devices.argtypes = [POINTER(c_uint), POINTER(DPFPDD_DEV_INFO)]
dpfpdd.dpfpdd_query_devices.restype = c_int

dpfpdd.dpfpdd_open.argtypes = [c_char_p, POINTER(POINTER(DPFPDD_DEV))]
dpfpdd.dpfpdd_open.restype = c_int

dpfpdd.dpfpdd_get_device_capabilities.argtypes = [POINTER(DPFPDD_DEV), POINTER(DPFPDD_DEV_CAPS)]
dpfpdd.dpfpdd_get_device_capabilities.restype = c_int

dpfpdd.dpfpdd_start_stream.argtypes = [POINTER(DPFPDD_DEV)]
dpfpdd.dpfpdd_start_stream.restype = c_int

dpfpdd.dpfpdd_stop_stream.argtypes = [POINTER(DPFPDD_DEV)]
dpfpdd.dpfpdd_stop_stream.restype = c_int

dpfpdd.dpfpdd_get_stream_image.argtypes = [
    POINTER(DPFPDD_DEV),
    POINTER(DPFPDD_CAPTURE_PARAM), 
    POINTER(DPFPDD_CAPTURE_RESULT), 
    POINTER (c_uint),
    c_void_p]
dpfpdd.dpfpdd_get_stream_image.restype = c_int

dpfpdd.dpfpdd_capture.argtypes = [
    POINTER(DPFPDD_DEV),
    POINTER(DPFPDD_CAPTURE_PARAM),
    c_uint,
    POINTER(DPFPDD_CAPTURE_RESULT),
    POINTER(c_uint),
    c_void_p
]
dpfpdd.dpfpdd_capture.restype = c_int

class MainApp(QWidget):
    def __init__(self):
        super().__init__()
        # === SETUP SERIAL UNTUK ARDUINO ===
        self.arduino = serial.Serial('COM14', 115200, timeout=1)  # Ganti COM3 sesuai port Arduino
        # Status motor
        self.motor_state = "STOP"
        # === SETUP KAMERA ===
        self.camera = cv2.VideoCapture(2)  # 0 untuk kamera default
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        # === SETUP FINGERPRINT DEVICE ===
        self.dev_handle = None
        self.init_fingerprint_device()
        # === WIDGETS ===
        self.video_label = QLabel("Display Video Capture Camera")
        self.video_label.setFixedSize(640, 300)  # Set ukuran label video
        self.fingerprint_label = QLabel("Display Capture Fingerprint", alignment=Qt.AlignmentFlag.AlignCenter)
        self.fingerprint_label.setFixedSize(640, 240)  # Set ukuran label fingerprint

        # === BUTTONS FOR MOTOR CONTROL ===
        self.up_button = QPushButton("↑")
        self.stop_button = QPushButton("⏹️")
        self.down_button = QPushButton("↓")
        
        self.data_label = QLabel("Data Information")
        self.data_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.data_label.setFixedSize(600, 20)
        self.preview_label = QLabel()
        self.preview_label.setFixedSize(300, 240)  # Ukuran tetap agar tidak mengganggu slider
        self.preview_label.setStyleSheet("border: 1px solid black;")
        # Preview label untuk gambar dari folder (sebelah kanan)
        self.folder_preview_label = QLabel()
        self.folder_preview_label.setFixedSize(300, 240)
        self.folder_preview_label.setStyleSheet("border: 1px solid black;")
        # Label tambahan untuk menampilkan gambar kedua dari folder
        self.preview_label_folder2 = QLabel()
        self.preview_label_folder2.setFixedSize(320, 240)
        self.preview_label_folder2.setStyleSheet("border: 1px solid black;")

        # Label teks tambahan untuk menjelaskan gambar dari folder
        self.text_label = QLabel("Kecocokan Gambar Sangat Match 100%")
        self.text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Set button styles
        self.up_button.setFixedSize(100, 50)
        self.stop_button.setFixedSize(100, 50)
        self.down_button.setFixedSize(100, 50)

        self.up_button.clicked.connect(self.move_up)
        self.stop_button.clicked.connect(self.stop_motor)
        self.down_button.clicked.connect(self.move_down)

        # === COMBOBOX FOR MODE SELECTION ===
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Manual", "Automatic"])
        self.mode_combo.currentIndexChanged.connect(self.toggle_mode)

        # === TIMER UNTUK UPDATE VIDEO DAN FINGERPRINT ===
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)  # Update setiap 30ms

        # === LAYOUT ===
        # Left layout (Camera and floating elements)
        left_layout = QVBoxLayout()
        left_layout.addWidget(self.video_label)
        left_layout.addWidget(self.fingerprint_label)

        # Right layout (Data information and preview)
        right_layout = QVBoxLayout()
        right_layout.setSpacing(0)
        right_layout.addWidget(self.data_label)
        # Layout untuk dua preview (hasil capture kiri, gambar dari folder kanan)
        preview_layout = QHBoxLayout()
        preview_layout.addWidget(self.preview_label)
        preview_layout.addWidget(self.folder_preview_label)
        right_layout.addLayout(preview_layout)
        right_layout.addWidget(self.preview_label_folder2, alignment=Qt.AlignmentFlag.AlignHCenter)
        right_layout.addWidget(self.text_label)
        self.text_label.setVisible(False)

        # Add motor control layout to the main layout
        main_layout = QHBoxLayout()
        main_layout.addLayout(left_layout)
        main_layout.addLayout(right_layout)

        self.setLayout(main_layout)
        self.setWindowIcon(QIcon("majore.png"))
        self.setWindowTitle("nice to MIT you... anjay!")
        self.setGeometry(100, 100, 800, 600)

        # Position buttons over the video label
        self.position_buttons()

        # Position the mode combo box above the video label
        self.mode_combo.setParent(self.video_label)
        self.mode_combo.move(520, 0)  # Adjust the position as needed

        # Initialize button states based on the default mode
        self.toggle_mode()

    def position_buttons(self):
        # Set the buttons as children of the video label
        self.up_button.setParent(self.video_label)
        self.stop_button.setParent(self.video_label)
        self.down_button.setParent(self.video_label)

        # Set button positions (absolute positioning)
        self.up_button.move(520, 40)    # Adjust the position as needed
        self.stop_button.move(520, 100)  # Adjust the position as needed
        self.down_button.move(520, 160)  # Adjust the position as needed

    def toggle_mode(self):
        if self.mode_combo.currentText() == "Automatic":
            self.up_button.setEnabled(False)
            self.stop_button.setEnabled(False)
            self.down_button.setEnabled(False)
        else:
            self.up_button.setEnabled(True)
            self.stop_button.setEnabled(True)
            self.down_button.setEnabled(True)

    def move_up(self):
        # Pastikan motor berhenti dulu sebelum bergerak
        self.stop_motor()
        time.sleep(0.1)  # Delay kecil untuk memastikan motor berhenti
        
        self.motor_state = "UP"
        if self.arduino:
            self.arduino.write((self.motor_state + "\n").encode())
        print("Motor naik")

    def stop_motor(self):
        self.motor_state = "STOP"
        if self.arduino:
            self.arduino.write((self.motor_state + "\n").encode())
        print("Motor berhenti")

    def move_down(self):
        # Pastikan motor berhenti dulu sebelum bergerak
        self.stop_motor()
        time.sleep(0.1)  # Delay kecil untuk memastikan motor berhenti
        
        self.motor_state = "DOWN"
        if self.arduino:
            self.arduino.write((self.motor_state + "\n").encode())
        print("Motor turun")
    # ... (rest of your existing methods remain unchanged)

    def capture_verification_frame(self):
        ret, frame = self.camera.read()
        if ret:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame = cv2.flip(frame, 1)
            h, w, ch = frame.shape
            bytes_per_line = ch * w
            qimg = QImage(frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            self.preview_label.setPixmap(QPixmap.fromImage(qimg).scaled(320, 240, Qt.AspectRatioMode.IgnoreAspectRatio))

    def on_floating_button_click(self):
        self.capture_verification_frame()
        self.load_image_from_folder()

    def load_image_from_folder(self):
        folder_path = "D:\Majore\Riset\mOTOR"  # Ganti dengan path folder yang benar
        if not os.path.isdir(folder_path):
            print(f"Folder '{folder_path}' tidak ditemukan!")
            return

        files = [f for f in os.listdir(folder_path) if f.endswith(('.png', '.jpg', '.jpeg'))]

        if not files:
            print("Tidak ada gambar di folder!")
            return

        # Ambil dua gambar pertama jika ada
        if len(files) > 0:
            image_path1 = os.path.join(folder_path, files[1])
            pixmap1 = QPixmap(image_path1)
            self.folder_preview_label.setPixmap(pixmap1.scaled(320, 240, Qt.AspectRatioMode.KeepAspectRatio))

        if len(files) > 1:
            image_path2 = os.path.join(folder_path, files[2])
            pixmap2 = QPixmap(image_path2)
            self.preview_label_folder2.setPixmap(pixmap2.scaled(320, 240, Qt.AspectRatioMode.KeepAspectRatio))
            self.preview_label_folder2.setVisible(True)  # Munculkan gambar kedua
            # Munculkan teks setelah gambar ditampilkan
            self.text_label.setVisible(True)

    def snap_to_tick(self):
        """Fungsi ini memastikan slider hanya berpindah ke titik tick terdekat."""
        value = self.slider.value()
        snapped_value = round(value / 1000) * 1000
        self.slider.setValue(snapped_value)
        self.slider_label.setText(f"Motor Position: {snapped_value}")
        self.arduino.write(f"POSITION:{snapped_value}\n".encode())        

    def init_fingerprint_device(self):
        if dpfpdd.dpfpdd_init() != 0:
            print("[ERROR] Gagal inisialisasi library")
            return

        version = DPFPDD_VERSION()
        version.size = ctypes.sizeof(DPFPDD_VERSION)
        if dpfpdd.dpfpdd_version(byref(version)) == 0:
            print(f"[INFO] Versi Library: {version.lib_ver.major}.{version.lib_ver.minor}")

        dev_count = c_uint(0)
        res = dpfpdd.dpfpdd_query_devices(byref(dev_count), None)
        if res != 0 and dev_count.value == 0:
            print("[ERROR] Tidak ada perangkat terdeteksi")
            return
        
        print(f"[INFO] Jumlah perangkat: {dev_count.value}")
        
        dev_info_array = (DPFPDD_DEV_INFO * dev_count.value)()
        for dev in dev_info_array:
            dev.size = ctypes.sizeof(DPFPDD_DEV_INFO)
        
        res = dpfpdd.dpfpdd_query_devices(byref (dev_count), dev_info_array)
        if res != 0:
            print("[ERROR] Gagal mendapatkan info perangkat")
            dpfpdd.dpfpdd_exit()
            return

        self.dev_handle = POINTER(DPFPDD_DEV)()
        device_name = cast(dev_info_array[0].name, c_char_p)
        res = dpfpdd.dpfpdd_open(device_name, byref(self.dev_handle))
        if res != 0:
            print("[ERROR] Gagal membuka perangkat")
            dpfpdd.dpfpdd_exit()
            return

        print("[SUCCESS] Perangkat berhasil dibuka")
        dpfpdd.dpfpdd_start_stream(self.dev_handle)

    def update_frame(self):
        # Update frame kamera
        ret, frame = self.camera.read()
        try:
            if ret:
                # Convert frame to RGB
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                results = holistic.process(rgb_frame)
                hand_results = hands.process(rgb_frame)
                # face_results = face_mesh.process(rgb_frame)
                pose_results = pose.process(rgb_frame)
                face_results = face_detection.process(rgb_frame)

                body_detected = False
                hand_detected = False
                # pose_results = False
                # face_detected = False

                # Status deteksi
                face_detected = face_results.detections is not None
                body_detected = pose_results.pose_landmarks is not None

                # Posisi pusat wajah
                face_center_y = None


                # if results.pose_landmarks:
                #     body_detected = True
                #     mp_drawing.draw_landmarks(frame, results.pose_landmarks, mp_holistic.POSE_CONNECTIONS)
                if results.pose_landmarks:
                    mp_drawing.draw_landmarks(frame, results.pose_landmarks, mp_holistic.POSE_CONNECTIONS)

                if results.left_hand_landmarks:
                    hand_detected = True
                    mp_drawing.draw_landmarks(frame, results.left_hand_landmarks, mp_holistic.HAND_CONNECTIONS)
                if results.right_hand_landmarks:
                    hand_detected = True
                    mp_drawing.draw_landmarks(frame, results.right_hand_landmarks, mp_holistic.HAND_CONNECTIONS)

                if hand_results.multi_hand_landmarks:
                    for hand_landmarks in hand_results.multi_hand_landmarks:
                        hand_detected = True
                        mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

                # if face_results.multi_face_landmarks:
                #     face_detected = True

                # Dapatkan ukuran frame
                frame_height, frame_width, _ = frame.shape

                # Tentukan batas deteksi wajah (80% area tengah)
                margin_x = int(frame_width * 0.15)  # 10% dari lebar frame di kiri & kanan
                margin_y = int(frame_height * 0.15)  # 10% dari tinggi frame di atas & bawah
                detection_area = (margin_x, margin_y, frame_width - margin_x, frame_height - margin_y)

                # Deteksi wajah menggunakan backend yang lebih ringan (contoh: 'yunet')
                detected_faces = DeepFace.extract_faces(
                    img_path=frame,
                    detector_backend='yunet',  # Backend deteksi wajah
                    enforce_detection=False,  # Menghindari error jika tidak ada wajah terdeteksi
                    anti_spoofing = True
                )
                # Membuat log data index wajah
                face_log = []
                # print(detected_faces)

                for face in detected_faces:
                    # Pastikan wajah memiliki confidence score yang valid
                    # print(face['is_real'])
                    # if face['is_real'] == True:
                    #     self.arduino.write(f"face detect\n".encode())
                    if face['confidence'] > 0.5:  # Threshold untuk validitas wajah
                        x, y, w, h = (
                            face['facial_area']['x'],
                            face['facial_area']['y'],
                            face['facial_area']['w'],
                            face['facial_area']['h']
                        )
                        confidence = face['confidence']

                        # Hitung ukuran bounding box (luas)
                        bounding_box_size = w * h

                        # Filter wajah yang berada dalam area deteksi
                        if (x > detection_area[0] and 
                            y > detection_area[1] and 
                            x + w < detection_area[2] and 
                            y + h < detection_area[3]):

                            # Simpan wajah yang valid dalam log
                            face_log.append({
                                'bounding_box': (x, y, w, h),
                                'confidence': face['confidence'],
                                'size': bounding_box_size
                            })

                # Urutkan wajah berdasarkan ukuran bounding box (dari besar ke kecil)
                face_log.sort(key=lambda x: x['size'], reverse=True)

                # Tambahkan indeks berdasarkan urutan baru
                for idx, face in enumerate(face_log):
                    face['index'] = idx + 1  # Indeks dimulai dari 1

                # if face_log != []:    
                #     print(face_log)

                # Gambar bounding box dan label indeks hanya untuk wajah dalam area deteksi
                for face in face_log:
                    x, y, w, h = face['bounding_box']
                    idx = face['index']
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    cv2.putText(frame, f"Face {idx}", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
                                
                if face_detected:  # Jika wajah terdeteksi, gunakan ini sebagai referensi
                    for detection in face_results.detections:
                        bboxC = detection.location_data.relative_bounding_box
                        y = int(bboxC.ymin * frame_height)
                        h = int(bboxC.height * frame_height)
                        face_center_y = y + h // 2  # Posisi tengah wajah
                        print(f"🟢 Wajah terdeteksi di Y: {face_center_y}")

                elif body_detected:  # Jika wajah tidak terdeteksi, gunakan pose landmarks
                    nose = pose_results.pose_landmarks.landmark[mp_pose.PoseLandmark.NOSE]
                    left_eye = pose_results.pose_landmarks.landmark[mp_pose.PoseLandmark.LEFT_EYE]
                    right_eye = pose_results.pose_landmarks.landmark[mp_pose.PoseLandmark.RIGHT_EYE]
                    mouth = pose_results.pose_landmarks.landmark[mp_pose.PoseLandmark.MOUTH_LEFT]
                    left_ear = pose_results.pose_landmarks.landmark[mp_pose.PoseLandmark.LEFT_EAR]
                    right_ear = pose_results.pose_landmarks.landmark[mp_pose.PoseLandmark.RIGHT_EAR]

                    # Konversi ke koordinat gambar
                    keypoints = [nose, left_eye, right_eye, mouth, left_ear, right_ear]
                    y_positions = [kp.y * frame_height for kp in keypoints if kp.visibility > 0.5]

                    if y_positions:
                        face_center_y = int(sum(y_positions) / len(y_positions))  # Rata-rata posisi vertikal wajah
                        print(f"🟡 Wajah jauh, menggunakan pose detection di Y: {face_center_y}")

                # Tentukan pergerakan motor berdasarkan posisi wajah
                new_motor_state = "STOP"
                threshold = frame_height // 3

                if face_center_y is not None:
                    if face_center_y < threshold:
                        new_motor_state = "UP"
                        print("⬆️ Wajah terlalu atas → Motor naik")
                    elif face_center_y > 2 * threshold:
                        new_motor_state = "DOWN"
                        print("⬇️ Wajah terlalu bawah → Motor turun")
                    else:
                        if face_center_y < 320 and face_log == []:
                            new_motor_state = "UP"
                            print("⬆️ Wajah terlalu atas → Motor naik")
                        elif face_center_y >= 320 and face_log != []:
                            new_motor_state = "STOP"
                            print("🟩 Wajah dalam posisi tengah → Motor berhenti")
                elif body_detected:
                    new_motor_state = "UP"  # Motor naik sampai menemukan wajah
                    print("🟡 Hanya badan/tangan terdeteksi → Motor naik")

                # Kirim perintah ke Arduino jika status berubah dan mode adalah Automatic
                if self.mode_combo.currentText() == "Automatic":
                    if new_motor_state != self.motor_state:
                        self.motor_state = new_motor_state
                        if self.arduino:
                            self.arduino.write((self.motor_state + "\n").encode())  
                            print(f"📡 Mengirim perintah ke Arduino: {self.motor_state}")

                # Gambar area deteksi sebagai batas panduan
                cv2.rectangle(frame, (margin_x, margin_y), (frame_width - margin_x, frame_height - margin_y), (255, 0, 0), 2)

                # Tampilkan jumlah wajah yang terdeteksi di pojok kiri atas frame
                num_faces = len(face_log)  # Hitung jumlah wajah valid
                cv2.putText(frame, f"Jumlah Wajah: {num_faces}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)
                
                # if results.face_landmarks:
                #     results.face_landmarks.Clear()  # Hapus data landmark wajah

                # Konversi frame dari BGR ke RGB
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                # Membalik gambar secara horizontal
                frame = cv2.flip(frame, 1)  
                h, w, ch = frame.shape
                bytes_per_line = ch * w
                qimg = QImage(frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
                self.video_label.setPixmap(QPixmap.fromImage(qimg).scaled(640, 300, Qt.AspectRatioMode.KeepAspectRatioByExpanding))
        except Exception as e:
            print(f"Error: {e}") 

        capture_param = DPFPDD_CAPTURE_PARAM()
        capture_param.size = ctypes.sizeof(DPFPDD_CAPTURE_PARAM)
        capture_param.image_fmt = DPFPDD_IMG_FMT_ANSI381
        capture_param.image_proc = 2
        capture_param.image_res = 500
        # Update fingerprint
        if self.dev_handle:
            capture_result = DPFPDD_CAPTURE_RESULT()
            capture_result.size = ctypes.sizeof(DPFPDD_CAPTURE_RESULT)
            image_size = c_uint(MAX_FMD_SIZE)
            # image_buffer = create_string_buffer(image_size.value)
            fid_data = POINTER(c_ubyte)()

            res = dpfpdd.dpfpdd_get_stream_image(self.dev_handle, byref(capture_param), byref(capture_result), byref(image_size), fid_data)
            if res is None:
                print(f"[ERROR] Gagal mendapatkan ukuran buffer. Kode: 0x{res:08X}")
                return None, None, None

            if image_size.value == 0:
                print("[ERROR] Ukuran gambar 0 byte, kemungkinan ada kesalahan.")
                return None, None, None
            
            image_buffer = create_string_buffer(image_size.value)
            res = dpfpdd.dpfpdd_get_stream_image(self.dev_handle, byref(capture_param), byref(capture_result), byref(image_size), image_buffer)
            # Debugging: Print capture result and dimensions
            print(f"[DEBUG] Capture Result: Success: {capture_result.success}, Width: {capture_result.info.width}, Height: {capture_result.info.height}")
            
            if res == DPFPDD_SUCCESS and capture_result.success:
                width = capture_result.info.width
                height = capture_result.info.height
                
                # Remove header (first 46 bytes)
                header_size = 50
                if image_size.value < header_size:
                    print(f"[ERROR] Image data size {image_size.value} is smaller than header size {header_size}")
                    return None, None, None
                
                # Get the image data without header
                image_data = image_buffer.raw[header_size:]
                print(f"[DEBUG] Image data size after removing header: {len(image_data)} bytes")
                expected_size = width * height
                
                if width > 0 and height > 0 and len(image_data) >= expected_size:
                    image_array = np.frombuffer(image_data[:expected_size], dtype=np.uint8).reshape((height, width))
                    qimg = QImage(image_array.data, width, height, width, QImage.Format.Format_Grayscale8)
                    self.fingerprint_label.setPixmap(QPixmap.fromImage(qimg).scaled(640, 240, Qt.AspectRatioMode.KeepAspectRatio))
                    # time.sleep(2)
                    
                    print(capture_result.quality)
                    if capture_result.quality == DPFPDD_QUALITY_GOOD:
                        res = dpfpdd.dpfpdd_capture(self.dev_handle, byref(capture_param), -1, byref(capture_result), byref(image_size), image_buffer)
                        self.fingerprint_label.setPixmap(QPixmap.fromImage(qimg).scaled(640, 240, Qt.AspectRatioMode.KeepAspectRatio))
                        self.arduino.write(f"fingerprint verified\n".encode())
                        time.sleep(1)
                else:
                    print("[ERROR] Dimensi gambar tidak valid atau data gambar tidak cukup setelah menghapus header.")
            else:
                print(f"[ERROR] Gagal mengambil gambar dari streaming. Kode: {res}")
                
    def closeEvent(self, event):
        if self.dev_handle:
            dpfpdd.dpfpdd_stop_stream(self.dev_handle)
            dpfpdd.dpfpdd_exit()
        self.camera.release()
        self.arduino.close()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainApp()
    window.show()
    sys.exit(app.exec())