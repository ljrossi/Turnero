"""
Sistema de Programación de Turnos Rotativos 6x2
================================================
- 4 Equipos: A, B, C, D
- 2 técnicos por equipo por turno
- Turnos: Mañana (06:00-14:00), Tarde (14:00-22:00), Noche (22:00-06:00)
- 6 días trabajo, 2 días franco
- Rotación: Mañana → Tarde → Noche → Franco → Franco → ...
- Anomalías por PERSONA y RANGO DE FECHAS
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import os
from datetime import date, timedelta, datetime
import calendar

try:
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors as rl_colors
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER
    REPORTLAB_OK = True
except ImportError:
    REPORTLAB_OK = False


# ─────────────────────────────────────────────
#  CONSTANTES
# ─────────────────────────────────────────────
EQUIPOS = ["A", "B", "C", "D"]
TURNOS = {
    "M": "Mañana  06:00-14:00",
    "T": "Tarde   14:00-22:00",
    "N": "Noche   22:00-06:00",
    "F": "Franco",
}
TURNO_COLORS = {
    "M": "#FFF9C4",
    "T": "#FFE0B2",
    "N": "#BBDEFB",
    "F": "#C8E6C9",
}
TURNO_FG = {
    "M": "#E65100",
    "T": "#BF360C",
    "N": "#0D47A1",
    "F": "#1B5E20",
}

# Color fijo por EQUIPO (se mantiene igual sin importar en qué turno esté ese día)
EQUIPO_COLORS = {
    "A": "#FFF9C4",   # amarillo
    "B": "#FFE0B2",   # naranja claro
    "C": "#BBDEFB",   # celeste
    "D": "#C8E6C9",   # verde claro
}
EQUIPO_FG = {
    "A": "#E65100",
    "B": "#BF360C",
    "C": "#0D47A1",
    "D": "#1B5E20",
}

CICLO_BASE    = ["M"]*6 + ["F"]*2 + ["T"]*6 + ["F"]*2 + ["N"]*6 + ["F"]*2  # 24 días
DESFASE_EQUIPO = {"A": 0, "B": 6, "C": 12, "D": 18}
DATA_FILE = "turnos_data.json"

TIPOS_ANOMALIA = ["Vacaciones", "Enfermedad", "Licencia", "Franco Compensatorio", "Otro"]


# ─────────────────────────────────────────────
#  LÓGICA DE TURNOS
# ─────────────────────────────────────────────
def get_turno_equipo(equipo: str, fecha: date) -> str:
    origen = date(2025, 1, 1)
    delta  = (fecha - origen).days
    idx    = (delta + DESFASE_EQUIPO[equipo]) % 24
    return CICLO_BASE[idx]

def get_equipos_en_turno(fecha: date) -> dict:
    res = {"M": [], "T": [], "N": [], "F": []}
    for eq in EQUIPOS:
        res[get_turno_equipo(eq, fecha)].append(eq)
    return res


# ─────────────────────────────────────────────
#  HELPERS DE ANOMALÍAS  (clave: persona)
# ─────────────────────────────────────────────
def get_anomalia_persona_fecha(datos: dict, equipo: str, idx_tec: int, fecha: date) -> str:
    """
    Devuelve el tipo de anomalía para (equipo, índice técnico 0|1, fecha)
    o "" si no hay.
    Estructura interna:
      datos["anomalias"][equipo][str(idx_tec)][fecha_iso] = tipo
    """
    return (datos.get("anomalias", {})
                 .get(equipo, {})
                 .get(str(idx_tec), {})
                 .get(fecha.isoformat(), ""))

def set_anomalia_rango(datos: dict, equipo: str, idx_tec: int,
                       fecha_ini: date, fecha_fin: date, tipo: str):
    """Registra anomalía para todos los días del rango [ini, fin]."""
    if "anomalias" not in datos:
        datos["anomalias"] = {}
    if equipo not in datos["anomalias"]:
        datos["anomalias"][equipo] = {}
    key = str(idx_tec)
    if key not in datos["anomalias"][equipo]:
        datos["anomalias"][equipo][key] = {}
    d = fecha_ini
    while d <= fecha_fin:
        datos["anomalias"][equipo][key][d.isoformat()] = tipo
        d += timedelta(days=1)

def del_anomalia_rango(datos: dict, equipo: str, idx_tec: int,
                       fecha_ini: date, fecha_fin: date):
    """Elimina anomalías en el rango dado."""
    pool = (datos.get("anomalias", {})
                 .get(equipo, {})
                 .get(str(idx_tec), {}))
    d = fecha_ini
    while d <= fecha_fin:
        pool.pop(d.isoformat(), None)
        d += timedelta(days=1)

def listar_anomalias(datos: dict):
    """
    Retorna lista de dicts con info de cada bloque de anomalía
    (agrupados por persona + tipo + días contiguos).
    """
    result = []
    for eq in EQUIPOS:
        tecs = datos.get("tecnicos", {}).get(eq, ["", ""])
        for idx in range(2):
            pool = (datos.get("anomalias", {})
                         .get(eq, {})
                         .get(str(idx), {}))
            if not pool:
                continue
            fechas_sorted = sorted(pool.keys())
            # agrupar días contiguos del mismo tipo
            bloques = []
            for f_iso in fechas_sorted:
                tipo = pool[f_iso]
                f = date.fromisoformat(f_iso)
                if bloques and bloques[-1]["tipo"] == tipo and \
                   (f - bloques[-1]["fin"]).days == 1:
                    bloques[-1]["fin"] = f
                    bloques[-1]["dias"] += 1
                else:
                    bloques.append({"ini": f, "fin": f, "tipo": tipo, "dias": 1})
            for b in bloques:
                nombre = tecs[idx] if idx < len(tecs) and tecs[idx] else f"Técnico {idx+1}"
                result.append({
                    "equipo": eq,
                    "idx": idx,
                    "nombre": nombre,
                    "ini": b["ini"],
                    "fin": b["fin"],
                    "tipo": b["tipo"],
                    "dias": b["dias"],
                })
    result.sort(key=lambda x: (x["ini"], x["equipo"], x["idx"]))
    return result


# ─────────────────────────────────────────────
#  PERSISTENCIA
# ─────────────────────────────────────────────
def cargar_datos() -> dict:
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            d = json.load(f)
        # migración: estructura vieja sin idx_tec
        if "anomalias" in d:
            for eq in list(d["anomalias"].keys()):
                val = d["anomalias"][eq]
                if val and not isinstance(next(iter(val.values())), dict):
                    # formato viejo: {fecha: tipo} → mover a idx "0"
                    d["anomalias"][eq] = {"0": val, "1": {}}
        return d
    return {"tecnicos": {eq: ["", ""] for eq in EQUIPOS}, "anomalias": {}}

def guardar_datos(datos: dict):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)


# ─────────────────────────────────────────────
#  EXPORTACIÓN PDF
# ─────────────────────────────────────────────
def exportar_pdf(datos: dict, anio: int, mes: int, filepath: str):
    if not REPORTLAB_OK:
        raise ImportError("reportlab no instalado")

    doc = SimpleDocTemplate(filepath, pagesize=landscape(A4),
                            rightMargin=1*cm, leftMargin=1*cm,
                            topMargin=1.5*cm, bottomMargin=1*cm)
    styles = getSampleStyleSheet()
    t_style = ParagraphStyle("Tit", parent=styles["Heading1"],
                             fontSize=15, alignment=TA_CENTER, spaceAfter=4)
    s_style = ParagraphStyle("Sub", parent=styles["Normal"],
                             fontSize=8, alignment=TA_CENTER, spaceAfter=8)
    elements = []
    meses_es = ["Enero","Febrero","Marzo","Abril","Mayo","Junio",
                "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]
    elements.append(Paragraph(
        f"Programación de Turnos Rotativos 6×2 — {meses_es[mes-1]} {anio}", t_style))
    elements.append(Paragraph(
        "Columnas = Mañana / Tarde / Noche / Franco  |  Color de la celda = Equipo  |  ⚠ = Anomalía",
        s_style))

    # Encabezado: una columna por turno (Mañana / Tarde / Noche / Franco)
    TURNO_ORDEN = ["M", "T", "N", "F"]
    TURNO_TITULO = {
        "M": "Mañana\n06:00-14:00",
        "T": "Tarde\n14:00-22:00",
        "N": "Noche\n22:00-06:00",
        "F": "Franco",
    }
    header = ["#", "Fecha", "Día"] + [TURNO_TITULO[t] for t in TURNO_ORDEN]

    table_data = [header]
    col_colors = {}

    _, dias_mes = calendar.monthrange(anio, mes)
    c_map = {eq: rl_colors.HexColor(EQUIPO_COLORS[eq]) for eq in EQUIPOS}
    c_anom = rl_colors.HexColor("#FFCDD2")

    for d in range(1, dias_mes + 1):
        fecha  = date(anio, mes, d)
        nom_dia = ["Lun","Mar","Mié","Jue","Vie","Sáb","Dom"][fecha.weekday()]
        fila   = [str(d), fecha.strftime("%d/%m/%Y"), nom_dia]
        row_idx = len(table_data)

        # Equipo asignado a cada turno ese día
        eq_del_turno = {}
        for eq in EQUIPOS:
            eq_del_turno[get_turno_equipo(eq, fecha)] = eq

        for col_idx, turno in enumerate(TURNO_ORDEN, start=3):
            eq = eq_del_turno.get(turno)
            tecs = datos["tecnicos"].get(eq, ["—", "—"]) if eq else ["—", "—"]
            a0 = get_anomalia_persona_fecha(datos, eq, 0, fecha) if eq else ""
            a1 = get_anomalia_persona_fecha(datos, eq, 1, fecha) if eq else ""

            linea_t0 = f"{'⚠ '+a0[:4] if a0 else '✓'}"
            linea_t1 = f"{'⚠ '+a1[:4] if a1 else '✓'}"
            texto = f"Eq {eq}\n{tecs[0][:8] if tecs[0] else '—'}: {linea_t0}\n{tecs[1][:8] if tecs[1] else '—'}: {linea_t1}"
            fila.append(texto)

            if a0 or a1:
                col_colors[(row_idx, col_idx)] = c_anom
            elif eq:
                col_colors[(row_idx, col_idx)] = c_map.get(eq, rl_colors.white)
            else:
                col_colors[(row_idx, col_idx)] = rl_colors.HexColor("#ECEFF1")

        table_data.append(fila)

    col_widths = [0.9*cm, 2.2*cm, 1.2*cm] + [5.5*cm]*4
    t = Table(table_data, colWidths=col_widths, repeatRows=1)
    style_cmds = [
        ("BACKGROUND", (0,0), (-1,0), rl_colors.HexColor("#263238")),
        ("TEXTCOLOR",  (0,0), (-1,0), rl_colors.white),
        ("FONTNAME",   (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",   (0,0), (-1,0), 8),
        ("FONTSIZE",   (0,1), (-1,-1), 7),
        ("ALIGN",      (0,0), (-1,-1), "CENTER"),
        ("VALIGN",     (0,0), (-1,-1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0,1),(2,-1), [rl_colors.white, rl_colors.HexColor("#F5F5F5")]),
        ("GRID",       (0,0), (-1,-1), 0.4, rl_colors.HexColor("#B0BEC5")),
        ("BOX",        (0,0), (-1,-1), 1,   rl_colors.HexColor("#607D8B")),
        ("ROWHEIGHT",  (0,1), (-1,-1), 0.9*cm),
    ]
    for (r,c), color in col_colors.items():
        style_cmds.append(("BACKGROUND", (c,r), (c,r), color))
    t.setStyle(TableStyle(style_cmds))
    elements.append(t)

    # Leyenda de anomalías
    elements.append(Spacer(1, 0.4*cm))
    bloques = listar_anomalias(datos)
    # filtrar solo los del mes
    bloques_mes = [b for b in bloques
                   if b["fin"].year == anio and b["fin"].month == mes
                   or b["ini"].year == anio and b["ini"].month == mes]
    if bloques_mes:
        ley_data = [["Técnico", "Equipo", "Desde", "Hasta", "Días", "Tipo"]]
        for b in bloques_mes:
            ley_data.append([b["nombre"], f"Eq {b['equipo']}",
                             b["ini"].strftime("%d/%m/%Y"),
                             b["fin"].strftime("%d/%m/%Y"),
                             str(b["dias"]), b["tipo"]])
        lt = Table(ley_data, colWidths=[4*cm,2*cm,2.5*cm,2.5*cm,1.5*cm,4*cm])
        lt.setStyle(TableStyle([
            ("BACKGROUND", (0,0),(-1,0), rl_colors.HexColor("#ECEFF1")),
            ("FONTNAME",   (0,0),(-1,0), "Helvetica-Bold"),
            ("FONTSIZE",   (0,0),(-1,-1), 7),
            ("GRID",       (0,0),(-1,-1), 0.3, rl_colors.HexColor("#90A4AE")),
            ("ALIGN",      (0,0),(-1,-1), "CENTER"),
            ("BACKGROUND", (0,1),(-1,-1), rl_colors.HexColor("#FFEBEE")),
        ]))
        elements.append(Paragraph("<b>Resumen de anomalías del mes:</b>",
                                  ParagraphStyle("sm", fontSize=8, spaceAfter=3)))
        elements.append(lt)

    doc.build(elements)


# ─────────────────────────────────────────────
#  INTERFAZ GRÁFICA
# ─────────────────────────────────────────────
class AppTurnos:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Sistema de Turnos Rotativos 6×2")
        self.root.configure(bg="#1C2833")
        self.root.geometry("1260x780")
        self.root.minsize(950, 620)

        self.datos = cargar_datos()
        self.mes_actual  = tk.IntVar(value=date.today().month)
        self.anio_actual = tk.IntVar(value=date.today().year)

        self._build_ui()
        self.actualizar_calendario()

    # ──────────────────────────────────────
    def _build_ui(self):
        top = tk.Frame(self.root, bg="#17202A", pady=7)
        top.pack(fill="x")
        tk.Label(top, text="⚙  SISTEMA DE TURNOS ROTATIVOS 6×2",
                 font=("Consolas",14,"bold"), bg="#17202A", fg="#00BCD4").pack(side="left", padx=16)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TNotebook", background="#1C2833", borderwidth=0)
        style.configure("TNotebook.Tab", background="#263238", foreground="#90A4AE",
                        padding=[12,5], font=("Consolas",10,"bold"))
        style.map("TNotebook.Tab",
                  background=[("selected","#00BCD4")],
                  foreground=[("selected","#17202A")])

        nb = ttk.Notebook(self.root)
        nb.pack(fill="both", expand=True, padx=8, pady=8)

        self.tab_cal      = tk.Frame(nb, bg="#1C2833")
        self.tab_personal = tk.Frame(nb, bg="#1C2833")
        self.tab_anom     = tk.Frame(nb, bg="#1C2833")
        self.tab_hoy      = tk.Frame(nb, bg="#1C2833")

        nb.add(self.tab_cal,      text="  📅  Calendario  ")
        nb.add(self.tab_personal, text="  👷  Personal  ")
        nb.add(self.tab_anom,     text="  ⚠️  Anomalías  ")
        nb.add(self.tab_hoy,      text="  🕐  Turno Actual  ")

        self._build_tab_calendario()
        self._build_tab_personal()
        self._build_tab_anomalias()
        self._build_tab_hoy()

    # ── CALENDARIO ────────────────────────
    def _build_tab_calendario(self):
        f = self.tab_cal

        nav = tk.Frame(f, bg="#263238", pady=6)
        nav.pack(fill="x", padx=4, pady=(4,0))

        tk.Button(nav, text="◀", command=self._mes_anterior,
                  bg="#37474F", fg="white", font=("Consolas",12,"bold"),
                  relief="flat", padx=10, cursor="hand2").pack(side="left", padx=4)

        self.lbl_mes = tk.Label(nav, text="", font=("Consolas",13,"bold"),
                                bg="#263238", fg="#00BCD4", width=22)
        self.lbl_mes.pack(side="left", padx=6)

        tk.Button(nav, text="▶", command=self._mes_siguiente,
                  bg="#37474F", fg="white", font=("Consolas",12,"bold"),
                  relief="flat", padx=10, cursor="hand2").pack(side="left", padx=4)

        tk.Label(nav, text="  Año:", bg="#263238", fg="#B0BEC5",
                 font=("Consolas",10)).pack(side="left", padx=(16,2))
        tk.Spinbox(nav, from_=2024, to=2040, textvariable=self.anio_actual,
                   width=6, font=("Consolas",11), bg="#37474F", fg="white",
                   command=self.actualizar_calendario,
                   buttonbackground="#546E7A").pack(side="left")

        tk.Button(nav, text="🖨  Exportar PDF", command=self._exportar_pdf,
                  bg="#00897B", fg="white", font=("Consolas",10,"bold"),
                  relief="flat", padx=12, pady=3, cursor="hand2").pack(side="right", padx=8)

        # Leyenda
        ley = tk.Frame(f, bg="#1C2833")
        ley.pack(fill="x", padx=8, pady=4)
        for eq in EQUIPOS:
            tk.Label(ley, text=f"  Equipo {eq}  ",
                     bg=EQUIPO_COLORS[eq], fg=EQUIPO_FG[eq],
                     font=("Consolas",9,"bold"), relief="ridge",
                     padx=4, pady=2).pack(side="left", padx=3)
        tk.Label(ley, text="  ⚠ Anomalía  ",
                 bg="#FFCDD2", fg="#B71C1C",
                 font=("Consolas",9,"bold"), relief="ridge",
                 padx=4, pady=2).pack(side="left", padx=3)

        # ── Contenedor canvas con scroll (permite colorear celda a celda) ──
        wrap = tk.Frame(f, bg="#1C2833")
        wrap.pack(fill="both", expand=True, padx=4, pady=4)

        vsb = ttk.Scrollbar(wrap, orient="vertical")
        vsb.pack(side="right", fill="y")
        hsb = ttk.Scrollbar(wrap, orient="horizontal")
        hsb.pack(side="bottom", fill="x")

        self.cal_canvas = tk.Canvas(wrap, bg="#1C2833",
                                    yscrollcommand=vsb.set,
                                    xscrollcommand=hsb.set,
                                    highlightthickness=0)
        self.cal_canvas.pack(side="left", fill="both", expand=True)
        vsb.config(command=self.cal_canvas.yview)
        hsb.config(command=self.cal_canvas.xview)

        # Frame interior donde se colocan todas las celdas
        self.cal_inner = tk.Frame(self.cal_canvas, bg="#1C2833")
        self._cal_window = self.cal_canvas.create_window(
            (0, 0), window=self.cal_inner, anchor="nw")

        def _on_inner_configure(event):
            self.cal_canvas.configure(
                scrollregion=self.cal_canvas.bbox("all"))
        self.cal_inner.bind("<Configure>", _on_inner_configure)

        # Scroll con rueda del mouse
        def _on_mousewheel(event):
            self.cal_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        self.cal_canvas.bind_all("<MouseWheel>", _on_mousewheel)

    # ── PERSONAL ──────────────────────────
    def _build_tab_personal(self):
        f = self.tab_personal
        tk.Label(f, text="Asignación de Técnicos por Equipo",
                 font=("Consolas",13,"bold"), bg="#1C2833", fg="#00BCD4").pack(pady=12)

        self.entries_tec = {}
        for eq in EQUIPOS:
            row = tk.Frame(f, bg="#263238", padx=10, pady=8)
            row.pack(fill="x", padx=40, pady=5)
            tk.Label(row, text=f"Equipo  {eq}", font=("Consolas",12,"bold"),
                     bg="#263238", fg="#00BCD4", width=12).pack(side="left")
            self.entries_tec[eq] = []
            for i in range(2):
                tk.Label(row, text=f"Técnico {i+1}:", bg="#263238", fg="#B0BEC5",
                         font=("Consolas",10)).pack(side="left", padx=(20,4))
                e = tk.Entry(row, font=("Consolas",11), width=22,
                             bg="#37474F", fg="white", insertbackground="white",
                             relief="flat", bd=4)
                e.insert(0, self.datos["tecnicos"].get(eq, ["",""])[i])
                e.pack(side="left", padx=(0,12))
                self.entries_tec[eq].append(e)

        tk.Button(f, text="💾  Guardar Personal", command=self._guardar_personal,
                  bg="#1565C0", fg="white", font=("Consolas",11,"bold"),
                  relief="flat", padx=20, pady=8, cursor="hand2").pack(pady=20)

    # ── ANOMALÍAS (nueva versión) ──────────
    def _build_tab_anomalias(self):
        f = self.tab_anom

        tk.Label(f, text="Registro de Anomalías por Persona y Rango de Fechas",
                 font=("Consolas",12,"bold"), bg="#1C2833", fg="#FF8A65").pack(pady=(10,4))

        # ── Panel de carga ──
        panel = tk.LabelFrame(f, text=" Nueva Anomalía ",
                              bg="#263238", fg="#FF8A65",
                              font=("Consolas",10,"bold"),
                              padx=14, pady=10, relief="ridge", bd=2)
        panel.pack(fill="x", padx=20, pady=6)

        # Fila 1: Equipo + Técnico
        r1 = tk.Frame(panel, bg="#263238")
        r1.pack(fill="x", pady=3)

        tk.Label(r1, text="Equipo:", bg="#263238", fg="#B0BEC5",
                 font=("Consolas",10)).pack(side="left", padx=(0,4))
        self.cb_eq_anom = ttk.Combobox(r1, values=EQUIPOS, width=5,
                                        font=("Consolas",11), state="readonly")
        self.cb_eq_anom.current(0)
        self.cb_eq_anom.pack(side="left", padx=(0,16))
        self.cb_eq_anom.bind("<<ComboboxSelected>>", self._on_eq_anom_change)

        tk.Label(r1, text="Técnico:", bg="#263238", fg="#B0BEC5",
                 font=("Consolas",10)).pack(side="left", padx=(0,4))
        self.cb_tec_anom = ttk.Combobox(r1, values=["Técnico 1","Técnico 2"],
                                         width=22, font=("Consolas",11), state="readonly")
        self.cb_tec_anom.current(0)
        self.cb_tec_anom.pack(side="left", padx=(0,16))

        tk.Label(r1, text="Tipo:", bg="#263238", fg="#B0BEC5",
                 font=("Consolas",10)).pack(side="left", padx=(0,4))
        self.cb_tipo_anom = ttk.Combobox(r1, values=TIPOS_ANOMALIA, width=22,
                                          font=("Consolas",11), state="readonly")
        self.cb_tipo_anom.current(0)
        self.cb_tipo_anom.pack(side="left")

        # Fila 2: Rango de fechas
        r2 = tk.Frame(panel, bg="#263238")
        r2.pack(fill="x", pady=3)

        tk.Label(r2, text="Desde (dd/mm/aaaa):", bg="#263238", fg="#B0BEC5",
                 font=("Consolas",10)).pack(side="left", padx=(0,4))
        self.ent_fecha_ini = tk.Entry(r2, font=("Consolas",11), width=13,
                                      bg="#37474F", fg="white", insertbackground="white",
                                      relief="flat", bd=4)
        self.ent_fecha_ini.insert(0, date.today().strftime("%d/%m/%Y"))
        self.ent_fecha_ini.pack(side="left", padx=(0,24))

        tk.Label(r2, text="Hasta (dd/mm/aaaa):", bg="#263238", fg="#B0BEC5",
                 font=("Consolas",10)).pack(side="left", padx=(0,4))
        self.ent_fecha_fin = tk.Entry(r2, font=("Consolas",11), width=13,
                                      bg="#37474F", fg="white", insertbackground="white",
                                      relief="flat", bd=4)
        self.ent_fecha_fin.insert(0, date.today().strftime("%d/%m/%Y"))
        self.ent_fecha_fin.pack(side="left", padx=(0,24))

        # Nota informativa
        self.lbl_info_anom = tk.Label(r2, text="", bg="#263238", fg="#80CBC4",
                                       font=("Consolas",9))
        self.lbl_info_anom.pack(side="left", padx=8)

        # Botones
        r3 = tk.Frame(panel, bg="#263238")
        r3.pack(fill="x", pady=(6,2))

        tk.Button(r3, text="➕  Registrar Anomalía", command=self._agregar_anomalia,
                  bg="#E65100", fg="white", font=("Consolas",10,"bold"),
                  relief="flat", padx=12, pady=4, cursor="hand2").pack(side="left", padx=(0,12))

        tk.Button(r3, text="🗑  Eliminar seleccionada", command=self._eliminar_anomalia,
                  bg="#B71C1C", fg="white", font=("Consolas",10,"bold"),
                  relief="flat", padx=12, pady=4, cursor="hand2").pack(side="left")

        tk.Label(r3, text="  (Seleccionar fila en la lista para eliminar)",
                 bg="#263238", fg="#546E7A", font=("Consolas",9)).pack(side="left", padx=10)

        # ── Lista de anomalías ──
        cols_a = ("Técnico", "Equipo", "Desde", "Hasta", "Días hábiles en turno", "Tipo")
        self.tree_anom = ttk.Treeview(f, columns=cols_a, show="headings",
                                       style="Turnos.Treeview", height=14)
        anchos = [200, 80, 110, 110, 180, 160]
        for c, w in zip(cols_a, anchos):
            self.tree_anom.heading(c, text=c)
            self.tree_anom.column(c, width=w, anchor="center")

        vsb2 = ttk.Scrollbar(f, orient="vertical", command=self.tree_anom.yview)
        self.tree_anom.configure(yscrollcommand=vsb2.set)
        self.tree_anom.pack(side="left", fill="both", expand=True, padx=(20,0), pady=6)
        vsb2.pack(side="left", fill="y", pady=6)

        self._refrescar_lista_tecnicos()
        self._refrescar_anomalias()

    def _on_eq_anom_change(self, event=None):
        """Actualiza el combobox de técnicos al cambiar equipo."""
        self._refrescar_lista_tecnicos()

    def _refrescar_lista_tecnicos(self):
        eq = self.cb_eq_anom.get()
        tecs = self.datos["tecnicos"].get(eq, ["",""])
        opciones = []
        for i, t in enumerate(tecs):
            opciones.append(f"Técnico {i+1}: {t}" if t else f"Técnico {i+1}")
        self.cb_tec_anom["values"] = opciones
        self.cb_tec_anom.current(0)

    def _agregar_anomalia(self):
        eq   = self.cb_eq_anom.get()
        idx  = self.cb_tec_anom.current()   # 0 o 1
        tipo = self.cb_tipo_anom.get()
        try:
            f_ini = datetime.strptime(self.ent_fecha_ini.get().strip(), "%d/%m/%Y").date()
            f_fin = datetime.strptime(self.ent_fecha_fin.get().strip(), "%d/%m/%Y").date()
        except ValueError:
            messagebox.showerror("Error", "Fecha inválida. Use dd/mm/aaaa")
            return
        if f_fin < f_ini:
            messagebox.showerror("Error", "La fecha final debe ser ≥ fecha inicial.")
            return

        # Contar días que son turno de trabajo (no franco) para informar
        dias_total = (f_fin - f_ini).days + 1
        dias_turno = sum(1 for i in range(dias_total)
                         if get_turno_equipo(eq, f_ini + timedelta(days=i)) != "F")

        nombre = self.datos["tecnicos"].get(eq, ["",""])[idx] or f"Técnico {idx+1}"
        set_anomalia_rango(self.datos, eq, idx, f_ini, f_fin, tipo)
        guardar_datos(self.datos)
        self._refrescar_anomalias()
        self.actualizar_calendario()

        self.lbl_info_anom.config(
            text=f"✓ {dias_total} días registrados ({dias_turno} con turno de trabajo)")
        messagebox.showinfo("Anomalía registrada",
            f"Técnico: {nombre}  (Equipo {eq})\n"
            f"Tipo: {tipo}\n"
            f"Desde: {f_ini.strftime('%d/%m/%Y')}  Hasta: {f_fin.strftime('%d/%m/%Y')}\n"
            f"Total: {dias_total} días  |  Con turno: {dias_turno} días")

    def _eliminar_anomalia(self):
        sel = self.tree_anom.selection()
        if not sel:
            messagebox.showwarning("Atención", "Seleccione una fila para eliminar.")
            return
        vals = self.tree_anom.item(sel[0])["values"]
        # vals: (nombre, equipo_str, desde, hasta, dias_turno, tipo)
        eq_str = str(vals[1]).replace("Eq ", "").strip()
        try:
            f_ini = datetime.strptime(str(vals[2]), "%d/%m/%Y").date()
            f_fin = datetime.strptime(str(vals[3]), "%d/%m/%Y").date()
        except Exception:
            return
        nombre = str(vals[0])
        # buscar idx por nombre
        tecs = self.datos["tecnicos"].get(eq_str, ["",""])
        idx = 0
        for i, t in enumerate(tecs):
            if t and t in nombre:
                idx = i
                break
        del_anomalia_rango(self.datos, eq_str, idx, f_ini, f_fin)
        guardar_datos(self.datos)
        self._refrescar_anomalias()
        self.actualizar_calendario()

    def _refrescar_anomalias(self):
        for item in self.tree_anom.get_children():
            self.tree_anom.delete(item)
        bloques = listar_anomalias(self.datos)
        for b in bloques:
            # contar días con turno (no franco)
            total = (b["fin"] - b["ini"]).days + 1
            dias_turno = sum(1 for i in range(total)
                             if get_turno_equipo(b["equipo"],
                                                  b["ini"] + timedelta(days=i)) != "F")
            self.tree_anom.insert("", "end", values=(
                b["nombre"],
                f"Eq {b['equipo']}",
                b["ini"].strftime("%d/%m/%Y"),
                b["fin"].strftime("%d/%m/%Y"),
                f"{b['dias']} días ({dias_turno} con turno)",
                b["tipo"],
            ))

    # ── HOY ───────────────────────────────
    def _build_tab_hoy(self):
        f = self.tab_hoy
        hoy = date.today()
        tk.Label(f, text=f"Turno Actual  —  {hoy.strftime('%A %d de %B de %Y').title()}",
                 font=("Consolas",13,"bold"), bg="#1C2833", fg="#00BCD4").pack(pady=12)

        frame_t = tk.Frame(f, bg="#1C2833")
        frame_t.pack(pady=8)

        for turno_letra, eq_lista in get_equipos_en_turno(hoy).items():
            if not eq_lista:
                continue
            col = tk.Frame(frame_t, bg=TURNO_COLORS[turno_letra],
                           padx=18, pady=14, relief="ridge", bd=2)
            col.pack(side="left", padx=8, ipadx=4)
            tk.Label(col, text=TURNOS[turno_letra],
                     font=("Consolas",10,"bold"),
                     bg=TURNO_COLORS[turno_letra], fg=TURNO_FG[turno_letra]).pack(pady=(0,6))
            for eq in eq_lista:
                tecs = self.datos["tecnicos"].get(eq, ["—","—"])
                tk.Label(col, text=f"Equipo {eq}",
                         font=("Consolas",10,"bold"),
                         bg=TURNO_COLORS[turno_letra], fg=TURNO_FG[turno_letra]).pack()
                for i, tec in enumerate(tecs):
                    a = get_anomalia_persona_fecha(self.datos, eq, i, hoy)
                    txt  = f"• {tec or '(sin asignar)'}"
                    color = TURNO_FG[turno_letra]
                    if a:
                        txt  += f"  ⚠ {a}"
                        color = "#D32F2F"
                    tk.Label(col, text=txt, font=("Consolas",9),
                             bg=TURNO_COLORS[turno_letra], fg=color).pack(anchor="w")
                tk.Label(col, text="", bg=TURNO_COLORS[turno_letra]).pack()

        tk.Label(f, text="Próximos 7 días", font=("Consolas",11,"bold"),
                 bg="#1C2833", fg="#B0BEC5").pack(pady=(14,4))
        prox = tk.Frame(f, bg="#1C2833")
        prox.pack()
        for d in range(7):
            dia   = hoy + timedelta(days=d)
            eq_t  = get_equipos_en_turno(dia)
            resumen = "  ".join(f"{k}:{','.join(v)}" for k,v in eq_t.items() if v)
            # anomalías del día
            anoms = []
            for eq in EQUIPOS:
                tecs = self.datos["tecnicos"].get(eq, ["",""])
                for i, t in enumerate(tecs):
                    a = get_anomalia_persona_fecha(self.datos, eq, i, dia)
                    if a:
                        anoms.append(f"⚠{t or f'T{i+1}'}")
            anom_txt = "  " + " ".join(anoms) if anoms else ""
            tk.Label(prox,
                     text=f"  {dia.strftime('%a %d/%m')}  {resumen}{anom_txt}  ",
                     font=("Consolas",9),
                     bg="#263238", fg="#FFCDD2" if anoms else "#ECEFF1",
                     relief="flat", pady=3, padx=6).pack(fill="x", pady=1)

    # ── ACTUALIZAR CALENDARIO ─────────────
    def actualizar_calendario(self):
        mes  = self.mes_actual.get()
        anio = self.anio_actual.get()
        MESES = ["Enero","Febrero","Marzo","Abril","Mayo","Junio",
                 "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]
        self.lbl_mes.config(text=f"  {MESES[mes-1]}  {anio}  ")

        # Borrar celdas anteriores
        for w in self.cal_inner.winfo_children():
            w.destroy()

        hoy = date.today()
        _, dias_mes = calendar.monthrange(anio, mes)

        # Anchos de columna (px)
        W_NUM   = 36
        W_FECHA = 96
        W_DIA   = 44
        W_EQ    = 185   # por equipo
        H_HDR   = 36    # alto encabezado
        H_ROW   = 34    # alto fila normal

        COL_HDR_BG = "#263238"
        COL_HDR_FG = "#00BCD4"
        COL_FIX_BG = "#1E272E"   # fondo columnas fijas (nro, fecha, día)
        COL_FIX_FG = "#B0BEC5"
        COL_HOY_BG = "#1A237E"
        COL_HOY_FG = "#FFFFFF"
        COL_ANOM   = "#FFCDD2"
        COL_ANOM_FG= "#B71C1C"
        FONT_HDR   = ("Consolas", 9, "bold")
        FONT_CELL  = ("Consolas", 9)
        FONT_TURNO = ("Consolas", 9, "bold")

        def celda(parent, row, col, texto, bg, fg, font=FONT_CELL,
                  w=None, h=H_ROW, anchor="center", wrap=0):
            """Crea un Label como celda de grilla."""
            lbl = tk.Label(parent, text=texto, bg=bg, fg=fg, font=font,
                           width=0, relief="flat", anchor=anchor,
                           padx=4, pady=0, wraplength=wrap)
            lbl.grid(row=row, column=col, sticky="nsew", padx=1, pady=1)
            return lbl

        # ── Fila de encabezados ──
        tecs_por_eq = {eq: self.datos["tecnicos"].get(eq, ["",""])
                       for eq in EQUIPOS}

        TURNO_ORDEN  = ["M", "T", "N", "F"]
        TURNO_NOMBRE = {"M": "🌅 Mañana", "T": "🌇 Tarde",
                        "N": "🌙 Noche",  "F": "🏖 Franco"}
        TURNO_HORA   = {"M": "06:00-14:00", "T": "14:00-22:00",
                        "N": "22:00-06:00", "F": ""}

        encabezados_fijos = [("#", W_NUM), ("Fecha", W_FECHA), ("Día", W_DIA)]
        for col_idx, (txt, w) in enumerate(encabezados_fijos):
            celda(self.cal_inner, 0, col_idx, txt,
                  COL_HDR_BG, COL_HDR_FG, FONT_HDR, w=w, h=H_HDR)
            self.cal_inner.grid_columnconfigure(col_idx, minsize=w)

        for t_idx, turno in enumerate(TURNO_ORDEN):
            col = t_idx + 3
            hora = TURNO_HORA[turno]
            txt_hdr = f"{TURNO_NOMBRE[turno]}\n{hora}" if hora else TURNO_NOMBRE[turno]
            lbl = tk.Label(self.cal_inner, text=txt_hdr,
                           bg=TURNO_COLORS[turno], fg=TURNO_FG[turno], font=FONT_HDR,
                           justify="center", relief="flat", padx=4, pady=4)
            lbl.grid(row=0, column=col, sticky="nsew", padx=1, pady=1)
            self.cal_inner.grid_columnconfigure(col, minsize=W_EQ)

        self.cal_inner.grid_rowconfigure(0, minsize=H_HDR)

        DIAS_ES = ["Lun","Mar","Mié","Jue","Vie","Sáb","Dom"]

        for d in range(1, dias_mes + 1):
            row  = d          # fila 0 = encabezado
            fecha = date(anio, mes, d)
            nom_dia = DIAS_ES[fecha.weekday()]
            es_hoy  = (fecha == hoy)
            es_finde = fecha.weekday() >= 5

            self.cal_inner.grid_rowconfigure(row, minsize=H_ROW)

            # Color de fondo para columnas fijas
            if es_hoy:
                bg_fix, fg_fix = COL_HOY_BG, COL_HOY_FG
            elif es_finde:
                bg_fix, fg_fix = "#263238", "#80CBC4"
            else:
                bg_fix = "#1E272E" if d % 2 == 0 else "#212F3C"
                fg_fix = "#B0BEC5"

            # Celdas fijas: número, fecha, día
            celda(self.cal_inner, row, 0, str(d),
                  bg_fix, fg_fix, FONT_CELL)
            celda(self.cal_inner, row, 1, fecha.strftime("%d/%m/%Y"),
                  bg_fix, fg_fix, FONT_CELL)
            celda(self.cal_inner, row, 2, nom_dia,
                  bg_fix, fg_fix,
                  ("Consolas", 9, "bold") if es_finde else FONT_CELL)

            # Qué equipo cae en cada turno ese día (siempre 1 equipo por turno)
            eq_del_turno = {}
            for eq in EQUIPOS:
                eq_del_turno[get_turno_equipo(eq, fecha)] = eq

            # Celdas de turno — cada una con su propio color fijo
            for t_idx, turno in enumerate(TURNO_ORDEN):
                col = t_idx + 3
                eq  = eq_del_turno.get(turno)
                tecs = tecs_por_eq.get(eq, ["", ""])
                a0   = get_anomalia_persona_fecha(self.datos, eq, 0, fecha) if eq else ""
                a1   = get_anomalia_persona_fecha(self.datos, eq, 1, fecha) if eq else ""

                hay_anom = bool(a0 or a1)

                if es_hoy:
                    bg_cel = COL_HOY_BG
                    fg_cel = COL_HOY_FG
                elif hay_anom:
                    bg_cel = COL_ANOM
                    fg_cel = COL_ANOM_FG
                elif eq:
                    bg_cel = EQUIPO_COLORS[eq]
                    fg_cel = EQUIPO_FG[eq]
                else:
                    bg_cel = "#37474F"
                    fg_cel = "#B0BEC5"

                # Texto de la celda
                def estado(nombre, anom):
                    n = (nombre[:10] if nombre else "—")
                    if anom:
                        return f"⚠ {n}: {anom[:4].upper()}"
                    return f"✓ {n}"

                if eq is None:
                    lineas = ["—"]
                elif hay_anom:
                    lineas = [f"Equipo {eq}",
                              estado(tecs[0] if len(tecs)>0 else "", a0),
                              estado(tecs[1] if len(tecs)>1 else "", a1)]
                else:
                    lineas = [f"Equipo {eq}"]
                    if tecs[0]: lineas.append(f"✓ {tecs[0][:12]}")
                    if tecs[1]: lineas.append(f"✓ {tecs[1][:12]}")

                txt_cel = "\n".join(lineas)

                lbl = tk.Label(self.cal_inner, text=txt_cel,
                               bg=bg_cel, fg=fg_cel,
                               font=FONT_TURNO if not hay_anom else FONT_CELL,
                               justify="center", relief="flat",
                               padx=4, pady=2, wraplength=W_EQ - 10)
                lbl.grid(row=row, column=col, sticky="nsew", padx=1, pady=1)

    # ── NAVEGACIÓN ────────────────────────
    def _mes_anterior(self):
        m, a = self.mes_actual.get(), self.anio_actual.get()
        self.mes_actual.set(12 if m == 1 else m-1)
        if m == 1: self.anio_actual.set(a-1)
        self.actualizar_calendario()

    def _mes_siguiente(self):
        m, a = self.mes_actual.get(), self.anio_actual.get()
        self.mes_actual.set(1 if m == 12 else m+1)
        if m == 12: self.anio_actual.set(a+1)
        self.actualizar_calendario()

    # ── GUARDAR PERSONAL ──────────────────
    def _guardar_personal(self):
        for eq in EQUIPOS:
            self.datos["tecnicos"][eq] = [e.get().strip() for e in self.entries_tec[eq]]
        guardar_datos(self.datos)
        messagebox.showinfo("Guardado", "Personal guardado correctamente.")
        self.actualizar_calendario()
        self._refrescar_lista_tecnicos()
        self._refrescar_anomalias()

    # ── EXPORTAR PDF ──────────────────────
    def _exportar_pdf(self):
        mes  = self.mes_actual.get()
        anio = self.anio_actual.get()
        MESES = ["Enero","Febrero","Marzo","Abril","Mayo","Junio",
                 "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]
        fp = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF","*.pdf")],
            initialfile=f"Turnos_{MESES[mes-1]}_{anio}.pdf",
            title="Guardar calendario de turnos")
        if not fp:
            return
        try:
            exportar_pdf(self.datos, anio, mes, fp)
            messagebox.showinfo("PDF generado", f"Archivo guardado:\n{fp}")
        except ImportError:
            messagebox.showerror("Falta librería", "Instale reportlab:\n\npip install reportlab")
        except Exception as ex:
            messagebox.showerror("Error al generar PDF", str(ex))


# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    AppTurnos(root)
    root.mainloop()