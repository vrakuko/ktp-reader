import streamlit as st
import easyocr
import numpy as np
import json
import zipfile
import os
import cv2
import matplotlib.pyplot as plt
from prep import process_img, display_img
from proc import ereader, imgocr
from postproc import ktp_fields, recchar,txthasilocr, extrocr

# ---------------------------
# Load OCR model
# ---------------------------
ereader = easyocr.Reader(['id'], gpu=False)

# ---------------------------
# Fungsi process_img
# ---------------------------
def process_img(image_bytes, image_name):
    imgori = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
    imgorirgb = cv2.cvtColor(imgori, cv2.COLOR_BGR2RGB)
    imggray = cv2.cvtColor(imgorirgb, cv2.COLOR_RGB2GRAY)
    imginvert = cv2.bitwise_not(imggray)
    _, bin_img = cv2.threshold(imginvert, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    noise_removed = cv2.medianBlur(bin_img, 3)

    rgba_img = cv2.cvtColor(noise_removed, cv2.COLOR_GRAY2RGBA)
    rgba_img[:, :, 3] = np.where(noise_removed == 0, 0, 255)

    image_name = os.path.splitext(image_name)[0]

    listimg = [imgori, imgorirgb, imggray, imginvert, bin_img, noise_removed, rgba_img]
    listimgname = [
        f'imgori {image_name}', f'imgorirgb {image_name}', f'imggray {image_name}',
        f'imginvert {image_name}', f'bin_img {image_name}',
        f'noise_removed {image_name}', f'rgba_img {image_name}'
    ]
    return listimg, listimgname

# ---------------------------
# Fungsi OCR (EasyOCR)
# ---------------------------
def run_easyocr(img, imgname, outdir):
    reseasy = ereader.readtext(img)
    outeasy = {}
    confeasy = []
    
    for (_, txt, confs) in reseasy:
        outeasy[txt] = confs
        confeasy.append(confs)
    outeasy['avgconfscore'] = float(np.mean(confeasy)) if confeasy else 0.0

    resjson_easy = os.path.join(outdir, f"{imgname}_easyocr.json")
    with open(resjson_easy, 'w', encoding='utf-8') as f:
        json.dump(outeasy, f, indent=4, ensure_ascii=False)

# ---------------------------
# Streamlit UI
# ---------------------------
st.set_page_config(page_title="OCR TEST")
st.title("KTP READER")

uploaded = st.file_uploader(
    "Pilih file gambar...",
    type=["png", "jpg", "jpeg"],
    accept_multiple_files=True
)

if uploaded:
    st.success(f"{len(uploaded)} file berhasil di-upload ✅")

    if st.button("Process gambar"):
        for uploaded_file in uploaded:
            nama_file = uploaded_file.name
            konten_bytes = uploaded_file.getvalue()

            # Proses gambar
            list_img, list_imgname = process_img(konten_bytes, nama_file)

            # Buat folder output
            img_name = os.path.splitext(nama_file)[0]
            fotoproc = f'fotoproc_{img_name}'
            resocr = f'resocr_{img_name}'
            os.makedirs(fotoproc, exist_ok=True)
            os.makedirs(resocr, exist_ok=True)

            # Simpan hasil processing
            for imgproc, imgname in zip(list_img, list_imgname):
                imgpath = os.path.join(fotoproc, f"{imgname}.png")
                cv2.imwrite(imgpath, imgproc)

                # OCR EasyOCR
                run_easyocr(imgproc, imgname, resocr)

            # Zip folder hasil
            fotoproc_zip = f'{fotoproc}.zip'
            resocr_zip = f'{resocr}.zip'

            with zipfile.ZipFile(fotoproc_zip, 'w') as f:
                for file in os.listdir(fotoproc):
                    f.write(os.path.join(fotoproc, file), arcname=file)

            with zipfile.ZipFile(resocr_zip, 'w') as f:
                for file in os.listdir(resocr):
                    f.write(os.path.join(resocr, file), arcname=file)

            # Tampilkan hasil
            st.subheader(f"Hasil untuk {nama_file}")
            st.image(list_img[0], caption=list_imgname[0])  # tampilkan gambar ori
            st.image(list_img[4], caption=list_imgname[4])  # tampilkan hasil binarisasi

            with open(resocr_zip, "rb") as f:
                st.download_button(
                    label=f"Download OCR JSON {nama_file}",
                    data=f,
                    file_name=resocr_zip,
                    mime="application/zip"
                )

            with open(fotoproc_zip, "rb") as f:
                st.download_button(
                    label=f"Download Hasil Processing {nama_file}",
                    data=f,
                    file_name=fotoproc_zip,
                    mime="application/zip"
                )
