import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import App from './App';
import { VkBridgeProvider } from './context/VkBridgeContext';
import { SessionProvider } from './context/SessionContext';
import './styles/theme.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter basename="/holidays">
      <VkBridgeProvider>
        <SessionProvider>
          <App />
        </SessionProvider>
      </VkBridgeProvider>
    </BrowserRouter>
  </React.StrictMode>,
);
