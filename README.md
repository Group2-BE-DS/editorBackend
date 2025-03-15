# editorBackend

DRF based backend for C^3 - Collaborative Code Editor

## Table of Contents
- [Introduction](#introduction)
- [Features](#features)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [API Documentation](#api-documentation)
- [Contributing](#contributing)
- [License](#license)

## Introduction
`editorBackend` is a Django Rest Framework (DRF) based backend for the C^3 - Collaborative Code Editor. This backend provides the necessary APIs and functionalities to support collaborative coding features.

## Features
- User Authentication and Authorization
- Code Collaboration
- Real-time Code Editing
- Project and File Management
- WebSocket Support for Real-time Updates

## Installation
To install and run the backend locally, follow these steps:

1. Clone the repository:
   ```bash
   git clone https://github.com/Group2-BE-DS/editorBackend.git
   cd editorBackend
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Apply the migrations:
   ```bash
   python manage.py migrate
   ```

## Configuration
Before running the server, ensure you have configured the necessary environment variables:

- **WakaTime API Key**: You need to set your WakaTime API key in the environment variable `WAKATIME_API_KEY`.
- **Google App Password**: You need to set your Google App password in the environment variable `GOOGLE_APP_PASSWORD`.

You can set these variables in a `.env` file in the root directory of the project:
```env
WAKATIME_API_KEY=your_wakatime_api_key
GOOGLE_APP_PASSWORD=your_google_app_password
```

## Usage
To run the development server using Daphne for ASGI support, execute the following command:
```bash
daphne -p 8000 editorBackend.asgi:application
```

After running the server, the API will be available at `http://127.0.0.1:8000/`. You can use tools like `Postman` or `curl` to interact with the API endpoints.

## API Documentation
The API documentation provides detailed information about the available endpoints, request parameters, and responses. You can access the API documentation at `[API documentation URL]`.

## Contributing
We welcome contributions to improve the editorBackend. To contribute, please follow these steps:

1. Fork the repository.
2. Create a new branch with a descriptive name.
3. Make your changes and commit them with clear messages.
4. Push your changes to your forked repository.
5. Create a pull request to the `main` branch of the original repository.

## License
This project is licensed under the [LICENSE NAME] License. See the `LICENSE` file for more details.
