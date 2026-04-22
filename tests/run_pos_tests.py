import os
import sys
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication
# Asegurar que el root del proyecto está en sys.path (cuando el script se ejecuta desde tests/)
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import ui.pos as pos


def run():
    app = QApplication([])

    # Producto de prueba
    product = {
        'id': 101,
        'nombre': 'Malbec Reserva',
        'precio_venta': 1200.0,
        'stock_actual': 3,
        'codigo_barras': '000101'
    }

    def stub_buscar_por_nombre(texto):
        texto = (texto or "").strip()
        if not texto:
            return []
        if str(product['id']) in texto or product['nombre'].lower() in texto.lower() or 'malb' in texto.lower():
            return [product]
        return []

    def stub_buscar_por_codigo(codigo):
        return product if codigo == product['codigo_barras'] else None

    def stub_obtener_lotes_producto(producto_id):
        if producto_id == product['id']:
            return [{'id': 1001, 'producto_id': product['id'], 'cantidad': 3, 'cosecha': 2019, 'fecha_vencimiento': None}]
        return []

    # Inyectar stubs
    pos.db.buscar_por_nombre = stub_buscar_por_nombre
    pos.db.buscar_por_codigo = stub_buscar_por_codigo
    pos.db.obtener_lotes_producto = stub_obtener_lotes_producto

    carrito = pos.CarritoWidget()

    # Test 1: selección desde el completer
    carrito._actualizar_sugerencias("Malb")
    etiquetas = carrito._completer_model.stringList()
    print("Etiquetas:", etiquetas)
    assert etiquetas, "No se generaron etiquetas"
    etiqueta = etiquetas[0]
    carrito._sugerencia_elegida(etiqueta)
    # Tras elegir una sugerencia debería quedar SOLO el nombre en el campo
    app.processEvents()
    import time
    # Esperar un poco para que el QTimer que libera _completando se ejecute
    time.sleep(0.2)
    app.processEvents()
    assert carrito.scan_input.text().strip() == product['nombre'], "La sugerencia no dejó solo el nombre en el campo"
    # Ahora simular Enter para agregar
    carrito._procesar_escaneo()
    app.processEvents()
    assert len(carrito.carrito) == 1 and carrito.carrito[0].producto_id == product['id'], "Seleccionar sugerencia + Enter no agregó producto al carrito"
    print("Test 1 passed: selección via completer deja el nombre y Enter agrega producto.")

    # Reset
    carrito.carrito.clear()
    carrito._refrescar_tabla()

    # Test 2: pegar etiqueta en scan_input y presionar Enter
    carrito.scan_input.setText(etiqueta)
    carrito._procesar_escaneo()
    app.processEvents()
    assert len(carrito.carrito) == 1 and carrito.carrito[0].producto_id == product['id'], "Procesar escaneo con etiqueta pegada falló"
    print("Test 2 passed: _procesar_escaneo normaliza etiqueta y agrega producto.")

    carrito.carrito.clear()
    carrito._refrescar_tabla()

    # Test 3: escaneo por código de barras
    carrito.scan_input.setText(product['codigo_barras'])
    carrito._procesar_escaneo()
    assert len(carrito.carrito) == 1 and carrito.carrito[0].producto_id == product['id'], "Procesar escaneo por código falló"
    print("Test 3 passed: escaneo por código agrega producto.")

    # Test 4: asignación automática de lote único
    carrito.carrito.clear()
    carrito._refrescar_tabla()
    carrito._agregar_al_carrito(dict(product))
    assert len(carrito.carrito) == 1
    item = carrito.carrito[0]
    assert item.lote_id == 1001 and item.cosecha == 2019, f"Lote no asignado: lote_id={item.lote_id}, cosecha={item.cosecha}"
    print("Test 4 passed: asignación automática de lote único.")

    print("All tests passed.")
    app.exit(0)


if __name__ == "__main__":
    run()
