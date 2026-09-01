class CardScanData {
  const CardScanData({
    required this.rawValue,
    this.orderNumber,
    this.dieNumber,
    this.rawDieNumber,
    this.quantity,
  });

  final String rawValue;
  final String? orderNumber;
  final String? dieNumber;
  final String? rawDieNumber;
  final int? quantity;

  bool get hasRecognizedValue =>
      orderNumber != null || dieNumber != null || quantity != null;
}

CardScanData parseCardText(String rawValue) {
  String? firstMatch(RegExp pattern) =>
      pattern.firstMatch(rawValue)?.group(1)?.trim();

  final orderNumber = firstMatch(
    RegExp(r'(?:^|[\s|;])FA\s*[|:;]\s*([A-Z0-9-]+)', caseSensitive: false),
  );
  final labeledDieNumber = firstMatch(
    RegExp(r'(?:^|\s)GN\s*[:|;]?\s*([0-9]+(?:-[0-9]+)?)', caseSensitive: false),
  );
  final standaloneDieNumber = rawValue
      .split(RegExp(r'[\r\n]+'))
      .map(
        (line) => line
            .trim()
            .replaceAll(RegExp(r'[‐‑‒–—−]'), '-')
            .replaceAll(RegExp(r'\s*-\s*'), '-'),
      )
      .where((line) => RegExp(r'^\d{3,7}-\d{2}$').hasMatch(line))
      .firstOrNull;
  final safeLabeledDieNumber =
      normalizeDieNumber(labeledDieNumber) == orderNumber
      ? null
      : labeledDieNumber;
  final rawDieNumber = safeLabeledDieNumber ?? standaloneDieNumber;
  final faQuantity = firstMatch(
    RegExp(
      r'Gesamtmenge\s*[\[({]?\s*FA\s*[\])}]?\s*[:|;]?\s*(\d+)',
      caseSensitive: false,
    ),
  );
  final chargeQuantity = firstMatch(
    RegExp(
      r'Gesamtmenge\s*[\[({]?\s*Charge\s*[\])}]?\s*[:|;]?\s*(\d+)',
      caseSensitive: false,
    ),
  );
  final hasFaQuantityLabel = RegExp(
    r'Gesamtmenge\s*[\[({]?\s*FA\s*[\])}]?',
    caseSensitive: false,
  ).hasMatch(rawValue);
  final standaloneNumbers = rawValue
      .split(RegExp(r'[\r\n]+'))
      .map((line) => line.trim())
      .where((line) => RegExp(r'^\d{1,5}$').hasMatch(line))
      .toList();
  String? repeatedQuantity;
  if (standaloneNumbers.length >= 2 &&
      standaloneNumbers.last ==
          standaloneNumbers[standaloneNumbers.length - 2]) {
    repeatedQuantity = standaloneNumbers.last;
  }

  return CardScanData(
    rawValue: rawValue,
    orderNumber: orderNumber,
    dieNumber: normalizeDieNumber(rawDieNumber),
    rawDieNumber: rawDieNumber,
    quantity: int.tryParse(
      faQuantity ??
          repeatedQuantity ??
          (hasFaQuantityLabel ? chargeQuantity : null) ??
          '',
    ),
  );
}

String? normalizeDieNumber(String? value) {
  final trimmed = value?.trim();
  if (trimmed == null || trimmed.isEmpty) return null;
  return trimmed.replaceFirst(RegExp(r'-\d{2}$'), '');
}
