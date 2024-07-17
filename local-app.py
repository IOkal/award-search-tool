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
    try:
        # Ensure cabin is not None
        if cabin is None:
            raise ValueError("Cabin is None")

        # Parse the cabin using BeautifulSoup
        soup = BeautifulSoup(str(cabin), 'html.parser')
       
        points_text = cabin.select_one('.points-total').text
        points_price = convert_points_price(points_text)
        
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

    except Exception as e:
        print(f"Error extracting flight details: {e}")

    return cabin_info

def search_flight_from_file():
    with open('ap-award-page.html', 'r', encoding='utf-8') as file:
        html_content = file.read()

    soup = BeautifulSoup(html_content, 'html.parser')
    
    print("Extracting flight details from file...")
    flight_details_list = []

    # Locate the main container for flight details
    available_cabins = soup.find_all(class_="available-cabin")
    print(f"Found {len(available_cabins)} cabins.")

    for index, container in enumerate(available_cabins):
        print(f"Inspecting container {index+1}/{len(available_cabins)}")
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
    # print("count = ")
    # print(len(results))
    if results == "Error":
        return jsonify({"error": "An error occurred while searching for flights."}), 500
    
    return jsonify(results)

if __name__ == '__main__':
    app.run(debug=True)
