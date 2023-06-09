from flask import Flask, request, jsonify
from elasticsearch import Elasticsearch
from datetime import datetime
import mysql.connector
import srt
import logging
import retrying

# Set up the logging configuration
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)

@retrying.retry(wait_fixed=2000, stop_max_attempt_number=5, retry_on_exception=lambda e: isinstance(e, ConnectionError))
def connect_to_elasticsearch():
    es = Elasticsearch(
        hosts=[
            {
                'host': 'localhost',
                'port': 9200,
                'scheme': 'http'
            }
        ]
    )
    return es

try:
    es = connect_to_elasticsearch()
    # Continue with Elasticsearch operations
except ConnectionError as e:
    # Handle connection errors
    print(f"Failed to connect to Elasticsearch: {e}")


mysql_config = {
    'user': 'subtitles_user',
    'password': 'password123',
    'host': 'mysql',
    'port': 3306,
    'database': 'subtitles_db',
    'raise_on_warnings': True
}



# Initialize MySQL connection and cursor
cnx = mysql.connector.connect(**mysql_config)
cursor = cnx.cursor()

def search_elasticsearch(query):
    # Search Elasticsearch for query text
    search_body = {
        "query": {
            "match": {
                "subtitle": query
            }
        }
    }
    result = es.search(index='subtitles', body=search_body)
    hits = result['hits']['hits']

    movie_lines = []
    for hit in hits:
        movie_lines.append((hit['_source']['movie_id'], hit['_source']['line_id']))

    return movie_lines


def search_mysql(movie_lines):
    results = []
    for movie_id, line_id in movie_lines:
        query = "SELECT movie_id, line_id, start_time, end_time, text FROM subtitles_db WHERE movie_id = %s AND line_id = %s"
        cursor.execute(query, (movie_id, line_id))
        row = cursor.fetchone()
        if row:
            results.append({
                "movie_id": row[0],
                "line_id": row[1],
                "start_time": row[2],
                "end_time": row[3],
                "text": row[4]
            })

    return results

@app.route('/search', methods=['POST'])
def search_subtitle():
    query = request.json.get('query')

    if not query:
        return jsonify({"error": "Query parameter is missing."}), 400

    # Step 2: Search Elasticsearch for movie and line details
    movie_lines = search_elasticsearch(query)

    # Step 3: Search MySQL for movie and line details
    results = search_mysql(movie_lines)

    return jsonify({"movies": results}), 200


def write_to_mysql(movie_name, subtitle_data):
    # Get the maximum movie_id from the subtitles table
    #TODO: Change this to autoincrement
    query = "SELECT IFNULL(MAX(movie_id), 0) + 1 FROM subtitles"
    cursor.execute(query)
    row = cursor.fetchone()
    movie_id = row[0]

    # Prepare the insert query
    query = "INSERT INTO subtitles (movie_id, movie_name, line_id, start_time, end_time, text) VALUES (%s, %s, %s, %s, %s, %s)"

    # Insert each subtitle into MySQL
    for subtitle in subtitle_data:
        line_id = subtitle['line_id']
        start_time = datetime.fromtimestamp(subtitle['start_time']).strftime('%H:%M:%S')
        end_time = datetime.fromtimestamp(subtitle['end_time']).strftime('%H:%M:%S')
        text = subtitle['text']
        cursor.execute(query, (movie_id, movie_name, line_id, start_time, end_time, text))

    # Commit the changes to the database
    cnx.commit()

def write_to_elasticsearch(movie_name, subtitle_data):
    # Index each subtitle into Elasticsearch
    for subtitle in subtitle_data:
        text = subtitle['text']
        start_time = subtitle['start_time']
        end_time = subtitle['end_time']
        doc = {
            'movie_name': movie_name,
            'text': text,
            'start_time': start_time,
            'end_time': end_time
        }
        es.index(index='subtitles', body=doc)

@app.route('/upload', methods=['POST'])
def upload_subtitle():
    file = request.files.get('srt_file')
    movie_name = request.form.get('movie_name')

    if not movie_name:
        return jsonify(error='Movie name is required.')

    try:
        content = file.read().decode('utf-8')
    except UnicodeDecodeError:
        logging.debug("UnicodeDecodeError occurred!")
        try:
            file.seek(0)  # Reset the file pointer to the beginning
            content = file.read().decode("latin-1")
        except Exception as e:
            logging.debug("Exception occurred in Latin-1 conversion:", str(e))

    logging.debug(content)
    # Parse the SRT content
    subs = srt.parse(content)

    subtitle_data = []
    for i, subtitle in enumerate(subs):
        data = {
            'line_id': i + 1,
            'start_time': subtitle.start.total_seconds(),
            'end_time': subtitle.end.total_seconds(),
            'text': subtitle.content
        }
        subtitle_data.append(data)
    logging.debug(subtitle_data)
    # Write subtitle data to MySQL
    write_to_mysql(movie_name, subtitle_data)

    # # Write subtitle data to Elasticsearch
    write_to_elasticsearch(movie_name, subtitle_data)

    return jsonify({"message": "Subtitle uploaded successfully."}), 200

@app.route('/subtitles', methods=['GET'])
def get_subtitles():
    # Connect to the MySQL database
    connection = mysql.connector.connect(**mysql_config)
    cursor = connection.cursor()

    # Retrieve all rows from the "subtitles" table
    query = "SELECT * FROM subtitles"
    cursor.execute(query)
    rows = cursor.fetchall()

    # Close the database connection
    cursor.close()
    connection.close()

    # Format the rows as a list of dictionaries
    subtitles = []
    for row in rows:
        subtitle = {
            'movie_id': row[0],
            'movie_name': row[1],
            'line_id': row[2],
            'start_time': str(row[3]),
            'end_time': str(row[4]),
            'text': row[5]
        }
        subtitles.append(subtitle)

    # Return the subtitles line by line
    response = ''
    for subtitle in subtitles:
        response += f"Line ID: {subtitle['line_id']}\n"
        response += f"Movie Name: {subtitle['movie_name']}\n"
        response += f"Start Time: {subtitle['start_time']}\n"
        response += f"End Time: {subtitle['end_time']}\n"
        response += f"Text: {subtitle['text']}\n"
        response += '\n'

    return response

@app.route('/movies', methods=['GET'])
def get_movies():
    try:
        # Connect to MySQL
        cnx = mysql.connector.connect(**mysql_config)
        cursor = cnx.cursor()

        # Retrieve movie names
        query = "SELECT movie_name FROM subtitles"
        cursor.execute(query)
        movies = [row[0] for row in cursor.fetchall()]

        # Close MySQL connection
        cursor.close()
        cnx.close()

        # Return the movie names as JSON response
        return jsonify(movies)

    except mysql.connector.Error as err:
        # Handle MySQL errors
        return str(err), 500
if __name__ == '__main__':
    app.run(debug=True)
