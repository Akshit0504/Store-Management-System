import streamlit as st
import pandas as pd
import sqlite3
import hashlib

# ---------------------------------------------------------
# DATABASE SETUP & HELPER FUNCTIONS
# ---------------------------------------------------------
DB_FILE = "inventory_system.db"

def get_connection():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def init_db():
    conn = get_connection()
    c = conn.cursor()

    # Table for Users
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    ''')

    # UPDATED: Table for Inventory Items (Matches your 4 new fields)
    c.execute('''
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_name TEXT UNIQUE NOT NULL,
            store_stock INTEGER DEFAULT 0,
            duty_point_stock INTEGER DEFAULT 0,
            total_stock INTEGER DEFAULT 0
        )
    ''')

    # Create default Super Admin if no users exist
    c.execute("SELECT count(*) FROM users")
    if c.fetchone()[0] == 0:
        admin_pass = hash_password("admin123")
        c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", 
                  ("admin", admin_pass, "Super Admin"))

    conn.commit()
    conn.close()

# Initialize DB
init_db()

# ---------------------------------------------------------
# AUTHENTICATION SYSTEM
# ---------------------------------------------------------
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
    st.session_state["username"] = ""
    st.session_state["role"] = ""

def login_user(username, password):
    conn = get_connection()
    c = conn.cursor()
    hashed_p = hash_password(password)
    c.execute("SELECT role FROM users WHERE username = ? AND password = ?", (username, hashed_p))
    result = c.fetchone()
    conn.close()
    if result:
        st.session_state["authenticated"] = True
        st.session_state["username"] = username
        st.session_state["role"] = result[0]
        return True
    return False

def logout_user():
    st.session_state["authenticated"] = False
    st.session_state["username"] = ""
    st.session_state["role"] = ""

# ---------------------------------------------------------
# UI & APP LOGIC
# ---------------------------------------------------------
st.set_page_config(page_title="Inventory System", layout="wide")

if not st.session_state["authenticated"]:
    st.title("🔑 Inventory Management Login")
    
    with st.form("login_form"):
        username_input = st.text_input("Username")
        password_input = st.text_input("Password", type="password")
        submit_button = st.form_submit_button("Login")
        
        if submit_button:
            if login_user(username_input, password_input):
                st.success(f"Welcome, {username_input}!")
                st.rerun()
            else:
                st.error("Invalid Username or Password.")
    st.info("Default Admin Credentials -> Username: **admin** | Password: **admin123**")

else:
    # --- CUSTOM CSS FOR UI LAYOUT & WHITE THEME ---
    st.markdown("""
        <style>
            /* Force overall background to white and text to black */
            .stApp {
                background-color: #FFFFFF !important;
                color: #000000 !important;
            }
            
            /* Target text elements, headers, and labels */
            h1, h2, h3, h4, h5, h6, p, span, label, div {
                color: #000000 !important;
            }

            /* Increased padding-top to prevent text clipping */
            .block-container { padding-top: 3.5rem !important; background-color: #FFFFFF !important; }
            
            /* Sticky header container styling for white theme */
            div[data-testid="stVerticalBlock"] > div:first-of-type {
                position: sticky;
                top: 2.875rem; 
                z-index: 999;
                background-color: #F8F9FA !important; 
                padding-top: 10px; 
                padding-bottom: 10px;
                border-bottom: 1px solid #DDD;
            }

            /* Fix input field backgrounds and text color */
            div[data-baseweb="input"], div[data-baseweb="select"], input {
                background-color: #FFFFFF !important;
                color: #000000 !important;
            }

            .stButton > button {
                padding: 0px 15px !important;
                min-height: 0px !important;
                height: 35px !important;
            }
        </style>
    """, unsafe_allow_html=True)

    # --- TOP STICKY HEADER ---
    header_container = st.container()
    
    with header_container:
        col_title, col_user, col_btn = st.columns([6, 2, 1])
        
        with col_title:
            # Increased font size to 22px and made it bold so it looks like a proper title
            st.markdown("<span style='font-size: 22px; font-weight: bold; color: #a5a5a5;'>Store Management System</span>", unsafe_allow_html=True)
            
        with col_user:
            st.write(f"👤 **Welcome, {st.session_state['username']}** ({st.session_state['role']})")
            
        with col_btn:
            if st.button("Logout"):
                logout_user()
                st.rerun()
        
        menu_options = ["View Inventory", "Update Stock"]
        if st.session_state["role"] == "Super Admin":
            menu_options.extend(["Manage Items (Add/Delete)", "User Administration"])

        choice = st.radio("Navigation Menu", menu_options, horizontal=True, label_visibility="collapsed")
    
    conn = get_connection()
    # 1. VIEW INVENTORY
    if choice == "View Inventory":
        st.header("📊 Current Inventory")
        df = pd.read_sql_query("SELECT item_name AS 'Items Name', store_stock AS 'Store Stock', duty_point_stock AS 'Duty Point Stock', total_stock AS 'Total Stock' FROM inventory", conn)
        st.dataframe(df, use_container_width=True)

    # 2. UPDATE STOCK
    elif choice == "Update Stock":
        st.header("📦 Update Issued Stock")
        items = pd.read_sql_query("SELECT item_name FROM inventory", conn)["item_name"].tolist()
        if not items:
            st.warning("No items available in the database.")
        else:
            selected_item = st.selectbox("Select Item", items)
            issued_qty = st.number_input("Issued Quantity", min_value=0, step=1)
            
            if st.button("Save Issue Record"):
                c = conn.cursor()
                c.execute("UPDATE inventory SET issued_stock = issued_stock + ? WHERE item_name = ?", (issued_qty, selected_item))
                conn.commit()
                st.success(f"Updated issued stock for {selected_item}!")

    # 3. MANAGE ITEMS (Super Admin Only)
    elif choice == "Manage Items (Add/Delete)":
        st.header("🛠️ Inventory Controls (Admin Only)")

        tab1, tab2, tab3 = st.tabs(["Add New Item", "Delete Item", "Bulk Excel Upload"])

        with tab1:
            new_name = st.text_input("Items Name")
            col1, col2, col3 = st.columns(3)
            new_store = col1.number_input("Store Stock", min_value=0, step=1)
            new_duty = col2.number_input("Duty Point Stock", min_value=0, step=1)
            new_total = col3.number_input("Total Stock", min_value=0, step=1)
            
            if st.button("Add Item"):
                if new_name:
                    try:
                        c = conn.cursor()
                        c.execute("INSERT INTO inventory (item_name, store_stock, duty_point_stock, total_stock) VALUES (?, ?, ?, ?)", 
                                  (new_name, new_store, new_duty, new_total))
                        conn.commit()
                        st.success(f"Added '{new_name}' to inventory!")
                    except sqlite3.IntegrityError:
                        st.error("Item already exists!")
                else:
                    st.error("Item name cannot be empty.")

        with tab2:
            items = pd.read_sql_query("SELECT item_name FROM inventory", conn)["item_name"].tolist()
            if items:
                delete_item = st.selectbox("Select Item to Delete", items)
                if st.button("Delete Selected Item", type="primary"):
                    c = conn.cursor()
                    c.execute("DELETE FROM inventory WHERE item_name = ?", (delete_item,))
                    conn.commit()
                    st.warning(f"Deleted '{delete_item}' from database.")
                    st.rerun()

        with tab3:
            st.info("Upload an Excel file with exactly these columns: **Items Name**, **Store Stock**, **Duty Point Stock**, **Total Stock**")
            uploaded_file = st.file_uploader("Upload Excel File", type=["xlsx", "xls"])

            if uploaded_file is not None:
                try:
                    df_upload = pd.read_excel(uploaded_file)
                    st.write("Preview of uploaded data:")
                    st.dataframe(df_upload.head(3))

                    if st.button("Process Bulk Upload"):
                        c = conn.cursor()
                        items_added = 0
                        items_updated = 0

                        for index, row in df_upload.iterrows():
                            # Extract the 4 specific fields
                            item_name = str(row.get("Items Name", "")).strip()
                            
                            try:
                                store_stock = int(row.get("Store Stock", 0))
                            except:
                                store_stock = 0
                                
                            try:
                                duty_point = int(row.get("Duty Point Stock", 0))
                            except:
                                duty_point = 0
                                
                            try:
                                total_stock = int(row.get("Total Stock", 0))
                            except:
                                total_stock = 0

                            if not item_name or item_name.lower() == 'nan':
                                continue

                            # Try to add new, if it exists, update it instead
                            try:
                                c.execute("INSERT INTO inventory (item_name, store_stock, duty_point_stock, total_stock) VALUES (?, ?, ?, ?)", 
                                          (item_name, store_stock, duty_point, total_stock))
                                items_added += 1
                            except sqlite3.IntegrityError:
                                c.execute("UPDATE inventory SET store_stock = ?, duty_point_stock = ?, total_stock = ? WHERE item_name = ?", 
                                          (store_stock, duty_point, total_stock, item_name))
                                items_updated += 1

                        conn.commit()
                        st.success(f"✅ Upload complete! Added {items_added} new items and updated {items_updated} existing items.")

                except Exception as e:
                    st.error(f"Error reading file. Ensure you have the exact column headers. Details: {e}")

    # 4. USER ADMINISTRATION (Super Admin Only)
    elif choice == "User Administration":
        st.header("👥 User & Access Control Management")
        
        tab_users1, tab_users2 = st.tabs(["Create New User", "Existing Users"])
        
        with tab_users1:
            new_user = st.text_input("New Username")
            new_pass = st.text_input("New Password", type="password")
            new_role = st.selectbox("Assign Role", ["User", "Super Admin"])
            
            if st.button("Create Account"):
                if new_user and new_pass:
                    try:
                        c = conn.cursor()
                        c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", 
                                  (new_user, hash_password(new_pass), new_role))
                        conn.commit()
                        st.success(f"User '{new_user}' created successfully with role: {new_role}!")
                    except sqlite3.IntegrityError:
                        st.error("Username already taken.")
                else:
                    st.error("Please fill in all fields.")
                    
        with tab_users2:
            users_df = pd.read_sql_query("SELECT username AS 'Username', role AS 'Role' FROM users", conn)
            st.dataframe(users_df, use_container_width=True)

    conn.close()