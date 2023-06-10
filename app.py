from flask import Flask, request, jsonify
from elasticsearch import Elasticsearch
from datetime import datetime, timedelta
import srt
import logging
import retrying
import hashlib

# Set up the logging configuration
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)

@retrying.retry(wait_fixed=2000, stop_max_attempt_number=5, retry_on_exception=lambda e: isinstance(e, ConnectionError))
def connect_to_elasticsearch():
    es = Elasticsearch(
        hosts=[
            {
                'host': 'elasticsearch',
                'port': 9200,
                'scheme': 'http'
            }
        ]
    )
    body = {
        "mappings": {
            "properties": {
                "line_id": {"type": "long"},
                "movie_name": {"type": "keyword"},
                "start_time": {"type": "keyword"},
                "end_time": {"type": "keyword"},
                "text": {
                    "type": "text",
                    "fields": {
                        "keyword": {"type": "keyword", "ignore_above": 256}
                    }
                }
            }
        }
    }
    try:
        es.indices.create(index="subtitles", body=body)
    except:
        logging.debug("Index subtitles Already Exists! No need to create")
    return es

try:
    es = connect_to_elasticsearch()
    # Continue with Elasticsearch operations
except ConnectionError as e:
    # Handle connection errors
    print(f"Failed to connect to Elasticsearch: {e}")




def search_elasticsearch(query):
    # Search Elasticsearch for query text
    search_body = {
        "query": {
            "match": {
                "text": query
            }
        }
    }
    result = es.search(index='subtitles', body=search_body)
    hits = result['hits']['hits']

    movie_lines = []
    for hit in hits:
        movie_lines.append(
            {
                "movie_name": hit['_source']['movie_name'],
                "line_id": hit['_source']['line_id'],
                "start_time":  hit['_source']['start_time'],
                "end_time":  hit['_source']['end_time'],
                "text": hit['_source']['text']
            }
        )
    return movie_lines


def write_to_elasticsearch(movie_name, subtitle_data):
    # Index each subtitle into Elasticsearch
    for subtitle_info in subtitle_data:
        doc = {
            'movie_name': movie_name,
            'line_id': subtitle_info["line_id"],
            'start_time': subtitle_info["start_time"],
            'end_time': subtitle_info["end_time"],
            'text': subtitle_info["text"]
        }
        es.index(index='subtitles', body=doc)

@app.route('/search', methods=['POST'])
def search_subtitle():
    query = request.json.get('query')

    if not query:
        return jsonify({"error": "Query parameter is missing."}), 400

    # Step 2: Search Elasticsearch for movie and line details
    results = search_elasticsearch(query)
    
    # Serialize the response using the custom JSON serializer
    # for result in results:
    #     result['start_time'] = str(result['start_time'])
    #     result['end_time'] = str(result['end_time'])
    return jsonify({"movies": results}), 200

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
        start_time = str(subtitle.start)
        end_time = str(subtitle.end)
        
        data = {
            'line_id': i + 1,
            'start_time': start_time,
            'end_time': end_time,
            'text': subtitle.content
        }
        subtitle_data.append(data)
    # # Write subtitle data to Elasticsearch
    write_to_elasticsearch(movie_name, subtitle_data)
    logging.debug("Written to ElasticSearch!!!")

    return jsonify({"message": "Subtitle uploaded successfully."}), 200

if __name__ == '__main__':
    app.run(debug=True)
