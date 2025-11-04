from dataclasses import dataclass
from typing import Protocol, Dict
import requests
import json

from domain.value_objects import DeviceId, Timestamp
from sensor.sensor_device import EncryptedPayload


@dataclass(frozen=True)
class ApiEndpointUrl:
    _url: str

    def __post_init__(self):
        self._validate_format()

    def _validate_format(self) -> None:
        starts_with_http = self._url.startswith('http://')
        starts_with_https = self._url.startswith('https://')

        is_valid = starts_with_http or starts_with_https

        if not is_valid:
            raise ValueError(
                f"URL inválida: {self._url}. "
                f"Deve começar com http:// ou https://"
            )

    def as_string(self) -> str:
        return self._url

    def __str__(self) -> str:
        return self._url


@dataclass(frozen=True)
class HttpHeaders:
    _headers_map: Dict[str, str]

    def as_dict(self) -> Dict[str, str]:
        return self._headers_map.copy()

    @classmethod
    def for_json_request(cls) -> 'HttpHeaders':
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "IoT-Sensor/1.0"
        }
        return cls(headers)

    @classmethod
    def with_authentication(cls, token: str) -> 'HttpHeaders':
        headers = cls.for_json_request().as_dict()
        headers["Authorization"] = f"Bearer {token}"
        return cls(headers)


@dataclass(frozen=True)
class TransmissionPayload:
    device_identifier: DeviceId
    encrypted_data: EncryptedPayload
    timestamp: Timestamp

    def as_json_string(self) -> str:
        payload_dict = self._build_dictionary()
        json_string = json.dumps(payload_dict)

        return json_string

    def _build_dictionary(self) -> Dict[str, any]:
        device_id = self.device_identifier.as_string()
        encrypted_hex = self.encrypted_data.as_hex_string()
        unix_timestamp = self.timestamp.as_unix()

        return {
            "device_id": device_id,
            "encrypted_data": encrypted_hex,
            "timestamp": unix_timestamp
        }


@dataclass(frozen=True)
class TransmissionResult:
    success: bool
    status_code: int
    response_body: str

    def is_successful(self) -> bool:
        return self.success

    def is_failure(self) -> bool:
        return not self.success

    @classmethod
    def successful(cls, status_code: int, body: str) -> 'TransmissionResult':
        return cls(
            success=True,
            status_code=status_code,
            response_body=body
        )

    @classmethod
    def failed(cls, status_code: int, error_message: str) -> 'TransmissionResult':
        return cls(
            success=False,
            status_code=status_code,
            response_body=error_message
        )


class HttpTransmitter:
    _api_endpoint: ApiEndpointUrl
    _http_headers: HttpHeaders

    def __init__(
            self,
            api_endpoint: ApiEndpointUrl,
            http_headers: HttpHeaders
    ):
        self._api_endpoint = api_endpoint
        self._http_headers = http_headers

    def transmit(self, payload: TransmissionPayload) -> TransmissionResult:
        try:
            response = self._send_http_post(payload)
            result = self._process_response(response)
            return result

        except requests.exceptions.RequestException as error:
            return self._handle_network_error(error)

    def _send_http_post(self, payload: TransmissionPayload) -> requests.Response:
        url = self._api_endpoint.as_string()
        headers = self._http_headers.as_dict()
        json_body = payload.as_json_string()

        response = requests.post(
            url=url,
            headers=headers,
            data=json_body,
            timeout=10
        )

        return response

    def _process_response(self, response: requests.Response) -> TransmissionResult:
        is_success = response.status_code == 200

        if is_success:
            return self._create_success_result(response)

        return self._create_failure_result(response)

    def _create_success_result(self, response: requests.Response) -> TransmissionResult:
        status_code = response.status_code
        body = response.text

        return TransmissionResult.successful(status_code, body)

    def _create_failure_result(self, response: requests.Response) -> TransmissionResult:
        status_code = response.status_code
        error_message = response.text

        return TransmissionResult.failed(status_code, error_message)

    def _handle_network_error(self, error: Exception) -> TransmissionResult:
        error_message = str(error)

        return TransmissionResult.failed(0, error_message)


class TransmissionLogger(Protocol):
    def log_attempt(self, payload: TransmissionPayload) -> None:
        ...

    def log_success(self, result: TransmissionResult) -> None:
        ...

    def log_failure(self, result: TransmissionResult) -> None:
        ...


class ConsoleTransmissionLogger:
    def log_attempt(self, payload: TransmissionPayload) -> None:
        device_id = payload.device_identifier.as_string()
        timestamp = payload.timestamp.as_iso_string()

        print(f"[HTTP] Transmitindo dados de {device_id} ({timestamp})")

    def log_success(self, result: TransmissionResult) -> None:
        status = result.status_code

        print(f"[HTTP] ✓ Transmissão bem-sucedida (status: {status})")

    def log_failure(self, result: TransmissionResult) -> None:
        status = result.status_code
        error = result.response_body[:100]

        print(f"[HTTP] ✗ Transmissão falhou (status: {status})")
        print(f"[HTTP] Erro: {error}")


class HttpTransmissionOrchestrator:
    _transmitter: HttpTransmitter
    _logger: TransmissionLogger

    def __init__(
            self,
            transmitter: HttpTransmitter,
            logger: TransmissionLogger
    ):
        self._transmitter = transmitter
        self._logger = logger

    def transmit_with_logging(self, payload: TransmissionPayload) -> TransmissionResult:
        self._logger.log_attempt(payload)

        result = self._transmitter.transmit(payload)

        if result.is_successful():
            self._logger.log_success(result)
            return result

        self._logger.log_failure(result)
        return result
