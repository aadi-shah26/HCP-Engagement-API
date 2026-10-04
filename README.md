# HCP Engagement API

A comprehensive healthcare professional engagement platform with AI-powered medical literature search, risk assessment, and analytics capabilities.

![top screenshot](docs/dashboard-top.png)
----
![bottom screenshot](docs/dashboard-bottom.png)

## Features

### AI-Powered Medical Search
- **Real-time Literature Search**: Search PubMed database for medical research articles
- **AI-Generated Summaries**: Get intelligent summaries of search results using Groq AI
- **Real-time Streaming**: PubMed results render immediately while the Groq synthesis streams into the dashboard token by token over an authenticated WebSocket
- **Smart Suggestions**: AI-powered autocomplete for medical terms and conditions
- **Collapsible Article View**: Expandable article entries with full abstracts

### Analytics Dashboard
- **Risk Assessment**: AI-powered patient risk analysis with confidence scores
- **Cost Analysis**: Treatment cost estimation and efficiency ratings
- **Population Trends**: Demographic analysis and risk distribution
- **Interactive Charts**: Visual representation of analytics data

### Authentication & Security
- **JWT-based Authentication**: Signed, expiring tokens on every protected REST route and on the WebSocket handshake
- **Role-based Access**: Support for different user roles and specialties
- **Brute-force Protection**: Failed logins are rate-limited per username
- **Origin Allow-list**: Only configured frontend origins may open a WebSocket
- **No Hardcoded Secrets**: Signing keys come from the environment (random per-process fallback)

## Tech Stack

### Backend
- **Flask**: Python web framework
- **Flask-SocketIO**: WebSocket streaming of AI responses and real-time alerts
- **PyJWT + bcrypt**: JWT authentication and password hashing
- **Flask-Limiter**: Login rate limiting
- **Groq AI**: AI-powered analysis and summaries (streamed via server-sent events)
- **PubMed API**: Medical literature search via `pymed`
- **Gunicorn**: Threaded production server

### Frontend
- **Next.js**: React framework
- **TypeScript**: Type-safe JavaScript
- **Tailwind CSS**: Utility-first CSS framework
- **Lucide React**: Beautiful icons
- **API Proxy**: Next.js API routes for backend communication
- **socket.io-client**: Receives streamed AI output in real time

### Infrastructure
- **Docker**: Separate images for the API and frontend (non-root, health-checked)
- **Docker Compose**: One command to run the full stack

## Prerequisites

- Groq API key
- **With Docker:** Docker with Compose v2
- **Without Docker:** Python 3.11, Node.js 18+, npm

## Quick Start with Docker

```bash
cp hcp-engagement-api-dev/.env.example hcp-engagement-api-dev/.env
# edit .env: set GROQ_API_KEY, SECRET_KEY and JWT_SECRET_KEY

docker compose up --build
```

- Frontend: http://localhost:3000
- Backend API docs: http://localhost:5000/docs/

The frontend container reaches the API over the Compose network (`BACKEND_URL=http://backend:5000`); the browser opens the streaming WebSocket to `localhost:5000`. The API runs as a single Gunicorn process with threads, because WebSocket sessions and rate limits are kept in memory.

## Quick Start without Docker

### 1. Clone the Repository
```bash
git clone <repository-url>
cd demo-hcp-engagement-api
```

### 2. Backend Setup
```bash
cd hcp-engagement-api-dev

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables (then fill in the values)
cp .env.example .env

# Start the backend server
python3 app.py
```

### 3. Frontend Setup
```bash
cd hcp-frontend

# Install dependencies
npm install

# Start the development server
npm run dev
```

### 4. Access the Application
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:5000
- **Health Check**: http://localhost:5000/health

## Environment Variables

### Backend (.env)
See [`hcp-engagement-api-dev/.env.example`](hcp-engagement-api-dev/.env.example):
```env
GROQ_API_KEY=your_groq_api_key_here
SECRET_KEY=...        # python3 -c "import secrets; print(secrets.token_hex(32))"
JWT_SECRET_KEY=...
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

### Frontend
- `BACKEND_URL` (server-side, default `http://localhost:5000`): where the Next.js proxy sends API calls
- `NEXT_PUBLIC_SOCKET_URL` (build time, default `http://localhost:5000`): where the browser opens the WebSocket

### Getting a Groq API Key
1. Visit [Groq Console](https://console.groq.com/)
2. Sign up/Login to your account
3. Navigate to API Keys section
4. Create a new API key
5. Copy the key (starts with `gsk_`)

## API Endpoints

### Authentication
- `POST /auth/login` - User login
- `POST /auth/logout` - User logout

### Literature Search
- `POST /literature/search` - Search medical literature with AI analysis
- `GET /literature/health` - Literature service health check

### Analytics
- `POST /analytics/predict-risk` - Risk assessment analysis
- `POST /analytics/predict-cost` - Cost analysis
- `POST /analytics/population-trends` - Population analysis

### AI Services
- `POST /ai/analyze` - General AI analysis
- `POST /ai/suggestions` - AI-powered search suggestions

### WebSocket (Socket.IO)
Connect with `io(url, { auth: { token: '<JWT>' } })`; connections without a valid token are refused.
- emit `stream_analysis` `{ request_id, studies, specialty, keywords, patient_conditions }`
- receive `analysis_chunk` `{ request_id, delta }` for each generated piece of text
- receive `analysis_done` `{ request_id, source }` when finished (`source` is `groq` or `rule_based_fallback`)
- receive `analysis_error` `{ request_id, message }` if the stream breaks partway

A newer `stream_analysis` from the same client cancels the previous one, and disconnecting stops generation upstream.

## Usage

### 1. Login
- Default credentials: `demo_admin` / `admin123`
- Or create new user accounts

### 2. Search Medical Literature
- Enter medical terms, conditions, or treatments
- Get AI-powered suggestions as you type
- View collapsible article results with full abstracts

### 3. View Analytics
- Risk assessment with confidence scores
- Cost analysis and efficiency ratings
- Population trends and demographics

### 4. AI Summaries
- AI-generated summaries stream in live as Groq produces them
- Combines literature findings with analytics data
- Powered by Groq's Llama models

## Development

### Backend Development
```bash
cd hcp-engagement-api-dev
source venv/bin/activate
python3 app.py
```

### Frontend Development
```bash
cd hcp-frontend
npm run dev
```

### Testing
```bash
# Test environment variables
python3 test_env.py

# Test API endpoints
python3 test_api.py
```

## Troubleshooting

### Common Issues

#### Port Conflicts
```bash
# Kill processes on ports 5000 and 5001
lsof -ti:5000,5001 | xargs kill -9
```

#### CORS Issues
- The frontend uses Next.js API proxy routes to avoid CORS
- All API calls go through `/api/proxy/*` endpoints

#### Authentication Errors
- Clear browser localStorage: `localStorage.clear()`
- Re-login to get fresh JWT tokens

#### API Key Issues
- Verify your Groq API key is valid
- Check the `.env` file in the backend directory
- Restart the backend server after updating the key

### Debug Mode
- Backend logs are available in the terminal
- Frontend console shows detailed API request/response logs
- Check browser Network tab for failed requests

## Project Structure

```
demo-hcp-engagement-api/
├── hcp-engagement-api-dev/          # Backend Flask API
│   ├── app.py                       # Main Flask application
│   ├── requirements.txt             # Python dependencies
│   ├── .env                         # Environment variables
│   └── test_*.py                    # Test scripts
├── hcp-frontend/                    # Frontend Next.js app
│   ├── src/app/                     # Next.js app directory
│   │   ├── login/                   # Login page
│   │   ├── dashboard/               # Main dashboard
│   │   └── api/proxy/               # API proxy routes
│   ├── package.json                 # Node.js dependencies
│   └── next.config.js               # Next.js configuration
└── README.md                        # This file
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:
1. Check the troubleshooting section above
2. Review the console logs for error messages
3. Ensure all dependencies are installed correctly
4. Verify API keys are valid and properly configured

## Updates

### Recent Changes
- Added AI-powered search suggestions
- Implemented collapsible article dropdowns
- Added real PubMed integration
- Enhanced AI summary generation
- Improved error handling and debugging
- Fixed CORS issues with Next.js proxy

### Planned Features
- User management system
- Advanced filtering options
- Export functionality
- Real-time notifications
- Mobile responsiveness improvements

## Credits

Built at HackGT 12 with [@aandrx](https://github.com/aandrx).
