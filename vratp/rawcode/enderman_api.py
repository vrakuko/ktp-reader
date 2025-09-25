import os
import re
import cv2
import numpy as np
import json
import pandas as pd
from fuzzywuzzy import process
import easyocr
from flasgger import Swagger

from http.server import BaseHTTPRequestHandler, HTTPServer

from flask import Flask, request, jsonify
from flask_cors import CORS

swagger_config = {
    "headers": [],
    "specs": [
        {
            "endpoint": 'apispec_1',
            "route": '/apispec_1.json',
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui_bundle_path": "/flasgger_static/swagger-ui-bundle.js",
    "swagger_ui_standalone_path": "/flasgger_static/swagger-ui-standalone-preset.js",
    "specs_route": "/apidocs/" # Ini URL untuk UI dokumentasi Anda
}

# # from fastapi import FastAPI
# # from fastapi.middleware.cors import CORSMiddleware 


app = Flask(__name__)
CORS(app)
swagger = Swagger(app, config=swagger_config)
# app = FastAPI()


# origins = [
#     "http://localhost",
#     "http://localhost:8080",
#     # Tambahkan alamat lain jika diperlukan
# ]
# Memuat model & data di sini agar tidak diulang setiap request (SOLUSI PERFORMA)
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=origins,
#     allow_credentials=True,
#     allow_methods=["*"], # allow all metode (get post, dll)
#     allow_headers=["*"], # allow all tipe header
# )

# @app.get("/")
# def read_root():
#     return {"message": "Selamat datang di API Python saya!"}



ereader = easyocr.Reader(['id'], gpu=False)

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
# 2. FUNGSI-FUNGSI MURNI (Bersih dari logic API)
# ===================================================================

def imgocr(image_bytes: bytes) -> dict:
    """Fungsi ini HANYA menerima bytes gambar dan mengembalikan hasil OCR sebagai dict."""
    imgori = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
    
    reseasy = ereader.readtext(imgori)
    
    outeasy = {}
    confeasy = []
    for (_, txt, confs) in reseasy:
        outeasy[txt] = confs
        confeasy.append(confs)
    outeasy['avgconfscore'] = float(np.mean(confeasy)) if confeasy else 0.0
    return outeasy

def extrocr(txthasilocr: list) -> dict:
    """
    Fungsi ini HANYA menerima list teks hasil OCR dan mengekstrak field KTP.
    (SOLUSI TANGGUNG JAWAB FUNGSI TERCAMPUR)
    """
    ktp_data = {}
    wordmatched = set()
    
    for i, word in enumerate(txthasilocr):
        print(f'{i} {word}')

        if i in wordmatched:
            # print(f'{i} utk kata {word} udah ada di wordmatched')
            continue # Lanjut ke kata berikutnya jika sudah ditemukan di tahap ini

        #kasus provinsi
        if i == 0 :
            provname, score = process.extractOne(word,listnamaprov)
            #print(f"ditemukan provname yg paling mungkin dengan {word} : {provname} dengan skor: {score}")

            value = provname
            feld = 'provinsi'
            # print(f"✔️ Ditemukan field '{feld}' : {value} di kasus provinsi")

            wordmatched.add(i)
    
        #kasus kabukota
        elif i ==1 :
            kabukota, score = process.extractOne(word,listnamakabkota)
            # print(f"ditemukan kabukota yg paling mungkin dengan {word} : {kabukota} dengan skor: {score}")

            if 'Kota' in kabukota :
                feld= 'kota'
            else :
                feld = 'kabupaten'


            value = kabukota
            #print(f"✔️ Ditemukan field '{feld}' : {value} di kasus kabukota")

            wordmatched.add(i)
  


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
# 3. FUNGSI API (Jembatan antara Dunia Luar dan Fungsi Murni)
# ===================================================================

@app.route('/ocr/ktp', methods=['POST'])
#swagger.validate() # Opsional, untuk validasi otomatis input
def handle_ocr_request():
    """
    Endpoint untuk melakukan OCR pada gambar KTP dan mengekstrak datanya.
    Mengembalikan data KTP yang terstruktur dan hasil OCR mentah.
    ---
    tags:
      - OCR KTP
    parameters:
      # Karena Anda menghilangkan input gambar, bagian 'parameters' ini harus diubah
      # atau dihapus jika tidak ada input sama sekali.
      # Untuk tujuan testing, kita bisa membuat parameter opsional atau menghapusnya.
      # Jika Anda ingin tetap ada, tapi tidak wajib, ubah 'required: true' menjadi 'required: false'
      # Tapi untuk kasus ini, kita akan hapus bagian parameter 'image' agar tidak ada input yang diharapkan.
      # Jika Anda ingin API tetap menerima input tapi diabaikan untuk testing,
      # maka bisa biarkan 'parameters' seperti semula dan abaikan di kode.

      # Untuk tujuan demonstrasi dan menghilangkan input:
      # Anda bisa mengosongkan 'parameters:' atau menghapus baris di bawahnya
      # jika Anda ingin endpoint ini tidak menerima parameter apapun saat testing.
      # Misalnya:
      # parameters: []

      # Atau, jika Anda hanya ingin membuatnya opsional, ubh 'required: true' menjadi 'required: false'
      # Jika Anda menghapus seluruh blok 'parameters', Flasgger akan menganggap tidak ada input.
      # Untuk saat ini, saya akan biarkan bagian 'parameters' seperti semula agar dokumentasinya tidak error,
      # dan kita akan abaikan input di dalam fungsi. Ini adalah praktik umum untuk API dummy.
      - name: image
        in: formData
        type: file
        required: false # Mengubah ke false agar tetap bisa diakses tanpa file
        description: (OPSIONAL UNTUK TESTING) File gambar KTP. Tidak digunakan saat ini.

    responses:
      200:
        description: Data KTP berhasil diekstraksi.
        schema:
          type: object
          properties:
            success: {type: boolean, example: true}
            data:
              type: array
              items:
                - type: object
                  properties:
                    provinsi: {type: string, example: "JAWA TIMUR"}
                    # Tambahkan semua field KTP yang mungkin diekstrak di sini sebagai contoh
                    kabupaten: {type: string, example: "JEMBER"}
                    nik: {type: string, example: "3509190704990003"}
                    nama: {type: string, example: "MOHAMMAD AINUN ARDIANSYAH"}
                    'tempat tgl lahir': {type: string, example: "Jember, 17-04-1999"}
                    'jenis kelamin': {type: string, example: "Laki-laki"} # Akan diperbaiki oleh ttlextrocr
                    agama: {type: string, example: "ISLAM"}
                    'status perkawinan': {type: string, example: "BELUM KAWIN"}
                    pekerjaan: {type: string, example: "PELAJAR/MAHASISWA"}
                    kewarganegaraan: {type: string, example: "WNI"}
                    'berlaku hingga': {type: string, example: "SEUMUR HIDUP"}
                # Karena Anda tidak mengembalikan ocr_result_dict secara terpisah,
                # objek kedua dalam array 'data' ini dihapus dari skema respons.
                # Namun, jika Anda ingin menyertakan hasil OCR mentah,
                # Anda bisa mengembalikannya sebagai bagian dari extracted_data
                # atau membuat dummy ocr_result_dict di dalam fungsi ini.
                # Untuk saat ini, kita ikuti instruksi Anda dan hanya kembalikan extracted_data.
                # - type: object
                #   properties:
                #     text_recognized_1: {type: number, example: 0.95}
                #     avgconfscore: {type: number, example: 0.91}
      400:
        description: Request tidak valid.
        schema:
          type: object
          properties:
            error: {type: string, example: "Request harus menyertakan file dengan key 'image'"}
      500:
        description: Terjadi kesalahan internal server.
        schema:
          type: object
          properties:
            error: {type: string, example: "Terjadi kesalahan internal: [detail error]"}
    """
    # === Bagian ini adalah kode Python yang sebenarnya ===

    # Data dummy txthasilocr yang Anda sediakan
    txthasilocr = ['PROVINSI JAWA TIMUR', 'KABUPATEN JEMBER', 'NIK', '3509190704990003', 'Namg', 'MOHAMMAD AINUN ARDIANSYAH', 'Topatiqi Lahi', 'JevbEr. 17-04-1999', 'Jensahhamur', 'EAKHLAKI', 'AMMal', 'JTEUKU UMAR UINGK KRAJAN', 'BARAT', 'FIRW', '002/006', 'Kel Desa', 'EGAEBESAR', 'Kecamatan', 'KALIWAIES', 'Agama', 'ISEAM', 'Stalus Perkawinan', 'BELUM KAWIN', 'Pckorjaan', 'PELAJARIMAHASISWA', 'JEMBER', 'Kowrarganegaraan', 'WNI', '03-03-2018', 'Beraku Hingga', 'SEUMUB HIOUP']

    # Panggil fungsi extrocr Anda
    extracted_data = extrocr(txthasilocr)
    
    # Karena Anda ingin menghilangkan input gambar, kita juga mengasumsikan
    # tidak ada 'ocr_result_dict' terpisah yang dikembalikan dari imgocr.
    # Jadi, respons 'data' hanya berisi objek 'extracted_data'.
    return jsonify({'success': True, 'data': [extracted_data]})
    
    # ... (implementasi fungsi Anda)

# @app.route('/ocr/ktp', methods=['POST'])
# def handle_ocr_request():
#     # """Fungsi ini satu-satunya yang berinteraksi dengan request API."""
#     # if 'image' not in request.files:
#     #     return jsonify({'error': "Request harus menyertakan file dengan key 'image'"}), 400
#     # file = request.files['image']
#     # if file.filename == '':
#     #     return jsonify({'error': 'Tidak ada file yang dipilih'}), 400

#     try:
#         # Langkah 1: Dapatkan data mentah dari request
#         # image_bytes = file.read()
        
#         # # Langkah 2: Panggil fungsi murni pertama (OCR)
#         # ocr_result_dict = imgocr(image_bytes)
#         txthasilocr =  ['PROVINSI JAWA TIMUR', 'KABUPATEN JEMBER', 'NIK', '3509190704990003', 'Namg', 'MOHAMMAD AINUN ARDIANSYAH', 'Topatiqi Lahi', 'JevbEr. 17-04-1999', 'Jensahhamur', 'EAKHLAKI',  'AMMal', 'JTEUKU UMAR UINGK KRAJAN', 'BARAT', 'FIRW', '002/006', 'Kel Desa', 'EGAEBESAR', 'Kecamatan', 'KALIWAIES', 'Agama', 'ISEAM', 'Stalus Perkawinan', 'BELUM KAWIN', 'Pckorjaan', 'PELAJARIMAHASISWA', 'JEMBER', 'Kowrarganegaraan', 'WNI', '03-03-2018', 'Beraku Hingga', 'SEUMUB HIOUP']
#         # Langkah 3: Siapkan input untuk fungsi murni kedua
#         # txthasilocr = [key for key in ocr_result_dict if key != 'avgconfscore']
        
#         # Langkah 4: Panggil fungsi murni kedua (Ekstraksi)
#         extracted_data = extrocr(txthasilocr)
        
        
#         # Langkah 6: Kembalikan hasil akhir
#         return jsonify({'success': True, 'data': [extracted_data]})

#     except Exception as e:
#         import traceback

#         print(traceback.format_exc())
#         return jsonify({'error': f'Terjadi kesalahan internal: {str(e)}'}), 500

# ===================================================================
# Menjalankan Server
# ===================================================================
if __name__ == '__main__':
    # app.run(host='192.168.56.1', port=5000)
    # app.run(host='10.0.2.2', port=5000)
    app.run(host='0.0.0.0', port=5000, debug = True)