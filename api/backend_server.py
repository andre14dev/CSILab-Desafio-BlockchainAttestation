from flask import Flask, request, jsonify
from dataclasses import dataclass
from typing import Protocol, Dict, Optional
import sqlite3
import binascii
import hashlib
from datetime import datetime

from domain.value_objects import (
    DeviceId,
    SensorValue,
    EncryptionKey,
    DataHash,
    Timestamp
)


# ============================ DOMAIN LAYER ======================

@dataclass(frozen=True)
class ReceivedPayload:


    _hexadecimal_data: str

    def as_hex_string(self) -> str:
        return self._hexadecimal_data

    def as_bytes(self) -> bytes:
        return binascii.unhexlify(self._hexadecimal_data)


@dataclass(frozen=True)
class DecryptedData:

    _plaintext: str

    def as_string(self) -> str:
        return self._plaintext

    def parse_sensor_reading(self) -> 'ParsedSensorReading':

        parts = self._plaintext.split(':')

        self._validate_parts_count(parts)

        device_id = self._extract_device_id(parts)
        sensor_value = self._extract_sensor_value(parts)

        return ParsedSensorReading(device_id, sensor_value)

    def _validate_parts_count(self, parts: list) -> None:
        expected_parts = 2
        actual_parts = len(parts)

        is_invalid = actual_parts != expected_parts

        if is_invalid:
            raise ValueError(
                f"Formato inválido. Esperado: ID:VALOR, "
                f"mas encontrado {actual_parts} partes"
            )

    def _extract_device_id(self, parts: list) -> DeviceId:
        device_id_string = parts[0].strip()
        return DeviceId(device_id_string)

    def _extract_sensor_value(self, parts: list) -> SensorValue:
        value_string = parts[1].strip()

        try:
            value_float = float(value_string)
            return SensorValue(value_float)
        except ValueError:
            raise ValueError(f"Valor inválido: {value_string}")


@dataclass(frozen=True)
class ParsedSensorReading:

    device_identifier: DeviceId
    measured_value: SensorValue


@dataclass(frozen=True)
class SensorRecord:

    _reading: ParsedSensorReading
    _metadata: 'RecordMetadata'

    def get_reading(self) -> ParsedSensorReading:
        return self._reading

    def get_metadata(self) -> 'RecordMetadata':
        return self._metadata


@dataclass(frozen=True)
class RecordMetadata:

    data_hash: DataHash
    received_at: Timestamp


# ============= SERVICE LAYER =================

class DataDecryptor:
    _encryption_key: EncryptionKey
    _initialization_vector: bytes

    def __init__(self, encryption_key: EncryptionKey):
        self._encryption_key = encryption_key
        self._initialization_vector = self._create_iv()

    def _create_iv(self) -> bytes:
        return bytes([
            0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07,
            0x08, 0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x0e, 0x0f
        ])

    def decrypt(self, payload: ReceivedPayload) -> DecryptedData:


        encrypted_bytes = payload.as_bytes()
        decrypted_bytes = self._perform_decryption(encrypted_bytes)
        unpadded_bytes = self._remove_padding(decrypted_bytes)
        plaintext = unpadded_bytes.decode('utf-8')

        return DecryptedData(plaintext)

    def _perform_decryption(self, encrypted_bytes: bytes) -> bytes:
        key_bytes = self._encryption_key.as_bytes()
        decrypted = bytearray()

        for index, byte in enumerate(encrypted_bytes):
            key_index = index % len(key_bytes)
            decrypted_byte = byte ^ key_bytes[key_index]
            decrypted.append(decrypted_byte)

        return bytes(decrypted)

    def _remove_padding(self, padded_data: bytes) -> bytes:
        padding_length = padded_data[-1]
        unpadded_data = padded_data[:-padding_length]

        return unpadded_data


class HashCalculator:

    @staticmethod
    def calculate(data: str) -> DataHash:
        data_bytes = data.encode('utf-8')
        hash_object = hashlib.sha256(data_bytes)
        hash_hex = hash_object.hexdigest()

        return DataHash(hash_hex)


# ======================= REPOSITORY LAYER =====================

class SensorDataRepository(Protocol):

    def save(self, record: SensorRecord) -> int:
        ...

    def find_by_device_id(
            self,
            device_id: DeviceId,
            limit: int
    ) -> list[SensorRecord]:
        ...


@dataclass(frozen=True)
class DatabaseConnectionString:
    _path: str

    def as_string(self) -> str:
        return self._path

    @classmethod
    def default(cls) -> 'DatabaseConnectionString':
        return cls('sensor_attestation.db')


class SqliteSensorRepository:
    _connection_string: DatabaseConnectionString
    _table_name: str

    def __init__(self, connection_string: DatabaseConnectionString):
        self._connection_string = connection_string
        self._table_name = 'sensor_data'
        self._ensure_table_exists()

    def _ensure_table_exists(self) -> None:
        connection = self._create_connection()
        self._create_table(connection)
        connection.close()

    def _create_connection(self) -> sqlite3.Connection:
        db_path = self._connection_string.as_string()
        return sqlite3.connect(db_path)

    def _create_table(self, connection: sqlite3.Connection) -> None:
        cursor = connection.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sensor_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                sensor_value REAL NOT NULL,
                data_hash TEXT NOT NULL,
                received_at INTEGER NOT NULL
            )
        ''')

        connection.commit()

    def save(self, record: SensorRecord) -> int:
        connection = self._create_connection()
        record_id = self._insert_record(connection, record)
        connection.close()

        return record_id

    def _insert_record(
            self,
            connection: sqlite3.Connection,
            record: SensorRecord
    ) -> int:
        cursor = connection.cursor()

        reading = record.get_reading()
        metadata = record.get_metadata()

        device_id = reading.device_identifier.as_string()
        sensor_value = reading.measured_value.in_celsius()
        data_hash = metadata.data_hash.as_string()
        timestamp = metadata.received_at.as_unix()

        cursor.execute('''
            INSERT INTO sensor_data 
            (device_id, sensor_value, data_hash, received_at)
            VALUES (?, ?, ?, ?)
        ''', (device_id, sensor_value, data_hash, timestamp))

        connection.commit()

        return cursor.lastrowid

    def find_by_device_id(
            self,
            device_id: DeviceId,
            limit: int
    ) -> list[Dict]:
        connection = self._create_connection()
        records = self._query_records(connection, device_id, limit)
        connection.close()

        return records

    def _query_records(
            self,
            connection: sqlite3.Connection,
            device_id: DeviceId,
            limit: int
    ) -> list[Dict]:
        connection.row_factory = sqlite3.Row
        cursor = connection.cursor()

        device_id_string = device_id.as_string()

        cursor.execute('''
            SELECT * FROM sensor_data
            WHERE device_id = ?
            ORDER BY received_at DESC
            LIMIT ?
        ''', (device_id_string, limit))

        rows = cursor.fetchall()

        return [dict(row) for row in rows]


# ========================== API LAYER ==================

@dataclass(frozen=True)
class ApiRequest:
    _json_data: Dict

    def get_device_id(self) -> DeviceId:
        device_id_string = self._json_data.get('device_id', '')
        return DeviceId(device_id_string)

    def get_encrypted_data(self) -> ReceivedPayload:
        encrypted_hex = self._json_data.get('encrypted_data', '')
        return ReceivedPayload(encrypted_hex)

    @classmethod
    def from_flask_request(cls, flask_request) -> 'ApiRequest':
        json_data = flask_request.get_json() or {}
        return cls(json_data)


class RequestValidator:

    @staticmethod
    def validate(api_request: ApiRequest) -> None:
        RequestValidator._validate_device_id(api_request)
        RequestValidator._validate_encrypted_data(api_request)

    @staticmethod
    def _validate_device_id(api_request: ApiRequest) -> None:
        try:
            api_request.get_device_id()
        except Exception as error:
            raise ValueError(f"device_id inválido: {error}")

    @staticmethod
    def _validate_encrypted_data(api_request: ApiRequest) -> None:
        try:
            payload = api_request.get_encrypted_data()
            is_empty = len(payload.as_hex_string()) == 0

            if is_empty:
                raise ValueError("encrypted_data vazio")

        except Exception as error:
            raise ValueError(f"encrypted_data inválido: {error}")


class SensorDataHandler:
    _decryptor: DataDecryptor
    _repository: SensorDataRepository

    def __init__(
            self,
            decryptor: DataDecryptor,
            repository: SensorDataRepository
    ):
        self._decryptor = decryptor
        self._repository = repository

    def handle(self, api_request: ApiRequest) -> SensorRecord:
        RequestValidator.validate(api_request)

        device_id = api_request.get_device_id()
        encrypted_payload = api_request.get_encrypted_data()

        decrypted_data = self._decryptor.decrypt(encrypted_payload)
        parsed_reading = decrypted_data.parse_sensor_reading()

        self._validate_device_id_match(device_id, parsed_reading)

        record = self._create_record(parsed_reading, decrypted_data)
        record_id = self._repository.save(record)

        print(f"[API] ✓ Registro salvo: ID={record_id}")

        return record

    def _validate_device_id_match(
            self,
            claimed_id: DeviceId,
            reading: ParsedSensorReading
    ) -> None:
        claimed = claimed_id.as_string()
        actual = reading.device_identifier.as_string()

        is_mismatch = claimed != actual

        if is_mismatch:
            raise ValueError(
                f"Device ID não corresponde: "
                f"requisição={claimed}, pacote={actual}"
            )

    def _create_record(
            self,
            reading: ParsedSensorReading,
            decrypted_data: DecryptedData
    ) -> SensorRecord:
        plaintext = decrypted_data.as_string()
        data_hash = HashCalculator.calculate(plaintext)
        timestamp = Timestamp.now()

        metadata = RecordMetadata(data_hash, timestamp)

        return SensorRecord(reading, metadata)


# ================= FLASK APPLICATION ==========================

def create_flask_app() -> Flask:

    app = Flask(__name__)

    #dep
    encryption_key = EncryptionKey.default()
    decryptor = DataDecryptor(encryption_key)

    connection_string = DatabaseConnectionString.default()
    repository = SqliteSensorRepository(connection_string)

    handler = SensorDataHandler(decryptor, repository)

    #rotas
    setup_routes(app, handler, repository)

    return app


def setup_routes(
        app: Flask,
        handler: SensorDataHandler,
        repository: SensorDataRepository
) -> None:

    @app.route('/api/sensor-data', methods=['POST'])
    def receive_sensor_data():
        try:
            api_request = ApiRequest.from_flask_request(request)
            record = handler.handle(api_request)

            return create_success_response(record)

        except ValueError as error:
            return create_error_response(str(error), 400)
        except Exception as error:
            return create_error_response(str(error), 500)

    @app.route('/api/sensor-data/<device_id>', methods=['GET'])
    def get_sensor_history(device_id: str):
        try:
            device = DeviceId(device_id)
            limit = request.args.get('limit', 100, type=int)

            records = repository.find_by_device_id(device, limit)

            return jsonify({
                "status": "success",
                "device_id": device_id,
                "count": len(records),
                "records": records
            })

        except Exception as error:
            return create_error_response(str(error), 500)

    @app.route('/api/health', methods=['GET'])
    def health_check():
        """Health check"""
        return jsonify({
            "status": "healthy",
            "service": "Blockchain Attestation API"
        })


def create_success_response(record: SensorRecord) -> tuple:
    reading = record.get_reading()
    metadata = record.get_metadata()

    device_id = reading.device_identifier.as_string()
    sensor_value = reading.measured_value.in_celsius()
    data_hash = metadata.data_hash.as_string()
    timestamp = metadata.received_at.as_iso_string()

    response = {
        "status": "success",
        "device_id": device_id,
        "sensor_value": sensor_value,
        "data_hash": data_hash,
        "received_at": timestamp
    }

    return jsonify(response), 200


def create_error_response(message: str, status_code: int) -> tuple:
    return jsonify({
        "status": "error",
        "message": message
    }), status_code


# ===================== MAIN ================================

def main() -> None:
    print("=" * 60)
    print("  API Backend - Blockchain Attestation")
    print("  Object Calisthenics Edition")
    print("=" * 60)
    print("\n[SERVER] Iniciando...\n")

    app = create_flask_app()
    app.run(host='0.0.0.0', port=5000, debug=True)


if __name__ == "__main__":
    main()