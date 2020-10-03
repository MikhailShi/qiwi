#!/usr/bin/python3

# This module is a concise implementation of qiwi.con p2p payment API
# for information purposes only. No liability accepted upon any
# intended or unintended loss due to the below scripts.
# Those running this module takes full responsibility on any
# possible outcome.
# Part of this code was sourced from https://t.me/ssleg

import os
import sys
import json
import time
import uuid
import hmac
import hashlib
import logging
import requests

from datetime import datetime, timedelta, timezone

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)


class Qiwi:
    # https://developer.qiwi.com/en/p2p-payments/#http
    # https://github.com/QIWI-API/p2p-payments-docs/blob/master/p2p-payments_en.html.md

    HEADERS = {
        "Authorization": "Bearer ",
        "Accept": "application/json",
    }

    BASE_URL = "https://api.qiwi.com/partner/bill/v1/bills/"

    INVOICE_JSON = {
        "amount": {
            "currency": "RUB",
            "value": "",
        },
        "expirationDateTime": "",
        "comment": "",
        "customer": {},
        "customFields": {},
    }

    @property
    def JSON_HEADERS(self):
        return {"Content-Type": "application/json", **self.HEADERS}

    def init_key(self):
        # Use this url to create Secret/Public Keys pair: https://p2p.qiwi.com

        if os.getenv("QIWI_SECRET_KEY") is not None:
            self.HEADERS['Authorization'] = "Bearer " + os.getenv("QIWI_SECRET_KEY")


def issue_invoice(bill_id, amount, comment=None, email=None, minutes=5):
    """Method to initiate invoice.
    https://developer.qiwi.com/en/p2p-payments/#API

    :param bill_id: bill id
    :type bill_id: str (200)
    :param amount: bill amount in rubbles
    :type amount: float/int/str
    :param comment: comment to the bill
    :type comment: str (255)
    :param email: customer email
    :type email: str
    :param minutes: invoice due period (in minutes)
    :type minutes: int
    :return: payment url or 'error'
    :rtype: str
    """
    invoice_json = Qiwi().INVOICE_JSON
    if comment is not None:
        invoice_json["comment"] = comment
    if email is not None:
        invoice_json["customer"] = {"email": email}

    invoice_json["amount"]["value"] = "{:.2f}".format(amount)

    # This invoice is valid for X minutes, adjust accordingly
    invoice_json["expirationDateTime"] = (
            datetime.utcnow().replace(tzinfo=timezone.utc) +
            timedelta(minutes=minutes)
    ).isoformat(sep="T", timespec="seconds")

    url = Qiwi.BASE_URL + str(bill_id)
    headers = Qiwi().JSON_HEADERS
    try:
        invoice_response = requests.put(
            url,
            json=invoice_json,
            headers=headers,
            timeout=15
        )
        cod = invoice_response.status_code
        invoice_data = invoice_response.json()
        if cod == 200:
            return invoice_data["payUrl"]
        else:
            levent = 'qiwi server error (create bill). code - ' + str(cod) + ', response - ' + str(invoice_data)
            logging.warning(levent)
            return 'error'

    except Exception as e:
        levent = 'protocol error (create bill): ' + str(e)
        logging.error(levent)
        return 'error'


def payment_confirmation(bill_id):
    """Receive payment confirmation.
    https://developer.qiwi.com/en/p2p-payments/#invoice-status
    Statuses:
    =====================================================
    Status   Description                            Final
    WAITING  Invoice issued awaiting for payment    -
    PAID     Invoice paid                           +
    REJECTED Invoice rejected by customer           +
    EXPIRED  Invoice expired. Invoice not paid      +

    :param bill_id: bill id
    :type bill_id: str
    :return: response status value or 'error'
    :rtype: str
    """

    try:
        response = requests.get(
            Qiwi.BASE_URL + str(bill_id),
            headers=Qiwi().HEADERS,
            timeout=15
        )
        cod = response.status_code
        res = response.json()
        if cod == 200:
            status = res.get("status")
            return status.get("value")
        else:
            levent = ("qiwi server error (bill status). code - " +
                      str(cod) + ", response - " + str(res))
            logging.warning(levent)
            return 'error'

    except Exception as e:
        levent = "protocol error (bill status): " + str(e)
        logging.error(levent)
        return "error"


def payment_cancellation(bill_id):
    """Cancel the invoice.
    https://developer.qiwi.com/en/p2p-payments/#cancel
    Statuses:
    =====================================================
    Status   Description                            Final
    WAITING  Invoice issued awaiting for payment    -
    PAID     Invoice paid                           +
    REJECTED Invoice rejected by customer           +
    EXPIRED  Invoice expired. Invoice not paid      +

    :param bill_id: bill id
    :type bill_id: str
    :return: response status value or 'error'
    :rtype: str
    """

    try:
        response = requests.get(
            Qiwi.BASE_URL + str(bill_id) + "/reject",
            headers=Qiwi().HEADERS,
            timeout=15
        )
        cod = response.status_code  # getting 40X all the time
        res = response.json()
        if cod == 200:
            status = res.get("status")
            return status.get("value")
        else:
            levent = ("qiwi server error (bill status). code - " +
                      str(cod) + ", response - " + str(res))
            logging.warning(levent)
            return 'error'

    except Exception as e:
        levent = "protocol error (bill status): " + str(e)
        logging.error(levent)
        return "error"


def check_bill(signature, json_data):
    """
    JSON response example:
    {
        "bill": {
            "siteId": "vwxyz1-00",
            "billId": "bd9f21f7-1973-4e2f-b9fb-0469e95fd003",
            "amount": {
                "value": "1.00",
                "currency": "RUB"
            },
            "status":{
                "value": "PAID",
                "changedDateTime": "2020-10-02T19:26:39+03"
            },
            "customer": {},
            "customFields": {
                "CHECKOUT_REFERER": "https://your-site-url.com"
            },
            "comment": "",
            "creationDateTime": "2020-10-02T19:24:18+03",
            "expirationDateTime": "2020-10-02T19:34:17+03"
        },
        "version": "1"
    }

    invoice_parameters_bytes = b"RUB|1.00|bd9f21f7-1973-4e2f-b9fb-0469e95fd003|tmdso5-00|PAID"

    :param signature: X-Api-Signature-SHA256
    :type signature: string
    :param json_data: json data
    :type json_data: json
    :return: signature verification results (True - verified)
    :rtype: bool
    """

    s = json.dumps(json_data)
    logging.debug(f"JSON received {s}")

    bill_id = json_data["bill"].get("billId")
    site_id = json_data["bill"].get("siteId")
    amount_currency = json_data["bill"]["amount"].get("currency")
    amount_value = json_data["bill"]["amount"].get("value")
    status_value = json_data["bill"]["status"].get("value")
    logging.debug(f"Checking hash for {bill_id}")

    invoice_parameters_bytes = f"{amount_currency}|{amount_value}|{bill_id}|{site_id}|{status_value}".encode()

    secret_key = os.getenv("QIWI_SECRET_KEY")
    secret_key_bytes = secret_key.encode()

    hash_generated = hmac.new(
        secret_key_bytes,
        msg=invoice_parameters_bytes,
        digestmod=hashlib.sha256
    ).hexdigest()
    flag = signature == hash_generated

    logging.debug(f"hash1: {signature}")
    logging.debug(f"hash2: {hash_generated}")
    logging.debug(f"hashes equal: {flag}")

    return flag


if __name__ == "__main__":

    Qiwi().init_key()

    key = str(uuid.uuid4())

    # try with 1 rubble bill
    url = issue_invoice(key, amount=1, comment="test")
    logging.info(url)

    for i in range(10):
        logging.info(payment_confirmation(key))
        time.sleep(10)
