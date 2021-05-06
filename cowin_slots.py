import requests
import argparse
import multiprocessing
from multiprocessing import Process
from datetime import date
from time import sleep
from playsound import playsound
import sys
import os
import json

VACCINE_TYPES = ['covishield', 'covaxin', 'both']


def initialize_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--pin_code", type=str, action='append',
                        help="PIN_CODE(s) to look in. Can be passed multiple times")
    parser.add_argument("-a", "--age", type=int, help="AGE to look for")
    parser.add_argument("-t", "--type", type=str, default=None,
                        help="Vaccine type ({})".format(', '.join(VACCINE_TYPES)))
    parser.add_argument("-f", "--free", action="store_true",
                        help="Look only for free vaccination centers")
    parser.add_argument("-r", "--retry_in", type=int,
                        default=10, help="Retry lookup in RETRY_IN seconds")
    parser.add_argument("-pi", "--print_in", type=int,
                        default=600, help="Print elapsed time every PRINT_IN seconds\n\
                        This should be a multiple of RETRY_IN")
    return parser


def print_result(result):
    print("\n")
    if result == []:
        print("Sorry, no centers for your parameters.\n")
        return
    for row in result:
        print("CENTER DETAILS")
        address = row[0]
        sessions = row[1]
        print("Center Name - {}\nCenter Pin Code - {}\nDistrict - {}\nBlock - {}\nCentre Fee - {}\n".format(*address))
        print("Printing Sessions for this center:")
        for session in sessions:
            print("For", session[2], end='\t')
            print("{} doses available with minimum age {} and vaccine {}".format(
                session[0], session[1], session[3]))
        print("\n")


def extract_info(data, age, vaccine_type, only_free):
    result = []
    centers = data['centers']
    for center in centers:
        center_name = center['name']
        centre_pincode = center['pincode']
        district_name = center['district_name']
        block_name = center['block_name']
        centre_fee = center['fee_type']
        sessions = center['sessions']
        temp_result = []

        if only_free and centre_fee == 'Paid':
            continue

        for session in sessions:
            available_capacity = int(session['available_capacity'])
            if available_capacity == 0:
                continue

            session_age = int(session['min_age_limit'])
            session_vaccine = session['vaccine']
            if (
                session_age > age or
                (vaccine_type != 'both' and vaccine_type != session_vaccine.lower())
            ):
                continue
            session_date = session['date']
            if session_vaccine == '':
                session_vaccine = 'unknown'
            row = (available_capacity, session_age,
                   session_date, session_vaccine)
            temp_result.append(row)
        if temp_result != []:
            address = (center_name, centre_pincode,
                       district_name, block_name, centre_fee)
            row = (address, temp_result)
            result.append(row)

    return result


def search_slots(pin, static_data):
    cowin_date, age, vaccine_type, only_free, retry_in, print_in, work_dir = static_data
    URL = "https://cdn-api.co-vin.in/api/v2/appointment/sessions/public/calendarByPin"
    PARAMS = {'pincode': pin, 'date': cowin_date}
    HEADER = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1 Safari/605.1.15'}
    idx = 0
    while (1):
        time_elapsed = idx * retry_in
        try:
            r = requests.get(url=URL, params=PARAMS, headers=HEADER)
            data = r.json()
            if r.status_code == 400:
                print("Wrong input parameters. Please check. \n")
                sleep(retry_in)
                exit(0)
            if not data:
                print("Data not found for {}.\n".format(pin))
            result = extract_info(data, age, vaccine_type, only_free)
            if result:
                print('Register now at {}!'.format(pin))
                print_result(result)
                while(1):
                    playsound(os.path.join(work_dir, 'alarm.wav'))
            else:
                if time_elapsed % print_in == 0:
                    print('For {}, can not register yet. Time elapsed {} mins'.format(
                        pin, time_elapsed / 60))
        except requests.exceptions.ConnectionError:
            print("Connection error. Will silently retry in {} seconds".format(retry_in))
        except json.decoder.JSONDecodeError:
            print("Bad data from CoWIN server. Will silently retry in {} seconds".format(retry_in))
        sleep(retry_in)
        idx += 1


def main():
    print("\nThis software is distributed AS IS, under developer non-liability constraints, and in good faith.")
    print("Please visit https://github.com/yashjakhotiya/cowin-slots/blob/main/LICENSE for the complete license.")
    print("\nWant to add something? Visit https://github.com/yashjakhotiya/cowin-slots/\n")
    args = initialize_parser().parse_args()
    pins = args.pin_code
    if not pins:
        pins = input("Please enter space-separated pincode(s): ").split()
    age = args.age
    if not age:
        age = int(input("Please enter your age: "))
    vaccine_type = args.type
    if vaccine_type:
        vaccine_type = args.type.lower()
    while vaccine_type not in VACCINE_TYPES:
        vaccine_type = input("Please enter a vaccine type from {}: ".format(
            ', '.join(VACCINE_TYPES)
        )).lower()
    only_free = args.free
    retry_in = args.retry_in
    print_in = args.print_in
    today = date.today()
    cowin_date = "{}-{}-{}".format(today.day, today.month, today.year)
    try:
        work_dir = sys._MEIPASS
    except AttributeError:
        work_dir = '.'
    static_data = (cowin_date, age, vaccine_type, only_free, retry_in,
                   print_in, work_dir)
    print("Looking for pin codes: {}".format(pins))
    # search_slots(pins, static_data)
    procs = []
    for pin in pins:
        p = Process(target=search_slots, args=(pin, static_data))
        p.start()
        procs.append(p)
    for p in procs:
        p.join()


if __name__ == '__main__':
    multiprocessing.freeze_support()
    main()