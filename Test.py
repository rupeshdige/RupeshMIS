import streamlit as st
import pandas as pd
import base64
import os
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px

# === CONFIG ===

bg_image = os.path.join("Travel_Photo.jpg")
logo_path = os.path.join("TC-logo-Vertical.png")
tm_logo_path = os.path.join("TM logo.png")
user_file = os.path.join("Emp_base.csv")
current_base_file = os.path.join("Current_Base.xlsb")
sap_file = os.path.join("SAP.xlsb")
target_file = os.path.join("Target.csv")

st.set_page_config(page_title="Thomas Cook Dashboard", layout="wide")

# Initialize session state
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "access" not in st.session_state:
    st.session_state.access = ""
if "change_pw" not in st.session_state:
    st.session_state.change_pw = False
if "active_tab" not in st.session_state:
    st.session_state.active_tab = "Dashboard"
if "refresh_trigger" not in st.session_state:
    st.session_state.refresh_trigger = False

# Global CSS for banner and app styling
st.markdown("""
    <style>
    .stApp {
        background-color: #afcff0;
    }
    button, div[data-testid="stFormSubmitButton"] > button {
        background-color: orange !important;
        color: white !important;
        border: none;
    }
    button:hover { background-color: #6a4500 !important; }
    button:active { background-color: #d1730f !important; }
    .top-banner {
        background-color: #003087 !important;
        color: #ffffff !important;
        height: 50px;
        width: 100%;
        position: sticky;
        top: 0;
        display: flex;
        align-items: center;
        justify-content: space-between;
        font-size: 24px;
        font-weight: bold !important;
        z-index: 10000;
        box-sizing: border-box;
        padding: 0 10px;
    }
    .banner-text {
        flex-grow: 1;
        text-align: center;
        color: #ffffff !important;
        font-weight: bold !important;
    }
    .kpi-container {
        margin-bottom: 30px;
    }
    .kpi-card { 
        margin: 0 5px; 
        min-height: 100px;
        padding: 12px;
        border-radius: 10px;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
        transition: transform 0.2s;
    }
    .kpi-card:hover {
        transform: scale(1.05);
    }
    .kpi-card.total-sales {
        background: linear-gradient(135deg, #fad97f 0%, #fff8dc 100%);
        color: #000000;
        border: 2px solid #e6e6fa;
    }
    .kpi-card.other {
        background: linear-gradient(135deg, #cfcdca 0%, #fff8dc 100%);
        border: 2px solid #e6e6fa;
    }
    .kpi-card h3 {
        font-size: 20px;
        font-weight: 700;
        margin: 0 0 8px 0;
        display: flex;
        align-items: center;
        text-align: center;
    }
    .kpi-card h3 i {
        margin-right: 8px;
    }
    .kpi-card p {
        font-size: 14px;
        font-weight: 600;
        margin: 5px 0;
    }
    .main-content {
        margin-top: 20px;
        margin-left: 0;
        padding: 0;
    }
    </style>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css">
""", unsafe_allow_html=True)

@st.cache_data
def load_data():
    try:
        # Current date and yesterday for filtering
        current_date = datetime.now()
        yesterday = current_date - timedelta(days=1)
        current_month = current_date.month
        current_year = current_date.year
        previous_year = current_year - 1
        previous_year_yesterday = yesterday.replace(year=previous_year)

        # Required and optional columns
        required_cols = ["Sale In Cr", "Travel M", "Travel Y"]
        optional_cols = ["REGION", "TOUR START DATE", "FILE_DATE", "TOTAL_PAX", "Travel Qtr", "Final Buniess", "Destination", "FILE_TYPE", "REGION_B", "FILE_SUB_TYPE"]

        # Load Current_Base.xlsb (Jul-Dec 2024 and 2025, filtered by FILE_DATE)
        df_current = pd.read_excel(current_base_file, engine='pyxlsb')
        df_current.columns = df_current.columns.str.strip()
        df_current["Source"] = "Current_Base"  # Add source identifier

        # Rename only TOUR_START_DATE and Destination
        df_current = df_current.rename(columns={
            "TOUR_START_DATE": "TOUR START DATE",
            "Destination": "Destination"
        })

        # Normalize Final Buniess, FILE_TYPE, REGION_B, and FILE_SUB_TYPE to uppercase
        if "Final Buniess" in df_current.columns:
            df_current["Final Buniess"] = df_current["Final Buniess"].str.strip().str.upper()
        if "FILE_TYPE" in df_current.columns:
            df_current["FILE_TYPE"] = df_current["FILE_TYPE"].str.strip().str.upper()
        if "REGION_B" in df_current.columns:
            df_current["REGION_B"] = df_current["REGION_B"].str.strip().str.upper()
        if "FILE_SUB_TYPE" in df_current.columns:
            df_current["FILE_SUB_TYPE"] = df_current["FILE_SUB_TYPE"].str.strip().str.upper()

        # Create BAREADEP column
        if "FILE_SUB_TYPE" in df_current.columns and "Final Buniess" in df_current.columns:
            df_current["BAREADEP"] = df_current.apply(
                lambda row: "NTCIL" if row["FILE_SUB_TYPE"] in ["ESCORTED TOUR", "CRUISE", "RAIL"] else row["Final Buniess"], axis=1
            )
        else:
            df_current["BAREADEP"] = df_current["Final Buniess"] if "Final Buniess" in df_current.columns else "Unknown"

        # Check required columns
        missing_required = [col for col in required_cols if col not in df_current.columns]
        if missing_required:
            st.error(f"Missing required columns in {current_base_file}: {', '.join(missing_required)}")
            return pd.DataFrame()

        # Log missing optional columns
        missing_optional = [col for col in optional_cols if col not in df_current.columns]
        if missing_optional:
            st.warning(f"Missing optional columns in {current_base_file}: {', '.join(missing_optional)}")

        # Filter Current_Base for Jul-Dec 2024 and 2025, FILE_DATE <= yesterday
        df_current["Travel M"] = df_current["Travel M"].astype(str).str.strip().str.lower()
        df_current["Travel Y"] = df_current["Travel Y"].astype(int)
        month_map = {
            "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
            "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
            "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
            "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
            "1": 1, "2": 2, "3": 3, "4": 4, "5": 5, "6": 6,
            "7": 7, "8": 8, "9": 9, "10": 10, "11": 11, "12": 12
        }
        df_current["Month Num"] = df_current["Travel M"].map(month_map)
        df_current["Month Name"] = df_current["Month Num"].map({
            1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
            7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"
        })
        df_current["FILE_DATE"] = pd.to_datetime(df_current["FILE_DATE"], errors="coerce")
        df_current = df_current[
            ((df_current["Travel Y"] == current_year) & (df_current["Month Num"] >= current_month) & 
             (df_current["FILE_DATE"] <= yesterday)) |
            ((df_current["Travel Y"] == previous_year) & (df_current["Month Num"] >= current_month) & 
             (df_current["FILE_DATE"] <= previous_year_yesterday))
        ]

        # Load SAP.xlsb (Jan-Jun 2024 and 2025)
        df_sap = pd.read_excel(sap_file, engine='pyxlsb')
        df_sap.columns = df_sap.columns.str.strip()
        df_sap["Source"] = "SAP"  # Add source identifier

        # Rename only TOUR_START_DATE and Group Destination
        df_sap = df_sap.rename(columns={
            "TOUR_START_DATE": "TOUR START DATE",
            "Group Destination": "Destination"
        })

        # Normalize Final Buniess, FILE_TYPE, REGION_B, and FILE_SUB_TYPE to uppercase
        if "Final Buniess" in df_sap.columns:
            df_sap["Final Buniess"] = df_sap["Final Buniess"].str.strip().str.upper()
        if "FILE_TYPE" in df_sap.columns:
            df_sap["FILE_TYPE"] = df_sap["FILE_TYPE"].str.strip().str.upper()
        if "REGION_B" in df_sap.columns:
            df_sap["REGION_B"] = df_sap["REGION_B"].str.strip().str.upper()
        if "FILE_SUB_TYPE" in df_sap.columns:
            df_sap["FILE_SUB_TYPE"] = df_sap["FILE_SUB_TYPE"].str.strip().str.upper()

        # Create BAREADEP column
        if "FILE_SUB_TYPE" in df_sap.columns and "Final Buniess" in df_sap.columns:
            df_sap["BAREADEP"] = df_sap.apply(
                lambda row: "NTCIL" if row["FILE_SUB_TYPE"] in ["ESCORTED TOUR", "CRUISE", "RAIL"] else row["Final Buniess"], axis=1
            )
        else:
            df_sap["BAREADEP"] = df_sap["Final Buniess"] if "Final Buniess" in df_sap.columns else "Unknown"

        # Check required columns
        missing_required = [col for col in required_cols if col not in df_sap.columns]
        if missing_required:
            st.error(f"Missing required columns in {sap_file}: {', '.join(missing_required)}")
            return pd.DataFrame()

        # Log missing optional columns
        missing_optional = [col for col in optional_cols if col not in df_sap.columns]
        if missing_optional:
            st.warning(f"Missing optional columns in {sap_file}: {', '.join(missing_optional)}")

        # Filter SAP for Jan-Jun 2024 and 2025
        df_sap["Travel M"] = df_sap["Travel M"].astype(str).str.strip().str.lower()
        df_sap["Travel Y"] = df_sap["Travel Y"].astype(int)
        df_sap["Month Num"] = df_sap["Travel M"].map(month_map)
        df_sap["Month Name"] = df_sap["Month Num"].map({
            1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
            7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"
        })
        df_sap = df_sap[
            ((df_sap["Travel Y"] == current_year) & (df_sap["Month Num"] >= 1) & (df_sap["Month Num"] < current_month)) |
            ((df_sap["Travel Y"] == previous_year) & (df_sap["Month Num"] >= 1) & (df_sap["Month Num"] < current_month))
        ]

        # Combine DataFrames
        df = pd.concat([df_current, df_sap], ignore_index=True)
        df["Sale In Cr"] = pd.to_numeric(df["Sale In Cr"], errors="coerce").fillna(0)
        if "TOTAL_PAX" in df.columns:
            df["TOTAL_PAX"] = pd.to_numeric(df["TOTAL_PAX"], errors="coerce").fillna(0)
        if "TOUR START DATE" in df.columns:
            df["TOUR START DATE"] = pd.to_datetime(df["TOUR START DATE"], errors="coerce")
        return df
    except Exception as e:
        st.error(f"Failed to load data: {str(e)}")
        return pd.DataFrame()

@st.cache_data
def load_target_data():
    try:
        df = pd.read_csv(target_file)
        df.columns = df.columns.str.strip()
        df = df.rename(columns={
            col: "Region" for col in df.columns if col.lower() in ["region", "reg"]
        })
        df = df.rename(columns={
            col: "Month" for col in df.columns if col.lower() in ["month", "month name"]
        })
        df = df.rename(columns={
            col: "Target Amount" for col in df.columns if col.lower() in ["target", "target amount", "target_cr"]
        })
        required_cols = ["Region", "Month", "Target Amount"]
        if not all(col in df.columns for col in required_cols):
            st.error(f"Missing required columns in {target_file}: {', '.join(set(required_cols) - set(df.columns))}")
            return pd.DataFrame()
        if "Target Amount" in df.columns and df["Target Amount"].max() > 1e7:
            df["Target Amount Cr"] = df["Target Amount"] / 1e7
        else:
            df["Target Amount Cr"] = df["Target Amount"]
        return df
    except Exception as e:
        st.error(f"Failed to load target data from {target_file}: {str(e)}")
        return pd.DataFrame()

def set_background(image_path):
    try:
        with open(image_path, "rb") as file:
            encoded = base64.b64encode(file.read()).decode()
        ext = image_path.split('.')[-1]
        st.markdown(f"""
            <style>
            .stApp {{
                background-image: url("data:image/{ext};base64,{encoded}");
                background-size: cover;
                background-repeat: no-repeat;
                background-position: center;
            }}
            </style>
        """, unsafe_allow_html=True)
    except FileNotFoundError:
        st.markdown("""
            <style>
            .stApp {{
                background-color: #f0f2f6;
            }}
            </style>
        """, unsafe_allow_html=True)

def change_password():
    users_df = pd.read_csv(user_file)
    pw_col = next((col for col in users_df.columns if col.strip().lower() == "password"), None)
    if not pw_col:
        st.error("Password column not found in Emp_base.csv")
        return

    with st.form("change_password_form"):
        st.markdown("### Change Password")
        current_password = st.text_input("Current Password", type="password")
        new_password = st.text_input("New Password", type="password")
        confirm_password = st.text_input("Confirm New Password", type="password")
        submitted = st.form_submit_button("Update Password")

        if submitted:
            user_row = users_df[
                (users_df["User Name"].str.strip().str.lower() == st.session_state.username.strip().lower()) &
                (users_df[pw_col].astype(str).str.strip() == current_password.strip())
            ]
            if user_row.empty:
                st.error("Current password is incorrect.")
                return
            if new_password != confirm_password:
                st.error("New password and confirm password do not match.")
                return
            if not new_password:
                st.error("New password cannot be empty.")
                return

            users_df.loc[
                users_df["User Name"].str.strip().str.lower() == st.session_state.username.strip().lower(),
                pw_col
            ] = new_password.strip()
            
            try:
                users_df.to_csv(user_file, index=False)
                st.success("Password updated successfully!")
            except Exception as e:
                st.error(f"Failed to update password: {str(e)}")

def refresh_callback():
    st.cache_data.clear()
    load_data.clear()
    load_target_data.clear()
    st.session_state.refresh_trigger = True

def dashboard_page():
    # Load TM logo for banner
    try:
        with open(tm_logo_path, "rb") as img_file:
            tm_logo_base64 = base64.b64encode(img_file.read()).decode()
        tm_logo_html = f"<img src='data:image/png;base64,{tm_logo_base64}' style='height: 40px; margin-left: 10px;'>"
    except FileNotFoundError:
        tm_logo_html = "<p style='color: red; margin-left: 10px;'>TM Logo not found</p>"

    # Display top banner with logo and text (no refresh button)
    st.markdown(f"""
        <div class="top-banner">
            {tm_logo_html}
            <div class="banner-text">YOY Sales Comparison Dashboard</div>
        </div>
    """, unsafe_allow_html=True)

    # Handle refresh action
    if st.session_state.refresh_trigger:
        st.session_state.refresh_trigger = False
        st.rerun()

    # Main content container
    with st.container():
        st.markdown('<div class="main-content">', unsafe_allow_html=True)

        df = load_data()
        if df.empty:
            st.error("No data available for Dashboard.")
            st.markdown('</div>', unsafe_allow_html=True)
            return

        # Verify required columns
        if "FILE_SUB_TYPE" not in df.columns:
            st.error("FILE_SUB_TYPE column not found in data.")
            st.markdown('</div>', unsafe_allow_html=True)
            return
        if "BAREADEP" not in df.columns:
            st.error("BAREADEP column not created properly.")
            st.markdown('</div>', unsafe_allow_html=True)
            return

        with st.sidebar:
            st.subheader("👤 Profile")
            with st.expander("🔽 Profile Options"):
                st.text(f"User: {st.session_state.username}")
                st.text(f"Role: {st.session_state.access}")
                if st.button("🚪 Logout"):
                    for key in list(st.session_state.keys()):
                        del st.session_state[key]
                    st.rerun()
                change_password()
            st.markdown("---")
            st.button("↻ Refresh Data", on_click=refresh_callback)
            st.title("🔍 Filters")
            region_options = ["All"] + sorted(df["REGION"].dropna().astype(str).unique()) if "REGION" in df.columns else ["All"]
            region = st.selectbox("Region", region_options, key="dash_region")
            travel_qtr_options = ["All"] + sorted(df["Travel Qtr"].dropna().astype(str).unique()) if "Travel Qtr" in df.columns else ["All"]
            quarter = st.selectbox("Travel Quarter", travel_qtr_options, key="dash_quarter")
            final_business_options = ["All"] + sorted(df["Final Buniess"].dropna().astype(str).unique()) if "Final Buniess" in df.columns else ["All"]
            final_business = st.selectbox("Final Buniess", final_business_options, key="dash_final_business")

        # Apply filters
        filtered_df = df.copy()
        if region != "All" and "REGION" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["REGION"].astype(str) == region]
        if quarter != "All" and "Travel Qtr" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["Travel Qtr"].astype(str) == quarter]
        if final_business != "All" and "Final Buniess" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["Final Buniess"].astype(str) == final_business]

        # Calculate sales for current year (as of yesterday) and previous year
        current_date = datetime.now()
        yesterday = current_date - timedelta(days=1)
        current_year = current_date.year
        current_month = current_date.month
        previous_year = current_year - 1
        previous_year_yesterday = yesterday.replace(year=previous_year)

        # Current year sales: Jan-Jun from SAP.xlsb, Jul-Dec from Current_Base.xlsb
        current_year_df = filtered_df[filtered_df["Travel Y"] == current_year]
        sap_2025 = pd.DataFrame()
        current_base_2025 = pd.DataFrame()
        if not current_year_df.empty:
            sap_2025 = current_year_df[
                (current_year_df["Source"] == "SAP") & 
                (current_year_df["Month Num"] >= 1) & 
                (current_year_df["Month Num"] < current_month)
            ]
            current_base_2025 = current_year_df[
                (current_year_df["Source"] == "Current_Base") & 
                (current_year_df["Month Num"] >= current_month)
            ]
            current_year_df = pd.concat([sap_2025, current_base_2025], ignore_index=True)
        sales_current = current_year_df["Sale In Cr"].sum()

        # Previous year sales: Jan-Jun from SAP.xlsb, Jul-Dec from Current_Base.xlsb
        previous_year_df = filtered_df[filtered_df["Travel Y"] == previous_year]
        sap_2024 = pd.DataFrame()
        current_base_2024 = pd.DataFrame()
        if not previous_year_df.empty:
            sap_2024 = previous_year_df[
                (previous_year_df["Source"] == "SAP") & 
                (previous_year_df["Month Num"] >= 1) & 
                (previous_year_df["Month Num"] < current_month)
            ]
            current_base_2024 = previous_year_df[
                (previous_year_df["Source"] == "Current_Base") & 
                (previous_year_df["Month Num"] >= current_month)
            ]
            previous_year_df = pd.concat([sap_2024, current_base_2024], ignore_index=True)
        sales_previous = previous_year_df["Sale In Cr"].sum()

        # Calculate growth percentage
        growth_pct = ((sales_current - sales_previous) / sales_previous * 100) if sales_previous > 0 else 0

        # KPI Cards (Total Sales, LOLH, LOSH, LTDM, AIR)
        with st.container():
            st.markdown('<div class="kpi-container">', unsafe_allow_html=True)
            cols = st.columns([2, 2, 2, 2, 2])
            required_businesses = ["Total Sales", "LOLH", "LOSH", "LTDM", "AIR"]
            icon_map = {
                "Total Sales": "fa-chart-line",
                "LOLH": "fa-globe-asia",
                "LOSH": "fa-globe-europe",
                "LTDM": "fa-globe-africa",
                "AIR": "fa-plane"
            }
            for idx, business in enumerate(required_businesses):
                with cols[idx]:
                    if business == "Total Sales":
                        # Total Sales card
                        card_style = "total-sales"
                        text_style = "color: #000000; font-weight: 600;"
                        header_style = "color: #000000;"
                        st.markdown(f"""
                            <div class="kpi-card {card_style}" style='text-align: center;'>
                                <h3 style='{header_style}'><i class="fas {icon_map[business]}"></i> Total Sales (Cr)</h3>
                                <p style='{text_style}'>2025 (as of {yesterday.strftime('%b %d')}): ₹{sales_current:.2f} Cr</p>
                                <p style='{text_style}'>2024 (as of {yesterday.strftime('%b %d')}): ₹{sales_previous:.2f} Cr</p>
                                <p style='{text_style}'>Growth: {growth_pct:.2f}% 
                                    {'<i class="fas fa-arrow-up" style="color: #008000;"></i>' if growth_pct > 0 else '<i class="fas fa-arrow-down" style="color: #ff0000;"></i>' if growth_pct < 0 else ''}
                                </p>
                            </div>
                        """, unsafe_allow_html=True)
                    elif "Final Buniess" in filtered_df.columns and business in filtered_df["Final Buniess"].dropna().astype(str).unique():
                        # Business-specific cards
                        current_business_df = current_year_df[current_year_df["Final Buniess"].astype(str) == business]
                        previous_business_df = previous_year_df[previous_year_df["Final Buniess"].astype(str) == business]
                        current_sales = current_business_df["Sale In Cr"].sum()
                        previous_sales = previous_business_df["Sale In Cr"].sum()
                        growth = ((current_sales - previous_sales) / previous_sales * 100) if previous_sales > 0 else 0
                        growth_style = "color: #008000;" if growth > 0 else "color: #ff0000;" if growth < 0 else ""
                        growth_icon = '<i class="fas fa-arrow-up"></i>' if growth > 0 else '<i class="fas fa-arrow-down"></i>' if growth < 0 else ''
                        card_style = "other"
                        text_style = "font-weight: 600;"
                        st.markdown(f"""
                            <div class="kpi-card {card_style}" style='text-align: center;'>
                                <h3><i class="fas {icon_map[business]}"></i> {business} (Cr)</h3>
                                <p style='{text_style}'>2025 (as of {yesterday.strftime('%b %d')}): ₹{current_sales:.2f} Cr</p>
                                <p style='{text_style}'>2024 (as of {yesterday.strftime('%b %d')}): ₹{previous_sales:.2f} Cr</p>
                                <p style='{text_style} {growth_style}'>Growth: {growth:.2f}% {growth_icon}</p>
                            </div>
                        """, unsafe_allow_html=True)
                    else:
                        # No data for business-specific card
                        card_style = "other"
                        text_style = "color: #ff4b4b; font-weight: 600;"
                        st.markdown(f"""
                            <div class="kpi-card {card_style}" style='text-align: center;'>
                                <h3><i class="fas {icon_map[business]}"></i> {business} (Cr)</h3>
                                <p style='{text_style}'>No Data Available</p>
                            </div>
                        """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        # Prepare data for bar graph using Travel M (Jan-Dec)
        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        
        # Aggregate sales by Month Name for current year (Jan-Jun from SAP, Jul-Dec from Current_Base)
        current_year_monthly = current_year_df.groupby("Month Name")["Sale In Cr"].sum().reindex(months, fill_value=0)
        
        # Aggregate sales by Month Name for previous year (Jan-Jun from SAP, Jul-Dec from Current_Base)
        previous_year_monthly = previous_year_df.groupby("Month Name")["Sale In Cr"].sum().reindex(months, fill_value=0)
        
        # Calculate month-wise growth percentage
        growth_monthly = []
        for month in months:
            sales_current = current_year_monthly.get(month, 0)
            sales_prev = previous_year_monthly.get(month, 0)
            growth = ((sales_current - sales_prev) / sales_prev * 100) if sales_prev > 0 else 0
            growth_monthly.append(growth)

        # Create Plotly bar figure for month-wise sales
        fig = go.Figure()
        
        # Add bars for previous year with normal font
        fig.add_trace(go.Bar(
            x=months,
            y=previous_year_monthly,
            name=f"{previous_year} Sales",
            marker_color="blue",
            text=previous_year_monthly,
            texttemplate="%{y:.2f}",
            textposition="auto",
            textfont=dict(
                family="Arial, sans-serif",
                size=12
            )
        ))
        
        # Add bars for current year with normal font
        fig.add_trace(go.Bar(
            x=months,
            y=current_year_monthly,
            name=f"{current_year} Sales",
            marker_color="orange",
            text=current_year_monthly,
            texttemplate="%{y:.2f}",
            textposition="auto",
            textfont=dict(
                family="Arial, sans-serif",
                size=12
            )
        ))
        
        # Add single Growth % line with bold font for non-zero values
        fig.add_trace(go.Scatter(
            x=months,
            y=growth_monthly,
            name="Growth %",
            yaxis="y2",
            mode="lines+markers+text",
            line=dict(color="darkgreen", width=2),
            marker=dict(color="darkgreen", size=8),
            text=[f"{growth_value:.2f}%" if growth_value != 0 else "" for growth_value in growth_monthly],
            textposition="top center",
            textfont=dict(
                family="Arial Black, Arial, sans-serif",
                size=14,
                color=["red" if growth_value < 0 else "darkgreen" if growth_value > 0 else "darkgreen" for growth_value in growth_monthly]
            )
        ))

        # Update layout for dual y-axes with formatted labels and legend at bottom
        fig.update_layout(
            title=dict(
                text=f"Month-wise Sales ({previous_year} vs {current_year}, as of {yesterday.strftime('%b %d')}) with Growth %",
                x=0.5,
                xanchor="center",
                y=0.95,
                font=dict(family="Arial, sans-serif", size=16, color="black")
            ),
            xaxis=dict(title="Month"),
            yaxis=dict(
                title="Sales (Cr)",
                side="left",
                tickformat=".2f"
            ),
            yaxis2=dict(
                title="Growth %",
                overlaying="y",
                side="right",
                tickformat=".2f",
                ticksuffix="%"
            ),
            barmode="group",
            legend=dict(
                x=0.5,
                y=-0.1,
                xanchor="center",
                yanchor="top",
                orientation="h"
            ),
            template="plotly_white",
            margin=dict(t=80, b=80, l=60, r=60)
        )

        # Prepare data for business contribution donut chart (2025)
        businesses = ["LOLH", "LOSH", "LTDM", "AIR"]
        sales_values = []
        for business in businesses:
            if "Final Buniess" in current_year_df.columns and business in current_year_df["Final Buniess"].dropna().astype(str).unique():
                business_sales = current_year_df[current_year_df["Final Buniess"].astype(str) == business]["Sale In Cr"].sum()
                sales_values.append(business_sales)
            else:
                sales_values.append(0)

        # Create business contribution donut chart
        fig_donut_business = go.Figure(data=[
            go.Pie(
                labels=businesses,
                values=sales_values,
                hole=0.4,
                textinfo='label+percent',
                insidetextorientation='radial',
                marker=dict(colors=['#ff7f0e', '#1f77b4', '#2ca02c', '#9467bd']),  # Orange, Blue, Green, Purple
                textfont=dict(family="Arial, sans-serif", size=12)
            )
        ])
        fig_donut_business.update_layout(
            title=dict(
                text=f"Business Contribution (2025, as of {yesterday.strftime('%b %d')})",
                x=0.5,
                xanchor="center",
                y=0.95,
                font=dict(family="Arial, sans-serif", size=14, color="black")
            ),
            showlegend=True,
            legend=dict(
                x=0.5,
                y=-0.1,
                xanchor="center",
                yanchor="top",
                orientation="h"
            ),
            template="plotly_white",
            margin=dict(t=60, b=60, l=40, r=40)
        )

        # Prepare data for file type contribution pie chart (2025)
        file_types = ["GIT", "FIT", "AIR"]
        file_type_sales = []
        for file_type in file_types:
            if "FILE_TYPE" in current_year_df.columns:
                file_type_sales_value = current_year_df[current_year_df["FILE_TYPE"].astype(str).str.upper() == file_type]["Sale In Cr"].sum()
                file_type_sales.append(file_type_sales_value)
            else:
                file_type_sales.append(0)

        # Create file type contribution pie chart
        fig_pie_file_type = go.Figure(data=[
            go.Pie(
                labels=file_types,
                values=file_type_sales,
                hole=0,
                textinfo='label+percent',
                insidetextorientation='radial',
                marker=dict(colors=['#d62728', '#17becf', '#2ca02c']),  # Red for GIT, Cyan for FIT, Green for AIR
                textfont=dict(family="Arial, sans-serif", size=12)
            )
        ])
        fig_pie_file_type.update_layout(
            title=dict(
                text=f"File Type Contribution (2025, as of {yesterday.strftime('%b %d')})",
                x=0.5,
                xanchor="center",
                y=0.95,
                font=dict(family="Arial, sans-serif", size=14, color="black")
            ),
            showlegend=True,
            legend=dict(
                x=0.5,
                y=-0.1,
                xanchor="center",
                yanchor="top",
                orientation="h"
            ),
            template="plotly_white",
            margin=dict(t=60, b=60, l=40, r=40)
        )

        # Display existing charts side by side with 50%, 25%, 25% width
        col1, col2, col3 = st.columns([5, 2.5, 2.5])
        with col1:
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            if sum(sales_values) > 0:
                st.plotly_chart(fig_donut_business, use_container_width=True)
            else:
                st.markdown("<p style='text-align: center; color: #ff4b4b;'>No data available for Business Contribution chart.</p>", unsafe_allow_html=True)
        with col3:
            if sum(file_type_sales) > 0:
                st.plotly_chart(fig_pie_file_type, use_container_width=True)
            else:
                st.markdown("<p style='text-align: center; color: #ff4b4b;'>No data available for File Type Contribution chart.</p>", unsafe_allow_html=True)



        # Prepare data for region-wise bar graph
        regions = sorted(set(current_year_df["REGION_B"].dropna().astype(str).unique()) | set(previous_year_df["REGION_B"].dropna().astype(str).unique()))
        current_year_region = current_year_df.groupby("REGION_B")["Sale In Cr"].sum().reindex(regions, fill_value=0)
        previous_year_region = previous_year_df.groupby("REGION_B")["Sale In Cr"].sum().reindex(regions, fill_value=0)
        
        # Calculate region-wise growth percentage
        growth_region = [(current_year_region.get(region, 0) - previous_year_region.get(region, 0)) / previous_year_region.get(region, 0) * 100 if previous_year_region.get(region, 0) > 0 else 0 for region in regions]

        # Create Plotly bar figure for region-wise sales
        fig_region = go.Figure()
        
        # Add bars for previous year
        fig_region.add_trace(go.Bar(
            x=regions,
            y=previous_year_region,
            name=f"{previous_year} Sales",
            marker_color="blue",
            text=previous_year_region,
            texttemplate="%{y:.2f}",
            textposition="auto",
            textfont=dict(
                family="Arial, sans-serif",
                size=12
            )
        ))
        
        # Add bars for current year
        fig_region.add_trace(go.Bar(
            x=regions,
            y=current_year_region,
            name=f"{current_year} Sales",
            marker_color="orange",
            text=current_year_region,
            texttemplate="%{y:.2f}",
            textposition="auto",
            textfont=dict(
                family="Arial, sans-serif",
                size=12
            )
        ))
        
        # Add Growth % line
        fig_region.add_trace(go.Scatter(
            x=regions,
            y=growth_region,
            name="Growth %",
            yaxis="y2",
            mode="lines+markers+text",
            line=dict(color="darkgreen", width=2),
            marker=dict(color="darkgreen", size=8),
            text=[f"{growth_value:.2f}%" if growth_value != 0 else "" for growth_value in growth_region],
            textposition="top center",
            textfont=dict(
                family="Arial Black, Arial, sans-serif",
                size=14,
                color=["red" if growth_value < 0 else "darkgreen" if growth_value > 0 else "darkgreen" for growth_value in growth_region]
            )
        ))

        # Update layout for region-wise graph
        fig_region.update_layout(
            title=dict(
                text=f"Region-wise Sales ({previous_year} vs {current_year}, as of {yesterday.strftime('%b %d')}) with Growth %",
                x=0.5,
                xanchor="center",
                y=0.95,
                font=dict(family="Arial, sans-serif", size=16, color="black")
            ),
            xaxis=dict(title="Region"),
            yaxis=dict(
                title="Sales (Cr)",
                side="left",
                tickformat=".2f"
            ),
            yaxis2=dict(
                title="Growth %",
                overlaying="y",
                side="right",
                tickformat=".2f",
                ticksuffix="%"
            ),
            barmode="group",
            legend=dict(
                x=0.5,
                y=-0.1,
                xanchor="center",
                yanchor="top",
                orientation="h"
            ),
            template="plotly_white",
            margin=dict(t=80, b=80, l=60, r=60)
        )

        # Prepare data for horizontal bar plot (2024 and 2025, BAREADEP)
        barea_sales_current = current_year_df.groupby("BAREADEP")["Sale In Cr"].sum().reset_index()
        barea_sales_previous = previous_year_df.groupby("BAREADEP")["Sale In Cr"].sum().reset_index()
        barea_sales_current = barea_sales_current[barea_sales_current["Sale In Cr"] > 0]  # Exclude zero sales
        barea_sales_previous = barea_sales_previous[barea_sales_previous["Sale In Cr"] > 0]  # Exclude zero sales
        barea_sales_current = barea_sales_current.sort_values("BAREADEP")  # Sort for consistency
        barea_sales_previous = barea_sales_previous.sort_values("BAREADEP")  # Sort for consistency

        # Combine categories from both years
        barea_categories = sorted(set(barea_sales_current["BAREADEP"]).union(set(barea_sales_previous["BAREADEP"])))
        barea_sales_current = barea_sales_current.set_index("BAREADEP").reindex(barea_categories, fill_value=0).reset_index()
        barea_sales_previous = barea_sales_previous.set_index("BAREADEP").reindex(barea_categories, fill_value=0).reset_index()

        # Calculate growth percentage
        growth_barea = [
            (barea_sales_current[barea_sales_current["BAREADEP"] == cat]["Sale In Cr"].iloc[0] - 
             barea_sales_previous[barea_sales_previous["BAREADEP"] == cat]["Sale In Cr"].iloc[0]) / 
             barea_sales_previous[barea_sales_previous["BAREADEP"] == cat]["Sale In Cr"].iloc[0] * 100 
             if barea_sales_previous[barea_sales_previous["BAREADEP"] == cat]["Sale In Cr"].iloc[0] > 0 else 0 
             for cat in barea_categories
        ]

        # Create color map for BAREADEP categories
        colors = px.colors.qualitative.Plotly[:len(barea_categories)]  # Use Plotly qualitative colors
        color_map = dict(zip(barea_categories, colors))

        # Create horizontal bar plot
        fig_barea = go.Figure()

        # Add horizontal bars for 2024 sales
        fig_barea.add_trace(go.Bar(
            y=barea_categories,
            x=barea_sales_previous["Sale In Cr"],
            name="2024 Sales",
            marker_color="blue",
            text=[f"₹{val:.2f} Cr" for val in barea_sales_previous["Sale In Cr"]],
            texttemplate="%{text}",
            textposition="auto",
            textfont=dict(
                family="Arial, sans-serif",
                size=12
            ),
            orientation='h'
        ))

        # Add horizontal bars for 2025 sales
        fig_barea.add_trace(go.Bar(
            y=barea_categories,
            x=barea_sales_current["Sale In Cr"],
            name="2025 Sales",
            marker_color="orange",
            text=[f"₹{val:.2f} Cr" for val in barea_sales_current["Sale In Cr"]],
            texttemplate="%{text}",
            textposition="auto",
            textfont=dict(
                family="Arial, sans-serif",
                size=12
            ),
            orientation='h'
        ))

        # Add Growth % line
        fig_barea.add_trace(go.Scatter(
            y=barea_categories,
            x=growth_barea,
            name="Growth %",
            xaxis="x2",
            mode="lines+markers+text",
            line=dict(color="darkgreen", width=2),
            marker=dict(color="darkgreen", size=8),
            text=[f"{growth_value:.2f}%" if growth_value != 0 else "" for growth_value in growth_barea],
            textposition="middle right",
            textfont=dict(
                family="Arial Black, Arial, sans-serif",
                size=14,
                color=["red" if growth_value < 0 else "darkgreen" if growth_value > 0 else "darkgreen" for growth_value in growth_barea]
            )
        ))

        # Update layout for horizontal bar plot with dual axes
        fig_barea.update_layout(
            title=dict(
                text=f"Business Area-wise Sales (2024 vs 2025, as of {yesterday.strftime('%b %d')}) with Growth %",
                x=0.5,
                xanchor="center",
                y=0.95,
                font=dict(family="Arial, sans-serif", size=16, color="black")
            ),
            yaxis=dict(title="Business Area"),
            xaxis=dict(
                title="Sales (Cr)",
                tickformat=".2f"
            ),
            xaxis2=dict(
                title="Growth %",
                overlaying="x",
                side="top",
                tickformat=".2f",
                ticksuffix="%"
            ),
            barmode="group",
            showlegend=True,
            legend=dict(
                x=0.5,
                y=-0.1,
                xanchor="center",
                yanchor="top",
                orientation="h"
            ),
            template="plotly_white",
            margin=dict(t=80, b=80, l=100, r=60)
        )

        # Display region-wise and business area charts in the same row (60% and 40%)
        with st.container():
            col_region, col_barea = st.columns([6, 4])
            with col_region:
                st.plotly_chart(fig_region, use_container_width=True)
            with col_barea:
                st.plotly_chart(fig_barea, use_container_width=True)
        
        st.markdown('</div>', unsafe_allow_html=True)

def drr_summary_page():
    # Set background color for DRR page
    st.markdown("""
        <style>
        .stApp {
            background-color: #afcff0;
        }
        button, div[data-testid="stFormSubmitButton"] > button {
            background-color: orange !important;
            color: white !important;
            border: none;
        }
        button:hover { background-color: #6a4500 !important; }
        button:active { background-color: #d1730f !important; }
        </style>
    """, unsafe_allow_html=True)

    # Handle refresh action
    if st.session_state.refresh_trigger:
        st.session_state.refresh_trigger = False
        st.rerun()

    df = load_data()
    if df.empty:
        st.error("No data available for DRR Summary.")
        return

    with st.sidebar:
        st.subheader("👤 Profile")
        with st.expander("🔽 Profile Options"):
            st.text(f"User: {st.session_state.username}")
            st.text(f"Role: {st.session_state.access}")
            if st.button("🚪 Logout"):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()
            change_password()
        st.markdown("---")
        st.button("↻ Refresh Data", on_click=refresh_callback)
        st.title("🔍 Filters")
        date_range = st.date_input("Select FILE_DATE Range", 
                                 [df["FILE_DATE"].min(), df["FILE_DATE"].max()] if "FILE_DATE" in df.columns else [datetime.now(), datetime.now()])

    st.title("📊 Detailed DRR Summary")
    if len(date_range) == 2 and "FILE_DATE" in df.columns:
        df = df[(df["FILE_DATE"] >= pd.to_datetime(date_range[0])) & (df["FILE_DATE"] <= pd.to_datetime(date_range[1]))]
    st.markdown("### No data displayed (all tables and KPIs removed).")
#################################################################################################################################################################################
def target_vs_ach_page():
    # Define date variables
    current_date = datetime.now()
    yesterday = current_date - timedelta(days=1)
    current_year = current_date.year
    current_month = current_date.month
    previous_year = current_year - 1
    previous_year_yesterday = yesterday.replace(year=previous_year)

    # Load TM logo for banner
    try:
        with open(tm_logo_path, "rb") as img_file:
            tm_logo_base64 = base64.b64encode(img_file.read()).decode()
        tm_logo_html = f"<img src='data:image/png;base64,{tm_logo_base64}' style='height: 40px; margin-left: 10px;'>"
    except FileNotFoundError:
        tm_logo_html = "<p style='color: red; margin-left: 10px;'>TM Logo not found</p>"

    # Display top banner with logo and text (no refresh button)
    st.markdown(f"""
        <div class="top-banner">
            {tm_logo_html}
            <div class="banner-text">🎯 Target vs Achievement Dashboard</div>
        </div>
    """, unsafe_allow_html=True)

    # Handle refresh action
    if st.session_state.refresh_trigger:
        st.session_state.refresh_trigger = False
        st.rerun()

    # Main content container
    with st.container():
        st.markdown('<div class="main-content">', unsafe_allow_html=True)

        # Load data
        df = load_data()
        target_df = load_target_data()
        if df.empty or target_df.empty:
            st.error("Required data is missing. Check CSV and Excel files.")
            st.markdown('</div>', unsafe_allow_html=True)
            return

        # Check for TYPE column (case-insensitive)
        type_col = None
        for col in target_df.columns:
            if col.strip().lower() in ['type', 'category']:
                type_col = col
                break
        if type_col is None:
            st.warning(f"Column 'TYPE' not found in Target.csv. Available columns: {', '.join(target_df.columns.tolist())}. Using all rows for BAREA/REGION calculations.")
            target_barea = target_df
            target_region = target_df
            target_file_type = target_df
        else:
            target_barea = target_df[target_df[type_col].str.strip().str.upper() == "BAREA"]
            target_region = target_df[target_df[type_col].str.strip().str.upper() == "REGION"]
            target_file_type = target_df[target_df[type_col].str.strip().str.upper() == "FILE TYPE"]
            if target_region.empty:
                st.warning("No rows with TYPE='REGION' found in Target.csv for region-wise graph.")
            if target_barea.empty:
                st.warning("No rows with TYPE='BAREA' found in Target.csv for month-wise graph and KPI cards.")
            if target_file_type.empty:
                st.warning("No rows with TYPE='FILE TYPE' found in Target.csv for file type graphs.")

        # Check for REGION column for File Type graphs (case-insensitive)
        region_col = None
        for col in target_df.columns:
            if col.strip().lower() in ['region', 'file_type']:
                region_col = col
                break
        if region_col is None and not target_file_type.empty:
            st.warning(f"Column 'REGION' (or similar) not found in Target.csv for TYPE='FILE TYPE'. Available columns: {', '.join(target_df.columns.tolist())}. File Type graphs will show zero targets.")

        # Sidebar filters
        with st.sidebar:
            st.subheader("👤 Profile")
            with st.expander("🔽 Profile Options"):
                st.text(f"User: {st.session_state.username}")
                st.text(f"Role: {st.session_state.access}")
                if st.button("🚪 Logout"):
                    for key in list(st.session_state.keys()):
                        del st.session_state[key]
                    st.rerun()
                change_password()
            st.markdown("---")
            st.button("↻ Refresh Data", on_click=refresh_callback)
            st.title("🔍 Filters")
            region_options = ["All"] + sorted(df["REGION"].dropna().astype(str).unique()) if "REGION" in df.columns else ["All"]
            region = st.selectbox("Region", region_options, key="tva_region")
            travel_qtr_options = ["All"] + sorted(df["Travel Qtr"].dropna().astype(str).unique()) if "Travel Qtr" in df.columns else ["All"]
            quarter = st.selectbox("Travel Quarter", travel_qtr_options, key="tva_quarter")
            final_business_options = ["All"] + sorted(df["Final Buniess"].dropna().astype(str).unique()) if "Final Buniess" in df.columns else ["All"]
            final_business = st.selectbox("Final Buniess", final_business_options, key="tva_final_business")

        # Filter sales data for 2025
        current_year_df = df[df["Travel Y"] == 2025]
        sap_2025 = pd.DataFrame()
        current_base_2025 = pd.DataFrame()
        if not current_year_df.empty:
            sap_2025 = current_year_df[
                (current_year_df["Source"] == "SAP") & 
                (current_year_df["Month Num"] >= 1) & 
                (current_year_df["Month Num"] < current_month)
            ]
            current_base_2025 = current_year_df[
                (current_year_df["Source"] == "Current_Base") & 
                (current_year_df["Month Num"] >= current_month)
            ]
            current_year_df = pd.concat([sap_2025, current_base_2025], ignore_index=True)

        # Apply filters to sales data
        filtered_df = current_year_df.copy()
        if region != "All" and "REGION" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["REGION"].astype(str) == region]
        if quarter != "All" and "Travel Qtr" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["Travel Qtr"].astype(str) == quarter]
        if final_business != "All" and "Final Buniess" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["Final Buniess"].astype(str) == final_business]

        # Calculate total sales for 2025
        sales_current = filtered_df["Sale In Cr"].sum()

        # Calculate total target for BAREA
        total_target = target_barea["Target Amount Cr"].sum() if "Target Amount Cr" in target_barea.columns else 0

        # Calculate targets for LOLH, LOSH, LTDM, AIR
        business_targets = {}
        for business in ["LOLH", "LOSH", "LTDM", "AIR"]:
            target_business = target_barea[
                target_barea["Region"].str.strip().str.upper() == business
            ]
            business_targets[business] = target_business["Target Amount Cr"].sum() if "Target Amount Cr" in target_business.columns else 0

        # KPI Cards with Progress Bars
        with st.container():
            st.markdown('<div class="kpi-container">', unsafe_allow_html=True)
            cols = st.columns([2, 2, 2, 2, 2])
            required_businesses = ["Total Sales", "LOLH", "LOSH", "LTDM", "AIR"]
            icon_map = {
                "Total Sales": "fa-chart-line",
                "LOLH": "fa-globe-asia",
                "LOSH": "fa-globe-europe",
                "LTDM": "fa-globe-africa",
                "AIR": "fa-plane"
            }
            for idx, business in enumerate(required_businesses):
                with cols[idx]:
                    if business == "Total Sales":
                        # Total Sales card
                        ach_pct = (sales_current / total_target * 100) if total_target > 0 else 0
                        card_style = "total-sales"
                        text_style = "color: #000000; font-weight: 600;"
                        header_style = "color: #000000;"
                        st.markdown(f"""
                            <div class="kpi-card {card_style}" style='text-align: center;'>
                                <h3 style='{header_style}'><i class="fas {icon_map[business]}"></i> Total Sales (Cr)</h3>
                                <p style='{text_style}'>2025 (as of {yesterday.strftime('%b %d')}): ₹{sales_current:.2f} Cr</p>
                                <p style='{text_style}'>Target: ₹{total_target:.2f} Cr</p>
                                <p style='{text_style}'>Achievement: {ach_pct:.2f}%</p>
                                <div style='width: 100%; height: 10px; background-color: #d3d3d3; border: 1px solid #000000; border-radius: 5px; margin-top: 5px;'>
                                    <div style='width: {min(ach_pct, 100):.2f}%; height: 100%; background-color: #003087; border-radius: 5px;'></div>
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
                    elif "Final Buniess" in filtered_df.columns and business in filtered_df["Final Buniess"].dropna().astype(str).unique():
                        # Business-specific cards
                        current_sales = filtered_df[filtered_df["Final Buniess"].astype(str) == business]["Sale In Cr"].sum()
                        target = business_targets.get(business, 0)
                        ach_pct = (current_sales / target * 100) if target > 0 else 0
                        card_style = "other"
                        text_style = "font-weight: 600;"
                        st.markdown(f"""
                            <div class="kpi-card {card_style}" style='text-align: center;'>
                                <h3><i class="fas {icon_map[business]}"></i> {business} (Cr)</h3>
                                <p style='{text_style}'>2025 (as of {yesterday.strftime('%b %d')}): ₹{current_sales:.2f} Cr</p>
                                <p style='{text_style}'>Target: ₹{target:.2f} Cr</p>
                                <p style='{text_style}'>Achievement: {ach_pct:.2f}%</p>
                                <div style='width: 100%; height: 10px; background-color: #d3d3d3; border: 1px solid #000000; border-radius: 5px; margin-top: 5px;'>
                                    <div style='width: {min(ach_pct, 100):.2f}%; height: 100%; background-color: #003087; border-radius: 5px;'></div>
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
                    else:
                        # No data for business-specific card
                        card_style = "other"
                        text_style = "color: #ff4b4b; font-weight: 600;"
                        target = business_targets.get(business, 0)
                        ach_pct = 0
                        st.markdown(f"""
                            <div class="kpi-card {card_style}" style='text-align: center;'>
                                <h3><i class="fas {icon_map[business]}"></i> {business} (Cr)</h3>
                                <p style='{text_style}'>2025 Sales: No Data</p>
                                <p style='{text_style}'>Target: ₹{target:.2f} Cr</p>
                                <p style='{text_style}'>Achievement: N/A</p>
                                <div style='width: 100%; height: 10px; background-color: #d3d3d3; border: 1px solid #000000; border-radius: 5px; margin-top: 5px;'>
                                    <div style='width: 0%; height: 100%; background-color: #003087; border-radius: 5px;'></div>
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        # REGION_B-wise Target vs Achievement Bar Graph
        regions = sorted(filtered_df["REGION_B"].str.strip().str.upper().dropna().unique()) if "REGION_B" in filtered_df.columns else []
        sales_by_region = filtered_df.groupby(filtered_df["REGION_B"].str.strip().str.upper())["Sale In Cr"].sum().reindex(regions, fill_value=0) if not filtered_df.empty else pd.Series(index=regions, dtype=float).fillna(0)
        target_by_region = target_region.groupby(target_region["Region"].str.strip().str.upper())["Target Amount Cr"].sum().reindex(regions, fill_value=0) if not target_region.empty and "Target Amount Cr" in target_region.columns else pd.Series(index=regions, dtype=float).fillna(0)
        ach_pct_by_region = [(sales_by_region.get(region, 0) / target_by_region.get(region, 0) * 100) if target_by_region.get(region, 0) > 0 else 0 for region in regions]

        fig_region = go.Figure()
        fig_region.add_trace(go.Bar(
            x=regions,
            y=sales_by_region,
            name="2025 Sales",
            marker_color="#FFC107",
            text=[f"₹{val:.2f} Cr" for val in sales_by_region],
            texttemplate="%{text}",
            textposition="auto",
            textfont=dict(family="Arial, sans-serif", size=12)
        ))
        fig_region.add_trace(go.Bar(
            x=regions,
            y=target_by_region,
            name="Target",
            marker_color="#8B8000",
            text=[f"₹{val:.2f} Cr" for val in target_by_region],
            texttemplate="%{text}",
            textposition="auto",
            textfont=dict(family="Arial, sans-serif", size=12)
        ))
        fig_region.add_trace(go.Scatter(
            x=regions,
            y=ach_pct_by_region,
            name="Achievement %",
            yaxis="y2",
            mode="lines+markers+text",
            line=dict(color="darkgreen", width=2),
            marker=dict(color="darkgreen", size=8),
            text=[f"{pct:.2f}%" if pct != 0 else "" for pct in ach_pct_by_region],
            textposition="top center",
            textfont=dict(family="Arial Black, Arial, sans-serif", size=14, color=["red" if pct < 0 else "darkgreen" for pct in ach_pct_by_region])
        ))
        fig_region.update_layout(
            title=dict(text=f"Region-wise Target vs Achievement (2025, as of {yesterday.strftime('%b %d')})", x=0.5, xanchor="center", y=0.95, font=dict(family="Arial, sans-serif", size=16, color="black")),
            xaxis=dict(title="Region"),
            yaxis=dict(title="Amount (Cr)", side="left", tickformat=".2f", tickprefix="₹"),
            yaxis2=dict(title="Achievement %", overlaying="y", side="right", tickformat=".2f", ticksuffix="%"),
            barmode="group",
            legend=dict(x=0.5, y=-0.1, xanchor="center", yanchor="top", orientation="h"),
            template="plotly_white",
            margin=dict(t=80, b=80, l=60, r=60)
        )

        with st.container():
            st.plotly_chart(fig_region, use_container_width=True)

        # Month-on-Month Target vs Achievement Bar Graph
        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        sales_by_month = filtered_df.groupby("Month Num")["Sale In Cr"].sum().reindex(range(1, 13), fill_value=0) if not filtered_df.empty else pd.Series(index=range(1, 13), dtype=float).fillna(0)
        target_by_month = target_barea.groupby("Month")["Target Amount Cr"].sum().reindex(months, fill_value=0) if not target_barea.empty and "Target Amount Cr" in target_barea.columns else pd.Series(index=months, dtype=float).fillna(0)
        ach_pct_by_month = [(sales_by_month.get(i, 0) / target_by_month.get(m, 0) * 100) if target_by_month.get(m, 0) > 0 else 0 for i, m in enumerate(months, 1)]

        fig_month = go.Figure()
        fig_month.add_trace(go.Bar(
            x=months,
            y=sales_by_month,
            name="2025 Sales",
            marker_color="#FFC107",
            text=[f"₹{val:.2f} Cr" for val in sales_by_month],
            texttemplate="%{text}",
            textposition="auto",
            textfont=dict(family="Arial, sans-serif", size=12)
        ))
        fig_month.add_trace(go.Bar(
            x=months,
            y=target_by_month,
            name="Target",
            marker_color="#8B8000",
            text=[f"₹{val:.2f} Cr" for val in target_by_month],
            texttemplate="%{text}",
            textposition="auto",
            textfont=dict(family="Arial, sans-serif", size=12)
        ))
        fig_month.add_trace(go.Scatter(
            x=months,
            y=ach_pct_by_month,
            name="Achievement %",
            yaxis="y2",
            mode="lines+markers+text",
            line=dict(color="darkgreen", width=2),
            marker=dict(color="darkgreen", size=8),
            text=[f"{pct:.2f}%" if pct != 0 else "" for pct in ach_pct_by_month],
            textposition="top center",
            textfont=dict(family="Arial Black, Arial, sans-serif", size=14, color=["red" if pct < 0 else "darkgreen" for pct in ach_pct_by_month])
        ))
        fig_month.update_layout(
            title=dict(text=f"Month-wise Target vs Achievement (2025, as of {yesterday.strftime('%b %d')})", x=0.5, xanchor="center", y=0.95, font=dict(family="Arial, sans-serif", size=16, color="black")),
            xaxis=dict(title="Month"),
            yaxis=dict(title="Amount (Cr)", side="left", tickformat=".2f", tickprefix="₹"),
            yaxis2=dict(title="Achievement %", overlaying="y", side="right", tickformat=".2f", ticksuffix="%"),
            barmode="group",
            legend=dict(x=0.5, y=-0.1, xanchor="center", yanchor="top", orientation="h"),
            template="plotly_white",
            margin=dict(t=80, b=80, l=60, r=60)
        )

        with st.container():
            st.plotly_chart(fig_month, use_container_width=True)
        # File Type vs Achievement Graphs (LOLH, LOSH, LTDM) - Horizontal Layout
        businesses = ["LOLH", "LOSH", "LTDM"]
        file_types = ["FIT", "GIT"]
        cols = st.columns([1, 1, 1])  # Three equal columns
        for idx, business in enumerate(businesses):
            with cols[idx]:
                # Filter sales data for the business
                business_df = filtered_df[filtered_df["Final Buniess"].str.strip().str.upper() == business] if "Final Buniess" in filtered_df.columns else pd.DataFrame()
                sales_by_file_type = business_df.groupby(business_df["FILE_TYPE"].str.strip().str.upper())["Sale In Cr"].sum().reindex(file_types, fill_value=0) if not business_df.empty else pd.Series(index=file_types, dtype=float).fillna(0)

                # Filter target data for the business
                target_business = target_file_type[target_file_type["ZONE"].str.strip().str.upper() == business]
                if target_business.empty:
                    st.warning(f"No rows with ZONE='{business}' and TYPE='FILE TYPE' found in Target.csv for {business} graph.")
                    target_by_file_type = pd.Series(index=file_types, dtype=float).fillna(0)
                elif region_col is None:
                    target_by_file_type = pd.Series(index=file_types, dtype=float).fillna(0)
                else:
                    target_by_file_type = target_business.groupby(target_business[region_col].str.strip().str.upper())["Target Amount Cr"].sum().reindex(file_types, fill_value=0) if "Target Amount Cr" in target_business.columns else pd.Series(index=file_types, dtype=float).fillna(0)

                # Calculate achievement percentages
                ach_pct_by_file_type = [(sales_by_file_type.get(ft, 0) / target_by_file_type.get(ft, 0) * 100) if target_by_file_type.get(ft, 0) > 0 else 0 for ft in file_types]

                # Create Plotly figure
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=file_types,
                    y=sales_by_file_type,
                    name="2025 Sales",
                    marker_color="#FFC107",
                    text=[f"₹{val:.2f} Cr" for val in sales_by_file_type],
                    texttemplate="%{text}",
                    textposition="auto",
                    textfont=dict(family="Arial, sans-serif", size=12)
                ))
                fig.add_trace(go.Bar(
                    x=file_types,
                    y=target_by_file_type,
                    name="Target",
                    marker_color="#8B8000",
                    text=[f"₹{val:.2f} Cr" for val in target_by_file_type],
                    texttemplate="%{text}",
                    textposition="auto",
                    textfont=dict(family="Arial, sans-serif", size=12)
                ))
                fig.add_trace(go.Scatter(
                    x=file_types,
                    y=ach_pct_by_file_type,
                    name="Achievement %",
                    yaxis="y2",
                    mode="lines+markers+text",
                    line=dict(color="darkgreen", width=2),
                    marker=dict(color="darkgreen", size=8),
                    text=[f"{pct:.2f}%" if pct != 0 else "" for pct in ach_pct_by_file_type],
                    textposition="top center",
                    textfont=dict(family="Arial Black, Arial, sans-serif", size=14, color=["red" if pct < 0 else "darkgreen" for pct in ach_pct_by_file_type])
                ))
                fig.update_layout(
                    title=dict(text=f"{business} Target vs Achievement (2025, as of {yesterday.strftime('%b %d')})", x=0.5, xanchor="center", y=0.95, font=dict(family="Arial, sans-serif", size=16, color="black")),
                    xaxis=dict(title="File Type"),
                    yaxis=dict(title="Amount (Cr)", side="left", tickformat=".2f", tickprefix="₹"),
                    yaxis2=dict(title="Achievement %", overlaying="y", side="right", tickformat=".2f", ticksuffix="%"),
                    barmode="group",
                    legend=dict(x=0.5, y=-0.1, xanchor="center", yanchor="top", orientation="h"),
                    template="plotly_white",
                    margin=dict(t=80, b=80, l=60, r=60),
                    height=400
                )

                st.plotly_chart(fig, use_container_width=True)

        st.markdown('</div>', unsafe_allow_html=True)
#################################################################################################################################################################################
if __name__ == '__main__':
    if st.session_state.logged_in:
        tab_selection = st.radio("", ["Dashboard", "Detailed DRR", "Target Vs Ach"], horizontal=True, label_visibility="collapsed")
        st.session_state.active_tab = tab_selection
        if tab_selection == "Dashboard":
            dashboard_page()
        elif tab_selection == "Detailed DRR":
            drr_summary_page()
        elif tab_selection == "Target Vs Ach":
            target_vs_ach_page()
    else:
        set_background(bg_image)
        try:
            users_df = pd.read_csv(user_file)
        except FileNotFoundError:
            st.error(f"User file not found at {user_file}")
            st.stop()

        try:
            with open(logo_path, "rb") as img_file:
                logo_base64 = base64.b64encode(img_file.read()).decode()
            logo_html = f"<div style='text-align: center;'><img src='data:image/png;base64,{logo_base64}' width='150'></div>"
        except FileNotFoundError:
            logo_html = ""

        st.markdown("""
            <style>
            div.stForm {
                background-color: rgba(0, 0, 0, 0.6);
                padding: 20px;
                border-radius: 10px;
                color: white;
                max-width: 400px;
                margin: auto;
                margin-top: 50px;
            }
            h3 { text-align: center; color: white; }
            label { color: orange !important; font-weight: bold; }
            </style>
        """, unsafe_allow_html=True)

        with st.form("login_form"):
            st.markdown(logo_html, unsafe_allow_html=True)
            st.markdown("### Login")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")

            pw_col = next((col for col in users_df.columns if col.strip().lower() == "password"), None)
            if not pw_col:
                st.error("Password column not found in Emp_base.csv")
                st.stop()

            if submitted:
                user_row = users_df[
                    (users_df["User Name"].str.strip().str.lower() == username.strip().lower()) &
                    (users_df[pw_col].astype(str).str.strip() == password.strip())
                ]
                if not user_row.empty:
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.session_state.access = user_row["Access"].values[0]
                    st.success(f"Welcome, {username}!")
                    st.rerun()
                else:
                    st.error("Invalid Username or Password")
