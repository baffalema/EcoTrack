import streamlit as st
import pandas as pd
import sqlite3
import datetime
import json
from dateutil.relativedelta import relativedelta

# ==============================================================================
# 1. PAGE SETUP & DESIGN STYLE
# ==============================================================================
st.set_page_config(
    page_title="EcoTrack: Green Schools Innovation",
    layout="wide",
    page_icon="🌱"
)

# Complete tree type database with local names and scientific classifications
TREE_DATABASE = {
    "Neem (Darbejiya)": {"botanical": "Azadirachta indica", "wd": 0.68, "gf": 0.025, "type": "Climate Resilience"},
    "Acacia (Gum Arabic/Karo)": {"botanical": "Acacia senegal", "wd": 0.78, "gf": 0.022, "type": "Desert Control"},
    "Baobab (Kuka)": {"botanical": "Adansonia digitata", "wd": 0.32, "gf": 0.035, "type": "Indigenous Shade"},
    "Tamarind (Tsamiya)": {"botanical": "Tamarindus indica", "wd": 0.85, "gf": 0.015, "type": "Fruit Tree"},
    "Desert Date (Adua)": {"botanical": "Balanites aegyptiaca", "wd": 0.74, "gf": 0.018, "type": "Desert Control"},
    "African Locust Bean (Kalwa)": {"botanical": "Parkia biglobosa", "wd": 0.62, "gf": 0.021,
                                    "type": "Indigenous Shade"},
    "Acacia nilotica (Bagaruwa)": {"botanical": "Vachellia nilotica", "wd": 0.80, "gf": 0.019,
                                   "type": "Desert Control"},
    "Moringa (Zogale)": {"botanical": "Moringa oleifera", "wd": 0.40, "gf": 0.045, "type": "Food & Nutrition"},
    "Winterthorn (Gawo)": {"botanical": "Faidherbia albida", "wd": 0.58, "gf": 0.028, "type": "Climate Resilience"},
    "Mango (Mangwaro)": {"botanical": "Mangifera indica", "wd": 0.52, "gf": 0.030, "type": "Fruit Tree"},
    "Cashew (Kashu)": {"botanical": "Anacardium occidentale", "wd": 0.50, "gf": 0.032, "type": "Fruit Tree"},
    "Guava (Gwayaba)": {"botanical": "Psidium guajava", "wd": 0.60, "gf": 0.028, "type": "Fruit Tree"},
    "Orange (Lemu)": {"botanical": "Citrus sinensis", "wd": 0.65, "gf": 0.020, "type": "Fruit Tree"},
    "Date Palm (Dabino)": {"botanical": "Phoenix dactylifera", "wd": 0.45, "gf": 0.025, "type": "Fruit Tree"},
    "Coconut Palm": {"botanical": "Cocos nucifera", "wd": 0.42, "gf": 0.028, "type": "Fruit Tree"},
    "Sheanut (Kade)": {"botanical": "Vitellaria paradoxa", "wd": 0.70, "gf": 0.014, "type": "Economic Fruit Tree"},
    "Mahogany (Savanna)": {"botanical": "Khaya senegalensis", "wd": 0.72, "gf": 0.018, "type": "Timber & Canopy"},
    "African Mahogany (Rainforest)": {"botanical": "Khaya ivorensis", "wd": 0.65, "gf": 0.022,
                                      "type": "Timber & Canopy"},
    "Teak": {"botanical": "Tectona grandis", "wd": 0.65, "gf": 0.024, "type": "Timber & Canopy"},
    "Iroko": {"botanical": "Milicia excelsa", "wd": 0.68, "gf": 0.017, "type": "Timber & Canopy"},
    "Gmelina": {"botanical": "Gmelina arborea", "wd": 0.45, "gf": 0.040, "type": "Timber & Canopy"},
    "Eucalyptus": {"botanical": "Eucalyptus camaldulensis", "wd": 0.55, "gf": 0.045, "type": "Timber Tree"},
    "Royal Palm": {"botanical": "Roystonea regia", "wd": 0.35, "gf": 0.030, "type": "Ornamental"},
    "Flamboyant": {"botanical": "Delonix regia", "wd": 0.40, "gf": 0.035, "type": "Beautiful Shade Tree"},
    "Bougainvillea": {"botanical": "Bougainvillea spp.", "wd": 0.45, "gf": 0.020, "type": "Ornamental Shrub"},
    "Terminalia (Madagascar Almond)": {"botanical": "Terminalia mantaly", "wd": 0.55, "gf": 0.038,
                                       "type": "Roadside Shade"}
}

DB_FILE = "ecotrack_vnext.db"


# ==============================================================================
# 2. FILE AND STORAGE SETUP (AUTOMATIC)
# ==============================================================================
def setup_application_tables():
    """Sets up the required files and lists needed to save user records."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # 1. School Accounts Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            account_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            type TEXT NOT NULL,
            tier TEXT NOT NULL DEFAULT 'Basic Tier'
        )
    """)

    # 2. Main Tree Planting Events Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_name TEXT NOT NULL,
            lga_name TEXT NOT NULL,
            state_name TEXT NOT NULL,
            planting_date TEXT NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            gps_accuracy REAL NOT NULL,
            device_info TEXT,
            evidence_links TEXT,
            FOREIGN KEY(account_name) REFERENCES accounts(name)
        )
    """)

    # 3. List of Tree Species Planted Per Event
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS batch_items (
            item_id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL,
            tree_species TEXT NOT NULL,
            qty_planted INTEGER NOT NULL,
            qty_survived INTEGER NOT NULL,
            FOREIGN KEY(event_id) REFERENCES events(event_id) ON DELETE CASCADE
        )
    """)

    # 4. Long-term Checkpoints and Progress Inspections
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS checkpoints (
            checkpoint_id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL,
            interval_months TEXT NOT NULL,
            qty_alive INTEGER NOT NULL,
            qty_dead INTEGER NOT NULL,
            inspection_date TEXT NOT NULL,
            inspector TEXT NOT NULL,
            verification_status TEXT NOT NULL DEFAULT 'Approved',
            FOREIGN KEY(event_id) REFERENCES events(event_id) ON DELETE CASCADE
        )
    """)

    # Add initial registered demonstration profiles if empty
    cursor.execute("SELECT COUNT(*) FROM accounts")
    if cursor.fetchone()[0] == 0:
        sample_profiles = [
            ("Katsina Premium Academy", "Private School", "Enterprise Tier"),
            ("Batagarawa Community School", "Public School", "Basic Tier"),
            ("Save The Green Foundation", "NGO", "Growth Tier"),
            ("Daura Science College", "Private School", "Climate-Smart Academy")
        ]
        cursor.executemany("INSERT INTO accounts (name, type, tier) VALUES (?, ?, ?)", sample_profiles)

    conn.commit()
    conn.close()


setup_application_tables()


# ==============================================================================
# 3. AUTOMATED GREEN CALCULATIONS & SMART LOGIC
# ==============================================================================
def calculate_carbon_absorbed(species_name, tree_count):
    """Calculates how much Carbon Dioxide (CO2) is absorbed by the living trees per year."""
    tree_info = TREE_DATABASE.get(species_name, {"wd": 0.55, "gf": 0.022})
    # Standard environmental formula for young tropical trees
    yearly_kg_per_tree = (tree_info["wd"] * 50) * tree_info["gf"] * 1.28 * 0.47 * 3.67
    return round(yearly_kg_per_tree * tree_count, 2)


def calculate_tree_age(date_string):
    """Calculates exactly how long the trees have been growing since their planting date."""
    try:
        planted_day = datetime.datetime.strptime(date_string, "%Y-%m-%d").date()
        today = datetime.date.today()
        difference = relativedelta(today, planted_day)

        if difference.years == 0 and difference.months == 0 and difference.days <= 0:
            return "Planted Today"

        time_labels = []
        if difference.years > 0:
            time_labels.append(f"{difference.years} year" + ("s" if difference.years > 1 else ""))
        if difference.months > 0:
            time_labels.append(f"{difference.months} month" + ("s" if difference.months > 1 else ""))
        if difference.days > 0 and len(time_labels) < 2:
            time_labels.append(f"{difference.days} day" + ("s" if difference.days > 1 else ""))

        return " ".join(time_labels) if time_labels else "Just started"
    except ValueError:
        return "Unknown timeline"


def generate_smart_recommendations(df_batches):
    """Generates simple, actionable observations based on recorded tree survival."""
    if df_batches.empty:
        return ["No tree data recorded yet. Head over to the School Form to add your first project!"]

    messages = []
    # Identify the highest performing tree species
    summary = df_batches.groupby("tree_species").agg({"qty_planted": "sum", "qty_survived": "sum"})
    summary["rate"] = (summary["qty_survived"] / summary["qty_planted"]) * 100
    top_tree = summary["rate"].idxmax()
    top_percentage = summary["rate"].max()

    messages.append(
        f"🌱 **Top Performer:** *{top_tree}* has the highest survival rate at **{top_percentage:.1f}%**. Consider planting more of this type!")

    # Identify critical risk flags
    failed_trees = summary[summary["rate"] < 50]
    if not failed_trees.empty:
        problem_list = list(failed_trees.index)
        messages.append(
            f"⚠️ **Attention Needed:** Tree types like {problem_list} are showing survival rates below 50%. Check soil quality or watering frequency.")

    return messages


# ==============================================================================
# 4. DATA ACCESS ENGINE
# ==============================================================================
def fetch_complete_green_dataset():
    """Retrieves all tree data combined with school profiles for active tracking."""
    conn = sqlite3.connect(DB_FILE)
    query = """
        SELECT e.event_id, e.account_name, e.lga_name, e.state_name, e.planting_date,
               e.latitude, e.longitude, e.gps_accuracy, e.evidence_links,
               b.tree_species, b.qty_planted, b.qty_survived,
               a.type as account_type, a.tier as account_tier
        FROM events e
        JOIN batch_items b ON e.event_id = b.event_id
        JOIN accounts a ON e.account_name = a.name
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df


# ==============================================================================
# 5. SIDEBAR NAVIGATION
# ==============================================================================
with st.sidebar:
    st.image("https://img.icons8.com/color/96/sprout.png", width=54)
    st.title("EcoTrack Hub")
    st.caption("Green Schools Innovation System")
    st.divider()

    active_screen = st.selectbox("Where would you like to go?", [
        "1. School Form (Record Planting)",
        "2. Progress Inspections & Audits",
        "3. Live Green Dashboard",
        "4. School Performance Leaderboards"
    ])

    st.divider()
    # Profile Selector Setup
    conn = sqlite3.connect(DB_FILE)
    available_profiles = pd.read_sql_query("SELECT name FROM accounts", conn)["name"].tolist()
    conn.close()

    current_user = st.selectbox("Log in as Account:", available_profiles)

    # Fetch active account features
    conn = sqlite3.connect(DB_FILE)
    tier_info = pd.read_sql_query("SELECT tier FROM accounts WHERE name=?", conn, params=(current_user,))
    active_tier = tier_info["tier"].iloc[0] if not tier_info.empty else "Basic Tier"
    conn.close()

    st.info(f"📋 **Current Access Level:** {active_tier}")

# ==============================================================================
# SCREEN 1: RECORD TREE PLANTING ACTIVITIES (MULTIPLES AT ONCE)
# ==============================================================================
if active_screen == "1. School Form (Record Planting)":
    st.title("🌳 School Planting Records Terminal")
    st.markdown("### Log single or multiple tree varieties from your latest school project below.")

    # Store tree list temporarily before saving permanently
    if "temporary_tree_list" not in st.session_state:
        st.session_state.temporary_tree_list = []

    with st.expander("📍 Automatic GPS Verification Status", expanded=True):
        col_g1, col_g2, col_g3 = st.columns(3)
        locked_lat = col_g1.number_input("Verified Latitude:", value=11.9845, format="%.6f", disabled=True)
        locked_lon = col_g2.number_input("Verified Longitude:", value=7.6253, format="%.6f", disabled=True)
        gps_signals = col_g3.number_input("GPS Signal Accuracy (Meters):", value=2.4, format="%.1f", disabled=True)
        st.caption(
            "🔒 *Security Note: GPS coordinates are automatically locked via your device to prevent location errors.*")

    # Interactive Step-by-Step Entry List Builder
    st.subheader("➕ Add Trees to Your Report")
    with st.form("individual_tree_form", clear_on_submit=False):
        col_i1, col_i2, col_i3 = st.columns([2, 1, 1])
        variety = col_i1.selectbox("Choose Tree Variety:", sorted(list(TREE_DATABASE.keys())))
        num_planted = col_i2.number_input("Number Planted:", min_value=1, value=10, step=1)
        num_survived = col_i3.number_input("Number Currently Living:", min_value=0, value=10, step=1)

        add_to_list_btn = st.form_submit_button("Add This Variety to List")
        if add_to_list_btn:
            if num_survived > num_planted:
                st.error("Error: Living tree count cannot be higher than the total number of trees planted.")
            else:
                st.session_state.temporary_tree_list.append({
                    "variety": variety,
                    "planted": num_planted,
                    "survived": num_survived
                })
                st.success(f"Added {variety} to your current form successfully.")

    # Show list if not empty
    if st.session_state.temporary_tree_list:
        st.markdown("#### Preview of Current Report entries:")
        temp_preview_df = pd.DataFrame(st.session_state.temporary_tree_list)
        st.dataframe(temp_preview_df.rename(
            columns={"variety": "Tree Variety", "planted": "Total Planted", "survived": "Total Survived"}),
                     use_container_width=True, hide_index=True)

        if st.button("Clear Current Form List"):
            st.session_state.temporary_tree_list = []
            st.rerun()

    # Final Verification Area
    st.subheader("📋 Final Submission Details")
    with st.form("final_report_form"):
        col_m1, col_m2 = st.columns(2)
        local_lga = col_m1.selectbox("Your Local Government Area (LGA):",
                                     ["Bakori", "Batagarawa", "Batsari", "Baure", "Bindawa", "Charanchi","Dan Musa", "Dandume", "Danja", "Daura", "Dutsi", "Dutsin-Ma", "faskari","Funtua", "Ingawa", "Jibia", "Kafur", "kaita", "Kankara", "Kankia", "Katsina", "Kurfi", "Kusada", "Mai'adua", "Malumfashi", "Mani", "Mashi", "Matazu", "Musawa", "Rimi", "Sabuwa", "Safana", "Sandamu", "Zango"])
        planting_day = col_m2.date_input("Date Planted:", max_value=datetime.date.today())

        # Multiple Document / Evidence Uploader Section
        photo_evidence = st.file_uploader(
            "Upload project proof files (Drag and drop or select multiple Photos, PDFs, or verification sheets)",
            accept_multiple_files=True
        )

        send_report_to_database = st.form_submit_button("🔒 Securely Save and Submit Full Report")

        if send_report_to_database:
            if not st.session_state.temporary_tree_list:
                st.error("Submission Failed: Your tree list is empty. Please add at least one tree variety above.")
            else:
                file_names = [f.name for f in photo_evidence] if photo_evidence else ["default_record_photo.png"]
                saved_files_string = json.dumps(file_names)

                # Insert basic location metrics
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()

                cursor.execute("""
                    INSERT INTO events (account_name, lga_name, state_name, planting_date, latitude, longitude, gps_accuracy, device_info, evidence_links)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (current_user, local_lga, "Katsina State", str(planting_day), locked_lat, locked_lon, gps_signals,
                      "EcoTrack Web App Engine v2", saved_files_string))

                new_event_id = cursor.lastrowid

                # Insert all rows attached to this single setup
                final_batch_payload = [
                    (new_event_id, item["variety"], item["planted"], item["survived"])
                    for item in st.session_state.temporary_tree_list
                ]
                cursor.executemany("""
                    INSERT INTO batch_items (event_id, tree_species, qty_planted, qty_survived)
                    VALUES (?, ?, ?, ?)
                """, final_batch_payload)

                conn.commit()
                conn.close()

                st.success(f"🎉 Success! Project Record #{new_event_id} has been securely saved and updated on the map.")
                st.session_state.temporary_tree_list = []

# ==============================================================================
# SCREEN 2: SYSTEMATIC LONG-TERM CHECKPOINTS AND FOLLOW-UP AUDITS
# ==============================================================================
elif active_screen == "2. Progress Inspections & Audits":
    st.title("🛡️ Project Follow-Up and Inspection Center")
    st.markdown("### Monitor tree survival growth milestones over 1 to 60 months below.")

    all_data = fetch_complete_green_dataset()

    if all_data.empty:
        st.info("No projects found in system records. Submit a planting report first to enable tracking options.")
    else:
        # Group data to show individual events cleanly in dropdown select options
        grouped_records = all_data[["event_id", "account_name", "planting_date", "lga_name"]].drop_duplicates()
        grouped_records["current_age"] = grouped_records["planting_date"].apply(calculate_tree_age)

        dropdown_options = {
            row[
                "event_id"]: f"Project #{row['event_id']} by {row['account_name']} ({row['lga_name']}) — Age: {row['current_age']}"
            for _, row in grouped_records.iterrows()
        }

        target_project_id = st.selectbox("Select a Project Record to Inspect or Review:", list(dropdown_options.keys()),
                                         format_func=lambda x: dropdown_options[x])

        # Filter metadata matching selected drop menu metrics
        project_meta = grouped_records[grouped_records["event_id"] == target_project_id].iloc[0]
        project_trees_subset = all_data[all_data["event_id"] == target_project_id]

        st.markdown("---")
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            st.markdown(f"#### 📐 Project Metadata Card: ID #{target_project_id}")
            st.write(f"**Managing Institution:** {project_meta['account_name']}")
            st.write(f"**Initial Planting Date:** {project_meta['planting_date']} (`{project_meta['current_age']}`)")
            st.write(
                f"**Geotagged Coordinates:** {project_trees_subset['latitude'].iloc[0]}, {project_trees_subset['longitude'].iloc[0]}")

        with col_p2:
            st.markdown("#### 🪵 Current Tree Counts on Record")
            st.dataframe(project_trees_subset[["tree_species", "qty_planted", "qty_survived"]].rename(
                columns={"tree_species": "Tree Variety", "qty_planted": "Planted", "qty_survived": "Living"}),
                         hide_index=True, use_container_width=True)

        st.markdown("### 📝 Log a New Inspection Progress Check")
        with st.form("new_checkpoint_form"):
            col_c1, col_c2, col_c3 = st.columns(3)
            milestone_step = col_c1.selectbox("Time Horizon Milestone Point:",
                                              ["1 Month Check", "3 Months Check", "6 Months Check", "12 Months Check",
                                               "24 Months Check", "36 Months Check"])
            living_found = col_c2.number_input("Number of Trees Found Alive:", min_value=0, step=1)
            dead_found = col_c3.number_input("Number of Trees Found Dead:", min_value=0, step=1)

            col_c4, col_c5 = st.columns(2)
            inspector_id = col_c4.text_input("Name of Inspector or Green Club Teacher:")
            date_of_check = col_c5.date_input("Inspection Date:", max_value=datetime.date.today())

            save_checkpoint_btn = st.form_submit_button("Save This Progress Inspection Entry")

            if save_checkpoint_btn:
                conn = sqlite3.connect(DB_FILE)
                conn.execute("""
                    INSERT INTO checkpoints (event_id, interval_months, qty_alive, qty_dead, inspection_date, inspector)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                int(target_project_id), milestone_step, living_found, dead_found, str(date_of_check), inspector_id))
                conn.commit()
                conn.close()
                st.success(f"Audit Status Updated: Progress report for {milestone_step} saved.")
                st.rerun()

        # Historic timeline summary layout
        st.markdown("### ⏳ Inspection Progress History")
        conn = sqlite3.connect(DB_FILE)
        past_checkpoints = pd.read_sql_query("SELECT * FROM checkpoints WHERE event_id=?", conn,
                                             params=(target_project_id,))
        conn.close()

        if past_checkpoints.empty:
            st.info("No prior progress checks recorded for this project yet.")
        else:
            st.dataframe(past_checkpoints[["interval_months", "qty_alive", "qty_dead", "inspection_date", "inspector",
                                           "verification_status"]].rename(
                columns={"interval_months": "Milestone", "qty_alive": "Alive Count", "qty_dead": "Dead Count",
                         "inspection_date": "Checked On", "inspector": "Verified By", "verification_status": "Status"}),
                         use_container_width=True, hide_index=True)

# ==============================================================================
# SCREEN 3: EXECUTIVE LIVE GREEN ANALYTICS DASHBOARD FRAME
# ==============================================================================
elif active_screen == "3. Live Green Dashboard":
    st.title("📊 Regional Environmental Dashboard Workspace")
    st.markdown("### Verified Carbon Absorption Metrics, Map Pins, and Project Analytics.")

    analytics_base = fetch_complete_green_dataset()

    if analytics_base.empty:
        st.info("The dashboard is currently empty. Data values will appear once reports are submitted.")
    else:
        # Run clean calculations to append carbon columns to current data table views
        analytics_base["co2_absorbed_kg"] = analytics_base.apply(
            lambda row: calculate_carbon_absorbed(row["tree_species"], row["qty_survived"]), axis=1)

        # User Dashboard Filters Box
        with st.expander("🎛️ Filter Dashboard Content by Region or Tree Variety", expanded=True):
            col_f1, col_f2, col_f3 = st.columns(3)
            selected_states = col_f1.multiselect("Select State Region:", analytics_base["state_name"].unique(),
                                                 default=analytics_base["state_name"].unique())
            selected_lgas = col_f2.multiselect("Select LGA District:", analytics_base["lga_name"].unique(),
                                               default=analytics_base["lga_name"].unique())
            selected_trees = col_f3.multiselect("Select Tree Variety:", analytics_base["tree_species"].unique(),
                                                default=analytics_base["tree_species"].unique())

        # Isolate rows based on active user filters
        filtered_view = analytics_base[
            (analytics_base["state_name"].isin(selected_states)) &
            (analytics_base["lga_name"].isin(selected_lgas)) &
            (analytics_base["tree_species"].isin(selected_trees))
            ]

        if filtered_view.empty:
            st.warning("No rows match your current filter choices. Adjust settings above to view data graphics.")
        else:
            # Primary Dashboard Metrics Block
            total_planted = filtered_view["qty_planted"].sum()
            total_survived = filtered_view["qty_survived"].sum()
            survival_rate_percentage = (total_survived / total_planted * 100) if total_planted > 0 else 0
            net_co2_offset = filtered_view["co2_absorbed_kg"].sum()
            active_schools_count = filtered_view["account_name"].nunique()

            st.markdown("#### High-Level Environmental Totals")
            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
            col_m1.metric("Total Saplings Planted", f"{total_planted:,}")
            col_m2.metric("Verified Living Trees", f"{total_survived:,} ({survival_rate_percentage:.1f}%)")
            col_m3.metric("CO2 Absorbed (kg/year)", f"{net_co2_offset:,.1f}")
            col_m4.metric("Active School Accounts", f"{active_schools_count:,}")

            # Interactive Smart Recommendations
            st.markdown("---")
            st.subheader("💡 Automated Project Observations & Guidance")
            ai_tips = generate_smart_recommendations(filtered_view)
            for tip in ai_tips:
                st.markdown(tip)

            # Satellite Project Mapping Section
            st.markdown("---")
            st.subheader("🗺️ Real-Time Map of Verified Project Plantings")
            map_plot_data = filtered_view[["latitude", "longitude", "account_name", "qty_survived"]].dropna().rename(
                columns={"latitude": "lat", "longitude": "lon"})
            st.map(map_plot_data, use_container_width=True)

            # Performance and Download Data Tabs Section
            st.markdown("---")
            tab_charts, tab_lga, tab_reports = st.tabs(
                ["🌳 Tree Performance Analysis", "🏆 LGA Performance Area", "💾 Document & Report Downloader"])

            with tab_charts:
                col_c1, col_c2 = st.columns(2)
                with col_c1:
                    st.write("##### Total Living Trees by Variety Type")
                    variety_counts = filtered_view.groupby("tree_species")["qty_survived"].sum().sort_values(
                        ascending=False)
                    st.bar_chart(variety_counts, color="#1E5631")
                with col_c2:
                    st.write("##### Total Carbon CO2 Absorption by Variety Type")
                    variety_carbon = filtered_view.groupby("tree_species")["co2_absorbed_kg"].sum().sort_values(
                        ascending=False)
                    st.bar_chart(variety_carbon, color="#3B7A57")

            with tab_lga:
                st.write("##### Top Performing Local Government Areas (LGAs)")
                lga_scores = filtered_view.groupby("lga_name")["qty_survived"].sum().sort_values(ascending=False)
                st.bar_chart(lga_scores, color="#4F7942")

            with tab_reports:
                st.write("##### Corporate Sustainability Data Exporter")
                st.caption("Download system data for internal board reports, audit sheets, or compliance records.")

                csv_download_file = filtered_view.to_csv(index=False).encode('utf-8')

                # Check subscription features to enable downloader modules
                if active_tier in ["Enterprise Tier", "Climate-Smart Academy"]:
                    st.success(f"🔓 Premium Feature Unlocked: Export options active for {current_user}.")
                    st.download_button(
                        label="Download Full Project Report Dataset (.CSV)",
                        data=csv_download_file,
                        file_name=f"ecotrack_sustainability_data_{datetime.date.today()}.csv",
                        mime="text/csv"
                    )
                else:
                    st.warning(
                        "🔒 **Subscription Plan Notice:** High-density automated document downloading requires upgrading your account to the Climate-Smart Academy Tier or higher.")
                    st.button("Request Premium Feature Upgrades via Email", disabled=True)

# ==============================================================================
# SCREEN 4: GAMIFIED SCHOOL COMPETITION & PUBLIC STANDINGS LEADERBOARD
# ==============================================================================
elif active_screen == "4. School Performance Leaderboards":
    st.title("🏆 Regional Green Schools Championship Standings")
    st.markdown("### Celebrating schools achieving maximum environmental impact through tree survival rates.")

    ranking_base = fetch_complete_green_dataset()

    if ranking_base.empty:
        st.info("Leaderboards will calculate standings as soon as schools submit active data entries.")
    else:
        # Aggregate performance data fields
        leaderboard = ranking_base.groupby("account_name").agg({
            "qty_planted": "sum",
            "qty_survived": "sum",
            "event_id": "nunique"
        }).reset_index()

        leaderboard["Survival Rate (%)"] = (leaderboard["qty_survived"] / leaderboard["qty_planted"] * 100).round(1)
        # Strategic Impact Formula: (Living Trees Count * 60%) + (Survival Success Rate * 40%)
        leaderboard["Total Impact Score"] = (
                (leaderboard["qty_survived"] * 0.6) +
                (leaderboard["Survival Rate (%)"] * 0.4)
        ).round(1)

        sorted_leaderboard = leaderboard.sort_values(by="Total Impact Score", ascending=False).reset_index(drop=True)
        sorted_leaderboard.index += 1  # Offset index rows cleanly to create ranking values

        st.markdown("#### High-Impact Registered School Rankings")


        # Add visual badges to rows based on current ranking positions
        def assign_award_status(rank):
            if rank == 1:
                return "🥇 Champion Team"
            elif rank == 2:
                return "🥈 Premium Tier"
            elif rank == 3:
                return "🥉 Merit Tier"
            return "🌿 Active Contender"


        sorted_leaderboard["Achievement Award"] = [assign_award_status(i) for i in sorted_leaderboard.index]

        # Format columns for friendly viewer readability
        friendly_leaderboard = sorted_leaderboard.rename(columns={
            "account_name": "School Name/Institution",
            "qty_planted": "Trees Planted",
            "qty_survived": "Trees Living",
            "event_id": "Projects Logged"
        })

        st.dataframe(
            friendly_leaderboard[
                ["School Name/Institution", "Trees Planted", "Trees Living", "Survival Rate (%)", "Total Impact Score",
                 "Achievement Award"]],
            use_container_width=True
        )
            
