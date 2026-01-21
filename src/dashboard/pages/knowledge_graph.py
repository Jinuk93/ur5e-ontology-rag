# ============================================================
# src/dashboard/pages/knowledge_graph.py - Knowledge Graph Visualization
# ============================================================

import streamlit as st
import streamlit.components.v1 as components
import os
import sys

# Add project root to path for imports
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from src.dashboard.services.graph_service import graph_service, GraphData
from src.dashboard.utils.config import config


def render_knowledge_graph():
    """Render the Knowledge Graph visualization page (Neo4j Browser style)"""

    st.title("🕸️ Knowledge Graph Explorer")
    st.caption("Interactive visualization of the UR5e error ontology")

    # ============================================================
    # Query Bar
    # ============================================================

    col1, col2, col3 = st.columns([3, 1, 1])

    with col1:
        search_query = st.text_input(
            "Search Node",
            placeholder="Enter error code or component (e.g., C4A15, Joint 3)",
            label_visibility="collapsed",
        )

    with col2:
        depth = st.number_input("Depth", min_value=1, max_value=4, value=2, label_visibility="collapsed")

    with col3:
        search_clicked = st.button("🔍 Search", use_container_width=True, type="primary")

    # Quick filters
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        if st.button("All Errors", use_container_width=True):
            st.session_state["graph_mode"] = "all_errors"
    with col2:
        if st.button("All Components", use_container_width=True):
            st.session_state["graph_mode"] = "all_components"
    with col3:
        if st.button("Error→Solution", use_container_width=True):
            st.session_state["graph_mode"] = "error_solution"
    with col4:
        if st.button("Full Graph", use_container_width=True):
            st.session_state["graph_mode"] = "full"
    with col5:
        if st.button("Clear", use_container_width=True):
            st.session_state["graph_data"] = None
            st.session_state["graph_mode"] = None

    st.divider()

    # ============================================================
    # Graph Visualization
    # ============================================================

    # Initialize session state
    if "graph_data" not in st.session_state:
        st.session_state["graph_data"] = None
    if "selected_node" not in st.session_state:
        st.session_state["selected_node"] = None

    # Load graph data based on mode
    graph_data = None

    if search_clicked and search_query:
        with st.spinner(f"Loading graph for '{search_query}'..."):
            graph_data = graph_service.get_neighbors(search_query, depth=depth)
            st.session_state["graph_data"] = graph_data
            st.session_state["selected_node"] = search_query

    elif st.session_state.get("graph_mode") == "all_errors":
        with st.spinner("Loading all error codes..."):
            graph_data = graph_service.run_cypher("""
                MATCH (e:ErrorCode)-[r]-(n)
                RETURN e, r, n
                LIMIT 100
            """)
            st.session_state["graph_data"] = graph_data

    elif st.session_state.get("graph_mode") == "all_components":
        with st.spinner("Loading all components..."):
            graph_data = graph_service.run_cypher("""
                MATCH (c:Component)-[r]-(n)
                RETURN c, r, n
                LIMIT 100
            """)
            st.session_state["graph_data"] = graph_data

    elif st.session_state.get("graph_mode") == "error_solution":
        with st.spinner("Loading error-solution relationships..."):
            graph_data = graph_service.run_cypher("""
                MATCH (e:ErrorCode)-[r:RESOLVED_BY]->(s:Solution)
                RETURN e, r, s
                LIMIT 100
            """)
            st.session_state["graph_data"] = graph_data

    elif st.session_state.get("graph_mode") == "full":
        with st.spinner("Loading full graph (this may take a moment)..."):
            graph_data = graph_service.run_cypher("""
                MATCH (n)-[r]-(m)
                RETURN n, r, m
                LIMIT 200
            """)
            st.session_state["graph_data"] = graph_data

    else:
        graph_data = st.session_state.get("graph_data")

    # Render graph
    if graph_data and graph_data.nodes:
        col1, col2 = st.columns([3, 1])

        with col1:
            st.markdown("### 📊 Graph Visualization")
            render_pyvis_graph(graph_data)

        with col2:
            render_node_details_panel(graph_data, st.session_state.get("selected_node"))

    else:
        # Show placeholder
        st.info("👆 Search for a node or use quick filters to visualize the knowledge graph")

        # Show statistics instead
        st.subheader("📊 Graph Statistics")
        stats = graph_service.get_statistics()

        if "error" not in stats:
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("Total Nodes", f"{stats.get('total_nodes', 0):,}")
            with col2:
                st.metric("Total Edges", f"{stats.get('total_edges', 0):,}")
            with col3:
                st.metric("Node Types", stats.get("node_types", 0))
            with col4:
                st.metric("Edge Types", stats.get("edge_types", 0))

            # Node type distribution
            st.markdown("#### Node Types")
            node_counts = stats.get("node_counts", {})
            for node_type, count in node_counts.items():
                color = config.NODE_COLORS.get(node_type, "#999")
                st.markdown(f"<span style='color:{color}'>●</span> **{node_type}**: {count}", unsafe_allow_html=True)

            # Top connected nodes
            st.markdown("#### Top Connected Nodes")
            top_nodes = graph_service.get_top_connected_nodes(limit=5)
            for node in top_nodes:
                st.text(f"• {node.get('name', 'Unknown')} ({node.get('type', 'Unknown')}) - {node.get('connections', 0)} connections")
        else:
            st.warning(f"Could not load statistics: {stats.get('error')}")

    # ============================================================
    # Exploration Modes
    # ============================================================

    st.divider()

    with st.expander("🔍 Advanced Exploration"):
        tab1, tab2, tab3 = st.tabs(["🎯 Focus Mode", "🔍 Path Finder", "📝 Cypher Query"])

        with tab1:
            st.markdown("**Focus on a specific node and its neighbors**")
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                focus_node = st.text_input("Center Node", placeholder="e.g., C4A15")
            with col2:
                focus_depth = st.number_input("Depth", min_value=1, max_value=4, value=2, key="focus_depth")
            with col3:
                if st.button("Focus", use_container_width=True):
                    if focus_node:
                        st.session_state["graph_data"] = graph_service.get_neighbors(focus_node, depth=focus_depth)
                        st.session_state["selected_node"] = focus_node
                        st.rerun()

        with tab2:
            st.markdown("**Find shortest path between two nodes**")
            col1, col2, col3 = st.columns([2, 2, 1])
            with col1:
                path_from = st.text_input("From", placeholder="e.g., C4A15")
            with col2:
                path_to = st.text_input("To", placeholder="e.g., Control Box")
            with col3:
                if st.button("Find Path", use_container_width=True):
                    if path_from and path_to:
                        st.session_state["graph_data"] = graph_service.find_path(path_from, path_to)
                        st.rerun()

        with tab3:
            st.markdown("**Run custom Cypher query**")
            cypher_query = st.text_area(
                "Cypher Query",
                placeholder="MATCH (e:ErrorCode)-[:CAUSED_BY]->(c:Component)\nWHERE c.name CONTAINS 'Joint'\nRETURN e, c LIMIT 50",
                height=100,
            )
            if st.button("Run Query", use_container_width=True):
                if cypher_query:
                    st.session_state["graph_data"] = graph_service.run_cypher(cypher_query)
                    st.rerun()


def render_pyvis_graph(graph_data: GraphData):
    """Render graph using Pyvis with Neo4j Browser style"""

    try:
        from pyvis.network import Network
    except ImportError:
        st.error("Pyvis not installed. Run: pip install pyvis")
        return

    # Create network
    net = Network(
        height="500px",
        width="100%",
        bgcolor="#1a1a2e",
        font_color="white",
        directed=True,
    )

    # Physics settings for interactive behavior
    net.set_options("""
    {
        "physics": {
            "enabled": true,
            "forceAtlas2Based": {
                "gravitationalConstant": -50,
                "centralGravity": 0.01,
                "springLength": 100,
                "springConstant": 0.08
            },
            "solver": "forceAtlas2Based",
            "stabilization": {"iterations": 100}
        },
        "interaction": {
            "hover": true,
            "tooltipDelay": 200,
            "navigationButtons": true,
            "keyboard": true
        },
        "nodes": {
            "borderWidth": 2,
            "borderWidthSelected": 4,
            "shadow": true
        },
        "edges": {
            "arrows": {"to": {"enabled": true, "scaleFactor": 0.5}},
            "smooth": {"type": "continuous"},
            "font": {"size": 10, "color": "white"}
        }
    }
    """)

    # Add nodes
    for node in graph_data.nodes:
        color = config.NODE_COLORS.get(node.node_type, "#9E9E9E")
        size = 30 if node.node_type in ["ErrorCode", "Component"] else 20

        net.add_node(
            node.id,
            label=node.label,
            color=color,
            size=size,
            title=f"{node.node_type}: {node.label}\n{str(node.properties)[:100]}",
        )

    # Add edges
    for edge in graph_data.edges:
        color = config.EDGE_COLORS.get(edge.edge_type, "#9E9E9E")
        net.add_edge(
            edge.source,
            edge.target,
            label=edge.edge_type,
            color=color,
            title=edge.edge_type,
        )

    # Generate HTML
    html = net.generate_html()

    # Display in Streamlit
    components.html(html, height=520)

    # Show stats
    st.caption(f"Nodes: {len(graph_data.nodes)} | Edges: {len(graph_data.edges)}")


def render_node_details_panel(graph_data: GraphData, selected_node: str = None):
    """Render node details panel"""

    st.markdown("### 📋 Details")

    if selected_node:
        # Find selected node
        node = next((n for n in graph_data.nodes if n.id == selected_node), None)

        if node:
            color = config.NODE_COLORS.get(node.node_type, "#999")
            st.markdown(f"<h4 style='color:{color}'>● {node.label}</h4>", unsafe_allow_html=True)
            st.caption(f"Type: {node.node_type}")

            st.divider()

            st.markdown("**Properties:**")
            for key, value in node.properties.items():
                st.text(f"• {key}: {value}")

            st.divider()

            # Show relationships
            st.markdown("**Relationships:**")
            related_edges = [e for e in graph_data.edges if e.source == selected_node or e.target == selected_node]
            for edge in related_edges[:10]:
                direction = "→" if edge.source == selected_node else "←"
                other_node = edge.target if edge.source == selected_node else edge.source
                st.text(f"{direction} {edge.edge_type} → {other_node}")

    else:
        st.info("Click a node to see details")

    # Node type legend
    st.divider()
    st.markdown("**Legend:**")
    for node_type, color in config.NODE_COLORS.items():
        st.markdown(f"<span style='color:{color}'>●</span> {node_type}", unsafe_allow_html=True)
