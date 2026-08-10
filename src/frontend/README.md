# ZIMA Frontend - HOPAMINE Brand

This is the React frontend for the ZIMA platform, implementing the HOPAMINE "Eco-Brutalism" design system.

## Setup

### Prerequisites
- Node.js v18+ (LTS recommended)
- npm v9+
- Backend API running (see main README)

### Installation

```bash
cd src/frontend
npm install
```

### Configuration

Create a `.env` file in the `src/frontend` directory:

```env
REACT_APP_API_URL=http://localhost:8000/api/v1
```

### Running the Development Server

```bash
npm start
```

This will start the development server on `http://localhost:3000`.

### Building for Production

```bash
npm run build
```

This creates an optimized build in the `build/` directory.

## Project Structure

```
src/frontend/
├── components/          # Reusable UI components
│   ├── ProfileCard.jsx  # Profile card with neurotype styling
│   └── ConnectModal.jsx # Connection modal with message templates
│
├── pages/              # Page components
│   └── ProfilePage.jsx  # Detailed profile view
│
├── App.jsx             # Main application component
├── Login.jsx           # Authentication page
├── index.jsx           # Entry point with routing
├── api.js              # API client
├── package.json        # Frontend dependencies
└── README.md           # This file
```

## API Integration

The frontend connects to the FastAPI backend through the `api.js` module, which provides:

- `authApi`: Authentication endpoints
- `profileApi`: Profile management
- `matchApi`: Matching and connection requests
- `neurotypeApi`: Neurotype information

All API calls include proper error handling and JWT authentication.

## Design System

The frontend implements the HOPAMINE "Eco-Brutalism" design:

### Colors
- Sky Blue: `#57B8DC` (Primary)
- Near-Black: `#131313` (Background)
- Hot Magenta: `#E93CA7` (Accent)
- Deep Ocean Blue: `#1E6193` (Secondary)
- Lime: `#A4C24B` (Accent)

### Typography
- **The Shout**: Archivo Black / Helvetica Now Black (ALL CAPS)
- **The Talk**: Oswald Narrow / Roboto Condensed (ALL CAPS)
- **The Whisper**: Caveat / Ephesis (Magenta, script)

### Layout
- Swiss-grid discipline
- Brutalist typography
- Acid-bright flat colors
- 1-bit dithered nature imagery

## Routes

- `/`: Main matching interface
- `/login`: Authentication page
- `/profile/:profileId`: Detailed profile view

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `REACT_APP_API_URL` | Backend API base URL | `http://localhost:8000/api/v1` |

## Testing

Run tests with:

```bash
npm test
```

## Linting

```bash
npm run lint
```

## Formatting

```bash
npm run format
```

## Deployment

The frontend is designed to be served from the backend's static files directory or deployed separately to a CDN.

Build the production bundle:

```bash
npm run build
```

Then serve the `build/` directory with your preferred web server.
