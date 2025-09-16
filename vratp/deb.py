import os
import re
import cv2
import numpy as np
import json
import pandas as pd
from fuzzywuzzy import process
import easyocr
# from flask import Flask, request, jsonify # Uncomment if using Flask
# from flask_cors import CORS # Uncomment if using Flask
import copy

# ===================================================================
# 1. INISIALISASI GLOBAL
# ===================================================================

datasetdir = "dataset" 
datadir = 'data'

print("[INIT] Memulai inisialisasi global...")

# app = Flask(__name__) # Uncomment if using Flask
# CORS(app) # Uncomment if using Flask

print("[INIT] Memuat model EasyOCR...")
ereader = easyocr.Reader(['id'], gpu=False)
print("[INIT] Model EasyOCR siap.")

ktp_fields = [
    "provinsi", "kabupaten", "kota", "nik", "nama", "tempat tgl lahir", "tempat lahir", "tanggal lahir",  "jenis kelamin",
    'gol darah', "alamat", "rt/rw", "kel/desa", "kecamatan", "agama", "status perkawinan",
    "pekerjaan", "kewarganegaraan", "berlaku hingga"
]

agamaval = ["ISLAM", "KRISTEN", "KATOLIK", "HINDU", "BUDDHA", "KHONGHUCU"]
jobval = ["PELAJAR/MAHASISWA", "MENGURUS RUMAH TANGGA", "KARYAWAN SWASTA", "WIRASWASTA",
    "PEGAWAI NEGERI SIPIL", "BELUM/TIDAK BEKERJA"]
citizenval = ["WNI", "WNA"]
untilval = ["SEUMUR HIDUP"]

#init array mapping
arrktpdata = [None]*44
i = 0
for f in ktp_fields :
    arrktpdata[i] = f
    i +=2

ktpdata = {}
wordmatched = set()
fieldset = set()

try:
    print("[INIT] Memuat file CSV...")
    prov_df = pd.read_csv(os.path.join(datasetdir, 'provinsi.csv'))
    
    kabkota_df = pd.read_csv(os.path.join(datasetdir, 'kabupaten_kota.csv'))
    kabkota_dict = kabkota_df.set_index('name')['id'].astype(str).to_dict()

    kec_df = pd.read_csv(os.path.join(datasetdir, 'kecamatan.csv'))
    listnamakec = list(kec_df['name'].values)
    kec_dict = kec_df.set_index('name')['id'].astype(str).to_dict()

    kel_df = pd.read_csv(os.path.join(datasetdir, 'kelurahan.csv'))
    listnamakel = list(kel_df['name'].values)
    kel_dict = kel_df.set_index('name')['id'].astype(str).to_dict()
    
    print("[INIT] ✅ Semua file CSV berhasil dimuat.")
except FileNotFoundError as e:
    print(f"FATAL ERROR: Pastikan file CSV ada di folder 'dataset/'. Detail: {e}")
    exit()

print("[INIT] Inisialisasi global selesai.")

# ===================================================================
# 2. FUNGSI-FUNGSI MURNI
# ===================================================================

def straighten_ktp(img_path, save_path=None, canny_thresh1=50, canny_thresh2=150, hough_thresh=200):
    """
    Meluruskan gambar KTP dengan deteksi garis (Hough Transform).
    """
    img = cv2.imread(img_path)
    if img is None:
        raise FileNotFoundError(f"Gagal load gambar: {img_path}")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, canny_thresh1, canny_thresh2, apertureSize=3)

    lines = cv2.HoughLines(edges, 1, np.pi/180, hough_thresh)
    if lines is None:
        raise ValueError("Tidak ditemukan garis pada gambar, coba ubah threshold.")

    rho, theta = lines[0][0]
    angle = np.degrees(theta)

    if angle > 45:
        angle -= 90

    (h, w) = img.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

    if save_path is not None:
        cv2.imwrite(save_path, rotated)

    return rotated, angle


def imgocr(image_bytes: bytes) -> dict:
    print("\n[START] --- Memulai Fungsi imgocr ---")
    imgori = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
    print("[DEBUG] 📸 Gambar berhasil di-decode oleh OpenCV.")
    
    reseasy = ereader.readtext(imgori)
    print(f"[DEBUG] 👁️ EasyOCR menemukan {len(reseasy)} blok teks.")
    
    outeasy = {}
    confeasy = []
    
    img_with_boxes = imgori.copy()
    bbox_color = (0, 255, 0)  
    text_color = (0, 0, 255)  
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.5
    font_thickness = 1
    
    for (bbox, txt, confs) in reseasy:
        outeasy[txt] = confs
        confeasy.append(confs)
        
        top_left = tuple(map(int, bbox[0]))
        bottom_right = tuple(map(int, bbox[2]))
        cv2.rectangle(img_with_boxes, top_left, bottom_right, bbox_color, 2)
        text_pos = (top_left[0], top_left[1] - 10 if top_left[1] - 10 > 10 else top_left[1] + 20)
        cv2.putText(img_with_boxes, txt, text_pos, font, font_scale, text_color, font_thickness, cv2.LINE_AA)
        
    outeasy['avgconfscore'] = float(np.mean(confeasy)) if confeasy else 0.0
    
    is_success, im_buf_arr = cv2.imencode(".jpg", img_with_boxes)
    if is_success:
        outeasy['image_with_boxes_bytes'] = im_buf_arr.tobytes()
        print("[DEBUG] 🖼️ Gambar dengan bounding box berhasil di-encode.")
    else:
        print("[ERROR] Gagal meng-encode gambar dengan bounding box.")
        outeasy['image_with_boxes_bytes'] = None 
        
    print("[END] --- Selesai Fungsi imgocr ---")
    return outeasy


def dictToList(ocrdict):
    return [key for key in ocrdict if key not in ['avgconfscore', 'image_with_boxes_bytes']]


# ===================================================================
# 3. TESTING LOKAL
# ===================================================================
print("\n[TESTING] Rozpoczynanie lokalnego biegu testowego...")

test_image_path = os.path.join(datadir, 'ktp514.jpg')

# 1. Luruskan dulu
# rotated_img, angle = straighten_ktp(test_image_path, save_path="ktp514_lurus.jpg")
# print(f"[TESTING] Gambar diluruskan dengan sudut {angle:.2f}° dan disimpan ke ktp514_lurus.jpg")

# # 2. OCR pakai gambar hasil rotasi
_, buf = cv2.imencode(".jpg", cv2.imread(test_image_path))
# ocr_results = imgocr(buf.tobytes())
ocr_results = imgocr(buf.tobytes())
txtocr = dictToList(ocr_results)
print(f"hasil ocr mentah : \n{txtocr}\n\n")

if 'image_with_boxes_bytes' in ocr_results and ocr_results['image_with_boxes_bytes'] is not None:
    output_image_path = f'output_514_with_boxes.jpg'
    with open(output_image_path, 'wb') as f:
        f.write(ocr_results['image_with_boxes_bytes'])
    print(f"[TESTING] Gambar dengan bounding box disimpan ke: {output_image_path}")
else:
    print("[TESTING] Tidak ada gambar dengan bounding box yang dihasilkan.")

print("\n[TESTING] Selesai.")
