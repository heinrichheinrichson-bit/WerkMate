import 'dart:io';

import 'package:flutter/material.dart';
import 'package:google_mlkit_text_recognition/google_mlkit_text_recognition.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import 'package:path_provider/path_provider.dart';

class CardScannerResult {
  const CardScannerResult({required this.qrValue, required this.printedText});

  final String qrValue;
  final String printedText;
}

class CardScannerPage extends StatefulWidget {
  const CardScannerPage({super.key});

  @override
  State<CardScannerPage> createState() => _CardScannerPageState();
}

class _CardScannerPageState extends State<CardScannerPage> {
  final controller = MobileScannerController(
    cameraResolution: const Size(1920, 1080),
    detectionSpeed: DetectionSpeed.unrestricted,
    formats: const [BarcodeFormat.qrCode],
    returnImage: true,
  );
  bool recognizingText = false;
  String? qrValue;
  List<int>? latestImage;

  void detected(BarcodeCapture capture) {
    if (recognizingText) return;
    final raw = capture.barcodes
        .map((barcode) => barcode.rawValue?.trim())
        .whereType<String>()
        .where((value) => value.isNotEmpty)
        .firstOrNull;
    if (raw == null) return;
    latestImage = capture.image ?? latestImage;
    if (qrValue != raw && mounted) setState(() => qrValue = raw);
  }

  Future<void> captureCard() async {
    final raw = qrValue;
    final image = latestImage;
    if (raw == null || image == null || recognizingText) return;
    setState(() => recognizingText = true);
    await controller.stop();
    final printedText = await recognizePrintedText(image);
    if (mounted) {
      Navigator.pop(
        context,
        CardScannerResult(qrValue: raw, printedText: printedText),
      );
    }
  }

  Future<String> recognizePrintedText(List<int>? bytes) async {
    if (bytes == null || bytes.isEmpty) return '';
    File? temporaryImage;
    final recognizer = TextRecognizer(script: TextRecognitionScript.latin);
    try {
      final directory = await getTemporaryDirectory();
      temporaryImage = File(
        '${directory.path}${Platform.pathSeparator}werkmate-card-${DateTime.now().microsecondsSinceEpoch}.jpg',
      );
      await temporaryImage.writeAsBytes(bytes, flush: true);
      final text = await recognizer.processImage(
        InputImage.fromFile(temporaryImage),
      );
      return text.text.trim();
    } catch (_) {
      return '';
    } finally {
      await recognizer.close();
      if (temporaryImage != null && await temporaryImage.exists()) {
        await temporaryImage.delete();
      }
    }
  }

  @override
  void dispose() {
    controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    backgroundColor: Colors.black,
    appBar: AppBar(
      backgroundColor: Colors.black,
      foregroundColor: Colors.white,
      title: const Text('Auftragskarte scannen'),
      actions: [
        IconButton(
          tooltip: 'Licht ein- oder ausschalten',
          onPressed: controller.toggleTorch,
          icon: const Icon(Icons.flashlight_on_outlined),
        ),
      ],
    ),
    body: Stack(
      fit: StackFit.expand,
      children: [
        MobileScanner(controller: controller, onDetect: detected),
        IgnorePointer(
          child: Center(
            child: Container(
              width: 340,
              height: 245,
              decoration: BoxDecoration(
                border: Border.all(color: Colors.white, width: 3),
                borderRadius: BorderRadius.circular(24),
              ),
            ),
          ),
        ),
        SafeArea(
          child: Align(
            alignment: Alignment.bottomCenter,
            child: Padding(
              padding: EdgeInsets.all(24),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    qrValue == null
                        ? 'Die gesamte Auftragskarte in den Rahmen halten'
                        : 'QR-Code erkannt – Karte ruhig und vollständig ausrichten',
                    textAlign: TextAlign.center,
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 17,
                      fontWeight: FontWeight.w700,
                      shadows: [Shadow(blurRadius: 8, color: Colors.black)],
                    ),
                  ),
                  const SizedBox(height: 16),
                  FilledButton.icon(
                    onPressed: qrValue == null ? null : captureCard,
                    icon: const Icon(Icons.camera_alt),
                    label: const Text('KARTE ERFASSEN'),
                    style: FilledButton.styleFrom(
                      minimumSize: const Size(double.infinity, 58),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
        if (recognizingText)
          ColoredBox(
            color: Color(0x99000000),
            child: Center(
              child: Card(
                child: Padding(
                  padding: EdgeInsets.all(22),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      CircularProgressIndicator(),
                      SizedBox(height: 16),
                      Text('Gedruckte Angaben werden gelesen …'),
                    ],
                  ),
                ),
              ),
            ),
          ),
      ],
    ),
  );
}
