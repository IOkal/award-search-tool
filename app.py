    from flask import Flask, render_template, request, jsonify
    import requests
    import json
    import time

    app = Flask(__name__)

    MAX_CONCURRENT_REQUESTS = 10

    def generate_date_range(start_date, end_date):
        from datetime import datetime, timedelta

        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        delta = end - start

        return [(start + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(delta.days + 1)]

    @app.route('/')
    def index():
        print("Rendering index.html")
        return render_template('index.html')

    @app.route('/search', methods=['POST'])
    def search():
        print("Search initiated")
        data = request.get_json()
        print(f"Received data: {data}")

        origins = data.get('origin').split(',')
        destinations = data.get('destination').split(',')
        dates = data.get('date')

        if ':' in dates:
            date_range = generate_date_range(*dates.split(':'))
        else:
            date_range = dates.split(',')

        permutations = [(origin.strip(), destination.strip(), date.strip()) for origin in origins for destination in destinations for date in date_range]
        print(f"Total permutations to process: {len(permutations)}")

        results = []
        failed_searches = []
        success_searches = 0

        batch_start_index = 0

        def process_batch(batch):
            nonlocal results, success_searches, failed_searches

            for origin, destination, date in batch:
                print(f"Processing: {origin} to {destination} on {date}")
                try:
                    response = requests.post(API_GATEWAY_ENDPOINT, json={"Origin": origin, "Destination": destination, "Date": date})
                    print(f"Response status code: {response.status_code}")
                    print(f"Response text: {response.text}")

                    if response.status_code == 200:
                        request_id = response.json().get('request_id')
                        print(f"Request ID: {request_id}")
                        if request_id:
                            # Poll for the result
                            result = poll_for_result(request_id)
                            if result:
                                results.extend(result if isinstance(result, list) else [result])
                                success_searches += 1
                            else:
                                failed_searches.append(f"{origin} to {destination} on {date}")
                        else:
                            failed_searches.append(f"{origin} to {destination} on {date}: No request_id in response")
                    else:
                        failed_searches.append(f"{origin} to {destination} on {date}: {response.status_code} - {response.text}")
                except Exception as e:
                    print(f"Failed to search {origin} to {destination} on {date}: {str(e)}")
                    failed_searches.append(f"{origin} to {destination} on {date}: {str(e)}")

        def poll_for_result(request_id):
            print(f"Polling for result with request ID: {request_id}")
            poll_url = f"{API_GATEWAY_ENDPOINT}/{request_id}/status"
            while True:
                time.sleep(5)  # wait for 5 seconds before polling again
                response = requests.get(poll_url)
                print(f"Poll response status code: {response.status_code}")
                print(f"Poll response text: {response.text}")

                if response.status_code == 200:
                    response_data = response.json()
                    print(f"Poll response data: {response_data}")
                    if response_data['status'] == 'completed':
                        return response_data['result']
                    elif response_data['status'] == 'failed':
                        return None
                else:
                    print(f"Polling failed with status code: {response.status_code}")
                    return None

        while batch_start_index < len(permutations):
            batch = permutations[batch_start_index:batch_start_index + MAX_CONCURRENT_REQUESTS]
            print(f"Processing batch {batch_start_index // MAX_CONCURRENT_REQUESTS + 1}")
            process_batch(batch)
            batch_start_index += MAX_CONCURRENT_REQUESTS

        print(f"Successful searches: {success_searches}")
        print(f"Failed searches: {failed_searches}")

        return jsonify({"success_searches": success_searches, "failed_searches": failed_searches, "results": results})

    if __name__ == '__main__':
        print("Starting Flask app")
        app.run(debug=True)
