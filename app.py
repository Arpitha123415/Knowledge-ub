import streamlit as st
import sqlite3
import hashlib
from datetime import datetime
import pandas as pd

# Initialize session state
if "user" not in st.session_state:
    st.session_state.user = None
if "page" not in st.session_state:
    st.session_state.page = "home"  # Default page

# Function to hash passwords
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()
 
# Get database connection
def get_db_connection():
    return sqlite3.connect("library.db", check_same_thread=False)

# Create tables
def create_tables():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(''' 
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT,
            email TEXT UNIQUE,
            is_admin INTEGER,
            registration_date TIMESTAMP
        )
    ''')
    c.execute(''' 
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            author TEXT,
            year INTEGER,
            pdf_link TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS borrowed_books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            book_id INTEGER,
            borrow_date TIMESTAMP,
            return_date TIMESTAMP NULL,
            FOREIGN KEY (username) REFERENCES users(username),
            FOREIGN KEY (book_id) REFERENCES books(id)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS requested_books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            book_title TEXT,
            request_date TIMESTAMP,
            FOREIGN KEY (username) REFERENCES users(username)
        )
    ''')
    
    conn.commit()
    conn.close()


# Check if username exists
def user_exists(username):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT username FROM users WHERE username = ?", (username,))
    exists = c.fetchone()
    conn.close()
    return exists is not None

# Add a new user
def add_user(username, password, email, is_admin=False):
    if user_exists(username):
        st.error("Username already exists! Please choose another.")
        return
    hashed_pw = hash_password(password)
    registration_date = datetime.now()
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute(''' 
            INSERT INTO users (username, password, email, is_admin, registration_date)
            VALUES (?, ?, ?, ?, ?)
        ''', (username, hashed_pw, email, int(is_admin), registration_date))
        conn.commit()
        st.success(f"{'Admin' if is_admin else 'User'} registered successfully!")
    except sqlite3.IntegrityError:
        st.error("Email already registered. Use a different email.")
    finally:
        conn.close()

# Validate user login
def validate_user(username, password):
    hashed_pw = hash_password(password)
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, hashed_pw))
    user = c.fetchone()
    conn.close()
    return user

# Add a book
def add_book(title, author, year, pdf_link):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("INSERT INTO books (title, author, year, pdf_link) VALUES (?, ?, ?, ?)", 
              (title, author, year, pdf_link))
    conn.commit()
    conn.close()
    st.success("Book added successfully!")

# Get all books including the PDF link
def get_all_books():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT title, author, year, pdf_link FROM books")  
    books = c.fetchall()
    conn.close()
    
    df = pd.DataFrame(books, columns=["Title", "Author", "Year", "PDF Link"])
    df.index = range(1, len(df) + 1)  # Index starts from 1
    df.index.name = "S.No"

    return df

# Fetch all users (Admin only)
def get_all_users():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT username, email, is_admin, registration_date FROM users")
    users = c.fetchall()
    conn.close()
    
    # Convert to DataFrame and add an ID column starting from 1
    df = pd.DataFrame(users, columns=["Username", "Email", "Admin Status", "Registration Date"])
    df.index = range(1, len(df) + 1)  # Set index starting from 1
    df.index.name = "S.No"  # Rename index to "S.No"
    
    return df

# Borrow a book
def borrow_book(username, book_id):
    conn = get_db_connection()
    c = conn.cursor()
    
    # Check if the book is already borrowed
    c.execute("SELECT * FROM borrowed_books WHERE book_id = ? AND return_date IS NULL", (book_id,))
    if c.fetchone():
        st.error("This book is already borrowed by someone else.")
        conn.close()
        return
    
    # Borrow the book
    borrow_date = datetime.now()
    c.execute("INSERT INTO borrowed_books (username, book_id, borrow_date) VALUES (?, ?, ?)", 
              (username, book_id, borrow_date))
    conn.commit()
    conn.close()
    st.success("Book borrowed successfully!")

# Get books borrowed by the user
def get_borrowed_books(username):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""SELECT books.id, books.title, books.author, books.year 
                 FROM borrowed_books 
                 JOIN books ON borrowed_books.book_id = books.id 
                 WHERE borrowed_books.username = ? AND borrowed_books.return_date IS NULL""", 
              (username,))
    books = c.fetchall()
    conn.close()
    return books

# Return a book
def return_book(username, book_id):
    conn = get_db_connection()
    c = conn.cursor()
    return_date = datetime.now()
    c.execute("UPDATE borrowed_books SET return_date = ? WHERE username = ? AND book_id = ? AND return_date IS NULL",
              (return_date, username, book_id))
    conn.commit()
    conn.close()
    st.success("Book returned successfully!")

# Search books
def search_books(query=""):
    conn = sqlite3.connect("library.db")
    cursor = conn.cursor()

    # ✅ Ensure PDF link is selected
    cursor.execute("SELECT id, title, author, year, pdf_link FROM books WHERE title LIKE ?", ('%' + query + '%',))
    
    books = cursor.fetchall()
    conn.close()
    return books

# Request a book
def request_book(username, book_title):
    conn = get_db_connection()
    c = conn.cursor()
    try:
        request_date = datetime.now()
        c.execute("INSERT INTO requested_books (username, book_title, request_date) VALUES (?, ?, ?)",
                  (username, book_title, request_date))
        conn.commit()
        st.success("Book request submitted successfully!")
    except Exception as e:
        st.error(f"Error: {e}")
    finally:
        conn.close()

def generate_view_button(link):
    """Generate a clickable 'View' button for a given PDF link."""
    if isinstance(link, str) and link.strip():
        return f'<a href="{link}" target="_blank"><button>View</button></a>'
    return "N/A"
  
def remove_book_by_title(title):
    conn = get_db_connection()
    c = conn.cursor()
   
    # Check if the book exists
    c.execute("SELECT * FROM books WHERE title = ?", (title,))
    books = c.fetchall()
    
    if not books:
        st.warning(f"No book found with the title: {title}")
    elif len(books) > 1:
        st.warning(f"Multiple books found with the title: {title}. Please specify further.")
    else:
        # Delete the book
        c.execute("DELETE FROM books WHERE title = ?", (title,))
        conn.commit()
        st.success(f"Book '{title}' removed successfully!")
    conn.close()
    
def update_book_details(old_title, new_title, new_author, new_year, new_pdf_link):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""
        UPDATE books SET title = ?, author = ?, year = ?, pdf_link = ?
        WHERE title = ?
    """, (new_title, new_author, new_year, new_pdf_link, old_title))
    conn.commit()
    conn.close()

    # ✅ Store success message in session state
    st.session_state["update_success"] = f"✅ '{old_title}' has been updated successfully!"
    st.session_state["edit_mode"] = False  # Close edit form after update

def remove_user_by_username(username):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE username = ?", (username,))
    conn.commit()
    conn.close()
    st.session_state["user_remove_success"] = f"❌ User '{username}' removed successfully!"
    st.rerun()

# Update User Details
def update_user_details(old_username, new_username, new_email, new_is_admin):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""
        UPDATE users SET username = ?, email = ?, is_admin = ? WHERE username = ?
    """, (new_username, new_email, int(new_is_admin), old_username))
    conn.commit()
    conn.close()
    st.session_state["update_success"] = f"✅ '{old_username}' updated successfully!"
    st.session_state["edit_user_mode"] = False
    st.rerun()

# Fetch requested books
def get_requested_books():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT id, username, book_title, request_date FROM requested_books")
    books = c.fetchall()
    conn.close()
    return books

# Function to approve book request
def approve_request(request_id, username, book_title):
    conn = get_db_connection()
    c = conn.cursor()
    
    # Get book details (assuming title is unique; otherwise, modify query)
    c.execute("SELECT id FROM books WHERE title = ?", (book_title,))
    book = c.fetchone()
    
    if book:
        book_id = book[0]
        borrow_date = datetime.now().strftime('%Y-%m-%d')

        # Insert into borrowed_books table
        c.execute("INSERT INTO borrowed_books (username, book_id, borrow_date) VALUES (?, ?, ?)", 
                  (username, book_id, borrow_date))

        # Remove request after approval
        c.execute("DELETE FROM requested_books WHERE id = ?", (request_id,))
        conn.commit()
        st.success(f"✅ Approved: '{book_title}' has been borrowed by {username}.")
    else:
        st.error("❌ Book not found in the system.")
    
    conn.close()
    
# Function to deny request
def deny_request(request_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM requested_books WHERE id = ?", (request_id,))
    conn.commit()
    conn.close()
    st.warning("❌ Request denied and removed from the list.")
# Initialize database tables
create_tables()

# Function to render home page
def render_home():
    
    st.title("📚 Welcome to KnowledgeHub")
    st.markdown("### Centralized Knowledge Management System")
    st.markdown(" 🏆 **Efficiently manage books and users**")
    st.markdown(" 🔍 **Search & Filter books easily**")
    st.markdown(" 📖 **Borrow & Return books hassle-free**")
    st.markdown(" 📜 **View your borrowing history**")
    st.markdown(" 🔑 **Secure login for users and admins**")

# Function to render book search
def render_search():
    st.title("🔍 Search Books")
    query = st.text_input("Enter book title or author:")
    if query:
        results = search_books(query)
        if results:
            for book in results:
                st.write(f"{book[1]} by {book[2]} ({book[3]})")
        else:
            st.write("No matching books found.")

# Function to render book request page
def render_request_book():
    st.title("📌 Request a Book")
    book_title = st.text_input("Enter the book title you want to request:")
    if st.button("Submit Request"):
        request_book(st.session_state.user[0], book_title)
        
# Function to get available books (not borrowed by anyone)
def get_available_books():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""
        SELECT id, title, author, year FROM books 
        WHERE id NOT IN (SELECT book_id FROM borrowed_books WHERE return_date IS NULL)
    """)
    books = c.fetchall()
    conn.close()
    return books

# Function to render registration page
def render_register():
    st.title("🔑 Register an Account")
    user_type = st.selectbox("Register as:", ["User", "Admin"])
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    confirm_password = st.text_input("Confirm Password", type="password")
    email = st.text_input("Email")
    register_button = st.button("✅ Register")

    if register_button:
        if username and password and email and confirm_password:
            if password != confirm_password:
                st.error("❌ Passwords do not match!")
            else:
                add_user(username, password, email, user_type == "Admin")
        else:
            st.error("⚠️ Please fill out all fields!")

# Function to render login page
def render_login():
    
    st.title("🔓 Login to KnowledgeHub")
    user_type = st.selectbox("Login as:", ["User", "Admin"])
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    login_button = st.button("🔑 Login")

    if login_button:
        user = validate_user(username, password)
        if user:
            is_admin = user[3] == 1
            if (user_type == "Admin" and is_admin) or (user_type == "User" and not is_admin):
                st.session_state.user = user
                st.session_state.page = "admin" if is_admin else "user"
                st.rerun()
            else:
                st.error("❌ Invalid credentials for the selected role.")
        else:
            st.error("❌ Invalid username or password.")

# Function to style the app
st.markdown(
    """
    <style>
        /* Sidebar Styling */
        [data-testid="stSidebar"] {
            background-color: white !important; /* Sidebar */
            color: black !important;
            padding-top: 0px;
            padding-left: 0px;
            padding-bottom: 0px;
            padding-right: 10px;
            border-right: 0px solid #1E1E1E; /* Adds a separator */
        }

        /* Sidebar Text */
        [data-testid="stSidebar"] * {
            color: black !important; /* Ensures text remains readable */
        }

        /* Main Content Background */
        .stApp {
            background-color: #F5F5F5 !important; /* Light gray background */
        }

        /* Titles & Headers */
        h1 {
            font-size: 36px !important; /* Adjusted title size */
            color: #1E1E1E !important; /* Dark text */
        }
        h2 {
            font-size: 34px !important;
            color: #1E1E1E !important;
        }
        h3 {
            font-size: 26px !important;
            color: #1E1E1E !important;
        }
        h4, h5, h6, p {
            font-size: 18px !important; /* Standard readable text */
            color: #1E1E1E !important;
        }

        /* Buttons */
        .stButton>button {
            background-color: #34A56F !important;  /* Green button */
            color: white !important;
            border-radius: 10px;
            font-size: 18px !important;
        }

        /* Customizable Text Styling */
        .custom-text {
            font-size: 20px !important; /* Default size */
            color: #FF5733 !important; /* Example: Orange text */
        }
    </style>
    """,
    unsafe_allow_html=True
)
    
# ---------------------- ADMIN PANEL ----------------------
if st.session_state.page == "admin":
    st.title("⚙️ Admin Panel")

    # Create top horizontal menu
    tab1, tab2, tab3 = st.tabs(["👥 Manage Users", "📚 Manage Books", "Manage Request"])

    # Manage Users Tab
    with tab1:
        st.subheader("➕ Add User")
        new_username = st.text_input("New Username")
        new_password = st.text_input("New Password", type="password")
        confirm_new_password = st.text_input("Confirm Password", type="password")
        new_email = st.text_input("Email")
        new_user_admin = st.checkbox("Admin Privileges")

        if st.button("Add User"):
            if new_password == confirm_new_password:
                add_user(new_username, new_password, new_email, new_user_admin)
            else:
                st.error("⚠️ Passwords do not match!")

        # Display Registered Users
        st.subheader("👥 Registered Users")
        users_df = get_all_users()
        if not users_df.empty:
            st.write(users_df)
        else:
            st.warning("No users available.")

        # ❌ Remove User Section
        st.subheader("❌ Remove a User")
        if not users_df.empty:
            user_names = users_df["Username"].tolist()
            user_to_remove = st.selectbox("Select a user to remove:", user_names)

            if st.button("Remove User"):
                remove_user_by_username(user_to_remove)
        else:
            st.warning("No users available to remove.")

        if "user_remove_success" in st.session_state:
            st.success(st.session_state["user_remove_success"])
            del st.session_state["user_remove_success"]

        # ✏️ Edit User Section        
        st.subheader("✏️ Edit a User")
        if not users_df.empty:
            user_names = users_df["Username"].tolist()
            user_to_edit = st.selectbox("Select a user to edit:", user_names, key="select_edit_user")

            if st.button("Edit User"):
                st.session_state["edit_user_mode"] = True
                st.session_state["selected_user"] = user_to_edit

        # Show edit form **only if "Edit User" was clicked**
        if st.session_state.get("edit_user_mode", False) and "selected_user" in st.session_state:
            user_details = users_df[users_df["Username"] == st.session_state["selected_user"]].iloc[0]
            existing_username = user_details["Username"]
            existing_email = user_details["Email"]
            existing_is_admin = bool(user_details["Admin Status"])

            new_username = st.text_input("Username", value=existing_username, key="edit_user_username")
            new_email = st.text_input("Email", value=existing_email, key="edit_user_email")
            new_is_admin = st.checkbox("Admin Privileges", value=existing_is_admin, key="edit_user_admin")

            if st.button("Update User", key="update_user_button"):
                update_user_details(existing_username, new_username, new_email, new_is_admin)

        # ✅ Show success messages **after rerun**
        if "update_success" in st.session_state:
            st.success(st.session_state["update_success"])
            del st.session_state["update_success"]
   
    # Manage Books Tab
    with tab2:
        # ✅ Add Book Section
        st.subheader("➕ Add New Book")

        title = st.text_input("Title")
        author = st.text_input("Author")
        year = st.number_input("Year", min_value=1000, max_value=9999, step=1)
        pdf_link = st.text_input("PDF Link (optional)")  # Capture the link

        if st.button("Add Book"):
            if title and author and year:
                add_book(title, author, year, pdf_link)  # Ensure the link is stored
                st.success(f"✅ Book '{title}' added successfully!")
            else:
                st.error("⚠️ Please fill in all required fields.")

        # Display books with a clickable "View Book" link
        
        st.subheader("📚 Library Books")

        library_books_df = get_all_books()

        if not library_books_df.empty:
            library_books_df["View Book"] = library_books_df["PDF Link"].apply(generate_view_button)
            library_books_df = library_books_df.drop(columns=["PDF Link"])  # Hide raw PDF link column
            st.markdown(library_books_df.to_html(escape=False, index=False), unsafe_allow_html=True)
        else:
            st.warning("No books available in the library.")

        # Remove Book Section
        st.subheader("❌ Remove a Book")
        book_titles = library_books_df["Title"].tolist()  # Extract book titles
        book_title_to_remove = st.selectbox("Select a book to remove:", book_titles)
        
        if st.button("Remove Book"):
            remove_book_by_title(book_title_to_remove)
            st.success(f"'{book_title_to_remove}' has been removed successfully!")
                    
                # Edit Book Section        
        st.subheader("✏️ Edit a Book")

        if not library_books_df.empty:
            book_titles = library_books_df["Title"].tolist()
            
            # Step 1: Select a book
            book_title_to_edit = st.selectbox("Select a book to edit:", book_titles, key="select_edit_book")

            if st.button("Edit"):
                st.session_state["edit_mode"] = True
                st.session_state["selected_book"] = book_title_to_edit

        # Step 2: Show the edit form **only if "Edit" was clicked**
        if st.session_state.get("edit_mode", False):
            book_details = library_books_df[library_books_df["Title"] == st.session_state["selected_book"]].iloc[0]

            existing_title = book_details["Title"]
            existing_author = book_details["Author"]
            existing_year = int(book_details["Year"])
            existing_pdf_link = book_details.get("PDF Link", "")

            # Editable fields with unique keys
            new_title = st.text_input("Title", value=existing_title, key="edit_title")
            new_author = st.text_input("Author", value=existing_author, key="edit_author")
            new_year = st.number_input("Year", min_value=1000, max_value=9999, step=1, value=existing_year, key="edit_year")
            new_pdf_link = st.text_input("PDF Link (optional)", value=existing_pdf_link, key="edit_pdf")

            # Step 3: Click "Update" to save changes
            if st.button("Update", key="update_button"):
                update_book_details(st.session_state["selected_book"], new_title, new_author, new_year, new_pdf_link)
                st.rerun()  # Refresh UI after update

        # ✅ Show success message **after rerun**
        if "update_success" in st.session_state:
            st.success(st.session_state["update_success"])
            del st.session_state["update_success"]  # Remove message after showing
    
    
    with tab3:
        # Requested Books Section
        st.subheader("📌 Book Requests")
        requested_books = get_requested_books()

        if requested_books:
            for request in requested_books:
                req_id, username, book_title, req_date = request
                st.write(f"📖 **{book_title}** requested by **{username}** on {req_date}")

                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Approve", key=f"approve_{req_id}"):
                        approve_request(req_id, username, book_title)

                with col2:
                    if st.button("Deny", key=f"deny_{req_id}"):
                        deny_request(req_id)
        else:
            st.info("No pending book requests.")

            
# ---------------------Sidebar Navigation---------------------
st.sidebar.title("📌 Navigation")
if st.session_state.page in ["admin", "user"]:
    st.sidebar.write(f"🔹 Logged in as: **{st.session_state.user[0]}**")
    if st.sidebar.button("🚪 Logout"):
        st.session_state.page = "home"
        st.session_state.user = None
        st.rerun()
else:
    page_selection = st.sidebar.radio("🏠 Choose an option:", ["Home", "Register", "Login"])
    if page_selection == "Home":
        render_home()
    
    elif page_selection == "Register":
        render_register()
    elif page_selection == "Login":
        render_login()

# ---------------------- USER DASHBOARD ----------------------
if st.session_state.page == "user":
    st.title("📖 User Dashboard")
    
    username = st.session_state.user[0]
    is_admin = st.session_state.user[3] == 1
    role = "Admin" if is_admin else "User"
    
    st.write(f"Welcome, **{username}**! You are logged in as a **{role}**.")
    
    # Search Books Section
    st.subheader("🔍 Search Books")
    search_query = st.text_input("Enter book title or author:")
    if search_query:
        results = search_books(search_query)
        if results:
            for book in results:
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"{book[1]} by {book[2]} ({book[3]})")
                with col2:
                    if st.button(f"Borrow {book[1]}", key=f"borrow_{book[0]}"):
                        borrow_book(username, book[0])
        else:
            st.write("No matching books found.")
    
    # Request Book Section
    st.subheader("📌 Request a Book")
    book_title_request = st.text_input("Enter the book title you want to request:")
    if st.button("Submit Request"):
        request_book(username, book_title_request)

    # 📚 Available Books Section
    st.subheader("📚 Available Books")

    books = search_books()

    if books:
        book_data = [(i+1, book[1], book[2], book[3], book[4]) for i, book in enumerate(books)]
        books_df = pd.DataFrame(book_data, columns=["S.No", "Title", "Author", "Year", "PDF Link"])

        books_df["View Book"] = books_df["PDF Link"].apply(generate_view_button)
        books_df = books_df.drop(columns=["PDF Link"])  # Hide raw PDF link column

        st.markdown(books_df.to_html(escape=False, index=False), unsafe_allow_html=True)
    else:
        st.warning("No books found.")
                
    st.subheader("📚 Borrow a Book")
    available_books = get_available_books()
    if available_books:
        book_options = {f"{book[1]} by {book[2]} ({book[3]})": book[0] for book in available_books}
        selected_book = st.selectbox("Select a book to borrow:", list(book_options.keys()))
        if st.button("Borrow Book"):
            borrow_book(username, book_options[selected_book])
    else:
        st.warning("No books available for borrowing at the moment.")

    # 📖 Borrowed Books Section
    st.subheader("📖 Your Borrowed Books")
    borrowed_books = get_borrowed_books(username)
    if borrowed_books:
        borrowed_books_df = pd.DataFrame(
            [(i+1, book[1], book[2], book[3]) for i, book in enumerate(borrowed_books)],
            columns=["S.No", "Title", "Author", "Year"]
        )
        st.markdown(borrowed_books_df.to_html(escape=False, index=False), unsafe_allow_html=True)
    else:
        st.warning("You haven't borrowed any books yet.")
    
    # ✅ Return Book Section
    st.subheader("🔄 Return a Book")
    borrowed_books = get_borrowed_books(username)
    if borrowed_books:
        borrowed_book_options = {f"{book[1]} by {book[2]} ({book[3]})": book[0] for book in borrowed_books}
        selected_borrowed_book = st.selectbox("Select a book to return:", list(borrowed_book_options.keys()))
        if st.button("Return Book"):
            return_book(username, borrowed_book_options[selected_borrowed_book])
    else:
        st.write("You have no borrowed books.")

def set_background(image_path):
    """
    Sets a background image for the main page and the sidebar in Streamlit.
    :param image_path: Path to the image file (must be stored locally).
    """
    # Convert image to base64
    import base64
    def get_base64(file):
        with open(file, "rb") as f:
            return base64.b64encode(f.read()).decode()

    base64_image = get_base64(image_path)

    # Apply CSS for background
    st.markdown(
        f"""
        <style>
        .stApp {{
            background: url("data:image/png;base64,{base64_image}") no-repeat center center fixed;
            background-size: cover;
        }}
        [data-testid="stSidebar"] > div:first-child {{
            background: url("data:image/png;base64,{base64_image}") no-repeat center center fixed !important;
            background-size: cover !important;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

set_background("image.png")  # Ensure this image exists in your project directory

st.markdown(
    """
    <style>
        /* Hide Streamlit's default header */
        header {visibility: hidden;}

        /* Change the navigation separation line to white */
        [data-testid="stSidebarNav"]::before {
            content: "";
            display: block;
            height: 2px;
            background-color: white;
            margin-bottom: 10px;
        }
    </style>
    """,
    unsafe_allow_html=True
)
TABLE_STYLE = """
<style>
    table {
        width: 100%;
        border-collapse: collapse;
        background-color: #F5F5F5;
        border-radius: 10px;
        overflow: hidden;
        box-shadow: 2px 2px 10px rgba(0, 0, 0, 0.1);
    }
    th, td {
        padding: 10px;
        text-align: center;
        border-bottom: 1px solid #ddd;
    }
    th {
        background-color: #a9a9a9;
        color: white;
        padding: 12px;
        text-align: center; /* Center-align headers */
        
    }
    tr:hover {
        background-color: #F5F5F5;
    }
    button {
        background-color: #a9a9a9;
        color: black;
        padding: 5px 10px;
        border: none;
        border-radius: 5px;
        cursor: pointer;
    }
    button:hover {
        background-color: #0056b3;
    }
</style>
"""
st.markdown(TABLE_STYLE, unsafe_allow_html=True)
