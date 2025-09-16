from fuzzywuzzy import process
import pandas as pd
import os
import re


datasetdir = "dataset" # Pastikan path ini benar atau gunakan os.path.join(os.getcwd(), 'dataset')
datadir = 'data'

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



def validprov (word : str, nextword : str = None) -> str:
    listnamaprov = list(prov_df['name'].values)
    # misal ['provinsi jawa timur']
    if len(word) > 10:
        provval, _ = process.extractOne(word, listnamaprov)  
        provval += ' nyatu'
    else :
        #case langka , misal ['provinsi', 'jawa timur']
        if nextword == None:
            provval = 'dummy'
        else:
            provdummy = nextword
            match , score = process.extractOne(provdummy, listnamaprov)
            if match :
                if score>60 :
                    provval = match + ' misah'
                else:   #misal ['provinsi jawa', 'timur']
                    provval = match+' possibly'
            else :
                provval = match + " dummy"

    return provval


def validkab  (word : str, nextword : str= None) -> str:
    listnamakabkota = list(kabkota_df['name'].values)
    if len(word) > 12 :
        kabval, _ = process.extractOne(word, listnamakabkota)
        kabval += ' nyatu'
    else :  #case tidak umum
            
        if nextword == None:
            kabval = 'dummy'
        else:
            kabdummy = nextword
            match , score = process.extractOne(kabdummy, listnamakabkota)
            if match :
                if score>60 :
                    kabval = match   + ' misah'
                else:   #misal ['provinsi jawa', 'timur']
                    kabval = match+' possibly'
            else :
                kabval = match+ " dummy"

    return kabval




def validkota  (word : str, nextword : str= None) -> str:
    listnamakabkota = list(kabkota_df['name'].values)
    if len(word) > 6 :
        kotaval, _ = process.extractOne(word, listnamakabkota)
        kotaval += ' nyatu'
    else :  #case tidak umum
        if nextword == None:
            kotaval = 'dummy'
        else:
            kotadummy = nextword
            match , score = process.extractOne(kotadummy, listnamakabkota)
            if match :
                if score>60 :
                    kotaval = match + ' misah'
                else:   #misal ['provinsi jawa', 'timur']
                    kotaval = match+' possibly'
            else :
                kotaval = match + " dummy"

    return kotaval



def validnik(word:str, nextword : str = None):
    if len(word)>4:
        # Pattern: (?<=nik\s)\d+ → ambil digits setelah "nik "
        polanik = r'(?:nik|n1k|n1kk|NIK|NI4|NIA|NIk|Nlk|MiK|Mk|Nk|NK|.ik|.K)[\s:;.]{0,4}'   #asumsi pola umum pada 'nik : '
        #pemotongan nik pada word utk mengambil nik-nya saja
        cutnik = re.search(polanik, word)
        nikdummy = word[cutnik.end():]

        lennikdummy = len(nikdummy)


        if lennikdummy > 14:
            numcount =0
            ltrcount = 0
            symcount = 0
            for c in nikdummy :
                if c.isdigit():
                    numcount+=1 
                elif c.isalpha(): # Huruf
                    ltrcount += 1
                else: # Karakter lain seperti simbol, spasi
                    symcount += 1

            
                
            if numcount>ltrcount and numcount>symcount:
                if numcount == lennikdummy :
                    nikval = nikdummy+ ' nyatu'
                else :
                    nikval = nikdummy + ' possibly'   #kotor means nik terkontaminasi karakter selain angka
                
            else :                                       
                nikval = nikdummy + ' possibly'      #angka menjadi karakter minoritas di nik, lebih kotor dari kondisi pertama
        else:
            nikval = nikdummy + ' dummy'        #panjang nik kurang dari required 
        
    else :      
        if nextword == None:
            nikval = 'dummy'
        else:                #case langka
            nikdummy = nextword

            lennikdummy = len(nikdummy)
            if lennikdummy > 14:
                numcount =0
                ltrcount = 0
                symcount = 0
                for c in nikdummy :
                    if c.isdigit():
                        numcount+=1 
                    elif c.isalpha(): # Huruf
                        ltrcount += 1
                    else: # Karakter lain seperti simbol, spasi
                        symcount += 1
            
                if numcount>ltrcount and numcount>symcount:
                    if numcount == lennikdummy :
                        nikval = nikdummy+ ' misah'
                    else :
                        nikval = nikdummy + ' possibly'   #kotor means nik terkontaminasi karakter selain angka
                    
                else :                                       
                    nikval = nikdummy + ' possibly'      #angka menjadi karakter minoritas di nik, lebih kotor dari kondisi pertama
            else:
                nikval = nikdummy + ' dummy'        #panjang nik kurang dari required 

    return nikval


def validnama (nextword:str):
    with open(os.path.join(datasetdir, 'nama.txt'), "r", encoding="utf-8") as f:
        lines = f.readlines()

    listnama = [line.strip() for line in lines]

    match, score = process.extractOne(nextword,listnama)
    namaval = match

    return namaval + ' misah'




# def validttl(word, nextword=None):
    

#     if len(word)>21:
#         polattlfield = 
#     else:
    

#     numlist = r'[0OQoC1i!l\/I2Z3Eg4AH5S$fg6G7T8B&%9gqa]'
#     poladate = rf'({numlist}{{1,2}})[\s-]{{0,2}}({numlist}{{1,2}})[\s-]{{0,2}}({numlist}{{1,4}})'

#     match = re.search(poladate, nextword) # <--- Ganti ke re.search()


    




def validgender (word : str, nextword:str=None):
    gendervallist = ["LAKI-LAKI", "PEREMPUAN"]

    if len(word) > 14 :
        genderval, _ = process.extractOne(word, gendervallist)
        genderval += ' nyatu'
    else :  #case tidak umum
        if nextword == None:
            genderval = 'dummy'
        else:
            genderdummy = nextword
            match , score = process.extractOne(genderdummy, gendervallist)
            if match :
                if score>60 :
                    genderval = match + ' misah'
                else:   #misal ['provinsi jawa', 'timur']
                    genderval = match+' possibly'
            else :
                genderval = match + " dummy"
    return genderval


def validdarah(nextword):
    darahvallist = ['A', 'B', 'AB', 'O', '-']
    match, score = process.extractOne(nextword,darahvallist)
    if match:
        if score >50 :
            darahval = match + ' misah'
        else:
            darahval = match + ' possibly'
    else:
        darahval = match + " dummy"

    return darahval 


def validrtrw(nextword):
    polartrw = r'(?:rt/rw|rt rw|rtirw|rtrw|atirw|rt|rw|RTiRW|RT/RW|RTIRW|RTRW|.RW|.w)[\s:;./-]{0,4}' #asumsi pola umum pada 'nik : '
    #pemotongan nik pada word utk mengambil nik-nya saja
    cutrtrw = re.search(polartrw, nextword)
    print(cutrtrw)
    rtrwdummy = nextword[cutrtrw.end():]

    lenrtrwdummy = len(rtrwdummy)
    if lenrtrwdummy > 4:
        numcount =0
        ltrcount = 0
        symcount = 0
        for c in rtrwdummy :
            if c.isdigit():
                numcount+=1 
            elif c.isalpha(): # Huruf
                ltrcount += 1
            else: # Karakter lain seperti simbol, spasi
                symcount += 1
    
        if numcount>ltrcount and numcount>symcount:
            if numcount == lenrtrwdummy :
                rtrwval = rtrwdummy+ ' misah'
            else :
                rtrwval = rtrwdummy + ' possibly'   #kotor means nik terkontaminasi karakter selain angka
            
        else :                                       
            rtrwval = rtrwdummy + ' possibly'      #angka menjadi karakter minoritas di nik, lebih kotor dari kondisi pertama
    else:
        rtrwval = rtrwdummy + ' dummy'        #panjang nik kurang dari required 

    return rtrwval


# def validalamat (word: str):
def validkeldes  (nextword : str= None) -> str:
    listnamakel = list(kel_df['name'].values)

    keldummy = nextword
    match , score = process.extractOne(keldummy, listnamakel)
    if match :
        if score!=0 :
            kelval = match   + ' misah'
        else:   #misal ['provinsi jawa', 'timur']
            kelval = match+' possibly'
    else :
        kelval = match + " dummy"

    return kelval



# def validalamat (word: str):
def validkec  (word : str, nextword : str= None) -> str:
    listnamakec = list(kec_df['name'].values)
    if len(word) > 12 :
        kecval, _ = process.extractOne(word, listnamakec)
        kecval += ' nyatu'
    else :  #case tidak umum
        if nextword == None:
            kecval = 'dummy'
        else:
            kecdummy = nextword
            match , score = process.extractOne(kecdummy, listnamakec)
            if match :
                if score!=0 :
                    kecval = match  + ' misah'
                else:   #misal ['provinsi jawa', 'timur']
                    kecval = match+' possibly'
            else :
                kecval = match + " dummy"

    return kecval
    




def validagama (nextword):
    agamavallist = ["ISLAM", "KRISTEN", "KATOLIK", "HINDU", "BUDDHA", "KHONGHUCU"]

    match, score = process.extractOne(nextword,agamavallist )
    
    if match :
        print (match)
        if score > 60 :
            agamaval = match + ' misah'
        else :
            agamaval = match+" possibly"
    else : 
        agamaval = match+' dummy'

    return agamaval




def validkawin (word : str, nextword:str=None):
    kawinvallist = ["BELUM KAWIN",  "KAWIN",  "CERAI HIDUP", "CERAI MATI"]

    if len(word)>19:
        kawinval, _ = process.extractOne(word,kawinvallist )
        kawinval+=' nyatu'
    else:
        # kawindummy = nextword
        if nextword == None:
            kawinval = 'dummy'
        else:
            match, score = process.extractOne(nextword,kawinvallist )
            
            if match :
                print (match)
                if score > 60 :
                    kawinval = match + ' misah'
                else :
                    kawinval = match+" possibly"
            else : 
                kawinval = match + ' dummy'

    return kawinval


def validjob (nextword:str):
    with open(os.path.join(datasetdir, 'job.txt'), "r", encoding="utf-8") as f:
        lines = f.readlines()

    listjob = [line.strip() for line in lines]
    
    match, score = process.extractOne(nextword,listjob)

    if match :
        if score >40:
            jobval = match+ ' misah'
        else:
            jobval = match+' possibly'
    else:
        jobval= match+ ' dummy'

    return jobval 


def validwn (word : str, nextword:str=None):
    wnvallist = ["WNI", "WNA"]

    if len(word)>16:
        wnval, _ = process.extractOne(word,wnvallist )
        wnval+=' nyatu'
    else:
        # wndummy = nextword
        if nextword == None:
            wnval = 'dummy'
        else:
                
            match, score = process.extractOne(nextword,wnvallist )
            
            if match :
                print (match)
                if score > 60 :
                    wnval = match + ' misah'
                else :
                    wnval = match+" possibly"
            else : 
                wnval = match + ' dummy'

    return wnval


def validberlaku (nextword:str):
    berlakuvallist = ["SEUMUR HIDUP"]

    match, score = process.extractOne(nextword,berlakuvallist )

    if match :
        print (match)
        if score > 60 :
            berlakuval = match + ' misah'
        else :
            berlakuval = match+" possibly"
    else : 
        numlist= r'[0OQoC1i!l\/I2Z3Eg4AH5S$fg6G7T8B&%9gqa]'
        poladate = rf'({numlist}{{1,2}})[\s-]{{0,2}}({numlist}{{1,2}})[\s-]{{0,2}}({numlist}{{1,4}})'

        match = re.search(poladate, nextword) # <--- Ganti ke re.search()

        if match:
            if len(nextword) == 10:
                berlakuval = match.group(0) + ' misah'
            else:
                berlakuval = match.group(0) + ' possibly'
        else:
            berlakuval = 'dummy'

    return berlakuval