class CardScanData {
  const CardScanData({
    required this.rawValue,
    this.orderNumber,
    this.dieNumber,
    this.quantity,
  });

  final String rawValue;
  final String? orderNumber;
  final String? dieNumber;
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
  final dieNumber = firstMatch(
    RegExp(r'(?:^|\s)GN\s*[:|;]?\s*([0-9]+(?:-[0-9]+)?)', caseSensitive: false),
  );
  final quantityText = firstMatch(
    RegExp(r'Gesamtmenge(?:\s*\[FA\])?\s*[:|;]?\s*(\d+)', caseSensitive: false),
  );

  return CardScanData(
    rawValue: rawValue,
    orderNumber: orderNumber,
    dieNumber: dieNumber,
    quantity: int.tryParse(quantityText ?? ''),
  );
}
