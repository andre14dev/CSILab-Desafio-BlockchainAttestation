import time
from dataclasses import dataclass

from domain.value_objects import DeviceId, Timestamp
from sensor.sensor_device import (
    SensorDevice,
    RandomSensorReader,
    EncryptedPayload
)
from sensor.http_transmitter import (
    ApiEndpointUrl,
    HttpHeaders,
    TransmissionPayload,
    HttpTransmitter,
    ConsoleTransmissionLogger,
    HttpTransmissionOrchestrator
)


@dataclass(frozen=True)
class CollectionInterval:

    _seconds: int

    def __post_init__(self):
        self._validate_positive()

    def _validate_positive(self) -> None:
        is_negative_or_zero = self._seconds <= 0

        if is_negative_or_zero:
            raise ValueError("Intervalo deve ser maior que 0")

    def in_seconds(self) -> int:
        return self._seconds

    def __str__(self) -> str:
        return f"{self._seconds}s"


class CollectionCycleExecutor:

    _sensor_device: SensorDevice
    _transmission_orchestrator: HttpTransmissionOrchestrator

    def __init__(
            self,
            sensor_device: SensorDevice,
            transmission_orchestrator: HttpTransmissionOrchestrator
    ):

        self._sensor_device = sensor_device
        self._transmission_orchestrator = transmission_orchestrator

    def execute_cycle(self) -> None:

        self._log_cycle_start()

        encrypted_payload = self._collect_and_encrypt()
        transmission_result = self._transmit_data(encrypted_payload)

        self._log_cycle_end(transmission_result.is_successful())

    def _log_cycle_start(self) -> None:
        device_id = self._sensor_device.get_device_id()
        print(f"\n{'=' * 60}")
        print(f"[SENSOR] Iniciando ciclo de coleta - {device_id}")
        print(f"{'=' * 60}")

    def _collect_and_encrypt(self) -> EncryptedPayload:

        reading = self._sensor_device.collect_reading()

        print(f"[SENSOR] Leitura coletada: {reading}")

        encrypted_payload = self._sensor_device.prepare_encrypted_data()

        print(f"[CRYPTO] Dados criptografados: {encrypted_payload}")

        return encrypted_payload

    def _transmit_data(self, encrypted_payload: EncryptedPayload):

        device_id = self._sensor_device.get_device_id()
        timestamp = Timestamp.now()

        payload = TransmissionPayload(
            device_identifier=device_id,
            encrypted_data=encrypted_payload,
            timestamp=timestamp
        )

        result = self._transmission_orchestrator.transmit_with_logging(payload)

        return result

    def _log_cycle_end(self, was_successful: bool) -> None:
        status_symbol = "✓" if was_successful else "✗"
        status_text = "Sucesso" if was_successful else "Falha"

        print(f"[STATUS] {status_symbol} Ciclo finalizado: {status_text}")


class SensorApplication:
    _cycle_executor: CollectionCycleExecutor
    _collection_interval: CollectionInterval

    def __init__(
            self,
            cycle_executor: CollectionCycleExecutor,
            collection_interval: CollectionInterval
    ):
        self._cycle_executor = cycle_executor
        self._collection_interval = collection_interval

    def run(self) -> None:

        self._print_startup_banner()

        try:
            self._run_collection_loop()
        except KeyboardInterrupt:
            self._print_shutdown_message()

    def _print_startup_banner(self) -> None:
        print("\n" + "=" * 60)
        print("  SENSOR IOT - BLOCKCHAIN ATTESTATION")
        print("  CS&I Lab - Object Calisthenics Edition")
        print("=" * 60)
        print(f"Intervalo de coleta: {self._collection_interval}")
        print("Pressione Ctrl+C para encerrar")
        print("=" * 60)

    def _run_collection_loop(self) -> None:

        cycle_number = 1

        while True:
            self._execute_single_cycle(cycle_number)
            self._wait_for_next_cycle()
            cycle_number += 1

    def _execute_single_cycle(self, cycle_number: int) -> None:
        print(f"\n[CICLO {cycle_number}]")
        self._cycle_executor.execute_cycle()

    def _wait_for_next_cycle(self) -> None:
        interval_seconds = self._collection_interval.in_seconds()
        time.sleep(interval_seconds)

    def _print_shutdown_message(self) -> None:
        print("\n\n" + "=" * 60)
        print("[SISTEMA] Encerrando aplicação...")
        print("[SISTEMA] Até logo! 👋")
        print("=" * 60 + "\n")


class ApplicationFactory:

    @staticmethod
    def create_sensor_application() -> SensorApplication:

        # 1. dispositivo sensor
        device_id = DeviceId("ESP-01")
        sensor_reader = RandomSensorReader(
            minimum_temperature=15.0,
            maximum_temperature=35.0
        )
        sensor_device = SensorDevice(device_id, sensor_reader)

        # 2. transmissor HTTP
        api_url = ApiEndpointUrl("http://localhost:5000/api/sensor-data")
        headers = HttpHeaders.for_json_request()
        transmitter = HttpTransmitter(api_url, headers)

        # 3. logger e orquestrador
        logger = ConsoleTransmissionLogger()
        orchestrator = HttpTransmissionOrchestrator(transmitter, logger)

        # 4. executor de ciclo
        cycle_executor = CollectionCycleExecutor(sensor_device, orchestrator)

        # 5. aplicação
        interval = CollectionInterval(2)  # 2 segundos
        application = SensorApplication(cycle_executor, interval)

        return application


def main() -> None:
    application = ApplicationFactory.create_sensor_application()
    application.run()


if __name__ == "__main__":
    main()
