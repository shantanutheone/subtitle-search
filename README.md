# Subtitle Search System
The Subtitle Search System is a tool that allows users to search for specific text within the subtitles of movies. It provides the context in which the text appears and also indicates the movies where the text is found.

<h2>Overview</h2>
The Subtitle Search System is designed to assist users in finding specific text within movie subtitles. It is particularly useful for individuals who want to locate a particular quote, dialogue, or scene within a movie.

The system provides the following features:

- Text search within subtitle files: Users can search for any text they want within the subtitle files.
- Contextual results: The system displays the context of the matched text, including the nearby lines.
- Movie indicators: The system indicates the movies where the matched text is found.
<h2>Installation</h2>
To install and run the Subtitle Search System locally using Docker, follow these steps:

Clone the repository:

```sh
git clone https://github.com/your-username/subtitle-search.git
```
Navigate to the project directory:

```sh
cd subtitle-search
```
Build and run the Docker containers using docker-compose:
```sh
docker-compose up --build
```
This command will build the Docker images and start the containers.

Access the system using Postman or any other API testing tool at http://localhost:5000.

<h2>Usage</h2>
The Subtitle Search System provides a RESTful API for searching movie subtitles. Follow these steps to use the API:

1. Open Postman or any other API testing tool.

2. Make a POST request to the following endpoint: http://localhost:5000/search

3. Set the request body as JSON with the following structure:

```json
{
  "query": "text to search"
}
```
4. Replace "text to search" with the actual text you want to search for.

5. Send the request.

The API will return a response with a list of movies where the text was found and the context of the matched text.

<h2>API Endpoints</h2>
The Subtitle Search System exposes the following API endpoints:

<h3>Search for Text</h3>

- Endpoint: /search
- Method: POST
- Request Body: JSON
```json
{
  "query": "text to search"
}
```
Response:
```json
{
  "movies": [
    {
      "title": "Movie 1",
      "line": "Line where the hit is found",
      "context": [
        "Context line 1",
        "Context line 2",
        "...",
        "Context line 5"
      ]
    },
    {
      "title": "Movie 2",
      "line": "Line where the hit is found",
      "context": [
        "Context line 1",
        "Context line 2",
        "...",
        "Context line 5"
      ]
    }
  ]
}
```