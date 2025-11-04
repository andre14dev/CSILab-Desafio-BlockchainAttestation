from dataclasses import dataclass
from typing import Protocol
import random
import hashlib
import binascii

from domain.value_objects import (
    DeviceId,
    SensorValue,
    Timestamp,
    EncryptionKey,
    DataHash
)


class SensorReader(Protocol):

    def read(self) -> SensorValue:
        ...


@dataclass(frozen=True)
class SensorReading:

    device_identifier: DeviceId
    measured_value: SensorValue

    def __post_init__(self):
        self._validate_components()

    def _validate_components(self) -> None:
        has_device = self.device_identifier is not None
        has_value = self.measured_value is not None

        if not has_device:
            raise ValueError("SensorReading deve ter device_identifier")

        if not has_value:
            raise ValueError("SensorReading deve ter measured_value")

    def format_as_packet(self) -> str:
        device_part = self.device_identifier.as_string()
        value_part = str(self.measured_value.in_celsius())

        return f"{device_part}:{value_part}"

    def __str__(self) -> str:
        return self.format_as_packet()


class RandomSensorReader:
    _minimum_temperature: float
    _maximum_temperature: float

    def __init__(
            self,
            minimum_temperature: float = 15.0,
            maximum_temperature: float = 35.0
    ):
        self._minimum_temperature = minimum_temperature
        self._maximum_temperature = maximum_temperature

    def read(self) -> SensorValue:
        temperature_range = self._maximum_temperature - self._minimum_temperature
        random_offset = random.random() * temperature_range
        temperature = self._minimum_temperature + random_offset

        rounded_temperature = round(temperature, 1)

        return SensorValue(rounded_temperature)


@dataclass(frozen=True)
class DataPacket:
    _content: str

    def as_string(self) -> str:
        return self._content

    def as_bytes(self) -> bytes:
        return self._content.encode('utf-8')

    @classmethod
    def from_reading(cls, reading: SensorReading) -> 'DataPacket':
        formatted_content = reading.format_as_packet()
        return cls(formatted_content)

    def __str__(self) -> str:
        return self._content


class DataEncryptor:
    _encryption_key: EncryptionKey
    _initialization_vector: bytes

    def __init__(self, encryption_key: EncryptionKey):
        self._encryption_key = encryption_key
        self._initialization_vector = self._create_initialization_vector()

    def _create_initialization_vector(self) -> bytes:
        return bytes([
            0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07,
            0x08, 0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x0e, 0x0f
        ])

    def encrypt(self, packet: DataPacket) -> 'EncryptedPayload':
        plaintext_bytes = packet.as_bytes()
        padded_bytes = self._apply_padding(plaintext_bytes)
        encrypted_bytes = self._perform_encryption(padded_bytes)
        hexadecimal_string = self._convert_to_hex(encrypted_bytes)

        return EncryptedPayload(hexadecimal_string)

    def _apply_padding(self, data: bytes) -> bytes:
        block_size = 16
        data_length = len(data)
        padding_length = block_size - (data_length % block_size)

        padding_bytes = bytes([padding_length] * padding_length)
        padded_data = data + padding_bytes

        return padded_data

    def _perform_encryption(self, padded_data: bytes) -> bytes:
        key_bytes = self._encryption_key.as_bytes()
        encrypted = bytearray()

        for index, byte in enumerate(padded_data):
            key_index = index % len(key_bytes)
            encrypted_byte = byte ^ key_bytes[key_index]
            encrypted.append(encrypted_byte)

        return bytes(encrypted)

    def _convert_to_hex(self, encrypted_bytes: bytes) -> str:
        return binascii.hexlify(encrypted_bytes).decode('ascii')


@dataclass(frozen=True)
class EncryptedPayload:
    _hexadecimal_data: str

    def as_hex_string(self) -> str:
        return self._hexadecimal_data

    def calculate_hash(self) -> DataHash:
        hash_object = hashlib.sha256(self._hexadecimal_data.encode())
        hash_hex = hash_object.hexdigest()

        return DataHash(hash_hex)

    def truncated_preview(self) -> str:
        preview_length = 40

        is_long = len(self._hexadecimal_data) > preview_length

        if is_long:
            return f"{self._hexadecimal_data[:preview_length]}..."

        return self._hexadecimal_data

    def __str__(self) -> str:
        return self.truncated_preview()


class SensorDevice:
    _device_identifier: DeviceId
    _sensor_reader: SensorReader

    def __init__(self, device_identifier: DeviceId, sensor_reader: SensorReader):
        self._device_identifier = device_identifier
        self._sensor_reader = sensor_reader

    def collect_reading(self) -> SensorReading:
        measured_value = self._sensor_reader.read()

        reading = SensorReading(
            device_identifier=self._device_identifier,
            measured_value=measured_value
        )

        return reading

    def prepare_encrypted_data(self) -> EncryptedPayload:
        reading = self.collect_reading()
        packet = DataPacket.from_reading(reading)

        encryptor = DataEncryptor(EncryptionKey.default())
        encrypted_payload = encryptor.encrypt(packet)

        return encrypted_payload

    def get_device_id(self) -> DeviceId:
        return self._device_identifier
