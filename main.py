import psycopg2
import time
import serial
import json
# import yaml
# import utilities

# connection_string = "postgresql://postgres:sa123@localhost:5432/RapidSMS_Db"    # Local System
connection_string = "postgresql://postgres:sa123@192.168.1.227:5433/RapidSMS_Db"    # Docker Image

# Define Modem Port and Baud Rate
MODEM_PORT = "/dev/ttyUSB2"  # Change to COM3, COM4, etc., for Windows
BAUD_RATE = 115200

def connect_db():
    # yamlfile = open("config.yml", "r")
    # # Loads data from config file
    # data = yaml.load(yamlfile, Loader = yaml.FullLoader)
    # # mobile_numbers = data.get('mobile_number', [])
    # connection_string = data['db_connection']['connection_string']

    return psycopg2.connect(connection_string
    )

def fetch_pending_sms():
    """Fetch messages with status 'pending' from the database."""
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("SELECT sms_log_id, mobile_number, message from sms_log WHERE sms_status in (0, 2);")
    messages = cur.fetchall()
    cur.close()
    conn.close()
    return messages

def update_sms_status(sms_log_id, sms_status):
    """Update the status of the message in the database."""
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("UPDATE sms_log SET sms_status = %s WHERE sms_log_id = %s;", (sms_status, sms_log_id))
    conn.commit()
    cur.close()
    conn.close()

def insert_error_log(error_details):
    """Insert error log in to the database."""
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("""
                INSERT INTO error_log (error_details)
                VALUES (%s);
            """, (error_details))
    conn.commit()
    cur.close()
    conn.close()

def send_sms(mobile_number, message):
    """Send SMS using the 4G modem and return success status."""

    try:
        ser = serial.Serial(MODEM_PORT, BAUD_RATE, timeout=5)
        time.sleep(1)

        # Initialize the modem
        ser.write(b'AT\r')
        time.sleep(1)
        # response = ser.read(100)
        # print(response.decode())
        # ser.read(ser.inWaiting()).decode()

        # Set SMS mode to text
        ser.write(b'AT+CMGF=1\r')
        time.sleep(1)
        # ser.read(ser.inWaiting()).decode()

        # Set recipient phone number
        ser.write(f'AT+CMGS="{mobile_number}"\r'.encode())
        time.sleep(1)
        # ser.read(ser.inWaiting()).decode()

        # Send message with Ctrl+Z termination
        ser.write(message.encode() + b"\x1A")
        time.sleep(2)
        response = ser.read(ser.inWaiting()).decode()

        ser.close()
        
        if "OK" in response:
            return True
        else:
            return False

    except Exception as e:
        print("Error sending SMS:", str(e))
        insert_error_log(str(e))
        return False

def process_sms_queue():
    """Check for pending SMS messages and send them every 30 seconds."""
    while True:
        messages = fetch_pending_sms()
        # breakpoint()
        if messages:
            print(f"Found {len(messages)} messages to send.")
            # breakpoint()
            for sms_log_id, mobile_number, message in messages:
                success = send_sms(mobile_number, message)
                # Update message status from 0 to 1 (If SMS SENT) and update 2 If failed
                new_status = 1 if success else 2      
                update_sms_status(sms_log_id, new_status)
                print(f"Message {sms_log_id} sent to {mobile_number} - Status: {new_status}")

        else:
            print("No pending messages. Checking again in 5 seconds...")

        time.sleep(5)  # Wait for 15 seconds before checking again

# # Function to create the users table
# def create_table():
#     conn = connect_db()
#     cur = conn.cursor()
#     cur.execute('''
#         CREATE TABLE IF NOT EXISTS employee (
#             emp_id SERIAL PRIMARY KEY,
#             name VARCHAR(100),
#             department VARCHAR(100),
#             salary INT
#         );
#     ''')
#     conn.commit()
#     cur.close()
#     conn.close()

# # Function to insert a new user
# def insert_Employee(name, department, salary):
#     conn = None
#     cur = None
#     emp_id = None

#     try:
#         # conn = connect_db()
#         conn = psycopg2.connect(connection_string)
#         cur = conn.cursor()
#         cur.execute("""
#             INSERT INTO employee (name, department, salary)
#             VALUES (%s, %s, %s)
#             RETURNING EMP_ID;
#         """, (name, department, salary))
#         emp_id = cur.fetchone()[0]
#         conn.commit()
#         cur.close()
#         # conn.close()
#         return emp_id
#     except Exception as e:

#         print(f"Error connecting to database: {e}")

#     finally:

#         if conn:
#             conn.close()

# # Function to fetch all users
# def fetch_Employee():
#     conn = connect_db()
#     cur = conn.cursor()
#     cur.execute("""SELECT * FROM employee;""")
#     Employee = cur.fetchall()
#     cur.close()
#     conn.close()
#     return Employee



# Example usage
if __name__ == "__main__":
    process_sms_queue()
    # create_table()
    # emp_id = insert_Employee("Ginda", "IT", 2000)
    # print(f"Inserted Emp ID: {emp_id}")
    # Employee = fetch_Employee()
    # print("Employee:", Employee)