import psycopg2
import csv
from tabulate import tabulate

def get_connection():
    return psycopg2.connect(
        dbname="mydb",
        user="postgres",
        password="240407",
        host="localhost",
        port="5432"
    )

def create_table():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DROP TABLE IF EXISTS phonebook;")
            cur.execute("""
                CREATE TABLE phonebook (
                    id SERIAL PRIMARY KEY,
                    first_name VARCHAR(50) NOT NULL,
                    last_name VARCHAR(50),
                    phone VARCHAR(20) NOT NULL UNIQUE
                );
            """)
            conn.commit()
            print("PhoneBook table created successfully")

def insert_from_csv(path):
    with get_connection() as conn:
        with conn.cursor() as cur:
            with open(path, mode='r', encoding='utf-8') as file:
                reader = csv.reader(file)
                next(reader)  # Skip header
                for row in reader:
                    try:
                        cur.execute("""
                            INSERT INTO phonebook (first_name, last_name, phone)
                            VALUES (%s, %s, %s)
                        """, (row[0].strip(), row[1].strip(), row[2].strip()))
                    except psycopg2.IntegrityError:
                        conn.rollback()
                        print(f"Duplicate phone skipped: {row[2]}")
                        continue
            conn.commit()
            print("CSV data imported successfully")

def insert_from_console():
    print("\nEnter contact details:")
    first_name = input("First name: ").strip()
    last_name = input("Last name (optional): ").strip()
    phone = input("Phone number: ").strip()
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute("""
                    INSERT INTO phonebook (first_name, last_name, phone)
                    VALUES (%s, %s, %s)
                """, (first_name, last_name if last_name else None, phone))
                conn.commit()
                print("Contact added successfully")
            except psycopg2.IntegrityError:
                print("Error: Phone number already exists")

def update_contact():
    print("\nUpdate contact:")
    phone = input("Enter phone number of contact to update: ").strip()
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM phonebook WHERE phone = %s", (phone,))
            if not cur.fetchone():
                print("Contact not found")
                return
            
            print("\nWhat to update?")
            print("1. First name")
            print("2. Last name")
            print("3. Phone number")
            choice = input("Your choice (1-3): ")
            
            if choice == '1':
                new_name = input("New first name: ").strip()
                cur.execute("UPDATE phonebook SET first_name = %s WHERE phone = %s", 
                           (new_name, phone))
            elif choice == '2':
                new_last = input("New last name: ").strip()
                cur.execute("UPDATE phonebook SET last_name = %s WHERE phone = %s", 
                           (new_last if new_last else None, phone))
            elif choice == '3':
                new_phone = input("New phone number: ").strip()
                try:
                    cur.execute("UPDATE phonebook SET phone = %s WHERE phone = %s", 
                               (new_phone, phone))
                except psycopg2.IntegrityError:
                    print("Error: New phone number already exists")
                    return
            else:
                print("Invalid choice")
                return
            
            conn.commit()
            print("Contact updated successfully")

def query_contacts():
    print("\nSearch options:")
    print("1. By first name")
    print("2. By last name")
    print("3. By phone number")
    print("4. Show all contacts")
    choice = input("Your choice (1-4): ")
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            if choice == '1':
                name = input("Enter first name: ").strip()
                cur.execute("SELECT * FROM phonebook WHERE first_name ILIKE %s", 
                           (f"%{name}%",))
            elif choice == '2':
                name = input("Enter last name: ").strip()
                cur.execute("SELECT * FROM phonebook WHERE last_name ILIKE %s", 
                           (f"%{name}%",))
            elif choice == '3':
                phone = input("Enter phone number: ").strip()
                cur.execute("SELECT * FROM phonebook WHERE phone LIKE %s", 
                           (f"%{phone}%",))
            elif choice == '4':
                cur.execute("SELECT * FROM phonebook ORDER BY first_name")
            else:
                print("Invalid choice")
                return
            
            results = cur.fetchall()
            if results:
                print(tabulate(results, 
                             headers=["ID", "First Name", "Last Name", "Phone"],
                             tablefmt="grid"))
            else:
                print("No contacts found")

def delete_contact():
    print("\nDelete by:")
    print("1. First name")
    print("2. Phone number")
    choice = input("Your choice (1-2): ")
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            if choice == '1':
                name = input("Enter first name: ").strip()
                cur.execute("DELETE FROM phonebook WHERE first_name = %s RETURNING *", 
                           (name,))
            elif choice == '2':
                phone = input("Enter phone number: ").strip()
                cur.execute("DELETE FROM phonebook WHERE phone = %s RETURNING *", 
                           (phone,))
            else:
                print("Invalid choice")
                return
            
            deleted = cur.fetchall()
            if deleted:
                print(f"Deleted {len(deleted)} contact(s):")
                for contact in deleted:
                    print(f"  {contact[1]} {contact[2]}: {contact[3]}")
            else:
                print("No contacts found to delete")
            conn.commit()

def menu():
    print("Starting menu...")
    create_table()
    while True:
        print("\nPHONEBOOK MENU")
        print("1. Add contacts from CSV")
        print("2. Add contact manually")
        print("3. Update contact")
        print("4. Search contacts")
        print("5. Delete contact")
        print("0. Exit")
        choice = input("Your choice: ").strip()
        
        if choice == '1':
            path = input("Enter CSV file path: ").strip()
            insert_from_csv(path)
        elif choice == '2':
            insert_from_console()
        elif choice == '3':
            update_contact()
        elif choice == '4':
            query_contacts()
        elif choice == '5':
            delete_contact()
        elif choice == '0':
            print("Goodbye!")
            break 
        else:
            print("Invalid choice, try again")

if __name__ == "__main__":
    menu()

