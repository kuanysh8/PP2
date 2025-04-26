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
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE OR REPLACE FUNCTION search_contacts(pattern TEXT)
                RETURNS TABLE(id INT, first_name VARCHAR, last_name VARCHAR, phone VARCHAR) AS $$
                BEGIN
                    RETURN QUERY
                    SELECT id, first_name, last_name, phone
                    FROM phonebook
                    WHERE first_name ILIKE '%' || pattern || '%'
                    OR last_name ILIKE '%' || pattern || '%'
                    OR phone ILIKE '%' || pattern || '%';
                END;
                $$ LANGUAGE plpgsql;
            """)
            conn.commit()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE OR REPLACE PROCEDURE insert_or_update_user(first_name TEXT, last_name TEXT, phone TEXT)
                LANGUAGE plpgsql AS $$
                BEGIN
                    IF EXISTS (SELECT 1 FROM phonebook WHERE phone = phone) THEN
                        UPDATE phonebook SET phone = phone WHERE phone = phone;
                    ELSE
                        INSERT INTO phonebook (first_name, last_name, phone) VALUES (first_name, last_name, phone);
                    END IF;
                END;
                $$;
            """)
            conn.commit()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE OR REPLACE PROCEDURE insert_multiple_users(users TEXT[])
                LANGUAGE plpgsql AS $$
                DECLARE
                    user_record TEXT;
                    first_name TEXT;
                    last_name TEXT;
                    phone TEXT;
                BEGIN
                    FOREACH user_record IN ARRAY users LOOP
                        first_name := split_part(user_record, ',', 1);
                        last_name := split_part(user_record, ',', 2);
                        phone := split_part(user_record, ',', 3);
                        IF LENGTH(phone) != 10 THEN
                            RAISE NOTICE 'Incorrect phone number: %', phone;
                        ELSE
                            PERFORM insert_or_update_user(first_name, last_name, phone);
                        END IF;
                    END LOOP;
                END;
                $$;
            """)
            conn.commit()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE OR REPLACE FUNCTION query_with_pagination(limit_count INT, offset_count INT)
                RETURNS TABLE(id INT, first_name VARCHAR, last_name VARCHAR, phone VARCHAR) AS $$
                BEGIN
                    RETURN QUERY
                    SELECT id, first_name, last_name, phone
                    FROM phonebook
                    LIMIT limit_count OFFSET offset_count;
                END;
                $$ LANGUAGE plpgsql;
            """)
            conn.commit()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE OR REPLACE PROCEDURE delete_by_username_or_phone(contact TEXT)
                LANGUAGE plpgsql AS $$
                BEGIN
                    DELETE FROM phonebook WHERE first_name = contact;
                    DELETE FROM phonebook WHERE phone = contact;
                END;
                $$;
            """)
            conn.commit()

def insert_from_csv(path):
    with get_connection() as conn:
        with conn.cursor() as cur:
            with open(path, mode='r', encoding='utf-8') as file:
                reader = csv.reader(file)
                next(reader)
                for row in reader:
                    try:
                        cur.execute("""
                            INSERT INTO phonebook (first_name, last_name, phone)
                            VALUES (%s, %s, %s)
                        """, (row[0].strip(), row[1].strip(), row[2].strip()))
                    except psycopg2.IntegrityError:
                        conn.rollback()
                        continue
            conn.commit()

def insert_from_console():
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
            except psycopg2.IntegrityError:
                print("Error: Phone number already exists")

def update_contact():
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
                cur.execute("UPDATE phonebook SET first_name = %s WHERE phone = %s", (new_name, phone))
            elif choice == '2':
                new_last = input("New last name: ").strip()
                cur.execute("UPDATE phonebook SET last_name = %s WHERE phone = %s", (new_last if new_last else None, phone))
            elif choice == '3':
                new_phone = input("New phone number: ").strip()
                try:
                    cur.execute("UPDATE phonebook SET phone = %s WHERE phone = %s", (new_phone, phone))
                except psycopg2.IntegrityError:
                    print("Error: New phone number already exists")
                    return
            else:
                print("Invalid choice")
                return
            conn.commit()

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
                cur.execute("SELECT * FROM phonebook WHERE first_name ILIKE %s", (f"%{name}%",))
            elif choice == '2':
                name = input("Enter last name: ").strip()
                cur.execute("SELECT * FROM phonebook WHERE last_name ILIKE %s", (f"%{name}%",))
            elif choice == '3':
                phone = input("Enter phone number: ").strip()
                cur.execute("SELECT * FROM phonebook WHERE phone LIKE %s", (f"%{phone}%",))
            elif choice == '4':
                cur.execute("SELECT * FROM phonebook ORDER BY first_name")
            else:
                print("Invalid choice")
                return
            results = cur.fetchall()
            if results:
                print(tabulate(results, headers=["ID", "First Name", "Last Name", "Phone"], tablefmt="grid"))
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
                cur.execute("CALL delete_by_username_or_phone(%s)", (name,))
            elif choice == '2':
                phone = input("Enter phone number: ").strip()
                cur.execute("CALL delete_by_username_or_phone(%s)", (phone,))
            else:
                print("Invalid choice")
                return
            conn.commit()

def menu():
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
