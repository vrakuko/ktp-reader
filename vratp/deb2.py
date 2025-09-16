
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
    "SEUMUR HIDUP"
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


def dictToList(ocrdict):
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

        
        if i in wordmatched:
            print(f"{i} sudah diproses dan valid, lanjut ke elemen selanjutnya")
            continue
        
        kata , score = process.extractOne(word, ktp_fields)

        
        if kata == "provinsi" :
            # misal ['provinsi jawa timur']
            nextword = arrtxtocr[i+1] if i+1 < len(arrtxtocr) and word.length()<=10 else None
            provval = validprov(word, nextword, arrtxtocr  listnamaprov)

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

            nextword = arrtxtocr[i+1] if i+1 < len(arrtxtocr) and word.length()<=11 else None
            kabval = validkab(word, nextword, listnamakabkota)

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
                    kabval = "kabupaten dummy"
                    print(f"kabval misah : {kabval} diinisiasi dummy")

            arrktpdata[arrktpdata.index(kata)+1] = kabval
            ktpdata[kata] = kabval
            wordmatched.add(i)
            carryocr.remove(word) 
            print(f"data {kata} : {kabval} sukses ditambahkan, data kota menjadi nil") 
            # proses untuk kabupaten

        elif kata == "kota":
            arrktpdata[arrktpdata.index('kabupaten')] = 'nil (alr in kota)'  
            

            nextword = arrtxtocr[i+1] if i+1 < len(arrtxtocr) and word.length()<=5 else None
            kotaval = validkota(word, nextword, listnamakabkota)

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
                    kabval = "kabupaten dummy"
                    print(f"kabval misah : {kabval} diinisiasi dummy")

            arrktpdata[arrktpdata.index(kata)+1] = kabval
            ktpdata[kata] = kabval
            wordmatched.add(i)
            carryocr.remove(word) 
            print(f"data {kata} : {kabval} sukses ditambahkan, data kota menjadi nil") 
            # proses untuk kota


        elif kata == "nik" :
            if word.length()>4:
                # Pattern: (?<=nik\s)\d+ → ambil digits setelah "nik "
                polanik = r'(?:nik|n1k|n1kk|NIK|NI4|NIA|NIk|Nlk|MiK|Mk|Nk|NK|.ik|.K)[\s:;.]{0,4}'   #asumsi pola umum pada 'nik : '
                #pemotongan nik pada word utk mengambil nik-nya saja
                cutnik = re.search(polanik, word)
                nikdummy = word[cutnik.end():]
                print(f"nik nyatu : {nikdummy}")
            else :
                nikdummy = arrtxtocr[i+1]

            lennikdummy = nikdummy.length()
            if lennikdummy > 14:
                numcount, ltrcount, symcount = 0
                for c in nikdummy :
                    if c.isdigit():
                        numcount+=1 
                    elif c.isalpha(): # Huruf
                        ltrcount += 1
                    else: # Karakter lain seperti simbol, spasi
                        symcount += 1
            
                if numcount>ltrcount and numcount>symcount:
                    
                    nikval = nikdummy
                    carryocr.remove(nikdata)
                    wordmatched.add(i+1)
                else :
                    rtwval = "possibly {nikdummy}"  
                    print(f"data {kata} : {adrval} tidak valid makanya nilainya gitu")

                
                ktpdata[kata]=nikval
                wordmatched.add(i+1)
                carryocr.remove(nikdummy)
                print(f"nik misah : {nikdummy}") 
                
            # if  nikdummy.length()>13:  
            arrktpdata[arrktpdata.index(kata)+1] = nikdummy
            ktpdata[kata] = nikdummy
            wordmatched.add(i)
            carryocr.remove(word)
            print(f"data {kata} : {nikdummy} sukses ditambahkan")



        elif kata == 'nama' :
            namainit = arrtxtocr[i+1]
            namavalue = namainit
            arrktpdata[arrktpdata.index(kata)+1] = namavalue
            wordmatched.add(i)
            wordmatched.add(i+1)
            carryocr.remove(word)
            carryocr.remove(namainit)
            print(f"data {kata} : {namavalue} sukses ditambahkan")
            

        elif kata == 'tempat tgl lahir' :
            numlist = r'[0OQoC1i!l/I2Z3Eg4AH5S$fg6G7T8B&%9gqa]'
            poladate = rf'({numlist}{{2}})[\s-]{{0,2}}({numlist}{{2}})[\s-]{{0,2}}({numlist}{{4}})'
            polatempatlahir = rf'(.*{2,50}?)'
            polattl = rf'(?:(?:{polatempatlahir})[\s,.]{{0,4}}(?:{poladate}))'
            # match= re.search(polattl, word)
            if match:
                # ttlvalue=match.group().split(',')[0]
                ttlvalue = "possibly jakarta 01-01-2001"
                print(f"ttl nyatu : {ttlvalue} tapi ini dummy dulu aja sih...\n")
                print('nanti dulu, caaapek gw')
            else :
                ttlinit = arrtxtocr[i+1]
                match= re.search(polattl, ttlinit)
                if match:
                    ttlvalue=match.group()
                    wordmatched.add(i+1)
                    carryocr.remove(ttlinit)
                    print(f"ttl misah : {ttlvalue}")

            
            # arrktpdata[arrktpdata.index(kata)+1] = "jakarta 01-01-2001"
            # wordmatched.add(i)
            # carryocr.remove(word)

            arrktpdata[arrktpdata.index(kata)+1] = ttlvalue
            wordmatched.add(i)
            carryocr.remove(word)
            print(f"data {kata} : {ttlvalue} sukses ditambahkan")

            
            

        elif kata == 'jenis kelamin' :
            genderval = ['LAKI-LAKI', 'PEREMPUAN']
            if word.length()>8 :
                gendervalue, _ = process.extractOne(word, genderval)
                print(f"jenis kelamin nyatu : {gendervalue}")
            else:
                genderinit = arrtxtocr[i+1]
                gendervalue, _ = process.extractOne(genderinit, genderval)
                carryocr.remove(genderinit)
                wordmatched.add(i+1)
                print(f"jenis kelamin misah: {gendervalue}")

                
                arrktpdata[arrktpdata.index(kata)+1] = gendervalue
                wordmatched.add(i)
                carryocr.remove(word)
                print(f"data {kata} : {gendervalue} sukses diadd")

        elif kata =='gol darah':
            pass

        elif kata == 'alamat' :
            #asumsi value ga nyatu sama field
            adrdata = arrtxtocr[i+1]

            match, score = process.extractOne(adrdata, ktp_fields)

            if match : 
                if score>40:
                    

            adrval = adrdata
            arrktpdata[arrktpdata.index(kata)+1] = adrval
            wordmatched.add(i)
            wordmatched.add(i+1)
            carryocr.remove(word)
            carryocr.remove(adrdata)

            print(f"data {kata} : {adrval} sukses diadd")

        elif kata == 'rt/rw' :
            rtwdata = arrtxtocr[i+1]

            numcount = 0
            ltrcount = 0
            symcount = 0

            for c in rtwdata :
                if c.isdigit():
                    numcount+=1 
                elif c.isalpha(): # Huruf
                    ltrcount += 1
                else: # Karakter lain seperti simbol, spasi
                    symcount += 1

            if numcount>ltrcount and numcount>symcount:
                rtwval = rtwdata
                carryocr.remove(rtwdata)
                wordmatched.add(i+1)
            else :
                rtwval = "possibly 000/000"  
                print(f"data {kata} : {adrval} tidak valid makanya nilainya gitu")
            
            arrktpdata[arrktpdata.index(kata)+1] = rtwval
            ktpdata[kata]=rtwval
            wordmatched.add(i)
            carryocr.remove(word)

            print(f"data {kata} : {adrval} sukses diadd")

        elif kata == 'kel/desa' :
            keldesadata = arrtxtocr[i+1]
            match, score = process.extractOne(keldesadata, kelname)
            if match :
                if score > 64:
                    keldesaval = keldesadata
                else:
                    keldesaval = 'possibly '+keldesadata
                    print('posibily {keldesaval} dari {keldesadata} cuma masih sus')
            else:
                keldesaval = 

            
            arrktpdata[arrktpdata.index(kata)+1] = keldesaval
            ktpdata[kata]=keldesaval
            wordmatched.add(i)
            wordmatched.add(i+1)
            carryocr.remove(word)
            carryocr.remove(keldesadata)

            print(f"data {kata} : {adrval} sukses diadd")




        elif feld_cand== "kecamatan" and word.length>11:
            if word.length()>11 :
                kecname, _ = process.extractOne(word, listnamakec)
                print(f"kecamatan nyatu : {kecname}")
            else:
                kecdata = arrtxtocr[i+1]
                gendervalue, _ = process.extractOne(genderdata, genderval)
                carryocr.remove(genderdata)
                wordmatched.add(i+1)
                print(f"jenis kelamin misah: {gendervalue}")

                
                arrktpdata[arrktpdata.index(kata)+1] = gendervalue
                wordmatched.add(i)
                carryocr.remove(word)
                print(f"data {kata} : {gendervalue} sukses diadd")          

            kecname, _ = process.extractOne(word, listnamakec)
            arrktpdata[23] = kecname
            wordmatched.add(i) 

        
        elif kata == "status perkawinan" :
            if word.length>19:
                kawindummy, _ = process.extractOne(word,statekawinval )
                if kawindummy
                arrktpdata[27] = statekawin
                wordmatched.add(i) 



        elif feld_cand== "status perkawinan" and word.length>19:

            statekawin, _ = process.extractOne(word,statekawinval )
            arrktpdata[27] = statekawin
            wordmatched.add(i) 

        elif feld_cand== "kewarganegaraan" and word.length>13:

            statewn, _ = process.extractOne(word,citizenval )
            arrktpdata[31] = statewn
            wordmatched.add(i)      


        if word not in arrktpdata:
            #pola ttl
            pass



        
        if i == 0 :
            provval, score = process.extractOne(word,listnamaprov)
            #print(f"ditemukan provval yg paling mungkin dengan {word} : {provval} dengan skor: {score}")

            value = provval
            feld = 'provinsi'
            # print(f"✔️ Ditemukan field '{feld}' : {value} di kasus provinsi")

            wordmatched.add(i)
            
            print(f"  [LOGIC] 🔢 Kasus provinsi: Ditemukan '{value}' .")

        elif i ==1 :
            kabukota, score = process.extractOne(word,listnamakabkota)
            # print(f"ditemukan kabukota yg paling mungkin dengan {word} : {kabukota} dengan skor: {score}")

            if 'Kota' in kabukota :
                feld= 'kota'
                arrktpdata['kabupaten'] = 'alr in city'
                fieldset.add('kabupaten')
                
            else :
                feld = 'kabupaten'
                arrktpdata['kota'] = 'alr in kab'
                fieldset.add('kota')
                

            value = kabukota
            print(f"  [LOGIC] 🔢 Kasus kabukota: Ditemukan '{value}' .")
            wordmatched.add(i)
            

        elif i == 2: # Saat memproses NIK
            feld = 'nik'
            value = arrtxtocr[3]
            print(f"  [LOGIC] 🔢 Kasus NIK: Ditemukan '{value}' pada baris berikutnya.")
            arrktpdata[feld] = value
            wordmatched.add(i)
            wordmatched.add(i+1)

         #kasus field nyatu dengan value  (misal 'provnisijambi', 'kota kediri', 'status perkawinan : belum kawin' )
        else : 
            
             #kasus field nyatu dengan value  (misal 'provnisijambi', 'kota kediri', 'status perkawinan : belum kawin' )
            # feld_cand, score = process.extractOne(word, ktp_fields, processor=lambda s: s.lower().replace(',', '').replace('.', ''))
            feld_cand, score = process.extractOne(word, ktp_fields)
            print(f'feld_cand = {feld_cand} with score {score}')

            value = None

            if score >= 60 and feld_cand not in arrktpdata:

                feld = feld_cand
                if feld_cand == 'kecamatan' and len(word)>9 :

                    #case 1 langsung aja bandingin sama listnama kec
                    value, score = process.extractOne(word,listnamakec)
                    wordmatched.add(i)
                    print(f"  [LOGIC] 🔢 Kasus Kecmatan: Ditemukan '{value}' pada field nyatu dnegan value.")


                    #case 2 yg dihubungin sama kabukota
                    # kecname, score = process.extractOne(word,listnamakec)
                    # print(kecname)
                    # idkec = kec_dict.get(kecname)
                    # print(idkec)

                    # #asumsi bahwa kabupaten sudah pasti ada nilainya as kecamatan diperiksa setelah kabupaten
                    # if arrktpdata['kabupaten']!='alr in city':
                    #     idkk = kabkota_dict.get(arrktpdata['kabupaten'])
                    # else :
                    #     idkk = kabkota_dict.get(arrktpdata['kota'])

                    # listidkec = list(id for id in kec_dict.values() if idkk in id)
                    # # print(listidkec)

                    # if idkec in listidkec :      #idkec ga kepake, value kecname akan berubah
                    #     #asumsi nik sudah terisi juga
                    #     value = kecname
                    # #print(f"✔️ Ditemukan field '{feld}' : {value} di kasus kabukota")

                    #     wordmatched.add(i)
                    #     print(f"  [LOGIC] 🔢 Kasus Kecmatan: Ditemukan '{value}' pada field nyatu dnegan value.")
                    # fieldset.add(feld_cand)
                    # kataset.add(word)
                elif feld_cand == 'status perkawinan' :
                    statekawin, score = process.extractOne(word, statekawinval)
                    value = statekawin
                    wordmatched.add(i)
                    print(f"  [LOGIC] 🔢 Kasus Status Kawin: Ditemukan '{value}' pada field nyatu dnegan value.")
                elif feld_cand == 'kewarganegaraan':
                    citizenvalue, f = process.extractOne(word, citizenval)
                    value = citizenvalue
                    print(f"  [LOGIC] 🔢 Kasus Status Kewarganegaraan: Ditemukan '{value}' pada field nyatu dnegan value.")

                else :

                    try:
                        metavalue = word[len(feld):].strip()

                        # for metavalue in metavalues :
                        if metavalue and not metavalue.isspace() and len(metavalue) > 1:
                            #print(f'ptential value = {metavalue}')
                            value = metavalue.strip(':;')
                    
                            wordmatched.add(i)
                            print(f"✔️ Ditemukan field menyatu '{feld}': {metavalue} untuk word {word} ")


                    except Exception:
                        pass # Lanjut ke strategi 2 jika regex gagal


            #kasus terpisah (field diikuti value)
            if value is None: # Jika nilai belum ditemukan 
                if i + 1 < len(arrtxtocr):
                    value_candidate = arrtxtocr[i+1]

                _, next_score = process.extractOne(value_candidate, ktp_fields)

                

                print(f'value_candidate = {value_candidate} with score {next_score}')
                if next_score < 75:
                    
                    feld = feld_cand

                    if feld_cand =='kel/desa'  :
                        #skema utama
                        kelname, _ = process.extractOne(value_candidate, listnamakel)
                        
                        value = kelname
                        print(f"✔️ Ditemukan field '{feld_cand}' : {value} dengan kondisi terpisah pada kelurahan")

                    elif feld_cand == 'kecamatan':
                        kecname, f = process.extractOne(value_candidate, listnamakec)
                        # print(f"✔️ Ditemukan field '{feld}' : {value} dengan kondisi terpisah pada kecamatan")
                        
                        idkel = kel_dict.get(arrktpdata['kel/desa'])
                        idkec = kec_dict.get(kecname)

                        if idkec not in idkel :
                            arrktpdata['kelurahan'] = arrktpdata['kel/desa'] + "could be true"
                            arrktpdata['kecamatan'] = kecname + "could be true"
                            print(f"✔️ Ditemukan field '{feld_cand}' : {value} dengan kondisi terpisah pada kecamatan dan kemungkinan salah kawokwaoak")

                        else :
                            value = kecname
                            print(f"✔️ Ditemukan field '{feld_cand}' : {value} dengan kondisi terpisah pada kecamatan")
                    
                    elif feld_cand == 'agama':
                        value, f = process.extractOne(value_candidate, agamaval)
                        print(f"✔️ Ditemukan field '{feld}' : {value} dengan kondisi terpisah pada agama")
                    elif feld_cand == 'pekerjaan':
                        value, f = process.extractOne(value_candidate, jobval)
                        print(f"✔️ Ditemukan field '{feld}' : {value} dengan kondisi terpisah pada pekerjaan")
                    elif feld_cand == 'berlaku hingga':
                        value, f = process.extractOne(value_candidate, untilval)
                        print(f"✔️ Ditemukan field '{feld}' : {value} dengan kondisi terpisah pada berlaku hingga")
                    elif feld_cand == 'kewarganegaraan':
                        if len(value_candidate) <= 4 :
                            value, f = process.extractOne(value_candidate, citizenval)
                            print(f"✔️ Ditemukan field '{feld}' : {value} tipe str dengan kondisi terpisah pada kewarganegaraan")
                        # value, f = process.extractOne(value_candidate, citizenval)
                        # if len(value) > 3 :
                        #     print(f"✔️ Ditemukan field '{feld}' : {value} tipe str dengan kondisi terpisah pada kewarganegaraan")
                        # else :
                        #     value  = value_candidate
                        #     print(f"✔️ Ditemukan field '{feld}' : {value} tipe date dengan kondisi terpisah pada kewarganegaraan")
                        

                    else :    
                        value = value_candidate

                        print(f"✔️ Ditemukan field '{feld}' : {value_candidate} dengan kondisi terpisah")

                    wordmatched.add(i)
                    wordmatched.add(i+1)

                
                    

                else :

                    print('gaje terpisah')
                    continue

            
        if value:
            print('bale bale')
            if feld not in arrktpdata:
                print('elf gaje')
                ktpdata[feld] = value
                # fieldset.add(feld)
            else:
                print(f'field {feld} dah ada di ktpdata, ga perlu diurus')
            print(f'arrktpdata ima : {ktpdata}')
        else:
            print('ndeh')
          

    for field in ktp_fields :
        if field not in arrktpdata :
            ktpdata[field] = 'dummy'


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

    # if nik_kotor[12:] 


    # if not nik_kotor:
    #     print("⚠️ [PERINGATAN] Kunci 'nik' tidak ada. Proses TTL dilewati.")
    #     return arrktpdata
    
    # nik_bersih = re.sub(r'[^0-9]', '', str(nik_kotor))
    nik_bersih = nik_kotor
    # print(f"[DEBUG] 🧼 NIK setelah dibersihkan: '{nik_bersih}'")

    # if len(nik_bersih) != 16:
    #     print(f"⚠️ [PERINGATAN] Panjang NIK setelah dibersihkan bukan 16 ({len(nik_bersih)}). Proses TTL dilewati.")
    #     arrktpdata['nik'] = nik_bersih
    #     return arrktpdata

    arrktpdata['nik'] = nik_bersih
    niktgl_str = nik_bersih[6:8]
    nikbulan_str = nik_bersih[8:10]
    niktahun_str = nik_bersih[10:12]

    # nikprov_str = nik_bersih[6:8]
    # nikkk_str = nik_bersih[8:10]
    # nikkec_str = nik_bersih[10:12]

    
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

    # if not arrktpdata.get('tempat tgl lahir') or 'tempat tgl lahir' not in arrktpdata.keys():
        arrktpdata['tanggal lahir'] = tgllahir

    # else :
        

        pos = 5  # posisi setelah 'nama'
        ttl = re.split(r"[., ]\s*", arrktpdata['tempat tgl lahir'], maxsplit=1)
        # print(ttl)
    
        items = list(arrktpdata.items())  # ubah jadi list of tuple

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
