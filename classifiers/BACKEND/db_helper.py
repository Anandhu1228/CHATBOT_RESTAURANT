import mysql.connector

# Function to create a new database connection
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="paSSwoRD@1228",
        database="pandeyji_eatery"
    )

# Function to fetch the order status from the order_tracking table
def get_order_status(order_id: int):
    cnx = get_db_connection()  # Open a new connection each time
    cursor = cnx.cursor()

    try:
        # Executing the SQL query to fetch the order status
        query = "SELECT status FROM order_tracking WHERE order_id = %s"
        cursor.execute(query, (order_id,))
        result = cursor.fetchone()
    finally:
        # Always close the cursor and connection after use
        cursor.close()
        cnx.close()

    # Returning the order status
    return result[0] if result else None



def insert_order_item(food_item, quantity, order_id):
    cnx = get_db_connection()
    try:
        cursor = cnx.cursor()

        # Calling the stored procedure
        cursor.callproc('insert_order_item', (food_item, quantity, order_id))

        # Committing the changes
        cnx.commit()

        # Closing the cursor
        cursor.close()

        print("Order item inserted successfully!")

        return 1

    except mysql.connector.Error as err:
        print(f"Error inserting order item: {err}")

        # Rollback changes if necessary
        cnx.rollback()

        return -1

    except Exception as e:
        print(f"An error occurred: {e}")
        # Rollback changes if necessary
        cnx.rollback()

        return -1

# Function to insert a record into the order_tracking table
def insert_order_tracking(order_id, status):
    cnx = get_db_connection()
    cursor = cnx.cursor()

    # Inserting the record into the order_tracking table
    insert_query = "INSERT INTO order_tracking (order_id, status) VALUES (%s, %s)"
    cursor.execute(insert_query, (order_id, status))

    # Committing the changes
    cnx.commit()

    # Closing the cursor
    cursor.close()

def get_total_order_price(order_id):
    cnx = get_db_connection()
    cursor = cnx.cursor()

    # Executing the SQL query to get the total order price
    query = f"SELECT get_total_order_price({order_id})"
    cursor.execute(query)

    # Fetching the result
    result = cursor.fetchone()[0]

    # Closing the cursor
    cursor.close()

    return result

# Function to get the next available order_id
# def get_next_order_id():
#     cnx = get_db_connection()
#     cursor = cnx.cursor()
#
#     # Executing the SQL query to get the next available order_id
#     query = "SELECT MAX(order_id) FROM orders"
#     cursor.execute(query)
#
#     # Fetching the result
#     result = cursor.fetchone()[0]
#
#     # Closing the cursor
#     cursor.close()
#
#     # Returning the next available order_id
#     if result is None:
#         return 1
#     else:
#         return result + 1


def get_next_order_id():
    cnx = get_db_connection()
    cursor = cnx.cursor()

    # Executing the SQL query to get the maximum order_id
    query = "SELECT MAX(order_id) FROM orders"
    cursor.execute(query)

    # Fetching the result
    result = cursor.fetchone()[0]

    # Closing the cursor
    cursor.close()

    # If table is empty, start from 12345678; otherwise, increment max order_id
    return 12345678 if result is None else result + 1


def cancell_order(order_id: int):
    cnx = get_db_connection()  # Open a new connection each time
    cursor = cnx.cursor()

    try:
        # Check if order exists
        query = "SELECT status FROM order_tracking WHERE order_id = %s"
        cursor.execute(query, (order_id,))
        result = cursor.fetchone()

        if result:
            # Update the order status to 'cancelled'
            update_query = "UPDATE order_tracking SET status = %s WHERE order_id = %s"
            cursor.execute(update_query, ("cancelled", order_id))
            cnx.commit()  # Commit the transaction
            return "cancelled"
        else:
            return None  # Order not found
    except Exception as e:
        print(f"Error cancelling order: {e}")
        return -1  # Indicate an error
    finally:
        # Always close the cursor and connection after use
        cursor.close()
        cnx.close()
