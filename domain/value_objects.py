from dataclasses import dataclass
import re


@dataclass(frozen=True)
class DeviceId:

    _value: str

    def __post_init__(self):
        self._validate_format()
        self._validate_length()

    def _validate_format(self) -> None:

        pattern = r'^ESP-[A-Z0-9]+$'
        is_valid = re.match(pattern, self._value)

        if not is_valid:
            raise ValueError(
                f"DeviceId inválido: {self._value}. "
                f"Formato esperado: ESP-XXXX"
            )

    def _validate_length(self) -> None:
        is_too_short = len(self._value) < 5
        is_too_long = len(self._value) > 20

        if is_too_short:
            raise ValueError("DeviceId muito curto (mínimo 5 caracteres)")

        if is_too_long:
            raise ValueError("DeviceId muito longo (máximo 20 caracteres)")

    def as_string(self) -> str:
        return self._value

    def __str__(self) -> str:
        return self._value


@dataclass(frozen=True)
class SensorValue:

    _celsius: float

    def __post_init__(self):
        self._validate_range()
        self._validate_precision()

    def _validate_range(self) -> None:
        minimum_temperature = -50.0
        maximum_temperature = 100.0

        is_too_cold = self._celsius < minimum_temperature
        is_too_hot = self._celsius > maximum_temperature

        if is_too_cold:
            raise ValueError(f"Temperatura muito baixa: {self._celsius}°C")

        if is_too_hot:
            raise ValueError(f"Temperatura muito alta: {self._celsius}°C")

    def _validate_precision(self) -> None:
        rounded = round(self._celsius, 1)
        object.__setattr__(self, '_celsius', rounded)

    def in_celsius(self) -> float:
        return self._celsius

    def in_fahrenheit(self) -> float:
        return (self._celsius * 9 / 5) + 32

    def __str__(self) -> str:
        return f"{self._celsius}°C"


@dataclass(frozen=True)
class Timestamp:

    _unix_seconds: int

    def __post_init__(self):
        self._validate_positive()

    def _validate_positive(self) -> None:
        is_negative = self._unix_seconds < 0

        if is_negative:
            raise ValueError("Timestamp não pode ser negativo")

    def as_unix(self) -> int:
        return self._unix_seconds

    def as_iso_string(self) -> str:
        from datetime import datetime
        dt = datetime.fromtimestamp(self._unix_seconds)
        return dt.isoformat()

    @classmethod
    def now(cls) -> 'Timestamp':
        import time
        return cls(int(time.time()))

    def __str__(self) -> str:
        return self.as_iso_string()


@dataclass(frozen=True)
class EncryptionKey:

    _bytes: bytes

    def __post_init__(self):
        self._validate_size()

    def _validate_size(self) -> None:
        expected_size = 16
        actual_size = len(self._bytes)

        is_wrong_size = actual_size != expected_size

        if is_wrong_size:
            raise ValueError(
                f"Chave deve ter {expected_size} bytes, "
                f"mas tem {actual_size}"
            )

    def as_bytes(self) -> bytes:
        return self._bytes

    @classmethod
    def default(cls) -> 'EncryptionKey':

        default_key = bytes([
            0x2b, 0x7e, 0x15, 0x16, 0x28, 0xae, 0xd2, 0xa6,
            0xab, 0xf7, 0x15, 0x88, 0x09, 0xcf, 0x4f, 0x3c
        ])
        return cls(default_key)


@dataclass(frozen=True)
class DataHash:

    _hexadecimal: str

    def __post_init__(self):
        self._validate_format()
        self._validate_length()

    def _validate_format(self) -> None:
        is_valid_hex = all(c in '0123456789abcdef' for c in self._hexadecimal.lower())

        if not is_valid_hex:
            raise ValueError("Hash deve conter apenas caracteres hexadecimais")

    def _validate_length(self) -> None:
        expected_length = 64
        actual_length = len(self._hexadecimal)

        is_wrong_length = actual_length != expected_length

        if is_wrong_length:
            raise ValueError(
                f"Hash SHA-256 deve ter {expected_length} caracteres, "
                f"mas tem {actual_length}"
            )

    def as_string(self) -> str:
        return self._hexadecimal

    def short_format(self) -> str:
        return self._hexadecimal[:8]

    def __str__(self) -> str:
        return self._hexadecimal
