"""Ventana principal: orquesta controles, tabla y tareas en segundo plano."""
from __future__ import annotations

import os
import queue
import threading
import time
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from ..config import DATA_DIR, DIAS_RETENCION, Settings
from ..database import Repositorio
from ..excel_exporter import exportar_matriz, exportar_resultados
from ..excel_reader import leer_nodos
from ..models import Estado, ParametrosPing
from ..service import MonitorService
from ..utils import es_admin, normalizar_ip
from .history_window import VentanaHistorial
from .list_picker import elegir_lista
from .results_table import TablaResultados
from .scans_window import VentanaEscaneos
from .tracert_window import VentanaTracert
from .worker import Trabajador, es_error_permisos


class VentanaPrincipal(tk.Tk):
    def __init__(self, settings: Settings, repo: Repositorio, service: MonitorService):
        super().__init__()
        self.settings = settings
        self.repo = repo
        self.service = service
        self.trabajador = Trabajador()
        self._ejecutando = False
        self._cancelar = threading.Event()
        self._ventanas: dict = {}          # ventanas secundarias abiertas (una por clave)
        self._exportando = False
        self._proxima_auto = 0.0

        self.title("Monitor de Cámaras - Latencia y Conexión")
        self.geometry("1100x720")
        self._crear_variables()
        self._crear_widgets()
        self.protocol("WM_DELETE_WINDOW", self._cerrar)
        self.after(100, self._sondear_cola)
        self.after(1000, self._tick_auto)
        if not es_admin():
            self.v_status.set(
                "AVISO: no eres administrador. El ping puede fallar. "
                "Abre el programa con 'Ejecutar como administrador'."
            )

    # ------------------------------------------------------------ construccion
    def _crear_variables(self) -> None:
        s = self.settings
        self.v_excel = tk.StringVar(value=s.excel)
        self.v_count = tk.StringVar(value=str(s.count))
        self.v_timeout = tk.StringVar(value=str(s.timeout))
        self.v_conc = tk.StringVar(value=str(s.conc))
        self.v_lento = tk.StringVar(value=str(s.lento))
        self.v_auto = tk.BooleanVar(value=s.auto)
        self.v_auto_min = tk.StringVar(value=str(s.auto_min))
        self.v_filtro = tk.StringVar(value="Todos")
        self.v_buscar = tk.StringVar()
        self.v_status = tk.StringVar(value="Listo.")
        self.v_cont = tk.StringVar()

    def _crear_widgets(self) -> None:
        self._barra_excel()
        self._barra_parametros()
        self._barra_botones()
        self.prog = ttk.Progressbar(self, mode="determinate")
        self.prog.pack(fill="x", padx=8)
        self._barra_filtros()
        self.tabla = TablaResultados(
            self, al_abrir=self._abrir_historial, al_tracert=self._abrir_tracert,
            al_seleccionar=self._actualizar_boton_tracert)
        self.tabla.pack(fill="both", expand=True, padx=8)
        ttk.Label(self, textvariable=self.v_status, relief="sunken", anchor="w").pack(
            fill="x", side="bottom")

    def _barra_excel(self) -> None:
        f = ttk.Frame(self, padding=8)
        f.pack(fill="x")
        ttk.Label(f, text="Excel del listado de cámaras:").pack(side="left")
        ttk.Entry(f, textvariable=self.v_excel).pack(side="left", fill="x", expand=True, padx=6)
        ttk.Button(f, text="Elegir...", command=self._elegir_excel).pack(side="left")

    def _barra_parametros(self) -> None:
        f = ttk.Frame(self, padding=(8, 0))
        f.pack(fill="x")
        for txt, var, ancho in (("Intentos (Pings)", self.v_count, 4), ("Tiempo de espera (s)", self.v_timeout, 5),
                                ("Dispositivos simultáneos", self.v_conc, 6), ("Lento > (ms)", self.v_lento, 6)):
            ttk.Label(f, text=txt).pack(side="left", padx=(0, 3))
            ttk.Entry(f, textvariable=var, width=ancho).pack(side="left", padx=(0, 12))
        ttk.Checkbutton(f, text="Repetir cada", variable=self.v_auto,
                        command=lambda: setattr(self, "_proxima_auto", time.time())).pack(side="left")
        ttk.Entry(f, textvariable=self.v_auto_min, width=4).pack(side="left", padx=3)
        ttk.Label(f, text="min").pack(side="left")

    def _barra_botones(self) -> None:
        f = ttk.Frame(self, padding=8)
        f.pack(fill="x")
        self.btn_run = ttk.Button(f, text="Ejecutar escaneo", command=self._alternar_escaneo)
        self._texto_ejecutar = "Ejecutar escaneo"
        self.btn_run.pack(side="left")
        ttk.Button(f, text="Exportar (Escaneo actual)", command=self._exportar_actual).pack(side="left", padx=6)
        ttk.Button(f, text=f"Exportar historial ({DIAS_RETENCION} dias)",
                   command=self._exportar_mes).pack(side="left")
        ttk.Button(f, text="Ver historial de escaneos", command=self._abrir_escaneos).pack(side="left", padx=6)
        self.btn_tracert = ttk.Button(f, text="Tracert", command=self._abrir_tracert, state="disabled")
        self.btn_tracert.pack(side="left")
        ttk.Button(f, text="Carpeta de datos", command=self._abrir_datos).pack(side="right")

    def _barra_filtros(self) -> None:
        f = ttk.Frame(self, padding=8)
        f.pack(fill="x")
        ttk.Label(f, text="Estado:").pack(side="left")
        cb = ttk.Combobox(f, textvariable=self.v_filtro, state="readonly", width=14,
                          values=("Todos",) + Estado.TODOS)
        cb.pack(side="left", padx=6)
        cb.bind("<<ComboboxSelected>>", lambda e: self._aplicar_filtro())
        ttk.Label(f, text="Buscar:").pack(side="left", padx=(12, 0))
        ent = ttk.Entry(f, textvariable=self.v_buscar, width=28)
        ent.pack(side="left", padx=6)
        ent.bind("<KeyRelease>", lambda e: self._aplicar_filtro())
        ttk.Label(f, textvariable=self.v_cont).pack(side="right")

    # ------------------------------------------------------------ helpers
    def _leer_parametros(self) -> ParametrosPing | None:
        try:
            p = ParametrosPing(
                count=int(self.v_count.get()), timeout=float(self.v_timeout.get()),
                concurrentes=int(self.v_conc.get()), lento_ms=float(self.v_lento.get()))
        except ValueError:
            return None
        if p.count < 1 or p.timeout <= 0 or p.concurrentes < 1:
            return None
        return p

    def _minutos_auto(self) -> int:
        try:
            return max(1, int(self.v_auto_min.get()))
        except ValueError:
            return 15

    def _aplicar_filtro(self) -> None:
        self.tabla.filtrar(self.v_filtro.get(), self.v_buscar.get())

    def _actualizar_contadores(self) -> None:
        c = self.tabla.conteo()
        self.v_cont.set(
            f"Total {len(self.tabla.resultados)} | OK {c[Estado.OK]} | Lento {c[Estado.LENTO]} | "
            f"Sin resp. {c[Estado.SIN_RESPUESTA]} | Sin IP {c[Estado.SIN_IP] + c[Estado.IP_INVALIDA]}")

    def _pedir_ruta(self, nombre: str) -> str:
        return filedialog.asksaveasfilename(
            defaultextension=".xlsx", initialfile=nombre, filetypes=[("Excel", "*.xlsx")])

    # ------------------------------------------------------------ acciones
    def _elegir_excel(self) -> None:
        p = filedialog.askopenfilename(title="Excel de nodos",
                                       filetypes=[("Excel", "*.xlsx *.xlsm")])
        if p:
            self.v_excel.set(p)

    def _abrir_datos(self) -> None:
        try:
            os.startfile(DATA_DIR)  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            messagebox.showinfo("Datos", str(DATA_DIR))

    def _abrir_historial(self, nombre: str, ip: str) -> None:
        if not nombre and not ip:
            return
        self._abrir_unica(("historial", nombre or ip),
                          lambda: VentanaHistorial(self, self.repo, nombre, ip))

    def _alternar_escaneo(self) -> None:
        """Un solo boton: ejecuta, y mientras corre cancela."""
        if self._ejecutando:
            self._cancelar.set()
            self.btn_run.state(["disabled"])
            self.v_status.set("Cancelando escaneo...")
        else:
            self._ejecutar()

    def _actualizar_boton_tracert(self) -> None:
        sel = self.tabla.seleccionado()
        valido = bool(sel and normalizar_ip(sel[1]))
        self.btn_tracert.state(["!disabled"] if valido else ["disabled"])

    def _abrir_tracert(self, nombre: str | None = None, ip: str | None = None) -> None:
        """Abre una ventana de tracert para la camara seleccionada (una por camara)."""
        if ip is None:
            sel = self.tabla.seleccionado()
            if not sel:
                return
            nombre, ip = sel
        norm = normalizar_ip(ip)
        if norm is None:
            messagebox.showinfo("Tracert", "Esta cámara no tiene una IP válida.")
            return
        self._abrir_unica(("tracert", norm),
                          lambda: VentanaTracert(self, nombre or "", norm))

    def _abrir_escaneos(self) -> None:
        self._abrir_unica(("escaneos",),
                          lambda: VentanaEscaneos(self, self.repo, self._ver_escaneo))

    def _abrir_unica(self, clave, crear):
        """Una sola ventana por clave: si ya esta abierta la trae al frente."""
        self._ventanas = {k: w for k, w in self._ventanas.items() if w.winfo_exists()}
        v = self._ventanas.get(clave)
        if v is not None:
            v.deiconify()
            v.lift()
            v.focus_force()
            return v
        v = self._ventanas[clave] = crear()
        return v

    def _ver_escaneo(self, ts: str) -> None:
        """Carga un escaneo guardado en el panel principal."""
        self.tabla.cargar(self.repo.cargar_escaneo(ts))
        self._aplicar_filtro()
        self._actualizar_contadores()
        self.v_status.set(f"Viendo escaneo guardado: {ts}")

    def _ejecutar(self, silencioso: bool = False) -> None:
        if self._ejecutando:
            return
        ruta = self.v_excel.get().strip()
        if not ruta or not os.path.exists(ruta):
            if silencioso:
                self.v_status.set("Auto: archivo Excel no encontrado.")
            else:
                messagebox.showwarning("Excel", "Elige un archivo Excel valido.")
            return
        params = self._leer_parametros()
        if params is None:
            messagebox.showwarning("Parametros", "Revisa los parametros numericos.")
            return
        try:
            nodos = leer_nodos(ruta)
        except Exception as e:  # noqa: BLE001
            msg = f"No se pudo leer el Excel: {e}"
            self.v_status.set(msg) if silencioso else messagebox.showerror("Excel", msg)
            return
        if not nodos:
            self.v_status.set("El Excel no tiene nodos (A = nombre, B = IP, fila 1 = encabezado).")
            return
        self._ejecutando = True
        self._cancelar.clear()
        self.btn_run.config(text="Cancelar escaneo")
        self.prog["value"] = 0
        self.v_status.set(f"Probando {len(nodos)} nodos...")
        self.trabajador.lanzar("ping", self.service.ejecutar, nodos, params,
                               self.trabajador.progreso, Path(ruta).stem, self._cancelar)

    def _exportar_actual(self) -> None:
        res = self.tabla.resultados
        if not res:
            messagebox.showinfo("Exportar", "Primero ejecuta una prueba.")
            return
        ts = res[0].ts
        ruta = self._pedir_ruta(f"resultado_{ts[:10]}_{ts[11:13]}{ts[14:16]}.xlsx")
        if not ruta:
            return
        try:
            exportar_resultados(ruta, res)
            self.v_status.set(f"Exportado: {ruta}")
        except Exception as e:  # noqa: BLE001
            messagebox.showerror("Exportar", str(e))

    def _exportar_mes(self) -> None:
        if self._exportando:
            return
        listas = self.repo.listas()
        if not listas:
            messagebox.showinfo("Exportar", "No hay historial todavia.")
            return
        actual = Path(self.v_excel.get()).stem
        lista = listas[0] if len(listas) == 1 else elegir_lista(
            self, listas, actual if actual in listas else listas[0])
        if lista is None:
            return
        params = self._leer_parametros()
        lento = params.lento_ms if params else 150.0
        ruta = self._pedir_ruta(
            f"historial_{lista or 'sin_lista'}_{DIAS_RETENCION}dias_{datetime.now():%Y-%m-%d}.xlsx")
        if not ruta:
            return
        self._exportando = True
        self.v_status.set("Generando historial (puede tardar unos segundos)...")
        self.trabajador.lanzar("exportar", self._tarea_exportar_mes, ruta, lento, lista)

    def _tarea_exportar_mes(self, ruta: str, lento: float, lista: str) -> str:
        timestamps, filas = self.repo.matriz(lista)
        exportar_matriz(ruta, timestamps, filas, lento)
        return ruta

    # ------------------------------------------------------------ cola de eventos
    def _sondear_cola(self) -> None:
        try:
            while True:
                self._procesar(*self.trabajador.cola.get_nowait())
        except queue.Empty:
            pass
        self.after(100, self._sondear_cola)

    def _procesar(self, tipo: str, tarea: str, dato) -> None:
        if tarea == "ping":
            self._evento_ping(tipo, dato)
        elif tarea == "exportar":
            self._exportando = False
            if tipo == "ok":
                self.v_status.set(f"Exportado: {dato}")
            else:
                self.v_status.set(f"Error al exportar: {dato}")
                messagebox.showerror("Exportar", str(dato))

    def _evento_ping(self, tipo: str, dato) -> None:
        if tipo == "prog":
            hecho, total = dato
            self.prog["maximum"] = max(total, 1)
            self.prog["value"] = hecho
            self.v_status.set(f"Probando... {hecho} / {total} IPs")
            return
        self._ejecutando = False
        self.btn_run.state(["!disabled"])
        self.btn_run.config(text=self._texto_ejecutar)
        self._proxima_auto = time.time() + self._minutos_auto() * 60
        if tipo == "cancel":
            self.prog["value"] = 0
            self.v_status.set("Escaneo cancelado. No se guardó ningún resultado.")
            return
        if tipo == "ok":
            self.prog["value"] = self.prog["maximum"]
            self.tabla.cargar(dato)
            self._aplicar_filtro()
            self._actualizar_contadores()
            v = self._ventanas.get(("escaneos",))      # refresca la lista si esta abierta
            if v is not None and v.winfo_exists():
                v.recargar()            
            self.v_status.set(f"Terminado: {dato[0].ts if dato else ''}")
        else:
            self.v_status.set(f"Error: {dato}")
            if es_error_permisos(dato):
                messagebox.showerror("Permisos", "Ejecuta el programa como administrador.")

    def _tick_auto(self) -> None:
        if self.v_auto.get() and not self._ejecutando and time.time() >= self._proxima_auto:
            self._ejecutar(silencioso=True)
        self.after(1000, self._tick_auto)

    # ------------------------------------------------------------ cierre
    def _cerrar(self) -> None:
        s = self.settings
        s.excel = self.v_excel.get()
        s.auto = self.v_auto.get()
        s.auto_min = self._minutos_auto()
        p = self._leer_parametros()
        if p:
            s.count, s.timeout, s.conc, s.lento = p.count, p.timeout, p.concurrentes, p.lento_ms
        s.guardar()
        self.destroy()
