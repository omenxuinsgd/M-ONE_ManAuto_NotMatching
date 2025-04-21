# ✨ Smart Motor Control with Biometric Authentication  (Haven't Matching) ✨

![GitHub Logo](https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png)

## 🌟 Overview
**Smart Motor Control with Biometric Authentication** adalah aplikasi berbasis Python yang memadukan teknologi biometrik (deteksi wajah & verifikasi sidik jari), kontrol motor otomatis/manual, serta GUI modern berbasis PyQt6.

Proyek ini memanfaatkan **MediaPipe**, **DeepFace**, **OpenCV**, dan **Arduino** untuk memberikan solusi kontrol motor yang cerdas dan aman.

---

## 🔍 Fitur Utama
- ✨ **Deteksi Wajah Otomatis**  
  Motor bergerak naik/turun berdasarkan posisi wajah pengguna dalam kamera.

- 🔑 **Verifikasi Sidik Jari**  
  Autentikasi pengguna dengan sensor fingerprint. Hanya pengguna terverifikasi yang dapat mengaktifkan motor.

- ✅ **Kontrol Manual**  
  Kontrol langsung motor melalui tombol GUI: "↑", "⏹️", "↓".

- 🌐 **Antarmuka Modern**  
  GUI responsif dan intuitif dibangun dengan PyQt6.

- ⚙️ **Komunikasi dengan Arduino**  
  Perintah motor dikirim melalui koneksi serial untuk kontrol fisik secara real-time.

---

## 🚀 Getting Started

### 🔗 Prasyarat
Pastikan Anda telah menginstal:
- Python >= 3.8
- OpenCV: `pip install opencv-python`
- PyQt6: `pip install PyQt6`
- MediaPipe: `pip install mediapipe`
- DeepFace: `pip install deepface`
- PySerial: `pip install pyserial`
- Driver Fingerprint DLL: `dpfpdd.dll` & `dpfj.dll` di direktori proyek

### 📂 Instalasi
```bash
git clone https://github.com/yourusername/smart-motor-control.git
cd smart-motor-control
pip install -r requirements.txt
```

### 🔧 Konfigurasi
- Hubungkan sensor sidik jari & Arduino ke komputer.
- Ubah konfigurasi port Arduino di `main.py`:
  ```python
  self.arduino = serial.Serial('COM14', 115200)
  ```

### 📁 Jalankan Aplikasi
```bash
python main.py
```

---

## 📄 Struktur Proyek
```
smart-motor-control/
├── main.py                # File utama aplikasi
├── dpfpdd.dll             # Driver fingerprint
├── dpfj.dll               # Driver tambahan fingerprint
├── requirements.txt       # Daftar dependencies
└── README.md              # Dokumentasi
```

---

## 💡 Cara Kerja

### 1. Deteksi Wajah Otomatis
Menggunakan MediaPipe + DeepFace untuk melacak wajah. Motor bergerak secara dinamis untuk menjaga wajah tetap di tengah frame.

### 2. Verifikasi Sidik Jari
Jika sidik jari sesuai, maka akses motor diberikan. Menjamin keamanan pengguna.

### 3. Kontrol Manual
GUI menyediakan kontrol motor:
- "↑" untuk naik
- "⏹️" untuk berhenti
- "↓" untuk turun

### 4. Komunikasi Arduino
Melalui komunikasi serial, instruksi dari GUI atau hasil deteksi dikirim ke Arduino untuk menggerakkan motor.

---

## 🎨 Screenshots
*(Tambahkan gambar antarmuka, deteksi wajah, dan verifikasi sidik jari di sini)*

---

## 😝 Contributing
Kontribusi sangat dihargai!
Silakan buat **Pull Request** atau buka **Issues** untuk laporan bug dan fitur baru.

---

## 📝 License
Proyek ini menggunakan lisensi **MIT License**. Lihat file `LICENSE` untuk info lengkap.

---

## 📞 Kontak
**Email:** nur_rokhman@majore.id 
**LinkedIn:** [Your LinkedIn Profile](https://www.linkedin.com/in/notfound)

---

> Powered by Python ♥

