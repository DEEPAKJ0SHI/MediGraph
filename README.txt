MEDIGRAPH FIXED STARTER (Windows)

1. Extract this ZIP.
2. In Neo4j Aura, copy the URI from Connect > Drivers.
3. Rotate the password previously pasted into chat, then use the NEW password.
4. Double-click run.bat. It installs the dependencies, asks for credentials, and loads the included synthetic demo CSV data.
5. Use an empty/dedicated database. This loader adds demo data and is designed to be rerun safely using MERGE; it does not delete existing nodes.
6. Double-click run_demo.bat to launch the interactive graph explorer. Enter the same Neo4j connection details in the sidebar; the password is masked. The app opens in your browser.

The included medical names/relationships are placeholders for software demonstration, not clinical advice or verified drug facts.

If running manually: install with `py -m pip install -r requirements.txt`, set NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD and optional NEO4J_DATABASE, then run `py load_data.py data`. Start the visual demo with `py -m streamlit run app.py`; connection details can be entered in the app or supplied through those environment variables.
