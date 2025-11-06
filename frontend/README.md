# Dimensional Research Agent - Frontend

React-based frontend for the Dimensional Research Agent using AWS Cloudscape Design System.

## Features

- **Research Dashboard**: Overview of all research sessions
- **Create Research Wizard**: Step-by-step research configuration
- **Real-time Progress Tracking**: Polling-based status updates every 5 seconds
- **Workflow Visualization**: Visual representation of 10-stage research workflow
- **Research History**: Browse and filter past research sessions
- **Settings Management**: Configure research preferences

## Prerequisites

- Node.js 16+
- npm or yarn

## Quick Start

### Install Dependencies

```bash
cd frontend
npm install
```

### Environment Configuration

Create `.env` file:

```bash
cp .env.example .env
```

Edit `.env`:
```
REACT_APP_API_URL=http://localhost:8000
```

### Development

```bash
npm start
```

Opens [http://localhost:3000](http://localhost:3000)

### Production Build

```bash
npm run build
```

Creates optimized production build in `build/` directory.

## Project Structure

```
frontend/
├── public/              # Static files
├── src/
│   ├── pages/          # Main pages
│   │   ├── ResearchDashboard.js
│   │   ├── CreateResearch.js
│   │   ├── ResearchDetails.js
│   │   ├── ResearchHistory.js
│   │   └── Settings.js
│   ├── components/     # Reusable components
│   │   ├── WorkflowVisualizer.js
│   │   └── ResearchProgressTracker.js
│   ├── services/       # API services
│   │   └── api.js
│   ├── hooks/          # Custom React hooks
│   │   └── useResearchStatus.js
│   └── utils/          # Utilities
│       ├── workflowStages.js
│       └── formatters.js
└── package.json
```

## Key Technologies

- **React 18**: UI framework
- **React Router**: Navigation
- **AWS Cloudscape**: Design system
- **Custom Hooks**: `useResearchStatus` for polling

## API Integration

The frontend communicates with the BFF (Backend for Frontend) through REST APIs:

- `POST /api/research` - Create new research
- `GET /api/research/{session_id}` - Get research status (polled every 5s)
- `GET /api/research/history` - Get research history
- `GET /api/research/{session_id}/download` - Download report

## Deployment

### Option 1: AWS Amplify

```bash
amplify init
amplify add hosting
amplify publish
```

### Option 2: CloudFront + S3

```bash
npm run build
aws s3 sync build/ s3://your-bucket/
```

See `../terraform/` for infrastructure setup.

## Development Notes

- Polling interval: 5 seconds (configurable in `useResearchStatus.js`)
- No WebSocket required (simplified architecture)
- Cognito authentication integrated via JWT tokens
- All API calls include JWT in Authorization header

## License

MIT
