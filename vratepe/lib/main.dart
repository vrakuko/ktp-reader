import 'dart:convert';
import 'dart:typed_data';
import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:image_picker/image_picker.dart';

void main() {
  FlutterError.onError = (details) {
  FlutterError.presentError(details);
    if (kReleaseMode) exit(1);
  };
  runApp(const Vrapp());
}

class Vrapp extends StatelessWidget {
  const Vrapp({super.key});

  // This widget is the root of your application.
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

  // This widget is the home page of your application. It is stateful, meaning
  // that it has a State object (defined below) that contains fields that affect
  // how it looks.

  // This class is the configuration for the state. It holds the values (in this
  // case the title) provided by the parent (in this case the App widget) and
  // used by the build method of the State. Fields in a Widget subclass are
  // always marked "final".

  final String title;

  @override
  State<VrappPage> createState() => _ImageInputScreenState();
}



class _ImageInputScreenState extends State<VrappPage> {
  // Variabel untuk menyimpan file gambar yang dipilih.
  // Nullable (?) karena awalnya belum ada gambar yang dipilih.
  Uint8List? _selectedImageBytes;
  bool _isLoading = false;
  String? _ktpData;
  String? _errorMessage;
  String? _ocrResult;

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

    // PERUBAHAN 3: Baca file sebagai bytes dan update state
    final imageBytes = await pickedImageFile.readAsBytes();
    setState(() {
      _selectedImageBytes = imageBytes;
      _ktpData = null; // Reset hasil jika gambar baru dipilih
      _errorMessage = null;
      _ocrResult = null;
    });
  }


    // FUNGSI BARU UNTUK MENGIRIM GAMBAR KE PYTHON
  Future<void> _sendImageToPython() async {
    if (_selectedImageBytes == null) {
      setState(() => _errorMessage = "Pilih gambar terlebih dahulu!");
      return;
    }

    setState(() {
      _isLoading = true;
      _errorMessage = null;
      _ktpData = null;
      _ocrResult = null;
    });

    // PENTING: Ganti URL ini dengan alamat IP komputer Anda
    // final url = Uri.parse("http://192.168.56.1:5000/ocr/ktp");
  // Future<http.Response> fetchHasil() {
  //   return http.get(Uri.parse('https://c2661b060809.ngrok-free.app/ '));
  // }
   final url = Uri.parse("http://10.100.0.168:5000/ocr/ktp");

    try {
      // Membuat multipart request
      var request = http.MultipartRequest('POST', url);

      // Menambahkan file gambar dari bytes
      request.files.add(
        http.MultipartFile.fromBytes(
          'image', // 'image' adalah key yang harus sama dengan di server Python
          _selectedImageBytes!,
          filename: 'nukitashi.png', // Nama file bebas
        ),
      );

      // Mengirim request dan menunggu respons
      final streamedResponse = await request.send();
      final response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode == 200) {
        // Jika berhasil, decode JSON dan tampilkan datanya
        final responseData = jsonDecode(response.body);
        setState(() {
          // Tampilkan hasil data dalam format yang mudah dibaca
          
          _ktpData = const JsonEncoder.withIndent('  ').convert(responseData['data'][0]);
          _ocrResult = const JsonEncoder.withIndent('  ').convert(responseData['data'][1]);
          // _ktpData = encodePreserveOrder(responseData['data']);
        });
      } else {
        setState(() {
          _errorMessage = "Error dari server: ${response.statusCode}\n${response.body}";
        });
      }
    } 

    catch (e) {
      setState(() {
        _errorMessage = "Tidak dapat terhubung ke server: $e";
      });
    } 
    
    finally {
      setState(() {
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {


    return Scaffold(
      appBar: AppBar(
          backgroundColor: const Color.fromARGB(255, 6, 136, 217), // Contoh: warna biru indigo

          // 2. Mengatur style untuk tulisan title
          titleTextStyle: const TextStyle(
            color: Colors.white,            // Warna tulisan
            fontSize: 22,                   // Ukuran font
            fontWeight: FontWeight.bold,    // Ketebalan tulisan (misal: tebal)
            fontFamily: 'Roboto',           // (Opsional) Menggunakan font custom
            letterSpacing: 1.2,             // (Opsional) Jarak antar huruf
          ),
          
          // Title Anda tetap sama
          title: const Text('OCR KTP'),

          // (Opsional) Mengatur warna ikon (seperti tombol back) agar kontras
          iconTheme: const IconThemeData(
            color: Colors.white,
          ),
      
      ),


      body:LayoutBuilder(
        builder : (BuildContext context, BoxConstraints constraints){

          if (constraints.maxWidth > 600){
              return Center(
                child : SingleChildScrollView(

                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    //Widget untuk menampilkan gambar yang dipilih
                    Container(
                      width: 200,
                      height: 300,
                      decoration: BoxDecoration(
                        border: Border.all(width: 1, color: Colors.grey),
                      ),
                      alignment: Alignment.topLeft,
                      child: _selectedImageBytes != null
                          ? Image.memory(
                              _selectedImageBytes!,
                              fit: BoxFit.cover,
                              width: double.infinity,
                            )
                          : const Text(
                              'Belum ada gambar dipilih',
                              textAlign: TextAlign.center,
                            ),
                    ),

                    const SizedBox(height: 20),
                    // Tombol untuk memilih gambar
                    Row(
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
                    ),

                    const SizedBox(height: 20),

                    // TextButton.icon(onPressed: () => , label: const Text ('Get OCR Result'))
                    ElevatedButton.icon(                
                        icon: const Icon(Icons.send),
                        label: const Text('Kirim ke Python'),
                        onPressed: _isLoading ? null : _sendImageToPython
                    ),


                    const SizedBox(height: 20),

                    if(_isLoading) const CircularProgressIndicator(),

                    if(_errorMessage!=null) Text(_errorMessage!, style: const TextStyle(color : Colors.red)),

                    if (_ktpData != null)
                      Row(
                        crossAxisAlignment: CrossAxisAlignment.start, // Agar box rata atas
                        children : [

                          Expanded(
                            child : Container(
                              padding: const EdgeInsets.all(12),
                              decoration: BoxDecoration(
                                color: Colors.grey.shade200,
                                borderRadius: BorderRadius.circular(8),
                              ),
                              child: SelectableText("Hasil OCR:\n$_ocrResult", style: const TextStyle(fontFamily: 'monospace')),
                            ),
                          ),  

                          const SizedBox(width: 12),

                          Expanded(
                            child : Container(
                              padding: const EdgeInsets.all(12),
                              decoration: BoxDecoration(
                                color: Colors.grey.shade200,
                                borderRadius: BorderRadius.circular(8),
                              ),
                              child: SelectableText("Data KTP:\n$_ktpData", style: const TextStyle(fontFamily: 'monospace')),
                            ),
                          ),  
                          
                        ]
                      )
                  ],
                ),
                ),
              );

          }
          else{ //untuk hp
              return Center(
                child : SingleChildScrollView(

                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    //Widget untuk menampilkan gambar yang dipilih
                    Container(
                      width: 200,
                      height: 300,
                      decoration: BoxDecoration(
                        border: Border.all(width: 1, color: Colors.grey),
                      ),
                      alignment: Alignment.topLeft,
                      child: _selectedImageBytes != null
                          ? Image.memory(
                              _selectedImageBytes!,
                              fit: BoxFit.cover,
                              width: double.infinity,
                            )
                          : const Text(
                              'Belum ada gambar dipilih',
                              textAlign: TextAlign.center,
                            ),
                    ),

                    const SizedBox(height: 20),
                    // Tombol untuk memilih gambar
                    Row(
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
                    ),

                    const SizedBox(height: 20),

                    // TextButton.icon(onPressed: () => , label: const Text ('Get OCR Result'))
                    ElevatedButton.icon(                
                        icon: const Icon(Icons.send),
                        label: const Text('Kirim ke Python'),
                        onPressed: _isLoading ? null : _sendImageToPython
                    ),


                    const SizedBox(height: 20),

                    if(_isLoading) const CircularProgressIndicator(),

                    if(_errorMessage!=null) Text(_errorMessage!, style: const TextStyle(color : Colors.red)),

                    if (_ktpData != null)
                      Row(
                        crossAxisAlignment: CrossAxisAlignment.start, // Agar box rata atas
                        children : [

                          Expanded(
                            child : Container(
                              padding: const EdgeInsets.all(12),
                              decoration: BoxDecoration(
                                color: Colors.grey.shade200,
                                borderRadius: BorderRadius.circular(8),
                              ),
                              child: SelectableText("Hasil OCR:\n$_ocrResult", style: const TextStyle(fontFamily: 'monospace')),
                            ),
                          ),  

                          const SizedBox(width: 12),

                          Expanded(
                            child : Container(
                              padding: const EdgeInsets.all(12),
                              decoration: BoxDecoration(
                                color: Colors.grey.shade200,
                                borderRadius: BorderRadius.circular(8),
                              ),
                              child: SelectableText("Data KTP:\n$_ktpData", style: const TextStyle(fontFamily: 'monospace')),
                            ),
                          ),  
                          
                        ]
                      )
                  ],
                ),
                ),
              );

          }
          // throw '';

        }

      ) 
      
    );
  }
}















































// class _MyHomePageState extends State<MyHomePage> {
//   int _counter = 0;

//   void _incrementCounter() {
//     setState(() {
//       // This call to setState tells the Flutter framework that something has
//       // changed in this State, which causes it to rerun the build method below
//       // so that the display can reflect the updated values. If we changed
//       // _counter without calling setState(), then the build method would not be
//       // called again, and so nothing would appear to happen.
//       _counter++;
//     });
//   }

//   @override
//   Widget build(BuildContext context) {
//     // This method is rerun every time setState is called, for instance as done
//     // by the _incrementCounter method above.
//     //
//     // The Flutter framework has been optimized to make rerunning build methods
//     // fast, so that you can just rebuild anything that needs updating rather
//     // than having to individually change instances of widgets.
//     return Scaffold(
//       appBar: AppBar(
//         // TRY THIS: Try changing the color here to a specific color (to
//         // Colors.amber, perhaps?) and trigger a hot reload to see the AppBar
//         // change color while the other colors stay the same.
//         backgroundColor: Theme.of(context).colorScheme.inversePrimary,
//         // Here we take the value from the MyHomePage object that was created by
//         // the App.build method, and use it to set our appbar title.
//         title: Text(widget.title),
//       ),
//       body: Center(
//         // Center is a layout widget. It takes a single child and positions it
//         // in the middle of the parent.
//         child: Column(
//           // Column is also a layout widget. It takes a list of children and
//           // arranges them vertically. By default, it sizes itself to fit its
//           // children horizontally, and tries to be as tall as its parent.
//           //
//           // Column has various properties to control how it sizes itself and
//           // how it positions its children. Here we use mainAxisAlignment to
//           // center the children vertically; the main axis here is the vertical
//           // axis because Columns are vertical (the cross axis would be
//           // horizontal).
//           //
//           // TRY THIS: Invoke "debug painting" (choose the "Toggle Debug Paint"
//           // action in the IDE, or press "p" in the console), to see the
//           // wireframe for each widget.
//           mainAxisAlignment: MainAxisAlignment.center,
//           children: <Widget>[
//             const Text('You have pushed the button this many times:'),
//             Text(
//               '$_counter',
//               style: Theme.of(context).textTheme.headlineMedium,
//             ),
//           ],
//         ),
//       ),
//       floatingActionButton: FloatingActionButton(
//         onPressed: _incrementCounter,
//         tooltip: 'Increment',
//         child: const Icon(Icons.add),
//       ), // This trailing comma makes auto-formatting nicer for build methods.
//     );
//   }
// }
