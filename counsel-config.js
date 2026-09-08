// Set this to the public HTTPS counseling endpoint after the backend is ready.
// Never put an Ollama URL or a secret API key in this public file.
window.COUNSEL_CONFIG = {
  endpoint: ['127.0.0.1', 'localhost'].includes(location.hostname)
    ? '/api/chat'
    : 'https://escape-surfaces-polo-swing.trycloudflare.com/api/chat',
};
