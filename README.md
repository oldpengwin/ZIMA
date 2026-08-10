# ZIMA Platform - Complete Guide

**The Builders Network** - A self-hosted community platform connecting builders based on skills and neurotypes.

![ZIMA Platform](https://via.placeholder.com/1200x600/131313/57B8DC?text=ZIMA+Platform)

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Node.js 18+
- PostgreSQL 14+
- Docker (optional)

### 1. Clone the Repository

```bash
git clone https://github.com/HOPAMINE/ZIMA.git
cd ZIMA
```

### 2. Set Up Backend

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your database and JWT settings

# Run backend
python src/main.py
```

### 3. Set Up Frontend

```bash
cd src/frontend
npm install

# Create .env
echo "REACT_APP_API_URL=http://localhost:8000/api/v1" > .env

# Run frontend
npm start
```

### 4. Set Up Discord Bot

```bash
cd src/bot
cp .env.example .env
# Edit .env with your Discord bot token

npm install
node index.js
```

The platform will be available at:
- **Frontend**: `http://localhost:3000`
- **API**: `http://localhost:8000`
- **API Docs**: `http://localhost:8000/api/docs`

## 📖 Documentation

- [Frontend Setup](src/frontend/README.md)
- [Backend Setup](backend/README.md)

## 🎯 Features

### ✅ Currently Implemented

- **Discord Bot**: Onboarding, profile collection, role management
- **Neurotype Matching**: 10 archetypes with compatibility matrix
- **RESTful API**: FastAPI backend with JWT authentication
- **React Frontend**: HOPAMINE brand compliant UI
- **Database**: PostgreSQL with SQLAlchemy models
- **Connection System**: Message templates and connection requests

### 🚧 In Development

- **Interactive Visualizations**: 3D globe and network graphs
- **Project Management**: Create and join projects
- **Event System**: Community events and notifications
- **Admin Dashboard**: Moderation tools

## 🏗️ Architecture

```
ZIMA Platform
├── frontend/          # React + Three.js + D3.js
├── backend/           # FastAPI + PostgreSQL
├── bot/               # Discord.js (modular cogs)
└── shared/            # Common resources
```

### Tech Stack

**Backend**:
- FastAPI (Python)
- PostgreSQL
- SQLAlchemy
- JWT Authentication
- Uvicorn / Gunicorn

**Frontend**:
- React 18
- React Router
- Axios
- Three.js (for visualizations)
- D3.js (for network graphs)

**Discord Bot**:
- discord.py
- Cog architecture
- Supabase integration

**Design**:
- HOPAMINE "Eco-Brutalism"
- Swiss-grid discipline
- Acid-bright flat colors
- 1-bit dithered imagery

## 🧠 Neurotypes

The platform uses 10 neurotypes for matching:

1. **🌱 Seedcaster** - Visionaries of regenerative systems
2. **⚙️ Fabricant** - Makers and builders
3. **🍄 Mycelian** - Biological systems experts
4. **🏗️ Terraformer** - Sustainable architecture
5. **💻 Developer** - Software and tools
6. **🎨 Artisan** - Design and aesthetics
7. **📡 Chronicler** - Storytelling and media
8. **🌿 Cultivar** - Food science and agriculture
9. **🔗 Loomkeeper** - Community builders
10. **📜 Verdant** - Policy and advocacy

## 🔧 Configuration

### Environment Variables

Create `.env` files for each component:

**Backend** (`.env`):
```env
DATABASE_URL=postgresql://user:password@localhost:5432/zima
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
FRONTEND_URL=http://localhost:3000
```

**Frontend** (`src/frontend/.env`):
```env
REACT_APP_API_URL=http://localhost:8000/api/v1
```

**Discord Bot** (`src/bot/.env`):
```env
DISCORD_TOKEN=your-bot-token
DISCORD_APPLICATION_ID=your-app-id
DISCORD_SERVER_ID=your-server-id
ONBOARDING_CHANNEL_ID=your-channel-id
VETTED_ROLE_ID=your-role-id
SUPABASE_URL=your-supabase-url
SUPABASE_SERVICE_ROLE_KEY=your-supabase-key
```

## 📦 Project Structure

```
ZIMA/
├── src/
│   ├── frontend/          # React frontend
│   │   ├── components/     # Reusable UI components
│   │   ├── pages/          # Page components
│   │   ├── api.js          # API client
│   │   └── App.jsx         # Main app
│   │
│   ├── api/               # FastAPI routes
│   │   └── routes.py       # API endpoints
│   │
│   ├── core/              # Core logic
│   │   ├── neurotype_matcher.py  # Matching algorithm
│   │   └── profile_manager.py   # Profile operations
│   │
│   ├── database/          # Database
│   │   └── models.py       # SQLAlchemy models
│   │
│   ├── bot/               # Discord bot
│   │   ├── cogs/           # Bot cogs
│   │   │   └── matching.py # Matching commands
│   │   └── index.js        # Bot entry point
│   │
│   └── main.py            # FastAPI entry point
│
├── demo/                  # Frontend prototypes
│   ├── index.html         # Main demo page
│   ├── zima-globe.html     # 3D globe visualization
│   └── zima-network-demo.html # Network graph
│
├── supabase/              # Database schema
│   └── schema.sql         # SQL schema
│
├── requirements.txt       # Python dependencies
├── package.json           # Node.js dependencies
└── README.md              # This file
```

## 🔗 API Endpoints

### Authentication
- `POST /api/v1/token` - Get JWT token
- `GET /api/v1/profiles/me` - Get current user

### Profiles
- `POST /api/v1/profiles` - Create profile
- `GET /api/v1/profiles` - Search profiles
- `GET /api/v1/profiles/{id}` - Get profile
- `PUT /api/v1/profiles/{id}` - Update profile

### Matching
- `GET /api/v1/match/{user_id}` - Find matches
- `POST /api/v1/match/request` - Send connection request
- `GET /api/v1/match/{user_id}/requests` - Get requests

### Neurotypes
- `GET /api/v1/neurotypes` - List all neurotypes

## 🤖 Discord Bot Commands

- `/setup-onboarding` - Set up onboarding in a channel
- `/match` - Find compatible builders
- `/connect @user` - Connect with a user
- `/my-matches` - View your connections
- `/neurotypes` - Learn about neurotypes

## 🎨 Design System (HOPAMINE)

### Colors
```
Sky Blue: #57B8DC (Primary)
Near-Black: #131313 (Background)
Hot Magenta: #E93CA7 (Accent)
Deep Ocean Blue: #1E6193 (Secondary)
Lime: #A4C24B (Accent)
Bone: #E7E4DB (Text)
Off-White: #F4F2EB (Light text)
```

### Typography
- **The Shout**: Archivo Black / Helvetica Now Black (ALL CAPS)
- **The Talk**: Oswald Narrow / Roboto Condensed (ALL CAPS)
- **The Whisper**: Caveat / Ephesis (Magenta, script)

### Layout Anatomy
```
[Top accent stripe]
[Micro kicker (top-left)]
[Justified display block]
[3-column micro grid OR hairline-ruled table]
[Footer (pill counter + two solid color dots + wordmark)]
```

## 🚀 Deployment

### Docker

```bash
docker-compose up --build
```

### Production

```bash
# Backend
gunicorn -k uvicorn.workers.UvicornWorker -w 4 -b 0.0.0.0:8000 main:app

# Frontend
npm run build
serve -s frontend/build -l 3000
```

## 🧪 Testing

Run tests for each component:

```bash
# Backend tests
pytest

# Frontend tests
cd src/frontend
npm test
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Write tests
4. Submit a pull request

## 📄 License

MIT License

## 📞 Support

For issues, questions, or contributions:
- Open an issue on GitHub
- Join our Discord community
- Check the documentation

---

**Status**: Active Development
**Version**: 1.0.0
**License**: MIT