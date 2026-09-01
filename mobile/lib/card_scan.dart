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
  final rawDieNumber = firstMatch(
    RegExp(r'(?:^|\s)GN\s*[:|;]?\s*([0-9]+(?:-[0-9]+)?)', caseSensitive: false),
  );
  final quantityText = firstMatch(
    RegExp(r'Gesamtmenge(?:\s*\[FA\])?\s*[:|;]?\s*(\d+)', caseSensitive: false),
  );

  return CardScanData(
    rawValue: rawValue,
    orderNumber: orderNumber,
    dieNumber: normalizeDieNumber(rawDieNumber),
    rawDieNumber: rawDieNumber,
    quantity: int.tryParse(quantityText ?? ''),
  );
}

String? normalizeDieNumber(String? value) {
  final trimmed = value?.trim();
  if (trimmed == null || trimmed.isEmpty) return null;
  return trimmed.replaceFirst(RegExp(r'-\d{2}$'), '');
}
