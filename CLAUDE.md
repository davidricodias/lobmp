# LOBMP - Limit Order Book Message Processor

## Contexto del Proyecto para Agentes IA

Este documento proporciona un contexto completo del proyecto LOBMP para ser entendido por agentes de IA como Claude.

---

## 1. Descripción General

**LOBMP** (Limit Order Book Message Processor) es un procesador de alto rendimiento para datos de trading de alta frecuencia, diseñado específicamente para transformar mensajes raw de LSEG (anteriormente Refinitiv) en formato Parquet estructurado.

### Características Principales
- **Procesamiento paralelo multi-thread** de archivos CSV de gran tamaño
- **Conversión eficiente** a formato Parquet particionado
- **CLI simple** con soporte de logging configurable
- **Alto rendimiento** gracias a Rust + Polars
- **Interfaz Python** amigable vía PyO3

### Casos de Uso
- Análisis de datos de mercado de alta frecuencia
- Investigación financiera y backtesting
- Procesamiento de datos de Limit Order Book (LOB)
- Transformación de datos LSEG/Refinitiv a formatos modernos

---

## 2. Arquitectura y Tecnologías

### Arquitectura Híbrida Python/Rust

```
┌─────────────────────────────────────────┐
│         Python Layer (CLI)              │
│  - Interface de usuario                 │
│  - Configuración y logging              │
│  - Entry points                         │
└──────────────┬──────────────────────────┘
               │ PyO3 Bindings
               ▼
┌─────────────────────────────────────────┐
│         Rust Layer (Core)               │
│  - Parsing de CSV                       │
│  - Procesamiento paralelo (Crossbeam)   │
│  - Transformación de datos (Polars)     │
│  - Escritura Parquet                    │
└─────────────────────────────────────────┘
```

### Stack Tecnológico

#### Rust (Core - src/lib.rs)
- **PyO3 (x)**: Bindings Python ↔ Rust, permite crear módulos Python nativos en Rust
- **Polars (0.46.0)**: DataFrame library de alto rendimiento (alternativa a pandas en Rust)
- **Crossbeam (0.8.4)**: Primitivas de concurrencia para procesamiento paralelo
- **pyo3-polars (0.20.0)**: Integración entre PyO3 y Polars para pasar DataFrames

#### Python (Interface - lobmp/)
- **Polars**: Manipulación de datos (usado desde Python cuando sea necesario)
- **Maturin (1.8.3)**: Build system para proyectos PyO3/Rust
- **argparse**: CLI parsing (stdlib)

#### Herramientas de Desarrollo
- **pytest + pytest-cov + pytest-xdist**: Testing con coverage y paralelización
- **mypy**: Type checking estático
- **ruff**: Linter y formatter moderno
- **pre-commit**: Git hooks para QA
- **mkdocs + mkdocs-material**: Documentación
- **nox**: Automatización de tareas

---

## 3. Estructura del Proyecto

```
lobmp/
├── src/
│   └── lib.rs                    # Core en Rust: toda la lógica de procesamiento
├── lobmp/                        # Package Python
│   ├── __init__.py              # Exporta funciones desde el módulo Rust
│   ├── __main__.py              # Entry point para python -m lobmp
│   ├── _lobmp.pyi               # Type stubs para el módulo Rust
│   ├── _version.py              # Versión del package
│   ├── cli.py                   # CLI con argparse
│   ├── main.py                  # Lógica principal de la aplicación
│   ├── logger.py                # Configuración de logging
│   ├── py.typed                 # Marker para PEP 561 (typed package)
│   └── definitions/
│       ├── __init__.py
│       └── fids.py              # Definiciones de Field IDs conocidos
├── tests/                       # Tests de pytest
├── docs/                        # Documentación MkDocs
├── testing_folder/              # Datos de prueba
├── Cargo.toml                   # Configuración Rust
├── pyproject.toml               # Configuración Python (PEP 621)
├── uv.lock                      # Lock file de dependencias (uv)
├── README.md                    # Documentación de usuario
└── LICENSE                      # MIT License
```

---

## 4. Componentes Principales

### 4.1 Módulo Rust (src/lib.rs)

#### Funciones Exportadas a Python

##### `find_market_by_price_lines(path: PathBuf) -> List[int]`
- **Propósito**: Encuentra todas las líneas que contienen "Market By Price"
- **Input**: Path a un archivo CSV
- **Output**: Lista de índices de línea donde aparece "Market By Price"
- **Uso**: Identificar rápidamente las secciones de Market By Price en el archivo

##### `extract_fids(path: PathBuf) -> Dict[str, List[str]]`
- **Propósito**: Extrae todos los Field IDs (FIDs) del archivo
- **Input**: Path a un archivo CSV
- **Output**: Diccionario {nombre_fid: [fid_number, has_two_values]}
- **Lógica**:
  - Busca líneas con columna[4] == "FID"
  - Extrae FID number (columna[5]) y nombre (columna[7])
  - Detecta si tiene dos valores (columna[9] no vacía)

##### `flatten_map_entry(message: str) -> List[List[str]]`
- **Propósito**: Convierte un mensaje estructurado en formato matriz
- **Input**: String de mensaje multi-línea
- **Output**: Matriz [headers] + [rows...]
- **Lógica**: Aplana entradas de MapEntry en formato tabular

##### `flatten_market_by_price(message: str) -> PyDataFrame`
- **Propósito**: Parsea un mensaje "Market By Price" completo a DataFrame
- **Input**: String de mensaje multi-línea
- **Output**: Polars DataFrame con todas las columnas estructuradas
- **Lógica**:
  - Extrae header info (TICKER, TIMESTAMP, GMT_OFFSET, etc.)
  - Procesa Summary section
  - Procesa MapEntry sections
  - Procesa FID fields
  - Combina todo en un DataFrame con esquema completo

##### `run(path: PathBuf, output_path: PathBuf) -> bool`
- **Propósito**: Función principal de procesamiento completo del archivo
- **Input**:
  - `path`: Path al archivo CSV de entrada
  - `output_path`: Directorio para archivos Parquet de salida
- **Output**: `bool` indicando éxito/fallo
- **Flujo** (ver sección 5 para detalles)

#### Estructuras Internas

```rust
struct IndexedMessage {
    index: usize,      // Orden secuencial del mensaje
    content: String,   // Contenido del mensaje completo
}

struct IndexedDataFrame {
    index: usize,      // Orden secuencial del DataFrame
    data: DataFrame,   // DataFrame procesado
}
```

### 4.2 Módulo Python

#### `lobmp/cli.py`
- **CLI Interface** usando `argparse`
- **Argumentos**:
  - `filepath` (required): Path al archivo CSV
  - `targetdir` (required): Directorio de salida
  - `--verbose` (optional): Nivel de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL, NOTSET)
- **Entry point**: Registrado en `pyproject.toml` como `lobmp`

#### `lobmp/main.py`
- **Función principal**: `main(filepath, targetdir, verbose)`
- **Responsabilidades**:
  - Activar y configurar logger según nivel
  - Construir paths de entrada/salida
  - Llamar a la función `run` de Rust
  - Medir tiempos de ejecución

#### `lobmp/logger.py`
- **Sistema de logging** personalizado
- **Funcionalidades**:
  - `activate_logger()`: Activa el logger
  - `set_logger_level(level)`: Configura nivel de logging
  - `log.timeit(name)`: Context manager para timing

#### `lobmp/definitions/fids.py`
- **Definiciones de Field IDs conocidos**
- **Estructuras**:
  - `known_fids`: Dict[str, List] - FIDs conocidos con número y flag de doble valor
  - `columns_order`: List[str] - Orden preferido de columnas en output
  - `supplement`: List[str] - Columnas suplementarias añadidas por el procesador

##### FIDs Clave
```python
# Ejemplos de FIDs importantes:
"PROD_PERM": ["1", False]       # Permiso de producto
"CURRENCY": ["15", True]        # Moneda (tiene dos valores)
"ORDER_PRC": ["3427", False]    # Precio de orden
"ORDER_SIDE": ["3428", True]    # Lado de orden (BID/ASK)
"NO_ORD": ["3430", False]       # Número de órdenes
"ACC_SIZE": ["4356", False]     # Tamaño acumulado
```

---

## 5. Flujo de Procesamiento Detallado

### Pipeline de la función `run()`

```
1. VALIDACIÓN
   ├─ Verificar extensión .csv
   ├─ Abrir archivo
   └─ Crear BufReader

2. ANÁLISIS INICIAL (Primera Pasada)
   ├─ Contar líneas totales
   ├─ Detectar FIDs posibles
   └─ Resetear reader a inicio

3. CONFIGURACIÓN DE CONCURRENCIA
   ├─ Detectar núcleos CPU disponibles
   ├─ Crear channel de parsing (bounded: 2*CPUs)
   ├─ Crear channel de dataframes (bounded: 2*CPUs)
   └─ Lanzar threads workers

4. WORKERS DE PARSING (num_cpus threads)
   Para cada mensaje recibido:
   ├─ Recibir IndexedMessage desde channel
   ├─ Ejecutar flat_market_by_price()
   ├─ Crear DataFrame
   ├─ Enviar IndexedDataFrame a channel de salida
   └─ Repetir hasta que channel se cierre

5. WORKER DE ESCRITURA (1 thread)
   ├─ Recibir DataFrames desordenados
   ├─ Reordenar secuencialmente por índice
   ├─ Normalizar esquema (añadir columnas faltantes)
   ├─ Acumular en batch (BATCH_SIZE = 16384)
   ├─ Cuando batch lleno:
   │  ├─ Concatenar todos los DataFrames
   │  ├─ Escribir a part-NNNNNN.parquet
   │  └─ Incrementar contador de batch
   └─ Flush final de DataFrames restantes

6. LECTURA Y DISTRIBUCIÓN (Thread principal)
   ├─ Leer archivo línea por línea
   ├─ Detectar inicio de mensaje ("Market By Price")
   ├─ Acumular líneas del mensaje
   ├─ Al encontrar siguiente mensaje:
   │  ├─ Crear IndexedMessage
   │  └─ Enviar a channel de parsing
   ├─ Logging de progreso cada 100k líneas
   └─ Enviar último mensaje

7. SINCRONIZACIÓN Y CIERRE
   ├─ Cerrar channel de parsing
   ├─ Esperar finalización de parsing threads
   ├─ Cerrar channel de dataframes
   ├─ Esperar finalización de writing thread
   └─ Retornar éxito/fallo
```

### Características de Concurrencia

#### Bounded Channels (Crossbeam)
- **Tamaño**: `2 * num_cpus`
- **Ventajas**:
  - Backpressure natural (evita consumir demasiada memoria)
  - Balance entre throughput y uso de memoria
  - Thread sender se bloquea si channel está lleno

#### Reordenamiento Secuencial
```rust
let mut dataframes_map: HashMap<usize, LazyFrame> = HashMap::new();
let mut next_index_to_write: usize = 0;

// Recibir DataFrame procesado (puede llegar desordenado)
dataframes_map.insert(indexed_df.index, df);

// Escribir en orden secuencial
while dataframes_map.contains_key(&next_index_to_write) {
    dfs.push(dataframes_map.remove(&next_index_to_write).unwrap());
    next_index_to_write += 1;
}
```
**Razón**: Garantiza que los mensajes se escriban en el orden original del archivo

#### Normalización de Esquema
```rust
// Todas las columnas posibles detectadas en primera pasada
let expected_columns: Vec<&str> = possible_fids.iter().collect();

// Para cada DataFrame, añadir columnas faltantes con valores vacíos
df_with_all_columns = expected_columns.iter().fold(df, |acc, &col_name| {
    if !df.schema().contains(col_name) {
        acc.with_column(lit("").alias(col_name))
    } else {
        acc
    }
});
```
**Razón**: Parquet requiere esquema consistente; algunos mensajes pueden no tener todos los FIDs

---

## 6. Formato de Datos

### Input: CSV de LSEG/Refinitiv

**Estructura de un mensaje Market By Price:**
```csv
TICKER,Market By Price,TIMESTAMP,GMT_OFFSET,,MSG_TYPE,...
,,,,Summary,...
,,,,FID,NUM,NAME,VALUE,...
,,,,MapEntry,TYPE,,,,,,,KEY,...
,,,,FID,NUM,NAME,VALUE,...
,,,,FID,NUM,NAME,VALUE,VALUE2,...
,,,,MapEntry,TYPE,,,,,,,KEY,...
...
```

**Ejemplo:**
```csv
EUR=,Market By Price,2024-01-01 09:30:15.123,+00:00,,REFRESH,...
,,,,Summary,...
,,,,FID,3,DSPLY_NAME,EUR/USD,...
,,,,MapEntry,ADD,,,,,,,1,...
,,,,FID,3427,ORDER_PRC,1.0850,...
,,,,FID,3428,ORDER_SIDE,BID,...
,,,,FID,3430,NO_ORD,5,...
```

### Output: Parquet Particionado

**Estructura de directorios:**
```
output_directory/
├── part-000000.parquet
├── part-000001.parquet
├── part-000002.parquet
└── ...
```

**Esquema típico:**
```
TICKER: String
TIMESTAMP: String
GMT_OFFSET: String
MARKET_MESSAGE_TYPE: String
MAP_ENTRY_TYPE: String
MAP_ENTRY_KEY: String
ORDER_PRC: String
ORDER_SIDE: String
NO_ORD: String
ACC_SIZE: String
... (todos los FIDs detectados)
```

**Nota**: Todos los valores son String para máxima flexibilidad; el usuario puede castear según necesite

---

## 7. Patrones de Diseño

### 7.1 Pipeline de Procesamiento (Producer-Consumer)

```
[Reader] → [Parser Workers] → [Writer]
   │              │                │
   │         (N threads)       (1 thread)
   │              │                │
   └─→ Channel ─→ ├─→ Channel ─→  │
                  └─→
```

### 7.2 Lazy Evaluation (Polars LazyFrame)

- **DataFrames** se procesan como `LazyFrame` hasta el momento de escritura
- **Optimización**: Polars optimiza el query plan antes de ejecutar
- **Eficiencia**: Solo se materializan los datos cuando se escriben

### 7.3 Schema on Read

- **Detección dinámica** de columnas en primera pasada
- **Flexibilidad**: No requiere esquema predefinido
- **Robusto**: Maneja variaciones en los datos

### 7.4 Batch Processing

- **Batch size**: 16384 mensajes por archivo Parquet
- **Trade-off**: Balance entre tamaño de archivo y overhead de I/O
- **Particionamiento**: Facilita procesamiento paralelo posterior

---

## 8. Puntos de Extensión

### 8.1 Agregar Soporte para Otros Providers

**Actualmente**: Solo soporta LSEG/Refinitiv

**Extensión propuesta**:
1. Crear `src/providers/lseg.rs` con lógica actual
2. Crear `src/providers/mod.rs` con trait:
   ```rust
   trait Provider {
       fn parse_message(&self, message: &str) -> Result<DataFrame>;
       fn detect_messages(&self, reader: &mut BufReader<File>) -> Vec<usize>;
   }
   ```
3. Implementar nuevos providers (ej. `src/providers/nyse.rs`)
4. Modificar `run()` para aceptar provider como parámetro

### 8.2 Soporte para L10 (Market Depth Level 10)

**TODO actual** en código:
```rust
// TODO: add run_l10 function to do a run with L10 files
```

**Implementación sugerida**:
1. Crear función `run_l10(path, output_path)` similar a `run()`
2. Adaptar `flat_market_by_price()` para manejar 10 niveles
3. Posiblemente diferentes FIDs o estructura de MapEntry
4. Añadir argumento CLI: `--market-depth [price|l10]`

### 8.3 Streaming Processing

**Actualmente**: Procesa archivo completo en memoria (con batching)

**Mejora potencial**:
- Usar Polars streaming API
- Procesar archivos que no caben en RAM
- Reducir latencia de primer batch

### 8.4 Validación de Datos

**Actualmente**: Minimal validation

**Extensiones posibles**:
1. Schema validation contra `known_fids`
2. Type checking (ej. ORDER_PRC debe ser numérico)
3. Range validation (ej. ORDER_SIDE solo BID/ASK)
4. Opción `--strict` que rechaza mensajes inválidos

---

## 9. Guía de Desarrollo

### 9.1 Setup Inicial

```bash
# 1. Clonar repositorio
git clone https://github.com/davidricodias/lobmp.git
cd lobmp

# 2. Crear entorno virtual Python
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# 3. Instalar uv y sincronizar dependencias
pip install uv
uv lock
just develop  # Instala dependencias + compila Rust

# 4. Instalar pre-commit hooks
pre-commit install

# 5. Instalar herramientas Rust
rustup component add llvm-tools-preview  # Para coverage
```

### 9.2 Flujo de Desarrollo

```bash
# Desarrollo iterativo (compila Rust + instala Python)
maturin develop

# Ejecutar tests
pytest

# Tests con coverage
pytest --cov=lobmp --cov-report=html

# Type checking
mypy lobmp/

# Linting y formatting
ruff check .
ruff format .

# Construir documentación
mkdocs serve  # http://localhost:8000

# Build para release
maturin build --release
```

### 9.3 Estructura de Tests

```python
# tests/test_main.py
def test_find_market_by_price_lines():
    # Test de función Rust desde Python
    ...

def test_extract_fids():
    # Test de extracción de FIDs
    ...

def test_flatten_market_by_price():
    # Test de parsing de mensaje completo
    ...

def test_run_integration():
    # Test end-to-end con archivo real
    ...
```

### 9.4 Debugging

#### Debugging Rust desde Python
```python
# Compilar con debug symbols
# En desarrollo, maturin develop usa debug por defecto

import lobmp
result = lobmp.run("input.csv", "output/")
# Errores de Rust aparecerán con stack traces
```

#### Logging desde Rust
```rust
// Usar Python logger desde Rust
let logging = PyModule::import(py, "logging")?;
let logger = logging.getattr("getLogger")?.call1(("lobmp",))?;
logger.call_method1("info", ("Mensaje desde Rust",))?;
```

### 9.5 Performance Profiling

```bash
# Python profiling
python -m cProfile -o profile.out -m lobmp input.csv output/
snakeviz profile.out

# Rust profiling (con cargo-flamegraph)
cargo install flamegraph
# Modificar temporalmente Cargo.toml para crear binario
cargo flamegraph --bin lobmp_bench
```

### 9.6 Build y Release

```bash
# Build wheel para distribución
maturin build --release

# Publicar a PyPI (requiere credenciales)
maturin publish

# Build para múltiples plataformas (CI/CD)
maturin build --release --target x86_64-unknown-linux-gnu
maturin build --release --target x86_64-apple-darwin
maturin build --release --target x86_64-pc-windows-msvc
```

---

## 10. Configuraciones Importantes

### 10.1 Cargo.toml (Rust)

```toml
[lib]
name = "_lobmp"              # Nombre del módulo Python
crate-type = ["cdylib"]      # Biblioteca dinámica para PyO3

[dependencies]
pyo3 = { version = "x", features = ["extension-module"] }
# "x" permite cualquier versión compatible con maturin
```

### 10.2 pyproject.toml (Python)

```toml
[build-system]
requires = ["maturin>=1.5,<2.0"]
build-backend = "maturin"    # Usa Maturin como build backend

[tool.maturin]
module-name = "lobmp._lobmp"  # Módulo Rust como submódulo de lobmp
binding = "pyo3"              # Tipo de binding
features = ["pyo3/extension-module"]
```

### 10.3 Pre-commit Hooks

```yaml
# .pre-commit-config.yaml (si existe)
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    hooks:
      - id: ruff
      - id: ruff-format
  - repo: https://github.com/pre-commit/mirrors-mypy
    hooks:
      - id: mypy
```

---

## 11. Limitaciones Conocidas

### 11.1 Formato de Input
- **Solo CSV**: No soporta otros formatos (JSON, binary, etc.)
- **Solo LSEG/Refinitiv**: Estructura específica hardcodeada

### 11.2 Performance
- **Single file**: No soporta procesamiento batch de múltiples archivos
- **Memoria**: Primera pasada lee archivo completo para contar líneas
- **Sin streaming**: Archivo debe ser legible secuencialmente desde disco

### 11.3 Calidad de Datos
- **No validation**: Acepta cualquier dato, no valida tipos ni rangos
- **Valores como String**: Todos los valores se guardan como String
- **Sin deduplicación**: No detecta mensajes duplicados

### 11.4 Error Handling
- **Fail-fast**: Un error en parsing detiene todo el procesamiento
- **No partial results**: No guarda batches completados si hay fallo posterior
- **Limited recovery**: No puede resumir procesamiento interrumpido

---

## 12. Roadmap y TODOs

### ✅ TODOs Resueltos (2024-12-10)

**Implementación L10 Completada:**

Todos los TODOs relacionados con L10 han sido implementados y testeados:

1. ✅ **src/lib.rs**: Implementadas funciones `run_l10()` y `flat_l10_csv()`
2. ✅ **lobmp/__init__.py**: Exportada función `run_l10`
3. ✅ **lobmp/_lobmp.pyi**: Añadida type signature para `run_l10`
4. ✅ **lobmp/main.py**: Soporta parámetro `format` con valores `mbp` y `l10`
5. ✅ **lobmp/cli.py**: Argumento `--format [mbp|l10]` implementado
6. ✅ **tests/test_lobmp.py**: 6 nuevos tests para `run_l10()` (todos pasando)
7. ✅ **Validado con datos reales**: Euro50xde.csv (39,493 filas) procesado exitosamente

**Funcionalidad L10:**
- Procesa archivos L10 (Normalized LL2) con 10 niveles de market depth
- Formato ancho mantenido: 65 columnas (RIC, Domain, Date-Time, L1-L10 Bid/Ask)
- Procesamiento paralelo multi-thread usando mismo pipeline que MBP
- Output: Parquet particionado con batch size de 16,384 mensajes
- Performance: ~41 segundos para 39K filas en 12 CPUs

### Mejoras Sugeridas

1. **Multiple Providers**: Abstraer lógica de LSEG a trait/interface
2. **Schema Validation**: Validar contra definiciones conocidas
3. **Type Casting**: Opción para castear columnas a tipos apropiados
4. **Resumable Processing**: Checkpoint para resumir si falla
5. **Multi-file Input**: Procesar directorios enteros
6. **Compression**: Comprimir Parquet output (actualmente sin compresión)
7. **Configuración Avanzada**:
   - Tamaño de batch configurable
   - Número de threads configurable
   - Columnas a excluir/incluir
8. **Métricas**: Reportar estadísticas de procesamiento
9. **Testing**: Aumentar coverage (especialmente edge cases)
10. **Documentación**: Ejemplos de uso con datos reales

---

## 13. Preguntas Frecuentes (para IA)

### Q1: ¿Por qué Rust + Python en lugar de solo Python?
**A**:
- **Performance**: Parsing y procesamiento de datos es CPU-intensive
- **Polars**: Librería Rust más rápida que pandas
- **Concurrencia**: Rust maneja threads de forma más segura y eficiente
- **UX**: Python CLI es más familiar para usuarios de data science

### Q2: ¿Por qué bounded channels en lugar de unbounded?
**A**:
- **Memoria**: Evita acumular millones de mensajes en memoria
- **Backpressure**: Reader se bloquea si parsers van lentos
- **Balance**: 2*CPUs es un buen balance throughput/memoria

### Q3: ¿Por qué reordenar DataFrames?
**A**:
- **Determinismo**: Output reproducible independiente de timing
- **Debugging**: Facilita comparar outputs
- **Analítica**: Muchas herramientas asumen orden temporal

### Q4: ¿Por qué todos los valores son String?
**A**:
- **Flexibilidad**: No todos los FIDs están documentados
- **Robustez**: Evita errores de parsing de tipos
- **User choice**: Usuario decide qué castear según su uso

### Q5: ¿Cómo escalar a archivos de TB?
**A**:
1. Particionar archivo en chunks más pequeños
2. Procesar cada chunk por separado
3. Usar herramientas como Dask/Spark para orquestar
4. O implementar streaming verdadero en Rust

### Q6: ¿Cómo añadir un nuevo FID?
**A**:
- **No es necesario**: Sistema detecta FIDs automáticamente
- **Para documentación**: Añadir a `lobmp/definitions/fids.py`
- **Para validación**: Implementar validation layer (futuro)

### Q7: ¿Cómo debuggear "parsing thread panicked"?
**A**:
1. Aumentar verbose level: `--verbose DEBUG`
2. Buscar mensaje antes del panic en logs
3. Extraer ese mensaje específico a archivo de prueba
4. Ejecutar `flatten_market_by_price(message)` aisladamente
5. Debuggear con prints o Rust debugger

---

## 14. Comandos Útiles

```bash
# Ejecutar CLI
lobmp input.csv output/ --verbose DEBUG

# Ejecutar como módulo
python -m lobmp input.csv output/

# Ver funciones exportadas
python -c "import lobmp; print(dir(lobmp))"

# Test específico
pytest tests/test_main.py::test_run_integration -v

# Ver dependencias del proyecto
uv tree

# Limpiar builds
rm -rf target/ *.so *.pyd  # Rust/Python artifacts
rm -rf .pytest_cache/ .coverage htmlcov/  # Test artifacts

# Ver tamaño de binarios compilados
ls -lh target/release/*.so

# Benchmark simple
time lobmp large_file.csv output/
```

---

## 15. Recursos Adicionales

### Documentación Externa
- **PyO3**: https://pyo3.rs/
- **Polars**: https://pola.rs/
- **Crossbeam**: https://docs.rs/crossbeam/
- **Maturin**: https://www.maturin.rs/
- **LSEG/Refinitiv**: Documentación oficial de formato de datos

### Repositorio
- **GitHub**: https://github.com/davidricodias/lobmp
- **PyPI**: https://pypi.org/project/lobmp/
- **Issues**: https://github.com/davidricodias/lobmp/issues

### Comunidad
- **Python**: 3.11, 3.12, 3.13 soportadas
- **Rust**: Edition 2021
- **Licencia**: MIT
- **Autor**: José David Rico Días

---

## 16. Glosario de Términos Financieros

- **LOB (Limit Order Book)**: Registro de todas las órdenes de compra/venta pendientes
- **LSEG**: London Stock Exchange Group (antes Refinitiv)
- **Refinitiv**: Proveedor de datos financieros (ahora parte de LSEG)
- **Market By Price (MBP)**: Agregación de órdenes por nivel de precio
- **Market Depth**: Niveles de profundidad del order book
- **L10**: Market depth con 10 niveles de precios
- **FID (Field ID)**: Identificador de campo en mensajes de mercado
- **Tick data**: Datos de trading de alta frecuencia (cada transacción/actualización)
- **BID**: Orden de compra
- **ASK**: Orden de venta
- **Order Book**: Colección de todas las órdenes pendientes
- **GMT Offset**: Diferencia horaria respecto a Greenwich Mean Time

---

## Notas Finales para Agentes IA

Este proyecto es un ejemplo excelente de:
- **Optimización prematura apropiada**: Rust se justifica por el volumen de datos
- **Interop Python/Rust**: Uso profesional de PyO3
- **Concurrencia bien diseñada**: Bounded channels y reordenamiento
- **Buenas prácticas**: Type hints, testing, pre-commit, documentación

**Al trabajar con este código**:
1. Respeta el esquema de concurrencia existente
2. Mantén compatibilidad con la interfaz Python
3. Añade tests para nuevas funcionalidades
4. Documenta TODOs claramente
5. Considera backward compatibility en cambios de API

**Performance es crítico**: Este código procesa archivos de GB/TB, cualquier regresión de performance es inaceptable.

---

**Versión de este documento**: 1.0
**Fecha**: 2024-12-10
**Versión del proyecto**: 0.1.6
