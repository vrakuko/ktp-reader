import 'dart:convert';
import 'dart:typed_data';
import 'dart:io'; // Perlu ditambahkan untuk `exit` jika kReleaseMode

import 'package:flutter/foundation.dart'; // Perlu ditambahkan untuk `kReleaseMode`
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:image_picker/image_picker.dart';
// import 'package:http_parser/http_parser.dart'; // Untuk MediaType, jika diperlukan, tapi 'image/jpeg' string sudah cukup

void main() {
  FlutterError.onError = (details) {
    FlutterError.presentError(details);
    if (kReleaseMode) exit(1);
  };
  runApp(const Vrapp());
}

class Vrapp extends StatelessWidget {
  const Vrapp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Vrapp',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: const Color.fromARGB(255, 0, 74, 211)),
      ),
      builder: (context, widget) {
        Widget error = const Text('...rendering error... mainkan lagu waifumu');
        if (widget is Scaffold || widget is Navigator) {
          error = Scaffold(body: Center(child: error));
        }
        ErrorWidget.builder = (errorDetails) => error;
        if (widget != null) return widget;
        throw StateError('widget is null, lanjut tambal ban');
      },
      home: const VrappPage(title: 'vrapp OCR KTP'),
    );
  }
}

class VrappPage extends StatefulWidget {
  const VrappPage({super.key, required this.title});

  final String title;

  @override
  State<VrappPage> createState() => _ImageInputScreenState();
}

class _ImageInputScreenState extends State<VrappPage> {
  Uint8List? _resImageBytes; // Gambar hasil (dengan bounding box)
  Uint8List? _selectedImageBytes; // Gambar yang dipilih
  bool _isLoading = false;
  String? _ktpDataFormatted; // Untuk data KTP yang diformat dari 'ktpdata'
  String? _arrKtpDataFormatted; // Untuk data 'arrktpdata'
  String? _carryOcrFormatted; // Untuk data 'carryocr'
  String? _errorMessage;

  // Fungsi untuk membuka galeri atau kamera
  Future<void> _pickImage(ImageSource source) async {
    final imagePicker = ImagePicker();
    final pickedImageFile = await imagePicker.pickImage(
      source: source,
      imageQuality: 100,
    );

    if (pickedImageFile == null) {
      return;
    }

    final imageBytes = await pickedImageFile.readAsBytes();
    setState(() {
      _resImageBytes = null; // Reset gambar hasil
      _selectedImageBytes = imageBytes;
      _ktpDataFormatted = null; // Reset hasil jika gambar baru dipilih
      _arrKtpDataFormatted = null;
      _carryOcrFormatted = null;
      _errorMessage = null;
    });
  }

  // FUNGSI UNTUK MENGIRIM GAMBAR KE PYTHON DAN MENGAMBIL HASIL
  Future<void> _sendImageToPython() async {
    if (_selectedImageBytes == null) {
      setState(() => _errorMessage = "Pilih gambar terlebih dahulu!");
      return;
    }

    setState(() {
      _isLoading = true;
      _errorMessage = null;
      _ktpDataFormatted = null;
      _arrKtpDataFormatted = null;
      _carryOcrFormatted = null;
      _resImageBytes = null; // Reset gambar hasil
    });

    final String baseUrl = "http://127.0.0.1:5000";
    final Uri urlKtpData = Uri.parse("$baseUrl/vratp/ocr/ktpdata");
    final Uri urlKtpImage = Uri.parse("$baseUrl/vratp/ocr/ktpimage");

    try {
      // --- LANGKAH 1: Mengirim gambar untuk OCR dan Ekstraksi Data ---
      var request = http.MultipartRequest('POST', urlKtpData);
      request.files.add(
        http.MultipartFile.fromBytes(
          'image', // 'image' adalah key yang harus sama dengan di server Python
          _selectedImageBytes!,
          filename: 'ktp_upload.jpg', // Nama file bebas
          // contentType: MediaType('image', 'jpeg'), // Uncomment jika perlu spesifik, tapi biasanya otomatis terdeteksi
        ),
      );

      final streamedResponse = await request.send();
      final response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode == 200) {
        final responseData = jsonDecode(response.body);

        setState(() {
          // --- Menganalisis dan menampilkan data KTP dari respons ---
          // Pastikan nama kunci ('arrktpdata', 'carryocr', 'ktpdata') sesuai dengan respons Python
          if (responseData.containsKey('arrktpdata') && responseData['arrktpdata'] != null) {
            _arrKtpDataFormatted = const JsonEncoder.withIndent('  ').convert(responseData['arrktpdata']);
          } else {
            _arrKtpDataFormatted = "Tidak ada 'arrktpdata' yang ditemukan.";
          }

          if (responseData.containsKey('carryocr') && responseData['carryocr'] != null) {
            _carryOcrFormatted = const JsonEncoder.withIndent('  ').convert(responseData['carryocr']);
          } else {
            _carryOcrFormatted = "Tidak ada 'carryocr' yang ditemukan.";
          }
          
          if (responseData.containsKey('ktpdata') && responseData['ktpdata'] != null) {
            _ktpDataFormatted = const JsonEncoder.withIndent('  ').convert(responseData['ktpdata']);
          } else {
            _ktpDataFormatted = "Tidak ada 'ktpdata' yang ditemukan.";
          }
        });

        // --- LANGKAH 2: Mengambil gambar dengan bounding box ---
        final imageResponse = await http.get(urlKtpImage);

        if (imageResponse.statusCode == 200) {
          setState(() {
            _resImageBytes = imageResponse.bodyBytes; // Ambil bytes gambar
            print("Gambar bounding box berhasil diterima!");
          });
        } else {
          setState(() {
            _errorMessage = "Error mengambil gambar bounding box: ${imageResponse.statusCode}\n${imageResponse.body}";
          });
          print("Error mengambil gambar bounding box: ${imageResponse.statusCode}\n${imageResponse.body}");
        }

      } else {
        setState(() {
          _errorMessage = "Error dari server (data): ${response.statusCode}\n${response.body}";
        });
        print("Error dari server (data): ${response.statusCode}\n${response.body}");
      }
    } catch (e) {
      setState(() {
        _errorMessage = "Tidak dapat terhubung ke server: $e";
      });
      print("Exception: $e");
    } finally {
      setState(() {
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        backgroundColor: const Color.fromARGB(255, 6, 136, 217),
        titleTextStyle: const TextStyle(
          color: Colors.white,
          fontSize: 22,
          fontWeight: FontWeight.bold,
          fontFamily: 'Roboto',
          letterSpacing: 1.2,
        ),
        title: const Text('OCR KTP'),
        iconTheme: const IconThemeData(
          color: Colors.white,
        ),
      ),
      body: LayoutBuilder(
        builder: (BuildContext context, BoxConstraints constraints) {
          // Layout untuk layar lebar (misal: tablet, desktop)
          if (constraints.maxWidth > 600) {
            return Center(
              child: SingleChildScrollView(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                      children: [
                        _buildImageContainer(_selectedImageBytes, 'Gambar Dipilih'),
                        _buildImageContainer(_resImageBytes, 'Gambar Hasil'),
                      ],
                    ),
                    const SizedBox(height: 20),
                    _buildImagePickButtons(),
                    const SizedBox(height: 20),
                    ElevatedButton.icon(
                      icon: const Icon(Icons.send),
                      label: const Text('Kirim ke Python'),
                      onPressed: _isLoading ? null : _sendImageToPython,
                    ),
                    const SizedBox(height: 20),
                    if (_isLoading) const CircularProgressIndicator(),
                    if (_errorMessage != null)
                      Text(_errorMessage!, style: const TextStyle(color: Colors.red)),
                    const SizedBox(height: 20),
                    if (_arrKtpDataFormatted != null || _carryOcrFormatted != null || _ktpDataFormatted != null)
                      Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                _buildResultBox("arrKtpData:", _arrKtpDataFormatted),
                                const SizedBox(height: 12),
                                _buildResultBox("carryOcr:", _carryOcrFormatted),
                              ],
                            ),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: _buildResultBox("ktpData:", _ktpDataFormatted),
                          ),
                        ],
                      ),
                  ],
                ),
              ),
            );
          } else {
            // Layout untuk layar kecil (misal: ponsel)
            return Center(
              child: SingleChildScrollView(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    _buildImageContainer(_selectedImageBytes, 'Gambar Dipilih'),
                    const SizedBox(height: 20),
                    _buildImageContainer(_resImageBytes, 'Gambar Hasil'),
                    const SizedBox(height: 20),
                    _buildImagePickButtons(),
                    const SizedBox(height: 20),
                    ElevatedButton.icon(
                      icon: const Icon(Icons.send),
                      label: const Text('Kirim ke Python'),
                      onPressed: _isLoading ? null : _sendImageToPython,
                    ),
                    const SizedBox(height: 20),
                    if (_isLoading) const CircularProgressIndicator(),
                    if (_errorMessage != null)
                      Text(_errorMessage!, style: const TextStyle(color: Colors.red)),
                    const SizedBox(height: 20),
                    if (_arrKtpDataFormatted != null || _carryOcrFormatted != null || _ktpDataFormatted != null)
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          _buildResultBox("arrKtpData:", _arrKtpDataFormatted),
                          const SizedBox(height: 12),
                          _buildResultBox("carryOcr:", _carryOcrFormatted),
                          const SizedBox(height: 12),
                          _buildResultBox("ktpData:", _ktpDataFormatted),
                        ],
                      ),
                  ],
                ),
              ),
            );
          }
        },
      ),
    );
  }

  // Helper widget untuk membuat container gambar
  Widget _buildImageContainer(Uint8List? imageBytes, String placeholderText) {
    return Container(
      width: 200,
      height: 300,
      decoration: BoxDecoration(
        border: Border.all(width: 1, color: Colors.grey),
        borderRadius: BorderRadius.circular(8),
      ),
      alignment: Alignment.center,
      child: imageBytes != null
          ? Image.memory(
              imageBytes,
              fit: BoxFit.contain, // Gunakan BoxFit.contain agar gambar tidak terpotong
              width: double.infinity,
              height: double.infinity,
            )
          : Text(
              placeholderText,
              textAlign: TextAlign.center,
              style: TextStyle(color: Colors.grey[600]),
            ),
    );
  }

  // Helper widget untuk tombol pilih gambar
  Widget _buildImagePickButtons() {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceEvenly,
      children: [
        TextButton.icon(
          icon: const Icon(Icons.camera),
          label: const Text('Kamera'),
          onPressed: () => _pickImage(ImageSource.camera),
        ),
        TextButton.icon(
          icon: const Icon(Icons.image),
          label: const Text('Galeri'),
          onPressed: () => _pickImage(ImageSource.gallery),
        ),
      ],
    );
  }

  // Helper widget untuk menampilkan hasil teks
  Widget _buildResultBox(String title, String? content) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.grey.shade200,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: const TextStyle(fontWeight: FontWeight.bold)),
          const SizedBox(height: 4),
          SelectableText(content ?? "Tidak ada data.", style: const TextStyle(fontFamily: 'monospace')),
        ],
      ),
    );
  }
}