from pyexpat.errors import messages
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import os
import sqlite3
from datetime import datetime
from flask import send_from_directory


# Initialize the Flask application
app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with a secure random key for production

# Define the current directory for the database path or any other resources
currentdirectory = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(currentdirectory, "pawplannerd.db")

# Function to get a database connection
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # This enables column access by name: row['column_name']
    return conn

# Route to display the registration form and handle registration logic
@app.route('/', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('Name')
        email = request.form.get('Email')
        password = request.form.get('Password')
        role = request.form.get('Role')
        phone_number = request.form.get('Phone_number')
        
        

        try:
            connection = get_db_connection()
            cursor = connection.cursor()

            # Start a transaction
            cursor.execute("BEGIN TRANSACTION")

            # Insert user into the users table
            cursor.execute(
                "INSERT INTO users (Name, Email, Password, Role) VALUES (?, ?, ?, ?)",
                (name, email, password, role)
            )
            user_id = cursor.lastrowid  # Retrieve the user ID of the newly created user

            # Insert into role-specific table
            if role == "Pet Owner":
                cursor.execute(
                    "INSERT INTO pet_owner (User_id, Name, Phone_number, Email) VALUES (?, ?, ?, ?)",
                    (user_id, name, phone_number, email)
                )
            elif role == "Veterinarian":
                cursor.execute(
                    "INSERT INTO vet (User_id, Name, Phone_number, Email) VALUES (?, ?, ?, ?)",
                    (user_id, name, phone_number, email)
                )

            # Commit the transaction if everything is successful
            connection.commit()

            # Flash success message
            flash('Registration successful!', 'success')

        except sqlite3.Error as e:
            # Roll back transaction in case of an error
            connection.rollback()
            flash(f"An error occurred: {e}", 'danger')
        finally:
            # Ensure the connection is closed
            connection.close()

        # Redirect to the registration success page
        return redirect(url_for('Reg_success'))

    # GET request renders the registration form
    return render_template('index.html')

@app.route('/Reg_success')
def Reg_success():
    return render_template('Reg_success.html')



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('Email')  # Get the email from the form
        password = request.form.get('Password')  # Get the password from the form

        # Debugging: print form data
        print(f"Form submitted: email={email}, password={password}")

        if not email or not password:
            flash('Please enter both email and password', 'warning')
            return redirect(url_for('login'))

        try:
            connection = get_db_connection()
            cursor = connection.cursor()

            # Check if email and password match a user in the database
            query = "SELECT * FROM users WHERE Email = ? AND Password = ?"
            cursor.execute(query, (email, password))
            user = cursor.fetchone()

            # Debugging: print the result of the query
            print(f"Query Result: {user}")

            if user:
                # Debugging: print user details
                print(f"Logging in user: {user}")
                session['Email'] = user[2]  # User's email
                session['Name'] = user[1]   # User's name
                session['Role'] = user[4]   # User's role
                session['User_id'] = user[0] # User's ID, assuming it's the first column

                flash(f'Login successful! Welcome {user[1]}!', 'success')

                # Redirect based on role
                if session['Role'] == 'Veterinarian':
                    return redirect(url_for('vet_dashboard'))
                else:  # Default to Pet Owner dashboard
                    return redirect(url_for('dashboard'))

            else:
                flash('Invalid email or password', 'danger')
                return redirect(url_for('login'))

        except sqlite3.Error as e:
            flash(f"An error occurred: {e}", 'danger')
            return redirect(url_for('login'))

        finally:
            if connection:
                connection.close()

    return render_template('login.html')








@app.route('/dashboard')
def dashboard():
    if 'Email' in session:  # Check if the user is logged in
        name = session.get('Name')  # Retrieve the user's name from the session
        return render_template('dashboard.html', name=name)
    else:
        flash('Please log in first', 'warning')
        return redirect(url_for('login'))



@app.route('/logout')
def logout():
    session.pop('Email', None)  # Remove email from session
    session.pop('Name', None)   # Remove name from session
    flash('You have successfully logged out.', 'success')
    return redirect(url_for('login'))  # Redirect back to the login page






@app.route('/petAccount', methods=['GET', 'POST'])
def petAccount():
    if request.method == 'POST':
        # Get data from form
        pName = request.form['Name']
        pet_breed = request.form['Breed']
        pet_age = request.form['Age']
        medical_history = request.form.get('Medical_history', '')  # Optional field

        # Get the current user's ID from the session
        owner_id = session.get('User_id')  # Make sure User_id is correctly set in the session

        if not owner_id:
            flash('User not logged in. Please log in first.', 'danger')
            return redirect(url_for('login'))

        try:
            # Connect to the database
            connection = get_db_connection()
            cursor = connection.cursor()

            # Insert the pet details into the pets table
            cursor.execute(
                "INSERT INTO pets (Owner_id, Name, Breed, Age, Medical_history) VALUES (?, ?, ?, ?, ?)",
                (owner_id, pName, pet_breed, pet_age, medical_history)
            )
            connection.commit()
            flash('Pet added successfully!', 'success')

        except sqlite3.Error as e:
            connection.rollback()
            flash(f"An error occurred: {e}", 'danger')
        finally:
            connection.close()
        
        # Redirect to the page where you want to show a success message or updated data
        return redirect(url_for('show_pets'))

    # Render the petAccount.html form for adding pets
    return render_template('petAccount.html')







@app.route('/show_pets')
def show_pets():
    # Get the current user's ID from the session
    owner_id = session.get('User_id')
    
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.row_factory = sqlite3.Row  # Ensure that rows are returned as dictionaries

    # Fetch all pets for the current user (owner)
    cursor.execute("SELECT Pet_id, Name, Breed, Age, Medical_history FROM pets WHERE Owner_id = ?", (owner_id,))
    pets = cursor.fetchall()

    connection.close()

    return render_template('show_pets.html', pets=pets)







@app.route('/edit_pet/<int:pet_id>', methods=['GET', 'POST'])
def edit_pet(pet_id):
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.row_factory = sqlite3.Row  # Ensure rows are returned as dictionaries

    if request.method == 'POST':
        name = request.form['Name']
        breed = request.form['Breed']
        age = request.form['Age']
        medical_history = request.form.get('Medical_history', '')

        try:
            cursor.execute(
                "UPDATE pets SET Name = ?, Breed = ?, Age = ?, Medical_history = ? WHERE Pet_id = ?",
                (name, breed, age, medical_history, pet_id)
            )
            connection.commit()
            flash('Pet updated successfully!', 'success')
            return redirect(url_for('show_pets'))
        except sqlite3.Error as e:
            connection.rollback()
            flash(f"An error occurred: {e}", 'danger')
        finally:
            connection.close()

    # Fetch the pet details to populate the form
    cursor.execute("SELECT * FROM pets WHERE Pet_id = ?", (pet_id,))
    pet = cursor.fetchone()
    connection.close()

    return render_template('edit_pet.html', pet=pet)



@app.route('/delete_pet/<int:pet_id>')
def delete_pet(pet_id):
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("DELETE FROM pets WHERE Pet_id = ?", (pet_id,))
        connection.commit()
        flash('Pet deleted successfully!', 'success')
    except sqlite3.Error as e:
        connection.rollback()
        flash(f"An error occurred: {e}", 'danger')
    finally:
        connection.close()

    return redirect(url_for('show_pets'))















# Route to handle forgot password functionality
@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('Email')

        # Check if email exists in the database
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM users WHERE Email = ?", (email,))
        user = cursor.fetchone()
        connection.close()

        if user:
            # Here you would typically send a reset email
            flash('Password reset link sent to your email.', 'info')
        else:
            flash('Email not found. Please check and try again.', 'danger')

        return redirect(url_for('forgot_password'))

    return render_template('forgot_password.html')

# Route to handle password reset
@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        email = request.form.get('Email')
        new_password = request.form.get('NewPassword')

        # Update the password in the database
        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            cursor.execute("UPDATE users SET Password = ? WHERE Email = ?", (new_password, email))
            connection.commit()
            flash('Password has been reset successfully!', 'success')
        except sqlite3.Error as e:
            flash(f"An error occurred: {e}", 'danger')
        finally:
            connection.close()

        return redirect(url_for('login'))

    return render_template('reset_password.html')



@app.route('/vet_dashboard', methods=['GET', 'POST'])
def vet_dashboard():
    # Retrieve User ID from session
    user_id = session.get('User_id')


    if 'Email' not in session:
        return redirect(url_for('login'))

    email = session['Email']
    role = session.get('Role')

    # Ensure that only users with the "veterinarian" role can access this dashboard
    if role != 'Veterinarian':
        flash('Access denied: You are not authorized to view this page.', 'danger')
        return redirect(url_for('login'))

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        # Retrieve the veterinarian's details from the vet table using the logged-in email
        cursor.execute("SELECT Name, Phone_number, Email FROM vet WHERE Email = ?", (email,))
        vet_profile = cursor.fetchone()
        connection.close()

        if vet_profile is None:
            flash('Veterinarian profile not found.', 'danger')
            return redirect(url_for('login'))

    except sqlite3.Error as e:
        flash(f"An error occurred: {e}", 'danger')
        return redirect(url_for('login'))

    # Unpack veterinarian details
    vet_name, phone_number, vet_email = vet_profile

    # If the form is submitted, update the veterinarian profile
    if request.method == 'POST':
        name = request.form.get('Name')
        phone_number = request.form.get('Phone_number')

        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            cursor.execute(
                "UPDATE vet SET Name = ?, Phone_number = ? WHERE Email = ?",
                (name, phone_number, email)
            )
            connection.commit()
            flash('Profile updated successfully!', 'success')
        except sqlite3.Error as e:
            flash(f"An error occurred: {e}", 'danger')
        finally:
            connection.close()

        return redirect(url_for('vet_dashboard'))

    return render_template('vet_dashboard.html', name=vet_name, phone_number=phone_number, email=vet_email,  user_id=user_id)



##############################################################################

# Database connection
def get_db_connection():
    conn = sqlite3.connect('pawplannerd.db')
    conn.row_factory = sqlite3.Row
    return conn



# Home route to render the form
@app.route('/')
def index():
    return render_template('appointment.html')

# Route to schedule an appointment
@app.route('/schedule', methods=['POST'])
def schedule_appointment():
    try:
        user_id = session.get('User_id')
        if not user_id:
            return jsonify({'error': 'User is not logged in. Please log in to schedule an appointment.'}), 403

        # Proceed with appointment scheduling
        date = request.form.get('appointmentDate')
        time = request.form.get('appointmentTime')
        vet = request.form.get('vet')
        owner_name = request.form.get('ownerName')
        pet_name = request.form.get('petName')
        pet_age = request.form.get('petAge')
        mobile = request.form.get('mobile')
        email = request.form.get('email')

        # Validate form inputs
        if not (date and time and vet and owner_name and pet_name and pet_age and mobile and email):
            return jsonify({'error': 'All fields are required.'}), 400

        # Save to database
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO appointments 
            (User_id, date, time, vet, owner_name, pet_name, pet_age, mobile, email) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, date, time, vet, owner_name, pet_name, pet_age, mobile, email))
        conn.commit()
        conn.close()

        return jsonify({'message': 'Appointment scheduled successfully!'}), 200

    except Exception as e:
        print(f"Error scheduling appointment: {e}")
        return jsonify({'error': 'An error occurred while scheduling the appointment.'}), 500


    
###########################################################################################################


# Database connection
def get_db_connection():
    conn = sqlite3.connect('pawplannerd.db')
    conn.row_factory = sqlite3.Row
    return conn



# Render calendar with appointments
@app.route('/appointments', methods=['GET'])
def view_appointments():
    conn = get_db_connection()
    appointments = conn.execute('SELECT * FROM appointments').fetchall()
    conn.close()
    return render_template('view_appointments.html', appointments=[dict(row) for row in appointments])

# API to fetch appointments for FullCalendar
@app.route('/api/appointments', methods=['GET'])
def api_appointments():
    conn = get_db_connection()
    appointments = conn.execute('SELECT * FROM appointments').fetchall()
    conn.close()

    events = []
    for appointment in appointments:
        # Convert sqlite3.Row to a dictionary
        appointment_dict = dict(appointment)
        events.append({
            "id": appointment_dict['id'],
            "title": f"Vet: {appointment_dict['vet']}",
            "start": appointment_dict['date'],
            "extendedProps": {
                "time": appointment_dict['time'],
                "token": appointment_dict.get('token', 'N/A'),
            },
        })
    return jsonify(events)


@app.route('/confirm_appointment', methods=['POST'])
def confirm_appointment():
    try:
        data = request.json
        appointment_id = data.get('appointment_id')
        user_phone = data.get('user_phone')

        conn = get_db_connection()

        # Fetch the appointment details, including owner ID
        appointment = conn.execute(
            'SELECT * FROM appointments WHERE id = ?',
            (appointment_id,)
        ).fetchone()

        if not appointment:
            return jsonify({'status': 'error', 'message': 'Appointment not found.'}), 404

        # Extract owner ID (assuming it is stored in the 'owner_id' column of appointments table)
        owner_id = appointment['User_id']

        # Insert into approval table with the owner ID
        conn.execute(
            '''
            INSERT INTO approval (appointment_id, User_id, vet, date, time, status) 
            VALUES (?, ?, ?, ?, ?, ?)
            ''',
            (
                appointment['id'],  # Appointment ID
                owner_id,           # Owner ID
                appointment['vet'], # Vet
                appointment['date'],# Date
                appointment['time'],# Time
                'Confirmed',        # Status
            )
        )

        # Delete the appointment from the `appointments` table
        conn.execute('DELETE FROM appointments WHERE id = ?', (appointment_id,))
        conn.commit()
        conn.close()

        return jsonify({'status': 'success', 'message': 'Appointment confirmed successfully!'}), 200
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/inbox', methods=['GET'])
def inbox():
    # Check if the user is logged in
    if 'User_id' not in session:
        flash('Please log in to view your inbox.', 'warning')
        return redirect('/login')

    # Get the logged-in user's ID from the session
    user_id = session.get('User_id')

    try:
        # Establish database connection
        conn = get_db_connection()

        # Retrieve appointments from `approval` table for the logged-in user
        appointments = conn.execute(
            '''
            SELECT vet, date, time, status
            FROM approval
            WHERE User_id = ?
            ''',
            (user_id,)
        ).fetchall()
        conn.close()

        # Render the inbox page with retrieved appointments
        return render_template(
            'inbox.html', 
            appointments=[dict(row) for row in appointments]
        )

    except Exception as e:
        print(f"Error fetching inbox data: {e}")
        flash('An error occurred while retrieving your appointments.', 'danger')
        return redirect('/')





##############################################################################






@app.route('/pet_accounts')
def pet_accounts():
    if 'Email' not in session:
        return redirect(url_for('login'))

    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM pets")
        pets = cursor.fetchall()
        connection.close()
    except sqlite3.Error as e:
        flash(f"An error occurred: {e}", 'danger')
        return redirect(url_for('vet_dashboard'))

    return render_template('pet_accounts.html', pets=pets)



@app.route('/appointment')
def appointment():
    return render_template('appointment.html')


def get_pets(owner_id):
    try:
        conn = sqlite3.connect('pawplannerd.db', timeout=10)  # Add timeout
        cursor = conn.cursor()
        cursor.execute("SELECT Pet_id, Name FROM pets WHERE Owner_id = ?", (owner_id,))
        pets = cursor.fetchall()
        return [{'Pet_id': pet[0], 'Name': pet[1]} for pet in pets]
    except sqlite3.OperationalError as e:
        print(f"Error fetching pets: {e}")
        return []
    finally:
        conn.close()

@app.route('/medical', methods=['GET', 'POST'])
def medical():
    user_id = session.get('User_id')
    if not user_id:
        return redirect(url_for('login'))  # Redirect to login if user not logged in

    if request.method == 'POST':
        pet_id = request.form['pet_id']
        vaccination_details = request.form['vaccination_details']
        treatment_history = request.form.get('treatment_history', '')
        medication = request.form.get('medication', '')

        # Insert vaccination details into the database
        try:
            conn = sqlite3.connect('pawplannerd.db', timeout=10)  # Add timeout
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO vaccination (Pet_id, Vaccination_details, Treatment_History, Medication)
                VALUES (?, ?, ?, ?)
            ''', (pet_id, vaccination_details, treatment_history, medication))
            conn.commit()
        except sqlite3.OperationalError as e:
            print(f"Error inserting vaccination details: {e}")
        finally:
            conn.close()  # Ensure the connection is always closed

        return redirect(url_for('medical'))

    # Handle GET request to display the form
    pets = get_pets(user_id)
    return render_template('medical.html', pets=pets)

@app.route('/get_vaccination_details/<int:pet_id>', methods=['GET'])
def get_vaccination_details(pet_id):
    try:
        conn = sqlite3.connect('pawplannerd.db', timeout=10)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT Vaccination_details, Treatment_History, Medication
            FROM vaccination
            WHERE Pet_id = ?
        ''', (pet_id,))
        records = cursor.fetchall()
        return jsonify([
            {
                'Vaccination_details': record[0],
                'Treatment_History': record[1],
                'Medication': record[2]
            } for record in records
        ])
    except sqlite3.OperationalError as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


@app.route('/contact')
def contact():
    return render_template('contact.html')




# Directory for uploaded files
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'avi', 'mov', 'pdf', 'txt'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure the upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/chat', methods=['GET'])
def chat():
    user_id = session.get('User_id')
    if not user_id:
        return "Unauthorized", 403
    return render_template('chat.html', user_id=user_id)

@app.route('/get_messages', methods=['GET'])
def get_messages():
    with sqlite3.connect('pawplannerd.db') as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT User_id, Username, MessageText, FilePath, FileType, Timestamp 
            FROM chats 
            ORDER BY Timestamp ASC
        """)
        messages = [
            {
                "userId": row[0], 
                "username": row[1], 
                "messageText": row[2], 
                "filePath": row[3], 
                "fileType": row[4],
                "timestamp": row[5]
            }
            for row in cursor.fetchall()
        ]
    return jsonify({"messages": messages})

@app.route('/send_message', methods=['POST'])
def send_message():
    user_id = session.get('User_id')
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 403

    # Fetch user details
    with sqlite3.connect('pawplannerd.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT Name, Role FROM users WHERE User_id = ?", (user_id,))
        user = cursor.fetchone()

    if not user:
        return jsonify({"error": "User not found"}), 404

    username, role = user
    if role == "Veterinarian":
        username = f"Dr. {username}"

    message_text = request.form.get('messageText', '').strip()
    file = request.files.get('file')

    if not message_text and not file:
        return jsonify({"error": "Message or file is required"}), 400

    file_path, file_type = None, None
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        file_type = file.mimetype

    # Save the message or file in the database
    with sqlite3.connect('pawplannerd.db') as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO chats (User_id, Username, MessageText, FilePath, FileType) 
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, username, message_text, file_path, file_type))
        conn.commit()

    return jsonify({"success": True}), 200

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)