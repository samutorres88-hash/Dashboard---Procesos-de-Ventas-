# =============================================================================
# DASHBOARD DE PRESUPUESTO — PROCESO DE VENTAS
# Versión definitiva para despliegue en Streamlit Cloud
# =============================================================================
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# =============================================================================
# 🔗 CONEXIÓN A GOOGLE SHEETS
# =============================================================================
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTNbX-TFAWNAvaY_qumrDy0oieF4GhzqJJGV_1vLf7mPvDRKisgcLCOuoMnTaM5G6_DyKKJGhI-YRuL/pub?gid=0&single=true&output=csv"

# =============================================================================
# CONFIGURACIÓN DE PÁGINA
# =============================================================================
st.set_page_config(
    page_title="Dashboard de Presupuesto",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =============================================================================
# ESTILOS CSS — PALETA AZUL CORPORATIVA
# =============================================================================
st.markdown("""
<style>
    /* ---------- Tipografía ---------- */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    html, body, [class*="css"] {
        font-family: 'Inter', 'Segoe UI', sans-serif;
    }

    /* ---------- Layout ---------- */
    .block-container {
        padding-top: 1.2rem;
        padding-bottom: 1rem;
        max-width: 1280px;
    }

    /* ---------- Encabezados ---------- */
    h1, h2, h3, h4 {
        color: #0a1628;
        font-weight: 700;
        letter-spacing: -0.02em;
    }

    /* ---------- Tarjetas KPI ---------- */
    div[data-testid="metric-container"] {
        background: linear-gradient(135deg, #e8f1fc 0%, #f5f9ff 100%);
        border: 1px solid #c3d9f0;
        border-left: 4px solid #1a5276;
        padding: 12px 16px;
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(15, 36, 68, 0.06);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    div[data-testid="metric-container"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(15, 36, 68, 0.12);
    }
    div[data-testid="metric-container"] label {
        color: #1a5276;
        font-weight: 600;
        font-size: 0.82rem;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }
    div[data-testid="metric-container"] div[data-testid="stMetricValue"] {
        color: #0a1628;
        font-size: 1.45rem;
        font-weight: 700;
    }

    /* ---------- Sidebar ---------- */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0a1628 0%, #132d50 100%);
    }
    section[data-testid="stSidebar"] * {
        color: #e0eaf5 !important;
    }
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {
        color: #ffffff !important;
    }

    /* ---------- Divisores ---------- */
    hr {
        border: none;
        border-top: 1px solid #d6e4f0;
        margin: 0.8rem 0;
    }

    /* ---------- Tabla ---------- */
    .dataframe {
        font-size: 0.82rem;
        border-radius: 8px;
        overflow: hidden;
    }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# LÓGICA DE NEGOCIO
# =============================================================================
def clasificar_negocio(centro: str) -> str:
    """Clasifica el centro de coste en Alimentos, Cervecería o Sin asignar."""
    centro_upper = str(centro).upper()
    if "DIVA" in centro_upper:
        return "Alimentos"
    elif "VNTS" in centro_upper:
        return "Cervecería"
    return "Sin asignar"


def fmt_moneda(valor: float) -> str:
    """Formatea un número como moneda con separador de miles."""
    return f"${valor:,.2f}"

# =============================================================================
# CARGA DE DATOS DESDE GOOGLE SHEETS
# =============================================================================
@st.cache_data(ttl=300)
def load_data(url: str) -> pd.DataFrame | None:
    """Lee la hoja de Google Sheets publicada como CSV y la transforma."""
    try:
        df = pd.read_csv(url)
    except Exception as e:
        st.error(f"❌ No se pudo conectar a la hoja de cálculo.\n\nDetalle: {e}")
        return None

    # Normalizar nombres de columna
    df.columns = [str(c).strip() for c in df.columns]

    # Mapeo flexible de nombres
    column_map = {}
    for col in df.columns:
        cl = col.lower()
        if "descripci" in cl or "texto" in cl:
            column_map[col] = "Descripcion"
        elif "desviaci" in cl and "abs" in cl:
            column_map[col] = "Desviacion_absoluta"
        elif "desviaci" in cl and ("%" in cl or "porc" in cl):
            column_map[col] = "Desviacion_porcentual"
    if column_map:
        df.rename(columns=column_map, inplace=True)

    # Rellenar nulos de texto
    text_defaults = {
        "Centro de coste": "Desconocido",
        "Gerencia": "Sin asignar",
        "Descripcion": "Sin descripción",
        "Clase de coste": "N/A",
    }
    for col, default in text_defaults.items():
        if col in df.columns:
            df[col] = df[col].fillna(default)

    # Convertir columnas numéricas
    num_cols = ["Real", "Plan", "Comprometido", "Desviacion_absoluta", "Desviacion_porcentual"]
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Clasificación automática por negocio
    if "Centro de coste" in df.columns:
        df["Negocio"] = df["Centro de coste"].apply(clasificar_negocio)
    else:
        df["Negocio"] = "Sin asignar"

    return df

# =============================================================================
# CARGAR DATOS
# =============================================================================
df = load_data(SHEET_URL)

if df is None:
    st.stop()

# =============================================================================
# BARRA LATERAL — FILTROS GLOBALES
# =============================================================================
with st.sidebar:
    st.markdown("## 📊 Panel de Control")
    st.markdown("---")

    st.markdown("### Filtros Globales")

    if "Gerencia" in df.columns:
        todas_gerencias = ["Todas"] + sorted(df["Gerencia"].unique().tolist())
        gerencia_sel = st.selectbox("Gerencia", todas_gerencias, key="filter_gerencia")
    else:
        gerencia_sel = "Todas"

    todos_negocios = ["Todos"] + sorted(df["Negocio"].unique().tolist())
    negocio_sel = st.selectbox("Categoría de Negocio", todos_negocios, key="filter_negocio")

    st.markdown("---")
    st.caption("Los datos se actualizan cada 5 min.")
    if st.button("🔄 Refrescar datos ahora"):
        st.cache_data.clear()
        st.rerun()

# Aplicar filtros
df_f = df.copy()
if gerencia_sel != "Todas" and "Gerencia" in df_f.columns:
    df_f = df_f[df_f["Gerencia"] == gerencia_sel]
if negocio_sel != "Todos":
    df_f = df_f[df_f["Negocio"] == negocio_sel]

# =============================================================================
# ENCABEZADO PRINCIPAL
# =============================================================================
st.markdown("## 📊 Resumen de Presupuesto")

# =============================================================================
# KPIs
# =============================================================================
total_real = df_f["Real"].sum() if "Real" in df_f.columns else 0
total_plan = df_f["Plan"].sum() if "Plan" in df_f.columns else 0
total_comp = df_f["Comprometido"].sum() if "Comprometido" in df_f.columns else 0
desv_abs = total_real - total_plan

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("Gasto Real", fmt_moneda(total_real))
with c2:
    st.metric("Plan (Presupuestado)", fmt_moneda(total_plan))
with c3:
    st.metric("Comprometido", fmt_moneda(total_comp))
with c4:
    pct = f"{(desv_abs / total_plan * 100):.1f}%" if total_plan else "0%"
    st.metric(
        "Variación (Real − Plan)",
        fmt_moneda(desv_abs),
        delta=pct,
        delta_color="inverse",
    )

st.markdown("---")

# =============================================================================
# GRÁFICOS SUPERIORES
# =============================================================================
col_left, col_right = st.columns(2)

# ---- Real vs Plan por Gerencia ----
with col_left:
    st.markdown("### 📈 Real vs Plan por Gerencia")
    if "Gerencia" in df_f.columns and "Real" in df_f.columns and "Plan" in df_f.columns:
        df_ger = df_f.groupby("Gerencia")[["Real", "Plan"]].sum().reset_index()

        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(
            x=df_ger["Gerencia"], y=df_ger["Real"],
            name="Real",
            marker_color="#1a5276",
            text=df_ger["Real"].apply(lambda v: f"${v:,.0f}"),
            textposition="auto",
        ))
        fig_bar.add_trace(go.Bar(
            x=df_ger["Gerencia"], y=df_ger["Plan"],
            name="Plan",
            marker_color="#5dade2",
            text=df_ger["Plan"].apply(lambda v: f"${v:,.0f}"),
            textposition="auto",
        ))
        fig_bar.update_layout(
            barmode="group",
            margin=dict(l=20, r=20, t=30, b=20),
            height=360,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter, sans-serif"),
        )
        fig_bar.update_yaxes(gridcolor="#e8f0fa")
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("Faltan datos de Gerencia, Real o Plan para este gráfico.")

# ---- Distribución por Negocio ----
with col_right:
    st.markdown("### 🏭 Distribución del Gasto por Negocio")
    if "Negocio" in df_f.columns and "Real" in df_f.columns and "Plan" in df_f.columns:
        df_neg = df_f.groupby("Negocio")[["Real", "Plan"]].sum().reset_index()

        fig_neg = go.Figure()
        fig_neg.add_trace(go.Bar(
            x=df_neg["Negocio"], y=df_neg["Real"],
            name="Real",
            marker_color="#0f2444",
            text=df_neg["Real"].apply(lambda v: f"${v:,.0f}"),
            textposition="auto",
        ))
        fig_neg.add_trace(go.Bar(
            x=df_neg["Negocio"], y=df_neg["Plan"],
            name="Plan",
            marker_color="#3498db",
            text=df_neg["Plan"].apply(lambda v: f"${v:,.0f}"),
            textposition="auto",
        ))
        fig_neg.update_layout(
            barmode="group",
            margin=dict(l=20, r=20, t=30, b=20),
            height=360,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter, sans-serif"),
        )
        fig_neg.update_yaxes(gridcolor="#e8f0fa")
        st.plotly_chart(fig_neg, use_container_width=True)
    else:
        st.info("Faltan datos de Negocio, Real o Plan para este gráfico.")

st.markdown("---")

# =============================================================================
# TABLA DE DETALLE
# =============================================================================
st.markdown("### 📋 Detalle de Partidas")

# Filtros específicos para la tabla
tc1, tc2, tc3 = st.columns([1, 1, 1.5])
with tc1:
    negocios_disp = sorted(df_f["Negocio"].unique().tolist())
    tabla_negocio = st.multiselect(
        "Filtrar por Negocio", options=negocios_disp, default=negocios_disp, key="tabla_neg"
    )
with tc2:
    if "Gerencia" in df_f.columns:
        gerencias_disp = sorted(df_f["Gerencia"].unique().tolist())
        tabla_gerencia = st.multiselect(
            "Filtrar por Gerencia", options=gerencias_disp, default=gerencias_disp, key="tabla_ger"
        )
    else:
        tabla_gerencia = []
with tc3:
    search_term = st.text_input("🔍 Buscar en Descripción o Clase…", "", key="tabla_search")

# Aplicar filtros de tabla
df_tabla = df_f[df_f["Negocio"].isin(tabla_negocio)].copy()
if "Gerencia" in df_tabla.columns and tabla_gerencia:
    df_tabla = df_tabla[df_tabla["Gerencia"].isin(tabla_gerencia)]

if search_term:
    mask = pd.Series([False] * len(df_tabla), index=df_tabla.index)
    if "Descripcion" in df_tabla.columns:
        mask = mask | df_tabla["Descripcion"].str.contains(search_term, case=False, na=False)
    if "Clase de coste" in df_tabla.columns:
        mask = mask | df_tabla["Clase de coste"].str.contains(search_term, case=False, na=False)
    df_tabla = df_tabla[mask]

# Orden de columnas
cols_order = [
    "Negocio", "Centro de coste", "Gerencia", "Clase de coste", "Descripcion",
    "Real", "Plan", "Comprometido", "Desviacion_absoluta", "Desviacion_porcentual",
]
cols_order = [c for c in cols_order if c in df_tabla.columns]
df_display = df_tabla[cols_order].copy()

# Formateo visual para la tabla
cols_moneda = ["Real", "Plan", "Comprometido", "Desviacion_absoluta"]
for c in cols_moneda:
    if c in df_display.columns:
        df_display[c] = df_display[c].apply(lambda x: f"${x:,.2f}")

if "Desviacion_porcentual" in df_display.columns:
    df_display["Desviacion_porcentual"] = df_display["Desviacion_porcentual"].apply(
        lambda x: f"{x:,.2f}%"
    )

st.dataframe(df_display, use_container_width=True, height=380)

# Indicador de registros
st.caption(f"Mostrando {len(df_display)} de {len(df)} registros totales.")
