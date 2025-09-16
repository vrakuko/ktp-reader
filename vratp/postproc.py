import json
import pandas as pd
from flask import Flask, request, jsonify
from proc import imgocr

# with open ("D:\dataset\resocr ktp284\imgorirgb ktp284_ocrcpu.json", 'r', encoding='utf-8') as f:
#   ocrres = json.load(f)


#ocrres = imgocr(imgfile)
# txthasilocr = [item for item in ocrres if item != 'avgconfscore']
# print('txthasilocr = ',txthasilocr)

import re
from fuzzywuzzy import process

# Daftar field KTP standar sebagai referensi
ktp_fields = [
    "provinsi",
    "kabupaten",
    "kota",
    "nik",
    "nama",
    "tempat tgl lahir",
    "jenis kelamin",
    'gol darah',
    "alamat",
    "rt/rw",
    "kel/desa",
    "kecamatan",
    "agama",
    "status perkawinan",
    "pekerjaan",
    "kewarganegaraan",
    "berlaku hingga"
]

# Kamus kemungkinan OCR error untuk tiap karakter
recchar = {
    "a": ["a", "@", "4"],
    "b": ["b", "8"],
    "c": ["c", "("],
    "d": ["d"],
    "e": ["e", "3"],
    "f": ["f"],
    "g": ["g", "9", '6'],
    "h": ["h", "#"],
    "i": ['i','1','!','l','|','\\','/','I'],
    "j": ["j"],
    "k": ["k"],
    "l": ["l", "1", "i", "|", "!", "I"],
    "m": ["m", "nn", 'n'],
    "n": ["n", 'm'],
    "o": ["o", "0", "O", "Q", ")"],
    "p": ["p"],
    "q": ["q", "9"],
    "r": ["r"],
    "s": ["s", "5", "$"],
    "t": ["t", "7"],
    "u": ["u", "v"],
    "v": ["v", "u"],
    "w": ["w", "vv"],
    "x": ["x", "%"],
    "y": ["y"],
    "z": ["z", "2"],

    "0": ["0", "O", "Q",'o', '()',')', ']', '[', '(', 'C'],
    "1": ['1','i','!','l','|','\\','/','I'],
    "2": ["2", "Z"], 
    "3": ["3", "E"],
    "4": ["4", "A"],
    "5": ["5", "S", '$', 'f'],
    "6": ["6", "G"],
    "7": ["7", "T"],
    "8": ["8", "B", '&', '%'],
    "9": ["9", "g", "q"],
}

# array nilai yg mungkin pada beberapa field
agama =  ['Islam', 'Kristen', 'Protestan', 'Katolik', 'Hindu', 'Buddha', 'Konghuchu']
statekawin = ['Belum Kawin', 'Kawin', 'Cerai Hidup', 'Cerai Mati']
job = ['Pelajar', 'Mahasiswa', 'T']

         

# Bikin dictionary regex siap pakai
recchar = {
    ch: "[" + "".join(re.escape(alt) for alt in alts) + "]"
    for ch, alts in recchar.items()
}

#pattern field
# keyword_patterns = {
#     'provinsi': f"(?:{recchar['p']}{recchar['r']}{recchar['o']}{recchar['v']}{recchar['i']}{recchar['n']}{recchar['s']}{recchar['i']})\\s+([A-Z\\s]+)",
#     'kabupaten_kota': f'(?:{recchar["k"]}{recchar["a"]}{recchar["b"]}{recchar["u"]}{recchar["p"]}{recchar["a"]}{recchar["t"]}{recchar["e"]}{recchar["n"]}|{recchar["k"]}{recchar["o"]}{recchar["t"]}{recchar["a"]})\\s+([A-Z\\s]+)',
#     'status_perkawinan': f'(?:{recchar["s"]}{recchar["t"]}{recchar["a"]}{recchar["t"]}{recchar["u"]}{recchar["s"]}\s?{recchar["p"]}{recchar["e"]}{recchar["r"]}{recchar["k"]}{recchar["a"]}{recchar["w"]}{recchar["i"]}{recchar["n"]}{recchar["a"]}{recchar["n"]})\\s?[:\-]?\\s?([A-Z\\s]+)',
#     'kewarganegaraan' : f'(?:{recchar["k"]}{recchar["e"]}{recchar["w"]}{recchar["a"]}{recchar["r"]}{recchar["g"]}{recchar["a"]}{recchar["n"]}{recchar["e"]}{recchar["g"]}{recchar["a"]}{recchar["r"]}{recchar["a"]}{recchar["a"]}{recchar["n"]})\s?[;:]?\s?({recchar["w"]}{recchar["n"]}{recchar["a"]}|{recchar["w"]}{recchar["n"]}{recchar["i"]})?'
# }

#kumpulan txthasilocr utk test 

# txthasilocr=  ['PROVINSI JAWA TIMUR', 'KOTA SURABAYA', 'NIK', '35780570]d010003', 'Nama', 'SALMAA ARIIBAH IMTINAAN', 'TempavTgl Lahr', 'SURABAYA, 30-10-2001', 'Jonis kelamin', 'PEREMPUAN', 'ColDarah', 'Alamal', 'WONOREJO 137 8', 'atirw', '003/003', 'Kel Desa', 'WONOREJO', 'Kocamatan', 'TEGALSAAI', 'Agama', 'ISLAM', 'Stalus Perkawinan', 'BELUM KAWIN', 'Pokerjaan', 'PELAJAAMAHASISWA', 'Kewarganegaraan', 'WNI', '19-11-2010', 'Barlaku Hınoga', 'SEUMUR HIDUP']
# txthasilocr =  ['PROVINSI JAWA TENGAH', 'KABUPATEN BANYUMAS', 'NIK', '330225430189000)', 'Nomng', 'FIKA JANUARTI', 'TompelTe Lahkr', 'BANYUMAS, 03-01-1008', 'Jenie Kelamin', 'PEREMPUAN', 'Gol Daroh', 'Alomoi', 'KARANGLEWAS LOR', 'RTIRW', '001', '003', 'KevDone', 'Kecemuten', 'PURWOKERTO BARAT', 'Ageme', 'ISLAM', 'Stotus Perkowinan : BELUM KAWIN', 'DaNYUMAS', 'Pekerfaan', 'KARYAWAN Swasta', '00/0-2012', 'Kewerpanogereen; WNI', 'Bertaku', '03-01-2017', 'IHinooe']

# txthasilocr =  ['PROVINSI JAWA TIMUR', 'KABUPATEN JEMBER', 'NIK', '3509190704990003', 'Namg', 'MOHAMMAD AINUN ARDIANSYAH', 'Topatiqi Lahi', 'JevbEr. 17-04-1999', 'Jensahhamur', 'EAKHLAKI',  'AMMal', 'JTEUKU UMAR UINGK KRAJAN', 'BARAT', 'FIRW', '002/006', 'Kel Desa', 'EGAEBESAR', 'Kecamatan', 'KALIWAIES', 'Agama', 'ISEAM', 'Stalus Perkawinan', 'BELUM KAWIN', 'Pckorjaan', 'PELAJARIMAHASISWA', 'JEMBER', 'Kowrarganegaraan', 'WNI', '03-03-2018', 'Beraku Hingga', 'SEUMUB HIOUP']
# txthasilocr =  ['PROVINSI DKI JAKARTA', 'JAKARTA TIMUR', 'Nik', '3175064703900012', 'Nama', 'DIAN LUTFIANA', 'TempaV TglLahır', 'BEKASL 07 03 1990', 'venis Kelamin', 'PEREMPUAN', 'Gol Darah', 'Alamat', 'PULO GEBANG PERMII BLOKF 88', 'RTRW', '905 /012', 'Ke Desa', 'PULO GEBANG', 'Kecaratan', 'CAKUNG', 'Agama', "'ISLAM", 'Stalus Perkawinan: BELUM KAWIN', 'Pekerjaan', 'PEL AJRMAHASISWA', 'Kewarganegaraan WNI', '14-06-2012', 'Berlaku ', '07-03,2017', 'JHingga']
# txthasilocr =  ['RhOViNSI JaWa TIMür[', 'Kora KEQIRl', 'Rgw', '357101gg02a80002', 'Mas Yuslia:MAWAAN', 'TerpauTg', 'ir', '29.02', 'Jeniskeauri', 'PeaevUan', '6', 'Hlama', '2ad', 'AvPw', '427 005', 'Ka)0esa', "a'", 'REJO', 'Kacamajar', 'Mo:oROIO', 'Agama', '152', 'stats Perkawinan_BELUM', 'avn', 'c2kero', 'PerajaavAHA5i814', 'KOTAjEdf', "2warganeja'0n", '17-Da 2v15', 'Benaky', 'SeuUfhioL?', '199?', 'WN', 'Hinoja', '3118?']

# txthasilocr = ['PROVINSIBANTEN:', 'KABUPATENSERANG', 'VaK', '360411590490000]', 'Nama', 'WiNDA SILVINA', 'Tempalggl Lahi', 'SERANG 29 04*1994.', "slefis Këlamin'", 'PEREMPUAN', 'Gol Darahi', 'Alamat', 'KP SEWTUL', 'RTARW', "'001/001", 'KelDesa', 'SENTU', 'Kecamalan:', 'KRAGILAN', 'Againa', '{SLAü', 'Status Peikawinan: BEXUM KAWIN:', "'Pekerjàan_", 'PELAARUAMAHASISWA', 'SERNNG', 'Kewarganiegäraan: WNI', '10-d2 2018', 'Berlaku ', "SEUMUR HIDUP'", 'Híngga']
# txthasilocr =  ['PROVINSF JaWA Timur', 'KOTAKEDIRI', 'NIK', '3571015302980002', 'Nama', 'AlMas YuslIKa Mawaani', 'Tempavigi Lahi', 'Kediri', '19-0241998', 'Janis kelanin', 'Perenpuan', 'Cor Uoah', 'Alamay', 'WILIS Ta:A H', '3', 'RTRW.', '027 085', "'KevDesa", 'GAMPUREVo', 'Kecanalan', 'MOJOROIO', 'Agama', 'ISEAM', 'Slatus', 'Perkawinan', 'Be', 'LUM KAWIN', 'Pekegaan', "PELAJAR MAHAS'SV4", 'KOTAKEDIF', 'evarganegaran', 'WNI', '17:03 2915', 'Jeraku Hingga', 'Seuuur Hidup', '3M8']



# nikktp = txthasilocr[3]

def extrocr (imgfile) :

    image_bytes = imgfile.read()

    ocrres = imgocr(image_bytes)

    # ocrres = imgocr(imgfile)

    txthasilocr = [item for item in ocrres if item != 'avgconfscore']
    print('txthasilocr = ',txthasilocr)

    ktp_data = {}
    wordmatched = set()
    # fieldset = set()
    # kataset = set()


    for i, word in enumerate(txthasilocr):
        print(f'{i} {word}')

        if i in wordmatched:
            print(f'{i} utk kata {word} udah ada di wordmatched')
            continue # Lanjut ke kata berikutnya jika sudah ditemukan di tahap ini

        #kasus provinsi
        if i == 0 :
            prov = pd.read_csv('D:\dataset\provinsi.csv')
            # kabkota['id'] = kabkota['id'].astype(str)
            prov = prov.set_index('id')['name'].to_dict()
            listnamaprov = list(prov.values())

            provname, score = process.extractOne(word,listnamaprov)
            print(f"ditemukan provname yg paling mungkin dengan {word} : {provname} dengan skor: {score}")

            value = provname
            feld = 'provinsi'
            print(f"✔️ Ditemukan field '{feld}' : {value} di kasus provinsi")

            wordmatched.add(i)
            fieldset.add(feld)
            kataset.add(word)
    


        #kasus kabukota
        elif i ==1 :
        
            kabkota = pd.read_csv('D:\dataset\kabupaten_kota.csv')
            # kabkota['id'] = kabkota['id'].astype(str)
            kabkota = kabkota.set_index('id')['name'].to_dict()
            listnamakabkota = list(kabkota.values())

            kabukota, score = process.extractOne(word,listnamakabkota)
            print(f"ditemukan kabukota yg paling mungkin dengan {word} : {kabukota} dengan skor: {score}")

            if 'Kota' in kabukota :
                feld= 'kota'
            else :
                feld = 'kabupaten'


            value = kabukota
            print(f"✔️ Ditemukan field '{feld}' : {value} di kasus kabukota")

            wordmatched.add(i)
            fieldset.add(feld)
            kataset.add(word)


        #kasus nik 
        elif i == 2 :
            feld = 'nik'
            value= txthasilocr[3]

            print(f"✔️ Ditemukan field '{feld}' : {value} di kasus nik")

            wordmatched.add(i)
            wordmatched.add(i+1)
            fieldset.add(feld)
            kataset.add(word)
            kataset.add(value)

        

        #kasus field nyatu dengan value  (misal 'provnisijambi', 'kota kediri', 'status perkawinan : belum kawin' )
        else : 
            best_match, score = process.extractOne(word, ktp_fields, processor=lambda s: s.lower().replace(',', '').replace('.', ''))
            print(f'best_match = {best_match} with score {score}')

            value = None

            if score >= 60 and best_match not in ktp_data:
                if best_match == 'kecamatan' :
                    feld = 'kecamatan'

                    kec = pd.read_csv('D:\dataset\kecamatan.csv')
                    # kabkota['id'] = kabkota['id'].astype(str)
                    kec = kec.set_index('id')['name'].to_dict()
                    listnamakec = list(kec.values())

                    kecname, score = process.extractOne(word,listnamakec)
                    print(f"ditemukan kabukota yg paling mungkin dengan {word} : {kecname} dengan skor: {score}")


                    value = kecname
                    print(f"✔️ Ditemukan field '{feld}' : {value} di kasus kabukota")

                    wordmatched.add(i)
                    fieldset.add(best_match)
                    kataset.add(word)
            
                else:

                    try:
                        # field_regex = r'\b' + re.escape(best_match) + r'\b'
                        # match = re.search(field_regex, word, re.IGNORECASE)

                        # potential_value = word[match.end():]
                        # print(f'ptential value = {potential_value}')
                        # metavalues = []

                        # cutter = [len(best_match)-2, len(best_match)-1, len(best_match), len(best_match)+1, len(best_match)+2]
                        # for cut in cutter :
                        #   metavalues.append(word[cut:]).strip()
                        feld = best_match
                        metavalue = word[len(feld):].strip()


                        # for metavalue in metavalues :
                        if metavalue and not metavalue.isspace() and len(metavalue) > 1:

                            print(f'ptential value = {metavalue}')
                            value = metavalue.strip(':;')
                            
                            wordmatched.add(i)
                            fieldset.add(feld)
                            kataset.add(value)
                            print(f"✔️ Ditemukan field menyatu '{feld}': {metavalue} untuk word {word} dnegan pakai regex patterns + fuzz")


                    except Exception:
                        pass # Lanjut ke strategi 2 jika regex gagal


            #kasus terpisah (field diikuti value)
            if value is None: # Jika nilai belum ditemukan dari strategi 1
                if i + 1 < len(txthasilocr):
                    value_candidate = txthasilocr[i+1]

                _, next_score = process.extractOne(value_candidate, ktp_fields)
                print(f'value_candidate = {value_candidate} with score {next_score}')
                if next_score < 75:

                    value = value_candidate
                    print(f"✔️ Ditemukan field '{feld}' : {value_candidate} dengan kondisi terpisah")

                    wordmatched.add(i)
                    wordmatched.add(i+1)
                    fieldset.add(feld)
                    kataset.add(word)
                    kataset.add(value)

                else :
                    print('gaje terpisah')
                    continue

            
        if value:
            ktp_data[feld] = value
            print(f'ktp_data = {ktp_data}')
        
        # if ktp_data[]


        print(f'wordmatched index = {wordmatched}')
        print(f'fieldset = {fieldset}')
        print(f'kataset = {kataset}')

        
    # print('gaje terpisah')
    # continue

    return ttlextrocr (ktp_data)



def ttlextrocr (ktp_data) : 
    nikktp = ktp_data.get('nik')
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

    pos = 5  # posisi setelah 'nama'

    ttl = re.split(r"[., ]\s*", ktp_data['tempat tgl lahir'], maxsplit=1)
    print(ttl)

    items = list(ktp_data.items())  # ubah jadi list of tuple

    #Insert tempat
    items.insert(pos, ('tempat lahir', ttl[0] ))  # sisipkan key-value


    #insert tgl lahir
    pos = 6

    bulan_nama = [
        "Januari", "Februari", "Maret", "April", "Mei", "Juni",
        "Juli", "Agustus", "September", "Oktober", "November", "Desember"
    ]

    if int(niktahun) > 10 :
        niktahun = str(int(niktahun) + 1900)
    else :
        niktahun = str(int(niktahun) + 2000)

    tgllahir = f'{niktgl} {bulan_nama[int(nikbulan)]} {niktahun}'

    items.insert(pos, ('tanggal lahir', tgllahir ))

    ktp_data = dict(items)  # balik lagi ke dict


    # print (f'ktp_data setelah= {ktp_data}')

    return ktp_data


    
# app = Flask(__name__)



# @app.route('/ocr/ktp', methods=['POST'])
# def handle_ocrreq():
#     if 'image' not in request.files:
#         return jsonify({'error': 'Tidak ada file gambar'}), 400

#     file = request.files['image']

#         # 2. Validasi: Pastikan nama filenya tidak kosong
#     if file.filename == '':
#         return jsonify({'error': 'Tidak ada file yang dipilih'}), 400
    
#     try:
#         # NOTE: Di sini Anda perlu memanggil library OCR Anda (EasyOCR/PaddleOCR)
#         # Kode di bawah ini hanya menggunakan data dummy 'txthasilocr'
#         # Ganti baris ini dengan pemanggilan OCR asli
#         # Contoh: image_bytes = file.read() -> img = cv2.imdecode(...) -> hasil_ocr = reader.readtext(img)
#         # txthasilocr= ['PROVINSF JaWA Timur', 'KOTAKEDIRI', 'NIK', '3571015302980002', 'Nama', 'AlMas YuslIKa Mawaani', 'Tempavigi Lahi', 'Kediri', '19-0241998', 'Janis kelanin', 'Perenpuan', 'Cor Uoah', 'Alamay', 'WILIS Ta:A H', '3', 'RTRW.', '027 085', "'KevDesa", 'GAMPUREVo', 'Kecanalan', 'MOJOROIO', 'Agama', 'ISEAM', 'Slatus', 'Perkawinan', 'Be', 'LUM KAWIN', 'Pekegaan', "PELAJAR MAHAS'SV4", 'KOTAKEDIF', 'evarganegaran', 'WNI', '17:03 2915', 'Jeraku Hingga', 'Seuuur Hidup', '3M8']
#         imgbyte = file.read()

#         # Proses teks hasil OCR
#         processed_data = extrocr(imgfile)
        
#         # Kembalikan hasilnya sebagai JSON
#         return jsonify({'success': True, 'data': processed_data})

#     except Exception as e:
#         return jsonify({'error': f'Terjadi kesalahan di server: {e}'}), 500

# if __name__ == '__main__':
#     # Jalankan server. host='0.0.0.0' agar bisa diakses dari jaringan lokal (HP)
#     app.run(host='0.0.0.0', port=5000)



# ocrres = imgocr("D:\dataset\kowareta\ktp1.jpg")
ktp_data = ttlextrocr(extrocr("D:\dataset\kowareta\ktp1.jpg"))

# #--------------------------------------------------------

listfieldktpdata = list(ktp_data.keys())

# print(listfieldktpdata)

print('\n\n')

for field in ktp_fields :
#   print(f'field = {field}')

  if field not in listfieldktpdata :

    ktp_data[field] = "varaz"

print(f'ktp data = \n\n {json.dumps(ktp_data, indent=4, ensure_ascii=False)}')

# print (len(ktp_fields))
# print(len(listfieldktpdata))


# # ktp_fields = [
# #     "provinsi",
# #     "kabupaten",
# #     "kota",
# #     "nik",
# #     "nama",
# #     "tempat tgl lahir",
# #     "jenis kelamin",
# #     'gol darah',
# #     "alamat",
# #     "rt/rw",
# #     "kel/desa",
# #     "kecamatan",
# #     "agama",
# #     "status perkawinan",
# #     "pekerjaan",
# #     "kewarganegaraan",
# #     "berlaku hingga"
# # ]



# print(ktp_data)
# print(json.dumps(ktp_data, indent=4, ensure_ascii=False))

# print (len(ktp_fields))
# print(len(listfieldktpdata))