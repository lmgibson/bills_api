from flask import Flask, request, jsonify
from flask_basicauth import BasicAuth
from flask_cors import CORS
import collections
import functools
import operator
import os
import json

app = Flask(__name__)
CORS(app)

app.config['BASIC_AUTH_USERNAME'] = os.environ['API_USERNAME']
app.config['BASIC_AUTH_PASSWORD'] = os.environ['API_PASSWORD']
basic_auth = BasicAuth(app)


# Data
with open('./data.json') as f:
    data = json.load(f)


# Functions
def validate(data_dict):
    """Validates form inputs

    Args:
        data_dict (dictionary): Dictionary of the form inputs that have been
        processed to make everything the correct type.

    Returns:
        Nothing: Returns no values if successful. However, if a check fails it will
        abruptly stop the process and return a reason why.
    """
    if type(data_dict['date']) != str:
        return "Date isn't a string"
    if type(data_dict['store']) != str:
        return "Store name needs to be a string"
    if type(data_dict['payor']) != str:
        return "Payor needs to be a string"
    if type(data_dict['total_price']) != float:
        return "Price needs to be a float or integer"
    if type(data_dict['payor_item_total']) != float:
        return "Payor item total needs to be a float or an integer"
    if type(data_dict['non_payor_item_total']) != float:
        return "Non-Payor item total needs to be a float or an integer"


def amount_owed_per_receipt(data_dict):
    """Calculates the amount owed to the payor of each receipt

    Args:
        data_dict (dictionary): Takes in the underlying database after it has
        been filtered through for a given month and year.

    Returns:
        Dictionary: Returns a dictionary with key value pairs of Payor: Amount owed
        per receipt.
    """
    shared_items = data_dict['total_price'] - \
        data_dict['payor_item_total'] - data_dict['non_payor_item_total']
    owed = (shared_items/2) + data_dict['non_payor_item_total']
    return {data_dict['payor']: owed}


def amount_owed_total(data_dict, rent_amount=2000, who_pays_rent='Hannah'):
    """Calculates the total amount owed from the non-rent payor to the rent payor

    Args:
        data_dict (dictionary): Dictionary with key value pairs of Payor: Amount owed
        for each receipt in a given month, year
        rent_amount (float): How much is your rent. Takes a float or integer value.
        who_pays_rent (String): Name of the person who will be paying the rent. This way
        the function can calculate with respect to whom the returns need to be estimated.
    """
    totals = dict(functools.reduce(operator.add,
                                   map(collections.Counter, data_dict)))
    non_payor_owed = rent_amount/2 + totals[who_pays_rent] - totals['Landon']
    return non_payor_owed

# Routes


@app.route('/api/v1/all', methods=['GET'])
def api_all():
    return jsonify(data)


@app.route('/api/v1/submit', methods=['POST'])
@basic_auth.required
def api_add_item():

    tmp = {
        'date': request.form.get('date'),
        'month': int(request.form.get('date')[5:7]),
        'year': int(request.form.get('date')[0:4]),
        'store': request.form.get('store'),
        'total_price': float(request.form.get('total_price')),
        'payor': request.form.get('payor'),
        'payor_item_total': float(request.form.get('payor_item_total')),
        'non_payor_item_total': float(request.form.get('non_payor_item_total'))
    }

    validate(tmp)
    data['receipts'].append(tmp)

    # Save to file - should be careful and prevent this happening often!
    with open('./data.json', 'w') as f:
        json.dump(data, f, indent=4)

    return jsonify(data)


@app.route('/api/v1/amount_owed', methods=['GET'])
def api_get_results():
    month = int(request.args.get('month'))
    year = int(request.args.get('year'))

    dt = []

    for i, val in enumerate(data['receipts']):
        if (val['month'] == month) & (val['year'] == year):
            dt.append(amount_owed_per_receipt(val))
        else:
            return "That Month/Year combination is not in the data"

    results = amount_owed_total(dt)

    return ("For the month of " + str(month) + "/" + str(year) + ": \n" +
            "Hannah is owed: " + "$" + str(results))
