from __future__ import annotations

import base64
import json
import datetime as dt_module
from datetime import datetime, timedelta
from html import escape
from io import StringIO
from pathlib import Path
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st
from PIL import Image
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode
from st_aggrid.shared import DataReturnMode, GridUpdateMode

try:
    from streamlit_autorefresh import st_autorefresh
except ImportError:
    st_autorefresh = None

# Configuration & Constants
SPREADSHEET_ID = "1bA5QldI-H0S449F2p0T0XJOhDFcLllbV6HuMSEPNk2E"
INTERACTIONS_SHEET_NAME = "BBDD_INTERACCIONES"
AGENTS_SHEET_NAME = "BBDD_ARMY"
DAILY_CONTROL_SHEET_NAME = "CONTROL_DIARIO"
MATCHES_SHEET_NAME = "PARTIDOS"
TIMEZONE = ZoneInfo("America/Lima")
CACHE_TTL_SECONDS = 15
REFRESH_INTERVAL_SECONDS = 15
VIEW_OPTIONS = [
    "Resumen Diario",
    "Cumplimiento por Evento",
    "Planificación de Partidos",
    "Análisis Histórico",
    "Calidad de Datos",
]
ECHARTS_CDN_URL = "https://cdn.jsdelivr.net/npm/echarts@6.1.0/dist/echarts.min.js"
ICONIFY_SVG_URL = "https://api.iconify.design/{icon}.svg"
APP_DIR = Path(__file__).resolve().parent
LOGO_SVG_PATH = APP_DIR / "assets" / "betsson-logo.svg"
LOGO_PNG_PATH = APP_DIR / "assets" / "betsson-logo.png"

# Color Palette (Light Theme Betsson-based)
ORANGE = "#ff6600"
INK = "#111827"
MUTED = "#64748b"
BG = "#f8fafc"
CARD_BG = "#ffffff"
BORDER = "#e2e8f0"
SUCCESS = "#10b981"
WARNING = "#f59e0b"
DANGER = "#ef4444"
CHART_COLORS = ["#ff6600", "#10b981", "#3b82f6", "#f59e0b", "#8b5cf6", "#64748b"]

# Grid IDs (GIDs) from Google Sheets to retrieve complete raw sheets
SHEET_GIDS = {
    AGENTS_SHEET_NAME: "2071723292",
    INTERACTIONS_SHEET_NAME: "145386846",
    DAILY_CONTROL_SHEET_NAME: "1252017492",
    MATCHES_SHEET_NAME: "236372855",
}

# Spreadsheet Column Names
TIMESTAMP_COL = "Marca temporal"
CONTACT_COL = "Número de Contacto"
EVENT_COL = "Evento del Día"
PARTICIPATION_COL = "Tipo de Participación"
EVIDENCE_COL = "Imagen de Evidencia"
RESPONSE_ARMY_COL = "Army"

AGENT_REGISTRATION_COL = "Fecha de Registro"
AGENT_NAME_COL = "Nombre Completo"
AGENT_EMAIL_COL = "Correo Electrónico"
AGENT_CONTACT_COL = "Número de contacto"
AGE_RANGE_COL = "Rango etario"
BILLING_STATUS_COL = "Datos Factuación"
AGENT_ARMY_COL = "ARMY"
STATUS_COL = "Estatus"
DROP_DATE_COL = "Fecha de Baja"

CONTROL_PERSON_COL = "Participantes"
CONTROL_CONTACT_COL = "Contacto"
CONTROL_ARMY_COL = "Army"
CONTROL_EVENT_COL = "Evento"
CONTROL_DATE_COL = "Fecha"
CONTROL_HASHTAGS_COL = "Hashtags"
CONTROL_NETWORK_COL = "RRSS"
COMMENTS_DONE_COL = "Comentarios Logrados"
REPOSTS_DONE_COL = "Repost Logrados"
COMMENTS_GOAL_COL = "Comentarios Objetivo"
REPOSTS_GOAL_COL = "Repost Objetivo"
COMMENTS_MISSING_COL = "Comentarios Faltantes"
REPOSTS_MISSING_COL = "Repost Faltante"

# Matches sheet columns
MATCH_PHASE_COL = "Fase"
MATCH_DATE_COL = "Fecha partido"
MATCH_TIME_COL = "Hora Lima"
MATCH_NAME_COL = "Partido"
MATCH_IMPORTANCE_COL = "Importancia"
MATCH_NETWORK_COL = "Red social"
MATCH_TOTAL_ACTIONS_COL = "Total acciones"

JOIN_KEY_COL = "Contacto normalizado"
PERSON_COL = "Persona"
FINAL_ARMY_COL = "Army final"
MATCH_COL = "Registrado en BBDD_ARMY"

INTERACTION_REQUIRED_COLUMNS = (
    TIMESTAMP_COL,
    CONTACT_COL,
    EVENT_COL,
    PARTICIPATION_COL,
    EVIDENCE_COL,
    RESPONSE_ARMY_COL,
)

AGENT_REQUIRED_COLUMNS = (
    AGENT_REGISTRATION_COL,
    AGENT_NAME_COL,
    AGENT_CONTACT_COL,
    AGENT_ARMY_COL,
    STATUS_COL,
)

DAILY_CONTROL_REQUIRED_COLUMNS = (
    CONTROL_PERSON_COL,
    CONTROL_CONTACT_COL,
    CONTROL_ARMY_COL,
    CONTROL_EVENT_COL,
    CONTROL_DATE_COL,
    COMMENTS_DONE_COL,
    REPOSTS_DONE_COL,
    COMMENTS_GOAL_COL,
    REPOSTS_GOAL_COL,
)

MATCHES_REQUIRED_COLUMNS = (
    MATCH_PHASE_COL,
    MATCH_DATE_COL,
    MATCH_TIME_COL,
    MATCH_NAME_COL,
    MATCH_IMPORTANCE_COL,
    MATCH_NETWORK_COL,
    MATCH_TOTAL_ACTIONS_COL,
)

SOCIAL_COLS = ["Link Instagram", "Link Tiktok", "Link Facebook", "Link Youtube", "Link X / Twitter"]

# Helper Functions for Sheets Loading and Preprocessing
def solo_digitos(val: str) -> str:
    import re
    if not val:
        return ""
    return re.sub(r"\D", "", str(val)).strip()

def sheet_csv_url(sheet_name: str, spreadsheet_id: str = SPREADSHEET_ID) -> str:
    gid = SHEET_GIDS.get(sheet_name)
    if gid:
        return f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=csv&gid={gid}"
    encoded_sheet = quote(sheet_name)
    return (
        f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/gviz/tq"
        f"?tqx=out:csv&sheet={encoded_sheet}"
    )

def configured_csv_url(sheet_name: str) -> str:
    secret_candidates = {
        INTERACTIONS_SHEET_NAME: ("GOOGLE_SHEET_INTERACTIONS_CSV_URL", "GOOGLE_SHEET_CSV_URL"),
        AGENTS_SHEET_NAME: ("GOOGLE_SHEET_ARMY_CSV_URL",),
        DAILY_CONTROL_SHEET_NAME: ("GOOGLE_SHEET_DAILY_CONTROL_CSV_URL",),
        MATCHES_SHEET_NAME: ("GOOGLE_SHEET_MATCHES_CSV_URL",),
    }.get(sheet_name, ())

    try:
        for secret_key in secret_candidates:
            configured_value = st.secrets.get(secret_key)
            if configured_value:
                return configured_value
    except Exception:
        pass

    return sheet_csv_url(sheet_name)

def add_cache_buster(url: str, refresh_key: int) -> str:
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query["_dashboard_refresh"] = str(refresh_key)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))

@st.cache_data(show_spinner=False, ttl=CACHE_TTL_SECONDS)
def load_sheet(sheet_name: str, required_columns: tuple[str, ...], refresh_key: int) -> pd.DataFrame:
    csv_url = add_cache_buster(configured_csv_url(sheet_name), refresh_key)
    request = Request(csv_url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=20) as response:
        csv_content = response.read().decode("utf-8")

    if "<!DOCTYPE html" in csv_content[:500] or "Debes acceder" in csv_content[:2000]:
        raise ValueError(
            f"Google Sheets devolvió una pantalla de login para {sheet_name}. "
            "Verifica que el archivo esté compartido como lector para cualquier persona con el enlace."
        )

    df = pd.read_csv(StringIO(csv_content), dtype=str, keep_default_na=False)
    missing_columns = [column for column in required_columns if column not in df.columns]

    if missing_columns:
        columns = ", ".join(df.columns.astype(str).tolist())
        missing = ", ".join(missing_columns)
        raise ValueError(
            f"La hoja {sheet_name} no tiene las columnas esperadas. Faltan: {missing}. Columnas recibidas: {columns}"
        )

    return df

def normalize_text(series: pd.Series, fallback: str = "Sin dato") -> pd.Series:
    return (
        series.astype(str)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
        .replace({"": fallback, "#N/A": fallback, "nan": fallback, "None": fallback})
    )

def to_number(series: pd.Series) -> pd.Series:
    return pd.to_numeric(
        series.astype(str).str.replace(",", ".", regex=False).str.strip(),
        errors="coerce",
    ).fillna(0)

def to_optional_number(series: pd.Series) -> pd.Series:
    cleaned = series.astype(str).str.replace(",", ".", regex=False).str.strip()
    cleaned = cleaned.replace({"": pd.NA, "nan": pd.NA, "None": pd.NA, "#N/A": pd.NA})
    return pd.to_numeric(cleaned, errors="coerce")

def normalize_optional_link(value: str) -> bool:
    cleaned = str(value).strip().lower()
    if not cleaned:
        return False
    invalid_values = {".", "-", "no", "no tengo", "no uso", "no uso:(", "ninguno", "sin dato"}
    return cleaned not in invalid_values

def prepare_interactions(df: pd.DataFrame) -> pd.DataFrame:
    prepared = df.copy()
    prepared[TIMESTAMP_COL] = pd.to_datetime(prepared[TIMESTAMP_COL], dayfirst=True, errors="coerce")
    prepared[CONTACT_COL] = normalize_text(prepared[CONTACT_COL], fallback="")
    prepared[JOIN_KEY_COL] = prepared[CONTACT_COL].apply(solo_digitos)
    prepared[RESPONSE_ARMY_COL] = normalize_text(prepared[RESPONSE_ARMY_COL], fallback="Sin army")
    prepared[EVIDENCE_COL] = normalize_text(prepared[EVIDENCE_COL], fallback="")

    # Derivations
    prepared["fecha_registro"] = prepared[TIMESTAMP_COL].dt.date
    prepared["hora_registro"] = prepared[TIMESTAMP_COL].dt.strftime("%H:%M:%S")
    prepared["hora_bloque"] = prepared[TIMESTAMP_COL].dt.hour
    prepared["Tiene evidencia"] = prepared[EVIDENCE_COL].ne("")
    prepared["Fecha"] = prepared[TIMESTAMP_COL].dt.date # compatibility field
    
    # Normalización del tipo de participación
    orig_part = prepared[PARTICIPATION_COL].astype(str)
    prepared["participation_original"] = orig_part
    norm_part = orig_part.str.strip().str.lower()
    prepared["tipo_participacion_normalizado"] = "COMENTARIO"
    is_repost = norm_part.str.contains("repost|compart", case=False, regex=True, na=False)
    prepared.loc[is_repost, "tipo_participacion_normalizado"] = "REPOST"
    
    # compatibility fields
    prepared["Es comentario"] = prepared["tipo_participacion_normalizado"] == "COMENTARIO"
    prepared["Es repost"] = prepared["tipo_participacion_normalizado"] == "REPOST"

    # Normalización de eventos
    def norm_event_row(row):
        val = str(row[EVENT_COL]).strip()
        cleaned = " ".join(val.split())
        upper = cleaned.upper()
        
        import unicodedata
        nfkd = unicodedata.normalize('NFKD', upper)
        key = "".join([c for c in nfkd if not unicodedata.combining(c)])
        
        if "MEME BELGICA 1502" in key or "MEME BELGICA 1502" in upper:
            key = "MEME BELGICA 1506"
            upper = "MEME BELGICA 1506"
        elif "MEME ESPANA 1502" in key or "MEME ESPAÑA 1502" in upper:
            key = "MEME ESPANA 1506"
            upper = "MEME ESPAÑA 1506"
            
        return pd.Series([val, key, upper])

    prepared[["evento_original", "evento_key", "evento_mostrar"]] = prepared.apply(norm_event_row, axis=1)

    return prepared.sort_values(TIMESTAMP_COL, ascending=False, na_position="last")

def prepare_agents(df: pd.DataFrame) -> pd.DataFrame:
    prepared = df.copy()

    for column in [AGENT_EMAIL_COL, AGE_RANGE_COL, BILLING_STATUS_COL, DROP_DATE_COL, *SOCIAL_COLS]:
        if column not in prepared.columns:
            prepared[column] = ""

    prepared[AGENT_REGISTRATION_COL] = pd.to_datetime(prepared[AGENT_REGISTRATION_COL], dayfirst=True, errors="coerce")
    prepared[AGENT_NAME_COL] = normalize_text(prepared[AGENT_NAME_COL], fallback="Sin nombre")
    prepared[AGENT_EMAIL_COL] = normalize_text(prepared[AGENT_EMAIL_COL], fallback="")
    prepared[AGENT_CONTACT_COL] = normalize_text(prepared[AGENT_CONTACT_COL], fallback="")
    prepared[JOIN_KEY_COL] = prepared[AGENT_CONTACT_COL].apply(solo_digitos)
    prepared[AGE_RANGE_COL] = normalize_text(prepared[AGE_RANGE_COL], fallback="Sin rango")
    prepared[BILLING_STATUS_COL] = normalize_text(prepared[BILLING_STATUS_COL], fallback="Sin dato")
    prepared[AGENT_ARMY_COL] = normalize_text(prepared[AGENT_ARMY_COL], fallback="Por definir")
    prepared[STATUS_COL] = normalize_text(prepared[STATUS_COL], fallback="Sin estatus").str.upper()
    prepared[DROP_DATE_COL] = normalize_text(prepared[DROP_DATE_COL], fallback="")
    
    prepared["Redes registradas"] = prepared[SOCIAL_COLS].apply(
        lambda row: sum(normalize_optional_link(value) for value in row),
        axis=1,
    )
    prepared["Activo"] = prepared[STATUS_COL].eq("ACTIVO")

    prepared = prepared[prepared[AGENT_NAME_COL].ne("Sin nombre")].copy()
    prepared = prepared.sort_values(["Activo", AGENT_REGISTRATION_COL], ascending=[False, False])
    return prepared.drop_duplicates(subset=[JOIN_KEY_COL], keep="first")

def recalculate_daily_control_metrics(prepared: pd.DataFrame) -> pd.DataFrame:
    prepared = prepared.copy()
    prepared["total_logrado"] = prepared["comentarios_logrados"] + prepared["reposts_logrados"]

    has_comment_objective = prepared["comentarios_objetivo"].notna()
    has_repost_objective = prepared["reposts_objetivo"].notna()
    has_any_objective = has_comment_objective | has_repost_objective

    prepared["total_objetivo"] = (
        prepared[["comentarios_objetivo", "reposts_objetivo"]]
        .fillna(0)
        .sum(axis=1)
    )
    prepared.loc[~has_any_objective, "total_objetivo"] = pd.NA

    prepared["comentarios_faltantes"] = pd.NA
    prepared["reposts_faltantes"] = pd.NA
    prepared["exceso_comentarios"] = pd.NA
    prepared["exceso_reposts"] = pd.NA

    prepared.loc[has_comment_objective, "comentarios_faltantes"] = (
        prepared.loc[has_comment_objective, "comentarios_objetivo"]
        - prepared.loc[has_comment_objective, "comentarios_logrados"]
    ).clip(lower=0)
    prepared.loc[has_comment_objective, "exceso_comentarios"] = (
        prepared.loc[has_comment_objective, "comentarios_logrados"]
        - prepared.loc[has_comment_objective, "comentarios_objetivo"]
    ).clip(lower=0)

    prepared.loc[has_repost_objective, "reposts_faltantes"] = (
        prepared.loc[has_repost_objective, "reposts_objetivo"]
        - prepared.loc[has_repost_objective, "reposts_logrados"]
    ).clip(lower=0)
    prepared.loc[has_repost_objective, "exceso_reposts"] = (
        prepared.loc[has_repost_objective, "reposts_logrados"]
        - prepared.loc[has_repost_objective, "reposts_objetivo"]
    ).clip(lower=0)

    prepared["cumplimiento_pct"] = pd.NA
    objective_mask = prepared["total_objetivo"].notna() & prepared["total_objetivo"].ne(0)
    prepared.loc[objective_mask, "cumplimiento_pct"] = (
        prepared.loc[objective_mask, "total_logrado"]
        / prepared.loc[objective_mask, "total_objetivo"]
    )

    def calc_status(row):
        c_log = row["comentarios_logrados"]
        r_log = row["reposts_logrados"]
        c_obj = row["comentarios_objetivo"]
        r_obj = row["reposts_objetivo"]

        if pd.isna(c_obj) and pd.isna(r_obj):
            return "SIN OBJETIVO CARGADO"

        if c_log == 0 and r_log == 0:
            return "SIN ACTIVIDAD"

        c_met = True if pd.isna(c_obj) else (c_log >= c_obj)
        r_met = True if pd.isna(r_obj) else (r_log >= r_obj)

        if c_met and r_met:
            return "CUMPLIDO"

        if c_log > 0 or r_log > 0:
            return "PARCIAL"

        return "NO CUMPLIDO"

    prepared["estado_cumplimiento"] = prepared.apply(calc_status, axis=1)
    return prepared

def prepare_daily_control(df: pd.DataFrame) -> pd.DataFrame:
    prepared = df.copy()
    prepared[CONTROL_PERSON_COL] = normalize_text(prepared[CONTROL_PERSON_COL], fallback="Sin nombre")
    prepared[CONTROL_CONTACT_COL] = normalize_text(prepared[CONTROL_CONTACT_COL], fallback="")
    prepared[JOIN_KEY_COL] = prepared[CONTROL_CONTACT_COL].apply(solo_digitos)
    prepared[CONTROL_ARMY_COL] = normalize_text(prepared[CONTROL_ARMY_COL], fallback="Sin army")
    
    def norm_event_cd(val):
        v = str(val).strip()
        cleaned = " ".join(v.split())
        upper = cleaned.upper()
        import unicodedata
        nfkd = unicodedata.normalize('NFKD', upper)
        key = "".join([c for c in nfkd if not unicodedata.combining(c)])
        
        if "MEME BELGICA 1502" in key or "MEME BELGICA 1502" in upper:
            key = "MEME BELGICA 1506"
            upper = "MEME BELGICA 1506"
        elif "MEME ESPANA 1502" in key or "MEME ESPAÑA 1502" in upper:
            key = "MEME ESPANA 1506"
            upper = "MEME ESPAÑA 1506"
            
        return pd.Series([v, key, upper])

    prepared[["evento_original", "evento_key", "evento_mostrar"]] = prepared[CONTROL_EVENT_COL].apply(norm_event_cd)
    prepared[CONTROL_DATE_COL] = pd.to_datetime(prepared[CONTROL_DATE_COL], dayfirst=True, errors="coerce").dt.date

    # CONTROL_DIARIO uses the "Logrados" columns as the operational target when
    # the explicit objective columns are blank.
    prepared["comentarios_logrados"] = to_number(prepared[COMMENTS_DONE_COL])
    prepared["reposts_logrados"] = to_number(prepared[REPOSTS_DONE_COL])
    prepared["comentarios_objetivo"] = to_optional_number(prepared[COMMENTS_GOAL_COL]).combine_first(
        to_optional_number(prepared[COMMENTS_DONE_COL])
    )
    prepared["reposts_objetivo"] = to_optional_number(prepared[REPOSTS_GOAL_COL]).combine_first(
        to_optional_number(prepared[REPOSTS_DONE_COL])
    )
    prepared = recalculate_daily_control_metrics(prepared)

    return prepared[prepared[CONTROL_PERSON_COL].ne("Sin nombre")].sort_values(
        [CONTROL_DATE_COL, "estado_cumplimiento", "total_logrado"],
        ascending=[False, True, False]
    )

def apply_interaction_actuals_to_daily_control(
    control_df: pd.DataFrame,
    enriched_df: pd.DataFrame,
) -> pd.DataFrame:
    prepared = control_df.copy()
    prepared["comentarios_logrados"] = 0.0
    prepared["reposts_logrados"] = 0.0

    if prepared.empty or enriched_df.empty:
        return recalculate_daily_control_metrics(prepared)

    actuals = (
        enriched_df
        .groupby([JOIN_KEY_COL, "evento_key", "tipo_participacion_normalizado"])
        .size()
        .unstack(fill_value=0)
    )
    for participation_type in ["COMENTARIO", "REPOST"]:
        if participation_type not in actuals.columns:
            actuals[participation_type] = 0

    actual_lookup = actuals[["COMENTARIO", "REPOST"]].to_dict("index")

    def distribute_actuals(indexes: list[int], objective_col: str, achieved_col: str, actual_total: float) -> None:
        remaining = float(actual_total)
        rows_with_objective = []

        for idx in indexes:
            objective = prepared.at[idx, objective_col]
            if pd.isna(objective) or float(objective) <= 0:
                prepared.at[idx, achieved_col] = 0.0
                continue

            assigned = min(remaining, float(objective))
            prepared.at[idx, achieved_col] = assigned
            remaining -= assigned
            rows_with_objective.append(idx)

        if remaining > 0 and indexes:
            overflow_idx = rows_with_objective[-1] if rows_with_objective else indexes[-1]
            prepared.at[overflow_idx, achieved_col] = float(prepared.at[overflow_idx, achieved_col]) + remaining

    for (contact_key, event_key), group in prepared.groupby([JOIN_KEY_COL, "evento_key"], sort=False):
        actual = actual_lookup.get((contact_key, event_key), {"COMENTARIO": 0, "REPOST": 0})
        group_indexes = group.index.tolist()
        distribute_actuals(group_indexes, "comentarios_objetivo", "comentarios_logrados", actual["COMENTARIO"])
        distribute_actuals(group_indexes, "reposts_objetivo", "reposts_logrados", actual["REPOST"])

    return recalculate_daily_control_metrics(prepared)

def prepare_matches(df: pd.DataFrame) -> pd.DataFrame:
    prepared = df.copy()

    text_columns = [MATCH_PHASE_COL, MATCH_NAME_COL, MATCH_IMPORTANCE_COL, MATCH_NETWORK_COL]
    for column in text_columns:
        if column not in prepared.columns:
            prepared[column] = ""
        prepared[column] = normalize_text(prepared[column], fallback="Sin dato")

    prepared[MATCH_TOTAL_ACTIONS_COL] = to_number(prepared[MATCH_TOTAL_ACTIONS_COL])

    date_text = prepared[MATCH_DATE_COL].astype(str).str.strip()
    parsed_short_dates = pd.to_datetime(date_text, format="%d/%m/%y", errors="coerce")
    parsed_long_dates = pd.to_datetime(date_text, format="%d/%m/%Y", errors="coerce")
    prepared[MATCH_DATE_COL] = parsed_short_dates.fillna(parsed_long_dates).dt.date

    return prepared.dropna(subset=[MATCH_DATE_COL]).sort_values(
        [MATCH_DATE_COL, MATCH_TIME_COL, MATCH_NAME_COL]
    )

def enrich_interactions(interactions: pd.DataFrame, agents: pd.DataFrame) -> pd.DataFrame:
    agent_cols = [JOIN_KEY_COL, AGENT_NAME_COL, AGENT_ARMY_COL, STATUS_COL, "Activo"]
    
    enriched = interactions.merge(
        agents[agent_cols],
        on=JOIN_KEY_COL,
        how="left",
        indicator=True,
    )

    enriched["join_exitoso"] = enriched["_merge"].eq("both")
    enriched["estatus_resuelto"] = enriched[STATUS_COL].fillna("SIN REGISTRO")
    enriched["nombre_resuelto"] = enriched[AGENT_NAME_COL].where(
        enriched["join_exitoso"],
        "Contacto no identificado: " + enriched[CONTACT_COL]
    )

    army_bbdd = enriched[AGENT_ARMY_COL]
    army_original = enriched[RESPONSE_ARMY_COL]
    
    bbdd_is_valid = army_bbdd.notna() & ~army_bbdd.isin(["", "Por definir", "Sin dato", "Sin army en BBDD_ARMY"])
    orig_is_valid = army_original.notna() & ~army_original.isin(["", "Por definir", "Sin dato", "Sin army"])
    
    enriched["army_resuelto"] = army_bbdd.where(
        bbdd_is_valid,
        army_original.where(orig_is_valid, "SIN ARMY IDENTIFICADO")
    )
    
    # compatibility fields
    enriched[FINAL_ARMY_COL] = enriched["army_resuelto"]
    enriched[STATUS_COL] = enriched["estatus_resuelto"]
    enriched[PERSON_COL] = enriched["nombre_resuelto"]
    enriched[MATCH_COL] = enriched["join_exitoso"]

    def get_no_id_reason(row):
        if row["join_exitoso"]:
            return ""
        phone = str(row[CONTACT_COL]).strip()
        cleaned_phone = row[JOIN_KEY_COL]
        if not phone:
            return "Teléfono vacío en interacción"
        if len(cleaned_phone) != 9:
            return f"Longitud de teléfono inválida ({len(cleaned_phone)} dígitos)"
        return "Número no registrado en el maestro"
        
    enriched["motivo_no_identificado"] = enriched.apply(get_no_id_reason, axis=1)

    def check_quality(row):
        issues = []
        if not row["join_exitoso"]:
            issues.append("No identificado en maestro")
        if not row[EVIDENCE_COL]:
            issues.append("Falta imagen de evidencia")
        if row["army_resuelto"] == "SIN ARMY IDENTIFICADO":
            issues.append("Sin army resuelto")
        if len(row[JOIN_KEY_COL]) != 9 and len(row[JOIN_KEY_COL]) != 8:
            issues.append(f"Longitud teléfono inválida ({len(row[JOIN_KEY_COL])} dig)")
        return ", ".join(issues) if issues else "ALTA CALIDAD"
        
    enriched["calidad_registro"] = enriched.apply(check_quality, axis=1)

    return enriched.drop(columns=["_merge"]).sort_values(TIMESTAMP_COL, ascending=False)

# Styling & CSS Injection
def inject_styles() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

        :root {
            --betsson-orange: #ff6600;
            --betsson-bg: #f8fafc;
            --betsson-card: #ffffff;
            --betsson-ink: #111827;
            --betsson-muted: #64748b;
            --betsson-border: #e2e8f0;
        }

        /* Hide streamlit headers and decorations to remove blank space at the top */
        header[data-testid="stHeader"] {
            visibility: hidden !important;
            height: 0px !important;
        }
        div[data-testid="stDecoration"] {
            visibility: hidden !important;
            height: 0px !important;
        }
        /* Remove extra top spacing inside the block-container */
        .block-container {
            padding-top: 0.5rem !important;
            padding-bottom: 2rem !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
            max-width: 100% !important;
            background-color: var(--betsson-bg);
        }

        /* Compact form labels */
        div[data-testid="stForm"] label p,
        .custom-widget-label {
            font-size: 0.72rem !important;
            font-weight: 800 !important;
            color: var(--betsson-ink) !important;
            margin-bottom: 4px !important;
            margin-top: 0px !important;
            font-family: 'Inter', sans-serif !important;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        /* Compact selectboxes and inputs */
        div[data-testid="stForm"] div[data-baseweb="select"] > div {
            background-color: #ffffff !important;
            border: 1px solid #cbd5e1 !important;
            border-radius: 6px !important;
            min-height: 32px !important;
            height: 32px !important;
            font-size: 0.8rem !important;
            transition: all 0.2s ease !important;
        }
        div[data-testid="stForm"] div[data-baseweb="select"] > div:hover {
            border-color: var(--betsson-orange) !important;
        }
        div[data-testid="stForm"] div[data-baseweb="select"] [role="combobox"] {
            padding: 0 6px !important;
            font-size: 0.8rem !important;
            font-family: 'Inter', sans-serif !important;
        }
        
        /* Compact date inputs */
        div[data-testid="stForm"] div[data-testid="stDateInput"] div[role="presentation"] {
            background-color: #ffffff !important;
            border: 1px solid #cbd5e1 !important;
            border-radius: 6px !important;
            min-height: 32px !important;
            height: 32px !important;
            font-size: 0.8rem !important;
        }

        /* Popover buttons styled as compact selectboxes */
        div[data-testid="stForm"] div[data-testid="stPopover"] button {
            background-color: #ffffff !important;
            border: 1px solid #cbd5e1 !important;
            border-radius: 6px !important;
            color: #1e293b !important;
            font-size: 0.8rem !important;
            height: 32px !important;
            min-height: 32px !important;
            font-weight: 500 !important;
            padding: 0 8px !important;
            transition: border-color 0.2s ease-in-out !important;
            box-shadow: none !important;
        }
        div[data-testid="stForm"] div[data-testid="stPopover"] button:hover {
            border-color: var(--betsson-orange) !important;
            background-color: #f8fafc !important;
        }
        
        /* Form buttons styling (Aplicar / Limpiar) */
        div[data-testid="stForm"] button[data-testid="baseButton-primary"] {
            background-color: var(--betsson-orange) !important;
            border: 1px solid var(--betsson-orange) !important;
            color: #ffffff !important;
            font-size: 0.78rem !important;
            font-weight: 700 !important;
            border-radius: 6px !important;
            height: 32px !important;
            transition: all 0.2s ease !important;
            box-shadow: 0 2px 4px rgba(255, 102, 0, 0.1) !important;
        }
        div[data-testid="stForm"] button[data-testid="baseButton-primary"]:hover {
            background-color: #e05500 !important;
            border-color: #e05500 !important;
            box-shadow: 0 4px 12px rgba(255, 102, 0, 0.2) !important;
        }
        div[data-testid="stForm"] button[data-testid="baseButton-secondary"] {
            background-color: #f8fafc !important;
            border: 1px solid #cbd5e1 !important;
            color: #475569 !important;
            font-size: 0.78rem !important;
            font-weight: 600 !important;
            border-radius: 6px !important;
            height: 32px !important;
            transition: all 0.2s ease !important;
        }
        div[data-testid="stForm"] button[data-testid="baseButton-secondary"]:hover {
            background-color: #f1f5f9 !important;
            color: #1e293b !important;
            border-color: #94a3b8 !important;
        }

        /* Hide the st_autorefresh element container completely */
        iframe[title="streamlit_autorefresh.st_autorefresh"] {
            opacity: 0 !important;
            height: 1px !important;
            width: 1px !important;
            position: absolute !important;
            pointer-events: none !important;
        }

        /* Top Header Card */
        .header-card {
            display: flex;
            align-items: center;
            justify-content: space-between;
            background-color: var(--betsson-card);
            border: 1px solid var(--betsson-border);
            border-radius: 6px;
            padding: 0.6rem 1.2rem;
            margin-bottom: 1rem;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.02);
        }

        .header-left {
            display: flex;
            align-items: center;
            gap: 1rem;
        }

        .header-logo img {
            height: 32px;
            object-fit: contain;
            display: block;
        }

        .header-title-section h1 {
            font-family: 'Inter', sans-serif;
            font-size: 1.2rem;
            font-weight: 800;
            color: var(--betsson-ink);
            margin: 0;
            line-height: 1.1;
        }

        .header-title-section p {
            font-family: 'Inter', sans-serif;
            font-size: 0.7rem;
            color: var(--betsson-muted);
            margin: 2px 0 0 0;
            font-weight: 500;
        }

        .update-badge {
            display: inline-block;
            background-color: #f1f5f9;
            color: var(--betsson-muted);
            font-family: 'Inter', sans-serif;
            font-size: 0.65rem;
            font-weight: 700;
            padding: 0.3rem 0.6rem;
            border-radius: 6px;
            border: 1px solid var(--betsson-border);
        }

        .header-right {
            display: flex;
            align-items: center;
            justify-content: flex-end;
            gap: 0.45rem;
            flex-wrap: wrap;
        }

        /* Sidebar settings */
        section[data-testid="stSidebar"] {
            display: none !important;
            width: 0 !important;
            min-width: 0 !important;
        }

        div[data-testid="stSidebarCollapsedControl"] {
            display: none !important;
        }

        .sidebar-logo {
            text-align: center;
            padding: 1rem 0;
            border-bottom: 1px solid var(--betsson-border);
            margin-bottom: 1rem;
        }

        .sidebar-logo img {
            width: 100px;
        }

        /* Horizontal Filter Form Bar styling (Max 6px borders, compact height) */
        /* Horizontal Filter Form Bar styling (Max 6px borders, compact height) */
        div[data-testid="stForm"] {
            background-color: var(--betsson-card) !important;
            border: 1px solid var(--betsson-border) !important;
            border-radius: 6px !important;
            padding: 0.6rem 0.8rem !important;
            margin-bottom: 0.8rem !important;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.02) !important;
        }

        div[data-testid="stForm"] div[data-testid="stHorizontalBlock"] {
            align-items: flex-end !important;
        }

        div[data-testid="stForm"] div[data-testid="stFormSubmitButton"] button {
            width: 100% !important;
            min-height: 32px !important;
            height: 32px !important;
        }

        div[data-baseweb="select"], 
        div[data-baseweb="input"], 
        input, 
        button,
        .stForm {
            border-radius: 6px !important;
        }

        /* Top card title */
        .section-title {
            font-family: 'Inter', sans-serif;
            font-size: 0.95rem;
            font-weight: 800;
            color: var(--betsson-ink);
            margin: 0.25rem 0 0.5rem 0;
            border-left: 3px solid var(--betsson-orange);
            padding-left: 6px;
            line-height: 1.1;
        }

        .filter-summary-card {
            background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
            border: 1px solid var(--betsson-border);
            border-radius: 8px;
            padding: 0.75rem 0.85rem;
            margin: 0 0 0.75rem 0;
            box-shadow: 0 8px 18px rgba(15, 23, 42, 0.04);
        }

        .filter-summary-head {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 0.75rem;
            margin-bottom: 0.55rem;
        }

        .filter-summary-title {
            font-family: 'Inter', sans-serif;
            font-size: 0.72rem;
            font-weight: 900;
            color: var(--betsson-ink);
            text-transform: uppercase;
            letter-spacing: 0.06em;
        }

        .filter-summary-hint {
            font-family: 'Inter', sans-serif;
            font-size: 0.66rem;
            font-weight: 700;
            color: var(--betsson-muted);
        }

        .filter-chip-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.45rem;
        }

        .filter-chip {
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            min-height: 28px;
            max-width: 100%;
            box-sizing: border-box;
            border: 1px solid #dbe3ee;
            border-radius: 999px;
            background-color: #ffffff;
            padding: 0.28rem 0.65rem;
            font-family: 'Inter', sans-serif;
            box-shadow: 0 2px 6px rgba(15, 23, 42, 0.03);
        }

        .filter-chip span {
            flex: 0 0 auto;
            font-size: 0.62rem;
            font-weight: 900;
            color: #718096;
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }

        .filter-chip strong {
            min-width: 0;
            font-size: 0.72rem;
            font-weight: 800;
            color: var(--betsson-ink);
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        .view-tabs-header {
            display: flex;
            align-items: flex-end;
            justify-content: space-between;
            gap: 0.75rem;
            margin: 0.2rem 0 0.45rem 0;
        }

        .view-tabs-label {
            font-family: 'Inter', sans-serif;
            font-size: 0.68rem;
            font-weight: 800;
            color: var(--betsson-muted);
            text-transform: uppercase;
            letter-spacing: 0.06em;
            margin: 0;
        }

        .view-tabs-caption {
            font-family: 'Inter', sans-serif;
            font-size: 0.66rem;
            font-weight: 700;
            color: #94a3b8;
        }

        div[data-testid="stSegmentedControl"] {
            background: #ffffff;
            border: 1px solid var(--betsson-border);
            border-radius: 8px;
            padding: 0.28rem;
            margin-bottom: 1rem;
            box-shadow: 0 8px 18px rgba(15, 23, 42, 0.04);
        }

        div[data-testid="stSegmentedControl"] button {
            border-radius: 6px !important;
            font-family: 'Inter', sans-serif !important;
            font-size: 0.78rem !important;
            font-weight: 700 !important;
            min-height: 34px !important;
            border-color: transparent !important;
            transition: background-color 0.15s ease, color 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease !important;
        }

        div[data-testid="stSegmentedControl"] button:hover {
            background-color: #fff7ed !important;
            border-color: #fed7aa !important;
            color: #c2410c !important;
        }

        div[data-testid="stSegmentedControl"] button[aria-checked="true"],
        div[data-testid="stSegmentedControl"] button[aria-selected="true"],
        div[data-testid="stSegmentedControl"] button[aria-pressed="true"] {
            background: linear-gradient(180deg, #ff7a1a 0%, #ff6600 100%) !important;
            color: #ffffff !important;
            border-color: #ff6600 !important;
            box-shadow: 0 6px 14px rgba(255, 102, 0, 0.22) !important;
        }

        /* Card container */
        /* Card container */
        div[data-testid="stVerticalBlockBorderWrapper"] {
            background-color: var(--betsson-card) !important;
            border: 1px solid var(--betsson-border) !important;
            border-radius: 6px !important;
            padding: 0.85rem !important;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.02) !important;
            margin-bottom: 1rem !important;
        }

        /* Grid of KPI cards */
        .kpi-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 0.75rem;
            margin-bottom: 1rem;
        }

        /* KPI Card */
        .kpi-card {
            background-color: var(--betsson-card);
            border: 1px solid var(--betsson-border);
            border-left: 4px solid var(--betsson-orange);
            border-radius: 6px;
            padding: 0.65rem 0.85rem;
            display: flex;
            align-items: center;
            gap: 0.75rem;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.02);
            transition: transform 0.2s ease;
        }

        .kpi-card:hover {
            transform: translateY(-2px);
        }

        .kpi-icon {
            width: 32px;
            height: 32px;
            display: flex;
            align-items: center;
            justify-content: center;
            background-color: #fff9f5;
            border-radius: 6px;
            flex-shrink: 0;
        }

        .kpi-icon img {
            width: 20px;
            height: 20px;
        }

        .kpi-body {
            display: flex;
            flex-direction: column;
            min-width: 0;
        }

        .kpi-value {
            font-family: 'Inter', sans-serif;
            font-size: 1.05rem;
            font-weight: 800;
            color: var(--betsson-ink);
            line-height: 1.1;
        }

        .kpi-label {
            font-family: 'Inter', sans-serif;
            font-size: 0.6rem;
            font-weight: 700;
            color: var(--betsson-muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-top: 0.1rem;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .kpi-sub {
            font-family: 'Inter', sans-serif;
            font-size: 0.55rem;
            color: #94a3b8;
            margin-top: 0.05rem;
            font-weight: 500;
        }

        @media (max-width: 900px) {
            .block-container {
                padding-top: 0.35rem !important;
                padding-left: 0.65rem !important;
                padding-right: 0.65rem !important;
                padding-bottom: 1rem !important;
            }

            .header-card {
                flex-direction: column;
                align-items: flex-start;
                gap: 0.75rem;
                padding: 0.75rem;
            }

            .header-left {
                width: 100%;
                align-items: flex-start;
                gap: 0.7rem;
            }

            .header-logo img {
                height: 28px;
            }

            .header-title-section h1 {
                font-size: 1rem;
                overflow-wrap: anywhere;
            }

            .header-title-section p {
                font-size: 0.65rem;
            }

            .header-right {
                width: 100%;
                justify-content: flex-start;
            }

            .update-badge {
                width: 100%;
                box-sizing: border-box;
                text-align: left;
            }

            div[data-testid="stForm"] {
                padding: 0.65rem !important;
            }

            div[data-testid="stForm"] div[data-testid="stHorizontalBlock"],
            div[data-testid="stHorizontalBlock"] {
                flex-wrap: wrap !important;
                gap: 0.55rem !important;
            }

            div[data-testid="stForm"] div[data-testid="column"] {
                flex: 1 1 220px !important;
                min-width: min(100%, 220px) !important;
            }

            div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
                flex: 1 1 320px !important;
                min-width: min(100%, 320px) !important;
            }

            div[data-testid="stSegmentedControl"] div[role="radiogroup"] {
                flex-wrap: wrap !important;
            }

            div[data-testid="stSegmentedControl"] button {
                flex: 1 1 180px !important;
            }

            .filter-summary-head,
            .view-tabs-header {
                align-items: flex-start;
                flex-direction: column;
                gap: 0.2rem;
            }

            .filter-chip {
                flex: 1 1 180px;
            }

            .kpi-grid {
                grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            }
        }

        @media (max-width: 560px) {
            .header-left {
                flex-direction: column;
            }

            div[data-testid="stForm"] div[data-testid="column"],
            div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
                flex: 1 1 100% !important;
                min-width: 100% !important;
            }

            div[data-testid="stForm"] div[data-baseweb="select"] > div,
            div[data-testid="stForm"] div[data-testid="stDateInput"] div[role="presentation"],
            div[data-testid="stForm"] div[data-testid="stPopover"] button,
            div[data-testid="stForm"] div[data-testid="stFormSubmitButton"] button {
                min-height: 38px !important;
                height: 38px !important;
            }

            .filter-summary-card {
                padding: 0.7rem;
            }

            .filter-chip {
                flex: 1 1 100%;
                justify-content: space-between;
                border-radius: 8px;
            }

            .filter-chip strong {
                text-align: right;
            }

            div[data-testid="stSegmentedControl"] button {
                flex: 1 1 100% !important;
                justify-content: center !important;
            }

            .kpi-grid {
                grid-template-columns: 1fr !important;
            }
        }

        /* Hide elements to clean Streamlit default UI */
        #MainMenu, header, footer {
            visibility: hidden;
            height: 0;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

def asset_data_uri(path: Path, mime_type: str) -> str:
    try:
        if path.exists():
            with open(path, "rb") as f:
                encoded = base64.b64encode(f.read()).decode("utf-8")
            return f"data:{mime_type};base64,{encoded}"
    except Exception:
        pass
    return ""

def format_int(val) -> str:
    try:
        if pd.isna(val) or val is None:
            return "0"
        return f"{int(float(val)):,}".replace(",", ".")
    except Exception:
        return str(val)

def render_kpi_cards(cards: list[dict]) -> None:
    html = '<div class="kpi-grid">'
    for card in cards:
        icon_name = card.get("icon", "")
        if ":" in icon_name:
            icon_path = icon_name.replace(":", "/")
        else:
            icon_path = icon_name
        icon_url = ICONIFY_SVG_URL.format(icon=icon_path)
        
        value = card.get("value", "")
        label = card.get("label", "")
        subtitle = card.get("subtitle", "")
        
        html += f"""
        <div class="kpi-card">
            <div class="kpi-icon">
                <img src="{icon_url}" alt="{label}" onerror="this.style.display='none'" />
            </div>
            <div class="kpi-body">
                <div class="kpi-value">{value}</div>
                <div class="kpi-label" title="{label}">{label}</div>
                <div class="kpi-sub">{subtitle}</div>
            </div>
        </div>
        """
    html += '</div>'
    st.html(html)

def daily_person_progress(day_df: pd.DataFrame, daily_goal: int) -> pd.DataFrame:
    if day_df.empty:
        return pd.DataFrame(columns=[
            "Fecha", PERSON_COL, JOIN_KEY_COL, FINAL_ARMY_COL, STATUS_COL, MATCH_COL,
            "Interacciones", "Comentarios", "Reposts", "Eventos", "Evidencias",
            "Meta", "Faltan", "Avance", "Estado avance", "Ultima"
        ])
    
    rows = []
    for c_key, grp in day_df.groupby(JOIN_KEY_COL):
        first_row = grp.iloc[0]
        
        coms = int(grp["tipo_participacion_normalizado"].eq("COMENTARIO").sum())
        reps = int(grp["tipo_participacion_normalizado"].eq("REPOST").sum())
        total_actions = len(grp)
        
        meta = daily_goal
        faltan = max(meta - total_actions, 0)
        avance = total_actions / meta if meta > 0 else 1.0
        
        if total_actions >= meta:
            estado = "Cumplido"
        elif total_actions > 0:
            estado = "Pendiente"
        else:
            estado = "Sin Actividad"
            
        events = grp["evento_key"].nunique()
        evidences = grp["Tiene evidencia"].sum()
        
        # Last interaction time
        last_time = grp[TIMESTAMP_COL].max()
        
        rows.append({
            "Fecha": first_row["fecha_registro"],
            PERSON_COL: first_row["nombre_resuelto"],
            JOIN_KEY_COL: c_key,
            FINAL_ARMY_COL: first_row["army_resuelto"],
            STATUS_COL: first_row["estatus_resuelto"],
            MATCH_COL: first_row["join_exitoso"],
            "Interacciones": total_actions,
            "Comentarios": coms,
            "Reposts": reps,
            "Eventos": events,
            "Evidencias": evidences,
            "Meta": meta,
            "Faltan": faltan,
            "Avance": avance,
            "Estado avance": estado,
            "Ultima": last_time
        })
        
    return pd.DataFrame(rows)

def render_top_header(df: pd.DataFrame, agents: pd.DataFrame, refreshed_at: datetime) -> None:
    latest_timestamp = df[TIMESTAMP_COL].dropna().max()
    latest_label = (
        latest_timestamp.strftime("%d/%m/%Y %H:%M")
        if pd.notna(latest_timestamp)
        else "Sin registros"
    )
    refreshed_label = refreshed_at.strftime("%d/%m/%Y %H:%M:%S")
    logo_src = asset_data_uri(LOGO_SVG_PATH, "image/svg+xml")
    logo_markup = (
        f'<div class="header-logo"><img src="{logo_src}" alt="Betsson" /></div>'
        if logo_src
        else '<div style="font-family: \'Inter\', sans-serif; font-size: 1.3rem; font-weight: 900; color: #ff6600; letter-spacing: -0.03em;">betsson</div>'
    )
    st.html(
        f"""
        <div class="header-card">
            <div class="header-left">
                {logo_markup}
                <div class="header-title-section">
                    <h1>Seguimiento de Actividad ARMY BETSSON</h1>
                    <p>Dashboard Profesional de Productividad y Control de Interacciones</p>
                </div>
            </div>
            <div class="header-right">
                <span class="update-badge">Última respuesta: {escape(latest_label)}</span>
                <span class="update-badge">Dashboard actualizado: {escape(refreshed_label)}</span>
            </div>
        </div>
        """
    )

# Multiselect Popover custom component to avoid pills and chips
def multiselect_popover(label: str, options: list[str], default_select_all: bool = True, key_prefix: str = "ms") -> list[str]:
    state_key = f"{key_prefix}_selected"
    if state_key not in st.session_state:
        st.session_state[state_key] = list(options) if default_select_all else []
        
    selected = st.session_state[state_key]
    
    summary_text = f"{len(selected)} seleccionados" if selected else "Ninguno"
    if len(selected) == len(options):
        summary_text = "Todos"
        
    with st.popover(f"{label}: {summary_text}", use_container_width=True):
        search_query = st.text_input("Buscar...", key=f"{key_prefix}_search", label_visibility="collapsed")
        
        # Checkbox for Select All / Clear All
        all_selected = (len(selected) == len(options))
        select_all_val = st.checkbox("Seleccionar todos", value=all_selected, key=f"{key_prefix}_all_cb")
        
        if select_all_val and not all_selected:
            st.session_state[state_key] = list(options)
            st.rerun()
        elif not select_all_val and all_selected:
            st.session_state[state_key] = []
            st.rerun()
            
        new_selected = []
        for opt in options:
            is_visible = not search_query or search_query.lower() in str(opt).lower()
            if is_visible:
                checked = opt in selected
                val = st.checkbox(str(opt), value=checked, key=f"{key_prefix}_cb_{opt}")
                if val:
                    new_selected.append(opt)
            else:
                if opt in selected:
                    new_selected.append(opt)
                    
        st.session_state[state_key] = new_selected
        
    return st.session_state[state_key]

# ECharts Rendering engine
def render_echart(options: dict, height: int = 360, key: str | None = None) -> None:
    chart_id = key or f"chart_{abs(hash(json.dumps(options, sort_keys=True, default=str))) % 10_000_000}"
    options_json = json.dumps(options, ensure_ascii=False, default=str)
    html = f"""
    <!doctype html>
    <html>
    <head>
      <meta charset="utf-8" />
      <script src="{ECHARTS_CDN_URL}"></script>
      <style>
        html, body {{
          margin: 0;
          padding: 0;
          background: transparent;
          font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        }}
        .chart-card {{
          width: 100%;
          height: {height}px;
          box-sizing: border-box;
          border: 1px solid #e2e8f0;
          border-radius: 6px;
          background: #ffffff;
          box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.02);
          overflow: hidden;
          padding: 8px 8px 4px 8px;
        }}
        #{chart_id} {{
          width: 100%;
          height: 100%;
        }}
      </style>
    </head>
    <body>
      <div class="chart-card"><div id="{chart_id}"></div></div>
      <script>
        const chart = echarts.init(document.getElementById("{chart_id}"), null, {{ renderer: "canvas" }});
        const option = {options_json};
        chart.setOption(option);
        window.addEventListener("resize", () => chart.resize());
      </script>
    </body>
    </html>
    """
    st.iframe(html, height=height + 4)

def echart_base(title: str) -> dict:
    return {
        "title": {
            "text": title,
            "left": 4,
            "top": 2,
            "textStyle": {"fontSize": 11, "fontWeight": 800, "color": INK, "fontFamily": "Inter"},
        },
        "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
        "legend": {"top": 2, "right": 4, "itemWidth": 8, "itemHeight": 8, "textStyle": {"fontSize": 9, "color": MUTED, "fontFamily": "Inter"}},
        "grid": {"top": 35, "left": 10, "right": 10, "bottom": 10, "containLabel": True},
        "color": CHART_COLORS,
        "animationDuration": 600,
    }

def render_bar_chart(
    data: pd.DataFrame,
    x_col: str,
    y_col: str,
    title: str,
    *,
    horizontal: bool = False,
    color: str = ORANGE,
    height: int = 200,
    key: str | None = None,
) -> None:
    if data.empty:
        st.info(f"No hay datos para {title.lower()}.")
        return

    labels = data[x_col].astype(str).tolist()
    values = data[y_col].round(2).tolist()
    option = echart_base(title)
    
    label_config = {
        "show": True,
        "position": "right" if horizontal else "top",
        "fontSize": 9,
        "fontWeight": "bold",
        "color": INK,
        "fontFamily": "Inter"
    }

    option["series"] = [
        {
            "name": y_col,
            "type": "bar",
            "data": values,
            "barMaxWidth": 20,
            "label": label_config,
            "itemStyle": {
                "borderRadius": [0, 4, 4, 0] if horizontal else [4, 4, 0, 0],
                "color": color,
            },
        }
    ]

    if horizontal:
        option["grid"] = {"top": 35, "left": 80, "right": 25, "bottom": 10, "containLabel": True}
        option["xAxis"] = {
            "type": "value", 
            "axisLabel": {"show": False},
            "splitLine": {"lineStyle": {"color": "#f1f5f9"}},
        }
        option["yAxis"] = {
            "type": "category",
            "data": labels,
            "axisLabel": {"color": INK, "fontSize": 9, "fontWeight": "600", "overflow": "truncate", "width": 80, "fontFamily": "Inter"},
            "axisTick": {"show": False},
            "axisLine": {"show": False},
        }
    else:
        option["grid"] = {"top": 35, "left": 15, "right": 15, "bottom": 20, "containLabel": True}
        option["xAxis"] = {
            "type": "category",
            "data": labels,
            "axisLabel": {"color": INK, "rotate": 0, "fontSize": 9, "fontWeight": "600", "overflow": "truncate", "width": 55, "hideOverlap": True, "fontFamily": "Inter"},
            "axisTick": {"show": False},
            "axisLine": {"show": False},
        }
        option["yAxis"] = {
            "type": "value", 
            "axisLabel": {"show": False},
            "splitLine": {"lineStyle": {"color": "#f1f5f9"}},
        }

    render_echart(option, height=height, key=key)

def render_donut_chart(
    data: pd.DataFrame, 
    name_col: str, 
    value_col: str, 
    title: str, 
    *, 
    height: int = 200, 
    key: str | None = None
) -> None:
    if data.empty:
        st.info(f"No hay datos para {title.lower()}.")
        return
    option = echart_base(title)
    option["tooltip"] = {"trigger": "item", "formatter": "{b}: {c} ({d}%)"}
    option["legend"] = {"bottom": 2, "left": "center", "itemWidth": 8, "itemHeight": 8, "textStyle": {"fontSize": 9, "color": MUTED, "fontFamily": "Inter"}}
    
    option["series"] = [
        {
            "name": title,
            "type": "pie",
            "radius": ["40%", "65%"],
            "center": ["50%", "45%"],
            "avoidLabelOverlap": True,
            "itemStyle": {"borderRadius": 4, "borderColor": "#ffffff", "borderWidth": 2},
            "label": {
                "show": True, 
                "fontSize": 9, 
                "fontWeight": "bold",
                "color": INK,
                "formatter": "{b}: {d}%",
                "fontFamily": "Inter"
            },
            "data": [
                {"name": str(row[name_col]), "value": float(row[value_col])}
                for _, row in data.iterrows()
            ],
        }
    ]
    render_echart(option, height=height, key=key)

# AgGrid Custom Table
def render_grid(data: pd.DataFrame, *, height: int = 320, key: str | None = None) -> None:
    if data.empty:
        st.info("No hay datos para mostrar.")
        return

    grid_data = data.copy()
    
    # Preformat date/datetime columns in Python to avoid javascript [object Object] serialisation bug
    for col in grid_data.columns:
        if pd.api.types.is_datetime64_any_dtype(grid_data[col]):
            if col in [TIMESTAMP_COL, "Ultima", "Primera interacción", "Última interacción"]:
                grid_data[col] = grid_data[col].dt.strftime("%d/%m/%Y %H:%M").fillna("")
            else:
                grid_data[col] = grid_data[col].dt.strftime("%d/%m/%Y").fillna("")
        else:
            sample = grid_data[col].dropna()
            if not sample.empty and sample.apply(lambda x: hasattr(x, "strftime") and pd.notna(x)).any():
                if col in [TIMESTAMP_COL, "Ultima", "Primera interacción", "Última interacción"]:
                    grid_data[col] = grid_data[col].apply(lambda x: x.strftime("%d/%m/%Y %H:%M") if (hasattr(x, "strftime") and pd.notna(x)) else str(x) if pd.notna(x) else "")
                else:
                    grid_data[col] = grid_data[col].apply(lambda x: x.strftime("%d/%m/%Y") if (hasattr(x, "strftime") and pd.notna(x)) else str(x) if pd.notna(x) else "")

    gb = GridOptionsBuilder.from_dataframe(grid_data)
    gb.configure_default_column(
        filter=True,
        sortable=True,
        resizable=True,
        wrapText=False,
        autoHeight=False,
        minWidth=110,
    )
    gb.configure_grid_options(
        rowHeight=32,
        headerHeight=34,
        pagination=True,
        paginationPageSize=20,
        suppressCellFocus=True,
        animateRows=True,
    )

    percent_formatter = JsCode(
        """
        function(params) {
            if (params.value == null || params.value === '') return '';
            return Math.round(params.value * 100) + '%';
        }
        """
    )

    army_match_renderer = JsCode(
        """
        class ArmyMatchRenderer {
          init(params) {
            this.eGui = document.createElement('span');
            let val = params.value;
            if (val === true || val === 'True' || val === 'true') {
              this.eGui.innerHTML = '🟢 Cruzado';
              this.eGui.style.color = '#065f46';
              this.eGui.style.fontWeight = 'bold';
              this.eGui.style.backgroundColor = '#d1fae5';
              this.eGui.style.padding = '2px 8px';
              this.eGui.style.borderRadius = '9999px';
              this.eGui.style.fontSize = '10px';
            } else {
              this.eGui.innerHTML = '🔴 Sin Registro';
              this.eGui.style.color = '#991b1b';
              this.eGui.style.fontWeight = 'bold';
              this.eGui.style.backgroundColor = '#fee2e2';
              this.eGui.style.padding = '2px 8px';
              this.eGui.style.borderRadius = '9999px';
              this.eGui.style.fontSize = '10px';
            }
          }
          getGui() { return this.eGui; }
        }
        """
    )

    status_renderer = JsCode(
        """
        class StatusRenderer {
          init(params) {
            this.eGui = document.createElement('span');
            let val = params.value ? params.value.toString().toUpperCase() : '';
            this.eGui.style.fontWeight = 'bold';
            this.eGui.style.padding = '2px 8px';
            this.eGui.style.borderRadius = '9999px';
            this.eGui.style.fontSize = '10px';
            if (val === 'ACTIVO' || val === 'TRUE' || val === 'true') {
              this.eGui.innerHTML = 'Activo';
              this.eGui.style.color = '#065f46';
              this.eGui.style.backgroundColor = '#d1fae5';
            } else if (val === 'INACTIVO' || val === 'FALSE' || val === 'false' || val === 'BAJA' || val === 'RETIRADO') {
              this.eGui.innerHTML = val.charAt(0) + val.slice(1).toLowerCase();
              this.eGui.style.color = '#374151';
              this.eGui.style.backgroundColor = '#f3f4f6';
            } else {
              this.eGui.innerHTML = val || 'Sin estado';
              this.eGui.style.color = '#374151';
              this.eGui.style.backgroundColor = '#f3f4f6';
            }
          }
          getGui() { return this.eGui; }
        }
        """
    )
    
    compliance_renderer = JsCode(
        """
        class ComplianceRenderer {
          init(params) {
            this.eGui = document.createElement('span');
            let val = params.value ? params.value.toString().toUpperCase() : '';
            this.eGui.style.fontWeight = 'bold';
            this.eGui.style.padding = '2px 8px';
            this.eGui.style.borderRadius = '9999px';
            this.eGui.style.fontSize = '10px';
            if (val === 'CUMPLIDO') {
              this.eGui.innerHTML = '🟢 Cumplido';
              this.eGui.style.color = '#065f46';
              this.eGui.style.backgroundColor = '#d1fae5';
            } else if (val === 'PENDIENTE' || val === 'PARCIAL') {
              this.eGui.innerHTML = '🟡 Parcial';
              this.eGui.style.color = '#92400e';
              this.eGui.style.backgroundColor = '#fef3c7';
            } else if (val === 'NO CUMPLIDO') {
              this.eGui.innerHTML = '🔴 No Cumplido';
              this.eGui.style.color = '#991b1b';
              this.eGui.style.backgroundColor = '#fee2e2';
            } else if (val === 'SIN OBJETIVO CARGADO') {
              this.eGui.innerHTML = '⚪ Sin Objetivo';
              this.eGui.style.color = '#475569';
              this.eGui.style.backgroundColor = '#f1f5f9';
            } else if (val === 'SIN ACTIVIDAD') {
              this.eGui.innerHTML = '⚪ Sin Actividad';
              this.eGui.style.color = '#4b5563';
              this.eGui.style.backgroundColor = '#f3f4f6';
            } else if (val === 'RETIRADO') {
              this.eGui.innerHTML = '⚫ Retirado';
              this.eGui.style.color = '#64748b';
              this.eGui.style.backgroundColor = '#e2e8f0';
            } else if (val === 'INACTIVO') {
              this.eGui.innerHTML = '⚫ Inactivo';
              this.eGui.style.color = '#64748b';
              this.eGui.style.backgroundColor = '#e2e8f0';
            } else {
              this.eGui.innerHTML = val;
              this.eGui.style.color = '#4b5563';
              this.eGui.style.backgroundColor = '#f3f4f6';
            }
          }
          getGui() { return this.eGui; }
        }
        """
    )

    importance_renderer = JsCode(
        """
        class ImportanceRenderer {
          init(params) {
            this.eGui = document.createElement('span');
            let val = params.value ? params.value.toString().toUpperCase() : '';
            this.eGui.innerHTML = val;
            this.eGui.style.fontWeight = 'bold';
            this.eGui.style.fontSize = '10px';
            this.eGui.style.padding = '2px 8px';
            this.eGui.style.borderRadius = '9999px';
            if (val === 'ALTA') {
              this.eGui.style.color = '#991b1b';
              this.eGui.style.backgroundColor = '#fee2e2';
            } else if (val === 'MEDIA') {
              this.eGui.style.color = '#b45309';
              this.eGui.style.backgroundColor = '#fef3c7';
            } else {
              this.eGui.style.color = '#1e3a8a';
              this.eGui.style.backgroundColor = '#dbeafe';
            }
          }
          getGui() { return this.eGui; }
        }
        """
    )

    total_actions_renderer = JsCode(
        """
        class TotalActionsRenderer {
          init(params) {
            this.eGui = document.createElement('span');
            let val = parseInt(params.value);
            if (isNaN(val)) {
              this.eGui.innerHTML = params.value || '';
              return;
            }
            this.eGui.style.fontWeight = 'bold';
            this.eGui.style.padding = '2px 8px';
            this.eGui.style.borderRadius = '9999px';
            this.eGui.style.fontSize = '10px';
            if (val >= 5) {
              this.eGui.innerHTML = '✅ ' + val + ' (Meta)';
              this.eGui.style.color = '#065f46';
              this.eGui.style.backgroundColor = '#d1fae5';
            } else {
              this.eGui.innerHTML = '⏳ ' + val + ' / 5';
              this.eGui.style.color = '#c2410c';
              this.eGui.style.backgroundColor = '#ffedd5';
            }
          }
          getGui() { return this.eGui; }
        }
        """
    )

    quality_renderer = JsCode(
        """
        class QualityRenderer {
          init(params) {
            this.eGui = document.createElement('span');
            let val = params.value ? params.value.toString() : '';
            if (val === '') {
              this.eGui.innerHTML = '';
              return;
            }
            this.eGui.style.fontWeight = 'bold';
            this.eGui.style.padding = '2px 8px';
            this.eGui.style.borderRadius = '9999px';
            this.eGui.style.fontSize = '10px';
            if (val === 'ALTA CALIDAD') {
              this.eGui.innerHTML = '🟢 Alta Calidad';
              this.eGui.style.color = '#065f46';
              this.eGui.style.backgroundColor = '#d1fae5';
            } else {
              this.eGui.innerHTML = '⚠️ ' + val;
              this.eGui.style.color = '#b91c1c';
              this.eGui.style.backgroundColor = '#fee2e2';
            }
          }
          getGui() { return this.eGui; }
        }
        """
    )

    compliance_pct_renderer = JsCode(
        """
        class CompliancePctRenderer {
          init(params) {
            this.eGui = document.createElement('span');
            let val = parseFloat(params.value);
            if (isNaN(val)) {
              this.eGui.innerHTML = '';
              return;
            }
            let pct = Math.round(val * 100);
            this.eGui.style.fontWeight = 'bold';
            this.eGui.style.padding = '2px 8px';
            this.eGui.style.borderRadius = '9999px';
            this.eGui.style.fontSize = '10px';
            if (pct >= 100) {
              this.eGui.innerHTML = '🎯 ' + pct + '%';
              this.eGui.style.color = '#065f46';
              this.eGui.style.backgroundColor = '#d1fae5';
            } else if (pct > 0) {
              this.eGui.innerHTML = '📈 ' + pct + '%';
              this.eGui.style.color = '#b45309';
              this.eGui.style.backgroundColor = '#fef3c7';
            } else {
              this.eGui.innerHTML = '❌ ' + pct + '%';
              this.eGui.style.color = '#b91c1c';
              this.eGui.style.backgroundColor = '#fee2e2';
            }
          }
          getGui() { return this.eGui; }
        }
        """
    )

    if EVIDENCE_COL in grid_data.columns:
        link_renderer = JsCode(
            """
            class LinkRenderer {
              init(params) {
                this.eGui = document.createElement('a');
                this.eGui.innerText = params.value ? '👁️ Evidencia' : '';
                this.eGui.href = params.value || '#';
                this.eGui.target = '_blank';
                this.eGui.style.color = '#ff6600';
                this.eGui.style.fontWeight = 'bold';
                this.eGui.style.textDecoration = 'none';
                this.eGui.style.backgroundColor = '#fff5f0';
                this.eGui.style.padding = '2px 8px';
                this.eGui.style.borderRadius = '9999px';
                this.eGui.style.fontSize = '10px';
                this.eGui.style.border = '1px solid #ffe5d9';
              }
              getGui() { return this.eGui; }
            }
            """
        )
        gb.configure_column(EVIDENCE_COL, header_name="Evidencia", cellRenderer=link_renderer)

    if "Avance" in grid_data.columns:
        gb.configure_column("Avance", cellRenderer=compliance_pct_renderer)
    if "Cumplimiento" in grid_data.columns:
        gb.configure_column("Cumplimiento", cellRenderer=compliance_pct_renderer)
    if "cumplimiento_pct" in grid_data.columns:
        gb.configure_column("cumplimiento_pct", cellRenderer=compliance_pct_renderer)
        
    if "Total de acciones" in grid_data.columns:
        gb.configure_column("Total de acciones", cellRenderer=total_actions_renderer)
    if "Alerta de calidad" in grid_data.columns:
        gb.configure_column("Alerta de calidad", cellRenderer=quality_renderer)
        
    if "En BBDD_ARMY" in grid_data.columns:
        gb.configure_column("En BBDD_ARMY", cellRenderer=army_match_renderer)
    if "Registrado en BBDD_ARMY" in grid_data.columns:
        gb.configure_column("Registrado en BBDD_ARMY", cellRenderer=army_match_renderer)
    if "Estado de identificación" in grid_data.columns:
        gb.configure_column("Estado de identificación", cellRenderer=army_match_renderer)

    if "Estatus" in grid_data.columns:
        gb.configure_column("Estatus", cellRenderer=status_renderer)
    if "Status" in grid_data.columns:
        gb.configure_column("Status", cellRenderer=status_renderer)

    if "Estado avance" in grid_data.columns:
        gb.configure_column("Estado avance", cellRenderer=compliance_renderer)
    if "estado_cumplimiento" in grid_data.columns:
        gb.configure_column("estado_cumplimiento", cellRenderer=compliance_renderer)
    if "Estado" in grid_data.columns:
        gb.configure_column("Estado", cellRenderer=compliance_renderer)

    if "Importancia" in grid_data.columns:
        gb.configure_column("Importancia", cellRenderer=importance_renderer)

    grid_options = gb.build()
    custom_css = {
        ".ag-root-wrapper": {
            "border-radius": "6px",
            "border": "1px solid #e2e8f0",
            "box-shadow": "0 4px 6px -1px rgba(0, 0, 0, 0.02)",
            "overflow": "hidden",
            "background-color": "#ffffff",
        },
        ".ag-header": {"background-color": "#f8fafc", "border-bottom": "1px solid #e2e8f0"},
        ".ag-header-cell-text": {"font-weight": "800", "color": "#111827", "font-family": "Inter"},
        ".ag-row": {"font-size": "11.5px", "font-family": "Inter", "color": "#111827"},
        ".ag-cell": {"display": "flex", "align-items": "center"},
    }
    
    # Enable exporting to CSV inside AgGrid
    AgGrid(
        grid_data,
        gridOptions=grid_options,
        height=height,
        theme="alpine", # Switched to professional Alpine theme
        update_mode=GridUpdateMode.NO_UPDATE,
        data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
        allow_unsafe_jscode=True,
        custom_css=custom_css,
        key=key,
        show_search=True,
        show_download_button=True,
    )

# Views
def render_daily_progress_tab(
    enriched_df: pd.DataFrame, 
    agents: pd.DataFrame,
    daily_goal: int,
    selected_day: object,
    selected_armies: list[str],
    selected_statuses: list[str],
    selected_participation: str,
    selected_event: str,
    selected_participant: str
) -> None:
    # 1. Apply tab-specific selections that are NOT global
    day_df = enriched_df[enriched_df["fecha_registro"] == selected_day].copy()
    
    if selected_event != "Todos":
        day_df = day_df[day_df["evento_mostrar"] == selected_event]
    if selected_armies:
        day_df = day_df[day_df["army_resuelto"].isin(selected_armies)]
    if selected_statuses:
        day_df = day_df[day_df["estatus_resuelto"].isin(selected_statuses)]
    if selected_participation != "Todos":
        day_df = day_df[day_df["tipo_participacion_normalizado"] == selected_participation]
    if selected_participant != "Todos":
        day_df = day_df[day_df["nombre_resuelto"] == selected_participant]

    # Calculate active agents matching filter
    active_agents = agents[agents["Activo"]].copy()
    if selected_armies:
        active_agents = active_agents[active_agents[AGENT_ARMY_COL].isin(selected_armies)]
    
    total_active_agents = active_agents.shape[0]

    # Recalculate daily progress
    progress = daily_person_progress(day_df, daily_goal)
    
    # In order to show active agents who had no activity today, we merge active_agents with progress
    if not progress.empty:
        day_progress = progress[progress["Fecha"] == selected_day].copy()
    else:
        day_progress = pd.DataFrame(columns=[JOIN_KEY_COL, "Interacciones", "Comentarios", "Reposts", "Eventos", "Evidencias", "Avance", "Estado avance", "Ultima"])

    # Merge active agents
    if not active_agents.empty:
        active_contacts = set(active_agents[JOIN_KEY_COL].tolist())
        active_with_interactions = set(day_progress[JOIN_KEY_COL].tolist()) if not day_progress.empty else set()
        silent_contacts = active_contacts - active_with_interactions
        
        if silent_contacts:
            silent_agents = active_agents[active_agents[JOIN_KEY_COL].isin(silent_contacts)].copy()
            silent_rows = pd.DataFrame({
                "Fecha": selected_day,
                PERSON_COL: silent_agents[AGENT_NAME_COL],
                JOIN_KEY_COL: silent_agents[JOIN_KEY_COL],
                FINAL_ARMY_COL: silent_agents[AGENT_ARMY_COL],
                STATUS_COL: silent_agents[STATUS_COL],
                MATCH_COL: True,
                "Interacciones": 0,
                "Comentarios": 0,
                "Reposts": 0,
                "Eventos": 0,
                "Evidencias": 0,
                "Meta": daily_goal,
                "Faltan": daily_goal,
                "Avance": 0.0,
                "Estado avance": "Sin Actividad",
                "Ultima": ""
            })
            daily_tracking = pd.concat([day_progress, silent_rows], ignore_index=True)
        else:
            daily_tracking = day_progress.copy()
    else:
        daily_tracking = day_progress.copy()

    # Total stats
    total_interactions = day_df.shape[0]
    com_count = day_df[day_df["tipo_participacion_normalizado"] == "COMENTARIO"].shape[0]
    rep_count = day_df[day_df["tipo_participacion_normalizado"] == "REPOST"].shape[0]
    
    active_participated = daily_tracking[(daily_tracking["Interacciones"] > 0) & (daily_tracking[STATUS_COL] == "ACTIVO")].shape[0]
    active_completed = daily_tracking[(daily_tracking["Estado avance"] == "Cumplido") & (daily_tracking[STATUS_COL] == "ACTIVO")].shape[0]
    active_pending = daily_tracking[(daily_tracking["Estado avance"] == "Pendiente") & (daily_tracking[STATUS_COL] == "ACTIVO")].shape[0]
    active_no_activity = daily_tracking[(daily_tracking["Estado avance"] == "Sin Actividad") & (daily_tracking[STATUS_COL] == "ACTIVO")].shape[0]
    
    participated_count = daily_tracking[daily_tracking["Interacciones"] > 0].shape[0]
    
    unidentified_count = day_df[~day_df["join_exitoso"]].shape[0]
    last_interaction = day_df[TIMESTAMP_COL].max()
    last_int_str = last_interaction.strftime("%H:%M:%S") if pd.notna(last_interaction) else "Sin actividad"
    
    # Cobertura
    if total_active_agents > 0:
        coverage_pct = active_participated / total_active_agents
        coverage_lbl = f"{coverage_pct:.1%} de cobertura"
        agents_val = f"{active_participated} / {total_active_agents}"
        completed_val = f"{active_completed} / {total_active_agents}"
    else:
        coverage_lbl = "Sin base activa"
        agents_val = f"{active_participated}"
        completed_val = f"{active_completed}"
        
    avg_actions = total_interactions / participated_count if participated_count > 0 else 0.0
    active_events = day_df["evento_key"].nunique()

    # KPI Layout
    render_kpi_cards([
        {
            "icon": "fluent-emoji-flat:bar-chart",
            "value": format_int(total_interactions),
            "label": "Interacciones",
            "subtitle": f"{com_count} Com. · {rep_count} Rep.",
        },
        {
            "icon": "fluent-emoji-flat:busts-in-silhouette",
            "value": agents_val,
            "label": "Part. con Actividad",
            "subtitle": coverage_lbl,
        },
        {
            "icon": "fluent-emoji-flat:hourglass-done",
            "value": f"{active_pending + active_no_activity}",
            "label": "Part. sin Meta",
            "subtitle": f"{active_pending} pend · {active_no_activity} inact",
        },
        {
            "icon": "fluent-emoji-flat:check-mark-button",
            "value": completed_val,
            "label": "Metas Cumplidas",
            "subtitle": "Agentes que cumplieron",
        },
        {
            "icon": "fluent-emoji-flat:exclamation-mark",
            "value": format_int(unidentified_count),
            "label": "No Identificados",
            "subtitle": f"Última: {last_int_str}",
        }
    ])

    # Charts Section
    st.markdown("<div class='section-title'>Análisis Horario y de ARMY</div>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    
    with col1:
        # Chart 1: Cumulative interactions by hour
        with st.container(border=True):
            hour_counts = day_df.groupby("hora_bloque").size().reindex(range(24), fill_value=0)
            cum_total = hour_counts.cumsum()

            com_counts = day_df[day_df["tipo_participacion_normalizado"] == "COMENTARIO"].groupby("hora_bloque").size().reindex(range(24), fill_value=0)
            cum_com = com_counts.cumsum()

            rep_counts = day_df[day_df["tipo_participacion_normalizado"] == "REPOST"].groupby("hora_bloque").size().reindex(range(24), fill_value=0)
            cum_rep = rep_counts.cumsum()

            # Unique participants per hour
            cum_unique = []
            seen_participants = set()
            for h in range(24):
                hour_df = day_df[day_df["hora_bloque"] == h]
                seen_participants.update(hour_df[JOIN_KEY_COL].dropna().tolist())
                cum_unique.append(len(seen_participants))

            var_total = [cum_total.iloc[0]]
            for i in range(1, 24):
                var_total.append(cum_total.iloc[i] - cum_total.iloc[i-1])

            option = echart_base("Productividad Acumulada por Hora")
            option["xAxis"] = {"type": "category", "data": [f"{h:02d}:00" for h in range(24)], "axisLabel": {"color": INK}}
            option["yAxis"] = {"type": "value", "splitLine": {"lineStyle": {"color": "#f1f5f9"}}}
            option["series"] = [
                {"name": "Total Acumulado", "type": "line", "data": cum_total.tolist(), "smooth": True, "label": {"show": True, "position": "top", "fontSize": 8, "fontWeight": "bold"}},
                {"name": "Comentarios Acumulados", "type": "line", "data": cum_com.tolist(), "smooth": True, "label": {"show": True, "position": "top", "fontSize": 8}},
                {"name": "Reposts Acumulados", "type": "line", "data": cum_rep.tolist(), "smooth": True, "label": {"show": True, "position": "top", "fontSize": 8}},
                {"name": "Participantes Únicos", "type": "line", "data": cum_unique, "symbolSize": 0, "lineStyle": {"width": 0}, "showSymbol": False},
                {"name": "Variación vs Hora Anterior", "type": "line", "data": var_total, "symbolSize": 0, "lineStyle": {"width": 0}, "showSymbol": False},
            ]
            render_echart(option, height=220, key="cum_hour_chart")
        
    with col2:
        # Chart 2: Stacked bar comments vs reposts by ARMY
        with st.container(border=True):
            army_total = day_df.groupby(["army_resuelto", "tipo_participacion_normalizado"]).size().unstack(fill_value=0).reindex(columns=["COMENTARIO", "REPOST"], fill_value=0)
            army_total["total"] = army_total["COMENTARIO"] + army_total["REPOST"]
            army_total = army_total.sort_values("total", ascending=True) # Ascending because horizontal bar renders bottom-to-top

            armies = army_total.index.tolist()

            option = echart_base("Productividad por ARMY")
            option["grid"] = {"top": 35, "left": 15, "right": 25, "bottom": 10, "containLabel": True}
            option["xAxis"] = {"type": "value", "splitLine": {"lineStyle": {"color": "#f1f5f9"}}}
            option["yAxis"] = {
                "type": "category",
                "data": armies,
                "axisLabel": {"color": INK, "fontSize": 9, "fontWeight": "600", "overflow": "truncate", "width": 110, "fontFamily": "Inter"},
                "axisTick": {"show": False},
                "axisLine": {"show": False},
            }
            option["series"] = [
                {"name": "COMENTARIO", "type": "bar", "stack": "army", "data": army_total["COMENTARIO"].tolist(), "barMaxWidth": 20, "label": {"show": True, "position": "insideRight", "fontSize": 8, "color": "#ffffff"}},
                {"name": "REPOST", "type": "bar", "stack": "army", "data": army_total["REPOST"].tolist(), "barMaxWidth": 20, "label": {"show": True, "position": "insideRight", "fontSize": 8, "color": "#ffffff"}}
            ]
            render_echart(option, height=220, key="army_stacked_chart")

    col3, col4 = st.columns(2)
    
    with col3:
        # Chart 3: Top 15 participants
        with st.container(border=True):
            top15 = daily_tracking.sort_values("Interacciones", ascending=False).head(15)
            top15 = top15.sort_values("Interacciones", ascending=True) # for bottom-to-top rendering

            names_list = []
            for idx, row in top15.iterrows():
                if row[MATCH_COL]:
                    names_list.append(row[PERSON_COL])
                else:
                    names_list.append(f"Contacto no identificado: {row[JOIN_KEY_COL]}")

            option = echart_base("Ranking de Participantes (Top 15)")
            option["grid"] = {"top": 35, "left": 15, "right": 25, "bottom": 10, "containLabel": True}
            option["xAxis"] = {"type": "value", "splitLine": {"lineStyle": {"color": "#f1f5f9"}}}
            option["yAxis"] = {
                "type": "category",
                "data": names_list,
                "axisLabel": {"color": INK, "fontSize": 9, "fontWeight": "600", "overflow": "truncate", "width": 130, "fontFamily": "Inter"},
                "axisTick": {"show": False},
                "axisLine": {"show": False},
            }
            option["series"] = [
                {"name": "Interacciones", "type": "bar", "data": top15["Interacciones"].tolist(), "barMaxWidth": 14, "itemStyle": {"borderRadius": [0, 4, 4, 0]}, "label": {"show": True, "position": "right", "fontSize": 8, "fontWeight": "bold", "color": INK}}
            ]
            render_echart(option, height=220, key="top15_participants_chart")
        
    with col4:
        # Chart 4: Heatmap por hora y ARMY
        with st.container(border=True):
            heatmap_armies = sorted(day_df["army_resuelto"].dropna().unique().tolist())
            heat_data = []
            heat_values = []
            for r_idx, army in enumerate(heatmap_armies):
                army_df = day_df[day_df["army_resuelto"] == army]
                hour_counts = army_df.groupby("hora_bloque").size().reindex(range(24), fill_value=0)
                for c_idx, count in enumerate(hour_counts):
                    count = int(count)
                    heat_values.append(count)
                    heat_data.append({
                        "value": [c_idx, r_idx, count],
                        "label": {"show": count > 0, "formatter": str(count)},
                    })

            option = echart_base("Mapa de Calor por Hora y ARMY")
            option["grid"] = {"top": 35, "left": 15, "right": 15, "bottom": 16, "containLabel": True}
            option["xAxis"] = {
                "type": "category", 
                "data": [f"{h:02d}:00" for h in range(24)], 
                "axisLabel": {"color": INK, "fontSize": 9, "fontFamily": "Inter", "rotate": 0}
            }
            option["yAxis"] = {
                "type": "category", 
                "data": heatmap_armies, 
                "axisLabel": {"color": INK, "fontSize": 9, "width": 110, "overflow": "truncate", "fontFamily": "Inter"}
            }
            option["visualMap"] = {
                "show": False,
                "min": 0,
                "max": max(heat_values, default=1),
                "calculable": False,
                "inRange": {"color": ["#f8fafc", "#ffe5d9", "#ff6600"]}
            }
            option["series"] = [{
                "type": "heatmap",
                "data": heat_data,
                "label": {"show": True, "fontSize": 8, "fontWeight": "bold", "color": INK},
                "emphasis": {"itemStyle": {"shadowBlur": 10, "shadowColor": "rgba(0, 0, 0, 0.5)"}}
            }]
            heatmap_height = max(280, min(420, 150 + len(heatmap_armies) * 34))
            render_echart(option, height=heatmap_height, key="hour_army_heatmap")

    # Chart 5: Tendencia diaria
    st.markdown("<div class='section-title'>Tendencia de los Últimos Días</div>", unsafe_allow_html=True)
    with st.container(border=True):
        trend_df = enriched_df.groupby("fecha_registro").agg(
            Interacciones=("join_exitoso", "size"),
            Comentarios=("Es comentario", "sum"),
            Reposts=("Es repost", "sum"),
            Unicos=(JOIN_KEY_COL, "nunique")
        ).sort_index().tail(10)

        dates_labels = [d.strftime("%d-%m") for d in trend_df.index]

        option = echart_base("Evolución de Productividad y Participantes")
        option["xAxis"] = {"type": "category", "data": dates_labels, "axisLabel": {"color": INK}}
        option["yAxis"] = {"type": "value", "splitLine": {"lineStyle": {"color": "#f1f5f9"}}}
        option["series"] = [
            {"name": "Interacciones", "type": "line", "data": trend_df["Interacciones"].tolist(), "smooth": True, "label": {"show": True, "position": "top", "fontSize": 8, "fontWeight": "bold"}},
            {"name": "Comentarios", "type": "line", "data": trend_df["Comentarios"].tolist(), "smooth": True, "label": {"show": True, "position": "top", "fontSize": 8}},
            {"name": "Reposts", "type": "line", "data": trend_df["Reposts"].tolist(), "smooth": True, "label": {"show": True, "position": "top", "fontSize": 8}},
            {"name": "Part. Únicos", "type": "line", "data": trend_df["Unicos"].tolist(), "smooth": True, "label": {"show": True, "position": "top", "fontSize": 8}}
        ]
        render_echart(option, height=200, key="daily_trend_chart")

    # Tables Section
    st.markdown("<div class='section-title'>Tabla de Productividad Diaria</div>", unsafe_allow_html=True)
    with st.container(border=True):

        # Aggregate fields for presentation
        # Persona, Número de contacto, ARMY, Estatus, Comentarios, Reposts, Total de acciones, Eventos distintos,
        # Primera interacción, Última interacción, Cantidad de evidencias, Promedio de acciones por evento, Estado de identificación, Alerta de calidad
        grid_rows = []
        for join_key, grp in day_df.groupby(JOIN_KEY_COL):
            matched = grp["join_exitoso"].iloc[0]
            first_row = grp.iloc[0]

            name = first_row[PERSON_COL]
            contact = first_row[CONTACT_COL]
            army = first_row["army_resuelto"]
            status = first_row["estatus_resuelto"]

            coms = grp["Es comentario"].sum()
            reps = grp["Es repost"].sum()
            total = len(grp)
            events = grp["evento_key"].nunique()

            first_int = grp[TIMESTAMP_COL].min()
            last_int = grp[TIMESTAMP_COL].max()

            evidences = grp["Tiene evidencia"].sum()
            avg_actions_per_event = round(total / events, 2) if events > 0 else 0.0

            grid_rows.append({
                "Persona": name,
                "Número de contacto": contact,
                "ARMY": army,
                "Estatus": status,
                "Comentarios": int(coms),
                "Reposts": int(reps),
                "Total de acciones": int(total),
                "Eventos distintos": int(events),
                "Primera interacción": first_int,
                "Última interacción": last_int,
                "Cantidad de evidencias": int(evidences),
                "Promedio de acciones por evento": avg_actions_per_event,
                "Estado de identificación": matched,
                "Alerta de calidad": first_row["calidad_registro"]
            })

        grid_df = pd.DataFrame(grid_rows)
        if grid_df.empty:
            grid_df = pd.DataFrame(columns=["Persona", "Número de contacto", "ARMY", "Estatus", "Comentarios", "Reposts", "Total de acciones", "Eventos distintos", "Primera interacción", "Última interacción", "Cantidad de evidencias", "Promedio de acciones por evento", "Estado de identificación", "Alerta de calidad"])

        render_grid(grid_df.sort_values("Total de acciones", ascending=False), height=300, key="daily_prod_table")

    # Silent agents section
    st.markdown("<div class='section-title'>Participantes sin Actividad</div>", unsafe_allow_html=True)
    with st.container(border=True):

        # base activa agents (filtered_agents) who had NO interactions on selected_day
        active_agent_contacts = set(active_agents[JOIN_KEY_COL].tolist())
        day_contacts = set(day_df[JOIN_KEY_COL].tolist())
        silent_contacts = active_agent_contacts - day_contacts

        silent_rows = []
        if silent_contacts:
            silent_agents_df = active_agents[active_agents[JOIN_KEY_COL].isin(silent_contacts)]
            for idx, row in silent_agents_df.iterrows():
                c_key = row[JOIN_KEY_COL]
                # Find last activity date for this agent in history
                agent_history = enriched_df[enriched_df[JOIN_KEY_COL] == c_key]
                if not agent_history.empty:
                    last_act = agent_history["fecha_registro"].max()
                    days_since = (selected_day - last_act).days
                    events_count = agent_history["evento_key"].nunique()
                    state = "SIN ACTIVIDAD HOY" if days_since == 0 else "SIN ACTIVIDAD EN EL PERIODO"
                else:
                    last_act = pd.NaT
                    days_since = pd.NA
                    events_count = 0
                    state = "SIN ACTIVIDAD"

                silent_rows.append({
                    "Nombre": row[AGENT_NAME_COL],
                    "Contacto": row[AGENT_CONTACT_COL],
                    "ARMY": row[AGENT_ARMY_COL],
                    "Estatus": row[STATUS_COL],
                    "Última fecha en la que registró actividad": last_act,
                    "Días desde la última actividad": days_since,
                    "Cantidad de eventos realizados en el periodo": events_count,
                    "Estado": state
                })

        silent_df = pd.DataFrame(silent_rows)
        if silent_df.empty:
            silent_df = pd.DataFrame(columns=["Nombre", "Contacto", "ARMY", "Estatus", "Última fecha en la que registró actividad", "Días desde la última actividad", "Cantidad de eventos realizados en el periodo", "Estado"])

        render_grid(silent_df, height=240, key="silent_agents_table")

def render_compliance_tab(
    control_df: pd.DataFrame,
    selected_day: object,
    selected_event: str,
    selected_armies: list[str],
    selected_rrss: str,
    selected_participant: str,
    selected_status: str
) -> None:
    # Filter control data
    filtered_ctrl = control_df.copy()
    
    if selected_day:
        filtered_ctrl = filtered_ctrl[filtered_ctrl[CONTROL_DATE_COL] == selected_day]
    if selected_event != "Todos":
        filtered_ctrl = filtered_ctrl[filtered_ctrl["evento_mostrar"] == selected_event]
    if selected_armies:
        filtered_ctrl = filtered_ctrl[filtered_ctrl[CONTROL_ARMY_COL].isin(selected_armies)]
    if selected_rrss != "Todos":
        filtered_ctrl = filtered_ctrl[filtered_ctrl[CONTROL_NETWORK_COL] == selected_rrss]
    if selected_participant != "Todos":
        filtered_ctrl = filtered_ctrl[filtered_ctrl[CONTROL_PERSON_COL] == selected_participant]
    if selected_status != "Todos":
        filtered_ctrl = filtered_ctrl[filtered_ctrl["estado_cumplimiento"] == selected_status]

    # Metrics
    considered = filtered_ctrl.shape[0]
    com_log = filtered_ctrl["comentarios_logrados"].sum()
    rep_log = filtered_ctrl["reposts_logrados"].sum()
    total_log = filtered_ctrl["total_logrado"].sum()
    
    # Calculate objectives excluding NA
    com_obj_series = filtered_ctrl["comentarios_objetivo"].dropna()
    rep_obj_series = filtered_ctrl["reposts_objetivo"].dropna()
    
    com_obj_val = com_obj_series.sum()
    rep_obj_val = rep_obj_series.sum()
    
    total_obj_series = filtered_ctrl["total_objetivo"].dropna()
    total_obj_val = total_obj_series.sum()
    
    # Compliance %
    comp_pct = total_log / total_obj_val if total_obj_val > 0 else 0.0
    
    met_count = filtered_ctrl[filtered_ctrl["estado_cumplimiento"] == "CUMPLIDO"].shape[0]
    no_goal_count = filtered_ctrl[filtered_ctrl["estado_cumplimiento"] == "SIN OBJETIVO CARGADO"].shape[0]

    render_kpi_cards([
        {
            "icon": "fluent-emoji-flat:check-mark-button",
            "value": format_int(considered),
            "label": "Part. Considerados",
            "subtitle": f"{met_count} cumplieron",
        },
        {
            "icon": "fluent-emoji-flat:bar-chart",
            "value": f"{format_int(total_log)} / {format_int(total_obj_val)}",
            "label": "Logrado vs Objetivo",
            "subtitle": f"Com: {format_int(com_log)}/{format_int(com_obj_val)} · Rep: {format_int(rep_log)}/{format_int(rep_obj_val)}",
        },
        {
            "icon": "fluent-emoji-flat:chart-increasing",
            "value": f"{comp_pct:.1%}" if total_obj_val > 0 else "N/A",
            "label": "Cumplimiento Total",
            "subtitle": "Avance de objetivos",
        },
        {
            "icon": "fluent-emoji-flat:warning",
            "value": format_int(no_goal_count),
            "label": "Sin Objetivo Cargado",
            "subtitle": "Requieren configuración",
        }
    ])

    # Show warning if any selected event is missing objectives
    events_missing_goals = filtered_ctrl[filtered_ctrl["estado_cumplimiento"] == "SIN OBJETIVO CARGADO"]["evento_mostrar"].unique()
    if len(events_missing_goals) > 0:
        st.warning(f"⚠️ Objetivo no configurado para los siguientes eventos: {', '.join(events_missing_goals)}")

    # Charts Section
    st.markdown("<div class='section-title'>Visualizaciones de Cumplimiento</div>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    
    with col1:
        # Chart 1: Logrado vs Objetivo por evento
        with st.container(border=True):
            by_event = filtered_ctrl.groupby("evento_mostrar").agg(
                Logrado=("total_logrado", "sum"),
                Objetivo=("total_objetivo", lambda s: s.dropna().sum())
            ).sort_values("Logrado", ascending=True)

            events_list = by_event.index.tolist()

            option = echart_base("Logrado vs Objetivo por Evento")
            option["grid"] = {"top": 35, "left": 15, "right": 25, "bottom": 10, "containLabel": True}
            option["xAxis"] = {"type": "value", "splitLine": {"lineStyle": {"color": "#f1f5f9"}}}
            option["yAxis"] = {
                "type": "category",
                "data": events_list,
                "axisLabel": {"color": INK, "fontSize": 9, "fontWeight": "600", "overflow": "truncate", "width": 120, "fontFamily": "Inter"},
                "axisTick": {"show": False},
                "axisLine": {"show": False},
            }
            option["series"] = [
                {"name": "Logrado", "type": "bar", "data": by_event["Logrado"].tolist(), "barMaxWidth": 14},
                {"name": "Objetivo", "type": "bar", "data": by_event["Objetivo"].tolist(), "barMaxWidth": 14}
            ]
            render_echart(option, height=220, key="log_vs_obj_event")
        
    with col2:
        # Chart 2: Logrado vs Objetivo por ARMY
        with st.container(border=True):
            by_army = filtered_ctrl.groupby(CONTROL_ARMY_COL).agg(
                Logrado=("total_logrado", "sum"),
                Objetivo=("total_objetivo", lambda s: s.dropna().sum())
            ).sort_values("Logrado", ascending=True)

            armies_list = by_army.index.tolist()

            option = echart_base("Logrado vs Objetivo por ARMY")
            option["grid"] = {"top": 35, "left": 15, "right": 25, "bottom": 10, "containLabel": True}
            option["xAxis"] = {"type": "value", "splitLine": {"lineStyle": {"color": "#f1f5f9"}}}
            option["yAxis"] = {
                "type": "category",
                "data": armies_list,
                "axisLabel": {"color": INK, "fontSize": 9, "fontWeight": "600", "overflow": "truncate", "width": 110, "fontFamily": "Inter"},
                "axisTick": {"show": False},
                "axisLine": {"show": False},
            }
            option["series"] = [
                {"name": "Logrado", "type": "bar", "data": by_army["Logrado"].tolist(), "barMaxWidth": 14},
                {"name": "Objetivo", "type": "bar", "data": by_army["Objetivo"].tolist(), "barMaxWidth": 14}
            ]
            render_echart(option, height=220, key="log_vs_obj_army")

    col3, col4 = st.columns(2)
    
    with col3:
        # Chart 3: Mix por RRSS
        with st.container(border=True):
            by_net = filtered_ctrl.groupby(CONTROL_NETWORK_COL)["total_logrado"].sum().reset_index()
            option = echart_base("Distribución por Red Social")
            option["tooltip"] = {"trigger": "item", "formatter": "{b}: {c} ({d}%)"}
            option["series"] = [{
                "type": "pie",
                "radius": ["40%", "65%"],
                "data": [{"name": str(row[CONTROL_NETWORK_COL]), "value": float(row["total_logrado"])} for _, row in by_net.iterrows()]
            }]
            render_echart(option, height=200, key="net_donut_chart")
        
    with col4:
        # Chart 4: % cumplido donut chart
        with st.container(border=True):
            status_counts = filtered_ctrl["estado_cumplimiento"].value_counts().reset_index()
            option = echart_base("Proporción de Estado de Cumplimiento")
            option["tooltip"] = {"trigger": "item", "formatter": "{b}: {c} ({d}%)"}
            option["series"] = [{
                "type": "pie",
                "radius": ["40%", "65%"],
                "data": [{"name": str(row["estado_cumplimiento"]), "value": float(row["count"])} for _, row in status_counts.iterrows()]
            }]
            render_echart(option, height=200, key="status_donut_chart")

    col5, col6 = st.columns(2)
    
    with col5:
        # Chart 5: Ranking de participantes por cumplimiento
        with st.container(border=True):
            top_compl = filtered_ctrl.dropna(subset=["cumplimiento_pct"]).sort_values("cumplimiento_pct", ascending=False).head(15)
            top_compl = top_compl.sort_values("cumplimiento_pct", ascending=True)
            option = echart_base("Top 15 Participantes por % Cumplimiento")
            option["grid"] = {"top": 35, "left": 15, "right": 25, "bottom": 10, "containLabel": True}
            option["xAxis"] = {"type": "value", "splitLine": {"lineStyle": {"color": "#f1f5f9"}}}
            option["yAxis"] = {
                "type": "category",
                "data": top_compl[CONTROL_PERSON_COL].tolist(),
                "axisLabel": {"color": INK, "fontSize": 9, "fontWeight": "600", "overflow": "truncate", "width": 130, "fontFamily": "Inter"},
            }
            option["series"] = [
                {"name": "Cumplimiento", "type": "bar", "data": [float(v*100) for v in top_compl["cumplimiento_pct"]], "barMaxWidth": 14}
            ]
            render_echart(option, height=220, key="top_compliance_ranking")
        
    with col6:
        # Chart 6: Heatmap de participante por evento
        with st.container(border=True):
            heat_pp = sorted(filtered_ctrl[CONTROL_PERSON_COL].dropna().unique().tolist())[:15] # Top 15 alphabetically or filtered
            heat_evs = sorted(filtered_ctrl["evento_mostrar"].dropna().unique().tolist())

            heat_data = []
            for r_idx, pp in enumerate(heat_pp):
                for c_idx, ev in enumerate(heat_evs):
                    match_row = filtered_ctrl[(filtered_ctrl[CONTROL_PERSON_COL] == pp) & (filtered_ctrl["evento_mostrar"] == ev)]
                    if not match_row.empty:
                        val = match_row["cumplimiento_pct"].dropna().iloc[0] if not pd.isna(match_row["cumplimiento_pct"].iloc[0]) else 0.0
                    else:
                        val = 0.0
                    heat_data.append({
                        "value": [c_idx, r_idx, float(val)],
                        "label": {"show": True, "formatter": f"{float(val) * 100:.0f}%"},
                    })

            option = echart_base("Mapa de Cumplimiento (Participante x Evento)")
            option["grid"] = {"top": 35, "left": 15, "right": 25, "bottom": 45, "containLabel": True}
            option["xAxis"] = {
                "type": "category", 
                "data": heat_evs, 
                "axisLabel": {"color": INK, "fontSize": 9, "width": 80, "overflow": "truncate", "rotate": 0}
            }
            option["yAxis"] = {
                "type": "category", 
                "data": heat_pp, 
                "axisLabel": {"color": INK, "fontSize": 9, "width": 120, "overflow": "truncate"}
            }
            option["visualMap"] = {
                "show": False,
                "min": 0,
                "max": 1,
                "calculable": False,
                "inRange": {"color": ["#fee2e2", "#fef3c7", "#d1fae5"]}
            }
            option["series"] = [{
                "type": "heatmap",
                "data": heat_data,
                "label": {"show": True, "fontSize": 8, "fontWeight": "bold", "color": INK}
            }]
            compliance_heatmap_height = max(340, min(540, 120 + len(heat_pp) * 24))
            render_echart(option, height=compliance_heatmap_height, key="pp_event_heatmap")

    # Detailed table
    st.markdown("<div class='section-title'>Tabla de Cumplimiento Detallado</div>", unsafe_allow_html=True)
    with st.container(border=True):

        # Columns: Fecha, Evento, Participante, Contacto, ARMY, RRSS, Comentarios logrados, Comentarios objetivo,
        # Comentarios faltantes, Reposts logrados, Reposts objetivo, Reposts faltantes, Total logrado, Total objetivo, Cumplimiento, Estado, Hashtags
        table_df = filtered_ctrl[[
            CONTROL_DATE_COL,
            "evento_mostrar",
            CONTROL_PERSON_COL,
            CONTROL_CONTACT_COL,
            CONTROL_ARMY_COL,
            CONTROL_NETWORK_COL,
            "comentarios_logrados",
            "comentarios_objetivo",
            "comentarios_faltantes",
            "reposts_logrados",
            "reposts_objetivo",
            "reposts_faltantes",
            "total_logrado",
            "total_objetivo",
            "cumplimiento_pct",
            "estado_cumplimiento",
            CONTROL_HASHTAGS_COL
        ]].copy()

        table_df = table_df.rename(columns={
            "evento_mostrar": "Evento",
            CONTROL_PERSON_COL: "Participante",
            CONTROL_CONTACT_COL: "Contacto",
            CONTROL_ARMY_COL: "ARMY",
            CONTROL_NETWORK_COL: "RRSS",
            "comentarios_logrados": "Comentarios logrados",
            "comentarios_objetivo": "Comentarios objetivo",
            "comentarios_faltantes": "Comentarios faltantes",
            "reposts_logrados": "Reposts logrados",
            "reposts_objetivo": "Reposts objetivo",
            "reposts_faltantes": "Reposts faltantes",
            "total_logrado": "Total logrado",
            "total_objetivo": "Total objetivo",
            "cumplimiento_pct": "Cumplimiento",
            "estado_cumplimiento": "Estado",
            CONTROL_HASHTAGS_COL: "Hashtags"
        })

        render_grid(table_df, height=320, key="compliance_detail_grid")

def render_planning_tab(
    matches_df: pd.DataFrame,
    start_date: object,
    end_date: object,
    selected_phase: str,
    selected_match: str,
    selected_rrss: str,
    selected_profile: str,
    selected_pressure: str
) -> None:
    # Filter matches
    filtered_matches = matches_df.copy()
    
    if start_date and end_date:
        filtered_matches = filtered_matches[(filtered_matches[MATCH_DATE_COL] >= start_date) & (filtered_matches[MATCH_DATE_COL] <= end_date)]
    if selected_phase != "Todos":
        filtered_matches = filtered_matches[filtered_matches[MATCH_PHASE_COL] == selected_phase]
    if selected_match != "Todos":
        filtered_matches = filtered_matches[filtered_matches[MATCH_NAME_COL] == selected_match]
    if selected_rrss != "Todos":
        filtered_matches = filtered_matches[filtered_matches[MATCH_NETWORK_COL] == selected_rrss]
    if selected_profile != "Todos":
        filtered_matches = filtered_matches[filtered_matches["Tipo de perfil"] == selected_profile]
    if selected_pressure != "Todos":
        filtered_matches = filtered_matches[filtered_matches["Nivel de presión"] == selected_pressure]

    # KPIs next match
    today = datetime.now(TIMEZONE).date()
    upcoming = matches_df[matches_df[MATCH_DATE_COL] >= today].copy()
    if upcoming.empty:
        upcoming = matches_df.copy()
        
    next_match = upcoming.iloc[0] if not upcoming.empty else None
    
    if next_match is not None:
        next_match_name = next_match[MATCH_NAME_COL]
        next_match_date = next_match[MATCH_DATE_COL].strftime("%d/%m/%Y")
        next_match_time = next_match[MATCH_TIME_COL]
        next_match_actions = next_match[MATCH_TOTAL_ACTIONS_COL]
        next_match_pressure = next_match["Nivel de presión"]
    else:
        next_match_name = "Sin partidos"
        next_match_date = "N/A"
        next_match_time = "N/A"
        next_match_actions = 0
        next_match_pressure = "N/A"

    render_kpi_cards([
        {
            "icon": "fluent-emoji-flat:soccer-ball",
            "value": next_match_name,
            "label": "Próximo Partido",
            "subtitle": f"{next_match_date} a las {next_match_time}",
        },
        {
            "icon": "fluent-emoji-flat:bullseye",
            "value": format_int(next_match_actions),
            "label": "Acciones Planificadas",
            "subtitle": "Para el próximo partido",
        },
        {
            "icon": "fluent-emoji-flat:fire",
            "value": next_match_pressure,
            "label": "Presión del Encuentro",
            "subtitle": "Nivel de exigencia",
        },
        {
            "icon": "fluent-emoji-flat:check-mark-button",
            "value": format_int(filtered_matches.shape[0]),
            "label": "Partidos Filtrados",
            "subtitle": f"Rango: {start_date} a {end_date}",
        }
    ])

    # Charts Section
    st.markdown("<div class='section-title'>Análisis de Planificación de Partidos</div>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    
    with col1:
        # Chart 1: Actions planified by date
        with st.container(border=True):
            by_date = filtered_matches.groupby(MATCH_DATE_COL)[MATCH_TOTAL_ACTIONS_COL].sum().reset_index()
            by_date["FechaLabel"] = by_date[MATCH_DATE_COL].apply(lambda d: d.strftime("%d-%m"))
            option = echart_base("Acciones Planificadas por Fecha")
            option["xAxis"] = {"type": "category", "data": by_date["FechaLabel"].tolist()}
            option["yAxis"] = {"type": "value"}
            option["series"] = [{"name": "Acciones", "type": "line", "data": by_date[MATCH_TOTAL_ACTIONS_COL].tolist(), "smooth": True, "label": {"show": True, "position": "top", "fontSize": 8, "fontWeight": "bold"}}]
            render_echart(option, height=200, key="plan_actions_by_date")
        
    with col2:
        # Chart 2: Actions by match
        with st.container(border=True):
            by_match = filtered_matches.groupby(MATCH_NAME_COL)[MATCH_TOTAL_ACTIONS_COL].sum().sort_values(ascending=False).head(10)
            option = echart_base("Acciones por Partido (Top 10)")
            option["grid"] = {"top": 35, "left": 15, "right": 25, "bottom": 10, "containLabel": True}
            option["xAxis"] = {"type": "value", "splitLine": {"lineStyle": {"color": "#f1f5f9"}}}
            option["yAxis"] = {
                "type": "category",
                "data": by_match.index.tolist(),
                "axisLabel": {"color": INK, "fontSize": 9, "fontWeight": "600", "overflow": "truncate", "width": 120, "fontFamily": "Inter"},
                "axisTick": {"show": False},
                "axisLine": {"show": False},
            }
            option["series"] = [{"name": "Acciones", "type": "bar", "data": by_match.tolist(), "barMaxWidth": 14, "label": {"show": True, "position": "right", "fontSize": 8, "fontWeight": "bold"}}]
            render_echart(option, height=200, key="plan_actions_by_match")

    col3, col4, col5 = st.columns(3)
    
    with col3:
        # Chart 3: Social Network Distribution
        with st.container(border=True):
            by_net = filtered_matches.groupby(MATCH_NETWORK_COL)[MATCH_TOTAL_ACTIONS_COL].sum().reset_index()
            option = echart_base("Distribución por Red Social")
            option["tooltip"] = {"trigger": "item"}
            option["series"] = [{"type": "pie", "radius": ["40%", "65%"], "data": [{"name": str(row[MATCH_NETWORK_COL]), "value": float(row[MATCH_TOTAL_ACTIONS_COL])} for _, row in by_net.iterrows()]}]
            render_echart(option, height=200, key="plan_net_donut")
        
    with col4:
        # Chart 4: Profile type distribution
        with st.container(border=True):
            by_prof = filtered_matches.groupby("Tipo de perfil")[MATCH_TOTAL_ACTIONS_COL].sum().reset_index()
            option = echart_base("Distribución por Tipo de Perfil")
            option["tooltip"] = {"trigger": "item"}
            option["series"] = [{"type": "pie", "radius": ["40%", "65%"], "data": [{"name": str(row["Tipo de perfil"]), "value": float(row[MATCH_TOTAL_ACTIONS_COL])} for _, row in by_prof.iterrows()]}]
            render_echart(option, height=200, key="plan_profile_donut")
        
    with col5:
        # Chart 5: Pressure level load
        with st.container(border=True):
            by_press = filtered_matches.groupby("Nivel de presión")[MATCH_TOTAL_ACTIONS_COL].sum().reset_index()
            option = echart_base("Acciones por Nivel de Presión")
            option["xAxis"] = {"type": "category", "data": by_press["Nivel de presión"].tolist()}
            option["yAxis"] = {"type": "value"}
            option["series"] = [{"name": "Acciones", "type": "bar", "data": by_press[MATCH_TOTAL_ACTIONS_COL].tolist(), "barMaxWidth": 14, "label": {"show": True, "position": "top", "fontSize": 8, "fontWeight": "bold"}}]
            render_echart(option, height=200, key="plan_pressure_bar")

    # matches table
    st.markdown("<div class='section-title'>Calendario Operativo de Partidos</div>", unsafe_allow_html=True)
    with st.container(border=True):
        render_grid(
            filtered_matches[[
                MATCH_DATE_COL,
                MATCH_TIME_COL,
                MATCH_NAME_COL,
                MATCH_PHASE_COL,
                "Grupo",
                "País y ciudad",
                MATCH_IMPORTANCE_COL,
                "Nivel de presión",
                MATCH_NETWORK_COL,
                "Tipo de perfil",
                "N° perfiles",
                MATCH_TOTAL_ACTIONS_COL
            ]],
            height=320,
            key="planning_schedule_grid"
        )

def render_quality_tab(
    raw_interactions: pd.DataFrame,
    raw_agents: pd.DataFrame,
    raw_control: pd.DataFrame,
    raw_matches: pd.DataFrame,
    enriched_df: pd.DataFrame,
    agents: pd.DataFrame
) -> None:
    st.markdown("<div class='section-title'>Auditoría de Inconsistencias y Calidad de Datos</div>", unsafe_allow_html=True)
    
    # Generate audit report
    audit_report = generate_quality_report(
        raw_interactions, 
        raw_agents, 
        raw_control, 
        raw_matches,
        enriched_df, 
        agents
    )
    
    if audit_report.empty:
        st.success("¡Excelente! No se han detectado inconsistencias en los conjuntos de datos analizados.")
    else:
        st.markdown("<p style='font-family: Inter; font-size: 0.75rem; color: #64748b; margin-top: -0.5rem; margin-bottom: 0.75rem;'>Resumen detallado de registros duplicados, teléfonos inválidos, nombres faltantes o fallas de cruces en hojas de cálculo.</p>", unsafe_allow_html=True)
        with st.container(border=True):
            render_grid(
                audit_report,
                height=360,
                key="quality_audit_grid"
            )

def generate_quality_report(
    raw_interactions: pd.DataFrame, 
    raw_agents: pd.DataFrame, 
    raw_control: pd.DataFrame, 
    raw_matches: pd.DataFrame,
    enriched_df: pd.DataFrame,
    agents: pd.DataFrame
) -> pd.DataFrame:
    records = []
    
    # 1. Interacciones sin participante identificado
    no_id = enriched_df[~enriched_df["join_exitoso"]]
    for idx, row in no_id.iterrows():
        records.append({
            "Hoja": INTERACTIONS_SHEET_NAME,
            "Número de fila": str(idx + 2),
            "Campo": CONTACT_COL,
            "Valor original": row[CONTACT_COL],
            "Tipo de problema": "Número de contacto no identificado en maestro BBDD_ARMY",
            "Corrección sugerida": "Registrar el número de contacto en la hoja BBDD_ARMY"
        })
        
    # 2. Interacciones con ARMY vacío
    empty_army = raw_interactions[raw_interactions[RESPONSE_ARMY_COL].str.strip() == ""]
    for idx, row in empty_army.iterrows():
        records.append({
            "Hoja": INTERACTIONS_SHEET_NAME,
            "Número de fila": str(idx + 2),
            "Campo": RESPONSE_ARMY_COL,
            "Valor original": "",
            "Tipo de problema": "Army vacío en formulario de interacción",
            "Corrección sugerida": "Definir el Army en el formulario o en el maestro"
        })
        
    # 3. Interacciones con ARMY igual a #N/A
    na_army = raw_interactions[raw_interactions[RESPONSE_ARMY_COL].str.upper() == "#N/A"]
    for idx, row in na_army.iterrows():
        records.append({
            "Hoja": INTERACTIONS_SHEET_NAME,
            "Número de fila": str(idx + 2),
            "Campo": RESPONSE_ARMY_COL,
            "Valor original": "#N/A",
            "Tipo de problema": "Valor de Army es #N/A",
            "Corrección sugerida": "Corregir fórmula o ingresar Army válido"
        })
        
    # 4. Contactos con longitud inválida
    for idx, row in raw_interactions.iterrows():
        c_key = solo_digitos(row[CONTACT_COL])
        if c_key and len(c_key) not in [8, 9]:
            records.append({
                "Hoja": INTERACTIONS_SHEET_NAME,
                "Número de fila": str(idx + 2),
                "Campo": CONTACT_COL,
                "Valor original": row[CONTACT_COL],
                "Tipo de problema": f"Longitud de teléfono incorrecta ({len(c_key)} dígitos)",
                "Corrección sugerida": "Revisar y corregir a 9 dígitos"
            })
            
    for idx, row in raw_agents.iterrows():
        c_key = solo_digitos(row[AGENT_CONTACT_COL])
        if c_key and len(c_key) not in [8, 9]:
            records.append({
                "Hoja": AGENTS_SHEET_NAME,
                "Número de fila": str(idx + 2),
                "Campo": AGENT_CONTACT_COL,
                "Valor original": row[AGENT_CONTACT_COL],
                "Tipo de problema": f"Longitud de teléfono incorrecta ({len(c_key)} dígitos)",
                "Corrección sugerida": "Revisar y corregir a 9 dígitos"
            })
            
    # 5. Contactos duplicados en el maestro BBDD_ARMY
    agents_c_keys = raw_agents[AGENT_CONTACT_COL].apply(solo_digitos)
    dup_contacts = agents_c_keys[agents_c_keys.duplicated(keep=False) & agents_c_keys.ne("")]
    for idx, row in raw_agents.iterrows():
        c_key = solo_digitos(row[AGENT_CONTACT_COL])
        if c_key in dup_contacts.values:
            records.append({
                "Hoja": AGENTS_SHEET_NAME,
                "Número de fila": str(idx + 2),
                "Campo": AGENT_CONTACT_COL,
                "Valor original": row[AGENT_CONTACT_COL],
                "Tipo de problema": "Contacto duplicado en el maestro",
                "Corrección sugerida": "Remover fila duplicada o unificar datos"
            })
            
    # 6. Nombres duplicados en el maestro BBDD_ARMY
    dup_names = raw_agents[raw_agents[AGENT_NAME_COL].duplicated(keep=False) & raw_agents[AGENT_NAME_COL].ne("")]
    for idx, row in raw_agents.iterrows():
        if row[AGENT_NAME_COL] in dup_names[AGENT_NAME_COL].values:
            records.append({
                "Hoja": AGENTS_SHEET_NAME,
                "Número de fila": str(idx + 2),
                "Campo": AGENT_NAME_COL,
                "Valor original": row[AGENT_NAME_COL],
                "Tipo de problema": "Nombre completo duplicado en el maestro",
                "Corrección sugerida": "Validar si es la misma persona"
            })
            
    # 7. Registros de CONTROL_DIARIO con contacto #N/A
    na_ctrl_contacts = raw_control[raw_control[CONTROL_CONTACT_COL].str.upper() == "#N/A"]
    for idx, row in na_ctrl_contacts.iterrows():
        records.append({
            "Hoja": DAILY_CONTROL_SHEET_NAME,
            "Número de fila": str(idx + 2),
            "Campo": CONTROL_CONTACT_COL,
            "Valor original": "#N/A",
            "Tipo de problema": "Contacto es #N/A en el plan",
            "Corrección sugerida": "Corregir fórmula en Excel"
        })
        
    # 8. Eventos con nombres inconsistentes
    for idx, row in raw_control.iterrows():
        ev = str(row[CONTROL_EVENT_COL]).strip()
        if "MEME BELGICA 1502" in ev.upper():
            records.append({
                "Hoja": DAILY_CONTROL_SHEET_NAME,
                "Número de fila": str(idx + 2),
                "Campo": CONTROL_EVENT_COL,
                "Valor original": row[CONTROL_EVENT_COL],
                "Tipo de problema": "Inconsistencia de fecha de evento (1502 vs 1506)",
                "Corrección sugerida": "Cambiar a MEME BELGICA 1506"
            })
        elif "MEME ESPAÑA 1502" in ev.upper() or "MEME ESPAÑA 1502" in ev:
            records.append({
                "Hoja": DAILY_CONTROL_SHEET_NAME,
                "Número de fila": str(idx + 2),
                "Campo": CONTROL_EVENT_COL,
                "Valor original": row[CONTROL_EVENT_COL],
                "Tipo de problema": "Inconsistencia de fecha de evento (1502 vs 1506)",
                "Corrección sugerida": "Cambiar a MEME ESPAÑA 1506"
            })
            
    # 9. Eventos sin objetivo
    comment_objectives = to_optional_number(raw_control[COMMENTS_GOAL_COL]).combine_first(
        to_optional_number(raw_control[COMMENTS_DONE_COL])
    )
    repost_objectives = to_optional_number(raw_control[REPOSTS_GOAL_COL]).combine_first(
        to_optional_number(raw_control[REPOSTS_DONE_COL])
    )
    na_goals = raw_control[comment_objectives.isna() & repost_objectives.isna()]
    for idx, row in na_goals.iterrows():
        records.append({
            "Hoja": DAILY_CONTROL_SHEET_NAME,
            "Número de fila": str(idx + 2),
            "Campo": f"{COMMENTS_GOAL_COL} / {REPOSTS_GOAL_COL}",
            "Valor original": "Vacío / #N/A",
            "Tipo de problema": "Objetivos no configurados para el evento",
            "Corrección sugerida": "Configurar objetivos o cargar el objetivo operativo en las columnas de comentarios/reposts"
        })
        
    # 10. Evidencias vacías en interacciones
    empty_ev = raw_interactions[raw_interactions[EVIDENCE_COL].str.strip() == ""]
    for idx, row in empty_ev.iterrows():
        records.append({
            "Hoja": INTERACTIONS_SHEET_NAME,
            "Número de fila": str(idx + 2),
            "Campo": EVIDENCE_COL,
            "Valor original": "",
            "Tipo de problema": "Evidencia vacía en interacción registrada",
            "Corrección sugerida": "Cargar link de la imagen de evidencia"
        })
        
    # 11. Evidencias duplicadas
    dup_ev = raw_interactions[raw_interactions[EVIDENCE_COL].duplicated(keep=False) & raw_interactions[EVIDENCE_COL].ne("")]
    for idx, row in raw_interactions.iterrows():
        if row[EVIDENCE_COL] in dup_ev[EVIDENCE_COL].values:
            records.append({
                "Hoja": INTERACTIONS_SHEET_NAME,
                "Número de fila": str(idx + 2),
                "Campo": EVIDENCE_COL,
                "Valor original": row[EVIDENCE_COL],
                "Tipo de problema": "Link de evidencia duplicado",
                "Corrección sugerida": "Revisar si es un registro repetido"
            })
            
    # 12. Registros exactos duplicados
    dup_rows = raw_interactions[raw_interactions.duplicated(keep=False)]
    for idx, row in raw_interactions.iterrows():
        is_dup = dup_rows.index.isin([idx]).any()
        if is_dup:
            records.append({
                "Hoja": INTERACTIONS_SHEET_NAME,
                "Número de fila": str(idx + 2),
                "Campo": "Fila completa",
                "Valor original": f"Contacto: {row[CONTACT_COL]} | Evento: {row[EVENT_COL]}",
                "Tipo de problema": "Fila de interacción duplicada exacta",
                "Corrección sugerida": "Eliminar fila duplicada en la hoja de origen"
            })
            
    return pd.DataFrame(records)

# Main Application Entrypoint

def render_historical_tab(enriched_df: pd.DataFrame, control_df: pd.DataFrame) -> None:
    st.markdown("<div class='section-title'>Resumen Histórico de Operaciones</div>", unsafe_allow_html=True)
    
    # Drop rows with null dates to prevent NaTType strftime errors
    clean_enriched = enriched_df.dropna(subset=["fecha_registro"])
    clean_control = control_df.dropna(subset=[CONTROL_DATE_COL])
    
    # 1. Calculate historical KPIs
    total_ints = len(clean_enriched)
    comments = clean_enriched[clean_enriched["tipo_participacion_normalizado"] == "COMENTARIO"].shape[0]
    reposts = clean_enriched[clean_enriched["tipo_participacion_normalizado"] == "REPOST"].shape[0]
    unique_staff = clean_enriched[JOIN_KEY_COL].nunique()
    
    tot_logged = clean_control["total_logrado"].sum()
    tot_obj = clean_control["total_objetivo"].dropna().sum()
    overall_comp = (tot_logged / tot_obj) if tot_obj > 0 else 0.0
    
    render_kpi_cards([
        {
            "icon": "fluent-emoji-flat:counterclockwise-arrows-button",
            "value": format_int(total_ints),
            "label": "Interacciones Históricas",
            "subtitle": f"Com: {format_int(comments)} · Rep: {format_int(reposts)}",
        },
        {
            "icon": "fluent-emoji-flat:check-mark-button",
            "value": f"{overall_comp*100:.1f}%",
            "label": "Tasa de Cumplimiento Global",
            "subtitle": f"Logrado: {format_int(tot_logged)} / {format_int(tot_obj)}",
        },
        {
            "icon": "fluent-emoji-flat:person-raising-hand",
            "value": format_int(unique_staff),
            "label": "Participantes Únicos",
            "subtitle": "Registraron al menos 1 acción",
        }
    ])
    
    # 2. Charts Section
    st.markdown("<div class='section-title'>Visualizaciones Históricas</div>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    # Chart 1: Daily Evolution of Interactions (Area chart)
    with col1:
        with st.container(border=True):
            hist_df = clean_enriched.groupby(["fecha_registro", "tipo_participacion_normalizado"]).size().unstack(fill_value=0)
            hist_df = hist_df.reindex(columns=["COMENTARIO", "REPOST"], fill_value=0)
            hist_df["Total"] = hist_df["COMENTARIO"] + hist_df["REPOST"]
            hist_df = hist_df.sort_index()
            
            dates = [d.strftime("%d/%m/%Y") for d in hist_df.index]
            com_data = hist_df["COMENTARIO"].tolist()
            rep_data = hist_df["REPOST"].tolist()
            tot_data = hist_df["Total"].tolist()
            
            option1 = echart_base("Evolución Temporal de Interacciones Diarias")
            option1["xAxis"] = {"type": "category", "data": dates, "axisLabel": {"color": INK}}
            option1["yAxis"] = {"type": "value", "splitLine": {"lineStyle": {"color": "#f1f5f9"}}}
            option1["series"] = [
                {"name": "Comentarios", "type": "line", "stack": "Total", "areaStyle": {"opacity": 0.15}, "data": com_data, "smooth": True, "label": {"show": True, "position": "inside", "fontSize": 8, "color": "#111827"}},
                {"name": "Reposts", "type": "line", "stack": "Total", "areaStyle": {"opacity": 0.15}, "data": rep_data, "smooth": True, "label": {"show": True, "position": "inside", "fontSize": 8, "color": "#111827"}},
                {"name": "Total Acción", "type": "line", "data": tot_data, "smooth": True, "label": {"show": True, "position": "top", "fontSize": 8, "fontWeight": "bold", "color": "#ff6600"}}
            ]
            render_echart(option1, height=220, key="hist_evolution_chart")
            
    # Chart 2: Goal compliance over time (Dual axis)
    with col2:
        with st.container(border=True):
            ctrl_hist = clean_control.groupby(CONTROL_DATE_COL).agg(
                Logrado=("total_logrado", "sum"),
                Objetivo=("total_objetivo", lambda s: s.dropna().sum())
            ).sort_index()
            
            ctrl_dates = [d.strftime("%d/%m/%Y") for d in ctrl_hist.index]
            log_data = ctrl_hist["Logrado"].tolist()
            obj_data = ctrl_hist["Objetivo"].tolist()
            comp_data = [(log / obj * 100) if obj > 0 else 0 for log, obj in zip(log_data, obj_data)]
            
            option2 = echart_base("Histórico de Cumplimiento de Objetivos")
            option2["grid"] = {"top": 58, "left": 12, "right": 18, "bottom": 14, "containLabel": True}
            option2["xAxis"] = {"type": "category", "data": ctrl_dates, "axisLabel": {"color": INK}}
            option2["yAxis"] = [
                {"type": "value", "name": "Acciones", "splitLine": {"lineStyle": {"color": "#f1f5f9"}}},
                {"type": "value", "name": "Cumplimiento %", "axisLabel": {"formatter": "{value}%"}, "splitLine": {"show": False}}
            ]
            option2["series"] = [
                {"name": "Logrado", "type": "bar", "data": log_data, "barMaxWidth": 14, "label": {"show": True, "position": "top", "fontSize": 8, "fontWeight": "bold"}},
                {"name": "Objetivo", "type": "bar", "data": obj_data, "barMaxWidth": 14, "label": {"show": True, "position": "top", "fontSize": 8, "color": "#475569"}},
                {"name": "Cumplimiento %", "type": "line", "yAxisIndex": 1, "data": [round(c, 1) for c in comp_data], "smooth": True, "label": {"show": True, "position": "right", "formatter": "{c}%", "fontSize": 8, "fontWeight": "bold", "color": "#065f46"}}
            ]
            render_echart(option2, height=240, key="hist_goals_compliance_chart")
            
    col3, col4 = st.columns(2)
    
    # Chart 3: Cumulative Productivity per ARMY
    with col3:
        with st.container(border=True):
            army_hist = clean_enriched.groupby("army_resuelto").size().sort_values(ascending=True)
            armies = army_hist.index.tolist()
            counts = army_hist.values.tolist()
            
            option3 = echart_base("Productividad Acumulada por ARMY")
            option3["grid"] = {"top": 35, "left": 15, "right": 35, "bottom": 10, "containLabel": True}
            option3["xAxis"] = {"type": "value", "splitLine": {"lineStyle": {"color": "#f1f5f9"}}}
            option3["yAxis"] = {
                "type": "category",
                "data": armies,
                "axisLabel": {"color": INK, "fontSize": 9, "fontWeight": "600", "overflow": "truncate", "width": 120, "fontFamily": "Inter"},
                "axisTick": {"show": False},
                "axisLine": {"show": False},
            }
            option3["series"] = [
                {"name": "Interacciones", "type": "bar", "data": counts, "barMaxWidth": 14, "itemStyle": {"borderRadius": [0, 4, 4, 0]}, "label": {"show": True, "position": "right", "fontSize": 8, "fontWeight": "bold", "color": INK}}
            ]
            render_echart(option3, height=220, key="hist_army_prod_chart")
            
    # Chart 4: Unique active staff daily
    with col4:
        with st.container(border=True):
            part_hist = clean_enriched.groupby("fecha_registro")[JOIN_KEY_COL].nunique().sort_index()
            part_dates = [d.strftime("%d/%m/%Y") for d in part_hist.index]
            part_counts = part_hist.values.tolist()
            
            option4 = echart_base("Participación Diaria (Personal Único)")
            option4["xAxis"] = {"type": "category", "data": part_dates, "axisLabel": {"color": INK}}
            option4["yAxis"] = {"type": "value", "splitLine": {"lineStyle": {"color": "#f1f5f9"}}}
            option4["series"] = [
                {"name": "Participantes Activos", "type": "line", "data": part_counts, "smooth": True, "areaStyle": {"opacity": 0.08}, "label": {"show": True, "position": "top", "fontSize": 8, "fontWeight": "bold"}}
            ]
            render_echart(option4, height=220, key="hist_participation_chart")
            
    # 3. Detailed historical data table
    st.markdown("<div class='section-title'>Tabla de Productividad Histórica Diaria</div>", unsafe_allow_html=True)
    
    table_rows = []
    clean_dates = sorted(clean_enriched["fecha_registro"].unique())
    for d in clean_dates:
        day_df = clean_enriched[clean_enriched["fecha_registro"] == d]
        coms = day_df[day_df["tipo_participacion_normalizado"] == "COMENTARIO"].shape[0]
        reps = day_df[day_df["tipo_participacion_normalizado"] == "REPOST"].shape[0]
        total = len(day_df)
        staff_active = day_df[JOIN_KEY_COL].nunique()
        
        day_ctrl = clean_control[clean_control[CONTROL_DATE_COL] == d]
        obj = day_ctrl["total_objetivo"].dropna().sum() if not day_ctrl.empty else 0.0
        comp = (total / obj) if obj > 0 else 0.0
        
        table_rows.append({
            "Fecha": d,
            "Total Interacciones": int(total),
            "Comentarios": int(coms),
            "Reposts": int(reps),
            "Participantes Activos": int(staff_active),
            "Objetivo Diario": int(obj),
            "Cumplimiento": float(comp)
        })
    table_df = pd.DataFrame(table_rows)
    if table_df.empty:
        table_df = pd.DataFrame(columns=["Fecha", "Total Interacciones", "Comentarios", "Reposts", "Participantes Activos", "Objetivo Diario", "Cumplimiento"])
    else:
        table_df = table_df.sort_values("Fecha", ascending=False)
        
    with st.container(border=True):
        render_grid(table_df, height=300, key="historical_summary_table")


def current_navigation_view() -> str:
    selector_view = st.session_state.get("navigation_view_selector")
    stored_view = st.session_state.get("navigation_view")
    view = selector_view if selector_view in VIEW_OPTIONS else stored_view

    if view not in VIEW_OPTIONS:
        view = VIEW_OPTIONS[0]

    st.session_state["navigation_view"] = view
    if "navigation_view_selector" not in st.session_state:
        st.session_state["navigation_view_selector"] = view
    return view


def render_filter_summary(items: list[tuple[str, str]], *, hint: str = "Filtros aplicados") -> None:
    chip_html = ""
    for label, value in items:
        chip_html += (
            "<div class='filter-chip'>"
            f"<span>{escape(str(label))}</span>"
            f"<strong title='{escape(str(value))}'>{escape(str(value))}</strong>"
            "</div>"
        )

    st.html(
        f"""
        <div class="filter-summary-card">
            <div class="filter-summary-head">
                <div class="filter-summary-title">Contexto activo</div>
                <div class="filter-summary-hint">{escape(hint)}</div>
            </div>
            <div class="filter-chip-row">
                {chip_html}
            </div>
        </div>
        """
    )


def render_view_tabs() -> None:
    st.html(
        """
        <div class="view-tabs-header">
            <div class="view-tabs-label">Vistas del dashboard</div>
            <div class="view-tabs-caption">Cambia de módulo sin abrir menús laterales</div>
        </div>
        """
    )
    selected_view = st.segmented_control(
        "Vistas del dashboard",
        VIEW_OPTIONS,
        key="navigation_view_selector",
        label_visibility="collapsed",
        width="stretch",
    )
    if selected_view in VIEW_OPTIONS:
        st.session_state["navigation_view"] = selected_view


def main() -> None:
    inject_styles()
    daily_goal = 5
    
    refresh_seconds = REFRESH_INTERVAL_SECONDS
    refresh_key = int(datetime.now(TIMEZONE).timestamp() // refresh_seconds)
    if st_autorefresh:
        st_autorefresh(interval=refresh_seconds * 1000, key="sheet_refresh")
        
    try:
        raw_interactions = load_sheet(INTERACTIONS_SHEET_NAME, INTERACTION_REQUIRED_COLUMNS, refresh_key)
        raw_agents = load_sheet(AGENTS_SHEET_NAME, AGENT_REQUIRED_COLUMNS, refresh_key)
        raw_control = load_sheet(DAILY_CONTROL_SHEET_NAME, DAILY_CONTROL_REQUIRED_COLUMNS, refresh_key)
        raw_matches = load_sheet(MATCHES_SHEET_NAME, MATCHES_REQUIRED_COLUMNS, refresh_key)
        dashboard_refreshed_at = datetime.now(TIMEZONE)
    except Exception as exc:
        st.error("No se pudo conectar a Google Sheets.")
        st.exception(exc)
        st.stop()

    # Pre-process datasets using clean transform layer
    interactions = prepare_interactions(raw_interactions)
    agents = prepare_agents(raw_agents)
    daily_control = prepare_daily_control(raw_control)
    matches = prepare_matches(raw_matches)
    enriched = enrich_interactions(interactions, agents)
    daily_control = apply_interaction_actuals_to_daily_control(daily_control, enriched)

    # Merge daily_control with agents to get Estatus and Activo
    daily_control = daily_control.merge(
        agents[[JOIN_KEY_COL, STATUS_COL, "Activo"]],
        on=JOIN_KEY_COL,
        how="left"
    )
    # Override status for retired/inactive agents so they are not considered as failing/incumplidos
    is_retired = daily_control[STATUS_COL] == "RETIRADO"
    is_inactive = daily_control[STATUS_COL] == "INACTIVO"
    daily_control.loc[is_retired, "estado_cumplimiento"] = "RETIRADO"
    daily_control.loc[is_inactive, "estado_cumplimiento"] = "INACTIVO"

    # 1. Header Layout
    render_top_header(enriched, agents, dashboard_refreshed_at)
    
    # 2. In-content navigation tabs
    view = current_navigation_view()
    
    # Render view-specific layouts
    if view == "Resumen Diario":
        # Form Filter container at the top
        with st.form("daily_filters_form"):
            col1, col2, col3, col4, col5, col6, col7, col8 = st.columns(
                (1.0, 1.2, 1.2, 1.2, 1.0, 1.2, 1.0, 1.0),
                vertical_alignment="bottom",
            )
            
            # Select Day
            valid_dates = sorted(enriched["fecha_registro"].dropna().unique().tolist(), reverse=True)
            f_day = col1.selectbox("Día Operativo", options=valid_dates, format_func=lambda d: d.strftime("%d/%m/%Y"))
            
            # Event filter
            event_options = ["Todos"] + sorted(enriched["evento_mostrar"].dropna().unique().tolist())
            f_event = col2.selectbox("Evento", options=event_options)
            
            # ARMY filter (multiselect popover)
            with col3:
                st.markdown("<p class='custom-widget-label'>Filtrar ARMY</p>", unsafe_allow_html=True)
                army_options = sorted(enriched["army_resuelto"].dropna().unique().tolist())
                f_armies = multiselect_popover("ARMY", options=army_options, key_prefix="daily_army")
                
            # Participant filter
            part_options = ["Todos"] + sorted(enriched["nombre_resuelto"].dropna().unique().tolist())
            f_participant = col4.selectbox("Participante", options=part_options)
            
            # Status filter
            status_options = sorted(enriched["estatus_resuelto"].dropna().unique().tolist())
            f_statuses = col5.selectbox("Estatus", options=["Todos"] + status_options)
            
            # Tipo Participación
            f_participation = col6.selectbox("Tipo Participación", options=["Todos", "COMENTARIO", "REPOST"])
            
            apply_btn = col7.form_submit_button("Aplicar", use_container_width=True, type="primary")
            
            clear_btn = col8.form_submit_button("Limpiar", use_container_width=True)
            
            # State management for form submission
            if "daily_applied" not in st.session_state or clear_btn:
                st.session_state["daily_applied"] = {
                    "day": valid_dates[0] if valid_dates else None,
                    "event": "Todos",
                    "armies": army_options,
                    "participant": "Todos",
                    "statuses": ["ACTIVO"], # default status: Activos
                    "participation": "Todos"
                }
                if clear_btn:
                    st.rerun()
                    
            if apply_btn:
                # Convert f_statuses to list
                sel_statuses = [f_statuses] if f_statuses != "Todos" else status_options
                st.session_state["daily_applied"] = {
                    "day": f_day,
                    "event": f_event,
                    "armies": f_armies,
                    "participant": f_participant,
                    "statuses": sel_statuses,
                    "participation": f_participation
                }
                
        # Text summary below form
        act = st.session_state["daily_applied"]
        day_str = act["day"].strftime("%d/%m/%Y") if act["day"] else "N/A"
        armies_str = "Todos" if len(act["armies"]) == len(army_options) else f"{len(act['armies'])} seleccionados"
        statuses_str = ", ".join(act["statuses"])
        render_filter_summary([
            ("Día operativo", day_str),
            ("Evento", act["event"]),
            ("ARMY", armies_str),
            ("Estatus", statuses_str),
            ("Tipo", act["participation"]),
        ])
        render_view_tabs()
        
        # Render Tab 1
        render_daily_progress_tab(
            enriched, 
            agents, 
            daily_goal,
            selected_day=act["day"],
            selected_armies=act["armies"],
            selected_statuses=act["statuses"],
            selected_participation=act["participation"],
            selected_event=act["event"],
            selected_participant=act["participant"]
        )
        
    elif view == "Cumplimiento por Evento":
        with st.form("compliance_filters_form"):
            col1, col2, col3, col4, col5, col6, col7, col8 = st.columns(
                (1.0, 1.2, 1.2, 1.2, 1.0, 1.2, 1.0, 1.0),
                vertical_alignment="bottom",
            )
            
            # Dates in control
            valid_ctrl_dates = sorted(daily_control[CONTROL_DATE_COL].dropna().unique().tolist(), reverse=True)
            f_day = col1.selectbox("Fecha Evento", options=["Todos"] + valid_ctrl_dates, format_func=lambda d: d if d == "Todos" else d.strftime("%d/%m/%Y"))
            
            # Event list
            ctrl_events = ["Todos"] + sorted(daily_control["evento_mostrar"].dropna().unique().tolist())
            f_event = col2.selectbox("Evento", options=ctrl_events)
            
            # ARMY
            with col3:
                st.markdown("<p class='custom-widget-label'>Filtrar ARMY</p>", unsafe_allow_html=True)
                ctrl_armies = sorted(daily_control[CONTROL_ARMY_COL].dropna().unique().tolist())
                f_armies = multiselect_popover("ARMY", options=ctrl_armies, key_prefix="compl_army")
                
            # RRSS
            ctrl_rrss = ["Todos"] + sorted(daily_control[CONTROL_NETWORK_COL].dropna().unique().tolist())
            f_rrss = col4.selectbox("Red Social", options=ctrl_rrss)
            
            # Participant
            ctrl_participants = ["Todos"] + sorted(daily_control[CONTROL_PERSON_COL].dropna().unique().tolist())
            f_participant = col5.selectbox("Participante", options=ctrl_participants)
            
            # Estatus Cumplimiento
            f_compliance_status = col6.selectbox("Cumplimiento", options=["Todos", "CUMPLIDO", "PARCIAL", "NO CUMPLIDO", "SIN OBJETIVO CARGADO", "SIN ACTIVIDAD"])
            
            apply_btn = col7.form_submit_button("Aplicar", use_container_width=True, type="primary")
            
            clear_btn = col8.form_submit_button("Limpiar", use_container_width=True)
            
            if "compliance_applied" not in st.session_state or clear_btn:
                st.session_state["compliance_applied"] = {
                    "day": "Todos",
                    "event": "Todos",
                    "armies": ctrl_armies,
                    "rrss": "Todos",
                    "participant": "Todos",
                    "status": "Todos"
                }
                if clear_btn:
                    st.rerun()
                    
            if apply_btn:
                st.session_state["compliance_applied"] = {
                    "day": f_day,
                    "event": f_event,
                    "armies": f_armies,
                    "rrss": f_rrss,
                    "participant": f_participant,
                    "status": f_compliance_status
                }
                
        # Text summary
        act = st.session_state["compliance_applied"]
        day_str = act["day"].strftime("%d/%m/%Y") if isinstance(act["day"], dt_module.date) else "Todos"
        armies_str = "Todos" if len(act["armies"]) == len(ctrl_armies) else f"{len(act['armies'])} seleccionados"
        render_filter_summary([
            ("Fecha evento", day_str),
            ("Evento", act["event"]),
            ("ARMY", armies_str),
            ("RRSS", act["rrss"]),
            ("Estatus", act["status"]),
        ])
        render_view_tabs()
        
        # Render compliance tab
        render_compliance_tab(
            daily_control,
            selected_day=act["day"] if act["day"] != "Todos" else None,
            selected_event=act["event"],
            selected_armies=act["armies"],
            selected_rrss=act["rrss"],
            selected_participant=act["participant"],
            selected_status=act["status"]
        )
        
    elif view == "Planificación de Partidos":
        with st.form("planning_filters_form"):
            col1, col2, col3, col4, col5, col6, col7, col8 = st.columns(
                (1.5, 1.1, 1.2, 1.1, 1.1, 1.1, 1.0, 1.0),
                vertical_alignment="bottom",
            )
            
            # Dates
            match_dates = sorted(matches[MATCH_DATE_COL].dropna().unique().tolist())
            min_match_date = match_dates[0] if match_dates else datetime.now().date()
            max_match_date = match_dates[-1] if match_dates else datetime.now().date()
            f_dates = col1.date_input("Fechas", value=(min_match_date, max_match_date))
            
            # Phase
            phase_options = ["Todos"] + sorted(matches[MATCH_PHASE_COL].dropna().unique().tolist())
            f_phase = col2.selectbox("Fase", options=phase_options)
            
            # Match
            match_names = ["Todos"] + sorted(matches[MATCH_NAME_COL].dropna().unique().tolist())
            f_match = col3.selectbox("Partido", options=match_names)
            
            # Network
            net_options = ["Todos"] + sorted(matches[MATCH_NETWORK_COL].dropna().unique().tolist())
            f_rrss = col4.selectbox("Red Social", options=net_options)
            
            # Profile Type
            profile_options = ["Todos"] + sorted(matches["Tipo de perfil"].dropna().unique().tolist())
            f_profile = col5.selectbox("Perfil", options=profile_options)
            
            # Pressure
            pressure_options = ["Todos"] + sorted(matches["Nivel de presión"].dropna().unique().tolist())
            f_pressure = col6.selectbox("Presión", options=pressure_options)
            
            apply_btn = col7.form_submit_button("Aplicar", use_container_width=True, type="primary")
            
            clear_btn = col8.form_submit_button("Limpiar", use_container_width=True)
            
            if "planning_applied" not in st.session_state or clear_btn:
                st.session_state["planning_applied"] = {
                    "start_date": min_match_date,
                    "end_date": max_match_date,
                    "phase": "Todos",
                    "match": "Todos",
                    "rrss": "Todos",
                    "profile": "Todos",
                    "pressure": "Todos"
                }
                if clear_btn:
                    st.rerun()
                    
            if apply_btn:
                # Handle single or range date input
                if isinstance(f_dates, (tuple, list)) and len(f_dates) == 2:
                    s_d, e_d = f_dates
                elif isinstance(f_dates, (tuple, list)) and len(f_dates) == 1:
                    s_d = e_d = f_dates[0]
                else:
                    s_d = e_d = f_dates
                    
                st.session_state["planning_applied"] = {
                    "start_date": s_d,
                    "end_date": e_d,
                    "phase": f_phase,
                    "match": f_match,
                    "rrss": f_rrss,
                    "profile": f_profile,
                    "pressure": f_pressure
                }
                
        # Text summary
        act = st.session_state["planning_applied"]
        dates_str = f"{act['start_date'].strftime('%d/%m/%Y')} - {act['end_date'].strftime('%d/%m/%Y')}" if act["start_date"] else "Todos"
        render_filter_summary([
            ("Rango", dates_str),
            ("Fase", act["phase"]),
            ("Partido", act["match"]),
            ("RRSS", act["rrss"]),
            ("Presión", act["pressure"]),
        ])
        render_view_tabs()
        
        # Render planning tab
        render_planning_tab(
            matches,
            start_date=act["start_date"],
            end_date=act["end_date"],
            selected_phase=act["phase"],
            selected_match=act["match"],
            selected_rrss=act["rrss"],
            selected_profile=act["profile"],
            selected_pressure=act["pressure"]
        )
        
    elif view == "Análisis Histórico":
        render_view_tabs()
        render_historical_tab(enriched, daily_control)
        
    elif view == "Calidad de Datos":
        # Audit Tab
        render_view_tabs()
        render_quality_tab(
            raw_interactions,
            raw_agents,
            raw_control,
            raw_matches,
            enriched,
            agents
        )

if __name__ == "__main__":
    main()
