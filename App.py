import streamlit as st
import pandas as pd
import sqlite3
import hashlib
import time

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

    # Table for Inventory Items
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
# AUTHENTICATION & 5-MINUTE SESSION TIMEOUT SETUP
# ---------------------------------------------------------
SESSION_TIMEOUT_SECONDS = 300  # 5 Minutes (5 * 60 seconds)

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
    st.session_state["username"] = ""
    st.session_state["role"] = ""
    st.session_state["login_time"] = 0

# Check if session has expired (5 minutes check)
if st.session_state["authenticated"]:
    current_time = time.time()
    if (current_time - st.session_state["login_time"]) > SESSION_TIMEOUT_SECONDS:
        st.session_state["authenticated"] = False
        st.session_state["username"] = ""
        st.session_state["role"] = ""
        st.session_state["login_time"] = 0
        st.warning("Session expired due to 5 minutes of inactivity. Please login again.")
    else:
        # Refresh the timer on every active interaction/rerun
        st.session_state["login_time"] = current_time

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
        st.session_state["login_time"] = time.time()  # Save login timestamp
        return True
    return False

def logout_user():
    st.session_state["authenticated"] = False
    st.session_state["username"] = ""
    st.session_state["role"] = ""
    st.session_state["login_time"] = 0

# ---------------------------------------------------------
# UI & APP LOGIC
# ---------------------------------------------------------
st.set_page_config(page_title="Inventory System", layout="wide")

if not st.session_state["authenticated"]:
    st.title("🔑 Inventory Management Login")
    
    with st.form("login_form"):
        username_input = st.text_input("Username", key="login_username")
        password_input = st.text_input("Password", type="password", key="login_password")
        submit_button = st.form_submit_button("Login")
        
        if submit_button:
            if login_user(username_input, password_input):
                st.success(f"Welcome, {username_input}!")
                st.rerun()
            else:
                st.error("Invalid Username or Password.")

else:
    # --- CUSTOM CSS FOR FULL FORCED LIGHT THEME ---
    st.markdown("""
        <style>
            /* Force overall background to white and text to black everywhere */
            .stApp, .main, [data-testid="stAppViewContainer"], [data-testid="stHeader"], [data-testid="stToolbar"] {
                background-color: #FFFFFF !important;
                color: #000000 !important;
            }
            
            /* Force all text elements, headers, labels, and writing to black */
            h1, h2, h3, h4, h5, h6, p, span, label, div, .stMarkdown, .streamlit-expanderHeader {
                color: #000000 !important;
            }

            /* Container padding */
            .block-container { 
                padding-top: 3.5rem !important; 
                background-color: #FFFFFF !important; 
            }
            
            /* Sticky header styling */
            div[data-testid="stVerticalBlock"] > div:first-of-type {
                position: sticky;
                top: 2.875rem; 
                z-index: 999;
                background-color: #F8F9FA !important; 
                padding-top: 10px; 
                padding-bottom: 10px;
                border-bottom: 1px solid #DDD;
            }

            /* Input boxes, text fields, and select dropdowns */
            input, select, textarea, div[data-baseweb="select"] > div, div[data-baseweb="input"] > div {
                background-color: #FFFFFF !important;
                color: #000000 !important;
                border-color: #CCCCCC !important;
            }

            /* Dropdown lists and text color inside selects */
            div[data-baseweb="popover"] div, div[role="listbox"] div {
                background-color: #FFFFFF !important;
                color: #000000 !important;
            }

            /* Force ALL buttons (including Logout, Submit, Add Item) to have a clean light grey/white background and black text */
            button, .stButton > button, div.stButton > button, [data-testid="baseButton-secondary"], [data-testid="baseButton-primary"] {
                background-color: #F0F2F6 !important;
                color: #000000 !important;
                border: 1px solid #B0B0B0 !important;
            }

            button:hover, .stButton > button:hover {
                background-color: #E0E2E6 !important;
                color: #000000 !important;
            }
        </style>
    """, unsafe_allow_html=True)

    # --- TOP STICKY HEADER ---
    header_container = st.container()
    
    with header_container:
        col_title, col_user, col_btn = st.columns([6, 2, 1])
        
        with col_title:
            st.markdown("<span style='font-size: 22px; font-weight: bold; color: #a5a5a5;'>Store Management System</span>", unsafe_allow_html=True)
            
        with col_user:
            st.write(f"👤 **Welcome, {st.session_state['username']}** ({st.session_state['role']})")
            
        with col_btn:
            if st.button("Logout"):
                logout_user()
                st.rerun()
        
        menu_options = ["View Inventory"]
        if st.session_state["role"] == "Super Admin":
            menu_options.extend(["Manage Items (Add/Delete)", "User Administration"])

        choice = st.radio("Navigation Menu", menu_options, horizontal=True, label_visibility="collapsed")
    
    conn = get_connection()
    
    # 1. VIEW INVENTORY
    if choice == "View Inventory":
        st.header("📊 Current Inventory")
        df = pd.read_sql_query("SELECT item_name AS 'Items Name', store_stock AS 'Store Stock', duty_point_stock AS 'Duty Point Stock', total_stock AS 'Total Stock' FROM inventory", conn)
        st.dataframe(df, use_container_width=True, hide_index=True)

    # 2. MANAGE ITEMS (Super Admin Only)
    elif choice == "Manage Items (Add/Delete)":
        st.header("🛠️ Inventory Controls (Admin Only)")

        tab1, tab2, tab3, tab4 = st.tabs(["Add New Item", "Update Stock", "Delete Item", "Bulk Excel Upload"])

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
            st.subheader("Update Existing Stock")
            items_list = pd.read_sql_query("SELECT item_name FROM inventory", conn)["item_name"].tolist()
            
            if not items_list:
                st.warning("No items available to update.")
            else:
                up_item = st.selectbox("Items Name", items_list, key="update_stock_item")
                up_qty = st.number_input("Qty", step=1, key="update_stock_qty")
                up_target = st.selectbox("Update in", ["Store Stock", "Duty point stock"], key="update_stock_target")
                
                if st.button("Update Stock Count"):
                    c = conn.cursor()
                    if up_target == "Store Stock":
                        c.execute("UPDATE inventory SET store_stock = store_stock + ?, total_stock = total_stock + ? WHERE item_name = ?", 
                                  (up_qty, up_qty, up_item))
                    else:
                        c.execute("UPDATE inventory SET duty_point_stock = duty_point_stock + ?, total_stock = total_stock + ? WHERE item_name = ?", 
                                  (up_qty, up_qty, up_item))
                    conn.commit()
                    st.success("Item has been updated")
                    st.rerun()

        with tab3:
            items = pd.read_sql_query("SELECT item_name FROM inventory", conn)["item_name"].tolist()
            if items:
                delete_item = st.selectbox("Select Item to Delete", items)
                if st.button("Delete Selected Item", type="primary"):
                    c = conn.cursor()
                    c.execute("DELETE FROM inventory WHERE item_name = ?", (delete_item,))
                    conn.commit()
                    st.warning(f"Deleted '{delete_item}' from database.")
                    st.rerun()

        with tab4:
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

    # 3. USER ADMINISTRATION (Super Admin Only)
    elif choice == "User Administration":
        st.header("👥 User & Access Control Management")
        
        tab_users1, tab_users2, tab_users3 = st.tabs(["Create New User", "Existing Users", "Bulk Excel Upload"])
        
        with tab_users1:
            new_user = st.text_input("New Username")
            new_pass = st.text_input("New Password", type="password")
            new_role = st.selectbox("Assign Role", ["User", "Super Admin"])
            
            if st.button("Create Account"):
                if new_user and new_pass:
                    try:
                        c = conn.cursor()
                        c.execute('''
                            CREATE TABLE IF NOT EXISTS users (
                                username TEXT PRIMARY KEY,
                                password TEXT NOT NULL,
                                role TEXT NOT NULL,
                                plain_pass TEXT
                            )
                        ''')
                        hashed_p = hash_password(new_pass)
                        c.execute("INSERT OR REPLACE INTO users (username, password, role, plain_pass) VALUES (?, ?, ?, ?)", 
                                  (new_user, hashed_p, new_role, new_pass))
                        conn.commit()
                        st.success(f"User '{new_user}' created successfully with role: {new_role}!")
                    except Exception as e:
                        st.error(f"Error: {e}")
                else:
                    st.error("Please fill in all fields.")
                    
        with tab_users2:
            st.subheader("Manage Existing Users")
            
            try:
                users_list = pd.read_sql_query("SELECT username, role, plain_pass FROM users", conn)
            except:
                c = conn.cursor()
                try:
                    c.execute("ALTER TABLE users ADD COLUMN plain_pass TEXT")
                    conn.commit()
                except:
                    pass
                users_list = pd.read_sql_query("SELECT username, role, plain_pass FROM users", conn)
            
            if users_list.empty:
                st.info("No users found.")
            else:
                for idx, row in users_list.iterrows():
                    uname = row["username"]
                    urole = row["role"]
                    upass = row["plain_pass"] if pd.notna(row["plain_pass"]) else "N/A (Encrypted)"
                    
                    col_u, col_r, col_p, col_edit, col_del = st.columns([2, 2, 2, 1, 1])
                    
                    with col_u:
                        st.write(f"**{uname}**")
                    with col_r:
                        st.write(f"Role: {urole}")
                    with col_p:
                        st.write(f"Pass: `{upass}`")
                        
                    with col_del:
                        if uname == "admin":
                            st.write("🔒 Protected")
                        else:
                            if st.button("🗑️ Delete", key=f"del_{uname}"):
                                c = conn.cursor()
                                c.execute("DELETE FROM users WHERE username = ?", (uname,))
                                conn.commit()
                                st.warning(f"Deleted user '{uname}'.")
                                st.rerun()
                                
                    with col_edit:
                        with st.popover("✏️ Edit"):
                            st.markdown(f"**Edit User: {uname}**")
                            new_edit_username = st.text_input("Username", value=uname, key=f"euser_{uname}")
                            new_edit_pass = st.text_input("New Password", value=upass if upass != "N/A (Encrypted)" else "", type="default", key=f"epass_{uname}")
                            new_edit_role = st.selectbox("New Role", ["User", "Super Admin"], index=0 if urole == "User" else 1, key=f"erole_{uname}")
                            
                            if st.button("Save Changes", key=f"save_{uname}"):
                                c = conn.cursor()
                                try:
                                    if new_edit_username.strip() == "":
                                        st.error("Username cannot be empty.")
                                    else:
                                        if new_edit_username != uname:
                                            c.execute("SELECT username FROM users WHERE username = ?", (new_edit_username,))
                                            if c.fetchone():
                                                st.error("Username already taken!")
                                            else:
                                                hashed_pass = hash_password(new_edit_pass) if new_edit_pass.strip() != "" else row.get("password", "")
                                                c.execute("INSERT INTO users (username, password, role, plain_pass) VALUES (?, ?, ?, ?)", 
                                                          (new_edit_username, hashed_pass, new_edit_role, new_edit_pass))
                                                c.execute("DELETE FROM users WHERE username = ?", (uname,))
                                                conn.commit()
                                                st.success("User updated successfully!")
                                                st.rerun()
                                        else:
                                            if new_edit_pass.strip() != "":
                                                hashed_new_pass = hash_password(new_edit_pass)
                                                c.execute("UPDATE users SET password = ?, role = ?, plain_pass = ? WHERE username = ?", 
                                                          (hashed_new_pass, new_edit_role, new_edit_pass, uname))
                                            else:
                                                c.execute("UPDATE users SET role = ? WHERE username = ?", (new_edit_role, uname))
                                            conn.commit()
                                            st.success(f"Updated user '{uname}' successfully!")
                                            st.rerun()
                                except Exception as e:
                                    st.error(f"Error: {e}")
                    
                    st.divider()

        with tab_users3:
            st.info("Upload an Excel file with exactly these columns: **Username**, **Pwd**, **Role**")
            user_upload_file = st.file_uploader("Upload Users Excel File", type=["xlsx", "xls"], key="user_excel_uploader")

            if user_upload_file is not None:
                try:
                    df_users_upload = pd.read_excel(user_upload_file)
                    st.write("Preview of uploaded users data:")
                    st.dataframe(df_users_upload.head(3))

                    if st.button("Process Users Bulk Upload"):
                        c = conn.cursor()
                        c.execute('''
                            CREATE TABLE IF NOT EXISTS users (
                                username TEXT PRIMARY KEY,
                                password TEXT NOT NULL,
                                role TEXT NOT NULL,
                                plain_pass TEXT
                            )
                        ''')
                        
                        users_added = 0
                        users_updated = 0

                        for index, row in df_users_upload.iterrows():
                            u_name = str(row.get("Username", "")).strip()
                            u_pwd = str(row.get("Pwd", "")).strip()
                            u_role = str(row.get("Role", "User")).strip()

                            if not u_name or u_name.lower() == 'nan' or not u_pwd or u_pwd.lower() == 'nan':
                                continue

                            if "admin" in u_role.lower():
                                u_role = "Super Admin"
                            else:
                                u_role = "User"

                            hashed_upwd = hash_password(u_pwd)

                            try:
                                c.execute("INSERT INTO users (username, password, role, plain_pass) VALUES (?, ?, ?, ?)", 
                                          (u_name, hashed_upwd, u_role, u_pwd))
                                users_added += 1
                            except sqlite3.IntegrityError:
                                c.execute("UPDATE users SET password = ?, role = ?, plain_pass = ? WHERE username = ?", 
                                          (hashed_upwd, u_role, u_pwd, u_name))
                                users_updated += 1

                        conn.commit()
                        st.success(f"✅ Bulk upload complete! Added {users_added} new users and updated {users_updated} existing users.")

                except Exception as e:
                    st.error(f"Error reading users file. Ensure headers are Username, Pwd, Role. Details: {e}")

    conn.close()