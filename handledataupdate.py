import gspread
from oauth2client.service_account import ServiceAccountCredentials
import mysql.connector
from mysql.connector import errorcode

# Define the scope and authenticate using the credentials JSON
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_name('path/to/your/credentials.json', scope)
client = gspread.authorize(credentials)

# Open the Google Sheet by name
sheet = client.open("Control Dashboard 2024").worksheet("ZU")

# Fetch all rows
rows = sheet.get_all_values()

# Connect to the MySQL database
try:
    cnx = mysql.connector.connect(user='your_username', password='your_password',
                                  host='your_host', database='your_database')
    cursor = cnx.cursor(dictionary=True)
except mysql.connector.Error as err:
    if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
        print("Something is wrong with your user name or password")
    elif err.errno == errorcode.ER_BAD_DB_ERROR:
        print("Database does not exist")
    else:
        print(err)

# Fetch existing data from the database
cursor.execute("SELECT * FROM customer")
existing_customers = {row['c_name']: row for row in cursor.fetchall()}

cursor.execute("SELECT * FROM sale")
existing_sales = {row['s_type']: row for row in cursor.fetchall()}

cursor.execute("SELECT * FROM revenue")
existing_revenues = {(row['sale_id'], row['r_year'], row['r_month'], row['r_currency']): row for row in cursor.fetchall()}

# Iterate through the rows and insert/update data in the database
for row in rows[1:]:  # Skip the header row
    c_name = row[0]
    c_country = row[1]
    c_segment = row[2]
    s_type = row[8]
    s_consultant = row[11]

    # Check if the customer exists
    if c_name in existing_customers:
        customer_id = existing_customers[c_name]['id']
        cursor.execute("UPDATE customer SET c_country=%s, c_segment=%s WHERE id=%s",
                       (c_country, c_segment, customer_id))
    else:
        cursor.execute("INSERT INTO customer (c_name, c_country, c_segment) VALUES (%s, %s, %s)",
                       (c_name, c_country, c_segment))
        customer_id = cursor.lastrowid

    # Check if the sale exists
    if s_type in existing_sales:
        sale_id = existing_sales[s_type]['id']
        cursor.execute("UPDATE sale SET s_consultant=%s WHERE id=%s",
                       (s_consultant, sale_id))
    else:
        cursor.execute("INSERT INTO sale (customer_id, s_type, s_consultant) VALUES (%s, %s, %s)",
                       (customer_id, s_type, s_consultant))
        sale_id = cursor.lastrowid

    # Insert/update revenue data
    for i, col in enumerate(['p', 'q', 'r', 'x', 'y', 'z', 'af', 'ag', 'ah', 'an', 'ao', 'ap', 'av', 'aw', 'ax', 'bd', 'be', 'bf', 'bl', 'bm', 'bn', 'bt', 'bu', 'bv', 'cb', 'cc', 'cd', 'cj', 'ck', 'cl', 'cr', 'cs', 'ct', 'cz', 'da', 'db']):
        r_value = row[sheet.find(col).col - 1]
        r_year = '2024'
        r_month = str((i // 3) + 1).zfill(2)
        r_currency = ['CHF', 'EUR', 'GBP'][i % 3]

        key = (sale_id, r_year, r_month, r_currency)
        if key in existing_revenues:
            cursor.execute("UPDATE revenue SET r_value=%s WHERE sale_id=%s AND r_year=%s AND r_month=%s AND r_currency=%s",
                           (r_value, sale_id, r_year, r_month, r_currency))
        else:
            cursor.execute("INSERT INTO revenue (sale_id, r_year, r_month, r_value, r_currency) VALUES (%s, %s, %s, %s, %s)",
                           (sale_id, r_year, r_month, r_value, r_currency))

# Commit the transaction
cnx.commit()

# Close the connection
cursor.close()
cnx.close()
