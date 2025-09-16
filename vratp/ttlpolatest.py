import re

toleransichar = {
    't': r'(?:t|T|7|l|i|I|1|J)',
    'e': r'(?:e|E|3|c|C|g|G|6)',
    'm': r'(?:m|M|n|N)',
    'p': r'(?:p|P)',
    'a': r'(?:a|A|4|H)',
    'g': r'(?:g|G|9|6)',
    'n': r'(?:n|N|m|M)',
    'l': r'(?:l|L|1|I)',
    'h': r'(?:h|H|4)',
    'i': r'(?:i|I|1|l|L)',
    'r': r'(?:r|R|B)',
    'o': r'(?:o|O|0)',
    'q': r'(?:q|Q)',
}
separator = r'[\s:;.\-_]?'

# ====================================================================
# Pola Fuzzy untuk Kata Kunci "TEMPAT" atau "TGL"
# ====================================================================

polatempat = (
    r'(?:'
    + rf'(?:{toleransichar["t"]}{separator})?'
    + rf'(?:{toleransichar["e"]}{separator})?'
    + rf'(?:{toleransichar["m"]}{separator})?'
    + rf'(?:{toleransichar["p"]}{separator})?'
    + rf'(?:{toleransichar["a"]}{separator})?'
    + rf'(?:{toleransichar["t"]}{separator})?'
    + rf'(?:{toleransichar["o"]}{separator})?'
    + rf'(?:{toleransichar["q"]}{separator})?'
    + r')'
    + r'[\s:;.\-_]{0,5}' # Minimal satu pemisah
)

polatgl = (
    r'(?:'
    + rf'{toleransichar["t"]}{separator}?'
    + rf'{toleransichar["g"]}{separator}?'
    + rf'{toleransichar["l"]}{separator}?'
    + r')'
    + r'[\s:;.\-_]{0,5}'
)

polalahir = (
    r'(?:'
    + rf'{toleransichar["l"]}{separator}?'
    + rf'{toleransichar["a"]}{separator}?'
    + rf'{toleransichar["h"]}{separator}?'
    + rf'{toleransichar["i"]}{separator}?'
    + rf'{toleransichar["r"]}{separator}?'
    + r')'
    + r'[\s:;.\-_]{0,5}'
)

# ====================================================================
# Bagian 1: Tempat Lahir (kota/kabupaten)
# ====================================================================
# Ini harus lebih spesifik daripada .*, agar tidak terlalu greedy.
# Mengizinkan huruf, angka, spasi, titik, koma, dash
# dan juga beberapa karakter fuzzy yang bisa menjadi bagian dari nama tempat
# seperti 'evbe' -> 'JevbEr'
tempat_char_class = r'[A-Za-z0-9.,\s\-_' \
                    + re.escape(''.join(re.findall(r'[a-zA-Z0-9]', ''.join(toleransichar.values())))) \
                    + r']' # Semua karakter toleransi juga bisa jadi bagian tempat lahir

# Mengambil semua karakter fuzzy yang mungkin menjadi digit
# Ini adalah perbaikan untuk 'numlist'
fuzzy_digit_char_class = r'[0OQoC1i!l/I2Z3Eg4AH5S$fg6G7T8B&%9gqa]'

# Pola untuk tempat lahir: sebuah capturing group
# Minimal 2 karakter, maksimal 50
polatempatlahir = rf'({tempat_char_class}{{2,50}}?)' # Capturing group 1: non-greedy


# ====================================================================
# Bagian 2: Pemisah antara Tempat dan Tanggal
# ====================================================================
pemisah = r'[\s,.:;-]{1,5}?'


# ====================================================================
# Bagian 3: Tanggal Lahir (DD-MM-YYYY)
# ====================================================================

# Perbaikan poladate:
# Gunakan fuzzy_digit_char_class sebagai character class, bukan string dengan non-capturing group.
poladate = (
    r'(' # Buka capturing group untuk seluruh tanggal (misalnya '01-01-1990')
    + rf'(?:{fuzzy_digit_char_class}{{1,2}})' # Hari (1-2 fuzzy digit)
    + r'[\s\-/.]?' # Pemisah hari-bulan
    + rf'(?:{fuzzy_digit_char_class}{{1,2}})' # Bulan (1-2 fuzzy digit)
    + r'[\s\-/.]?' # Pemisah bulan-tahun
    + rf'(?:{fuzzy_digit_char_class}{{4}})' # Tahun (4 fuzzy digit)
    + r')' # Tutup capturing group untuk seluruh tanggal
)

# ====================================================================
# Gabungkan semua untuk polattlfield_normal
# ====================================================================
polattlfield_normal = (
    r'(?:' + polatempat + r'|' + polatgl + polalahir + r')?' # Awalan fuzzy opsional
    + polatempatlahir # Bagian Tempat Lahir (capturing group 1)
    + pemisah # Pemisah
    + poladate # Bagian Tanggal Lahir (capturing group 2)
)

# ====================================================================
# Contoh Penggunaan
# ====================================================================
if __name__ == "__main__":
    test_strings = [
        'SEMARANG, 01-01-1990',
        'JEMBER. 17-04-1999',
        'Topatiqi Lahi JevbEr. 17-04-1999', # Dari OCR Anda
        'Tempa tgl lahir JAKARTA, 25/12/2000',
        'BANDUNG 10-06-1985',
        'Bekasi. 05 03 1992',
        'Medan 12 Mei 1978', # 'Mei' tidak akan cocok dengan pola tanggal numerik fuzzy ini.
                              # Jika ingin tangkap bulan nama, butuh perubahan di poladate.
        'SURABAYA, 31.01.2001',
        'NO_MATCH_HERE',
        'Tempat/Tgl Lahir : SOLO, 02-02-1980',
        'TMPT/TGL LHR: BOGOR, 15-09-1995',
        'Lahir di Yogya 20-10-1990', # Masih belum cocok karena tidak ada pemisah jelas
        'JevbEr. 17-04-1999', # Contoh tempat lahir sendiri
    ]

    print(f"Pola Regex 'Agak Normal' untuk Tempat, Tanggal Lahir:\n{polattlfield_normal}\n")

    for text in test_strings:
        match = re.search(polattlfield_normal, text, re.IGNORECASE)

        if match:
            # group(1) adalah Tempat Lahir
            # group(2) adalah seluruh Tanggal (misal '01-01-1990')
            tempat_lahir = match.group(1).strip()
            tanggal_lengkap = match.group(2)
            
            # Anda perlu parsing tanggal_lengkap ini lebih lanjut jika ingin hari, bulan, tahun terpisah.
            # Contoh sederhana untuk memisahkan (akan lebih baik dengan regex terpisah atau datetime.strptime)
            parts = re.split(r'[\s\-/.]', tanggal_lengkap)
            hari, bulan, tahun = '', '', ''
            if len(parts) == 3:
                hari, bulan, tahun = parts
            
            print(f"✔️ '{text}' COCOK:")
            print(f"   Tempat Lahir: '{tempat_lahir}'")
            print(f"   Tanggal Lengkap: '{tanggal_lengkap}'")
            # print(f"   Hari: '{hari}', Bulan: '{bulan}', Tahun: '{tahun}'") # Hanya jika parsing berhasil
        else:
            print(f"❌ '{text}' TIDAK COCOK")