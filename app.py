"""Interactive graph explorer for the synthetic Medigraph demo."""

import csv
import hashlib
import os
from pathlib import Path

import networkx as nx
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from neo4j import GraphDatabase


st.set_page_config(page_title="Medigraph | Graph Explorer", page_icon="M", layout="wide")

LABEL_COLORS = {
    "Drug": "#e76f51",
    "Disease": "#2a9d8f",
    "Patient": "#e9c46a",
    "SideEffect": "#8d6e63",
}
DATA_DIR = Path(__file__).parent / "data"
NODE_FILES = (
    ("drugs.csv", "Drug"),
    ("diseases.csv", "Disease"),
    ("patients.csv", "Patient"),
    ("side_effects.csv", "SideEffect"),
)
RELATIONSHIP_FILES = (
    ("treats.csv", "TREATS", "drug_id", "Drug", "disease_id", "Disease"),
    ("contraindications.csv", "CONTRAINDICATED_IN", "drug_id", "Drug", "disease_id", "Disease"),
    ("interactions.csv", "INTERACTS_WITH", "drug_a", "Drug", "drug_b", "Drug"),
    ("causes.csv", "CAUSES", "drug_id", "Drug", "side_effect_id", "SideEffect"),
    ("patient_conditions.csv", "HAS_CONDITION", "patient_id", "Patient", "disease_id", "Disease"),
    ("patient_drugs.csv", "TAKES", "patient_id", "Patient", "drug_id", "Drug"),
)


@st.cache_data(ttl=45, show_spinner=False)
def fetch_graph(uri, username, password, database, labels, relationship_types, limit):
    query = """
    MATCH (source)-[relationship]->(target)
        WHERE any(label IN labels(source) WHERE label IN $labels)
            AND any(label IN labels(target) WHERE label IN $labels)
            AND type(relationship) IN $relationship_types
            AND (
                (type(relationship) IN ['TREATS', 'CONTRAINDICATED_IN']
                    AND source:Drug AND target:Disease)
                OR (type(relationship) = 'INTERACTS_WITH'
                    AND source:Drug AND target:Drug)
                OR (type(relationship) = 'CAUSES'
                    AND source:Drug AND target:SideEffect)
                OR (type(relationship) = 'HAS_CONDITION'
                    AND source:Patient AND target:Disease)
                OR (type(relationship) = 'TAKES'
                    AND source:Patient AND target:Drug)
            )
    RETURN elementId(source) AS source_id, labels(source) AS source_labels,
           properties(source) AS source_properties, type(relationship) AS relationship_type,
           properties(relationship) AS relationship_properties,
           elementId(target) AS target_id, labels(target) AS target_labels,
           properties(target) AS target_properties
    LIMIT $limit
    """
    driver = GraphDatabase.driver(uri, auth=(username, password))
    try:
        with driver.session(database=database) as session:
            return [record.data() for record in session.run(
                query,
                labels=labels,
                relationship_types=relationship_types,
                limit=limit,
            )]
    finally:
        driver.close()


def fetch_sample_graph(labels, relationship_types, limit):
    nodes = {}
    for filename, label in NODE_FILES:
        with (DATA_DIR / filename).open(newline="", encoding="utf-8-sig") as file:
            for properties in csv.DictReader(file):
                node_id = f"{label}:{properties['id']}"
                nodes[node_id] = ([label], properties)

    records = []
    for filename, relationship_type, source_key, source_label, target_key, target_label in RELATIONSHIP_FILES:
        if relationship_type not in relationship_types:
            continue
        with (DATA_DIR / filename).open(newline="", encoding="utf-8-sig") as file:
            for relationship in csv.DictReader(file):
                source_id = f"{source_label}:{relationship[source_key]}"
                target_id = f"{target_label}:{relationship[target_key]}"
                if source_label not in labels or target_label not in labels:
                    continue
                records.append({
                    "source_id": source_id,
                    "source_labels": nodes[source_id][0],
                    "source_properties": nodes[source_id][1],
                    "relationship_type": relationship_type,
                    "relationship_properties": relationship,
                    "target_id": target_id,
                    "target_labels": nodes[target_id][0],
                    "target_properties": nodes[target_id][1],
                })
                if len(records) >= limit:
                    return records
    return records


def node_title(labels, properties):
    label = labels[0] if labels else "Node"
    name = properties.get("name") or properties.get("id") or "Unnamed"
    return f"{name} ({label})"


def stable_color(label):
    return LABEL_COLORS.get(label, "#457b9d")


def make_figure(records):
    graph = nx.Graph()
    node_info = {}
    for record in records:
        for prefix in ("source", "target"):
            node_id = record[f"{prefix}_id"]
            labels = record[f"{prefix}_labels"]
            properties = record[f"{prefix}_properties"]
            node_info[node_id] = (labels, properties)
            graph.add_node(node_id)
        graph.add_edge(record["source_id"], record["target_id"])

    if not graph:
        return go.Figure()

    positions = nx.spring_layout(graph, seed=23, k=0.9, iterations=80)
    edge_x, edge_y = [], []
    edge_annotations = []
    for record in records:
        start = positions[record["source_id"]]
        end = positions[record["target_id"]]
        edge_x.extend([start[0], end[0], None])
        edge_y.extend([start[1], end[1], None])
        edge_annotations.append({
            "x": float((start[0] + end[0]) / 2),
            "y": float((start[1] + end[1]) / 2),
            "text": record["relationship_type"],
            "showarrow": False,
            "font": {"size": 9, "color": "#000000"},
            "bgcolor": "rgba(250, 249, 246, 0.84)",
            "borderpad": 2,
        })

    node_x, node_y, node_colors, node_labels, hover_text = [], [], [], [], []
    for node_id, (labels, properties) in node_info.items():
        position = positions[node_id]
        label = labels[0] if labels else "Node"
        node_x.append(position[0])
        node_y.append(position[1])
        node_colors.append(stable_color(label))
        node_labels.append(str(properties.get("name") or properties.get("id") or label))
        details = "<br>".join(
            f"{key}: {value}" for key, value in properties.items()
        )
        hover_text.append(f"<b>{node_title(labels, properties)}</b><br>{details}")

    figure = go.Figure()
    figure.add_trace(go.Scatter(
        x=edge_x,
        y=edge_y,
        mode="lines",
        line={"width": 1.3, "color": "#b8c1bc"},
        hoverinfo="skip",
        showlegend=False,
    ))
    figure.add_trace(go.Scatter(
        x=node_x,
        y=node_y,
        mode="markers+text",
        text=node_labels,
        textposition="top center",
        textfont={"size": 10, "color": "#26332f"},
        hovertext=hover_text,
        hoverinfo="text",
        marker={
            "size": 20,
            "color": node_colors,
            "line": {"width": 1.5, "color": "#faf9f6"},
        },
        showlegend=False,
    ))
    figure.update_layout(
        height=650,
        margin={"l": 10, "r": 10, "t": 10, "b": 10},
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        annotations=edge_annotations,
        xaxis={"visible": False, "fixedrange": False},
        yaxis={"visible": False, "fixedrange": False, "scaleanchor": "x", "scaleratio": 1},
        hoverlabel={"bgcolor": "#26332f", "font": {"color": "#ffffff"}},
        dragmode="pan",
    )
    return figure


st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@400;500;600;700;800&display=swap');
:root { --ink: #111111; --muted: #5f6368; --paper: #f5f3ef; --sidebar: #dfeeff; --panel: #ffffff; --rule: #bfd7f7; --gray: #6b7280; --gray-soft: #e5e7eb; }
html, body, [class*="css"] { font-family: 'Manrope', sans-serif; color: var(--ink); }
.stApp { background: linear-gradient(180deg, var(--paper) 0%, #f0f4f1 100%); }
[data-testid="stHeader"] { background: transparent; }
[data-testid="stSidebar"] { background: var(--sidebar); border-right: 1px solid var(--rule); }
section[data-testid="stSidebar"] > div { background: var(--sidebar); }
section[data-testid="stSidebar"] *,
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] .stRadio > div,
section[data-testid="stSidebar"] .stSelectbox,
section[data-testid="stSidebar"] .stMultiSelect,
section[data-testid="stSidebar"] .stSlider,
section[data-testid="stSidebar"] .stButton > button,
section[data-testid="stSidebar"] .stTextInput,
section[data-testid="stSidebar"] .stTextArea,
section[data-testid="stSidebar"] .stMarkdown p,
section[data-testid="stSidebar"] .stMarkdown h1,
section[data-testid="stSidebar"] .stMarkdown h2,
section[data-testid="stSidebar"] .stMarkdown h3,
section[data-testid="stSidebar"] .stMarkdown h4,
section[data-testid="stSidebar"] .stMarkdown h5,
section[data-testid="stSidebar"] .stMarkdown h6 { color: #111111 !important; }
.main .block-container { padding-top: 1.2rem; }
.masthead { border-bottom: 1px solid var(--rule); padding: 1.2rem 0 1.45rem; margin-bottom: 1.4rem; background: rgba(255,255,255,0.28); border-radius: 14px; padding-left: 1rem; padding-right: 1rem; }
.eyebrow { font: 500 11px 'DM Mono', monospace; letter-spacing: 1.5px; color: var(--gray); text-transform: uppercase; }
.title { font-size: 34px; font-weight: 800; letter-spacing: 0; line-height: 1.15; margin: 8px 0 5px; color: var(--ink); }
.subtitle { font-size: 14px; color: var(--muted); }
.metric { border-top: 2px solid var(--ink); padding-top: 10px; }
.metric-value { font: 500 25px 'DM Mono', monospace; color: var(--ink); }
.metric-label { font-size: 11px; color: var(--muted); text-transform: uppercase; margin-top: 3px; }
.note { font-size: 12px; line-height: 1.6; color: var(--muted); border-left: 2px solid #9aa3ad; padding: 4px 0 4px 10px; }
div[data-testid="stPlotlyChart"] { border: 1px solid var(--rule); background: var(--panel); }
</style>
<div class="masthead">
  <div class="eyebrow">Medigraph / Synthetic dataset</div>
  <div class="title">Graph Explorer</div>
  <div class="subtitle">Explore connections between drugs, conditions, side effects, and patient records.</div>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### Data source")
    data_source = st.radio("Show graph from", ["Bundled sample", "Neo4j database"], label_visibility="collapsed")
    if data_source == "Neo4j database":
        st.markdown("### Database connection")
        uri = st.text_input("Neo4j URI", value=os.getenv("NEO4J_URI", ""), placeholder="neo4j+s://...")
        username = st.text_input("Username", value=os.getenv("NEO4J_USERNAME", "neo4j"))
        password = st.text_input("Password", value=os.getenv("NEO4J_PASSWORD", ""), type="password")
        database = st.text_input("Database", value=os.getenv("NEO4J_DATABASE", "neo4j"))
    st.divider()
    st.markdown("### Graph filters")
    selected_labels = st.multiselect(
        "Node labels",
        ["Drug", "Disease", "Patient", "SideEffect"],
        default=["Drug", "Disease", "Patient", "SideEffect"],
    )
    selected_relationships = st.multiselect(
        "Relationships",
        ["TREATS", "CONTRAINDICATED_IN", "INTERACTS_WITH", "CAUSES", "HAS_CONDITION", "TAKES"],
        default=["TREATS", "CONTRAINDICATED_IN", "INTERACTS_WITH", "CAUSES", "HAS_CONDITION", "TAKES"],
    )
    row_limit = st.slider("Relationship limit", min_value=20, max_value=400, value=120, step=20)
    refresh = st.button("Refresh graph", type="primary", width="stretch")
    if refresh:
        fetch_graph.clear()
    st.markdown(
        '<div class="note">Synthetic placeholder data only. This graph is for software demonstration, not clinical guidance.</div>',
        unsafe_allow_html=True,
    )

if data_source == "Bundled sample":
    records = fetch_sample_graph(selected_labels, selected_relationships, row_limit)
else:
    if not uri or not username or not password:
        st.info("Enter your Neo4j URI, username, and password in the sidebar to load the graph.")
        st.stop()
    try:
        with st.spinner("Reading graph from Neo4j..."):
            records = fetch_graph(
                uri,
                username,
                password,
                database or "neo4j",
                selected_labels,
                selected_relationships,
                row_limit,
            )
    except Exception as error:
        error_fingerprint = hashlib.sha256(str(error).encode("utf-8")).hexdigest()[:8]
        st.error(f"Could not connect to Neo4j or read the graph ({type(error).__name__}, reference {error_fingerprint}). Check the URI, credentials, database, and Aura status.")
        st.stop()

node_count = len({record[key] for record in records for key in ("source_id", "target_id")})
relationship_count = len(records)
node_types = sorted({label for record in records for key in ("source_labels", "target_labels") for label in record[key]})
left, center, right = st.columns([1, 1, 2])
for column, value, label in (
    (left, f"{node_count:02d}", "Nodes in view"),
    (center, f"{relationship_count:02d}", "Relationships"),
    (right, "  /  ".join(node_types) if node_types else "No matching data", "Node types"),
):
    with column:
        st.markdown(f'<div class="metric"><div class="metric-value">{value}</div><div class="metric-label">{label}</div></div>', unsafe_allow_html=True)

st.write("")
if records:
    st.plotly_chart(make_figure(records), width="stretch", config={"displaylogo": False, "scrollZoom": True})
    with st.expander("Inspect returned relationships"):
        rows = []
        for record in records:
            rows.append({
                "Source": node_title(record["source_labels"], record["source_properties"]),
                "Relationship": record["relationship_type"],
                "Target": node_title(record["target_labels"], record["target_properties"]),
            })
        st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
else:
    st.info("No relationships match these filters. Try selecting more node labels or relationship types.")