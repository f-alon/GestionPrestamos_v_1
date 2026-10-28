# 💼 Gestión de Préstamos (GestionPrestamos)

Aplicación de escritorio moderna para Windows desarrollada en **Python 3.10+**, **PySide6 (Qt6)** con estética **Windows Fluent Design (QFluentWidgets)** y persistencia embebida en **SQLite3**.

---

## 🚀 Características Principales

1. **Panel de Control y Métricas (Dashboard):**
   - Tarjetas KPI en tiempo real:
     - 💳 **Capital Prestado:** Total de capital colocado y activo.
     - 📈 **Saldo a Cobrar:** Capital restante + intereses base + mora punitoria.
     - 💵 **Ganancia Estimada:** Intereses proyectados y punitorios acumulados.
     - ⚠️ **Morosos Activos:** Conteo de préstamos actualmente vencidos.
   - Tabla interactiva con ordenamiento multicriterio y código de colores:
     - 🟢 **Verde claro:** Préstamos al día.
     - 🔴 **Rojo tenue:** Préstamos en mora (atrasados).
     - ⚪ **Gris:** Préstamos terminados y cancelados.
   - Búsqueda en tiempo real por texto (nombre, apellido, teléfono o número de ID).
   - Filtros rápidos tipo chips: `[Todos]`, `[Al día]`, `[Con mora]`, `[Terminados]`.
   - Atajo de teclado global: `Ctrl + N` para crear un nuevo préstamo.

2. **Alta de Préstamos con Simulación en Tiempo Real:**
   - Selector inteligente de cliente con autocompletado y botón `+` para crear clientes al vuelo.
   - Panel lateral dinámico con cálculo instantáneo de intereses, fechas y total a cobrar.
   - Cálculo automático de fecha de vencimiento según tipo de plazo (`Días` o `Semanas`) y duración.
   - Validaciones estrictas de montos positivos y fechas consistentes.

3. **Sistema de Alertas y Scoring Crediticio:**
   - 🔴 **Alerta Roja (Riesgo Alto / Moroso):** Si posee un préstamo activo vencido con mora o si más del 20% de sus préstamos cerrados registraron atraso. Banner de advertencia destacado.
   - 🟢 **Badge Verde (Cliente Cumplidor):** Al menos 1 préstamo previo finalizado sin registrar ningún atraso ni punitorios.
   - ⚪ **Badge Neutro (Sin Historial):** Cliente nuevo sin préstamos anteriores registrados.

4. **Gestión de Cobro, Liquidación y WhatsApp:**
   - Desglose contable completo: Capital inicial, tasa de interés pactada, mora acumulada y saldo restante.
   - Registro de abonos parciales y pagos totales con botón rápido "Saldo Total".
   - Integración nativa con WhatsApp Web/Desktop vía `webbrowser` y `urllib.parse` con plantillas automáticas:
     - Mensaje de aviso de vencimiento / mora con liquidación detallada.
     - Confirmación y recibo de pago instantáneo tras registrar un abono.
   - Cierre del préstamo con validación estricta de saldo restante (`<= 0.01`) o condonación explícita asistida.

5. **Exportación y Resguardo de Información:**
   - Exportación de préstamos e historial de amortizaciones a **Microsoft Excel (`.xlsx`)** con estilos y formato contable.
   - Exportación rápida a formato plano **CSV (`.csv`)**.
   - Respaldo instantáneo de la base de datos SQLite con un solo clic (`prestamos_backup_YYYYMMDD_HHMMSS.db`).
   - Acceso directo al directorio de datos del sistema `%LOCALAPPDATA%\GestionPrestamos`.

---

## 📐 Estructura de la Base de Datos (SQLite)

El archivo de base de datos se almacena en:
```
%LOCALAPPDATA%\GestionPrestamos\prestamos.db
```

### Tabla `clientes`
| Campo | Tipo | Restricción | Descripción |
|---|---|---|---|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Identificador único |
| `nombre` | TEXT | NOT NULL | Nombre de pila |
| `apellido` | TEXT | NOT NULL | Apellido |
| `telefono` | TEXT | NOT NULL | Formato internacional sin símbolos (ej: `54911xxxxxxxx`) |
| `email` | TEXT | NULLABLE | Correo electrónico |
| `notas` | TEXT | NULLABLE | Observaciones generales |
| `fecha_alta`| TEXT | NOT NULL | Formato ISO `YYYY-MM-DD HH:MM:SS` |

### Tabla `prestamos`
| Campo | Tipo | Restricción | Descripción |
|---|---|---|---|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Identificador del crédito |
| `cliente_id` | INTEGER | NOT NULL, FK(`clientes.id`) | Cliente titular |
| `monto_prestado` | REAL | NOT NULL | Capital inicial otorgado |
| `porcentaje_interes` | REAL | NOT NULL | Tasa de interés base pactada (ej: `20.0`) |
| `tipo_plazo` | TEXT | NOT NULL | `'DIAS'` o `'SEMANAS'` |
| `duracion_plazo` | INTEGER | NOT NULL | Duración en días o semanas |
| `fecha_inicio` | TEXT | NOT NULL | Formato `YYYY-MM-DD` |
| `fecha_fin` | TEXT | NOT NULL | Formato `YYYY-MM-DD` |
| `tasa_mora_diaria` | REAL | NOT NULL | Recargo punitorio diario (ej: `1.0` = 1% diario) |
| `estado` | TEXT | NOT NULL | `'EN_CURSO'` o `'TERMINADO'` |

### Tabla `pagos`
| Campo | Tipo | Restricción | Descripción |
|---|---|---|---|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Identificador del pago |
| `prestamo_id` | INTEGER | NOT NULL, FK(`prestamos.id`) | Préstamo asociado |
| `monto` | REAL | NOT NULL | Importe abonado |
| `fecha_pago` | TEXT | NOT NULL | Formato `YYYY-MM-DD HH:MM:SS` |
| `metodo_pago` | TEXT | NULLABLE | Efectivo, Transferencia, etc. |
| `comprobante_ref` | TEXT | NULLABLE | Código de comprobante o referencia bancaria |

---

## 🧮 Fórmulas Financieras Aplicadas

1. **Total Base a Devolver:**
   $$\text{total\_base} = \text{monto\_prestado} \times \left(1.0 + \frac{\text{porcentaje\_interes}}{100.0}\right)$$

2. **Cálculo de Días de Atraso:**
   $$\text{dias\_diferencia} = \text{hoy} - \text{fecha\_fin}$$
   $$\text{dias\_atraso} = \begin{cases} \text{dias\_diferencia} & \text{si } \text{estado} == \text{'EN\_CURSO'} \text{ y } \text{dias\_diferencia} > 0 \\ 0 & \text{en cualquier otro caso} \end{cases}$$

3. **Interés Punitorio por Mora:**
   $$\text{saldo\_base\_pendiente} = \max(0.0, \text{total\_base} - \text{total\_abonado})$$
   $$\text{mora\_acumulada} = \text{saldo\_base\_pendiente} \times \left(\frac{\text{tasa\_mora\_diaria}}{100.0}\right) \times \text{dias\_atraso}$$

4. **Saldo Restante Final:**
   $$\text{saldo\_restante} = (\text{total\_base} + \text{mora\_acumulada}) - \text{total\_abonado}$$

---

## 💻 Instalación y Ejecución

### 1. Clonar el repositorio o descargar el código:
```bash
git clone <url-del-repositorio>
cd GestionPrestamos_v_1
```

### 2. Instalar dependencias:
```bash
pip install -r requirements.txt
```

### 3. Iniciar la aplicación:
```bash
python main.py
```

---

## 📦 Empaquetado a Ejecutable Standalone (.exe)

Para generar el ejecutable standalone para Windows sin necesidad de consola de comandos:

1. Ejecutar el script por lotes:
   ```cmd
   build_exe.bat
   ```
   o directamente vía PyInstaller:
   ```cmd
   pyinstaller --noconfirm GestionPrestamos.spec
   ```
2. El archivo `.exe` compilado y listo para distribuir se generará en la carpeta `dist\GestionPrestamos.exe`.

