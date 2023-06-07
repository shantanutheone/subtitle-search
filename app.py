from flask import Flask, request, jsonify
from elasticsearch import Elasticsearch
import mysql.connector

app = Flask(__name__)

# Elasticsearch connection settings
es = Elasticsearch(
    hosts=[
        {
            'host': 'localhost',
            'port': 9200,
            'scheme': 'http'  # Add the 'scheme' component here
        }
    ]
)


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
        start_time = subtitle['start_time']
        end_time = subtitle['end_time']
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
    # Get the movie_name from the request form data
    movie_name = request.form.get('movie_name')

    # Get the uploaded SRT file
    srt_file = request.files.get('srt_file')
    if not srt_file:
        return jsonify({"error": "No SRT file uploaded."}), 400

    # Process the SRT file and extract subtitle data
    subtitle_data = []
    for line in srt_file.readlines():
        line = line.strip().decode('utf-8')
        if line.isdigit():
            # Found the line number, prepare for the next subtitle entry
            subtitle = {}
            subtitle['start_time'], subtitle['end_time'] = srt_file.readline().strip().split(' --> ')

            # Read multiple lines for the subtitle text
            text_lines = []
            while True:
                text_line = srt_file.readline().strip()
                if not text_line or text_line.isdigit():
                    # Reached the end of the text or encountered the next line number
                    break
                text_lines.append(text_line)
            
            # Concatenate the text lines into a single string
            subtitle['text'] = ' '.join(text_lines)
            
            subtitle_data.append(subtitle)

    # Write subtitle data to MySQL
    write_to_mysql(movie_name, subtitle_data)

    # Write subtitle data to Elasticsearch
    write_to_elasticsearch(movie_name, subtitle_data)

    return jsonify({"message": "Subtitle uploaded successfully."}), 200

if __name__ == '__main__':
    app.run(debug=True)
