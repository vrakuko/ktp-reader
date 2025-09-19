import cv2
import matplotlib.pyplot as plt
import numpy as np
import os
from flask import Flask, request,  jsonify

def process_img(image_bytes, image_name):
  #Img ori dan versi rgb (versi ori formatnya bgr)
  imgori = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
  imgorirgb = cv2.cvtColor(imgori, cv2.COLOR_BGR2RGB)

  #gray
  imggray = cv2.cvtColor(imgorirgb, cv2.COLOR_RGB2GRAY)

  #  Inverted Image
  imginvert = cv2.bitwise_not(imggray)

  #  Binarization (Otsu)
  _, bin_img = cv2.threshold(imginvert, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

  #  Noise Removal (Median Blur)
  noise_removed = cv2.medianBlur(bin_img, 3)


  #  Transparency (latar belakang hitam menjadi transparan)

  # Konversi ke format RGBA
  rgba_img = cv2.cvtColor(noise_removed, cv2.COLOR_GRAY2RGBA)
  # Atur channel alpha: di mana piksel hitam (nilai 0), alpha menjadi 0 (transparan)
  rgba_img[:, :, 3] = np.where(noise_removed == 0, 0, 255)

  #set variabel untuk mempersimpel pemahaman return
  image_name = os.path.splitext(image_name)[0]

  listimg = [imgori, imgorirgb, imggray, imginvert, bin_img, noise_removed, rgba_img]
  listimgname = [f'imgori {image_name}', f'imgorirgb {image_name}', f'imggray {image_name}', f'imginvert {image_name}', f'bin_img {image_name}', f'noise_removed {image_name}', f'rgba_img {image_name}']


  return listimg, listimgname




# def display_img(image_name, image_bytes) :
#     #produce image yg akan ditampilkan beserta namanya
#     resproc = process_img(image_bytes, image_name)

#     listimg = resproc[0]
#     listimgname = resproc[1]

#     plt.figure(figsize=(15, 15))

#     #loop over semua gambar proses
#     for i in range(len(listimg)):
#         plt.subplot(3, 3, i + 1)
#         if i >= 2:
#             plt.imshow(listimg[i], cmap='gray')
#         else:
#             plt.imshow(listimg[i])

#         plt.title(listimgname[i])
#         plt.axis('off')

#     plt.show()



