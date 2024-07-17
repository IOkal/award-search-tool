from flask import Flask, render_template, request, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import re

app = Flask(__name__)

# from bs4 import BeautifulSoup

def extract_flight_details(container):
    # flight_details = {
    #     'segments': [],
    #     'connections': [],
    #     'prices': {'eco': None, 'ecoPremium': None, 'business': None},
    #     'mixed_cabin_percentages': {'eco': None, 'ecoPremium': None, 'business': None},
    #     'available_cabins': []
    # }
    flight_details = []

    try:
        # Ensure container is not None
        if container is None:
            raise ValueError("Container is None")

        # Parse the container using BeautifulSoup
        soup = BeautifulSoup(str(container), 'html.parser')
        
        # Extract the flight description to find segments and connections
        # flight_description = soup.select_one(".cdk-visually-hidden").text
        # print(f"Flight description: {flight_description}")
        
        # Extract segments
        # segment_matches = re.findall(r"SEG-(\w+)-(\w+)-(\d{4}-\d{2}-\d{2}-\d{4})", flight_description)
        # print(f"Segment matches: {segment_matches}")
        
        # for match in segment_matches:
        #     flight_number, route, flight_time = match
        #     departure, arrival = route.split('-')
        #     segment_info = {
        #         'flight_number': flight_number,
        #         'route': route,
        #         'departure_time': flight_time,
        #         'departure': departure,
        #         'arrival': arrival
        #     }
        #     flight_details['segments'].append(segment_info)
        
        # Extract layover information
        # layover_matches = re.findall(r"Layover of (\d+h\d+m) in (\w+)", flight_description)
        # print(f"Layover matches: {layover_matches}")
        
        # for match in layover_matches:
        #     layover_time, layover_airport = match
        #     flight_details['connections'].append({
        #         'layover_time': layover_time,
        #         'layover_airport': layover_airport
        #     })
        
        # Extract departure and arrival times
        # departure_time = soup.select_one('span.mat-h3.time.departure-time').text
        # arrival_time = soup.select_one('span.mat-h3.time.arrival-time').text
        # flight_details['departure_time'] = departure_time
        # flight_details['arrival_time'] = arrival_time
        # print(f"Departure Time: {departure_time}")
        # print(f"Arrival Time: {arrival_time}")

        # Find all instances of class "available-cabin"
        available_cabins = soup.find_all(class_="available-cabin")
        # print("len(available_cabins)")
        # print(len(available_cabins))
        
        for cabin in available_cabins:
            # Extract the Points price and format it
            points_text = cabin.select_one('.points-total').text.replace('K', '000')
            points_price = int(float(points_text.replace('.', '')))
            # print("points_price = ")
            # print(points_price)
            
            # Extract the cash price and format it
            cash_text = cabin.select_one('kilo-price').text
            cash_price = int(re.sub(r'[^\d]', '', cash_text))
            # print(cash_price)
            
            # Extract the number of seats left and format it
            seats_left_text = cabin.select_one('.seat-text').text if cabin.select_one('.seat-text') else '0'
            seats_left = int(re.search(r'\d+', seats_left_text).group()) if seats_left_text else 0
            
            # Extract the cabin type
            cabin_type_class = cabin.get('class', [])
            cabin_type_str = next((cls for cls in cabin_type_class if cls.startswith('business') or cls.startswith('eco') or cls.startswith('ecoPremium') or cls.startswith('first')), None)
            cabin_type_map = {'eco': 0, 'ecoPremium': 1, 'business': 2, 'first': 3}
            cabin_type = cabin_type_map.get(cabin_type_str.split('-')[0], -1)
            
            # Extract segment information
            segment_text = ' '.join(cabin.get('class', []))
            segment_matches = re.findall(r"SEG-(\w+)-(\w+)-(\d{4}-\d{2}-\d{2})-(\d{4})", segment_text)
            segments = []
            for match in segment_matches:
                flight_number, route, segment_dep_date, segment_dep_time = match
                segment_info = {
                    'flight_number': flight_number,
                    'route': route,
                    'segment_dep_date': segment_dep_date,
                    'segment_dep_time': segment_dep_time
                }
                segments.append(segment_info)
            
            # Save cabin details
            cabin_info = {
                'points_price': points_price,
                'cash_price': cash_price,
                'seats_left': seats_left,
                'cabin_type': cabin_type,
                'segments': segments
            }
            flight_details.append(cabin_info)
            # print(f"Cabin Info: {cabin_info}")

    except Exception as e:
        print(f"Error extracting flight details: {e}")

    return flight_details

def search_flight_from_file():
    with open('ap-award-page.html', 'r', encoding='utf-8') as file:
        html_content = file.read()

    soup = BeautifulSoup(html_content, 'html.parser')
    
    print("Extracting flight details from file...")
    flight_details_list = []

    # Locate the main container for flight details
    flight_containers = soup.select("kilo-upsell-row-cont")
    print(f"Found {len(flight_containers)} flight containers.")

    for index, container in enumerate(flight_containers):
        print(f"Inspecting container {index+1}/{len(flight_containers)}")
        flight_details = extract_flight_details(container)
        flight_details_list.append(flight_details)
        print(f"Flight details for container {index+1}: {flight_details}")

    print(f"Extracted flight details: {flight_details_list}")

    return flight_details_list


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    origin = request.form['origin']
    destination = request.form['destination']
    date = request.form['date']
    
    results = search_flight_from_file()
    
    if results == "Error":
        return jsonify({"error": "An error occurred while searching for flights."}), 500
    
    return jsonify(results)

if __name__ == '__main__':
    app.run(debug=True)
