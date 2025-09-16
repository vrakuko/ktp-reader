import os
import re
import cv2
import numpy as np
import json
import pandas as pd
from fuzzywuzzy import process
import io # Diperlukan untuk handle image bytes

# --- MODIFIKASI 1: Import library baru ---
import pytesseract
from PIL import Image 

from flask import Flask, request, jsonify
from flask_cors import CORS

# --- MODIFIKASI 2: (KHUSUS WINDOWS) Arahkan ke file instalasi Tesseract ---
# Jika Tesseract tidak ada di PATH sistem Anda, hapus tanda '#' di bawah dan sesuaikan path-nya.
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

app = Flask(__name__)
CORS(app)

# --- MODIFIKASI 3: Hapus inisialisasi easyocr ---
# ereader = easyocr.Reader(['id'], gpu=False)

# ===================================================================
# Sisa kode untuk memuat data CSV dan list field KTP tetap sama
# Pastikan path CSV Anda benar
# ===================================================================
ktp_fields = [
    "provinsi", "kabupaten", "kota", "nik", "nama", "tempat tgl lahir", "jenis kelamin",
    'gol darah', "alamat", "rt/rw", "kel/desa", "kecamatan", "agama", "status perkawinan",
    "pekerjaan", "kewarganegaraan", "berlaku hingga"
]


agamaval = [
    "ISLAM",
    "KRISTEN",
    "KATOLIK",
    "HINDU",
    "BUDDHA",
    "KHONGHUCU"
]

statekawinval = [
    "BELUM KAWIN",
    "KAWIN",
    "CERAI HIDUP",
    "CERAI MATI"
]

jobval = [
    "PELAJAR/MAHASISWA",
    "MENGURUS RUMAH TANGGA",
    "KARYAWAN SWASTA",
    "WIRASWASTA",
    "PEGAWAI NEGERI SIPIL",
    "BELUM/TIDAK BEKERJA"
]

citizenval = [
    "WNI",
    "WNA"
]

untilval = [
    "SEUMUR HIDUP", "berlaku hingga"
]

# ... (kode list agamaval, statekawinval, jobval, dll. tetap sama) ...
# ... (kode untuk membaca file-file CSV tetap sama) ...
try:
    # Menggunakan path relatif agar bisa jalan di mana saja (SOLUSI HARDCODED PATH)
    prov_df = pd.read_csv('D:/dataset/provinsi.csv')
    listnamaprov = list(prov_df['name'].values)

    kabkota_df = pd.read_csv('D:/dataset/kabupaten_kota.csv')
    listnamakabkota = list(kabkota_df['name'].values)
    kabkota_dict = kabkota_df.set_index('name')['id'].astype(str).to_dict()

    try:
        kec_df = pd.read_csv('D:/dataset/kecamatan.csv')
        listnamakec = list(kec_df['name'].values)
    except :
        print('engro')
    # PERBAIKAN BUG: Menggunakan kec_df, bukan kabkota_df
    kec_dict = kec_df.set_index('name')['id'].astype(str).to_dict()

    kel_df = pd.read_csv('D:/dataset/kelurahan.csv')
    listnamakel = list(kel_df['name'].values)
    kel_dict = kel_df.set_index('name')['id'].astype(str).to_dict()
except FileNotFoundError as e:
    print(f"FATAL ERROR: Pastikan file CSV ada di folder 'data/'. Detail: {e}")
    exit()
# ===================================================================
# FUNGSI-FUNGSI MURNI
# ===================================================================

# --- MODIFIKASI 4: Ganti total fungsi imgocr ---
def imgocr(image_bytes: bytes) -> dict:
    """Fungsi ini HANYA menerima bytes gambar dan mengembalikan hasil OCR sebagai dict menggunakan Pytesseract."""
    
    # Buka gambar dari bytes menggunakan Pillow
    img = Image.open(io.BytesIO(image_bytes))
    
    # (Opsional tapi direkomendasikan) Ubah ke grayscale untuk hasil lebih baik
    img = img.convert('L')

    ocr_data = pytesseract.image_to_data(img, lang='ind', output_type=pytesseract.Output.DICT)
    
    output = {}
    confidences = []
    
    n_boxes = len(ocr_data['level'])
    for i in range(n_boxes):
        # Ambil confidence score, jika di atas 40 (filter noise)
        conf = int(ocr_data['conf'][i])
        if conf > 40:
            text = ocr_data['text'][i]
            if text.strip():
                output[text] = float(conf) / 100.0
                confidences.append(float(conf))

    output['avgconfscore'] = float(np.mean(confidences)) if confidences else 0.0
    return output

# ===================================================================
# Fungsi extrocr dan ttlextrocr TIDAK PERLU DIUBAH SAMA SEKALI
# karena input dan outputnya sudah disesuaikan oleh fungsi imgocr baru
# ===================================================================
def extrocr(txthasilocr: list) -> dict:
    # ... (KODE ANDA DI SINI, TIDAK ADA PERUBAHAN) ...
    ktp_data = {}
    wordmatched = set()
    
    for i, word in enumerate(txthasilocr):
        print(f'{i} {word}')

        if i in wordmatched:
            # print(f'{i} utk kata {word} udah ada di wordmatched')
            continue # Lanjut ke kata berikutnya jika sudah ditemukan di tahap ini

        word, score = process.extractOne(word,feld_cand)

        if (word == 'provinsi') :
            provname, score = process.extractOne(word,listnamaprov)
            #print(f"ditemukan provname yg paling mungkin dengan {word} : {provname} dengan skor: {score}")

            value = provname
            feld = 'provinsi'
            # print(f"✔️ Ditemukan field '{feld}' : {value} di kasus provinsi")

            wordmatched.add(i)
    
        #kasus kabukota
        elif (word == 'kabupaten'):
            kabname, score = process.extractOne(word,listnamakabkota)
            # print(f"ditemukan kabukota yg paling mungkin dengan {word} : {kabukota} dengan skor: {score}")
            feld= 'kabupaten'


            value = kabname
            #print(f"✔️ Ditemukan field '{feld}' : {value} di kasus kabukota")

            wordmatched.add(i)

        elif (word == 'kota'):

            kotaname, score = process.extractOne(word,listnamakabkota)
            # print(f"ditemukan kabukota yg paling mungkin dengan {word} : {kabukota} dengan skor: {score}")

            feld= 'kota'

            value = kotaname
            #print(f"✔️ Ditemukan field '{feld}' : {value} di kasus kabukota")

            wordmatched.add(i)

        elif (word == 'kota'):

        #kasus nik 
        elif i == 2 :
            feld = 'nik'
            value= txthasilocr[3]

            #print(f"✔️ Ditemukan field '{feld}' : {value} di kasus nik")

            wordmatched.add(i)
            wordmatched.add(i+1)


        

        #kasus field nyatu dengan value  (misal 'provnisijambi', 'kota kediri', 'status perkawinan : belum kawin' )
        else : 
            feld_cand, score = process.extractOne(word, ktp_fields, processor=lambda s: s.lower().replace(',', '').replace('.', ''))
            #print(f'feld_cand = {feld_cand} with score {score}')

            value = None

            if score >= 60 and feld_cand not in ktp_data:
                feld = feld_cand
                if feld_cand == 'kecamatan' and len (word) > 9 :

                    kecname, score = process.extractOne(word,listnamakec)
                    #print(f"ditemukan kabukota yg paling mungkin dengan {word} : {kecname} dengan skor: {score}")

                    value = kecname
                    #print(f"✔️ Ditemukan field '{feld}' : {value} di kasus kabukota")

                    wordmatched.add(i)
                    # fieldset.add(feld_cand)
                    # kataset.add(word)
                elif feld_cand == 'status perkawinan' :
                    statekawin, score = process.extractOne(word, statekawinval)
                    value = statekawin
                    wordmatched.add(i)
                elif feld_cand == 'kewarganegaraan':
                    citizenvalue, f = process.extractOne(word, citizenval)
                    value = citizenvalue
                    wordmatched.add(i)
            
                else:

                    try:
                        metavalue = word[len(feld):].strip()

                        # for metavalue in metavalues :
                        if metavalue and not metavalue.isspace() and len(metavalue) > 1:
                            #print(f'ptential value = {metavalue}')
                            value = metavalue.strip(':;')
                    
                            wordmatched.add(i)
                            #print(f"✔️ Ditemukan field menyatu '{feld}': {metavalue} untuk word {word} dnegan pakai regex patterns + fuzz")


                    except Exception:
                        pass # Lanjut ke strategi 2 jika regex gagal


            #kasus terpisah (field diikuti value)
            if value is None: # Jika nilai belum ditemukan 
                if i + 1 < len(txthasilocr):
                    value_candidate = txthasilocr[i+1]

                _, next_score = process.extractOne(value_candidate, ktp_fields)
                #print(f'value_candidate = {value_candidate} with score {next_score}')
                if next_score < 75:
                    feld = feld_cand

                    if feld_cand =='kel/desa'  :
                        #skema utama
                        kelname, _ = process.extractOne(value_candidate, listnamakel)
                        
                        value = kelname

                    elif feld_cand == 'kecamatan':
                        kecname, f = process.extractOne(value_candidate, listnamakec)
                        # print(f"✔️ Ditemukan field '{feld}' : {value} dengan kondisi terpisah pada kecamatan")
                        if 'kel/desa' in ktp_data:
                            idkel = kel_dict.get(ktp_data['kel/desa'])
                            idkec = kec_dict.get(kecname)

                            if idkec not in idkel :
                                ktp_data['kelurahan'] = ktp_data['kel/desa'] + "could be true"
                                ktp_data['kecamatan'] = kecname + "could be true"


                        else :
                            value = kecname
                    
                    elif feld_cand == 'agama':
                        value, f = process.extractOne(value_candidate, agamaval)

                    elif feld_cand == 'pekerjaan':
                        value, f = process.extractOne(value_candidate, jobval)
                    
                    elif feld_cand == 'berlaku hingga':
                        value, f = process.extractOne(value_candidate, untilval)
                    
                    elif feld_cand == 'kewarganegaraan':
                        
                        if len(value_candidate) <= 4 :
                            value, f = process.extractOne(value_candidate, citizenval)
                    else:
                        value = value_candidate
                    #print(f"✔️ Ditemukan field '{feld}' : {value_candidate} dengan kondisi terpisah")

                    wordmatched.add(i)
                    wordmatched.add(i+1)

                else :
                    #print('gaje terpisah')
                    continue

            
        if value:
            if feld not in ktp_data:
                ktp_data[feld] = value
            #print(f'ktp_data = {ktp_data}')
    for f in ktp_fields:
        if f not in ktp_data :
            ktp_data[f] = 'dummy'
        # if ktp_data[]


        #print(f'wordmatched index = {wordmatched}')


    return ttlextrocr(ktp_data)

def ttlextrocr (ktp_data) : 
    # ... (KODE ANDA DI SINI, TIDAK ADA PERUBAHAN) ...
    nikktp = ktp_data['nik'][0:12]
    if len(re.sub(r'[^0-9]', '', str(nikktp))) != 12 :
        return ktp_data
    
    # print(nikktp)

    niktgl = nikktp[6:8]
    # print (niktgl)

    nikbulan = nikktp[8:10]
    # print (nikbulan)

    niktahun = nikktp[10:12]
    # print (niktahun)

    date  = [niktgl, nikbulan , niktahun]

    if int(niktgl) > 40  :
        ktp_data['jenis kelamin'] = 'Perempuan'
        niktgl = str(int(niktgl) - 40)
    else : 
        ktp_data['jenis kelamin'] = 'Laki-laki'

    bulan_nama = [
        "Januari", "Februari", "Maret", "April", "Mei", "Juni",
        "Juli", "Agustus", "September", "Oktober", "November", "Desember"
    ]
    
    if int(niktahun) > 10 :
        niktahun = str(int(niktahun) + 1900)
    else :
        niktahun = str(int(niktahun) + 2000)

    tgllahir = f'{niktgl} {bulan_nama[int(nikbulan)-1]} {niktahun}'

    items = list(ktp_data.items()) 
    ttl = re.split(r"[., ]\s*", ktp_data['tempat tgl lahir'], maxsplit=1)

    pos = 5  # posisi setelah 'nama'

    #Insert tempat
    tempatlahir,_ = process.extractOne(ttl[0], listnamakabkota)
    items.insert(pos, ('tempat lahir', tempatlahir ))  # sisipkan key-value


    #insert tgl lahir
    pos = 6

    items.insert(pos, ('tanggal lahir', tgllahir ))

    ktp_data = dict(items)  # balik lagi ke dict


    # print (f'ktp_data setelah= {ktp_data}')

    return ktp_data
# ===================================================================
# FUNGSI API (TIDAK ADA PERUBAHAN)
# ===================================================================
@app.route('/ocr/ktp', methods=['POST'])
def handle_ocr_request():
    # ... (KODE ANDA DI SINI, TIDAK ADA PERUBAHAN) ...
    if 'image' not in request.files:
        return jsonify({'error': "Request harus menyertakan file dengan key 'image'"}), 400
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'Tidak ada file yang dipilih'}), 400

    try:
        # Langkah 1: Dapatkan data mentah dari request
        image_bytes = file.read()
        
        # Langkah 2: Panggil fungsi murni pertama (OCR)
        ocr_result_dict = imgocr(image_bytes)
        
        # Langkah 3: Siapkan input untuk fungsi murni kedua
        txthasilocr = [key for key in ocr_result_dict if key != 'avgconfscore']
        
        # Langkah 4: Panggil fungsi murni kedua (Ekstraksi)
        extracted_data = extrocr(txthasilocr)
        
        
        # Langkah 6: Kembalikan hasil akhir
        return jsonify({'success': True, 'data': [extracted_data,ocr_result_dict]})

    except Exception as e:
        import traceback

        print(traceback.format_exc())
        return jsonify({'error': f'Terjadi kesalahan internal: {str(e)}'}), 500
# ===================================================================
# Menjalankan Server (TIDAK ADA PERUBAHAN)
# ===================================================================
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)