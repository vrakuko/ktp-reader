
import os
import re
import cv2
import numpy as np
import json
import pandas as pd
from fuzzywuzzy import process
import easyocr
from flask import Flask, request, jsonify
from flask_cors import CORS
import re
import copy
from valid import validagama, validgender, validkab, validkawin, validkec, validkeldes, validkota, validnama, validnik, validprov, validrtrw, validdarah, validjob, validwn, validberlaku

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
    "provinsi", "kabupaten", "kota", "nik", "nama", "tempat tgl lahir", "tempat lahir", "tanggal lahir",  "jenis kelamin",
    'gol darah', "alamat", "rt rw", "kel desa", "kecamatan", "agama", "status perkawinan",
    "pekerjaan", "kewarganegaraan", "berlaku hingga"
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

def straighten_ktp(img_path, save_path=None, canny_thresh1=50, canny_thresh2=150, hough_thresh=200):

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
    for (_, txt, confs) in reseasy:
        outeasy[txt] = confs
        confeasy.append(confs)
    outeasy['avgconfscore'] = float(np.mean(confeasy)) if confeasy else 0.0
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

        if kata not in ktpdata:
            if score >50:
        
                if kata == "provinsi" :
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

                    arrktpdata[arrktpdata.index(kata)+1] = provval   # ['provinsi', 'jawa timur']
                    ktpdata[kata] = provval                           # {'provinsi' : 'jawa timur' }
                    wordmatched.add(i)                                  
                    carryocr.remove(word) 
                    print(f"data {kata} : {provval} sukses ditambahkan")   

                
                    # proses untuk provinsi
                
                elif kata == "kabupaten":
                    arrktpdata[arrktpdata.index('kota')] = 'nil (alr in kab)'  
        
                    nextword = arrtxtocr[i+1] if i+1 < len(arrtxtocr) and len(word)<=14 else None
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

                    arrktpdata[arrktpdata.index(kata)+1] = kabval
                    ktpdata[kata] = kabval
                    wordmatched.add(i)
                    carryocr.remove(word) 
                    print(f"data {kata} : {kabval} sukses ditambahkan, data kota menjadi nil") 

                elif kata == "kota":
                    arrktpdata[arrktpdata.index('kabupaten')] = 'nil (alr in kota)'  
                    

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

                    arrktpdata[arrktpdata.index(kata)+1] = kabval
                    ktpdata[kata] = kabval
                    wordmatched.add(i)
                    carryocr.remove(word) 
                    print(f"data {kata} : {kabval} sukses ditambahkan, data kota menjadi nil") 

                elif kata == "nik" :
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

                    arrktpdata[arrktpdata.index(kata)+1] = nikval
                    ktpdata[kata] = nikval
                    wordmatched.add(i)
                    carryocr.remove(word) 
                    print(f"data {kata} : {nikval} sukses ditambahkan") 

                elif kata == 'nama' :

                    #collect nama dengan asumsi mungkin saja value nama ada 1-3 elemen array
                    arrname = []
                    j = i + 1  # mulai cek setelah field "nama"

                    while j < len(arrtxtocr):
                        candidate, skor = process.extractOne(arrtxtocr[j], ktp_fields)
                        if candidate in ktp_fields and skor >25 :
                            break  
                        arrname.append(arrtxtocr[j])
                        j += 1

                    namaval = None
                    for n in arrname :
                        namaval = namaval+validnama(n)
                        
                    arrktpdata[arrktpdata.index(kata)+1] = namaval
                    ktpdata[kata] = namaval 

                    while i<j:
                        wordmatched.add(i)
                        i+=1
                    
                    carryocr.remove(word)
                    for n in arrname:
                        carryocr.remove(n)

                    print(f"data {kata} : {namaval} sukses ditambahkan")
                
                elif kata == 'tempat tgl lahir' :
                    #handle khusus dengan asumsi value tempat tinggal lahir tidak menempel dengan fieldnya. 
                    #asumsi kedua : field tgl lahir sudah ap
                
                    print('nanti dulu')

                elif kata=='jenis kelamin':
                    nextword = arrtxtocr[i+1] if i+1 < len(arrtxtocr) and len(word)<=15 else None
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

                    arrktpdata[arrktpdata.index(kata)+1] = genderval
                    ktpdata[kata] = genderval
                    wordmatched.add(i)
                    carryocr.remove(word) 
                    print(f"data {kata} : {genderval} sukses ditambahkan") 

                elif kata == 'goldar':
                    
                    isfield, score = process.extractOne(arrtxtocr[i+1], ktp_fields)             #cek apakah setelah kata 'golongan darah' apakah field atau engga (field alamat)
                    nextword = arrtxtocr[i+1] if i+1< len(arrtxtocr) and len(arrtxtocr[i+1])==1  and  score < 20 else None
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

                    arrktpdata[arrktpdata.index(kata)+1] = darahval
                    ktpdata[kata] = darahval
                    wordmatched.add(i)
                    carryocr.remove(word) 
                    print(f"data {kata} : {darahval} sukses ditambahkan") 
                            
                elif kata == 'alamat' :
                    arradr = []
                    j = i + 1  # mulai cek setelah field "nama"

                    while j < len(arrtxtocr):
                        candidate, skor = process.extractOne(arrtxtocr[j], ktp_fields)
                        if candidate in ktp_fields and skor >40:
                            break  
                        arradr.append(arrtxtocr[j])
                        j += 1

                    alamatval = None
                    for a in arradr :
                        alamatval = alamatval + a
                        
                    arrktpdata[arrktpdata.index(kata)+1] = alamatval
                    ktpdata[kata] = alamatval

                    while i<j:
                        wordmatched.add(i)
                        i+=1
                    
                    carryocr.remove(word)
                    for a in arradr:
                        carryocr.remove(a)

                    print(f"data {kata} : {alamatval} sukses ditambahkan")

                elif kata == 'rt rw':
                    rtrwarr = []
                    j = i + 1  # mulai cek setelah field "nama"

                    while j < len(arrtxtocr):
                        candidate, skor = process.extractOne(arrtxtocr[j], ktp_fields)

                        if candidate and skor > 25 :
                            break  

                        rtrwarr.append(arrtxtocr[j])
                        j += 1
                    print(rtrwarr)

                    rtrwdummy = ""
                    for a in rtrwarr :
                        rtrwdummy  = rtrwdummy.join(a)
                        print(rtrwdummy)
                    print(rtrwdummy)
                    rtrwval  = validrtrw(rtrwdummy)
                    
                    if 'misah' in rtrwval :
                                
                        while i<j:
                            wordmatched.add(i)
                            i+=1
                        
                        for a in rtrwarr:
                            carryocr.remove(a)
                        print(f"rtrwval misah : {rtrwval}") 

                    elif 'possibly' in rtrwval :
                        print(f"rtrwval misah : {rtrwval} dengan data belum valid sepenuhnya")
                    elif 'possibly' in rtrwval :
                        print(f"rtrwval misah : {rtrwval} diinisiasi dummy")



                    arrktpdata[arrktpdata.index(kata)+1] = rtrwval
                    ktpdata[kata] = rtrwval

                    print(f"data {kata} : {rtrwval} sukses ditambahkan") 

                elif kata == 'kel desa':
                    
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

                    arrktpdata[arrktpdata.index(kata)+1] = kelval   # ['kelinsi', 'jawa timur']
                    ktpdata[kata] = kelval                           # {'kelinsi' : 'jawa timur' }
                    wordmatched.add(i)                                  
                    carryocr.remove(word) 
                    print(f"data {kata} : {kelval} sukses ditambahkan")      

                elif kata == 'kecamatan':
                    
                    nextword = arrtxtocr[i+1] if i+1 < len(arrtxtocr) and len(word)<=10 else None
                    kecval = validkec(word, nextword)

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

                    arrktpdata[arrktpdata.index(kata)+1] = kecval   # ['kecinsi', 'jawa timur']
                    ktpdata[kata] = kecval                           # {'kecinsi' : 'jawa timur' }
                    wordmatched.add(i)                                  
                    carryocr.remove(word) 
                    print(f"data {kata} : {kecval} sukses ditambahkan")    

                elif kata == 'agama':
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

                    arrktpdata[arrktpdata.index(kata)+1] = agamaval
                    ktpdata[kata] = agamaval
                    wordmatched.add(i)
                    carryocr.remove(word) 
                    print(f"data {kata} : {agamaval} sukses ditambahkan") 

                elif kata == 'status perkawinan':
                    nextword = arrtxtocr[i+1] if i+1 < len(arrtxtocr) and i > 20 and len(word) > 19 else None
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

                    arrktpdata[arrktpdata.index(kata)+1] = kawinval   # ['kawininsi', 'jawa timur']
                    ktpdata[kata] = kawinval                           # {'kawininsi' : 'jawa timur' }
                    wordmatched.add(i)                                  
                    carryocr.remove(word) 
                    print(f"data {kata} : {kawinval} sukses ditambahkan")       

                elif kata == 'pekerjaan':
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

                    arrktpdata[arrktpdata.index(kata)+1] = jobval
                    ktpdata[kata] = jobval
                    wordmatched.add(i)
                    carryocr.remove(word) 
                    print(f"data {kata} : {jobval} sukses ditambahkan")    

                elif kata == 'kewarganegaraan':
                    nextword = arrtxtocr[i+1] if i+1 < len(arrtxtocr) and len(word) > 19 else None
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

                    arrktpdata[arrktpdata.index(kata)+1] = wnval   # ['wninsi', 'jawa timur']
                    ktpdata[kata] = wnval                           # {'wninsi' : 'jawa timur' }
                    wordmatched.add(i)                                  
                    carryocr.remove(word) 
                    print(f"data {kata} : {wnval} sukses ditambahkan")   

                elif kata == 'berlaku hingga':
                    nextword = arrtxtocr[i+1] if i+1 < len(arrtxtocr)  else None
                    berlakuval = validberlaku(word,nextword) 

                    if 'misah' in berlakuval:
                        wordmatched.add(i+1)
                        carryocr.remove(nextword)
                        print(f"berlakuval misah : {berlakuval}") 
                    elif 'possibly' in berlakuval:
                        print(f"berlakuval misah : {berlakuval} dengan data belum valid sepenuhnya")
                    elif 'dummy' in wnval :
                        
                        print(f"berlakuval misah : {berlakuval} diinisiasi dummy")

                    arrktpdata[arrktpdata.index(kata)+1] = berlakuval     # ['wninsi', 'jawa timur']
                    ktpdata[kata] = berlakuval                           # {'wninsi' : 'jawa timur' }
                    wordmatched.add(i)                                  
                    carryocr.remove(word) 
                    print(f"data {kata} : {berlakuval} sukses ditambahkan")   

        
        if i ==4 :    #nama
            #collect nama dengan asumsi mungkin saja value nama ada 1-3 elemen array
            kata = 'nama'
            arrname = []
            j = i + 1  # mulai cek setelah field "nama"

            while j < len(arrtxtocr):
                candidate, skor = process.extractOne(arrtxtocr[j], ktp_fields)
                if candidate in ktp_fields and skor >40:
                    print('negro ', skor, ' ', candidate)
                    break  
                print(' ', skor, ' ', candidate)
                arrname.append(arrtxtocr[j])
                j += 1

            print(arrname)

            namaval = ""
            for n in arrname :
                namaval = namaval.join(n)
                
            arrktpdata[arrktpdata.index(kata)+1] = namaval
            ktpdata[kata] = namaval 

            while i<j:
                wordmatched.add(i)
                i+=1
            
            carryocr.remove(word)
            for n in arrname:
                carryocr.remove(n)

            print(f"data nama : {namaval} sukses ditambahkan jalur {i}")

        elif i==6:  #ttl
            nama = 'tempat tgl lahir'
            ttlval = arrtxtocr[7]
            arrktpdata[arrktpdata.index(nama)+1] = ttlval
            ktpdata[nama] = ttlval
            print(f"data tempat tgl lahir : {ttlval} sukses ditambahkan jalur {i}")

                        


    print("[DEBUG] 📋 Kamus KTP sementara sebelum dikirim ke ttlextrocr:")
    print(json.dumps(ktpdata, indent=2, ensure_ascii=False))
    
    final_arrktpdata = ktpdata
    print("[END] --- Selesai Fungsi extrocr ---")
    return ttlextrocr(final_arrktpdata)

def ttlextrocr(arrktpdata: dict) -> dict:
    print("\n[START] --- Memulai Fungsi ttlextrocr ---")
    print("[DEBUG] 📥 Menerima arrktpdata:", json.dumps(arrktpdata, indent=2))

    
    
    nik_kotor = arrktpdata['nik'][0:12]

    if len(re.sub(r'[^0-9]', '', str(nik_kotor))) != 12 :
        print(f"⚠️ [PERINGATAN] Panjang NIK setelah dibersihkan bukan 16 ({len(nik_bersih)}). Proses TTL dilewati.")
        return arrktpdata

    nik_bersih = nik_kotor
    arrktpdata['nik'] = nik_bersih
    niktgl_str = nik_bersih[6:8]
    nikbulan_str = nik_bersih[8:10]
    niktahun_str = nik_bersih[10:12]

    
    print(f"[DEBUG] slice NIK: tgl='{niktgl_str}', bln='{nikbulan_str}', thn='{niktahun_str}'")
    
    try:
        niktgl = int(niktgl_str)
        nikbulan = int(nikbulan_str)
        niktahun = int(niktahun_str)

        if niktgl > 40:
            arrktpdata['jenis kelamin'] = 'PEREMPUAN'
            niktgl -= 40
            print("[DEBUG] 🚺 Terdeteksi Perempuan dari NIK.")
        else:
            arrktpdata['jenis kelamin'] = 'LAKI-LAKI'
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
        arrktpdata['tanggal lahir'] = tgllahir

        pos = 5  # posisi setelah 'nama'
        ttl = re.split(r"[., ]\s*", arrktpdata['tempat tgl lahir'], maxsplit=1)
        # print(ttl)
    
        items = list(arrktpdata.items())  # ubah jadi list of tuple
        listnamakabkota = list(kabkota_df['name'].values)
        #Insert tempat
        tempatlahir,_ = process.extractOne(ttl[0], listnamakabkota)
        items.insert(pos, ('tempat lahir', tempatlahir))  # sisipkan key-value

        #insert tgl lahir
        pos = 6

        
        items.insert(pos, ('tanggal lahir', tgllahir ))

        arrktpdata = dict(items)  # balik lagi ke dict

        # ... (sisa logika TTL Anda) ...
        print("[DEBUG] 🎂 Logika Tanggal Lahir berhasil diproses.")
  

    except ValueError:
        print("⚠️ [PERINGATAN] Gagal mengubah potongan NIK menjadi angka. Proses TTL dihentikan.")
        return arrktpdata
    
    print("[END] --- Selesai Fungsi ttlextrocr ---")
    return arrktpdata


datadir = 'data'
imgpath = os.path.join(datadir, 'ktp514.jpg')

# 1. Luruskan dulu
rotated_img, angle = straighten_ktp(imgpath, save_path="ktp514_lurus.jpg")
# print(f"[TESTING] Gambar diluruskan dengan sudut {angle:.2f}° dan disimpan ke ktp514_lurus.jpg")

# # 2. OCR pakai gambar hasil rotasi
# _, buf = cv2.imencode(".jpg", cv2.imread(imgpath))

_, buf = cv2.imencode(".jpg", rotated_img)
# ocr_results = imgocr(buf.tobytes())
ocr_results = imgocr(buf.tobytes())
txtocr = dictToList(ocr_results)
print(f"hasil ocr mentah : \n{txtocr}\n\n")

if 'image_with_boxes_bytes' in ocr_results and ocr_results['image_with_boxes_bytes'] is not None:
    output_image_path = f'output_514lurus_with_boxes.jpg'
    with open(output_image_path, 'wb') as f:
        f.write(ocr_results['image_with_boxes_bytes'])
    print(f"[TESTING] Gambar dengan bounding box disimpan ke: {output_image_path}")
else:
    print("[TESTING] Tidak ada gambar dengan bounding box yang dihasilkan.")

ktpdata = extrocr(ocr_results)
print(f"hasil ktp data : \n{ktpdata}\n\n")

print("\n[TESTING] Selesai.")
