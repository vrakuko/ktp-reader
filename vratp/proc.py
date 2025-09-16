

import easyocr
import numpy as np
import json
import zipfile
import os
# from paddleocr import PaddleOCR
import app
from prep import process_img
import cv2




# Upload gambar
# print("Silakan pilih 5 (atau lebih) file gambar untuk di-upload:")
# uploaded = files.upload()
# if not uploaded:
#     print("Tidak ada file yang di-upload.")



# # # # Load model PaddleOCR
# # # preader = PaddleOCR(use_angle_cls=True, lang='ind')




def imgocr (image_bytes) :



    imgori = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)  

    
    #Load model EasyOCR
    ereader = easyocr.Reader(['id'], gpu=False)



    ### EasyOCR
    reseasy = ereader.readtext(imgori)
    outeasy = {}
    confeasy = []
    for (_, txt, confs) in reseasy:
        outeasy[txt] = confs
        confeasy.append(confs)
    outeasy['avgconfscore'] = float(np.mean(confeasy)) if confeasy else 0.0

    ### PaddleOCR
    # respaddle = preader.ocr(imgproc, cls=True)
    # outpaddle = {}
    # confpaddle = []
    # for line in respaddle[0]:
    #     txt, confs = line[1][0], line[1][1]
    #     outpaddle[txt] = float(confs)
    #     confpaddle.append(confs)
    # outpaddle['avgconfscore'] = float(np.mean(confpaddle)) if confpaddle else 0.0

    return outeasy




#sesi test


# uploaded = app.uploaded
# uploaded = "D:\dataset\kowareta\ktp1.jpg"

# img_name = os.path.splitext(uploaded)[0]

# print(img_name)

# jsonpromised = imgocr (uploaded)
# print(jsonpromised)