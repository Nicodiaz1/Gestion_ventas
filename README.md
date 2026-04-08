# 🍷 Vinoteca — Sistema de Gestión

Sistema de punto de venta y gestión integral para vinotecas.
Desarrollado en Python + PyQt6. Funciona **offline** con SQLite y sincroniza con SQL Server cuando hay red.

---

## ✅ Características

| Módulo | Funcionalidades |
|--------|----------------|
| **🛒 Punto de Venta** | Escaneo de código de barras, búsqueda por nombre, carrito, descuentos, 5 medios de pago |
| **📦 Stock** | Alta de productos (con o sin código), carga de stock por escaneo, alertas de stock bajo, historial |
| **📊 Reportes** | Métricas del día, reportes por período, top productos, ingresos mensuales/anuales, historial completo |
| **☁️ Sincronización** | SQLite local → SQL Server cuando hay red |
| **📈 Power BI** | Exportación de datasets CSV listos para dashboards |

---

## 🚀 Instalación

### Windows
```
instalar_windows.bat
```

### macOS
```bash
bash instalar_mac.sh
```

### Manual
```bash
pip install PyQt6 matplotlib pandas openpyxl pyodbc
python3 main.py
```

---

## 📁 Estructura del proyecto

```
Vinoteca/
├── main.py                  # Punto de entrada
├── config.py                # Configuración global
├── requirements.txt
│
├── db/
│   └── database.py          # SQLite - toda la lógica de datos
│
├── ui/
│   ├── styles.py            # Estilos y paleta de colores
│   ├── main_window.py       # Ventana principal + sidebar
│   ├── pos.py               # Punto de venta
│   ├── stock.py             # Gestión de stock y productos
│   ├── reportes.py          # Reportes y gráficas
│   └── config_panel.py      # Configuración
│
├── sync/
│   ├── sync_manager.py      # Sincronización con SQL Server
│   └── powerbi_export.py    # Exportación CSV para Power BI
│
└── exports/
    └── powerbi/             # Datasets generados (CSV)
```

---

## ⌨️ Atajos de teclado

| Tecla | Acción |
|-------|--------|
| **F2** | Buscar producto por nombre (sin código de barras) |
| **F5** | Ir a Punto de Venta |
| **F6** | Ir a Stock |
| **F7** | Ir a Reportes |
| **F8** | Ir a Configuración |
| **F12** | Confirmar cobro (desde POS) |
| **Escape** | Vaciar carrito |

---

## 💳 Medios de pago soportados

- 💵 Efectivo
- 💳 Débito
- 🏦 Crédito (con número de cuotas)
- 📲 Transferencia bancaria
- 🔲 QR (Mercado Pago u otro)

---

## ☁️ Configurar SQL Server (sincronización)

1. Abrir la app → ⚙️ Configuración → SQL Server
2. Completar: servidor, base de datos, usuario, contraseña
3. Probar conexión
4. Usar el botón **☁️ Sincronizar** en el sidebar

---

## 📊 Conectar Power BI

1. En la app → Reportes → **Exportar a Excel** (o desde terminal: `python3 sync/powerbi_export.py`)
2. Los CSV quedan en `exports/powerbi/`
3. Abrir Power BI Desktop → Obtener datos → Texto/CSV
4. Ver archivo `exports/powerbi/POWER_BI_INSTRUCCIONES.txt`

### Datasets disponibles:
- `ventas.csv` — todas las ventas con año/mes/semana
- `detalle_ventas.csv` — ítems con margen por producto
- `productos.csv` — catálogo con margen %
- `caja_diaria.csv` — cierre por día y medio de pago
- `resumen_mensual.csv` — totales mensuales
- `top_productos.csv` — ranking de más vendidos
- `sin_rotacion.csv` — productos sin ventas en 30+ días
- `movimientos_stock.csv` — historial de entradas/salidas

---

## 🔮 Funcionalidades futuras planeadas

- [ ] Facturación electrónica (AFIP)
- [ ] Cuentas corrientes de clientes
- [ ] Múltiples usuarios con roles
- [ ] Importación de catálogo desde Excel
- [ ] Backup automático
- [ ] App móvil (Android) para tomar pedidos

---

## 📞 Soporte

Ante cualquier problema, revisar:
1. Python 3.10+ instalado
2. Dependencias instaladas: `pip install -r requirements.txt`
3. Base de datos: `python3 -c "from db.database import init_db; init_db()"`
