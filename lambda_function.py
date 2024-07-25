import json
import re
import time
import boto3
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from botocore.exceptions import NoCredentialsError, PartialCredentialsError
import requests

s3_client = boto3.client('s3')

def write_to_log(log_message, bucket, log_file):
    log_message = f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {log_message}\n"
    try:
        existing_log = s3_client.get_object(Bucket=bucket, Key=log_file)['Body'].read().decode('utf-8')
    except s3_client.exceptions.NoSuchKey:
        existing_log = ""
    except Exception as e:
        print(f"Error retrieving existing log: {e}")
        existing_log = ""
    new_log = existing_log + log_message
    s3_client.put_object(Bucket=bucket, Key=log_file, Body=new_log)

def convert_points_price(points_text):
    if 'K' in points_text:
        if '.' in points_text:
            points_price = int(float(points_text.replace('K', '')) * 1000)
        else:
            points_price = int(points_text.replace('K', '000'))
    else:
        points_price = int(points_text)
    return points_price

def extract_flight_details(cabin):
    cabin_info = {}
    try:
        # Parse the cabin using BeautifulSoup
        soup = BeautifulSoup(str(cabin), 'html.parser')

        # Ensure cabin is not None
        if cabin is None:
            raise ValueError("Cabin is None")

        points_text = soup.select_one('.points-total').text
        points_price = convert_points_price(points_text)

        # Extract the cash price and format it
        cash_text = soup.select_one('kilo-price').text
        cash_price = int(re.sub(r'[^\d]', '', cash_text))

        # Extract the number of seats left and format it
        seats_left_text = soup.select_one('.seat-text').text if soup.select_one('.seat-text') else "9+"
        seats_left = int(re.search(r'\d+', seats_left_text).group()) if seats_left_text else 0

        # Extract the cabin type
        cabin_type_class = cabin.get('class', [])
        cabin_type_str = next((cls for cls in cabin_type_class if cls.startswith('business') or cls.startswith('eco') or cls.startswith('ecoPremium') or cls.startswith('first')), None)
        cabin_type_map = {'eco': 0, 'ecoPremium': 1, 'business': 2, 'first': 3}
        cabin_type = cabin_type_map.get(cabin_type_str.split('-')[0], -1)

        try:
            mixed_cabin_percentage = soup.select_one('.mixed-cabin-percentage').text
            mixed_cabin = int(re.search(r'\d+', mixed_cabin_percentage).group()) if mixed_cabin_percentage else 100
        except Exception as e:
            mixed_cabin = 100

        # Extract segment information
        segment_text = ' '.join(cabin.get('class', []))
        segment_matches = re.findall(r"SEG-(\w+)-(\w+)-(\d{4}-\d{2}-\d{2})-(\d{4})", segment_text)
        segments = []
        airports = []
        airlines = []
        for match in segment_matches:
            flight_number, route, segment_dep_date, segment_dep_time = match
            airline_code, flight_num = re.match(r"(\D+)(\d+)", flight_number).groups()
            flight_number = f"{airline_code} {flight_num}"
            departure, arrival = re.match(r"(\w{3})(\w{3})", route).groups()
            segment_info = {
                'flight_number': flight_number,
                'route': f"{departure}-{arrival}",
                'segment_dep_date': segment_dep_date,
                'segment_dep_time': segment_dep_time
            }
            segments.append(segment_info)
            airports.extend([departure, arrival])
            airlines.append(airline_code)

        # Save cabin details
        cabin_info = {
            'points_price': points_price,
            'cash_price': cash_price,
            'seats_left': seats_left,
            'cabin_type': cabin_type,
            'segments': segments,
            'mixed_cabin': mixed_cabin,
            'airports': list(set(airports)),
            'airlines': list(set(airlines))
        }

    except Exception as e:
        print(f"Error extracting flight details: {e}")

    return cabin_info

def upload_to_s3(file_name, bucket, object_name=None):
    if object_name is None:
        object_name = file_name

    try:
        response = s3_client.upload_file(file_name, bucket, object_name)
    except NoCredentialsError:
        print("Credentials not available")
        return False
    except PartialCredentialsError:
        print("Incomplete credentials provided")
        return False

    return True

def search_flight_live(origin, destination, date, log_file):
    url = f"https://www.aircanada.com/aeroplan/redeem/availability/outbound?org0={origin}&dest0={destination}&departureDate0={date}&ADT=1&YTH=0&CHD=0&INF=0&INS=0&lang=en-CA&tripType=O&marketCode=INT"

    payload = {
       'api_key': '',
       'country_code': '',
       'url': ''
    }

    response = requests.get('', params=payload)
    write_to_log(response.text, 'output-bucket-885053922788', log_file)

    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("window-size=1920,1080")
    chrome_options.add_argument("start-maximized")
    chrome_options.add_argument("--disable-setuid-sandbox")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--single-process")
    chrome_options.binary_location = "/opt/headless-chromium"
    chrome_options.add_argument("--proxy-server=http://43.130.61.30:3128")
    chrome_options.add_argument("--proxy-bypass-list=*")

    service = Service("/opt/chromedriver")
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        driver.get(url)
        write_to_log(f"Searching: {origin} to {destination} on {date}", 'output-bucket-885053922788', log_file)

        # Wait for the loading spinner to disappear
        write_to_log("Waiting for loading spinner to disappear...", 'output-bucket-885053922788', log_file)
        WebDriverWait(driver, 60).until(
            EC.invisibility_of_element((By.CSS_SELECTOR, "kilo-loading-spinner-pres"))
        )
        write_to_log("Loading spinner disappeared.", 'output-bucket-885053922788', log_file)

        # Save the current page source to S3 for debugging purposes
        page_source = driver.page_source
        file_name = f"/tmp/{origin}_{destination}_{date}.html"
        with open(file_name, "w", encoding="utf-8") as f:
            f.write(page_source)
        upload_to_s3(file_name, "output-bucket-885053922788")

        # Check if there are no flights available
        no_flights_element = driver.find_elements(By.XPATH, "//h1[contains(text(), 'No flights available')]")
        if no_flights_element:
            write_to_log(f"No flights available for {origin} to {destination} on {date}", 'output-bucket-885053922788', log_file)
            return []

        # Wait for the flights count element to be present
        write_to_log("Waiting for flights count element to be present...", 'output-bucket-885053922788', log_file)
        WebDriverWait(driver, 60).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "span.flights-count"))
        )
        write_to_log("Flights count element present.", 'output-bucket-885053922788', log_file)

        # Extract flight details
        write_to_log("Extracting flight details...", 'output-bucket-885053922788', log_file)
        flight_details_list = []

        # Extract the page source and parse it with BeautifulSoup
        soup = BeautifulSoup(page_source, 'html.parser')

        # Locate the main container for flight details
        available_cabins = soup.find_all(class_="available-cabin")
        write_to_log(f"Found {len(available_cabins)} cabins.", 'output-bucket-885053922788', log_file)

        for index, container in enumerate(available_cabins):
            write_to_log(f"Inspecting container {index+1}/{len(available_cabins)}", 'output-bucket-885053922788', log_file)
            flight_details = extract_flight_details(container)
            flight_details_list.append(flight_details)
            write_to_log(f"Flight details for container {index+1}: {flight_details}", 'output-bucket-885053922788', log_file)

        write_to_log(f"Extracted flight details: {flight_details_list}", 'output-bucket-885053922788', log_file)

        return flight_details_list
    except Exception as e:
        write_to_log(f"An error occurred: {e}", 'output-bucket-885053922788', log_file)
        return []
    finally:
        driver.quit()

def lambda_handler(event, context):
    events = event.get('body').get('Origin')
    origin = event.get('Origin')
    destination = event.get('Destination')
    date = event.get('Date')

    log_file = f"{origin}_{destination}_{date}_log.txt"
    write_to_log(event, 'output-bucket-885053922788', log_file)
    write_to_log("/n", 'output-bucket-885053922788', log_file)
    write_to_log(events, 'output-bucket-885053922788', log_file)

    if not origin or not destination or not date:
        write_to_log("Missing parameters", 'output-bucket-885053922788', log_file)
        return {
            'statusCode': 400,
            'body': json.dumps('Missing parameters')
        }

    results = search_flight_live(origin, destination, date, log_file)

    if not results:
        write_to_log("No flights found", 'output-bucket-885053922788', log_file)
        return {
            'statusCode': 200,
            'body': json.dumps('No flights found')
        }

    write_to_log("Search completed successfully", 'output-bucket-885053922788', log_file)
    return {
        'statusCode': 200,
        'body': json.dumps(results)
    }
