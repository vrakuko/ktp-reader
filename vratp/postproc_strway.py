
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
# import scipy
# import skimage
# from alyn import SkewDetect, Deskew
from valid import validagama, validgender, validkab, validkawin, validkec, validkeldes, validkota, validnama, validnik, validprov, validrtrw, validdarah, validjob, validwn, validberlaku, is_mostly_digits
ktpdata_global = {}

app = Flask(__name__)
CORS(app)
# basedir = os.path.dirname(os.path.abspath(__file__))
# datasetdir = os.path.join(basedir, 'dataset')

datasetdir = "dataset"

print("[INIT] Memulai inisialisasi global...")


# app = Flask(__name__)
# CORS(app)

print("[INIT] Memuat model EasyOCR...")
ereader = easyocr.Reader(['id'], gpu=False)
print("[INIT] Model EasyOCR siap.")



ktp_fields = [
    "provinsi", "kabupaten", "kota", "nik", "nama", "tempat tgl lahir", "tempat lahir", "tgl lahir",  "jenis kelamin",
    'gol darah', "alamat", "rt rw", "kel desa", "kecamatan", "agama", "status perkawinan",
    "pekerjaan", "kewarganegaraan wn", "berlaku hingga"
]



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

    # GANTI DENGAN PATH RELATIF UNTUK PORTABILITAS
    prov_df = pd.read_csv(os.path.join(datasetdir, 'provinsi.csv'))
    # prov_df = pd.read_csv('D:/dataset/provinsi.csv')
    

    # kabkota_df = pd.read_csv('D:/dataset/kabupaten_kota.csv')
    kabkota_df = pd.read_csv(os.path.join(datasetdir, 'kabupaten_kota.csv'))
    
    kabkota_dict = kabkota_df.set_index('name')['id'].astype(str).to_dict()

    # kec_df = pd.read_csv('D:/dataset/kecamatan.csv')
    kec_df = pd.read_csv(os.path.join(datasetdir, 'kecamatan.csv'))
    listnamakec = list(kec_df['name'].values)
    kec_dict = kec_df.set_index('name')['id'].astype(str).to_dict()

    # kel_df = pd.read_csv('D:/dataset/kelurahan.csv')
    kel_df = pd.read_csv(os.path.join(datasetdir, 'kelurahan.csv'))
    listnamakel = list(kel_df['name'].values)
    kel_dict = kel_df.set_index('name')['id'].astype(str).to_dict()

    
    print("[INIT] ✅ Semua file CSV berhasil dimuat.")
except FileNotFoundError as e:
    print(f"FATAL ERROR: Pastikan file CSV ada di folder 'data/'. Detail: {e}")
    exit()

print("[INIT] Inisialisasi global selesai.")

# ===================================================================
# 2. FUNGSI-FUNGSI MURNI
# ===================================================================
import cv2
import numpy as np
import os




import cv2
import numpy as np
import math

def straighten_ktp(image_bytes: bytes, save_path: str = None, 
                   canny_thresh1: int = 50, canny_thresh2: int = 150, 
                   hough_thresh: int = 150, min_line_length: int = 100, max_line_gap: int = 10,
                   min_rotation_angle_threshold: float = 0.5, # Ambang batas sudut minimum untuk rotasi
                   debug_mode: bool = False # Untuk menampilkan gambar debug
                  ):
    """
    Meluruskan (deskew) gambar dokumen dari bytes.
    Mengembalikan numpy.ndarray yang sudah diluruskan dan sudutnya.
    """
    img = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Gagal memuat gambar dari bytes. Pastikan data gambar valid.")

    original_h, original_w = img.shape[:2]

    scale_factor = 1.0
    if max(original_h, original_w) > 1000:
        scale_factor = 1000 / max(original_h, original_w)
        img_resized = cv2.resize(img, (int(original_w * scale_factor), int(original_h * scale_factor)), interpolation=cv2.INTER_AREA)
    else:
        img_resized = img.copy()

    gray = cv2.cvtColor(img_resized, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, canny_thresh1, canny_thresh2, apertureSize=3)

    if debug_mode:
        cv2.imshow("Edges", edges)
        cv2.waitKey(1) # Gunakan waitKey(1) agar tidak blocking, atau 0 jika ingin pause

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
    if not angles: # Jika list angles masih kosong setelah HoughLinesP
        lines_full = cv2.HoughLines(edges, 1, np.pi / 180, hough_thresh + 50) 
        if lines_full is not None:
            for line in lines_full:
                rho, theta = line[0]
                current_angle = np.degrees(theta)
                if current_angle > 45: current_angle -= 90
                elif current_angle < -45: current_angle += 90
                angles.append(current_angle)

    # --- PENANGANAN UNBOUNDLOCALERROR DI SINI ---
    if not angles:
        # Jika sama sekali tidak ada garis yang terdeteksi setelah kedua metode,
        # anggap gambar sudah lurus atau tidak bisa diperbaiki.
        print("[DESKEW] Tidak ditemukan garis signifikan untuk rotasi. Mengembalikan gambar asli.")
        if debug_mode:
            cv2.destroyAllWindows() # Tutup window debug jika ada
        return img, 0.0 # Kembali dengan gambar asli dan sudut 0
    
    # Jika ada sudut yang terdeteksi, hitung mediannya
    median_angle = np.median(angles)
    
    # Ambang batas sudut untuk rotasi
    if abs(median_angle) < min_rotation_angle_threshold:
        print(f"[DESKEW] Sudut terdeteksi ({median_angle:.2f} derajat) di bawah ambang batas ({min_rotation_angle_threshold} derajat). Gambar dianggap sudah lurus.")
        if debug_mode:
            cv2.destroyAllWindows()
        return img, 0.0 # Kembali dengan gambar asli dan sudut 0

    print(f"[DESKEW] Sudut rotasi terdeteksi: {median_angle:.2f} derajat. Melakukan rotasi.")

    # Rotasi Gambar
    (h, w) = img.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
    
    cos = np.abs(M[0, 0])
    sin = np.abs(M[0, 1])
    nW = int((h * sin) + (w * cos))
    nH = int((h * cos) + (w * sin))

    M[0, 2] += (nW / 2) - center[0]
    M[1, 2] += (nH / 2) - center[1]

    rotated = cv2.warpAffine(img, M, (nW, nH), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT, borderValue=(0,0,0))

    if save_path is not None:
        cv2.imwrite(save_path, rotated)
        
    if debug_mode:
        cv2.imshow("Rotated Image", rotated)
        cv2.waitKey(0) # Tunggu user menekan tombol
        cv2.destroyAllWindows()

    return rotated, median_angle




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


    # ... (loop utama Anda) ...
    for i, word in enumerate(arrtxtocr):
        print(f"  - Baris {i}: '{word}'")

        
        if i in wordmatched :
            print(f"{i} sudah diproses dan valid, lanjut ke elemen selanjutnya")
            continue
        
        kata , score = process.extractOne(word, ktp_fields)
        print(f'{word} {kata} {score}')

        

        # if kata not in ktpdata:
        #     if score >30:

        if i==0 : #or kata == "provinsi" :
            # misal ['provinsi jawa timur']
            nextword = arrtxtocr[i+1] if i+1 < len(arrtxtocr) and len(word)<=10 else None
            provval = validprov(word, nextword)

            if 'nyatu' in provval :
                print(f"provval nyatu : {provval}")    

            else :
                if 'misah' in provval :
                    carryocr.remove(nextword)
                    wordmatched.add(i+1)
                    print(f"provval misah : {provval}") 
                elif 'possibly' in provval :
                    print(f"provval misah : {provval} dengan data belum valid sepenuhnya")
                elif 'dummy' in provval :
                    print(f"provval misah : {provval} diinisiasi dummy")

            arrktpdata[arrktpdata.index("provinsi")+1] = provval   # ['provinsi', 'jawa timur']
            ktpdata["provinsi"] = provval                           # {'provinsi' : 'jawa timur' }
            wordmatched.add(i)                                  
            carryocr.remove(word) 
            print(f"data provinsi : {provval} sukses ditambahkan")   

        
            # proses untuk provinsi
        
        elif i == 1 : # or kata == "kabupaten":
            arrktpdata[arrktpdata.index('kota')] = 'nil (alr in kab)'  
            ktpdata['kota'] = 'nil (alr in kab)'

            nextword = arrtxtocr[i+1] if i+1 < len(arrtxtocr) and len(word)<=12 else None
            kabval = validkab(word, nextword)

            if 'nyatu' in kabval :
                print(f"kabval nyatu : {kabval}")    
            else :
                if 'misah' in kabval :
                    carryocr.remove(nextword)
                    wordmatched.add(i+1)
                    print(f"kabval misah : {kabval}") 
                elif 'possibly' in kabval :
                    print(f"kabval misah : {kabval} dengan data belum valid sepenuhnya")
                elif 'possibly' in kabval :
                    print(f"kabval misah : {kabval} diinisiasi dummy")

            arrktpdata[arrktpdata.index("kabupaten")+1] = kabval
            ktpdata["kabupaten"] = kabval
            wordmatched.add(i)
            carryocr.remove(word) 
            print(f"data kabupaten : {kabval} sukses ditambahkan, data kota menjadi nil") 

        elif  i==1 : #or kata == "kota":
            arrktpdata[arrktpdata.index('kabupaten')] = 'nil (alr in kota)'  
            ktpdata['kabupaten'] = 'nil (alr in kota)'

            nextword = arrtxtocr[i+1] if i+1 < len(arrtxtocr) and len(word)<=5 else None
            kotaval = validkota(word, nextword)

            if 'nyatu' in kotaval :
                print(f"kabval nyatu : {kotaval}")    
            else :
                if 'misah' in kabval :
                    carryocr.remove(nextword)
                    wordmatched.add(i+1)
                    print(f"kabval misah : {kabval}") 
                elif 'possibly' in kabval :
                    print(f"kabval misah : {kabval} dengan data belum valid sepenuhnya")
                elif 'possibly' in kabval :
                    print(f"kabval misah : {kabval} diinisiasi dummy")

            arrktpdata[arrktpdata.index('kabupaten')+1] = kabval
            ktpdata['kabupaten'] = kabval
            wordmatched.add(i)
            carryocr.remove(word) 
            print(f"data kabupaten : {kabval} sukses ditambahkan, data kota menjadi nil") 

        elif i==2 : #or kata == "nik" :
            nextword = arrtxtocr[i+1] if i+1 < len(arrtxtocr) and len(word)<=5 else None
            nikval = validnik(word, nextword)

            if 'nyatu' in nikval :
                print(f"nikval nyatu : {nikval}")    
            else :
                if 'misah' in nikval :
                    carryocr.remove(nextword)
                    wordmatched.add(i+1)
                    print(f"nikvall misah : {nikval}") 
                elif 'possibly' in nikval :
                    print(f"nikval misah : {nikval} dengan data belum valid sepenuhnya")
                elif 'possibly' in nikval :
                    print(f"nikval misah : {nikval} diinisiasi dummy")

            arrktpdata[arrktpdata.index('nik')+1] = nikval
            ktpdata['nik'] = nikval
            wordmatched.add(i)
            carryocr.remove(word) 
            print(f"data nik : {nikval} sukses ditambahkan") 

        elif i == 4 : #or kata == 'nama'  :
            #collect nama dengan asumsi mungkin saja value nama ada 1-3 elemen array
            # arrname = []
            # j = i + 1  # mulai cek setelah field "nama"

            # while j < len(arrtxtocr):
            #     candidate, skor = process.extractOne(arrtxtocr[j], ktp_fields)
            #     if candidate in ktp_fields and skor >25 :
            #         break  
            #     arrname.append(arrtxtocr[j])
            #     print(f'arrname = {arrname}')
            #     j += 1

            # namaval = ""
            # for n in arrname :
            #     # namaval = namaval.join(validnama(n))
            #     namaval = namaval.join(n)
            #     print(f'namaval = {namaval}')
            namaval = arrtxtocr[i+1]
            arrktpdata[arrktpdata.index('nama')+1] = namaval
            ktpdata['nama'] = namaval 

            # while i<j:
            #     wordmatched.add(i)
            #     i+=1
            
            # carryocr.remove(word)
            # for n in arrname:
            #     carryocr.remove(n)
            wordmatched.add(i)
            wordmatched.add(i+1)
            carryocr.remove(word)
            carryocr.remove(namaval)

            print(f"data nama : {namaval} sukses ditambahkan")
        
        elif (i ==6  )  or (kata == 'tempat tgl lahir' and i<10)  :        #and (  (i-arrktpdata[arrktpdata.index('nama')]) ==2 )
            #handle khusus dengan asumsi value tempat tinggal lahir tidak menempel dengan fieldnya. 
            #asumsi kedua : field tgl lahir sudah ap
            ttlval = arrtxtocr[i+1]
            ktpdata['tempat tgl lahir'] = ttlval
            arrktpdata[arrktpdata.index('tempat tgl lahir')+1] = ttlval
            wordmatched.add(i)
            wordmatched.add(i+1)
            carryocr.remove(word)
            carryocr.remove(ttlval)
            print(f"tempat tgl lahir dengan data {ttlval} diolah dengan raw")

        elif (i ==8 ) or (kata=='jenis kelamin' and i<10) :         #and (  (i-arrktpdata[arrktpdata.index('tempat tgl lahir')]) ==6 or (i-arrktpdata[arrktpdata.index('tempat tgl lahir')])==3  ) 
            nextword = arrtxtocr[i+1] if i+1 < len(arrtxtocr) and len(word)<=14 else None
            genderval = validgender(word, nextword)   

            if 'nyatu' in genderval :
                print(f"genderval nyatu : {genderval}")    
            else :
                if 'misah' in genderval :
                    carryocr.remove(nextword)
                    wordmatched.add(i+1)
                    print(f"gendervall misah : {genderval}") 
                elif 'possibly' in genderval :
                    print(f"genderval misah : {genderval} dengan data belum valid sepenuhnya")
                elif 'dummy' in genderval :
                    print(f"genderval misah : {genderval} diinisiasi dummy")

            arrktpdata[arrktpdata.index('jenis kelamin')+1] = genderval
            ktpdata['jenis kelamin'] = genderval
            wordmatched.add(i)
            carryocr.remove(word) 
            print(f"data jenis kelamin : {genderval} sukses ditambahkan") 

        elif (i==10 ) or (kata == 'gol darah' and i>8 and i<15) :           #and  (i-arrktpdata[arrktpdata.index('jenis kelamin')]) ==2) 
    #cek apakah setelah kata 'golongan darah' apakah field atau engga (field alamat)
            
            nextword = arrtxtocr[i+1] if i+1< len(arrtxtocr) and len(arrtxtocr[i+1])==1  and  process.extractOne(arrtxtocr[i+1], ktp_fields)[0]  not in ['nama', 'alamat', 'agama'] else None
            if nextword!=None:
                darahval = validdarah(nextword)
                if 'misah' in darahval:
                    print(f'darahval misah : {darahval}')
                    wordmatched.add(i+1)
                    carryocr.remove(nextword) 
                elif 'possibly' in darahval:
                    print(f"darahval misah : {darahval} dengan data belum valid sepenuhnya")
            else:
                darahval = 'dummy'
                print(f"darahval misah : {darahval} diinisiasi dummy")

            arrktpdata[arrktpdata.index('gol darah')+1] = darahval
            ktpdata['gol darah'] = darahval
            wordmatched.add(i)
            carryocr.remove(word) 
            print(f"data gol darah : {darahval} sukses ditambahkan") 
                    
        elif (i==11 and  ktpdata['gol darah']=='dummy') or (i==12 and  ktpdata['gol darah']!='dummy') or  (kata == 'alamat' and i>8 and i<15)   :
            # if i>=8 and i < 20:

            alamatval = arrtxtocr[i+1]

            # while i<j:
            #     wordmatched.add(i)
            #     i+=1
            
            # carryocr.remove(word)
            # for n in arrname:
            #     carryocr.remove(n)
            wordmatched.add(i)
            wordmatched.add(i+1)
            carryocr.remove(word)
            carryocr.remove(alamatval)

                
            arrktpdata[arrktpdata.index('alamat')+1] = alamatval
            ktpdata['alamat'] = alamatval



            print(f"data 'alamat : {alamatval} sukses ditambahkan")
            # else:
            #     #bukan alamat harusnya
            #     print(f'kata utk {word} seharusnya bukan alamat , skor = {score}')

        elif (i == 13 )  or (kata == 'rt rw' and i>8 and i<15) :          # and process.extractOne(arrtxtocr[i+2], ktp_fields)[0] in ['kecamatan', 'kel desa']
            # if  i>10 and i<20:
            # rtrwarr = []
            # j = i + 1  # mulai cek setelah field "nama"

            # while j < len(arrtxtocr):
            #     candidate, skor = process.extractOne(arrtxtocr[j], ktp_fields)

            #     if candidate and skor > 25 :
            #         break  

            #     rtrwarr.append(arrtxtocr[j])
            #     j += 1
            # print(rtrwarr)

            # rtrwdummy = ""
            # for a in rtrwarr :
            #     rtrwdummy  = rtrwdummy.join(a)
            #     print(rtrwdummy)
            # print(rtrwdummy)
            # # rtrwval  = validrtrw(rtrwdummy)
            # rtrwval = rtrwdummy
            # if 'misah' in rtrwval :
                        
            #     while i<j:
            #         wordmatched.add(i)
            #         i+=1
                
            #     for a in rtrwarr:
            #         carryocr.remove(a)
            #     print(f"rtrwval misah : {rtrwval}") 

            # elif 'possibly' in rtrwval :
            #     print(f"rtrwval misah : {rtrwval} dengan data belum valid sepenuhnya")
            # elif 'possibly' in rtrwval :
            #     print(f"rtrwval misah : {rtrwval} diinisiasi dummy")

            rtrwval = arrtxtocr[i+1]
            wordmatched.add(i)
            wordmatched.add(i+1)
            carryocr.remove(word)
            carryocr.remove(rtrwval)
            arrktpdata[arrktpdata.index('rt rw')+1] = rtrwval
            ktpdata['rt rw'] = rtrwval

            print(f"data rt rw : {rtrwval} sukses ditambahkan") 

            # else:
            #     print(f'kata utk {word} seharusnya bukan {kata}, skor = {score}')

        elif (i == 15 ) or (kata == 'kel desa' and i>12 and i<20)  :          #and 'alamat' in ktpdata
            if i > 10 and i < 20:
                nextword = arrtxtocr[i+1] if i+1 < len(arrtxtocr) else None
                kelval = validkeldes(nextword)

                if 'misah' in kelval :
                    carryocr.remove(nextword)
                    wordmatched.add(i+1)
                    print(f"kelval misah : {kelval}") 
                elif 'possibly' in kelval :
                    print(f"kelval misah : {kelval} dengan data belum valid sepenuhnya")
                elif 'dummy' in kelval :
                    print(f"kelval misah : {kelval} diinisiasi dummy")   

                arrktpdata[arrktpdata.index('kel desa')+1] = kelval   # ['kelinsi', 'jawa timur']
                ktpdata['kel desa'] = kelval                           # {'kelinsi' : 'jawa timur' }
                wordmatched.add(i)                                  
                carryocr.remove(word) 
                print(f"data kel desa : {kelval} sukses ditambahkan")  
            else : 
                print(f'kata utk {word} seharusnya bukan {kata}, skor = {score}')    

        elif i==17 or (kata == 'kecamatan' and process.extractOne(arrtxtocr[i+2], ktp_fields)[0] in ['agama', 'nama']) :        #and 'alamat' in ktpdata) or (process.extractOne(arrtxtocr[i+2], ktp_fields)[0] in ['agama', 'nama']

            nextword = arrtxtocr[i+1] if i+1 < len(arrtxtocr) and len(word)<=12 else None
            yetword = arrtxtocr[i-1]
            kecval = validkec(word,  nextword)

            if 'nyatu' in kecval :
                print(f"kecval nyatu : {kecval}")    

            else :
                if 'misah' in kecval :
                    carryocr.remove(nextword)
                    wordmatched.add(i+1)
                    print(f"kecval misah : {kecval}") 
                elif 'possibly' in kecval :
                    print(f"kecval misah : {kecval} dengan data belum valid sepenuhnya")
                elif 'dummy' in kecval :
                    print(f"kecval misah : {kecval} diinisiasi dummy")

            arrktpdata[arrktpdata.index('kecamatan')+1] = kecval   # ['kecinsi', 'jawa timur']
            ktpdata['kecamatan'] = kecval                           # {'kecinsi' : 'jawa timur' }
            wordmatched.add(i)                                  
            carryocr.remove(word) 
            print(f"data kecamatan : {kecval} sukses ditambahkan")    
            # else:
            #     print(f'kata utk {word} seharusnya bukan {kata}, skor = {score}')

        elif i==19 or (kata == 'agama' and i<24 and i >15):
            nextword = arrtxtocr[i+1] if i+1 < len(arrtxtocr) else None

            if nextword!=None:
                agamaval = validagama(nextword)
                if 'misah' in agamaval:
                    wordmatched.add(i+1)
                    carryocr.remove(nextword) 
                    print(f'agamaval misah : {agamaval}')
                elif 'possibly' in agamaval:
                    print(f"agamaval misah : {agamaval} dengan data belum valid sepenuhnya")
                elif 'dummy' in agamaval :
                    print(f"agamaval misah : {agamaval} diinisiasi dummy")
            else:
                agamaval = 'dummy'
                print(f"agamaval misah : {agamaval} diinisiasi dummy")

            arrktpdata[arrktpdata.index('agama')+1] = agamaval
            ktpdata['agama'] = agamaval
            wordmatched.add(i)
            carryocr.remove(word) 
            print(f"data agama : {agamaval} sukses ditambahkan") 

        elif i==21 or (kata == 'status perkawinan' and process.extractOne(arrtxtocr[i-2], ktp_fields)[0] in ['agama', 'nama'] ):
        
            nextword = arrtxtocr[i+1] if i+1 < len(arrtxtocr) and len(word) < 16 else None
            kawinval = validkawin(word,nextword)

            if 'nyatu' in kawinval :
                print(f"kawinval nyatu : {kawinval}")    

            else :
                if 'misah' in kawinval :
                    carryocr.remove(nextword)
                    wordmatched.add(i+1)
                    print(f"kawinval misah : {kawinval}") 
                elif 'possibly' in kawinval :
                    print(f"kawinval misah : {kawinval} dengan data belum valid sepenuhnya")
                elif 'dummy' in kawinval :
                    print(f"kawinval misah : {kawinval} diinisiasi dummy")

            arrktpdata[arrktpdata.index('status perkawinan')+1] = kawinval   # ['kawininsi', 'jawa timur']
            ktpdata['status perkawinan'] = kawinval                           # {'kawininsi' : 'jawa timur' }
            wordmatched.add(i)                                  
            carryocr.remove(word) 
            print(f"data status perkawinan : {kawinval} sukses ditambahkan") 
            # else:
            #     print(f'kata utk {word} seharusnya bukan {kata}, skor = {score}')


        elif (i==22 and 'nyatu' in ktpdata['status perkawinan']) or (i==23 and 'misah' in ktpdata['status perkawinan']) or (kata == 'pekerjaan' and i>20):
            # isvalid , skorvalid = process.extractOne(arrtxtocr[i+3], ktp_fields)
            # if isvalid in ['kewargenaraan wn'] and i > 20 :
            
            nextword = arrtxtocr[i+1] if i+1 < len(arrtxtocr) else None

            if nextword!=None:
                jobval = validjob(nextword)
                if 'misah' in jobval :
                    wordmatched.add(i+1)
                    carryocr.remove(nextword) 
                    print(f'jobval misah : {jobval}')
                elif 'possibly' in jobval :
                    print(f"jobval misah : {jobval} dengan data belum valid sepenuhnya")
                elif 'dummy' in jobval :
                    print(f"jobval misah : {jobval} diinisiasi dummy")
            else:
                jobval = 'dummy'
                print(f"jobval misah : {jobval} diinisiasi dummy")

            arrktpdata[arrktpdata.index('pekerjaan')+1] = jobval
            ktpdata['pekerjaan'] = jobval
            wordmatched.add(i)
            carryocr.remove(word) 
            print(f"data pekerjaan : {jobval} sukses ditambahkan")  
            # else :
            #     print(f'kata utk {word} seharusnya bukan {kata}, skor = {score}')


        elif (i==24 and 'nyatu' in ktpdata['status perkawinan']) or (i==25 and 'misah' in ktpdata['status perkawinan']) or (kata == 'kewarganegaraan wn' and i>20):
            isvalid1 , skorvalid1 = process.extractOne(arrtxtocr[i+1], ktp_fields)
            isvalid2 , skorvalid2 = process.extractOne(arrtxtocr[i+2], ktp_fields)
            if i>20 and (isvalid1 in ['berlaku hingga'] or isvalid2 in ['berlaku hingga'] ) :
                nextword = arrtxtocr[i+1] if i+1 < len(arrtxtocr) and len(word) <10 else None
                wnval = validwn(word,nextword)                

                if 'nyatu' in wnval :
                    print(f"wnval nyatu : {wnval}")    

                else :
                    if 'misah' in wnval :
                        carryocr.remove(nextword)
                        wordmatched.add(i+1)
                        print(f"wnval misah : {wnval}") 
                    elif 'possibly' in wnval :
                        print(f"wnval misah : {wnval} dengan data belum valid sepenuhnya")
                    elif 'dummy' in wnval :
                        print(f"wnval misah : {wnval} diinisiasi dummy")

                arrktpdata[arrktpdata.index('kewarganegaraan wn')+1] = wnval   # ['wninsi', 'jawa timur']
                ktpdata['kewarganegaraan wn'] = wnval                           # {'wninsi' : 'jawa timur' }
                wordmatched.add(i)                                  
                carryocr.remove(word) 
                print(f"data kewarganegaraan wn : {wnval} sukses ditambahkan")   
            else:
                print(f'kata utk {word} seharusnya bukan {kata}, skor = {score}')


        # elif kata == 'berlaku hingga' or (i == len(arrtxtocr)-2 and is_mostly_digits(arrtxtocr[i+1])):
        # elif (i==24 and 'nyatu' in ktpdata['status perkawinan']) or (i==25 and 'misah' in ktpdata['status perkawinan'])  or kata == 'berlaku hingga' :
        elif (kata == 'berlaku hingga' and i>20) or (i == len(arrtxtocr)-2 and is_mostly_digits(arrtxtocr[i+1])):

            nextword = arrtxtocr[i+1] if i+1 < len(arrtxtocr)  else None
            berlakuval = validberlaku(nextword) 

            if 'misah' in berlakuval:
                wordmatched.add(i+1)
                carryocr.remove(nextword)
                print(f"berlakuval misah : {berlakuval}") 
            elif 'possibly' in berlakuval:
                print(f"berlakuval misah : {berlakuval} dengan data belum valid sepenuhnya")
            elif 'dummy' in wnval :
                
                print(f"berlakuval misah : {berlakuval} diinisiasi dummy")

            arrktpdata[arrktpdata.index('berlaku hingga')+1] = berlakuval     # ['wninsi', 'jawa timur']
            ktpdata['berlaku hingga'] = berlakuval                           # {'wninsi' : 'jawa timur' }
            wordmatched.add(i)                                  
            carryocr.remove(word) 
            print(f"data berlaku hingga : {berlakuval} sukses ditambahkan")  
            # else:
            #     print(f'kata utk {word} seharusnya bukan {kata}, skor = {score}')

        #     else:
        #         print(f'being processed later : {word}  {kata} {score}')
        # else :
        #     print(f'already processed : {word}  {kata} {score}')


        print(f"arrktp data now = \n{arrktpdata}\n")
        print(f'ktpdata ima : \n{ktpdata}\n')
        print(f'carryocr ima : \n{carryocr}\n')

    tempatlahirval, tgllahirval= ttlextract(ktpdata['nik'], ktpdata['tempat tgl lahir'])

    ktpdata['tempat lahir'] = tempatlahirval
    arrktpdata[arrktpdata.index('tempat lahir')+1] = tempatlahirval

    ktpdata['tgl lahir'] = tgllahirval 
    arrktpdata[arrktpdata.index('tgl lahir')+1] = tgllahirval   

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
    return arrtxtocr, carryocr, ktpdata



def ttlextract(nik :str, datattl :str) :
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
        ttl = re.split(r"[., ]\s*", datattl, maxsplit=1)

    
        listnamakabkota = list(kabkota_df['name'].values)
        #Insert tempat
        tempatlahir,_ = process.extractOne(ttl[0], listnamakabkota)

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
#     # curl -X POST -F "image=@/path/to/your/ktp3.jpg" http://127.0.0.1:5000/vratp/ocr/ktpdata

#     # Contoh CURL untuk /vratp/ocr/ktpimage (setelah POST ke ktpdata)
#     # curl http://127.0.0.1:5000/vratp/ocr/ktpimage > output_image.jpg

#     # Jalankan aplikasi Flask
#     app.run(debug=True) # debug=True hanya untuk development


datadir = 'data'
imgpath = os.path.join(datadir, 'ktp25.jpg')
with open(imgpath, 'rb') as f:
        image_bytes_from_file = f.read()



# rotated_img, angle = straighten_ktp(imgpath, save_path="ktp25_lurus.jpg")
rotated_img, angle = straighten_ktp(image_bytes_from_file, save_path="ktp25_lurus.jpg")
# print(f"[TESTING] Gambar diluruskan dengan sudut {angle:.2f}° dan disimpan ke ktp514_lurus.jpg")

# # 2. OCR pakai gambar hasil rotasi
# _, buf = cv2.imencode(".jpg", cv2.imread(imgpath))

_, buf = cv2.imencode(".jpg", rotated_img)
# ocr_results = imgocr(buf.tobytes())
ocr_results = imgocr(buf.tobytes())
ktpdata,arrktpdata, carryocr = extrocr(ocr_results)
# txtocr = dictToList(ocr_results)
# print(f"hasil ocr mentah : \n{txtocr}\n\n")

if 'image_with_boxes_bytes' in ocr_results and ocr_results['image_with_boxes_bytes'] is not None:
    output_image_path = f'output_25lurus_with_boxes.jpg'
    with open(output_image_path, 'wb') as f:
        f.write(ocr_results['image_with_boxes_bytes'])
    print(f"[TESTING] Gambar dengan bounding box disimpan ke: {output_image_path}")
else:
    print("[TESTING] Tidak ada gambar dengan bounding box yang dihasilkan.")

print(f"hasil arrktpdata  : \n{arrktpdata}\n\n")

print(f"hasil ktp data : \n{ktpdata}\n\n")

print(f"hasil arrktpdata tersisa  : \n{carryocr}\n\n")
print("\n[TESTING] Selesai.")
