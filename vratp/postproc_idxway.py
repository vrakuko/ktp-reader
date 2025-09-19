
import io
import os
import re
import tempfile
import cv2
import numpy as np
import json
import pandas as pd
from fuzzywuzzy import process
import easyocr
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import re
import copy
import pytesseract
from PIL import Image
import math
import cv2
import numpy as np
import os

from validrombak import validagama, validgender, validkab, validkawin, validkec, validkeldes, validkota, validnama, validnik, validprov, validrtrw, validdarah, validjob, validwn, validberlaku, validgeokk, validgeokec, is_mostly_digits


app = Flask(__name__)
CORS(app)
# basedir = os.path.dirname(os.path.abspath(__file__))
# datasetdir = os.path.join(basedir, 'dataset')

datasetdir = "dataset"

print("[INIT] Memulai inisialisasi global...")


print("[INIT] Memuat model EasyOCR...")
ereader = easyocr.Reader(['id'], gpu=False)



ktp_fields = [
    "provinsi", "kabupaten", "kota", "nik", "nama", "tempat tgl lahir",   "jenis kelamin",
    'gol darah', "alamat", "rt rw", "kel desa", "kecamatan", "agama", "status perkawinan",
    "pekerjaan", "kewarganegaraan", "berlaku hingga"
]

#init array mapping

arrktpdata = [None]*44
i = 0
for f in ktp_fields : 
    arrktpdata[i] = f
    i +=2

ktpdata_global = {}
ktpdata = {}
wordmatched = set()
fieldset = set()


try:
    print("[INIT] Memuat file CSV...")

    # GANTI DENGAN PATH RELATIF UNTUK PORTABILITAS
    prov_df = pd.read_csv(os.path.join(datasetdir, 'provinsi.csv'))
    # prov_df = pd.read_csv('D:/dataset/provinsi.csv')

    # kabkota_df = pd.read_csv('D:/dataset/kabupaten_kota.csv')
    kabkota_df = pd.read_csv(os.path.join(datasetdir, 'kabupaten_kota.csv'))

    # kec_df = pd.read_csv('D:/dataset/kecamatan.csv')
    kec_df = pd.read_csv(os.path.join(datasetdir, 'kecamatan.csv'))

    # kel_df = pd.read_csv('D:/dataset/kelurahan.csv')
    kel_df = pd.read_csv(os.path.join(datasetdir, 'kelurahan.csv'))

    
    print("[INIT] ✅ Semua file CSV berhasil dimuat.")
except FileNotFoundError as e:
    print(f"FATAL ERROR: Pastikan file CSV ada di folder 'data/'. Detail: {e}")
    exit()

print("[INIT] Inisialisasi global selesai.")



# def straighten_ktp(image_bytes: bytes, save_path: str = None, 
def straighten_ktp(image_bytes: bytes, save_path: str = None, 
                   canny_thresh1: int = 50, canny_thresh2: int = 150, 
                   hough_thresh: int = 150, min_line_length: int = 100, max_line_gap: int = 10,
                   min_rotation_angle_threshold: float = 0.5, 
                #    debug_mode: bool = False,
                   # Parameter baru untuk deteksi orientasi Tesseract
                   perform_osd: bool = True, # Apakah akan mencoba mendeteksi orientasi dengan Tesseract
                   osd_pagesegmode: str = '3' # Page segmentation mode untuk OSD (3=full automatic)
                  ):
    """
    Meluruskan (deskew) gambar dokumen dari bytes.
    Termasuk penanganan rotasi 90/180/20 derajat menggunakan Tesseract OSD.
    Mengembalikan numpy.ndarray yang sudah diluruskan dan sudutnya.
    """
    img = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Gagal memuat gambar dari bytes. Pastikan data gambar valid.")

    # --- LANGKAH 1: Deteksi dan Koreksi Orientasi Mayor (0, 90, 180, 20 derajat) ---
    major_rotation_angle = 0.0 # Default: tidak ada rotasi mayor
    if perform_osd:
        try:
            # Pytesseract bekerja dengan PIL Image, jadi konversi dulu
            pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
            
            # Mendapatkan informasi orientasi dan skrip
            # OSD config: --psm <pagesegmode> osdonly
            # psm 0: Orientation and script detection (OSD) only.
            # psm 3: Fully automatic page segmentation, but no OSD. (Default)
            # psm 7: Treat the image as a single text line.
            # psm 8: Treat the image as a single word.
            # Kita ingin mendeteksi orientasi, jadi psm 0 atau 3 (jika psm 3 memberikan OSD)
            osd_data = pytesseract.image_to_osd(pil_img, config=f'--psm {osd_pagesegmode} osdonly')
            
            # Parsing output OSD. Output biasanya seperti:
            # Page number: 0
            # Orientation in degrees: 180
            # Rotate: 180
            # Orientation confidence: 2.12
            # Script: Latin
            # Script confidence: 1.00
            
            rotation_match = next((line for line in osd_data.split('\n') if "Orientation in degrees:" in line), None)
            if rotation_match:
                major_rotation_angle_str = rotation_match.split(': ')[1].strip()
                major_rotation_angle = float(major_rotation_angle_str)
                print(f"[OSD] Orientasi Tesseract terdeteksi: {major_rotation_angle} derajat.")
            
            if major_rotation_angle != 0:
                print(f"[OSD] Melakukan rotasi {major_rotation_angle} derajat berdasarkan OSD.")
                (h_osd, w_osd) = img.shape[:2]
                center_osd = (w_osd // 2, h_osd // 2)
                M_osd = cv2.getRotationMatrix2D(center_osd, major_rotation_angle, 1.0)
                
                # Hitung ukuran bounding box baru setelah rotasi
                cos_osd = np.abs(M_osd[0, 0])
                sin_osd = np.abs(M_osd[0, 1])
                nW_osd = int((h_osd * sin_osd) + (w_osd * cos_osd))
                nH_osd = int((h_osd * cos_osd) + (w_osd * sin_osd))

                M_osd[0, 2] += (nW_osd / 2) - center_osd[0]
                M_osd[1, 2] += (nH_osd / 2) - center_osd[1]

                img = cv2.warpAffine(img, M_osd, (nW_osd, nH_osd), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT, borderValue=(0,0,0))
            
            #if debug_mode and major_rotation_angle != 0:
            if  major_rotation_angle != 0:
                cv2.imshow("After OSD Rotation", img)
                cv2.waitKey(1)

        except pytesseract.TesseractError as e:
            print(f"[OSD] Pytesseract Error: {e}. Melanjutkan tanpa deteksi orientasi mayor.")
        except FileNotFoundError:
            print("[OSD] Tesseract executable not found. Please install Tesseract-OCR and ensure its path is correctly set. Melanjutkan tanpa deteksi orientasi mayor.")
        except Exception as e:
            print(f"[OSD] Error during OSD: {e}. Melanjutkan tanpa deteksi orientasi mayor.")


    # --- LANGKAH 2: Deskewing Halus (yang sudah ada) ---
    original_h, original_w = img.shape[:2] # Update dimensi setelah rotasi OSD

    scale_factor = 1.0
    if max(original_h, original_w) > 1000:
        scale_factor = 1000 / max(original_h, original_w)
        img_resized = cv2.resize(img, (int(original_w * scale_factor), int(original_h * scale_factor)), interpolation=cv2.INTER_AREA)
    else:
        img_resized = img.copy()

    gray = cv2.cvtColor(img_resized, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, canny_thresh1, canny_thresh2, apertureSize=3)

    # if debug_mode:
    #     cv2.imshow("Edges for Fine Deskew", edges)
    #     cv2.waitKey(1)

    angles = []

    # Mencoba HoughLinesP
    lines_p = cv2.HoughLinesP(edges, 1, np.pi / 180, hough_thresh, 
                             minLineLength=min_line_length, maxLineGap=max_line_gap)
    
    if lines_p is not None:
        for line in lines_p:
            x1, y1, x2, y2 = line[0]
            if x2 == x1: # Vertical line
                current_angle = 90.0
            else:
                current_angle = math.degrees(math.atan2(y2 - y1, x2 - x1))
            
            if current_angle > 45: current_angle -= 90
            elif current_angle < -45: current_angle += 90
            
            # Hanya pertimbangkan garis yang mendekati horizontal atau vertikal (opsional)
            if abs(current_angle) < 30 or abs(current_angle) > 60: 
                angles.append(current_angle)

    # Jika HoughLinesP tidak menemukan cukup garis relevan, coba HoughLines
    if not angles:
        lines_full = cv2.HoughLines(edges, 1, np.pi / 180, hough_thresh + 50) 
        if lines_full is not None:
            for line in lines_full:
                rho, theta = line[0]
                current_angle = np.degrees(theta)
                if current_angle > 45: current_angle -= 90
                elif current_angle < -45: current_angle += 90
                angles.append(current_angle)

    # --- PENANGANAN UNBOUNDLOCALERROR DAN AMBANG BATAS SUDUT ---
    fine_rotation_angle = 0.0 # Default fine rotation
    if not angles:
        print("[DESKEW] Tidak ditemukan garis signifikan untuk deskew halus. Mengembalikan gambar setelah OSD.")
        # if debug_mode:
        #     cv2.destroyAllWindows()
        return img, major_rotation_angle # Hanya rotasi mayor yang diterapkan
    
    median_angle = np.median(angles)
    
    if abs(median_angle) < min_rotation_angle_threshold:
        print(f"[DESKEW] Sudut deskew halus terdeteksi ({median_angle:.2f} derajat) di bawah ambang batas ({min_rotation_angle_threshold} derajat). Tidak ada deskew halus.")
        # if debug_mode:
        #     cv2.destroyAllWindows()
        return img, major_rotation_angle # Gambar setelah OSD, tidak ada deskew halus
    
    fine_rotation_angle = median_angle
    print(f"[DESKEW] Sudut deskew halus terdeteksi: {fine_rotation_angle:.2f} derajat. Melakukan rotasi.")

    # Rotasi Gambar untuk deskew halus
    (h, w) = img.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, fine_rotation_angle, 1.0)
    
    cos = np.abs(M[0, 0])
    sin = np.abs(M[0, 1])
    nW = int((h * sin) + (w * cos))
    nH = int((h * cos) + (w * sin))

    M[0, 2] += (nW / 2) - center[0]
    M[1, 2] += (nH / 2) - center[1]

    rotated = cv2.warpAffine(img, M, (nW, nH), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT, borderValue=(0,0,0))

    if save_path is not None:
        try:
            cv2.imwrite(save_path, rotated)
        except Exception as e:
            print(f"ERROR:  {e}")
            # traceback.print_exc() # Cetak traceback untuk detail error
        
    # if debug_mode:
    #     cv2.imshow("Final Rotated Image", rotated)
    #     cv2.waitKey(0)
    #     cv2.destroyAllWindows()

    return rotated, major_rotation_angle + fine_rotation_angle # Total rotasi yang diterapkan




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


def dictToList(ocrdict:dict):
    return [key for key in ocrdict if key != 'avgconfscore']


#def extrocr(arrtxtocr: list) -> dict:
def extrocr(ocrdict:dict) -> dict:
    print("\n[START] --- Memulai Fungsi extrocr ---")

    arrtxtocr = dictToList(ocrdict)
    
    carryocr = copy.deepcopy(arrtxtocr) 

    print(f"array map ktpdata awal = {arrktpdata}")

    print(f"array ocr awal = {carryocr}")

    print(f"ktpdata awal = {ktpdata}")

    print(f"kata yg sudah diproses dan valid awal = {wordmatched}")

    print(f"list field yg sudah divalidasi dari hasil ocr awal = {fieldset}")

    print("[DEBUG] 📜 Teks mentah yang akan diproses:")

    countvalnama = 1
    countvaladr = 1
    countvalttl = 1
    countvalblood = 1
    
    # Buat list atau tuple dari semua variabel yang ingin diperiksa
    all_counts = [countvalnama, countvalttl, countvaladr, countvalblood]

    # Hitung berapa banyak yang bernilai 1 dan berapa banyak yang bernilai 2
    count_of_ones = all_counts.count(1)
    count_of_twos = all_counts.count(2)
    # ... (loop utama Anda) ...
    for i, word in enumerate(arrtxtocr):
        print(f"  - Baris {i}: '{word}'")

        
        if i in wordmatched :
            print(f"{i} sudah diproses dan valid, lanjut ke elemen selanjutnya")
            continue
        
        kata , score = process.extractOne(word, ktp_fields)
        print(f'{word} {kata} {score}')


        if i==0 : #or kata == "provinsi" :  #asumsi provinsi hanya memakan 1 baris
            provval = validprov(word)

            if 'nyatu' in provval :
                print(f"provval nyatu : {provval}")    
            elif 'possibly' in provval :
                print(f"provval misah : {provval} dengan data belum valid sepenuhnya")
            elif 'dummy' in provval :
                print(f"provval misah : {provval} diinisiasi dummy")


            arrktpdata[arrktpdata.index("provinsi")+1] = provval   # ['provinsi', 'jawa timur']

            #pembersihan value dari keterangan yg menempel, keterangan dalam delwords dibutuhkan utk kualifikasi lanjutan pada hasil ocr yg disimpan di arrktpdata
            delwords = ['misah', 'nyatu', 'possibly', 'dummy']
            
            for dw in delwords:
                if dw in provval and provval != 'dummy':
                    
                    provval = provval.replace(dw, '').strip()
                    
                    if not provval:  #dummy
                        print(f'eror karena jadi kosong dek dummy terhapus')
                    break
                
            print (f'provnisi {provval}')
            ktpdata["provinsi"] = provval                           # {'provinsi' : 'jawa timur' }
            wordmatched.add(i)     
            print (f'word now {word}')                             
            carryocr.remove(word) 
            print(f"data provinsi : {provval} sukses ditambahkan")   


        elif i ==1:
            
            if  is_mostly_digits(arrtxtocr[i+2]) or is_mostly_digits(arrtxtocr[i+3]):    #kemungkinan terburuk yg mana data kabupaten/kota bisa memakan 2 baris dan didasarkan pada hasil ocr elemen ke 4 (nik) tapi tidak ada handle lanjutan pada pemrosesan value, handle kurang lebih sama seperti handle pada alamat dan nama
                print(f"ktpdata provinsi {ktpdata['provinsi']}")
                print(f"word {word}")
                val = validgeokk(ktpdata['provinsi'], word)
                if 'Kota' in val:
                    arrktpdata[arrktpdata.index('kabupaten')] = 'nil (alr in kota)'  
                    ktpdata['kabupaten'] = 'nil (alr in kota)'
                    arrktpdata[arrktpdata.index('kota')] = val 
                    ktpdata['kota'] = val
                    wordmatched.add(i)
                    carryocr.remove(word)
                    print(f"data kota : {val} sukses ditambahkan, data kabupaten menjadi nil") 
                else:
                    arrktpdata[arrktpdata.index('kota')] = 'nil (alr in kab)'  
                    ktpdata['kota'] = 'nil (alr in kabupaten)'
                    arrktpdata[arrktpdata.index('kabupaten')] = val 
                    ktpdata['kabupaten'] = val
                    wordmatched.add(i)
                    carryocr.remove(word)
                    print(f"data kabupaten : {val} sukses ditambahkan, data kota menjadi nil") 
    

        elif i==2 : #or kata == "nik" : #asumsi provinsi dan kabupaten kota masing masing hanya memakan 1 baris pada ktp
            #nextword = arrtxtocr[i+1] if i+1 < len(arrtxtocr) and len(word)<=5 else None  #asumsi yg hampir mustahil, hanya utk berjaga jaga, penganganan umumnya memakai situasi else di bawah
            nextword = arrtxtocr[i+1] if i+1 < len(arrtxtocr) else None
            nikval = validnik(nextword)

            if 'misah' in nikval :
                carryocr.remove(nextword)
                wordmatched.add(i+1)
                print(f"nikvall misah : {nikval}") 
            elif 'possibly' in nikval :
                print(f"nikval misah : {nikval} dengan data belum valid sepenuhnya")
            elif 'dummy' in nikval :
                print(f"nikval misah : {nikval} diinisiasi dummy")

            arrktpdata[arrktpdata.index('nik')+1] = nikval

            delwords = ['misah', 'nyatu', 'possibly', 'dummy']
            
            for dw in delwords:
                if dw in nikval and nikval != 'dummy':
                    
                    nikval = nikval.replace(dw, '').strip()
                    
                    if not nikval:  #dummy
                        print(f'eror karena jadi kosong dek dummy terhapus')
                    break

            ktpdata['nik'] = nikval
            wordmatched.add(i)
            carryocr.remove(word) 
            print(f"data nik : {nikval} sukses ditambahkan") 

        elif i == 4 : #or kata == 'nama'  :
            #collect nama dengan asumsi mungkin saja value nama ada 1-3 elemen array
            namaval =[arrtxtocr[i+1]]
            wordmatched.add(i)
            wordmatched.add(i+1)
            carryocr.remove(word)

            carryocr.remove(arrtxtocr[i+1])
            j = i+2

            while (process.extractOne(arrtxtocr[j], ktp_fields)[0] not in ['tempat tgl lahir' , 'tempat lahir', 'tgl lahir', 'kecamatan']):
                print(f'process {arrtxtocr[j]}')
                print(f'get {process.extractOne(arrtxtocr[j], ktp_fields)[0]} ')
                namaval.append(arrtxtocr[j])
                wordmatched.add(j)
                carryocr.remove(arrtxtocr[j])
                countvalnama+=1
                j+=1
                i+=1

            arrktpdata[arrktpdata.index('nama')+1] = namaval
            ktpdata['nama'] = namaval 

            print(f"data nama : {namaval} sukses ditambahkan")


        elif i==6 :
            if kata == 'tempat tgl lahir' or is_mostly_digits(arrtxtocr[i-3]):   #coutnamaval ==1
                ttlval =[arrtxtocr[i+1]]
                wordmatched.add(i)
                wordmatched.add(i+1)
                #wordmatched.add(i+1)
                carryocr.remove(word)
                carryocr.remove(arrtxtocr[i+1])
                j = i+2
                while is_mostly_digits(arrtxtocr[j]):
                    ttlval.append(arrtxtocr[j])
                    wordmatched.add(j)
                    carryocr.remove(arrtxtocr[j])
                    countvalttl+=1
                    j+=1
                    i+=1
                arrktpdata[arrktpdata.index('tempat tgl lahir')+1] = ttlval
                ktpdata['tempat tgl lahir'] = ttlval 

                print(f"data tempat tgl lahir : {ttlval} sukses ditambahkan")


        elif i== 7 :
            if kata == 'tempat tgl lahir' or is_mostly_digits(arrtxtocr[i-4]): #countvalnama == 2
                ttlval =[arrtxtocr[i+1]]
                wordmatched.add(i)
                wordmatched.add(i+1)
                #wordmatched.add(i+1)
                carryocr.remove(word)

                carryocr.remove(arrtxtocr[i+1])
                j = i+2
                while is_mostly_digits(arrtxtocr[j]):
                    ttlval.append(arrtxtocr[j])
                    wordmatched.add(j)
                    carryocr.remove(arrtxtocr[j])
                    countvalttl+=1
                    j+=1
                    i+=1
                arrktpdata[arrktpdata.index('tempat tgl lahir')+1] = ttlval
                ktpdata['tempat tgl lahir'] = ttlval 

                print(f"data tempat tgl lahir : {ttlval} sukses ditambahkan")
        
        elif i==8:
            if kata == 'jenis kelamin' or count_of_twos==0:
                #len word bisa bervariasi sehingga rawan perubahan
                nextword = arrtxtocr[i+1] if i+1 < len(arrtxtocr)   else None
                genderval = validgender(nextword)   

                if 'misah' in genderval :
                    carryocr.remove(nextword)
                    wordmatched.add(i+1)
                    print(f"gendervall misah : {genderval}") 
                elif 'possibly' in genderval :
                    print(f"genderval misah : {genderval} dengan data belum valid sepenuhnya")
                elif 'dummy' in genderval :
                    print(f"genderval misah : {genderval} diinisiasi dummy")

                arrktpdata[arrktpdata.index('jenis kelamin')+1] = genderval

                delwords = ['misah', 'nyatu', 'possibly', 'dummy']
            
                for dw in delwords:
                    if dw in genderval and genderval != 'dummy':
                        
                        genderval = genderval.replace(dw, '').strip()
                        
                        if not genderval:  #dummy
                            print(f'eror karena jadi kosong dek dummy terhapus')
                        break

                ktpdata['jenis kelamin'] = genderval
                wordmatched.add(i)
                carryocr.remove(word) 
                print(f"data jenis kelamin : {genderval} sukses ditambahkan") 

        elif i==9:
            if kata == 'jenis kelamin'  or count_of_twos == 1:
                nextword = arrtxtocr[i+1] if i+1 < len(arrtxtocr)   else None
                genderval = validgender(nextword)   

                if 'misah' in genderval :
                    carryocr.remove(nextword)
                    wordmatched.add(i+1)
                    print(f"gendervall misah : {genderval}") 
                elif 'possibly' in genderval :
                    print(f"genderval misah : {genderval} dengan data belum valid sepenuhnya")
                elif 'dummy' in genderval :
                    print(f"genderval misah : {genderval} diinisiasi dummy")

                arrktpdata[arrktpdata.index('jenis kelamin')+1] = genderval

                delwords = ['misah', 'nyatu', 'possibly', 'dummy']
            
                for dw in delwords:
                    if dw in genderval and genderval != 'dummy':
                        
                        genderval = genderval.replace(dw, '').strip()
                        
                        if not genderval:  #dummy
                            print(f'eror karena jadi kosong dek dummy terhapus')
                        break

                ktpdata['jenis kelamin'] = genderval
                wordmatched.add(i)
                carryocr.remove(word) 
                print(f"data jenis kelamin : {genderval} sukses ditambahkan") 
        

        elif i==10:  #handle hanya khusus worstcase umum ttl dan nama yg memakan 2 baris pada ktp
            if kata == 'jenis kelamin' or count_of_twos==2:
                nextword = arrtxtocr[i+1] if i+1 < len(arrtxtocr)   else None
                genderval = validgender(nextword)   

                if 'misah' in genderval :
                    carryocr.remove(nextword)
                    wordmatched.add(i+1)
                    print(f"gendervall misah : {genderval}") 
                elif 'possibly' in genderval :
                    print(f"genderval misah : {genderval} dengan data belum valid sepenuhnya")
                elif 'dummy' in genderval :
                    print(f"genderval misah : {genderval} diinisiasi dummy")

                arrktpdata[arrktpdata.index('jenis kelamin')+1] = genderval

                delwords = ['misah', 'nyatu', 'possibly', 'dummy']
            
                for dw in delwords:
                    if dw in genderval and genderval != 'dummy':
                        
                        genderval = genderval.replace(dw, '').strip()
                        
                        if not genderval:  #dummy
                            print(f'eror karena jadi kosong dek dummy terhapus')
                        break
                ktpdata['jenis kelamin'] = genderval
                wordmatched.add(i)
                carryocr.remove(word) 
                print(f"data jenis kelamin : {genderval} sukses ditambahkan") 
           
            elif kata == 'gol darah' and 'alamat' not in ktpdata and count_of_twos==0:
                nextword = arrtxtocr[i+1] if i+1< len(arrtxtocr) and len(arrtxtocr[i+1])==1  else None   # and  process.extractOne(arrtxtocr[i+1], ktp_fields)[0]  not in ['nama', 'alamat', 'agama']
                
                if nextword :
                    darahval = validdarah(nextword)   

                    if 'misah' in darahval :
                        carryocr.remove(nextword)
                        wordmatched.add(i+1)
                        print(f"darahvall misah : {darahval}") 
                    elif 'possibly' in darahval :
                        print(f"darahval misah : {darahval} dengan data belum valid sepenuhnya")
                    elif 'dummy' in darahval :
                        print(f"darahval misah : {darahval} diinisiasi dummy")
                    countvalblood+=1
                else:
                    darahval = 'dummy'
                    print(f"darahval misah : {darahval} diinisiasi dummy")

                arrktpdata[arrktpdata.index('gol darah')+1] = darahval

                delwords = ['misah', 'nyatu', 'possibly', 'dummy']
            
                for dw in delwords:
                    if dw in darahval and darahval != 'dummy':
                        
                        darahval = darahval.replace(dw, '').strip()
                        
                        if not darahval:  #dummy
                            print(f'eror karena jadi kosong dek dummy terhapus')
                        break

                ktpdata['gol darah'] = darahval
                wordmatched.add(i)
                carryocr.remove(word) 
                print(f"data gol darah : {darahval} sukses ditambahkan") 

             #   gol darah dan alamat could tertukar posisi dalam ocr mentah
            
            elif kata == 'alamat' and 'gol darah' not in ktpdata and count_of_twos==0 :
                adrval =[arrtxtocr[i+1]]
                wordmatched.add(i)
                wordmatched.add(i+1)
                carryocr.remove(word)
                carryocr.remove(arrtxtocr[i+1])
                j = i+2
                #asumsi alamat hanya memakan maks 2 baris
                if process.extractOne(arrtxtocr[j], ktp_fields)[0] not in ['rt rw', 'kewarganegaraan', 'status perkawinan', 'kecamatan']:
                    adrval.append(arrtxtocr[j])
                    wordmatched.add(j)
                    carryocr.remove(arrtxtocr[j])
                    countvalttl+=1
                    j+=1
                    i+=1
                
                arrktpdata[arrktpdata.index('alamat')+1] = adrval
                ktpdata['alamat'] = adrval

                print(f"data 'alamat : {adrval} sukses ditambahkan")


        elif i == 11:
            if kata == 'gol darah' and ( count_of_twos == 1 and 'alamat' not in ktpdata ):    #would be ttlvalcount == 2 or namevalcount==2

                nextword = arrtxtocr[i+1] if i+1< len(arrtxtocr) and len(arrtxtocr[i+1])==1  else None   # and  process.extractOne(arrtxtocr[i+1], ktp_fields)[0]  not in ['nama', 'alamat', 'agama']
                if nextword:
                    darahval = validdarah(word, nextword)                 
            
                    if 'misah' in darahval :
                        carryocr.remove(nextword)
                        wordmatched.add(i+1)
                        print(f"darahvall misah : {darahval}") 
                    elif 'possibly' in darahval :
                        print(f"darahval misah : {darahval} dengan data belum valid sepenuhnya")
                    elif 'dummy' in darahval :
                        print(f"darahval misah : {darahval} diinisiasi dummy")
                    countvalblood+=1
                else:
                    darahval = 'dummy'
                    print(f"darahval misah : {darahval} diinisiasi dummy")
                arrktpdata[arrktpdata.index('gol darah')+1] = darahval

                delwords = ['misah', 'nyatu', 'possibly', 'dummy']
            
                for dw in delwords:
                    if dw in darahval and darahval != 'dummy':
                        
                        darahval = darahval.replace(dw, '').strip()
                        
                        if not darahval:  #dummy
                            print(f'eror karena jadi kosong dek dummy terhapus')
                        break

                ktpdata['gol darah'] = darahval
                wordmatched.add(i)
                carryocr.remove(word) 
                print(f"data gol darah : {darahval} sukses ditambahkan") 
                nextword = arrtxtocr[i+1] if i+1< len(arrtxtocr) and len(arrtxtocr[i+1])==1  else None   # and  process.extractOne(arrtxtocr[i+1], ktp_fields)[0]  not in ['nama', 'alamat', 'agama']
                
                if nextword :
                    darahval = validdarah(nextword)   

                    if 'misah' in darahval :
                        carryocr.remove(nextword)
                        wordmatched.add(i+1)
                        print(f"darahvall misah : {darahval}") 
                    elif 'possibly' in darahval :
                        print(f"darahval misah : {darahval} dengan data belum valid sepenuhnya")
                    elif 'dummy' in darahval :
                        print(f"darahval misah : {darahval} diinisiasi dummy")
                else:
                    darahval = 'dummy'
                    print(f"darahval misah : {darahval} diinisiasi dummy")

                arrktpdata[arrktpdata.index('gol darah')+1] = darahval

                delwords = ['misah', 'nyatu', 'possibly', 'dummy']
            
                for dw in delwords:
                    if dw in darahval and darahval != 'dummy':
                        
                        darahval = darahval.replace(dw, '').strip()
                        
                        if not darahval:  #dummy
                            print(f'eror karena jadi kosong dek dummy terhapus')
                        break

                ktpdata['gol darah'] = darahval
                wordmatched.add(i)
                carryocr.remove(word) 
                print(f"data gol darah : {darahval} sukses ditambahkan")

            elif kata == 'alamat' and (  count_of_twos == 1 and 'gol darah' not in ktpdata ):    #would be ttlvalcount == 2 or namevalcount==2
                adrval =[arrtxtocr[i+1]]
                wordmatched.add(i)
                wordmatched.add(i+1)
                #wordmatched.add(i+1)
                carryocr.remove(word)

                carryocr.remove(arrtxtocr[i+1])
                j = i+2
                if process.extractOne(arrtxtocr[j], ktp_fields)[0] not in ['rt rw', 'kewarganegaraan', 'status perkawinan', 'kecamatan']:
                    adrval.append(arrtxtocr[j])
                    wordmatched.add(j)
                    carryocr.remove(arrtxtocr[j])
                    countvalttl+=1
                    j+=1
                    i+=1
                
                arrktpdata[arrktpdata.index('alamat')+1] = adrval
                ktpdata['alamat'] = adrval

                print(f"data 'alamat : {adrval} sukses ditambahkan")

        elif i==12:
            if kata == 'alamat' and ( count_of_twos == 1 and ktpdata['gol darah']=='dummy') or  ( (countvalttl==2 and countvalnama ==2) and 'gol darah' not in ktpdata)  :
                adrval =[arrtxtocr[i+1]]
                wordmatched.add(i)
                wordmatched.add(i+1)
                carryocr.remove(word)
                carryocr.remove(arrtxtocr[i+1])
                j = i+2
                #asumsi alamat hanya memakan maks 2 baris
                if process.extractOne(arrtxtocr[j], ktp_fields)[0] not in ['rt rw', 'kewarganegaraan', 'status perkawinan', 'kecamatan']:
                    adrval.append(arrtxtocr[j])
                    wordmatched.add(j)
                    carryocr.remove(arrtxtocr[j])
                    countvalttl+=1
                    j+=1
                    i+=1
                
                arrktpdata[arrktpdata.index('alamat')+1] = adrval
                ktpdata['alamat'] = adrval

                print(f"data 'alamat : {adrval} sukses ditambahkan")
            #worst and almost impossible case
            elif kata == 'gol darah' and ( count_of_twos == 2 and 'alamat' not in ktpdata)  :
                nextword = arrtxtocr[i+1] if i+1< len(arrtxtocr) and len(arrtxtocr[i+1])==1  else None   # and  process.extractOne(arrtxtocr[i+1], ktp_fields)[0]  not in ['nama', 'alamat', 'agama']
                
                if nextword :
                    darahval = validdarah(nextword)   

                    if 'misah' in darahval :
                        carryocr.remove(nextword)
                        wordmatched.add(i+1)
                        print(f"darahvall misah : {darahval}") 
                    elif 'possibly' in darahval :
                        print(f"darahval misah : {darahval} dengan data belum valid sepenuhnya")
                    elif 'dummy' in darahval :
                        print(f"darahval misah : {darahval} diinisiasi dummy")
                    countvalblood+=1
                else:
                    darahval = 'dummy'
                    print(f"darahval misah : {darahval} diinisiasi dummy")

                arrktpdata[arrktpdata.index('gol darah')+1] = darahval

                delwords = ['misah', 'nyatu', 'possibly', 'dummy']
            
                for dw in delwords:
                    if dw in darahval and darahval != 'dummy':
                        
                        darahval = darahval.replace(dw, '').strip()
                        
                        if not darahval:  #dummy
                            print(f'eror karena jadi kosong dek dummy terhapus')
                        break

                ktpdata['gol darah'] = darahval
                wordmatched.add(i)
                carryocr.remove(word) 
                print(f"data gol darah : {darahval} sukses ditambahkan")

        elif i==13:
            if kata == 'rt/rw' or count_of_twos==0 :
                # nextword = arrtxtocr[i+1]
                # rtrwval = validrtrw(nextword)
                rtrwval = arrtxtocr[i+1]
                wordmatched.add(i)
                wordmatched.add(i+1)
                carryocr.remove(word)
                carryocr.remove(arrtxtocr[i+1])
                arrktpdata[arrktpdata.index('rt rw')+1] = rtrwval
                ktpdata['rt rw'] = rtrwval

                print(f"data rt rw : {rtrwval} sukses ditambahkan") 

            if kata == 'alamat' and ( count_of_twos == 3 )  :
                adrval =[arrtxtocr[i+1]]
                wordmatched.add(i)
                wordmatched.add(i+1)
                carryocr.remove(word)
                carryocr.remove(arrtxtocr[i+1])
                j = i+2
                #asumsi alamat hanya memakan maks 2 baris
                if process.extractOne(arrtxtocr[j], ktp_fields)[0] not in ['rt rw', 'kewarganegaraan', 'status perkawinan', 'kecamatan']:
                    adrval.append(arrtxtocr[j])
                    wordmatched.add(j)
                    carryocr.remove(arrtxtocr[j])
                    countvalttl+=1
                    j+=1
                    i+=1
                
                arrktpdata[arrktpdata.index('alamat')+1] = adrval
                ktpdata['alamat'] = adrval

                print(f"data 'alamat : {adrval} sukses ditambahkan")

        elif i==14:
            if kata == 'rt/rw' or (count_of_twos == 1 ) :
                # nextword = arrtxtocr[i+1]
                # rtrwval = validrtrw(nextword)
                rtrwval = arrtxtocr[i+1]
                wordmatched.add(i)
                wordmatched.add(i+1)
                carryocr.remove(word)
                carryocr.remove(arrtxtocr[i+1])
                arrktpdata[arrktpdata.index('rt rw')+1] = rtrwval
                ktpdata['rt rw'] = rtrwval

                print(f"data rt rw : {rtrwval} sukses ditambahkan") 

            elif kata == 'alamat' and  count_of_twos == 3   :
                adrval =[arrtxtocr[i+1]]
                wordmatched.add(i)
                wordmatched.add(i+1)
                carryocr.remove(word)
                carryocr.remove(arrtxtocr[i+1])
                j = i+2
                #asumsi alamat hanya memakan maks 2 baris
                if process.extractOne(arrtxtocr[j], ktp_fields)[0] not in ['rt rw', 'kewarganegaraan', 'status perkawinan', 'kecamatan']:
                    adrval.append(arrtxtocr[j])
                    wordmatched.add(j)
                    carryocr.remove(arrtxtocr[j])
                    countvalttl+=1
                    j+=1
                    i+=1
                
                arrktpdata[arrktpdata.index('alamat')+1] = adrval
                ktpdata['alamat'] = adrval

                print(f"data 'alamat : {adrval} sukses ditambahkan")

            elif kata == 'gol darah' and 'alamat' in ktpdata and count_of_twos == 2:
                nextword = arrtxtocr[i+1] if i+1< len(arrtxtocr) and len(arrtxtocr[i+1])==1  else None   # and  process.extractOne(arrtxtocr[i+1], ktp_fields)[0]  not in ['nama', 'alamat', 'agama']
                
                if nextword :
                    darahval = validdarah(nextword)   

                    if 'misah' in darahval :
                        carryocr.remove(nextword)
                        wordmatched.add(i+1)
                        print(f"darahvall misah : {darahval}") 
                    elif 'possibly' in darahval :
                        print(f"darahval misah : {darahval} dengan data belum valid sepenuhnya")
                    elif 'dummy' in darahval :
                        print(f"darahval misah : {darahval} diinisiasi dummy")
                    countvalblood+=1
                else:
                    darahval = 'dummy'
                    print(f"darahval misah : {darahval} diinisiasi dummy")

                arrktpdata[arrktpdata.index('gol darah')+1] = darahval

                delwords = ['misah', 'nyatu', 'possibly', 'dummy']
            
                for dw in delwords:
                    if dw in darahval and darahval != 'dummy':
                        
                        darahval = darahval.replace(dw, '').strip()
                        
                        if not darahval:  #dummy
                            print(f'eror karena jadi kosong dek dummy terhapus')
                        break

                ktpdata['gol darah'] = darahval
                wordmatched.add(i)
                carryocr.remove(word) 
                print(f"data gol darah : {darahval} sukses ditambahkan")
            
        elif i ==15:
            if kata == 'rt/rw' or (count_of_twos == 2 ) :
                # nextword = arrtxtocr[i+1]
                # rtrwval = validrtrw(nextword)
                rtrwval = arrtxtocr[i+1]
                wordmatched.add(i)
                wordmatched.add(i+1)
                carryocr.remove(word)
                carryocr.remove(arrtxtocr[i+1])
                arrktpdata[arrktpdata.index('rt rw')+1] = rtrwval
                ktpdata['rt rw'] = rtrwval

                print(f"data rt rw : {rtrwval} sukses ditambahkan") 


                adrval =[arrtxtocr[i+1]]
                wordmatched.add(i)
                wordmatched.add(i+1)
                carryocr.remove(word)
                carryocr.remove(arrtxtocr[i+1])
                j = i+2
                #asumsi alamat hanya memakan maks 2 baris
                if process.extractOne(arrtxtocr[j], ktp_fields)[0] not in ['rt rw', 'kewarganegaraan', 'status perkawinan', 'kecamatan']:
                    adrval.append(arrtxtocr[j])
                    wordmatched.add(j)
                    carryocr.remove(arrtxtocr[j])
                    countvalttl+=1
                    j+=1
                    i+=1
                
                arrktpdata[arrktpdata.index('alamat')+1] = adrval
                ktpdata['alamat'] = adrval

                print(f"data 'alamat : {adrval} sukses ditambahkan")

            elif kata == 'gol darah' and count_of_twos == 3:
                nextword = arrtxtocr[i+1] if i+1< len(arrtxtocr) and len(arrtxtocr[i+1])==1  else None   # and  process.extractOne(arrtxtocr[i+1], ktp_fields)[0]  not in ['nama', 'alamat', 'agama']
                
                if nextword :
                    darahval = validdarah(nextword)   

                    if 'misah' in darahval :
                        carryocr.remove(nextword)
                        wordmatched.add(i+1)
                        print(f"darahvall misah : {darahval}") 
                    elif 'possibly' in darahval :
                        print(f"darahval misah : {darahval} dengan data belum valid sepenuhnya")
                    elif 'dummy' in darahval :
                        print(f"darahval misah : {darahval} diinisiasi dummy")
                    countvalblood+=1
                else:
                    darahval = 'dummy'
                    print(f"darahval misah : {darahval} diinisiasi dummy")

                arrktpdata[arrktpdata.index('gol darah')+1] = darahval

                delwords = ['misah', 'nyatu', 'possibly', 'dummy']
            
                for dw in delwords:
                    if dw in darahval and darahval != 'dummy':
                        
                        darahval = darahval.replace(dw, '').strip()
                        
                        if not darahval:  #dummy
                            print(f'eror karena jadi kosong dek dummy terhapus')
                        break

                ktpdata['gol darah'] = darahval
                wordmatched.add(i)
                carryocr.remove(word) 
                print(f"data gol darah : {darahval} sukses ditambahkan")
            

                nextword = arrtxtocr[i+1] if i+1< len(arrtxtocr) and len(arrtxtocr[i+1])==1  else None   # and  process.extractOne(arrtxtocr[i+1], ktp_fields)[0]  not in ['nama', 'alamat', 'agama']
                
                if nextword :
                    darahval = validdarah(nextword)   

                    if 'misah' in darahval :
                        carryocr.remove(nextword)
                        wordmatched.add(i+1)
                        print(f"darahvall misah : {darahval}") 
                    elif 'possibly' in darahval :
                        print(f"darahval misah : {darahval} dengan data belum valid sepenuhnya")
                    elif 'dummy' in darahval :
                        print(f"darahval misah : {darahval} diinisiasi dummy")
                    countvalblood+=1
                else:
                    darahval = 'dummy'
                    print(f"darahval misah : {darahval} diinisiasi dummy")

                arrktpdata[arrktpdata.index('gol darah')+1] = darahval

                delwords = ['misah', 'nyatu', 'possibly', 'dummy']
            
                for dw in delwords:
                    if dw in darahval and darahval != 'dummy':
                        
                        darahval = darahval.replace(dw, '').strip()
                        
                        if not darahval:  #dummy
                            print(f'eror karena jadi kosong dek dummy terhapus')
                        break

                ktpdata['gol darah'] = darahval
                wordmatched.add(i)
                carryocr.remove(word) 
                print(f"data gol darah : {darahval} sukses ditambahkan")
        
        # elif i ==16 :

        elif i == 17:
            if kata == 'rt/rw' or (count_of_twos == 3) :
                # nextword = arrtxtocr[i+1]
                # rtrwval = validrtrw(nextword)
                rtrwval = arrtxtocr[i+1]
                wordmatched.add(i)
                wordmatched.add(i+1)
                carryocr.remove(word)
                carryocr.remove(arrtxtocr[i+1])
                arrktpdata[arrktpdata.index('rt rw')+1] = rtrwval
                ktpdata['rt rw'] = rtrwval

                print(f"data rt rw : {rtrwval} sukses ditambahkan") 


                adrval =[arrtxtocr[i+1]]
                wordmatched.add(i)
                wordmatched.add(i+1)
                carryocr.remove(word)
                carryocr.remove(arrtxtocr[i+1])
                j = i+2
                #asumsi alamat hanya memakan maks 2 baris
                if process.extractOne(arrtxtocr[j], ktp_fields)[0] not in ['rt rw', 'kewarganegaraan', 'status perkawinan', 'kecamatan']:
                    adrval.append(arrtxtocr[j])
                    wordmatched.add(j)
                    carryocr.remove(arrtxtocr[j])
                    countvalttl+=1
                    j+=1
                    i+=1
                
                arrktpdata[arrktpdata.index('alamat')+1] = adrval
                ktpdata['alamat'] = adrval

                print(f"data 'alamat : {adrval} sukses ditambahkan")
            
            # elif kata==''
        
        
        
        
        print(f"arrktp data now = \n{arrktpdata}\n")
        print(f'ktpdata ima : \n{ktpdata}\n')
        print(f'carryocr ima : \n{carryocr}\n')


    tempatlahirval, tgllahirval= ttlextract(ktpdata['nik'], ktpdata['tempat tgl lahir'])

    ktpdata['tempat lahir'] = tempatlahirval
    arrktpdata[arrktpdata.index('tempat tgl lahir')+2] = 'tempat lahir'
    arrktpdata[arrktpdata.index('tempat lahir')+1] = tempatlahirval

    ktpdata['tgl lahir'] = tgllahirval 
    arrktpdata[arrktpdata.index('tempat lahir')+2] = 'tgl lahir'
    arrktpdata[arrktpdata.index('tgl lahir')+1] = tempatlahirval   

    # for f,v in ktpdata.items():
    #     if 'nyatu' in v or 'misah' in v:
    #         v = v.split()[0] 
    #         ktpdata[f] = v
    #     elif 'possibly' in v :
        
    #     elif 'dummy' in v:
    #         if v!='dummy':

    #         else :

    # for x in carryocr :
    #     if 'nyatu' in 

    print("[DEBUG] 📋 Kamus KTP now")
    print(json.dumps(ktpdata, indent=2, ensure_ascii=False))
    
    print("[END] --- Selesai Fungsi extrocr ---")
    # return ttlextrocr(final_arrktpdata)
    return arrtxtocr, carryocr, ktpdata, arrktpdata



def ttlextract(nik :str, datattl :list) :
    print("\n[START] --- Memulai Fungsi ttlextrocr ---")
    # print("[DEBUG] 📥 Menerima arrktpdata:", json.dumps(ktpdata, indent=2))


    if len(re.sub(r'[^0-9]', '', str(nik[0:12]))) != 12 :
        print(f"⚠️ [PERINGATAN]  NIK setelah dibersihkan memakan nilia inti utk pemrosesan, panjang nik after {len(nik)}. Proses TTL dilewati.")
        return 'dummy tempat lahir', 'dummy tgl lahir'

    
    # ktpdata['nik'] = nik_bersih
    niktgl_str = nik[6:8]
    nikbulan_str = nik[8:10]
    niktahun_str = nik[10:12]

    
    print(f"[DEBUG] slice NIK: tgl='{niktgl_str}', bln='{nikbulan_str}', thn='{niktahun_str}'")
    
    try:
        niktgl = int(niktgl_str)
        nikbulan = int(nikbulan_str)
        niktahun = int(niktahun_str)

        if niktgl > 40:
            # arrktpdata['jenis kelamin'] = 'PEREMPUAN'
            niktgl -= 40
            print("[DEBUG] 🚺 Terdeteksi Perempuan dari NIK.")
        else:
            # arrktpdata['jenis kelamin'] = 'LAKI-LAKI'
            print("[DEBUG] 🚹 Terdeteksi Laki-laki dari NIK.")

        bulan_nama = [
        "Januari", "Februari", "Maret", "April", "Mei", "Juni",
        "Juli", "Agustus", "September", "Oktober", "November", "Desember"
        ]

        if int(niktahun) > 10 :
            niktahun = str(int(niktahun) + 1900)
        else :
            niktahun = str(int(niktahun) + 2000)

        tgllahir = f'{niktgl} {bulan_nama[int(nikbulan)-1]} {niktahun}'

        # ttl = re.split(r"[., ]\s*", ktpdata['tempat tgl lahir'], maxsplit=1)
        # ttl = re.split(r"[., ]\s*", datattl, maxsplit=1)


        listnamakabkota = list(kabkota_df['name'].values)
        #Insert tempat
        tempatlahir,_ = process.extractOne(datattl[0], listnamakabkota)

        print("[DEBUG] 🎂 Logika Tanggal Lahir berhasil diproses.")
  

    except ValueError:
        print("⚠️ [PERINGATAN] Gagal mengubah potongan NIK menjadi angka. Proses TTL dihentikan.")
        return 'dummy tempat lahir', 'dummy tgl lahir'
    
    print("[END] --- Selesai Fungsi ttlextrocr ---")
    return  tempatlahir, tgllahir


# ... (impor lainnya) ...
# from tempfile import NamedTemporaryFile # Ini tidak lagi dibutuhkan

# ... (definisi fungsi-fungsi lainnya) ...

@app.route('/vratp/ocr/ktpdata', methods=['POST'])
def handle_ocr_request():
    """Mengembalikan data KTP yang diekstrak."""
    if 'image' not in request.files:
        return jsonify({'error': "Request harus menyertakan file dengan key 'image'"}), 400
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'Tidak ada file yang dipilih'}), 400

    try:
        image_bytes = file.read() # <--- Ambil bytes gambar langsung dari request
        
        # 1. Luruskan gambar (langsung dari bytes)
        # rotated_img_np, angle = straighten_ktp(temp_img_file.name, save_debug_images=False)
        # ^^^^^^ OLD CODE ^^^^^^

        # NEW CODE: Panggil straighten_ktp dengan image_bytes
        # Tambahkan output_path jika Anda ingin menyimpan debug gambar yang diluruskan
        output_rotated_path = os.path.join(tempfile.gettempdir(), f"rotated_debug_{os.path.basename(file.filename)}") if app.debug else None
        rotated_img_np, angle = straighten_ktp(
            image_bytes,
            save_path=output_rotated_path # Simpan jika diperlukan untuk debug
        )
            
        if rotated_img_np is None: # Ini hanya akan terjadi jika straighten_ktp mengembalikan None (tapi sekarang raise ValueError)
            return jsonify({'error': "Gagal meluruskan gambar."}), 500

        # Encode gambar yang sudah diluruskan kembali ke bytes untuk OCR
        is_success_encode, buf_rotated = cv2.imencode(".jpg", rotated_img_np)
        if not is_success_encode:
            return jsonify({'error': "Gagal meng-encode gambar hasil pelurusan."}), 500
        deskewed_image_bytes = buf_rotated.tobytes()

        ocr_results = imgocr(deskewed_image_bytes)
        
        global ktpdata_global
        ktpdata_global = ocr_results 
        
        arrktpdata, carryocr, ktpdata = extrocr(ocr_results) 
        
        return jsonify({
            'success': True,
            'arrktpdata': arrktpdata,
            'carryocr' : carryocr,
            'ktpdata' : ktpdata

            # 'avg_conf_score': ocr_results.get('avgconfscore', 0.0),
            # 'raw_ocr_texts': dictToList(ocr_results)
        })

    except ValueError as ve: # Tangkap ValueError dari straighten_ktp
        print(f"ValueError di straighten_ktp: {ve}")
        return jsonify({'error': f'Gagal memproses gambar: {str(ve)}'}), 500
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return jsonify({'error': f'Terjadi kesalahan internal: {str(e)}'}), 500

# ... (endpoint /vratp/ocr/ktpimage dan bagian __main__ lainnya) ...

@app.route('/vratp/ocr/ktpimage', methods=['GET'])

def get_ktp_image_with_boxes():
    """Mengembalikan gambar KTP dengan bounding box."""
    global ktpdata_global
    
    if not ktpdata_global or 'image_with_boxes_bytes' not in ktpdata_global or ktpdata_global['image_with_boxes_bytes'] is None:
        return jsonify({'error': "Gambar KTP dengan bounding box belum tersedia. Harap POST dulu ke /vratp/ocr/ktpdata."}), 404
    
    image_bytes = ktpdata_global['image_with_boxes_bytes']
    
    # Pastikan file-like object dibuka dalam mode binary 'rb'
    return send_file(
        io.BytesIO(image_bytes),
        mimetype='image/jpeg',
        as_attachment=False, # Jangan kirim sebagai attachment, tampilkan di browser
        download_name='ktp_with_boxes.jpg' # Nama file jika di-download
    )


# if __name__ == '__main__':
#     # Hapus semua testing lokal di sini, karena sudah diatur oleh Flask app.run()
#     # Jika Anda ingin melakukan pengujian lokal, buat file terpisah atau gunakan alat testing seperti Postman/Curl
#     print("[INFO] Flask app akan berjalan. Gunakan Postman/Curl untuk menguji endpoint.")

#     # Contoh CURL untuk /vratp/ocr/ktpdata
#     # curl -X POST -F "image=@/path/to/your/ktp3.jpg" http://12.0.0.1:5000/vratp/ocr/ktpdata

#     # Contoh CURL untuk /vratp/ocr/ktpimage (setelah POST ke ktpdata)
#     # curl http://12.0.0.1:5000/vratp/ocr/ktpimage > output_image.jpg

#     # Jalankan aplikasi Flask
#     app.run(debug=True) # debug=True hanya untuk development


datadir = 'data'
imgpath = os.path.join(datadir, 'ktp2.jpg')
with open(imgpath, 'rb') as f:
        image_bytes_from_file = f.read()
# 1. Luruskan dulu


# rotated_img, angle = straighten_ktp(imgpath, save_path="ktp109_lurus.jpg")
rotated_img, angle = straighten_ktp(image_bytes_from_file, save_path="ktp2_lurus.jpg", perform_osd=True, osd_pagesegmode='0' )
# print(f"[TESTING] Gambar diluruskan dengan sudut {angle:.2f}° dan disimpan ke ktp514_lurus.jpg")

# # 2. OCR pakai gambar hasil rotasi
_, buf = cv2.imencode(".jpg", rotated_img)

# _, buf = cv2.imencode(".jpg", image_bytes_from_file)
# ocr_results = imgocr(buf.tobytes())
ocr_results = imgocr(buf.tobytes())
initarr, carryocr , ktpdata, arrktpdata = extrocr(ocr_results)
# txtocr = dictToList(ocr_results)
# print(f"hasil ocr mentah : \n{txtocr}\n\n")
# with open('ktp125_lurus.jpg', 'wb') as f:
#     f.write(ocr_results['image_with_boxes_bytes'])

if 'image_with_boxes_bytes' in ocr_results and ocr_results['image_with_boxes_bytes'] is not None:
    output_image_path = f'ktp2_boxes.jpg'
    with open(output_image_path, 'wb') as f:
        f.write(ocr_results['image_with_boxes_bytes'])


    print(f"[TESTING] Gambar dengan bounding box disimpan ke: {output_image_path}")
else:
    print("[TESTING] Tidak ada gambar dengan bounding box yang dihasilkan.")


print(f"hasil init arrktpdata  sebelum diolah: \n{initarr}\n\n")
print(f"hasil arrktpdata setelah diolah : \n{arrktpdata}\n\n")

print(f"hasil ktp data : \n{ktpdata}\n\n")

print(f"hasil arrktpdata tersisa  : \n{carryocr}\n\n")
print("\n[TESTING] Selesai.")
