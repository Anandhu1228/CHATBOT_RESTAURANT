from fastapi import FastAPI
from fastapi import Request
from starlette.responses import JSONResponse
import db_helper
import general_helper

app = FastAPI()

inprogress_orders = {}

@app.post("/")
async def handle_request(request: Request):
    payload = await request.json()
    intent = payload['queryResult']['intent']['displayName']
    parameters = payload['queryResult']['parameters']
    output_contexts = payload['queryResult']['outputContexts']

    session_id = general_helper.extract_session_id(output_contexts[0]["name"])

    # Handle Order.now-initialize-order first to clear previous orders
    if intent == "Order.now-initialize-order":
        return order_now_clear_rec(parameters, session_id)

    # Proceed to other intents
    intent_handler_dict = {
        'order.add- context : ongoing order': add_to_order,
        'order.remove-context: ongoing-order': remove_from_order,
        'order.complete - context: ongoing order': complete_order,
        'track.order - context : ongoing tracking': track_order,
        'cancel-order-context-ongoing-order': cancel_order,
    }

    return intent_handler_dict[intent](parameters, session_id)



def track_order(parameters :dict,session_id: str):
    order_id = parameters['tracking_id']
    order_status = db_helper.get_order_status(order_id)

    if order_status:
        fullfillment_text = f"The order status for order id: {order_id} is: {order_status}"
    else:
        fullfillment_text = f"No order found with order id: {order_id}"

    return JSONResponse(content={
        "fulfillmentText": fullfillment_text
    })


#          UPDATE EXISTING WITH NEW VALUE
# def add_to_order(parameters: dict, session_id):
#     food_items = parameters["food-item"]
#     quantities = parameters["number"]
#
#     if len(food_items) != len(quantities):
#         fulfillment_text = "Sorry I didn't understand. Can you please specify food items and quantities clearly?"
#     else:
#         fulfillment_text = f"recieved {food_items} and {quantities} in the backend"
#         new_food_dict = dict(zip(food_items, quantities))
#
#         if session_id in inprogress_orders:
#             current_food_dict = inprogress_orders[session_id]
#             current_food_dict.update(new_food_dict)
#             inprogress_orders[session_id] = current_food_dict
#         else:
#             inprogress_orders[session_id] = new_food_dict
#
#         order_str = general_helper.get_str_from_food_dict(inprogress_orders[session_id])
#         fulfillment_text = f"So far you have: {order_str}. Do you need anything else?"
#
#     return JSONResponse(content={
#         "fulfillmentText": fulfillment_text
#     })


#          APPEND NEW WITH EXISTING VALUE
def add_to_order(parameters: dict, session_id):
    food_items = parameters["food-item"]
    quantities = parameters["number"]

    if len(food_items) != len(quantities):
        fulfillment_text = "Sorry I didn't understand. Can you please specify food items and quantities clearly?"
    else:
        fulfillment_text = f"Received {food_items} and {quantities} in the backend"
        new_food_dict = dict(zip(food_items, quantities))

        if session_id in inprogress_orders:
            current_food_dict = inprogress_orders[session_id]

            # Update the quantities instead of replacing them
            for item, qty in new_food_dict.items():
                if item in current_food_dict:
                    current_food_dict[item] += qty  # Increment the quantity
                else:
                    current_food_dict[item] = qty  # Add new item

            inprogress_orders[session_id] = current_food_dict
        else:
            inprogress_orders[session_id] = new_food_dict

        order_str = general_helper.get_str_from_food_dict(inprogress_orders[session_id])
        fulfillment_text = f"So far you have: {order_str}. Do you need anything else?"

    return JSONResponse(content={
        "fulfillmentText": fulfillment_text
    })


def complete_order(parameters: dict, session_id: str):
    if session_id not in inprogress_orders:
        fulfillment_text = "I'm having a trouble finding your order. Sorry! Can you place a new order please?"
    else:
        order = inprogress_orders[session_id]
        order_id = save_to_db(order)
        if order_id == -1:
            fulfillment_text = "Sorry, I couldn't process your order due to a backend error. " \
                               "Please place a new order again"
        else:
            order_total = db_helper.get_total_order_price(order_id)

            fulfillment_text = f"Awesome. We have placed your order. " \
                               f"Here is your order id # {order_id}. " \
                               f"Your order total is {order_total} which you can pay at the time of delivery!"

        del inprogress_orders[session_id]

    return JSONResponse(content={
        "fulfillmentText": fulfillment_text
    })



def save_to_db(order: dict):
    next_order_id = db_helper.get_next_order_id()

    # Insert individual items along with quantity in orders table
    for food_item, quantity in order.items():
        rcode = db_helper.insert_order_item(
            food_item,
            quantity,
            next_order_id
        )

        if rcode == -1:
            return -1

    # Now insert order tracking status
    db_helper.insert_order_tracking(next_order_id, "in progress")

    return next_order_id


def remove_from_order(parameters: dict, session_id: str):
    if session_id not in inprogress_orders:
        return JSONResponse(content={
            "fulfillmentText": "I'm having a trouble finding your order. Sorry! Can you place a new order please?"
        })

    food_items = parameters["food-item"]
    current_order = inprogress_orders[session_id]

    removed_items = []
    no_such_items = []

    for item in food_items:
        if item not in current_order:
            no_such_items.append(item)
        else:
            removed_items.append(item)
            del current_order[item]

    if len(removed_items) > 0:
        fulfillment_text = f'Removed {",".join(removed_items)} from your order!'

    if len(no_such_items) > 0:
        fulfillment_text = f' Your current order does not have {",".join(no_such_items)}'

    if len(current_order.keys()) == 0:
        fulfillment_text += " Your order is empty!"
    else:
        order_str = general_helper.get_str_from_food_dict(current_order)
        fulfillment_text += f" Here is what is left in your order: {order_str}"

    return JSONResponse(content={
        "fulfillmentText": fulfillment_text
    })


def cancel_order(parameters: dict, session_id: str):
    order_id = parameters['tracking_id']
    order_status = db_helper.cancell_order(order_id)

    if order_status == -1:
        fulfillment_text = "Sorry, I couldn't process your order due to a backend error. " \
                           "Please try again later or place a new order."
    elif order_status == "cancelled":
        fulfillment_text = f"Your order with order id {order_id} has been successfully cancelled."
    elif order_status is None:
        fulfillment_text = f"Sorry, I couldn't find any order with the order id {order_id}. Please check the id and try again."
    else:
        fulfillment_text = "Something went wrong. Please contact customer support for assistance."

    return JSONResponse(content={
        "fulfillmentText": fulfillment_text
    })


def order_now_clear_rec(parameters: dict, session_id):
    # Check if an order exists and clear it
    if session_id in inprogress_orders:
        del inprogress_orders[session_id]
        print(f"🛑 Cleared previous order. Proceed with new order")  # Debugging log

    return JSONResponse(content={})


@app.post("/get_name_quantity_order")
async def get_name_quantity_order(request: Request):
    try:
        data = await request.json()
        items = data.get("items", [])

        if not items or not isinstance(items, list):
            print("❌ Invalid input: Missing or incorrect 'items' list")
            return None  # Return None if invalid input

        food_items = [item["name"] for item in items]
        quantities = [item["quantity"] for item in items]

        order_details = dict(zip(food_items, quantities))
        print(f"✅ Received order: {order_details}")

        order_id = save_to_db_NODE(order_details)

        if order_id:  # If order is successfully saved, return order_id
            return order_id

        return None  # Return None if saving failed

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return None  # Return None if an error occurs



def save_to_db_NODE(order: dict):
    next_order_id = db_helper.get_next_order_id()

    # Insert individual items along with quantity in orders table
    for food_item, quantity in order.items():
        rcode = db_helper.insert_order_item(
            food_item,
            quantity,
            next_order_id
        )

        if rcode == -1:
            return -1

    # Now insert order tracking status
    db_helper.insert_order_tracking(next_order_id, "in progress")

    return next_order_id

