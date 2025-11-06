import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import { validateConfig } from './config/app.config';

// Validate configuration before starting the app
if (!validateConfig()) {
  console.error('Application configuration is invalid. Please check your environment variables.');
}

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
