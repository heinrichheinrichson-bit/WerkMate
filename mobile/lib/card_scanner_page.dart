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
  final recentImages = <List<int>>[];
  DateTime? lastImageAt;

  void detected(BarcodeCapture capture) {
    if (recognizingText) return;
    final raw = capture.barcodes
        .map((barcode) => barcode.rawValue?.trim())
        .whereType<String>()
        .where((value) => value.isNotEmpty)
        .firstOrNull;
    if (raw == null) return;
    final image = capture.image;
    if (image != null && image.isNotEmpty) {
      latestImage = image;
      final now = DateTime.now();
      if (lastImageAt == null ||
          now.difference(lastImageAt!).inMilliseconds >= 180) {
        recentImages.add(image);
        if (recentImages.length > 4) recentImages.removeAt(0);
        lastImageAt = now;
      }
    }
    if (qrValue != raw && mounted) setState(() => qrValue = raw);
  }

  Future<void> captureCard() async {
    final raw = qrValue;
    final image = latestImage;
    if (raw == null || image == null || recognizingText) return;
    setState(() => recognizingText = true);
    await Future<void>.delayed(const Duration(milliseconds: 350));
    await controller.stop();
    final images = recentImages.isEmpty ? [image] : [...recentImages];
    final candidates = <String>[];
    for (final candidateImage in images.reversed.take(3)) {
      final text = await recognizePrintedText(candidateImage);
      if (text.isNotEmpty) candidates.add(text);
    }
    final printedText = candidates.isEmpty
        ? ''
        : candidates.reduce(
            (best, candidate) =>
                _recognitionScore(candidate) > _recognitionScore(best)
                ? candidate
                : best,
          );
    if (mounted) {
      Navigator.pop(
        context,
        CardScannerResult(qrValue: raw, printedText: printedText),
      );
    }
  }

  int _recognitionScore(String text) {
    var score = text.length;
    if (RegExp(r'\d{3,7}\s*[-‐‑‒–—−]\s*\d{2}').hasMatch(text)) {
      score += 1000;
    }
    if (RegExp(r'Gesamtmenge', caseSensitive: false).hasMatch(text)) {
      score += 300;
    }
    if (RegExp(
      r'Gesamtmenge\s*\[?FA\]?',
      caseSensitive: false,
    ).hasMatch(text)) {
      score += 500;
    }
    return score;
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
