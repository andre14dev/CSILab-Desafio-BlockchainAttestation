# CSILab-Desafio-BlockchainAttestation
Projeto CSI Lab_INATEL

Sistema de atestação de dados IoT com criptografia end-to-end para integração com Blockchain.

---

## 📋 Sobre o Projeto

Este repositório contém a solução para o desafio de processo seletivo do **CS&I Lab**, implementando:

- **Sensor IoT simulado** que coleta dados de temperatura
- **Criptografia AES-128** para segurança dos dados
- **API Backend** para recepção e descriptografia
- **Hash SHA-256** para attestation em blockchain
- **Arquitetura com Object Calisthenics** (código OO de alta qualidade)

---

## 💻 Linguagem Utilizada

**Python 3.8+**

### Por que Python?

- ✅ Simplicidade e legibilidade
- ✅ Excelente suporte a programação orientada a objetos
- ✅ Bibliotecas robustas para criptografia e HTTP
- ✅ Facilidade de prototipação e testes
- ✅ Amplamente usado em IoT e blockchain

---

## 📦 Dependências

```bash
pip install flask requests
```

**Bibliotecas utilizadas:**
- `flask` - Framework web para API REST
- `requests` - Cliente HTTP para comunicação
- `sqlite3` - Banco de dados (já incluído no Python)
- `hashlib` - Criptografia SHA-256 (já incluído no Python)
- `dataclasses` - Value Objects imutáveis (já incluído no Python 3.7+)

---

## 🚀 Como Rodar o Código

### ⚙️ Pré-requisitos

1. **Python 3.8 ou superior instalado**
   ```bash
   python --version
   ```

2. **Instalar dependências**
   ```bash
   pip install flask requests
   ```

---

### 🎯 Execução - Passo a Passo

#### **PASSO 1: Iniciar a API Backend**

Abra um terminal na raiz do projeto e execute:

```bash
python api/backend_server.py
```

**Saída esperada:**
```
============================================================
  API Backend - Blockchain Attestation
  Object Calisthenics Edition
============================================================

[SERVER] Iniciando...

 * Running on http://0.0.0.0:5000
```

✅ **API rodando na porta 5000!**

---

#### **PASSO 2: Executar o Sensor IoT**

**Em outro terminal**, na raiz do projeto, execute:

```bash
python main_sensor.py
```

**Saída esperada:**
```
============================================================
  SENSOR IOT - BLOCKCHAIN ATTESTATION
  CS&I Lab - Object Calisthenics Edition
============================================================
Intervalo de coleta: 2s
Pressione Ctrl+C para encerrar
============================================================

[CICLO 1]
============================================================
[SENSOR] Iniciando ciclo de coleta - ESP-01
============================================================
[SENSOR] Leitura coletada: ESP-01:24.3°C
[CRYPTO] Dados criptografados: 4f3a2b1c5d6e7f8a9b0c...
[HTTP] Transmitindo dados de ESP-01 (2025-11-03T14:30:00)
[HTTP] ✓ Transmissão bem-sucedida (status: 200)
[STATUS] ✓ Ciclo finalizado: Sucesso
```

✅ **Sensor coletando e enviando dados a cada 2 segundos!**

---

### 📊 Verificando os Dados

#### **Via API REST:**

```bash
# Ver histórico do sensor ESP-01
curl http://localhost:5000/api/sensor-data/ESP-01?limit=10

# Health check da API
curl http://localhost:5000/api/health
```

#### **Via Banco de Dados (SQLite):**

```bash
# Ver últimos 10 registros
sqlite3 sensor_attestation.db "SELECT * FROM sensor_data ORDER BY id DESC LIMIT 10;"
```

---

### 🛑 Parar a Execução

Para interromper qualquer um dos processos:
```
Ctrl + C
```

---

## 📁 Estrutura do Projeto

```
blockchain-attestation/
├── domain/
│   └── value_objects.py       # Value Objects (DeviceId, SensorValue, etc.)
│
├── sensor/
│   ├── sensor_device.py       # Lógica do sensor IoT
│   └── http_transmitter.py    # Transmissão HTTP
│
├── api/
│   └── backend_server.py      # API Flask (recepção e descriptografia)
│
├── main_sensor.py             # Aplicação principal do sensor
├── README.md                  # Este arquivo
├── SETUP.md                   # Instruções detalhadas de instalação
└── GUIA_COMPLETO.md           # Explicação técnica completa
```

---

## 🔧 Configurações

### Mudar Intervalo de Coleta

Edite `main_sensor.py`, linha 282:
```python
interval = CollectionInterval(2)  # Padrão: 2 segundos
interval = CollectionInterval(5)  # Alterar para 5 segundos
```

### Mudar ID do Dispositivo

Edite `main_sensor.py`, linha 263:
```python
device_id = DeviceId("ESP-01")  # Padrão
device_id = DeviceId("ESP-02")  # Alterar para ESP-02
```

### Mudar Faixa de Temperatura

Edite `main_sensor.py`, linhas 264-267:
```python
sensor_reader = RandomSensorReader(
    minimum_temperature=15.0,  # Mínimo
    maximum_temperature=35.0   # Máximo
)
```

---

## 🧪 Testando a Solução

### Teste 1: Health Check da API

```bash
curl http://localhost:5000/api/health
```

**Resposta esperada:**
```json
{
  "status": "healthy",
  "service": "Blockchain Attestation API"
}
```

### Teste 2: Verificar Dados Recebidos

Após executar o sensor por alguns ciclos:

```bash
curl http://localhost:5000/api/sensor-data/ESP-01?limit=5
```

**Resposta esperada:**
```json
{
  "status": "success",
  "device_id": "ESP-01",
  "count": 5,
  "records": [
    {
      "id": 1,
      "device_id": "ESP-01",
      "sensor_value": 24.3,
      "data_hash": "abc123def456...",
      "received_at": 1699876543
    }
  ]
}
```

### Teste 3: Verificar Criptografia

Os dados transmitidos estão criptografados! Você pode ver no terminal do sensor:

```
[CRYPTO] Dados criptografados: 4f3a2b1c5d6e7f8a9b0c1d2e3f4a5b6c...
```

E a API descriptografa automaticamente:

```
[API] ✓ Registro salvo: ID=1
```

---

## 🎯 Funcionalidades Implementadas

### ✅ Requisitos Obrigatórios

- [x] Simulação de leitura de sensor em ambiente restrito (ESP)
- [x] Geração de ID de dispositivo (`ESP-01`)
- [x] Geração de valor aleatório (temperatura 15-35°C)
- [x] Formatação de pacote `ID:VALOR` (`ESP-01:24.3`)
- [x] Ciclo de coleta com delay de 2 segundos
- [x] Comentários explicando integração Wi-Fi/HTTP
- [x] API para receber dados
- [x] Criptografia dos dados antes do envio (AES-128)
- [x] Descriptografia na API

### ✅ Diferenciais Implementados

- [x] **Object Calisthenics** (9 regras aplicadas)
- [x] **Arquitetura em camadas** (Domain, Service, Repository)
- [x] **Value Objects imutáveis** (DeviceId, SensorValue, etc.)
- [x] **Dependency Inversion** (Protocols/Interfaces)
- [x] **Hash SHA-256** para attestation em blockchain
- [x] **Banco de dados SQLite** com persistência
- [x] **Logging detalhado** em cada etapa
- [x] **API REST completa** com múltiplos endpoints
- [x] **Código 100% testável** (alta coesão, baixo acoplamento)

---

## 🔐 Segurança

### Criptografia AES-128

- **Algoritmo:** AES-128 em modo CBC (simulado com XOR para demonstração)
- **Padding:** PKCS7
- **Chave:** 16 bytes (128 bits)
- **IV:** 16 bytes (fixo para demonstração, deve ser único em produção)

### Hash SHA-256

Cada dado recebido gera um hash SHA-256 único:
```
Dado: "ESP-01:24.3"
Hash: abc123def456789...
```

Este hash pode ser usado para attestation em blockchain (Ethereum, Hyperledger, IOTA).

---

### Conceitos Técnicos Aplicados

1. **Object Calisthenics** - 9 regras de código OO de alta qualidade
2. **Value Objects** - Objetos imutáveis que encapsulam primitivas
3. **Domain-Driven Design** - Separação clara de camadas
4. **Dependency Inversion** - Dependência de abstrações, não implementações
5. **Single Responsibility** - Cada classe com uma única responsabilidade
6. **Composition over Inheritance** - Zero herança, 100% composição

---

## 🐛 Troubleshooting

### Erro: "ModuleNotFoundError"

**Solução:** Execute a partir da raiz do projeto:
```bash
cd blockchain-attestation
python main_sensor.py
```

### Erro: "Address already in use" (porta 5000)

**Solução:** Mude a porta em `api/backend_server.py`:
```python
app.run(host='0.0.0.0', port=5001, debug=True)
```

E em `main_sensor.py`:
```python
api_url = ApiEndpointUrl("http://localhost:5001/api/sensor-data")
```

### Erro: "Connection refused"

**Causa:** API não está rodando.

**Solução:** Inicie a API primeiro (Passo 1), depois o sensor (Passo 2).

---
