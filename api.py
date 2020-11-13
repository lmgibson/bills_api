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


def calculateAmountOwedPerReceipt(data_dict):
    """Calculates the amount owed to the payor of each receipt

    Args:
        data_dict (dictionary): Takes in the underlying database after it has
        been filtered through for a given month and year.

    Returns:
        Dictionary: Returns a dictionary with key value pairs of Payor: Amount owed
        per receipt.
    """
    sharedItems = data_dict['total_price'] - \
        data_dict['payor_item_total'] - data_dict['non_payor_item_total']
    owed = (sharedItems / 2) + data_dict['non_payor_item_total']
    return {data_dict['payor']: owed}


def amountOwedPerMonth(data_dict):
    """Calculates the total amount owed from the non-rent payor to the rent payor

    Args:
        data_dict (dictionary): Dictionary with key value pairs of Payor: Amount owed
        for each receipt in a given month, year
    """
    totalRent = 1854
    whoPaidRent = 'Hannah'
    totalAmountOwed = dict(functools.reduce(operator.add,
                                            map(collections.Counter, data_dict)))
    amountOwedByNonRentPayor = (totalRent) / \
        (2 + totalAmountOwed[whoPaidRent] - totalAmountOwed['Landon'])
    return amountOwedByNonRentPayor


# Routes
@app.route('/')
def home():
    return "Hello. Endpoints are: /api/v1/ . . . [all, submit, amount_owed]"


@app.route('/api/v1/all', methods=['GET'])
@basic_auth.required
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
    monthYearRequested = request.args.get('month')
    year = int(monthYearRequested[0:4])
    month = int(monthYearRequested[5:7])

    amountOwedPerReceiptData = []

    for i, val in enumerate(data['receipts']):
        if (val['month'] == month) & (val['year'] == year):
            amountOwedPerReceiptData.append(calculateAmountOwedPerReceipt(val))
        else:
            return "That Month/Year combination is not in the data"

    results = amountOwedPerMonth(amountOwedPerReceiptData)

    return ("For the month of " + str(month) + "/" + str(year) + ": \n" +
            "Hannah is owed: " + "$" + str(round(results, 2)))
